import base64
import json
from pathlib import Path
from time import sleep
import paramiko
from paramiko import (
    BadHostKeyException,
    AuthenticationException,
    SSHException,
    ssh_exception,
)

import boto3
import click
import inquirer
from botocore.exceptions import ClientError
from requests import get
from ruamel.yaml import YAML

from .configure import get_config, set_config
from .console import Console

c = Console()


@click.group()
def ec2():
    pass


@ec2.command()
@click.option("-b", "--big", is_flag=True)
@click.option("-p", "--private", is_flag=True)
@click.option("-m", "--metal", is_flag=True)
def start(big, private, metal):
    key_name = get_config("key-name")

    client = boto3.client("ec2")

    running_inst = get_current_running()

    if len(running_inst) > 0:
        c.error("You currently have 1 or more dev instances running")
        c.command("lem ec2 terminate")
        return

    c.spinner.start("Checking key-pair exists")
    try:
        client.describe_key_pairs(KeyNames=[key_name])
        c.spinner.succeed(f"key-pair {key_name} exists")
    except ClientError as e:
        c.spinner.fail(str(e))
        c.info("Creating new key pair: {}".format(key_name))

        key_pair = client.create_key_pair(
            KeyName=key_name, DryRun=False, KeyType="rsa", KeyFormat="pem"
        )

        key_path = Path().home() / ".ssh" / f"{key_name}.pem"
        with open(key_path, "w") as f:
            f.write(key_pair["KeyMaterial"])
            f.close()
        # this is `chmod 600`
        key_path.chmod(33152)

    sg_name = key_name
    c.spinner.start("Checking security group exists")
    sg_id = None
    try:
        sg = client.describe_security_groups(GroupNames=[sg_name])
        c.spinner.succeed(f"Security group {sg_name} exists")

        if len(sg["SecurityGroups"]) > 1:
            c.error(
                f"There are multiple security groups w/ the Name {sg_name}, delete them"
            )
            exit(0)

        sg_id = sg["SecurityGroups"][0]["GroupId"]
    except ClientError as e:
        c.spinner.fail(str(e))
        c.info("Creating new security group: {sg_name}")

        sg = client.create_security_group(
            Description="Security group for {} Big Bang EC2 dev env".format(
                key_name[:-4]
            ),
            GroupName=sg_name,
            VpcId=get_config("vpc-id"),
            TagSpecifications=[
                {
                    "ResourceType": "security-group",
                    "Tags": [{"Key": "Name", "Value": sg_name}],
                }
            ],
        )
        c.info(f"Security group: {sg['GroupId']} created")
        sg_id = sg["GroupId"]

    public_ip = (
        get("https://checkip.amazonaws.com").content.decode("utf8").splitlines()[0]
    )
    public_ip_cidr = public_ip + "/32"
    c.spinner.start("Checking if public IP is authorized to access your sg")
    my_public_ip_is_authorized = False
    ingress_rule = None

    sgdr = client.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sg_id]}]
    )["SecurityGroupRules"]

    # TODO: change rules if they rerun create w/ --private AFTER running w/o --private?
    # TODO: same as above ^, but the reverse operation

    for rule in sgdr:
        if rule["CidrIpv4"] == public_ip_cidr:
            my_public_ip_is_authorized = True
            ingress_rule = rule
            c.spinner.succeed(f"{public_ip_cidr} is able to access {sg_name}")
            break

    if my_public_ip_is_authorized == False:
        c.spinner.fail(
            f"{public_ip_cidr} is unable to access {sg_name}, adding new rule"
        )
        if private:
            c.info("Granting port 22 access only")
            auth = client.authorize_security_group_ingress(
                IpProtocol="tcp",
                FromPort=22,
                ToPort=22,
                CidrIp=public_ip_cidr,
                GroupId=sg_id,
            )
            print(json.dumps(auth, indent=2))
            # TODO: what comes after this?
        else:
            c.info("Granting all port access")
            auth = client.authorize_security_group_ingress(
                IpProtocol="all", CidrIp=public_ip_cidr, GroupId=sg_id
            )
            print(json.dumps(auth, indent=2))

    launch_spec = {
        "ImageId": get_config("ami-id"),
        "InstanceType": "",
        "KeyName": key_name,
        "SecurityGroupIds": [sg_id],
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "DeleteOnTermination": True,
                    "VolumeType": "gp2",
                    "VolumeSize": 120,
                },
            }
        ],
        "UserData": str(
            base64.b64encode(
                Path.home().joinpath(".p1-lem/userdata.txt").open("rb").read()
            ).decode("ascii")
        ),
    }
    c.info("Will use ~/.p1-lem/userdata.txt")
    if big:
        c.info("Will use large m5a.4xlarge spot instance")
        launch_spec["InstanceType"] = "m5a.4xlarge"
        spot_price = "0.69"
    else:
        c.info("Will use standard t3a.2xlarge spot instance")
        launch_spec["InstanceType"] = "t3a.2xlarge"
        spot_price = "0.35"

    c.spinner.start("Requesting an EC2 spot instance")
    spot_inst_res = client.request_spot_instances(
        InstanceCount=1,
        Type="one-time",
        SpotPrice=spot_price,
        LaunchSpecification=launch_spec,
        TagSpecifications=[
            {
                "ResourceType": "spot-instances-request",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": f"{key_name}-spot-request",
                    }
                ],
            },
        ],
    )

    waiter = client.get_waiter("spot_instance_request_fulfilled")
    sir_id = spot_inst_res["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
    waiter.wait(SpotInstanceRequestIds=[sir_id])
    c.spinner.succeed(spot_inst_res["SpotInstanceRequests"][0]["Status"]["Message"])

    c.spinner.start(f"Tagging EC2 instance created from {sir_id}")
    inst_req = client.describe_spot_instance_requests(SpotInstanceRequestIds=[sir_id])
    inst_id = inst_req["SpotInstanceRequests"][0]["InstanceId"]
    client.create_tags(
        Resources=[inst_id],
        Tags=[
            {"Key": "Name", "Value": key_name},
            {"Key": "created-with", "Value": "https://github.com/Noxsios/lem"},
        ],
    )
    c.spinner.text = (
        f"Instance ({inst_id}) tagged, now waiting for instance to be (running)"
    )
    waiter = client.get_waiter("instance_running")
    waiter.wait(InstanceIds=[inst_id])
    while True:
        statuses = client.describe_instance_status(InstanceIds=[inst_id])
        status = statuses["InstanceStatuses"][0]
        if (
            status["InstanceStatus"]["Status"] == "ok"
            and status["SystemStatus"]["Status"] == "ok"
        ):
            break
        sleep(5)

    c.spinner.succeed(f"Instance ({inst_id}) is ready")
    inst = client.describe_instances(InstanceIds=[inst_id])["Reservations"][0][
        "Instances"
    ][0]

    c.spinner.start("Provisioning new instance w/ dev dependencies")
    with paramiko.SSHClient() as ssh:
        ssh_key = paramiko.RSAKey.from_private_key_file(
            str(Path.home() / ".ssh" / key_name) + ".pem"
        )
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        attempts = 0
        while attempts < 5:
            try:
                ssh.connect(inst["PublicIpAddress"], pkey=ssh_key, username="ubuntu")
                c.spinner.text = "Running ~/provision/install-deps.sh"
                stdin, stdout, stderr = ssh.exec_command(
                    "cd ~/provision && ./install-deps.sh"
                )
                stdout.channel.set_combine_stderr(True)
                out = stdout.read().decode().strip()
                # print(out)
                c.spinner.succeed("Ran ~/provision/install-deps.sh")
                break
            except (
                BadHostKeyException,
                AuthenticationException,
                SSHException,
                ssh_exception.NoValidConnectionsError,
            ) as e:
                c.spinner.text = "Unable to ssh, retrying in 5s"
                attempts += 1
                sleep(5)
        ssh.close()
        if attempts == 4:
            c.error("Unable to provision automatically.")
            c.error("Provision manually w/")
            c.command(base_ssh_command)

    c.info("Private IP: {}".format(inst["PrivateIpAddress"]))
    c.info("Public IP: {}".format(inst["PublicIpAddress"]))
    c.info("Connect w/")

    base_ssh_command = f"ssh -i ~/.ssh/{key_name}.pem ubuntu@{inst['PublicIpAddress']}"
    base_k3d_command = "k3d cluster create -c ~/provision/k3d-config.yaml"
    metal_flag = "--network k3d-network"
    public_flag = f"--k3s-arg '--tls-san={inst['PublicIpAddress']}@server:0'"
    private_flag = f"--k3s-arg '--tls-san={inst['PrivateIpAddress']}@server:0'"

    c.command(base_ssh_command)
    c.info("Starting k3d w/")
    if private and metal:
        k3d_start_command = f"{base_k3d_command} {private_flag} {metal_flag}"
    elif private:
        k3d_start_command = f"{base_k3d_command} {private_flag}"
    elif metal:
        k3d_start_command = f"{base_k3d_command} {public_flag} {metal_flag}"
    else:
        # public and no metal (default)
        k3d_start_command = f"{base_k3d_command} {public_flag}"
    c.command(k3d_start_command)

    c.spinner.start("Running above command...")
    with paramiko.SSHClient() as ssh:
        ssh_key = paramiko.RSAKey.from_private_key_file(
            str(Path.home() / ".ssh" / key_name) + ".pem"
        )
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(inst["PublicIpAddress"], pkey=ssh_key, username="ubuntu")

        if metal:
            c.spinner.text = "$ ssh ... 'bash ~/provision/init-metallb.sh'"
            stdin, stdout, stderr = ssh.exec_command("bash ~/provision/init-metallb.sh")
            stdout.channel.set_combine_stderr(True)
            out = stdout.read().decode().strip()
            # print(out)

        c.spinner.text = f"$ ssh ... '{k3d_start_command}'"
        stdin, stdout, stderr = ssh.exec_command(k3d_start_command)
        stdout.channel.set_combine_stderr(True)
        out = stdout.read().decode().strip()
        # print(out)

        c.spinner.stop()
        _, stdout, _ = ssh.exec_command("cat ~/.kube/config")
        remote_kubeconfig = YAML().load(stdout.read().decode().strip())
        remote_kubeconfig["clusters"][0]["cluster"]["server"] = (
            f"https://{inst['PrivateIpAddress']}:6443"
            if private
            else f"https://{inst['PublicIpAddress']}:6443"
        )
        dev_kubeconfig_path = Path.home() / ".kube" / f"{key_name}-bb-dev-config"
        with dev_kubeconfig_path.open("w") as f:
            YAML().dump(remote_kubeconfig, f)
            f.close()
        c.info("To access your new cluster w/ kubectl:")
        c.command(f"export KUBECONFIG={str(dev_kubeconfig_path.expanduser())}")

        set_config("current-instance-ip", inst["PublicIpAddress"])


def get_current_running():
    client = boto3.client("ec2")

    c.spinner.start("Getting currently running EC2 instances")
    running_inst = client.describe_instances(
        Filters=[
            {"Name": "key-name", "Values": [get_config("key-name")]},
            {"Name": "tag:created-with", "Values": ["https://github.com/Noxsios/lem"]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    )["Reservations"]
    c.spinner.succeed(
        "Got currently running EC2 instances ({})".format(len(running_inst))
    )

    return running_inst


@ec2.command()
def terminate():
    client = boto3.client("ec2")

    running_inst = get_current_running()

    inst_to_delete = []

    for reservation in running_inst:
        insts = list(
            map(
                lambda i: i["InstanceId"]
                + " created on "
                + i["LaunchTime"].strftime("%m-%d-%Y"),
                reservation["Instances"],
            )
        )
        c.warning(f"Planning to delete: {', '.join(insts)}")
        ans = c.prompt(
            [
                inquirer.Confirm(
                    "confirm-deletion",
                    message="Are you sure you want to delete this instance(s)?",
                    default=True,
                )
            ]
        )
        if ans["confirm-deletion"]:
            for inst_str in insts:
                inst_to_delete.append(inst_str.split(" ")[0])

    if len(inst_to_delete) > 0:
        c.spinner.start("Terminating {} EC2 instance(s)...".format(len(inst_to_delete)))
        client.terminate_instances(InstanceIds=inst_to_delete)

        waiter = client.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=inst_to_delete)
        c.spinner.succeed("Instances have been terminated")
    elif len(running_inst) > 0:
        c.info("No instances selected, Goodbye")
    else:
        c.info(
            f"There are no running instances attached to key-name ({get_config('key-name')})"
        )
