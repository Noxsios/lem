import os
from datetime import datetime
from pathlib import Path

import boto3
import click
import inquirer
from ruamel.yaml import YAML

from .console import Console

c = Console()


base_config = {
    "p1-dev-path": "~/dev/p1",
    "vpc-id": "vpc-065ffa1c7b2a2b979",
    "ami-id": "ami-84556de5",
    "key-name": "",
    "last-used-k3d-options": {},
}

ubuntu_20_04_amis = boto3.client("ec2").describe_images(
    Filters=[
        {
            "Name": "name",
            "Values": ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server*"],
        },
        {"Name": "architecture", "Values": ["x86_64"]},
    ],
    IncludeDeprecated=False,
)["Images"]

ubuntu_20_04_five_latest = sorted(
    ubuntu_20_04_amis, key=lambda img: img["CreationDate"], reverse=True
)[:5]

ubuntu_20_04_choices = list(
    map(
        lambda img: img["ImageId"]
        + " "
        + datetime.strptime(img["CreationDate"], r"%Y-%m-%dT%H:%M:%S.%fZ").isoformat(
            sep=" "
        ),
        ubuntu_20_04_five_latest,
    )
)

configure_questions = [
    inquirer.Path(
        "p1-dev-path",
        message="P1 Dev Directory",
        default="~/dev/p1",
    ),
    inquirer.Text("vpc-id", message="AWS VPC ID", default=base_config["vpc-id"]),
    inquirer.Text(
        "key-name",
        message="AWS Key Name",
        default=boto3.client("sts").get_caller_identity()["Arn"].split("/")[-1]
        + "-dev",
    ),
    inquirer.List(
        "ami-id",
        message="AMI (Ubuntu 20.04)",
        choices=ubuntu_20_04_choices,
        default=base_config["ami-id"],
    ),
]

config_path = Path.home().joinpath(".p1-lem/config.yaml")

cached_config = dict()


def get_config(key):
    if key not in cached_config:
        config = YAML().load(config_path)
        cached_config[key] = config[key]
    return cached_config[key]


def set_config(key, val):
    config = YAML().load(config_path)
    config[key] = val

    with config_path.open("w") as f:
        YAML().dump(config, f)
        f.close()


@click.command()
def configure():
    config = c.prompt(configure_questions)
    config["ami-id"] = config["ami-id"].split(" ")[0]

    os.makedirs(Path.home().joinpath(".p1-lem"), exist_ok=True)

    with config_path.open("w") as f:
        YAML().dump(config, f)
        f.close()

    c.info("Config saved to ~/.p1-lem/config.yaml")
