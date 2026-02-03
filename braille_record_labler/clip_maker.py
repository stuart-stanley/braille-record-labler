from solid2.extensions.bosl2 import BOTTOM, FRONT, LEFT, TOP
from solid2.extensions import bosl2
from . import configish
from . import braille_scad


WING_THICKNESS__MM = 3    # the thickness of each of the clip's "wings"
SPAN_THICKNESS__MM = 4    # the short bit on the front of the clip


class RecordClipController:
    def __init__(self, lp_config, configish_file=None):
        self.__cfgish = configish.load_config(configish_file)
        self.__lp_cfg = lp_config

        # Step 1: make and see how big the braille wants to be...
        lines = [lp_config.short_artist, lp_config.short_lp_name]
        braille_panel = braille_scad.MultilineBrailleScad(lines)
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

        # NOTE: config enforces the front-side min being >= the back side min,
        # so we can use whole_depth__mm here.
        self.total_depth__mm = whole_depth__mm
        self.total_height__mm = braille_panel.height__mm
        long_size = [WING_THICKNESS__MM, self.total_depth__mm, self.total_height__mm]
        back_size = [WING_THICKNESS__MM, lp_config.back_side_depth__mm, self.total_height__mm]
        # we want the span piece to be rounded at top/bottom (thin edge) as
        # well as having the long and back pieces rounded on all edges. This
        # means by default, there would be little bit of rounding at the join
        # between the long/back pieces and the span. SO, we make it go 1/2 way
        # INTO the long and back pieces. We do that by adding 1/2 of the thicknesses
        # of back & long and then shift the span left by 1/2 of the back (which is
        # the one that touches at x=0
        # TODO: this still isn't perfect. I probably need to figure out regions
        #   and advanced rounding.
        TODO_SPAN_WIDTH__MM = 4
        extra_span_back__mm = back_size[0] / 2
        extra_span_long__mm = long_size[0] / 2
        span_x_shift__mm = extra_span_back__mm
        adj_span_width = TODO_SPAN_WIDTH__MM + extra_span_back__mm + extra_span_long__mm
        span_size = [adj_span_width, SPAN_THICKNESS__MM, self.total_height__mm]
        long_shift__mm = back_size[0] + span_size[0] - span_x_shift__mm
        long_h = bosl2.cuboid(
            long_size,
            rounding=long_size[0] / 2,   # max rounding
            anchor=FRONT+BOTTOM+LEFT
        ).right(long_shift__mm)

        span_h = bosl2.cuboid(
            span_size,
            rounding=span_size[1] / 2,   # max rounding
            anchor=FRONT+BOTTOM+LEFT,
            edges=[FRONT+TOP, FRONT+BOTTOM],
        ).right(back_size[0] - span_x_shift__mm).forward(tab_depth__mm)

        back_h = bosl2.cuboid(
            back_size,
            rounding=back_size[0] / 2,   # max rounding
            anchor=FRONT+BOTTOM+LEFT
        ).forward(tab_depth__mm)
        braille_shift__mm = long_shift__mm + long_size[0]
        h_shape = long_h + span_h + back_h
        final = h_shape + braille_panel.scad_model.right(braille_shift__mm)
        print("HEY!", final.save_as_scad('foo.scad'))

    def validate(self, using_printer_name):
        printer = self.__cfgish.printer_geometry[using_printer_name]
        errors = []
        warnings = []
        if self.total_depth__mm > printer.bed_deep__mm:
            e = "print depth (along record) {}mm > printer {}'s depth {}mm".format(
                self.total_depth__mm, using_printer_name, printer.bed_deep__mm)
            errors.append(e)
        if self.total_depth__mm > self.__cfgish.label_config.max_depth__mm:
            e = "print depth (along record) {}mm > label_config max_depth__mm{}".format(
                self.total_depth__mm, self.__cfgish.label_config.max_depth__mm)
            errors.append(e)

        if self.total_height__mm > printer.bed_height__mm:
            e = "print height {}mm > printer {}'s height {}mm".format(
                self.total_height__mm, using_printer_name, printer.bed_height__mm)
            errors.append(e)
        # TODO: all clip width check
        return errors, warnings
