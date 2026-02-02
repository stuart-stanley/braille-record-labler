import click
from rich import print
from rich.console import Console
import rich
from . import configish
from . import label_tracker

console = Console()


@click.group('braille-record-labler')
@click.pass_context
@click.option('--lp-database-file', default='lp_database.yml')
@click.option('--config-ish-file')
def braille_record_labler(ctx, lp_database_file, config_ish_file):
    cfgish = configish.load_config(config_ish_file)
    label_db = label_tracker.RecordDataAccess(cfgish, lp_database_file)
    ctx.obj = {
        'lp_database': label_db,
        'config_ish': cfgish
    }


def _short_long_format(long_str, short_str):
    if long_str == short_str:
        return long_str
    if long_str.startswith(short_str):
        long_extra = long_str[len(short_str):]
        rs = "[underline]{}[/underline]{}".format(short_str, long_extra)
        return rs
    return "{}\n{}".format(long_str, short_str)


def _format_diffed(def_fmat, lp_record, setting_name):
    setting = getattr(lp_record, setting_name)
    if def_fmat[setting_name] == setting:
        return str(setting)
    return "[bold]{}[/bold]".format(setting)


@braille_record_labler.command()
@click.pass_context
def list(ctx):
    lpd = ctx.obj['lp_database']
    dfl = lpd.default_label_format
    cfi = ctx.obj['config_ish']
    print("Default label format:")
    print("  min_forward_tag_depth__mm:        {}".format(dfl.min_forward_tag_depth__mm))
    print("  forward_tag_depth_characters:     {}".format(
        dfl.forward_tag_depth_characters))
    print("  forward_tag_do_visual_characters: {}".format(
        dfl.forward_tag_do_visual_characters))
    # TODO: add bed/printer info. maybe new command
    print("  do_visual_text_line:              {}".format(dfl.do_visual_text_line))
    print("overall style version (OSV): {}".format(cfi.overall_style_version))
    t = rich.table.Table(title="defined records")
    t.add_column("lp-key")
    t.add_column("artist")
    t.add_column("lp_name")
    t.add_column("OSV")
    t.add_column('cksum')
    t.add_column('last-printed')
    t.add_column('do-visual')
    t.add_column('min-tag-depth-mm')
    t.add_column('tag-chars')
    t.add_column('visual-tag-chars')
    t.add_column('needs-to-print')
    t.add_column('why-to-print')

    for lp_key, lp in lpd.lps():
        artist = _short_long_format(lp.full_artist, lp.short_artist)
        lp_name = _short_long_format(lp.full_lp_name, lp.short_lp_name)
        if lp.last_printed is None:
            last_printed = 'never'
        else:
            last_printed = str(lp.last_printed)
        needs_to_print, why_print = lp.needs_to_print()
        t.add_row(
            lp.lp_key,
            artist,
            lp_name,
            str(lp.format_overridden),
            lp.printed_checksum,
            last_printed,
            _format_diffed(dfl, lp, 'do_visual_text_line'),
            _format_diffed(dfl, lp, 'min_forward_tag_depth__mm'),
            _format_diffed(dfl, lp, 'forward_tag_depth_characters'),
            _format_diffed(dfl, lp, 'forward_tag_do_visual_characters'),
            str(needs_to_print),
            why_print
        )
    console.print(t)


@braille_record_labler.group()
def lp():
    pass


@lp.command()
@click.argument('lp_index_name')
@click.pass_context
def validate(ctx, lp_index_name):
    print("validate", lp_index_name)


@lp.command()
@click.argument('lp_index_name')
@click.pass_context
def generate(ctx, lp_index_name):
    print("generate", lp_index_name, ctx.obj)
