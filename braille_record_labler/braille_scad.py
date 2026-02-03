import touchmap
import solid2
import math

CIRCLE_FN = 16    # segments to make a circle

# https://brailleaustralia.org/about-braille/physical-specifications-for-braille/
DOT_ROD_HEIGHT__MM = 0.6   # spec: this plus sphere-height is 0.6 to 0.9mm
DOT_DIAMETER__MM = 1.5     # spec: 1.5 to 1.6mm
DOT_SPHERE_RADIUS__MM = 0.76  # spec: 0.76 to 0.81mm


def _DOT_SPHERE_HEIGHT__MM():
    """
    pulled out as function because I want to show the formula being filled in.

    r = sphere-radius
    d = dot-diameter
    h = the "exposed" part of the sphere.

    r^2 = (.5d)^2 + (r-h)^2

    The sphere-radius will actualy be bigger than the dot's "rod" shape's diameter/2, so
    we will end up wanting to "chop off" the rest of the sphere after it comes in contact
    with the top of the rod. "h" will give us the size of that top of the sphere from
    its hightest point to the intersection.

    We could re-solve the equation for h=, but since we know all the variables we can cheat :). We can re-write as:
    r2 = d2 + (r-h)^2
    r2 - d2 = (r-h)^2
    sqrt(r2 - d2) = r - h
    sqrt(r2 - d2) - r = -h
    h = -sqrt(r2 - d2) + r

    where:
      r2 = r^2
      d2 = (.5d)^2
    """
    r2 = DOT_SPHERE_RADIUS__MM ** 2
    d2 = (0.5 * DOT_DIAMETER__MM) ** 2
    h = -math.sqrt(r2 - d2) + DOT_SPHERE_RADIUS__MM
    return h


DOT_SPHERE_HEIGHT__MM = _DOT_SPHERE_HEIGHT__MM()
DOT_TOTAL_HEIGHT__MM = DOT_ROD_HEIGHT__MM + DOT_SPHERE_HEIGHT__MM

DOT_SPACING__MM = 2.234
CELL_SPACING__MM = 6.2
MARGIN__MM = 3.5
LINE_TO_LINE__MM = 10


class _CellInfo:
    def __init__(self, uni_char, bin_map, circle_fn=CIRCLE_FN):
        assert len(uni_char) == 1
        assert len(bin_map) == 6, \
            '{} != 6'.format(len(bin_map))
        self.__unicode_char = uni_char
        self.__bin_map = bin_map
        self.__circle_fn = circle_fn

    @property
    def unicode(self):
        return self.__unicode_char

    def dot_value(self, column, row):
        assert column >= 0 and column < 2, \
          "column {} not 0 or 1".format(column)
        assert row >= 0 and row < 3, \
            "row {} not in 0..2".format(row)
        inx = row * 2 + column
        return self.__bin_map[inx] == '1'

    def dump_dot_values(self):
        for row in range(0, 3):
            tr = []
            for col in range(0, 2):
                tr.append(self.dot_value(col, row))
            print("{}: {:6} {:6}".format(row, tr[0], tr[1]))

    def __make_dot(self, row, col):
        chop_height = DOT_SPHERE_RADIUS__MM * 2 - DOT_SPHERE_HEIGHT__MM
        top_sphere = solid2.sphere(r=DOT_SPHERE_RADIUS__MM, _fn=CIRCLE_FN)

        chop_cyl = solid2.translate(0, 0, -chop_height)(
            solid2.cylinder(h=chop_height, r=DOT_SPHERE_RADIUS__MM, _fn=CIRCLE_FN)
        )
        chop_top = top_sphere - chop_cyl

        rnd_rod = solid2.union()(
            solid2.cylinder(DOT_ROD_HEIGHT__MM, d=DOT_DIAMETER__MM, _fn=CIRCLE_FN),
            solid2.translate(0, 0, DOT_ROD_HEIGHT__MM)(chop_top)
        ).rotate([0, 90, 0])
        placed = rnd_rod.translate(
            [0, col * DOT_SPACING__MM, LINE_TO_LINE__MM - (row * DOT_SPACING__MM)]
        )
        return placed

    def to_scad(self):
        joined = solid2.union()
        for row in range(0, 3):
            for col in range(0, 2):
                if self.dot_value(col, row):
                    joined += self.__make_dot(row, col)

        # now shift over to 0,0 effective
        zeroed = solid2.translate([0, DOT_DIAMETER__MM / 2, DOT_DIAMETER__MM / 2])(joined)
        return zeroed


class MultilineBrailleScad:
    def __init__(self, str_list, circle_fn=CIRCLE_FN):
        self.__circle_fn = circle_fn
        current_height__mm = len(str_list) * LINE_TO_LINE__MM
        full_scad = solid2.union()
        max_depth__mm = -1
        longest_line = None
        longest_line_index = -1
        inx = 0
        for src_string in str_list:
            line_scad, line_size_info = self.__str_to_braille_scad(src_string)
            depth__mm = line_size_info[0]
            if depth__mm > max_depth__mm:
                max_depth__mm = depth__mm
                longest_line = src_string
                longest_line_index = inx
            # "scroll" the line up. The line was built low to high, so
            # adjust our offset before shifting.
            current_height__mm -= LINE_TO_LINE__MM
            full_scad += solid2.up(current_height__mm)(line_scad)
            inx += 1

        self.scad_model = full_scad
        self.depth__mm = max_depth__mm
        self.height__mm = len(str_list) * LINE_TO_LINE__MM + MARGIN__MM * 2
        self.longest_line = longest_line
        self.longest_line_index = longest_line_index

    def get_depth_of_n_chars__mm(self, char_count):
        """
        This is the space taken up my this many chars and the (prefix) margin__mm.
        """
        if char_count > 0:
            return (char_count * CELL_SPACING__MM) + MARGIN__MM
        else:
            return 0

    def __str_to_braille_scad(self, src_string):
        # Step 1: use touchmap to make both the unicode and raised-map forms
        #  Note: because this is grade-2, we lose the 1:1 mapping from str_string[x] to the output.
        uni_br = touchmap.text_to_braille(src_string, grade=2)
        cell_bin_str = touchmap.text_to_braille(src_string, grade=2, binary=True)
        assert (len(uni_br) == len(cell_bin_str) / 6)
        colors = ["red", "blue", "green"]

        # Step 2: walk through the outputs and make a cell for each one.
        out_scad = solid2.union()
        for inx in range(0, len(uni_br)):
            bin_clip = cell_bin_str[inx*6:]
            cell = _CellInfo(uni_br[inx], bin_clip[:6], self.__circle_fn)
            # cell.dump_dot_values()
            out_scad += solid2.translate([0, inx * CELL_SPACING__MM + MARGIN__MM, 0])(
                solid2.color(colors[inx % 3])(
                    cell.to_scad()
                )
            )
        width__mm = len(uni_br) * CELL_SPACING__MM
        width__mm += MARGIN__MM * 2
        size_info = [width__mm, LINE_TO_LINE__MM, DOT_TOTAL_HEIGHT__MM]
        return out_scad, size_info
