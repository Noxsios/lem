import click
import boto3
from botocore.exceptions import ClientError
from requests import get
from .configure import get_config
from pathlib import Path
from .console import Console
import json

c = Console()


@click.group()
def k3d():
    pass


@k3d.command()
@click.option("--show-commands", is_flag=True, default=False)
@click.option("-b", "--big", is_flag=True)
@click.option("-p", "--private", is_flag=True)
@click.option("-m", "--metal", is_flag=True)
def create(show_commands, big, private, metal):
    c.set_show_commands(show_commands)
    opt = {}
    key_name = get_config("key-name")
    if big:
        c.info("Will use large m5a.4xlarge spot instance")
        opt["InstSize"] = "m5a.4xlarge"
        opt["SpotPrice"] = "0.69"
    else:
        c.info("Will use standard t3a.2xlarge spot instance")
        opt["InstSize"] = "t3a.2xlarge"
        opt["SpotPrice"] = "0.35"

    client = boto3.client("ec2")

    c.spinner.start("Checking key-pair exists")
    try:
        c.command(
            f"aws ec2 describe-key-pairs --output json --no-cli-pager --key-names {key_name}"
        )
        client.describe_key_pairs(KeyNames=[key_name])
        c.spinner.succeed(f"key-pair {key_name} exists")
    except ClientError as e:
        c.spinner.fail(str(e))
        c.info("Creating new key pair: {}".format(key_name))
        c.command(
            f"aws ec2 create-key-pair --output json --no-cli-pager --key-name {key_name} | jq -r '.KeyMaterial' > ~/.ssh/{key_name}.pem"
        )

        key_pair = client.create_key_pair(
            KeyName=key_name, DryRun=False, KeyType="rsa", KeyFormat="pem"
        )

        key_path = Path().home() / ".ssh" / f"{key_name}.pem"
        with open(key_path, "w") as f:
            f.write(key_pair["KeyMaterial"])
            f.close()
        # this is `chmod 600`
        c.command(f"chmod 600 ~/.ssh/{key_name}.pem")
        key_path.chmod(33152)

    sg_name = key_name
    c.spinner.start("Checking security group exists")
    sg_id = None
    try:
        c.command(
            f"aws ec2 describe-security-groups --output json --no-cli-pager --group-names {sg_name}"
        )
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

        c.command(
            f"aws ec2 create-security-group --output json --no-cli-pager --description 'Security group for {sg_name}' --group-name {sg_name} --vpc-id {get_config('vpc-id')}"
        )
        c.command(
            f"SecurityGroupId=$(aws ec2 describe-security-groups --output json --no-cli-pager --group-names {sg_name} --query 'SecurityGroups[0].GroupId' --output text)"
        )
        c.command(
            f"aws ec2 create-tags --resources ${{SecurityGroupId}} --tags Key=Name,Value={sg_name}"
        )
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
        else:
            c.info("Granting all port access")
            auth = client.authorize_security_group_ingress(
                IpProtocol="all", CidrIp=public_ip_cidr, GroupId=sg_id
            )

    # line 187

    # TODO: query AMIs and get Ubuntu 20 AMIs, then prompt user which to use, include as part of `configure`?

    # ec2 = boto3.resource("ec2")
    # instances = ec2.create_instances(
    #     ImageId=get_config("ami-id"),
    #     MinCount=1,
    #     MaxCount=1,
    #     InstanceType=opt["InstSize"],
    #     KeyName=get_config("key-name"),
    # )


@k3d.command()
def destroy():
    client = boto3.client("ec2")

    resp = client.delete_key_pair(KeyName=get_config("key-name"))

    print(resp)
