# -*- coding:utf-8 -*-

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# ----------------------------------------------------------
# Blender Parametric object skeleton
# Author: Stephen Leger (s-leger)
# ----------------------------------------------------------

bl_info = {
    'name': 'Floor',
    'description': 'Floor parametric object',
    'author': 's-leger, Jacob Morris',
    'license': 'GPL',
    'version': (1, 0, 0),
    'blender': (2, 7, 8),
    'location': 'View3D > Tools > Sample',
    'warning': '',
    'wiki_url': 'https://github.com/BlendingJake/BlenderFlooringParametricObject/wiki',
    'tracker_url': 'https://github.com/BlendingJake/BlenderFlooringParametricObject/issues',
    'link': 'https://github.com/BlendingJake/BlenderFlooringParametricObject',
    'support': 'COMMUNITY',
    'category': '3D View'
    }


import bpy
from bpy.types import Operator, PropertyGroup, Mesh, Panel
from bpy.props import FloatProperty, CollectionProperty, BoolProperty, IntProperty, EnumProperty
import mathutils
from random import uniform
from math import radians, cos, sin, atan, isclose
from .bmesh_utils import BmeshEdit
from .simple_manipulator import Manipulable

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

FOOT = 0.3048  # 1 foot in meters
INCH = 0.0254  # 1 inch in meters
EQUAL, NOT_EQUAL, LESS_EQUAL, GREATER_EQUAL, LESS, GREATER = [i for i in range(6)]
SLOP = 0.001  # amount of wiggle room in rough_comp

# ------------------------------------------------------------------
# Define property class to store object parameters and update mesh
# ------------------------------------------------------------------


def update(self, context):
    if self.auto_update:
        self.update(context)


