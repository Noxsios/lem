import click
import boto3
from botocore.exceptions import ClientError
from .configure import get_config
from pathlib import Path
from .console import Console

c = Console()


@click.group()
def k3d():
    pass


@k3d.command()
@click.option("-b", "--big", is_flag=True)
@click.option("-p", "--private", is_flag=True)
@click.option("-m", "--metal", is_flag=True)
def create(c, big, private, metal):
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

    # check that key-pair exists, otherwise create
    try:
        c.command(
            f"aws ec2 describe-key-pairs --output json --no-cli-pager --key-names {key_name}"
        )
        client.describe_key_pairs(KeyNames=[key_name])
    except ClientError as e:
        c.error(str(e))
        c.info("Creating new key pair: {}".format(key_name))
        key_pair = client.create_key_pair(
            KeyName=key_name, DryRun=False, KeyType="rsa", KeyFormat="pem"
        )

        c.command(
            f"aws ec2 create-key-pair --output json --no-cli-pager --key-name {key_name} | jq -r '.KeyMaterial' > ~/.ssh/{key_name}.pem"
        )
        key_path = Path().home() / ".ssh" / f"{key_name}.pem"
        with open(key_path, "w") as f:
            f.write(key_pair["KeyMaterial"])
            f.close()
        # this is `chmod 600`
        key_path.chmod(33152)

    # check that security group exists
    # on line 148

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
