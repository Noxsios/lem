import platform

import boto3
import click

from .configure import get_config
from .console import Console

c = Console()


@click.group()
def check():
    pass


@check.command()
def vpc():
    c.command(f"aws ec2 describe-vpcs | grep {vpc_id}")
    vpc_id = get_config()["vpc-id"]

    ec2 = boto3.resource("ec2")

    vpc = ec2.Vpc(vpc_id)

    c.spinner.start("Getting list of VPCs...")

    vpc_list = list(ec2.vpcs.filter())

    if vpc in vpc_list:
        c.spinner.succeed(f"VPC {vpc_id} is available!")
    else:
        c.spinner.fail(
            f"VPC {vpc_id} is not available in the current AWS_PROFILE - update the VPC ID"
        )


@check.command()
def username():
    c.command("aws sts get-caller-identity --query Arn --output text | cut -f 2 -d '/'")

    client = boto3.client("sts")

    arn = client.get_caller_identity()["Arn"]
    # arn:aws-us-gov:iam::11111111111:user/USERNAME

    username = arn.split("/")[-1]

    c.success(f"Your username is: {username}")


@check.command()
@click.option(
    "--extra", help="Check if you have all the tools that @razzle uses", is_flag=True
)
def tools(extra):
    def is_tool(name):
        """Check whether `name` is on PATH and marked as executable."""
        from shutil import which

        return which(name) is not None

    required_cli_tools = [
        "jq",
        "aws",
        "ssh",
        "ssh-keygen",
        "scp",
        "kubectl",
        "fluxctl",
        "helm",
        "kpt",
        "curl",
        "yq",
        "sops",
        "k9s",
        "k3d",
        "python3",
        "docker",
        "git",
    ]

    if platform.system() == "Darwin":
        required_cli_tools += "gsed"
        required_cli_tools += "brew"

    required_cli_tools.sort()

    for x in required_cli_tools:
        c.spinner.start(f"Checking {x} is on PATH")
        if is_tool(x):
            c.spinner.succeed(f"{x} is installed and on PATH")
        else:
            c.spinner.fail(f"{x} is not installed / on PATH")
            c.error(f"https://google.com/search?q=install+{x}+{platform.node()}")

    if extra:
        print()
        extra_tools = [
            "bat",
            "exa",
            "fd",
            "markdownlint-cli2",
            "btm",
            "volta",
            "fish",
            "starship",
        ]

        extra_tools.sort()

        for x in extra_tools:
            c.spinner.start(f"Checking {x} is on PATH")
            if is_tool(x) is not None:
                c.spinner.succeed(f"{x} is installed and on PATH")
            else:
                c.spinner.fail(f"{x} is not installed / on PATH")
