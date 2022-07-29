import click

from .configure import configure

from .check import check

from .console import Console

c = Console()


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog="Built and maintained by @razzle",
)
def cli():
    pass


cli.add_command(check)
cli.add_command(configure)

if __name__ == "__main__":
    cli()
