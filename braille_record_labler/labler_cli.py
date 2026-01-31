import click
from . import configish


@click.group('braille-record-labler')
@click.pass_context
@click.option('--lp-database-file', default='lp_database.yml')
@click.option('--config-ish-file')
def braille_record_labler(ctx, lp_database_file, config_ish_file):
    print("rl", lp_database_file, config_ish_file, ctx)
    cfgish = configish.load_config(config_ish_file)
    ctx.obj = {
        'lp_database': lp_database_file,
        'config_ish': cfgish
    }


@braille_record_labler.command()
@click.pass_context
def list(ctx):
    print("listing records", ctx.obj)


@braille_record_labler.group()
def lp():
    print("in lp subcommands")


@lp.command()
@click.argument('lp_index_name')
@click.pass_context
def validate(ctx, lp_index_name):
    print("validate xyz", lp_index_name, ctx.obj)


@lp.command()
@click.argument('lp_index_name')
@click.pass_context
def generate(ctx, lp_index_name):
    print("generate", lp_index_name, ctx.obj)