class archipack_floor(Manipulable, PropertyGroup):
    # keep track of data
    vs, fs = [], []  # vertices and faces
    ms = []  # mat ids

    auto_update = BoolProperty(
        name="Auto Update Mesh", default=True, update=update,
        description="Automatically update the mesh whenever a parameter is changed"
    )

    # floor type
    floor_material = EnumProperty(
        name="Floor Material", items=(("wood", "Wood", ""), ("tile", "Tile", "")),
        default="wood", description="Type of material the floor is made of", update=update
    )
    wood_style = EnumProperty(
        name='Wood Style', items=(("regular", "Regular", ""), ("square_parquet", "Square Parquet", ""),
                                  ("herringbone_parquet", "Herringbone Parquet", ""),
                                  ("herringbone", "Herringbone", "")), default="regular",
        description="Style of wood floor", update=update
    )
    tile_style = EnumProperty(
        name='Tile Style', items=(("regular", "Regular", ""), ("hopscotch", "Hopscotch", ""),
                                  ("stepping_stone", "Stepping Stone", ""), ("hexagon", "Hexagon", ""),
                                  ("windmill", "Windmill", "")),
        default="regular", update=update
    )

    # overall length and width
    width = FloatProperty(  # x
        name='Width',
        min=2*FOOT, soft_max=100*FOOT,
        default=20*FOOT, precision=2,
        description='Width', update=update,
        subtype="DISTANCE"
    )
    length = FloatProperty(  # y
        name='Length',
        min=2*FOOT, soft_max=100*FOOT,
        default=8*FOOT, precision=2,
        description='Length', update=update,
        subtype="DISTANCE"
    )

    # generic spacing
    spacing = FloatProperty(
        name='Spacing', unit='LENGTH', min=0, soft_max=1 * INCH,
        default=0.125 * INCH, precision=2, update=update,
        description='The amount of space between boards or tiles in both directions'
    )

    # general thickness
    thickness = FloatProperty(  # z
        name='Thickness',
        min=0.25*INCH, soft_max=2*INCH,
        default=1*INCH, precision=2,
        description='Thickness', update=update,
        subtype="DISTANCE"
    )
    vary_thickness = BoolProperty(
        name='Vary Thickness', update=update, default=False,
        description='Vary board thickness?'
    )
    thickness_variance = FloatProperty(
        name='Thickness Variance', min=0, max=100,
        default=25, update=update, precision=2,
        description='How much board thickness can vary by'
    )

    # board width, variance, and spacing
    board_width = FloatProperty(
        name='Board Width', unit='LENGTH', min=2*INCH,
        soft_max=2*FOOT, default=6*INCH, update=update,
        description='The width of the boards', precision=2
    )
    vary_width = BoolProperty(
        name='Vary Width', default=False,
        description='Vary board width?', update=update
    )
    width_variance = FloatProperty(
        name='Width Variance', subtype='PERCENTAGE',
        min=1, max=100, default=50, description='How much board width can vary by',
        precision=2, update=update
    )
    width_spacing = FloatProperty(
        name='Width Spacing', unit='LENGTH', min=0, soft_max=1*INCH,
        default=0.125*INCH, precision=2, update=update,
        description='The amount of space between boards in the width direction'
    )

    # board length
    board_length = FloatProperty(
        name='Board Length', unit='LENGTH', min=2*FOOT,
        soft_max=100*FOOT, default=8*FOOT, update=update,
        description='The length of the boards', precision=2
    )
    short_board_length = FloatProperty(
        name='Board Length', unit='LENGTH', min=6*INCH,
        soft_max=4*FOOT, default=2*FOOT, update=update,
        description='The length of the boards', precision=2
    )
    vary_length = BoolProperty(
        name='Vary Length', default=False,
        description='Vary board length?', update=update
    )
    length_variance = FloatProperty(
        name='Length Variance', subtype='PERCENTAGE',
        min=1, max=100, default=50, description='How much board length can vary by',
        precision=2, update=update
    )
    max_boards = IntProperty(
        name='Max Boards', min=1, soft_max=10, default=2,
        update=update, description='Max number of boards in one row'
    )
    length_spacing = FloatProperty(
        name='Length Spacing', unit='LENGTH', min=0, soft_max=1*INCH,
        default=0.125*INCH, precision=2, update=update,
        description='The amount of space between boards in the length direction'
    )

    # parquet specific
    boards_in_group = IntProperty(
        name='Boards in Group', min=1, soft_max=10, default=4,
        update=update, description='Number of boards in a group'
    )

    # tile specific
    tile_width = FloatProperty(
        name='Tile Width', min=2*INCH, soft_max=2*FOOT, default=1*FOOT,
        update=update, precision=2, description='Width of the tiles', unit='LENGTH',
    )
    tile_length = FloatProperty(
        name='Tile Length', min=2*INCH, soft_max=2*FOOT, default=8*INCH,
        update=update, precision=2, description='Length of the tiles', unit='LENGTH',
    )
    mortar_depth = FloatProperty(
        name='Mortar Depth', min=0, soft_max=1*INCH, default=0.25*INCH,
        update=update, precision=2, unit='LENGTH',
        description='The depth of the mortar from the surface of the tile'
    )

    # regular tile
    random_offset = BoolProperty(
        name='Random Offset', update=update, default=False,
        description='Random amount of offset for each row of tiles'
    )
    offset = FloatProperty(
        name='Offset', update=update, min=0, max=100, default=0,
        precision=2, description='How much to offset each row of tiles'
    )
    offset_variance = FloatProperty(
        name='Offset Variance', update=update, min=0.001, max=100, default=50,
        precision=2, description='How much to vary the offset each row of tiles'
    )

    @staticmethod
    def append_all(v_list, add):
        for i in add:
            v_list.append(i)

    @staticmethod
    def line_from_points(pt1, pt2) -> callable:
        slope = (pt2[1] - pt1[1]) / (pt2[0] - pt1[0]) if (pt2[0] - pt1[0]) != 0 else 0
        return lambda x: slope * (x - pt1[0]) + pt1[1]

    @staticmethod
    def line_segments_from_points(points):
        """
        Create line segments from the points listed
        :param points: point to form line segments [p1, p2, p3...]
        :return: line segments [[p1, p2], [p2, p3]...[pn, p1]]
        """
        out = [[points[i], points[i + 1]] for i in range(len(points) - 1)]
        out.append([points[len(points) - 1], points[0]])
        return out

    @staticmethod
    def point_of_intersection(p1, p2, p3, p4):
        """
        See if the lines containing [p1, p2] and [p3, p4] intersect. If they don't interest, aka they are parallel,
        then None is returned, else the point of intersection is returned
        :param p1: a point on line 1
        :param p2: another point on line 1
        :param p3: a point on line 2
        :param p4: another point on line 2
        :return: None if the lines are parallel, or (x, y) if they do intersect
        """
        bottom = (p1[0] - p2[0]) * (p3[1] - p4[1]) - (p1[1] - p2[1]) * (p3[0] - p4[0])
        part1, part2 = (p1[0] * p2[1] - p1[1] * p2[0]), (p3[0] * p4[1] - p3[1] * p4[0])
        if bottom != 0:
            x = (part1 * (p3[0] - p4[0]) - (p1[0] - p2[0]) * part2) / bottom
            y = (part1 * (p3[1] - p4[1]) - (p1[1] - p2[1]) * part2) / bottom
            return x, y
        else:
            return None

    @staticmethod
    def points_on_same_side_of_line_segment(pt1, pt2, line_segment) -> bool:
        """
        Check if pt1 and pt2 are on the same side of the line formed by line_segment. Do this by finding the y
        value that each point should be at, then checking how their actual y values compare to where they should be.
        Make sure they are both either <= or >=. Also, if line is vertical, make compare x-values
        :param pt1: first point
        :param pt2: second point
        :param line_segment: line segment to check pt1 and pt2 against
        :return: 
        """
        cl = archipack_floor

        line = archipack_floor.line_from_points(line_segment[0], line_segment[1])  # create a line function
        y1 = round(line(pt1[0]), 4)  # what the y-value on the line is for the x-value of the first point
        y2 = round(line(pt2[0]), 4)  # what the y-value on the line is for the x-value of the second point

        if cl.rough_comp(line_segment[0][0], line_segment[1][0], EQUAL):  # vertical line
            if cl.rough_comp(pt1[0], line_segment[0][0], GREATER_EQUAL) \
                    and cl.rough_comp(pt2[0], line_segment[0][0], GREATER_EQUAL):  # to the right of the line
                return True
            elif cl.rough_comp(pt1[0], line_segment[0][0], LESS_EQUAL) \
                    and cl.rough_comp(pt2[0], line_segment[0][0], LESS_EQUAL):  # to the left of the line
                return True
        # both points are below or on line
        elif cl.rough_comp(pt1[1], y1, LESS_EQUAL) and cl.rough_comp(pt2[1], y2, LESS_EQUAL):
            return True
        # both points are above line
        elif cl.rough_comp(pt1[1], y1, GREATER_EQUAL) and cl.rough_comp(pt2[1], y2, GREATER_EQUAL):
            return True

        return False

    @staticmethod
    def rotate_point(point, pivot, angle, units="DEGREES"):
        if units == "DEGREES":
            angle = radians(angle)

        x, y = point[0] - pivot[0], point[1] - pivot[1]
        new_x = (x * cos(angle)) - (y * sin(angle))
        new_y = (x * sin(angle)) - (y * cos(angle))

        return new_x + pivot[0], new_y + pivot[1]

    @staticmethod
    def rough_comp(val1, val2, comp: int) -> bool:
        """
        Check if val1 and val2 roughly compare to each other
        :param val1: first value
        :param val2: second value
        :param comp: How to compare them, defined using constants at top of file like EQUAL, LESS_EQUAL, etc.
        :return: Whether or not the values roughly compare to each other as specified by comp
        """

        # if allows equality
        if comp in (EQUAL, LESS_EQUAL, GREATER_EQUAL) and isclose(val1, val2, abs_tol=SLOP):
            return True
        elif comp == NOT_EQUAL and not isclose(val1, val2, abs_tol=SLOP):
            return True

        # check inequalities with equality
        upper, lower = val2 - SLOP, val2 + SLOP  # allow a spread of values for the regular inequalities

        if comp == LESS_EQUAL and val1 < val2:
            return True
        elif comp == GREATER_EQUAL and val1 > val2:
            return True

        # check inequalities
        elif comp == LESS and (val1 < upper or val1 < lower):
            return True
        elif comp == GREATER and (val1 > upper or val1 > lower):
            return True

        return False

    @staticmethod
    def round_tuple(tup, digits=4):
        return tuple([round(i, digits) for i in tup])

    @staticmethod
    def sort_corner_points(points, center):
        """
        Sort corner points so they are in a counter-clockwise order, do this by using the center and the angle
        between each point and the center. Then sort those angles from least to greatest and get the point associated
        with that angle. Since the shape is convex, no two points will have the same angle.
        :param points: The corner points to be sorted
        :param center: the center of the shape
        :return: the corner points sorted in a counter-clockwise order
        """

        # find angles
        unsorted = []
        for pt in points:
            if pt[0] - center[0] != 0:
                ang = atan((pt[1] - center[1]) / (pt[0] - center[0]))
            else:
                ang = radians(90)

            if pt[0] < center[0]:
                ang += radians(180)
            elif pt[1] < center[1]:
                ang += 360

            unsorted.append([ang, pt])

        # sort angles
        sorted_ = []
        for pt in unsorted:
            i = 0
            for pos in range(len(sorted_)):
                if pt[0] > sorted_[pos][0]:
                    i = pos + 1  # we are bigger than this one, so we need to go in next position
            sorted_.insert(i, pt)

        return [i[1] for i in sorted_]

    # TODO: speed up adding a board from boundaries
    def add_board_from_boundaries(self, shape, th, mat_id=0):
        """
        Add a board from boundary segments using the intersection of the segments as the corner points as long
        as they are within the specified shape, which is denoted by listing its boundary segments.
        :param shape: The boundary segments of the board itself, used to check if a point is in the board or not
        :param th: The thickness of the board
        :param mat_id: The material id to use for the board        
        """

        # shape center
        center = mathutils.Vector((0, 0))
        for seg in shape:
            center += mathutils.Vector(seg[0])
            center += mathutils.Vector(seg[1])
        center = archipack_floor.round_tuple(tuple(center / (2 * len(shape)))) if len(shape) != 0 else (0, 0)

        outer_boundaries = [((0, 0), (0, self.length)), ((0, 0), (self.width, 0)),
                            ((self.width, 0), (self.width, self.length)),
                            ((self.width, self.length), (0, self.length))]

        corners = self.corner_points_from_boundaries(outer_boundaries + shape, shape, center)  # find the corner points

        if len(corners) < 3:  # there needs to be at least three corners
            return

        # corners center - use to sort points because sometimes center from above is outside shape and it won't sort
        points_center = [0, 0]
        for i in corners:
            points_center[0] += i[0]
            points_center[1] += i[1]
        points_center = [i / len(corners) for i in points_center]

        points = archipack_floor.sort_corner_points(corners, points_center)

        p = len(self.vs)
        f = len(self.fs)
        # add vertices
        for pt in points:
            self.vs.append((pt[0], pt[1], 0))
            self.vs.append((pt[0], pt[1], th))

        # add faces
        start_p = p
        top_face = []
        bottom_face = []

        for i in range(len(points) - 1):  # most of the edge faces
            self.fs.append((p, p + 2, p + 3, p + 1))
            top_face.append(p)
            bottom_face.append(p + 1)
            p += 2

        # add last two vertices
        top_face.append(p)
        bottom_face.append(p + 1)

        # final side face
        self.fs.append((p, start_p, start_p + 1, p + 1))
        top_face.reverse()  # reverse to get normals right
        self.fs.append(top_face)
        self.fs.append(bottom_face)

        for i in range(len(self.fs) - f):  # at material ids
            self.ms.append(mat_id)

    def add_cube(self, x, y, z, w, l, t, clip=True, mat_id=0):
        """
        Adds vertices, faces, and material ids for a cube, makes it easy since this shape is added so much
        :param x: start x position
        :param y: start y position
        :param z: start z position
        :param w: width (in x direction)
        :param l: length (in y direction)
        :param t: thickness (in z direction)
        :param clip: trim back mesh to be within length and width
        :param mat_id: material id to use for the six faces        
        """
        # if starting point is greater than bounds, don't even bother
        if clip and (x >= self.width or y >= self.length):
            return

        if clip and x + w > self.width:
            w = self.width - x
        if clip and y + l > self.length:
            l = self.length - y

        self.append_all(self.vs, [(x, y, z), (x, y, z + t), (x + w, y, z), (x + w, y, z + t), (x, y + l, z),
                                  (x, y + l, z + t), (x + w, y + l, z), (x + w, y + l, z + t)])
        self.add_cube_faces()
        self.add_cube_mat_ids(mat_id)

    def add_cube_faces(self):
        p = len(self.vs) - 8
        self.append_all(self.fs, [(p, p + 2, p + 3, p + 1), (p + 2, p + 6, p + 7, p + 3), (p + 1, p + 3, p + 7, p + 5),
                                  (p + 6, p + 4, p + 5, p + 7), (p, p + 1, p + 5, p + 4), (p, p + 4, p + 6, p + 2)])

    def add_cube_mat_ids(self, mat_id=0):
        self.append_all(self.ms, [mat_id]*6)

    def add_manipulator(self, name, pt1, pt2, pt3):
        m = self.manipulators.add()
        m.prop1_name = name
        m.set_pts([pt1, pt2, pt3])

    def corner_points_from_boundaries(self, segments, shape, center) -> list:
        """
        Take segments and intersect them to find corner points of object. Make sure all points are within outer
        boundaries, and the shape
        :param segments: The segments that form that boundaries, [[start_v, end_v], [start_v2, end_v2]...]
        :param shape: The segments that make up the shape, [[start_v, end_v], [start_v2, end_v2]...]
        :param center: The center of shape
        :return: The points that form the corners of the object [corner_v, corner_v2...]
        """
        out = []

        # for every segment, intersect it with every other segment
        for i in range(0, len(segments) - 1):
            for j in range(i + 1, len(segments)):
                point = self.point_of_intersection(segments[i][0], segments[i][1], segments[j][0], segments[j][1])

                if point is not None:
                    r_point = self.round_tuple(tuple(point))

                    if r_point not in out and self.point_in_shape(r_point, shape, center):
                        out.append(r_point)
        return out

    def get_thickness(self):
        if self.vary_thickness:
            off = 1 / (100 / self.thickness_variance) if self.thickness_variance != 0 else 0
            v = off * self.thickness
            return uniform(self.thickness - v, self.thickness + v)
        else:
            return self.thickness

    def point_in_shape(self, point, shape, center) -> bool:
        """
        Find if the point is in the shape, do this by finding the center of the shape, and then go through each segment
        and make sure the point is on the same side of the line as the center, if it is, then it is inside the shape
        :param point: An (x, y) tuple with the point to check
        :param shape: The line segments that make up the shape, [[start_v, end_v], [start_v2, end_v2]...]
        :param center: the center of shape
        :return: Whether or not the point is in the shape
        """
        # not in outer boundaries - use NOT and self.rough_comp to allow a little bit of wiggle room at boundaries
        if not (self.rough_comp(point[0], 0, GREATER_EQUAL)
                and self.rough_comp(point[0], self.width, LESS_EQUAL)
                and self.rough_comp(point[1], 0, GREATER_EQUAL)
                and self.rough_comp(point[1], self.length, LESS_EQUAL)):
            with open('D:/test.txt', 'a') as f:
                f.write("Point: {}\n".format(point))
                # f.write("Seg: {}\n\n".format(seg))
            return False

        # go through each line segment and make sure point is on the same side as the center
        for seg in shape:
            if not archipack_floor.points_on_same_side_of_line_segment(center, point, seg):  # not in board
                return False

        return True

    def tile_grout(self):
        z = self.thickness - self.mortar_depth
        x = self.width
        y = self.length

        self.add_cube(0, 0, 0, x, y, z, mat_id=1)

    def tile_regular(self):
        """
         ____  ____  ____
        |    ||    ||    | Regular tile, rows can be offset, either manually or randomly
        |____||____||____|
           ____  ____  ____
          |    ||    ||    |
          |____||____||____| 
        """
        off = False
        o = 1 / (100 / self.offset) if self.offset != 0 else 0
        cur_y = 0.0

        while cur_y < self.length:
            cur_x = 0.0
            tl2 = self.tile_length
            if cur_y < self.length < cur_y + self.tile_length:
                tl2 = self.length - cur_y

            while cur_x < self.width:
                tw2 = self.tile_width

                if cur_x < self.width < cur_x + self.tile_width:
                    tw2 = self.width - cur_x
                elif cur_x == 0.0 and off and not self.random_offset:
                    tw2 = self.tile_width * o
                elif cur_x == 0.0 and self.random_offset:
                    v = self.tile_width * self.offset_variance * 0.0049
                    tw2 = uniform((self.tile_width / 2) - v, (self.tile_width / 2) + v)

                self.add_cube(cur_x, cur_y, 0, tw2, tl2, self.get_thickness())
                cur_x += tw2 + self.spacing

            cur_y += tl2 + self.spacing
            off = not off

    def tile_hopscotch(self):
        """
         ____  _  Large tile, plus small one on top right corner
        |    ||_|
        |____| ____  _  But shifted up so next large one is right below previous small one
              |    ||_|
              |____| 
        """
        cur_y = 0
        sp = self.spacing

        # movement variables
        row = 0

        tw = self.tile_width
        tl = self.tile_length
        s_tw = (tw - sp) / 2  # small tile width
        s_tl = (tl - sp) / 2  # small tile length

        pre_y = cur_y
        while cur_y < self.length or (row == 2 and cur_y - s_tl - sp < self.length):
            cur_x = 0
            step_back = True

            if row == 1:  # row start indented slightly
                cur_x = s_tw + sp

            while cur_x < self.width:
                if row == 0 or row == 1:
                    # adjust for if there is a need to cut off the bottom of the tile
                    if cur_y < 0:
                        self.add_cube(cur_x, 0, 0, tw, tl + cur_y, self.get_thickness())  # large one
                    else:
                        self.add_cube(cur_x, cur_y, 0, tw, tl, self.get_thickness())  # large one

                    self.add_cube(cur_x + tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, self.get_thickness())  # small one

                    if step_back:
                        cur_x += tw + sp
                        cur_y -= s_tl + sp
                    else:
                        cur_x += tw + s_tw + 2*sp
                        cur_y += s_tl + sp

                    step_back = not step_back
                else:
                    if cur_x == 0:  # half width for starting position
                        self.add_cube(cur_x, cur_y, 0, s_tw, tl, self.get_thickness())  # large one
                        # small one on right
                        self.add_cube(cur_x + s_tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, self.get_thickness())
                        # small one on bottom
                        self.add_cube(cur_x, cur_y - sp - s_tl, 0, s_tw, s_tl, self.get_thickness())
                        cur_x += (2 * s_tw) + tw + (3 * sp)
                    else:
                        self.add_cube(cur_x, cur_y, 0, tw, tl, self.get_thickness())  # large one
                        # small one on right
                        self.add_cube(cur_x + tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, self.get_thickness())
                        cur_x += (2 * tw) + (3*sp) + s_tw

            if row == 0 or row == 2:
                cur_y = pre_y + tl + sp
            else:
                cur_y = pre_y + s_tl + sp
            pre_y = cur_y

            row = (row + 1) % 3  # keep wrapping rows

    def tile_stepping_stone(self):
        """
         ____  __  ____
        |    ||__||    | Row of large one, then two small ones stacked beside it
        |    | __ |    |
        |____||__||____|
         __  __  __  __
        |__||__||__||__| Row of smalls
        """
        sp = self.spacing
        cur_y = 0.0
        row = 0

        tw = self.tile_width
        tl = self.tile_length
        s_tw = (tw - sp) / 2
        s_tl = (tl - sp) / 2

        while cur_y < self.length:
            cur_x = 0

            while cur_x < self.width:
                if row == 0:  # large one then two small ones stacked beside it
                    self.add_cube(cur_x, cur_y, 0, tw, tl, self.get_thickness())
                    self.add_cube(cur_x + tw + sp, cur_y, 0, s_tw, s_tl, self.get_thickness())
                    self.add_cube(cur_x + tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, self.get_thickness())
                    cur_x += tw + s_tw + (2 * sp)
                else:  # row of small ones
                    self.add_cube(cur_x, cur_y, 0, s_tw, s_tl, self.get_thickness())
                    self.add_cube(cur_x + s_tw + sp, cur_y, 0, s_tw, s_tl, self.get_thickness())
                    cur_x += tw + sp

            if row == 0:
                cur_y += tl + sp
            else:
                cur_y += s_tl + sp

            row = (row + 1) % 2

    def tile_hexagon(self):
        """
          __  Hexagon tiles
        /   \
        \___/ 
        """
        sp = self.spacing
        width = self.tile_width
        dia = (width / 2) / cos(radians(30))
        #               top of current, half way up next,    vertical spacing component
        vertical_spacing = dia * (1 + sin(radians(30))) + (sp * sin(radians(60)))  # center of one row to next row
        base_points = [self.rotate_point((dia, 0), (0, 0), ang + 30) for ang in range(0, 360, 60)]

        cur_y = 0
        offset = False
        while cur_y - width / 2 < self.length:  # place tile as long as bottom is still within bounds
            if offset:
                cur_x = width / 2
            else:
                cur_x = -sp / 2

            while cur_x - width / 2 < self.width:  # place tile as long as left is still within bounds
                segments = self.line_segments_from_points([(pt[0] + cur_x, pt[1] + cur_y) for pt in base_points])
                self.add_board_from_boundaries(segments, self.get_thickness())

                cur_x += width + sp

            cur_y += vertical_spacing
            offset = not offset

    def tile_windmill(self):
        """
         __  ____
        |  ||____| This also has a square one in the middle, totaling 5 tiles per pattern
        |__|   __
         ____ |  |
        |____||__|  
        """
        sp = self.spacing

        tw = self.tile_width
        tl = self.tile_length
        s_tw = (tw - sp) / 2
        s_tl = (tl - sp) / 2

        cur_y = 0
        while cur_y < self.length:
            cur_x = 0

            while cur_x < self.width:
                self.add_cube(cur_x, cur_y, 0, tw, s_tl, self.get_thickness())  # bottom
                self.add_cube(cur_x + tw + sp, cur_y, 0, s_tw, tl, self.get_thickness())  # right
                self.add_cube(cur_x + s_tw + sp, cur_y + tl + sp, 0, tw, s_tl, self.get_thickness())  # top
                self.add_cube(cur_x, cur_y + s_tl + sp, 0, s_tw, tl, self.get_thickness())  # left
                self.add_cube(cur_x + s_tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, self.get_thickness())  # center

                cur_x += tw + s_tw + (2*sp)
            cur_y += tl + s_tl + (2*sp)

    def wood_regular(self):
        """
        ||| Typical wood boards
        |||
        """
        cur_x = 0.0
        bw, bl = self.board_width, self.board_length

        while cur_x < self.width:
            if self.vary_width:
                v = bw * (self.width_variance / 100) * 0.99
                bw2 = uniform(bw - v, bw + v)
            else:
                bw2 = bw

            if bw2 + cur_x > self.width:
                bw2 = self.width - cur_x
            cur_y = 0.0

            counter = 1
            while cur_y < self.length:
                bl2 = bl
                if self.vary_length:
                    v = bl * (self.length_variance / 100) * 0.99
                    bl2 = uniform(bl - v, bl + v)
                if (counter >= self.max_boards and self.vary_length) or cur_y + bl2 > self.length:
                    bl2 = self.length - cur_y

                self.add_cube(cur_x, cur_y, 0, bw2, bl2, self.get_thickness())
                cur_y += bl2 + self.length_spacing
                counter += 1

            cur_x += bw2 + self.width_spacing

    def wood_square_parquet(self):
        """
        ||--||-- Alternating groups oriented either horizontally, or forwards and backwards.
        ||--||-- self.spacing is used because it is the same spacing for width and length
        --||--|| Board width is calculated using number of boards and the length.
        --||--||
        """
        cur_x = 0.0
        start_orient_length = True

        # figure board width
        bl = self.short_board_length
        bw = (bl - (self.boards_in_group - 1) * self.spacing) / self.boards_in_group
        while cur_x < self.width:
            cur_y = 0.0
            orient_length = start_orient_length
            while cur_y < self.length:

                if orient_length:
                    start_x = cur_x

                    for i in range(self.boards_in_group):
                        if cur_x < self.width and cur_y < self.length:
                            self.add_cube(cur_x, cur_y, 0, bw, bl, self.get_thickness())
                            cur_x += bw + self.spacing

                    cur_x = start_x
                    cur_y += bl + self.spacing

                else:
                    for i in range(self.boards_in_group):
                        if cur_x < self.width and cur_y < self.length:
                            self.add_cube(cur_x, cur_y, 0, bl, bw, self.get_thickness())
                            cur_y += bw + self.spacing

                orient_length = not orient_length

            start_orient_length = not start_orient_length
            cur_x += bl + self.spacing

    def wood_herringbone(self):
        """
        Boards are at 45 degree angle, in chevron pattern, ends are angled 
        """
        width_dif = self.board_width / cos(radians(45))
        x_dif = self.short_board_length * cos(radians(45))
        y_dif = self.short_board_length * sin(radians(45))
        total_y_dif = width_dif + y_dif
        sp_dif = self.spacing / cos(radians(45))

        cur_y = -y_dif
        while cur_y < self.length:
            cur_x = 0

            while cur_x < self.width:
                # left side
                board = self.line_segments_from_points(
                    [(cur_x, cur_y), (cur_x + x_dif, cur_y + y_dif),
                     (cur_x + x_dif, cur_y + total_y_dif), (cur_x, cur_y + width_dif)]
                )
                self.add_board_from_boundaries(board, self.get_thickness())
                cur_x += x_dif + self.spacing

                # right side
                if cur_x < self.width:
                    board = self.line_segments_from_points(
                        [(cur_x, cur_y + y_dif), (cur_x + x_dif, cur_y),
                         (cur_x + x_dif, cur_y + width_dif), (cur_x, cur_y + total_y_dif)]
                    )
                    self.add_board_from_boundaries(board, self.get_thickness())
                    cur_x += x_dif + self.spacing

            cur_y += width_dif + sp_dif  # adjust spacing amount for 45 degree angle

    def wood_herringbone_parquet(self):
        """
        Boards are at 45 degree angle, in chevron pattern, ends are square, not angled
        """
        x_dif = self.short_board_length * cos(radians(45))
        y_dif = self.short_board_length * sin(radians(45))
        y_dif_45 = self.board_width * cos(radians(45))
        x_dif_45 = self.board_width * sin(radians(45))
        total_y_dif = y_dif + y_dif_45

        sp_dif = (self.spacing / cos(radians(45))) / 2  # divide by two since it is used for both x and y
        width_dif = self.board_width / cos(radians(45))

        cur_y = -y_dif
        while cur_y - y_dif_45 < self.length:  # continue as long as bottom left corner is still good
            cur_x = 0
            pre_y = cur_y

            while cur_x - x_dif_45 < self.width:  # continue as long as top left corner is still good
                # left side
                board = self.line_segments_from_points(
                    [(cur_x, cur_y), (cur_x + x_dif, cur_y + y_dif),
                     (cur_x + x_dif - x_dif_45, cur_y + total_y_dif), (cur_x - x_dif_45, cur_y + y_dif_45)]
                )
                self.add_board_from_boundaries(board, self.get_thickness())
                cur_x += x_dif - x_dif_45 + sp_dif
                cur_y += y_dif - y_dif_45 - sp_dif

                if cur_x < self.width:
                    board = self.line_segments_from_points(
                        [(cur_x, cur_y), (cur_x + x_dif, cur_y - y_dif),
                         (cur_x + x_dif + x_dif_45, cur_y - y_dif + y_dif_45),
                         (cur_x + x_dif_45, cur_y + y_dif_45)]
                    )
                    self.add_board_from_boundaries(board, self.get_thickness())
                    cur_x += x_dif + x_dif_45 + sp_dif
                    cur_y -= y_dif - y_dif_45 - sp_dif

            cur_y = pre_y + width_dif + (2*sp_dif)

    def update_data(self):
        # clear data before refreshing it
        self.vs, self.fs, self.ms = [], [], []

        if self.floor_material == "wood":
            if self.wood_style == "regular":
                self.wood_regular()
            elif self.wood_style == "square_parquet":
                self.wood_square_parquet()
            elif self.wood_style == "herringbone":
                self.wood_herringbone()
            elif self.wood_style == "herringbone_parquet":
                self.wood_herringbone_parquet()

        elif self.floor_material == "tile":
            self.tile_grout()  # create grout

            if self.tile_style == "regular":
                self.tile_regular()
            elif self.tile_style == "hopscotch":
                self.tile_hopscotch()
            elif self.tile_style == "stepping_stone":
                self.tile_stepping_stone()
            elif self.tile_style == "hexagon":
                self.tile_hexagon()
            elif self.tile_style == "windmill":
                self.tile_windmill()

    def update_manipulators(self):
        self.manipulators.clear()  # clear every time, add new ones
        self.add_manipulator("length", (0, 0, 0), (0, self.length, 0), (-0.4, 0, 0))
        self.add_manipulator("width", (0, 0, 0), (self.width, 0, 0), (0.4, 0, 0))

        z = self.thickness

        if self.floor_material == "wood":
            if self.wood_style == "regular":
                self.add_manipulator("board_length", (0, 0, z), (0, self.board_length, z), (0.1, 0, z))
                self.add_manipulator("board_width", (0, 0, z), (self.board_width, 0, z), (-0.2, 0, z))
            elif self.wood_style == "square_parquet":
                self.add_manipulator("short_board_length", (0, 0, z), (0, self.short_board_length, z), (-0.2, 0, z))
            elif self.wood_style in ("herringbone", "herringbone_parquet"):
                dia = self.short_board_length * cos(radians(45))
                dia2 = self.board_width * cos(radians(45))
                self.add_manipulator("short_board_length", (0, 0, z), (dia, dia, z), (0, 0, z))
                self.add_manipulator("board_width", (dia, 0, z), (dia - dia2, dia2, z), (0, 0, z))

        elif self.floor_material == "tile":
            tl = self.tile_length
            tw = self.tile_width

            if self.tile_style in ("regular", "hopscotch", "stepping_stone"):
                self.add_manipulator("tile_width", (0, tl, z), (tw, tl, z), (0, 0, z))
                self.add_manipulator("tile_length", (0, 0, z), (0, tl, z), (0, 0, z))
            elif self.tile_style == "hexagon":
                self.add_manipulator("tile_width", (tw / 2 + self.spacing, 0, z), (tw * 1.5 + self.spacing, 0, z),
                                     (0, 0, 0))
            elif self.tile_style == "windmill":
                self.add_manipulator("tile_width", (0, 0, z), (tw, 0, 0), (0, 0, z))
                self.add_manipulator("tile_length", (0, tl / 2 + self.spacing, z), (0, tl * 1.5 + self.spacing, z),
                                     (0, 0, z))

    @property
    def verts(self):
        return self.vs

    @property
    def faces(self):
        return self.fs

    @property
    def uvs(self):
        return []

    @property
    def matids(self):
        return self.ms

    def update(self, context):

        old = context.active_object

        o, props = ARCHIPACK_PT_floor.params(old)
        if props != self:
            return

        o.select = True
        context.scene.objects.active = o

        self.update_data()  # update vertices and faces
        BmeshEdit.buildmesh(context, o, self.verts, self.faces, matids=self.matids)  # , uvs=self.uvs)

        # update manipulators
        self.update_manipulators()

        # restore context
        old.select = True
        context.scene.objects.active = old

