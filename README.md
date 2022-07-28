# lem

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
# check vpc is good
lem check vpc

# check all needed dev cli tools are installed
lem check tools
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