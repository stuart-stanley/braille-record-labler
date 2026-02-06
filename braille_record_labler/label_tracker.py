import yamale
import hashlib
import munch
import yaml
from datetime import datetime
from pathlib import Path


class _Record:
    def __init__(self, def_label_format, lp_key, lp_data, state_data, cfgish):
        self.lp_key = lp_key
        self.full_artist = lp_data['full_artist']
        if 'short_artist' not in lp_data:
            self.short_artist = self.full_artist
        else:
            self.short_artist = lp_data['short_artist']
        self.full_lp_name = lp_data['full_lp_name']
        if 'short_lp_name' not in lp_data:
            self.short_lp_name = self.full_lp_name
        else:
            self.short_lp_name = lp_data['short_lp_name']

        if 'override_format' in lp_data:
            self.__init_format(lp_data['override_format'])
            self.format_overridden = True
        else:
            self.__init_format(def_label_format)
            self.format_overridden = False

        if 'override_pressure_bump__mm' in lp_data:
            self.pressure_bump__mm = lp_data['overide_pressure_bump__mm']
        else:
            self.pressure_bump__mm = self.default_pressure_bump__mm
        self.thickness__mm = lp_data['thickness__mm']
        cksum = hashlib.sha256()
        cksum.update(self.lp_key.encode('utf-8'))
        cksum.update(self.full_artist.encode('utf-8'))
        cksum.update(self.short_artist.encode('utf-8'))
        cksum.update(self.full_lp_name.encode('utf-8'))
        cksum.update(self.short_lp_name.encode('utf-8'))
        cksum.update(str(self.thickness__mm).encode('utf-8'))
        cksum.update(str(self.pressure_bump__mm).encode('utf-8'))
        cksum.update(str(self.min_forward_tag_depth__mm).encode('utf-8'))
        cksum.update(str(self.forward_tag_depth_characters).encode('utf-8'))
        cksum.update(str(self.forward_tag_do_visual_characters).encode('utf-8'))
        cksum.update(str(self.back_side_depth__mm).encode('utf-8'))
        cksum.update(str(self.front_side_min_depth__mm).encode('utf-8'))
        cksum.update(str(self.default_pressure_bump__mm).encode('utf-8'))
        cksum.update(str(self.braille_back_to_front).encode('utf-8'))
        self.calculated_checksum = cksum.hexdigest()
        self.__state = state_data

        self.__global_overall_style_version = cfgish.overall_style_version

    @property
    def printed_checksum(self):
        return self.__state.printed_checksum

    @property
    def last_printed(self):
        return self.__state.last_printed

    @property
    def out_for_printing(self):
        return self.__state.out_for_printing

    def set_out_to_print(self, is_it):
        self.__state.out_for_printing = is_it

    def __init_format(self, use_format):
        """
        Format can be defined at the database level or overridden on
        a single record. It's the same data structure, so this routine
        is used to unpack and store it.
        """
        self.min_forward_tag_depth__mm = use_format['min_forward_tag_depth__mm']
        self.forward_tag_depth_characters = use_format['forward_tag_depth_characters']
        self.forward_tag_do_visual_characters = use_format['forward_tag_do_visual_characters']
        self.back_side_depth__mm = use_format['back_side_depth__mm']
        self.front_side_min_depth__mm = use_format['front_side_min_depth__mm']
        self.default_pressure_bump__mm = use_format['default_pressure_bump__mm']
        self.braille_back_to_front = use_format['braille_back_to_front']
        assert self.back_side_depth__mm <= self.front_side_min_depth__mm, \
            'min front {} must be >= min back {}'.format(
                self.front_side_min_depth__mm, self.back_side_depth__mm)

    def needs_to_print(self):
        if self.__global_overall_style_version != self.__state.overall_style_version:
            return True, "big-style-change {} != {}".format(
                self.__global_overall_style_version, self.__state.overall_style_version)

        if self.__state.printed_checksum != self.calculated_checksum:
            if self.__state.printed_checksum is None:
                return True, "checksum changed from None to value"
            return True, "checksum changed value"
        if self.__state.last_printed is None:
            return True, "never-printed"

        return False, None

    def complete_print(self):
        self.__state.last_printed = datetime.now()
        self.__state.printed_checksum = self.calculated_checksum

    def state_for_save(self):
        return dict(self.__state)


class RecordDataAccess:
    def __init__(self, cfgish, db_cfg_file, db_state_dir_path=None):
        installdir = Path(__file__).resolve().parent

        self.__db_schema = yamale.make_schema(installdir / 'lp_db.yamale')
        self.__db_state_schema = yamale.make_schema(installdir / 'lp_state.yamale')

        # TODO: smart home for this file!
        if db_state_dir_path is None:
            db_state_dir_path = Path(".").resolve()

        lp_path = Path(db_cfg_file).resolve()
        main_data = yamale.make_data(lp_path)

        # first, validate that ^^^
        yamale.validate(self.__db_schema, main_data)
        # yamale CAN handle multiple documents. We only do one, so:
        main_data = main_data[0][0]

        state_name = "{}_state.yml".format(lp_path.stem)
        state_path = Path(state_name)
        self.__state_path = state_path
        if not state_path.exists():
            # create a blank to use
            state_path.write_text("record_data:\n")

        # Now load the current state data
        state_data = yamale.make_data(state_path)
        yamale.validate(self.__db_state_schema, state_data)
        # yamale CAN handle multiple documents. We only do one, so:
        state_data = state_data[0][0]['record_data']
        # handle fresh file
        if state_data is None:
            state_data = {}

        self.active_printer_name = main_data['active_printer']
        # Scan the list of records and create a Record() for each. We
        # fill in a blank state if one doesn't already exist.
        self.__lp_map = {}
        label_format = munch.munchify(main_data['label_format'])
        self.default_label_format = label_format
        for lp_key, lp_data in main_data['record_data'].items():
            if lp_key in state_data:
                a_state = state_data[lp_key]
            else:
                a_state = {
                    'printed_checksum': None,
                    'last_printed': None,
                    'overall_style_version': cfgish.overall_style_version,
                    'out_for_printing': False
                }

            a_state = munch.munchify(a_state)
            self.__lp_map[lp_key] = _Record(label_format, lp_key, lp_data, a_state, cfgish)

    def lp_keys(self):
        return list(self.__lp_map.keys())

    def lp_by_key(self, lp_key):
        return self.__lp_map[lp_key]

    def lps(self, sort=True):
        slpk = list(self.__lp_map.keys())
        slpk = sorted(slpk)
        for lp_key in slpk:
            yield lp_key, self.__lp_map[lp_key]

    def __write_state(self):
        write_data = {'record_data': {}}
        for lp_key, lp in self.lps():
            write_data['record_data'][lp_key] = lp.state_for_save()

        with self.__state_path.open('w') as state_file:
            yaml.dump(write_data, state_file)

    def set_out_to_print(self, lp_key, is_it):
        lp = self.lp_by_key(lp_key)
        lp.set_out_to_print(is_it)
        self.__write_state()

    def complete_print(self, lp_key):
        lp = self.lp_by_key(lp_key)
        lp.complete_print()
        lp.set_out_to_print(False)
        self.__write_state()