# ------------------------------------------------------------------
# Define panel class to show object parameters in ui panel (N)
# ------------------------------------------------------------------


class ARCHIPACK_PT_floor(Panel):
    bl_idname = "ARCHIPACK_PT_floor"
    bl_label = "Floor"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Floor'

    def draw(self, context):
        layout = self.layout
        o = context.object

        o, props = ARCHIPACK_PT_floor.params(o)
        if props is None:
            return

        # manipulate
        layout.operator("archipack.floor_manipulate")
        layout.separator()

        # materials / style
        layout.prop(props, 'floor_material')
        if props.floor_material == "wood":
            layout.prop(props, 'wood_style')
        elif props.floor_material == 'tile':
            layout.prop(props, 'tile_style')
        layout.separator()

        # overall measurements
        layout.prop(props, 'width')
        layout.prop(props, 'length')

        # thickness
        layout.separator()
        layout.prop(props, 'thickness')
        layout.prop(props, 'vary_thickness', icon='RNDCURVE')
        if props.vary_thickness:
            layout.prop(props, 'thickness_variance')
        layout.separator()

        # wood
        if props.floor_material == "wood":
            # length
            if props.wood_style == 'regular':
                layout.prop(props, 'board_length')
                layout.prop(props, 'vary_length', icon='RNDCURVE')
                if props.vary_length:
                    layout.prop(props, 'length_variance')
                    layout.prop(props, 'max_boards')
                layout.separator()

                # width
                layout.prop(props, 'board_width')
                # vary width
                if props.wood_style == 'regular':
                    layout.prop(props, 'vary_width', icon='RNDCURVE')
                    if props.vary_width:
                        layout.prop(props, 'width_variance')
                    layout.separator()

                layout.prop(props, 'length_spacing')
                layout.prop(props, 'width_spacing')
                layout.separator()
            else:
                layout.prop(props, 'short_board_length')

                if props.wood_style != "square_parquet":
                    layout.prop(props, "board_width")
                layout.prop(props, "spacing")

                if props.wood_style == 'square_parquet':
                    layout.prop(props, 'boards_in_group')
        # tile
        elif props.floor_material == "tile":
            # width and length and mortar
            if props.tile_style != "hexagon":
                layout.prop(props, "tile_length")
            layout.prop(props, "tile_width")
            layout.prop(props, "mortar_depth")
            layout.separator()

            if props.tile_style == "regular":
                layout.prop(props, "random_offset", icon="RNDCURVE")
                if props.random_offset:
                    layout.prop(props, "offset_variance")
                else:
                    layout.prop(props, "offset")

        # updating
        layout.separator()
        layout.prop(props, 'auto_update', icon='FILE_REFRESH')
        if not props.auto_update:
            layout.operator('archipack.floor_update')

    @classmethod
    def params(cls, o):
        if cls.filter(o):
            if 'archipack_floor' in o.data:
                return o, o.data.archipack_floor[0]
        return o, None

    @classmethod
    def filter(cls, o):
        try:
            return o.data is not None and bool('archipack_floor' in o.data)
        except:
            return False

    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        return cls.filter(o)

