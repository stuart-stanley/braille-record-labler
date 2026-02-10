import math
from pathlib import Path
from solid2.extensions.bosl2 import BOTTOM, FRONT, LEFT, TOP, RIGHT, BACK
from solid2.extensions import bosl2
from . import configish
from . import braille_scad


class RecordClipController:
    def __init__(self, lp_config, configish_file=None):
        self.__cfgish = configish.load_config(configish_file)
        self.__lp_cfg = lp_config

        # Step 1: make and see how big the braille wants to be...
        lines = [lp_config.short_artist, lp_config.short_lp_name]
        circle_fn = self.__cfgish.tag_geometry.line_segments_per_circle
        braille_panel = braille_scad.MultilineBrailleScad(
            lines, lp_config.braille_back_to_front, circle_fn=circle_fn)
        self.__braille_panel = braille_panel

        # ok! now lets make the parts of the "h"ish shape that will the clip.
        # the long part of the "h" being the side with the braille. The short
        # side is the "back".
        #
        # build up the size of the top part of the "h":
        tab_depth__mm = braille_panel.get_depth_of_n_chars__mm(
            lp_config.forward_tag_depth_characters)
        if lp_config.min_forward_tag_depth__mm > tab_depth__mm:
            tab_depth__mm = lp_config.min_forward_tag_depth__mm

        # start out presuming the text is long enough to cover all minimums.
        whole_depth__mm = braille_panel.depth__mm
        min_depth__mm = lp_config.front_side_min_depth__mm + lp_config.min_forward_tag_depth__mm
        if min_depth__mm > whole_depth__mm:
            whole_depth__mm = min_depth__mm
        whole_depth__mm = math.ceil(whole_depth__mm)
        # NOTE: config enforces the front-side min being >= the back side min,
        # so we can use whole_depth__mm here.
        self.total_depth__mm = whole_depth__mm
        self.total_height__mm = braille_panel.height__mm
        wt__mm = self.__cfgish.tag_geometry.wing_thickness__mm
        long_size = [wt__mm, self.total_depth__mm, self.total_height__mm]
        back_size = [wt__mm, lp_config.back_side_depth__mm, self.total_height__mm]
        # we want the span piece to be rounded at top/bottom (thin edge) as
        # well as having the long and back pieces rounded on all edges. This
        # means by default, there would be little bit of rounding at the join
        # between the long/back pieces and the span. SO, we make it go 1/2 way
        # INTO the long and back pieces. We do that by adding 1/2 of the thicknesses
        # of back & long and then shift the span left by 1/2 of the back (which is
        # the one that touches at x=0
        # TODO: this still isn't perfect. I probably need to figure out regions
        #   and advanced rounding.
        span_width__mm = lp_config.thickness__mm
        extra_span_back__mm = back_size[0] / 2
        extra_span_long__mm = long_size[0] / 2
        span_x_shift__mm = extra_span_back__mm
        adj_span_width = span_width__mm + extra_span_back__mm + extra_span_long__mm
        span_size = [adj_span_width, self.__cfgish.tag_geometry.span_thickness__mm, self.total_height__mm]
        long_shift__mm = back_size[0] + span_size[0] - span_x_shift__mm
        long_h = bosl2.cuboid(
            long_size,
            rounding=long_size[0]/2,   # max rounding
            _fn=circle_fn,
            anchor=FRONT+BOTTOM+LEFT
        ).right(long_shift__mm)

        span_h = bosl2.cuboid(
            span_size,
            rounding=span_size[1]/2,   # max rounding
            _fn=circle_fn,
            anchor=FRONT+BOTTOM+LEFT,
            edges=[FRONT+TOP, FRONT+BOTTOM],
        ).right(back_size[0] - span_x_shift__mm).forward(tab_depth__mm)

        back_plate = bosl2.cuboid(
            back_size,
            rounding=back_size[0]/2,    # max rounding
            _fn=circle_fn,
            anchor=FRONT+BOTTOM+LEFT,
        ).forward(tab_depth__mm)

        # now the bump near the remote end of the back plate.
        #  We make a cylinder and then remove a cube to make a semi-cylinder.
        br = lp_config.pressure_bump__mm
        bump_cyl = bosl2.cyl(
            r=br,
            length=self.total_height__mm,
            rounding=br/2,    # max rounding
            _fn=circle_fn,
            anchor=BACK+BOTTOM
        )
        bump_rm = bosl2.cuboid(
            [br, br*2, self.total_height__mm],
            anchor=RIGHT+BACK+BOTTOM
        )
        bump_semi = bump_cyl - bump_rm
        # y-off is tab size plus back length minus the rounding on the back plate
        y_off = lp_config.back_side_depth__mm + tab_depth__mm - back_size[0] / 2
        bump_pos = bump_semi.translate([wt__mm, y_off, 0])

        braille_shift__mm = long_shift__mm + long_size[0]
        h_shape = long_h + span_h + back_plate + bump_pos
        h_and_braille = h_shape + braille_panel.scad_model.right(braille_shift__mm)
        if lp_config.forward_tag_do_visual_characters:
            txt_shape = self.__generate_visual_text(lp_config)
            # the txt_shape is centered both along the y and x axis, so we will
            # need to move it into the center of the tab area. In addition,
            # the "back" of the text is up against the y/z plane, so we will
            # need to push it along the x axis to touch the back of the tab.

            txt_positioned = txt_shape.translate(
                [long_shift__mm, tab_depth__mm / 2, self.total_height__mm / 2]
            )
            final = h_and_braille + txt_positioned
        else:
            final = h_and_braille
        # rotate 45 degrees to make use of build plate space by default
        self.__openscad_model = final.rotate([0, 0, 45])
        self.__validated = False
        self.__is_valid = False

    def __assert_validity(self):
        assert self.__validated, \
           'coding error: attempting to use model before validated.'
        assert self.__is_valid, \
            'coding error: attempt to use model that failed to validate.'

    def do_scad(self, filepath=None):
        self.__assert_validity()
        if filepath is None:
            fname = '{}.scad'.format(self.__lp_cfg.lp_key)
            filepath = Path('.').resolve() / fname
        self.__openscad_model.save_as_scad(filepath)

    def do_stl(self, filepath=None):
        self.__assert_validity()
        print("Note: this can take up to a few minutes")
        if filepath is None:
            fname = '{}.stl'.format(self.__lp_cfg.lp_key)
            filepath = Path('.').resolve() / fname
        self.__openscad_model.save_as_stl(filepath)
        self.__lp_cfg.set_out_to_print(True)

    @property
    def braille_artist(self):
        return self.__braille_panel.braille_lines[0]

    @property
    def braille_lp_name(self):
        return self.__braille_panel.braille_lines[1]

    def __generate_visual_text(self, lp_config):
        visual_text_height__mm = self.__cfgish.tag_geometry.visual_text_height__mm
        txt_chars = lp_config.full_artist[:lp_config.forward_tag_depth_characters]
        assert len(txt_chars) > 0
        txt_shape = bosl2.text3d(
            txt_chars,
            visual_text_height__mm,
            center=True,
            anchor=TOP,
        )
        rotated_txt = txt_shape.rotate([90, 0, -90])
        # the text is now "sitting" centered along both x and y with
        # its "front" touching the y/z plane. Let's shove it so the back
        # it touching instead and return it.
        return rotated_txt.translate([-1 * visual_text_height__mm, 0, 0])

    def validate(self, using_printer_name):
        printer = self.__cfgish.printer_geometry[using_printer_name]
        errors = []
        warnings = []
        # figure out the diagonal
        diag__mm = math.sqrt(printer.bed_deep__mm**2 + printer.bed_wide__mm**2)
        diag__mm -= 10   # remove enough to handle width. TODO: can calculate

        if self.total_depth__mm > diag__mm:
            e = "print depth (along record) {}mm > printer {}'s diag {}mm".format(
                self.total_depth__mm, using_printer_name, diag__mm)
            errors.append(e)
        if self.total_depth__mm > printer.bed_deep__mm:
            w = "print depth (along record) {}mm > printer {}'s straight depth {}mm".format(
                self.total_depth__mm, using_printer_name, printer.bed_deep__mm)
            warnings.append(w)
        if self.total_depth__mm > self.__cfgish.label_config.max_depth__mm:
            e = "print depth (along record) {}mm > label_config max_depth__mm{}".format(
                self.total_depth__mm, self.__cfgish.label_config.max_depth__mm)
            errors.append(e)

        if self.total_height__mm > printer.bed_height__mm:
            e = "print height {}mm > printer {}'s height {}mm".format(
                self.total_height__mm, using_printer_name, printer.bed_height__mm)
            errors.append(e)
        # TODO: all clip width check
        # TODO: font text fitting on tab
        self.__validated = True
        if len(errors) == 0:
            self.__is_valid = True
        return errors, warnings
