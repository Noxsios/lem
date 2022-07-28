import click
import platform
from .console import Console

c = Console()


@click.group()
def check():
    pass


@check.command()
def vpc():
    vpc_id = "vpc-065ffa1c7b2a2b979"
    ami_id = "ami-84556de5"

    import boto3

    ec2 = boto3.resource("ec2")

    vpc = ec2.Vpc(vpc_id)

    vpc_list = list(ec2.vpcs.filter())

    if vpc in vpc_list:
        c.success(f"VPC {vpc_id} is available!")
    else:
        c.error(
            f"VPC {vpc_id} is not available in the current AWS_PROFILE - update the VPC ID"
        )


@check.command()
def tools():
    def is_tool(name):
        """Check whether `name` is on PATH and marked as executable."""
        from shutil import which

        return which(name) is not None

    required_cli = [
        "jq",
        "aws",
        "ssh",
        "ssh-keygen",
        "scp",
        "kubectl",
        "fluxctl",
        "helm",
    ]

    required_cli.sort()

    if platform.system() == "Darwin":
        required_cli += "gsed"

    for x in required_cli:
        c.spinner.start(f"Checking {x} is on PATH")
        if is_tool(x) is not None:
            c.spinner.succeed(f"{x} is installed and on PATH")
        else:
            c.spinner.fail(f"{x} is not installed / on PATH")
            break