# ------------------------------------------------------------------
# Define operator class to create object
# ------------------------------------------------------------------


class ARCHIPACK_OT_floor(Operator):
    bl_idname = "archipack.floor"
    bl_label = "Floor"
    bl_description = "Floor"
    bl_category = 'Sample'
    bl_options = {'REGISTER', 'UNDO'}

    def create(self, context):
        """
            expose only basic params in operator
            use object property for other params
        """
        m = bpy.data.meshes.new("Floor")
        o = bpy.data.objects.new("Floor", m)

        # attach parametric datablock
        d = m.archipack_floor.add()

        context.scene.objects.link(o)
        # make newly created object active
        o.select = True
        context.scene.objects.active = o
        # create mesh data
        d.update(context)
        return o

    def execute(self, context):
        if context.mode == "OBJECT":
            bpy.ops.object.select_all(action="DESELECT")
            o = self.create(context)
            o.location = context.scene.cursor_location
            # activate manipulators at creation time
            o.select = True
            context.scene.objects.active = o
            bpy.ops.archipack.floor_manipulate()
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Option only valid in Object mode")
            return {'CANCELLED'}

# ------------------------------------------------------------------
# Define operator for manually updating mesh
# ------------------------------------------------------------------


class ARCHIPACK_OT_floor_update(Operator):
    bl_idname = "archipack.floor_update"
    bl_label = "Update Floor"
    bl_description = "Manually update floor"
    bl_category = 'Sample'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return ARCHIPACK_PT_floor.filter(context.active_object)

    def execute(self, context):
        if context.mode == "OBJECT":
            o, props = ARCHIPACK_PT_floor.params(context.object)
            if props is None:
                return

            props.update(context)
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Option only valid in Object mode")
            return {'CANCELLED'}

