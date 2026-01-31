import yamale
from pathlib import Path
import munch


def load_config(config_ish_file=None):
    installdir = Path(__file__).resolve().parent

    schema = yamale.make_schema(installdir / 'configish.yamale')

    if config_ish_file is None:
        config_ish_file = Path(__file__).resolve().parent / "default_configish.yml"

    data = yamale.make_data(config_ish_file)
    yamale.validate(schema, data)

    # yamale can handle multiple sub-schemas etc. We only use 1, so
    # pull that out for direct use
    data = data[0][0]
    # extra checks/fill-inst
    if 'do_visual_text_line' not in data['label_config']:
        data['label_config']['do_visual_text_line'] = -1

    # TODO: use yamale validators instead of asserts
    active_name = data['active_printer']
    assert active_name in data['printer_geometry'], \
        'printer {} not in defined list of {}.'.format(
            active_name, data['printer_geometry'].keys()
        )
    data['active_printer'] = data['printer_geometry'][active_name]
    assert data['label_config']['do_visual_text_line'] < len(data['active_printer'])

    as_attr = munch.Munch(data)
    return as_attr
