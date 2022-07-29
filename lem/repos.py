from pathlib import Path

import click
import inquirer
import requests
from ruamel.yaml import YAML

from .configure import get_config
from .console import Console

import subprocess as sp

c = Console()


@click.group()
def repo():
    pass


@repo.command()
def clone():
    root = Path(get_config()["p1-dev-path"]).expanduser().resolve()

    cloned_pkgs = [f.name for f in Path(root).iterdir() if f.is_dir()]

    c.spinner.start("cURLing Big Bang's chart/values.yaml")
    values_url = "https://repo1.dso.mil/platform-one/big-bang/bigbang/-/raw/master/chart/values.yaml"
    values_res = requests.get(values_url)

    if values_res.status_code != 200:
        c.spinner.fail("Unable to cURL Big Bang's chart values")
        return
    c.spinner.succeed("Got Big Bang's chart/values.yaml")

    values = YAML().load(values_res.text)

    pkgs = []

    # core
    for _, v in values.items():
        if isinstance(v, dict) and "git" in v:
            pkgs.append(
                {
                    "name": v["git"]["repo"].split("/")[-1].split(".")[0],
                    "repo": v["git"]["repo"],
                }
            )
    # addons
    for _, v in values["addons"].items():
        if isinstance(v, dict) and "git" in v:
            pkgs.append(
                {
                    "name": v["git"]["repo"].split("/")[-1].split(".")[0],
                    "repo": v["git"]["repo"],
                }
            )

    pkgs_not_installed = list(
        set([pkg["name"] for pkg in pkgs]).difference(cloned_pkgs)
    )
    pkgs_not_installed.sort()

    pkgs_question = [
        inquirer.Checkbox(
            "pkgs-selected",
            message="Select which repo(s) you would like to clone",
            choices=pkgs_not_installed,
        )
    ]

    ans = c.prompt(pkgs_question)

    if ans is None:
        exit()

    for pkg in ans["pkgs-selected"]:
        repo_url = [p for p in pkgs if p["name"] == pkg][0]["repo"]

        sp.run(["git", "clone", repo_url], cwd=root)

        c.info(f"\n{pkg} is now available at {root}/{pkg}\n")
