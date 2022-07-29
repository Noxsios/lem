import os
import click
from pathlib import Path
from .console import Console
import inquirer
from ruamel.yaml import YAML

c = Console()


base_config = {
    "p1-dev-path": "~/dev/p1",
    "vpc-id": "vpc-065ffa1c7b2a2b979",
    "ami-id": "ami-84556de5",
    "aws-username": "",
    "last-used-k3d-options": {},
}

configure_questions = [
    inquirer.Path(
        "p1-dev-path",
        message="P1 Dev Directory",
        default="~/dev/p1",
    ),
    inquirer.Text("vpc-id", message="AWS VPC ID", default=base_config["vpc-id"]),
    inquirer.Text("ami-id", message="AWS AMI ID", default=base_config["ami-id"]),
]

config_path = Path.home().joinpath(".p1-lem/config.yaml")


def get_config():
    config = YAML().load(config_path)
    return config


@click.command()
def configure():
    config = c.prompt(configure_questions)

    os.makedirs(Path.home().joinpath(".p1-lem"), exist_ok=True)

    with config_path.open("w") as f:
        YAML().dump(config, f)
        f.close()
