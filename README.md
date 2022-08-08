# lem

`lem` is a Python CLI for making the Big Bang developer experience a little easier.

Features:

- Clone Big Bang repo's interactively --> `lem repo clone`
- Check access to Big Bang's AWS GovCloud acc (vpc+username) --> `lem check vpc|username`
- Check if you have all the developer tools you will need (`kubectl`, `helm`, `yq`, etc...) --> `lem check tools`, plus I also included my own list w/ the `--extra` flag.
- Standup + teardown an Ubuntu 20.04 EC2 spot instance w/ `lem ec2 up|down`
- WIP: Autoconfigure spot instance w/ dev tools + docker + k3d
- WIP: Deploy Big Bang + run health checks

## Installing

Python 3.9+ is a prereq.
Configuring access to AWS via the AWS CLI is a prereq: [link](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration).

```shell
# create a venv if needed
python3 -m venv venv
source venv/bin/activate

# install from git
python3 -m pip install git+https://github.com/Noxsios/lem.git
```

## Usage

Run in interactive CLI mode:

```shell
lem --help
```

### Command examples

```bash
# configure
lem configure

# select big bang packages to clone
lem repo clone

# check vpc is good
lem check vpc

# check/get AWS username
lem check username

# check all needed dev cli tools are installed
lem check tools

# create a new EC2 spot instance on BB GovCloud
lem ec2 start

# delete your EC2 instance
lem ec2 terminate
```

## Developing

This project requires the `poetry` python package to be installed globally.  For developing on Windows, I recommend using the [`Open Folder in a Container...`](https://code.visualstudio.com/docs/remote/containers) feature of VS Code and opening in a Python 3.9+ container.

```shell
pip install poetry
```

After installation, you can run the following commands to install the project dependencies:

```shell
poetry config virtualenvs.in-project true
# ^ this is so that vscode can find the venv
poetry install

# run w/
poetry run lem
```