# ------------------------------------------------------------------
# Define operator class to manipulate object
# ------------------------------------------------------------------


class ARCHIPACK_OT_floor_manipulate(Operator):
    bl_idname = "archipack.floor_manipulate"
    bl_label = "Manipulate"
    bl_description = "Manipulate"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return ARCHIPACK_PT_floor.filter(context.active_object)

    def modal(self, context, event):
        return self.d.manipulable_modal(context, event)

    def invoke(self, context, event):
        if context.space_data.type == 'VIEW_3D':
            o = context.active_object
            self.d = o.data.archipack_floor[0]
            self.d.manipulable_invoke(context)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

# ------------------------------------------------------------------
# Define a panel class to add button on Create panel under regular primitives
# ------------------------------------------------------------------


class TOOLS_PT_parametric_object(Panel):
    bl_label = "ParametricObject"
    bl_idname = "TOOLS_PT_parametric_object"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Create"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        box = row.box()
        box.label("Objects")
        row = box.row(align=True)
        row.operator("archipack.floor")


def register():
    bpy.utils.register_class(archipack_floor)
    bpy.utils.register_class(ARCHIPACK_OT_floor_manipulate)
    bpy.utils.register_class(ARCHIPACK_OT_floor_update)
    bpy.utils.register_class(ARCHIPACK_OT_floor)
    bpy.utils.register_class(ARCHIPACK_PT_floor)
    bpy.utils.register_class(TOOLS_PT_parametric_object)
    Mesh.archipack_floor = CollectionProperty(type=archipack_floor)


def unregister():
    bpy.utils.unregister_class(archipack_floor)
    bpy.utils.unregister_class(ARCHIPACK_OT_floor_manipulate)
    bpy.utils.unregister_class(ARCHIPACK_OT_floor_update)
    bpy.utils.unregister_class(ARCHIPACK_OT_floor)
    bpy.utils.unregister_class(ARCHIPACK_PT_floor)
    bpy.utils.unregister_class(TOOLS_PT_parametric_object)
    del Mesh.archipack_floor


if __name__ == "__main__":
    register()
