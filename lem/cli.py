import click

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

if __name__ == "__main__":
    cli()
