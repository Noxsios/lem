import click

from .check import check
from .configure import configure
from .repos import repo


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog="Built and maintained by @razzle",
)
def cli():
    pass


cli.add_command(check)
cli.add_command(configure)
cli.add_command(repo)

if __name__ == "__main__":
    cli()
