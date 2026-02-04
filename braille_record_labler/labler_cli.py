import sys
import click
from pathlib import Path
from rich import print
from rich.console import Console
import rich
from . import configish
from . import label_tracker
from . import clip_maker

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
        'config_ish': cfgish,
        'configish_file': config_ish_file,
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
    print("  back_side_depth__mm:              {}".format(dfl.back_side_depth__mm))
    print("overall style version (OSV): {}".format(cfi.overall_style_version))
    t = rich.table.Table(title="defined records")
    t.add_column("lp-key")
    t.add_column("artist")
    t.add_column("lp_name")
    t.add_column("OSV")
    t.add_column('cksum')
    t.add_column('last-printed')
    t.add_column('back-depth')
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
            _format_diffed(dfl, lp, 'back_side_depth__mm'),
            _format_diffed(dfl, lp, 'min_forward_tag_depth__mm'),
            _format_diffed(dfl, lp, 'forward_tag_depth_characters'),
            _format_diffed(dfl, lp, 'forward_tag_do_visual_characters'),
            str(needs_to_print),
            why_print
        )
    console.print(t)


def _common_print_and_validate(ctx, lp_index_name):
    lpd = ctx.obj['lp_database']
    if lp_index_name not in lpd.lp_keys():
        raise click.BadParameter("record '{}' not in list of '{}'".format(
            lp_index_name, lpd.lp_keys()))
        print("z"*100)
    lp = lpd.lp_by_key(lp_index_name)
    clip_ctl = clip_maker.RecordClipController(lp, ctx.obj['configish_file'])
    errors, warnings = clip_ctl.validate(lpd.active_printer_name)
    print("Info for print of {} on {}:".format(lp_index_name, lpd.active_printer_name))
    print("  total depth along record:     {}mm".format(clip_ctl.total_depth__mm))
    print("  total height:                 {}mm".format(clip_ctl.total_height__mm))
    print("  todo: more info")

    for warning in warnings:
        print("[yellow]{}[/yellow]".format(warning))
    for error in errors:
        print("[red]{}[/red]".format(error))
    return len(errors) == 0, clip_ctl


@braille_record_labler.command()
@click.argument('lp_index_name')
@click.pass_context
def validate(ctx, lp_index_name):
    valid, clip_ctl = _common_print_and_validate(ctx, lp_index_name)
    if not valid:
        sys.exit(10)


def _setup_output(output_path, file_name, lp_index_name, default_suffix):
    output_path = Path(output_path)
    output_path.mkdir(exist_ok=True, parents=True)
    if not output_path.is_dir():
        print("output_path is not a directory")
        sys.exit(11)
    if file_name is None:
        file_name = '{}.{}'.format(lp_index_name, default_suffix)

    full_path = output_path / file_name
    return output_path, full_path


@braille_record_labler.command()
@click.argument('lp_index_name')
@click.option('--output-path', '-p', default='./generated', type=click.types.Path())
@click.option('--file-name', '-f', type=click.types.File())
@click.pass_context
def generate(ctx, lp_index_name, output_path, file_name):
    op, ofp = _setup_output(output_path, file_name, lp_index_name, 'scad')
    valid, clip_ctl = _common_print_and_validate(ctx, lp_index_name)
    if not valid:
        sys.exit(10)
    clip_ctl.do_scad(ofp)
    print("{} generated".format(ofp))


@braille_record_labler.command()
@click.argument('lp_index_name')
@click.option('--output-path', '-p', default='./generated', type=click.types.Path())
@click.option('--file-name', '-f', type=click.types.File())
@click.pass_context
def print_cmd(ctx, lp_index_name, output_path, file_name, name='print'):
    op, ofp = _setup_output(output_path, file_name, lp_index_name, 'stl')
    valid, clip_ctl = _common_print_and_validate(ctx, lp_index_name)
    if not valid:
        sys.exit(10)
    clip_ctl.do_stl(ofp)
    print_name = ctx.parent.info_name
    print("{} generated".format(ofp))
    print("")
    print("Load the stl file into your print software and print.")
    print("When complete, run '{} complete {}'".format(print_name, lp_index_name))


@braille_record_labler.command()
@click.argument('lp_index_name')
@click.pass_context
def complete(ctx, lp_index_name):
    valid, clip_ctl = _common_print_and_validate(ctx, lp_index_name)
    if not valid:
        print("Can not complete print while config is invalid.")
        sys.exit(10)
    lpd = ctx.obj['lp_database']
    lpd.complete_print(lp_index_name)
