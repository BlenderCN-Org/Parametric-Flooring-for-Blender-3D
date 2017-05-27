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
from math import radians, cos, sin, atan
from .bmesh_utils import BmeshEdit
from .simple_manipulator import Manipulable

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

FOOT = 0.3048  # 1 foot in meters
INCH = 0.0254  # 1 inch in meters

# ------------------------------------------------------------------
# Define property class to store object parameters and update mesh
# ------------------------------------------------------------------


def update(self, context):
    self.update(context)


class archipack_floor(Manipulable, PropertyGroup):

    # keep track of data
    vs, fs = [], []  # vertices and faces
    ms = []  # mat ids

    # floor type
    floor_material = EnumProperty(
        name="floor material", items=(("wood", "Wood", ""), ("tile", "Tile", "")),
        default="wood", description="Type of material the floor is made of", update=update
    )
    wood_style = EnumProperty(
        name='wood style', items=(("regular", "Regular", ""), ("parquet", "Parquet", ""),
                                  ("herringbone_parquet", "Herringbone Parquet", ""),
                                  ("herringbone", "Herringbone", "")), default="regular",
        description="Style of wood floor", update=update
    )
    tile_style = EnumProperty(
        name='tile style', items=(("regular", "Regular", ""), ("hopscotch", "Hopscotch", ""),
                                  ("stepping_stone", "Stepping Stone", ""), ("hexagon", "Hexagon", ""),
                                  ("windmill", "Windmill", "")),
        default="regular", update=update
    )

    # overall length and width
    width = FloatProperty(  # x
        name='width',
        min=2*FOOT, soft_max=100*FOOT,
        default=20*FOOT, precision=2,
        description='Width', update=update,
        subtype="DISTANCE"
    )
    length = FloatProperty(  # y
        name='length',
        min=2*FOOT, soft_max=100*FOOT,
        default=8*FOOT, precision=2,
        description='Length', update=update,
        subtype="DISTANCE"
    )

    # generic spacing
    spacing = FloatProperty(
        name='spacing', unit='LENGTH', min=0, soft_max=1 * INCH,
        default=0.125 * INCH, precision=2, update=update,
        description='The amount of space between boards or tiles in both directions'
    )

    # board thickness
    thickness = FloatProperty(  # z
        name='thickness',
        min=0.25*INCH, soft_max=2*INCH,
        default=1*INCH, precision=2,
        description='Thickness', update=update,
        subtype="DISTANCE"
    )
    vary_thickness = BoolProperty(
        name='vary thickness', update=update, default=False,
        description='Vary board thickness?'
    )
    thickness_variance = FloatProperty(
        name='thickness variance', min=1, max=100,
        default=50, update=update, precision=2,
        description='How much board thickness can vary by'
    )

    # board width, variance, and spacing
    board_width = FloatProperty(
        name='board width', unit='LENGTH', min=2*INCH,
        soft_max=2*FOOT, default=6*INCH, update=update,
        description='The width of the boards', precision=2
    )
    vary_width = BoolProperty(
        name='vary width', default=False,
        description='Vary board width?', update=update
    )
    width_variance = FloatProperty(
        name='width variance', subtype='PERCENTAGE',
        min=1, max=100, default=50, description='How much board width can vary by',
        precision=2, update=update
    )
    width_spacing = FloatProperty(
        name='width spacing', unit='LENGTH', min=0, soft_max=1*INCH,
        default=0.125*INCH, precision=2, update=update,
        description='The amount of space between boards in the width direction'
    )

    # board length
    board_length = FloatProperty(
        name='board length', unit='LENGTH', min=2*FOOT,
        soft_max=100*FOOT, default=8*FOOT, update=update,
        description='The length of the boards', precision=2
    )
    short_board_length = FloatProperty(
        name='board length', unit='LENGTH', min=6*INCH,
        soft_max=4*FOOT, default=2*FOOT, update=update,
        description='The length of the boards', precision=2
    )
    vary_length = BoolProperty(
        name='vary length', default=False,
        description='Vary board length?', update=update
    )
    length_variance = FloatProperty(
        name='length variance', subtype='PERCENTAGE',
        min=1, max=100, default=50, description='How much board length can vary by',
        precision=2, update=update
    )
    max_boards = IntProperty(
        name='max boards', min=1, soft_max=10, default=2,
        update=update, description='Max number of boards in one row'
    )
    length_spacing = FloatProperty(
        name='length spacing', unit='LENGTH', min=0, soft_max=1*INCH,
        default=0.125*INCH, precision=2, update=update,
        description='The amount of space between boards in the length direction'
    )

    # parquet specific
    boards_in_group = IntProperty(
        name='boards in group', min=1, soft_max=10, default=4,
        update=update, description='Number of boards in a group'
    )

    # tile specific
    tile_width = FloatProperty(
        name='tile width', min=2*INCH, soft_max=2*FOOT, default=1*FOOT,
        update=update, precision=2, description='Width of the tiles', unit='LENGTH',
    )
    tile_length = FloatProperty(
        name='tile length', min=2*INCH, soft_max=2*FOOT, default=8*INCH,
        update=update, precision=2, description='Length of the tiles', unit='LENGTH',
    )
    mortar_depth = FloatProperty(
        name='mortar depth', min=0, soft_max=1*INCH, default=0.25*INCH,
        update=update, precision=2, unit='LENGTH',
        description='The depth of the mortar from the surface of the tile'
    )

    # regular tile
    offset_tiles = BoolProperty(
        name='offset tiles', update=update, default=False,
        description='Offset the tiles?'
    )
    random_offset = BoolProperty(
        name='random offset', update=update, default=False,
        description='Random amount of offset for each row of tiles'
    )
    offset = FloatProperty(
        name='offset', update=update, min=0.001, max=100, default=50,
        precision=2, description='How much to offset each row of tiles'
    )
    offset_variance = FloatProperty(
        name='offset variance', update=update, min=0.001, max=100, default=50,
        precision=2, description='How much to vary the offset each row of tiles'
    )

    @staticmethod
    def append_all(v_list, add):
        for i in add:
            v_list.append(i)

    @staticmethod
    def round_tuple(tup, digits=4):
        return [round(i, digits) for i in tup]

    @staticmethod
    def round_2d_list(li, digits=4):
        return [archipack_floor.round_tuple(i, digits) for i in li]

    def add_cube_faces(self):
        p = len(self.vs) - 8
        self.append_all(self.fs, [(p, p + 2, p + 3, p + 1), (p + 2, p + 6, p + 7, p + 3), (p + 1, p + 3, p + 7, p + 5),
                                  (p + 6, p + 4, p + 5, p + 7), (p, p + 1, p + 5, p + 4), (p, p + 4, p + 6, p + 2)])

    def add_cube_mat_ids(self, mat_id=0):
        self.append_all(self.ms, [mat_id]*6)

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

    def corner_points_from_boundaries(self, segments, shape) -> list:
        """
        Take segments and intersect them to find corner points of object.
        :param segments: The segments that form that boundaries, [[start_v, end_v], [start_v, end_v]...]
        :param shape: The corner vertices to make sure the points found by intersecting the lines are inside the object,
        [corner_v, corner_v2...]
        :return: The points that form the corners of the object [corner_v, corner_v2...]
        """
        out = []
        shape = archipack_floor.round_2d_list(shape)

        for i in range(0, len(segments) - 1):
            for j in range(i + 1, len(segments)):
                point = mathutils.geometry.intersect_line_line_2d(segments[i][0], segments[i][1], segments[j][0],
                                                                  segments[j][1])

                if point is not None:
                    r_point = archipack_floor.round_tuple(tuple(point))

                    if r_point not in out and self.point_in_shape(r_point, shape):
                        out.append(r_point)
        return out

    def point_in_shape(self, point, shape) -> bool:
        """
        Find if the point is in the shape
        :param point: An (x, y) tuple with the point to check
        :param shape: The corner vertices that make up that shape [corner_v, corner_v2...]
        :return: Whether or not the point is in the shape
        """
        if mathutils.geometry.intersect_point_quad_2d(point, *shape) == 1:  # inside board
            if 0 <= point[0] <= self.width and 0 <= point[1] <= self.length:  # inside outer bounds
                return True

        return False

    def add_shape_from_corner_points(self, points, th, mat_id=0):
        points = archipack_floor.sort_corner_points(points)

        p = len(self.vs)
        # add vertices
        for pt in points:
            self.vs.append((pt[0], pt[1], 0))
            self.vs.append((pt[0], pt[1], th))

        # add faces
        start_p = p
        top_face = []
        bottom_face = []

        for i in range(len(points) - 1):
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

    def create_board_from_boundaries(self, segments, shape, th, mat_id=0):
        corners = self.corner_points_from_boundaries(segments, shape)
        self.add_shape_from_corner_points(corners, th, mat_id)

    @staticmethod
    def sort_corner_points(points):
        """
        Sort corner points so they are in a counter-clockwise order
        :param points: The corner points to be sorted
        :return: the corner points sorted in a counter-clockwise order
        """
        # find center
        center = mathutils.Vector((0, 0))
        for pt in points:
            center += mathutils.Vector(pt)
        center = center / len(points) if len(points) != 0 else 0

        # find angles
        unsorted = []
        for pt in points:
            ang = atan((pt[1] - center[1]) / (pt[0] - center[0]))
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
        o = 1 / (100 / self.offset)
        cur_y = 0.0
        z = self.thickness

        while cur_y < self.length:
            cur_x = 0.0
            tl2 = self.tile_length
            if cur_y < self.length < cur_y + self.tile_length:
                tl2 = self.length - cur_y

            while cur_x < self.width:
                tw2 = self.tile_width

                if cur_x < self.width < cur_x + self.tile_width:
                    tw2 = self.width - cur_x
                elif cur_x == 0.0 and off and self.offset_tiles and not self.random_offset:
                    tw2 = self.tile_width * o
                elif cur_x == 0.0 and self.offset_tiles and self.random_offset:
                    v = self.tile_length * 0.0049 * self.offset_variance
                    tw2 = uniform((self.tile_length / 2) - v, (self.tile_length / 2) + v)

                self.add_cube(cur_x, cur_y, 0, tw2, tl2, z)
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
        th = self.thickness
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
                        self.add_cube(cur_x, 0, 0, tw, tl + cur_y, th)  # large one
                    else:
                        self.add_cube(cur_x, cur_y, 0, tw, tl, th)  # large one

                    self.add_cube(cur_x + tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, th)  # small one

                    if step_back:
                        cur_x += tw + sp
                        cur_y -= s_tl + sp
                    else:
                        cur_x += tw + s_tw + 2*sp
                        cur_y += s_tl + sp

                    step_back = not step_back
                else:
                    if cur_x == 0:  # half width for starting position
                        self.add_cube(cur_x, cur_y, 0, s_tw, tl, th)  # large one
                        self.add_cube(cur_x + s_tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, th)  # small one on right
                        self.add_cube(cur_x, cur_y - sp - s_tl, 0, s_tw, s_tl, th)  # small one on bottom
                        cur_x += (2 * s_tw) + tw + (3 * sp)
                    else:
                        self.add_cube(cur_x, cur_y, 0, tw, tl, th)  # large one
                        self.add_cube(cur_x + tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, th)  # small one on right
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
        th = self.thickness
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
                    self.add_cube(cur_x, cur_y, 0, tw, tl, th)
                    self.add_cube(cur_x + tw + sp, cur_y, 0, s_tw, s_tl, th)
                    self.add_cube(cur_x + tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, th)
                    cur_x += tw + s_tw + (2 * sp)
                else:  # row of small ones
                    self.add_cube(cur_x, cur_y, 0, s_tw, s_tl, th)
                    self.add_cube(cur_x + s_tw + sp, cur_y, 0, s_tw, s_tl, th)
                    cur_x += tw + sp

            if row == 0:
                cur_y += tl + sp
            else:
                cur_y += s_tl + sp

            row = (row + 1) % 2

    def tile_hexagon(self):
        pass

    def tile_windmill(self):
        """
         __  ____
        |  ||____| This also has a square one in the middle, totaling 5 tiles per pattern
        |__|   __
         ____ |  |
        |____||__|  
        """
        th = self.thickness
        sp = self.spacing

        tw = self.tile_width
        tl = self.tile_length
        s_tw = (tw - sp) / 2
        s_tl = (tl - sp) / 2

        cur_y = 0
        while cur_y < self.length:
            cur_x = 0

            while cur_x < self.width:
                self.add_cube(cur_x, cur_y, 0, tw, s_tl, th)  # bottom
                self.add_cube(cur_x + tw + sp, cur_y, 0, s_tw, tl, th)  # right
                self.add_cube(cur_x + s_tw + sp, cur_y + tl + sp, 0, tw, s_tl, th)  # top
                self.add_cube(cur_x, cur_y + s_tl + sp, 0, s_tw, tl, th)  # left
                self.add_cube(cur_x + s_tw + sp, cur_y + s_tl + sp, 0, s_tw, s_tl, th)  # center

                cur_x += tw + s_tw + (2*sp)
            cur_y += tl + s_tl + (2*sp)

    def wood_regular(self):
        """
        ||| Typical wood boards
        |||
        """
        cur_x = 0.0
        zt = self.thickness
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
                z = zt
                if self.vary_thickness:
                    v = z * 0.99 * (self.thickness_variance / 100)
                    z = uniform(z - v, z + v)
                bl2 = bl
                if self.vary_length:
                    v = bl * (self.length_variance / 100) * 0.99
                    bl2 = uniform(bl - v, bl + v)
                if (counter >= self.max_boards and self.vary_length) or cur_y + bl2 > self.length:
                    bl2 = self.length - cur_y

                self.add_cube(cur_x, cur_y, 0, bw2, bl2, z)
                cur_y += bl2 + self.length_spacing
                counter += 1

            cur_x += bw2 + self.width_spacing

    def wood_parquet(self):
        """
        ||--||-- Alternating groups oriented either horizontally, or forwards and backwards.
        ||--||-- self.spacing is used because it is the same spacing for width and length
        --||--||
        --||--||
        """
        cur_x = 0.0
        z = self.thickness
        start_orient_length = True

        # figure board length
        bl = (self.board_width * self.boards_in_group) + (self.spacing * (self.boards_in_group - 1))
        while cur_x < self.width:
            cur_y = 0.0
            orient_length = start_orient_length
            while cur_y < self.length:
                bl2 = bl
                bw2 = self.board_width

                if orient_length:
                    start_x = cur_x

                    for i in range(self.boards_in_group):
                        if cur_x < self.width and cur_y < self.length:
                            # make sure board should be placed
                            if cur_x < self.width < cur_x + self.board_width:
                                bw2 = self.width - cur_x
                            if cur_y < self.length < cur_y + bl:
                                bl2 = self.length - cur_y
                            p = len(self.vs)

                            self.append_all(self.vs, [(cur_x, cur_y, 0.0), (cur_x, cur_y, z), (cur_x + bw2, cur_y, z),
                                                      (cur_x + bw2, cur_y, 0.0)])
                            cur_y += bl2
                            self.append_all(self.vs, [(cur_x, cur_y, 0.0), (cur_x, cur_y, z), (cur_x + bw2, cur_y, z),
                                                      (cur_x + bw2, cur_y, 0.0)])
                            cur_y -= bl2
                            cur_x += bw2 + self.spacing

                            self.append_all(self.fs, [(p, p + 3, p + 2, p + 1), (p + 4, p + 5, p + 6, p + 7),
                                                      (p, p + 4, p + 7, p + 3), (p + 3, p + 7, p + 6, p + 2),
                                                      (p + 1, p + 2, p + 6, p + 5), (p, p + 1, p + 5, p + 4)])
                            self.append_all(self.ms, [0]*6)

                    cur_x = start_x
                    cur_y += bl2 + self.spacing

                else:
                    for i in range(self.boards_in_group):
                        if cur_x < self.width and cur_y < self.length:
                            if cur_x < self.width < cur_x + bl:
                                bl2 = self.width - cur_x
                            if cur_y < self.length < cur_y + self.board_width:
                                bw2 = self.length - cur_y
                            p = len(self.vs)

                            self.append_all(self.vs, [(cur_x, cur_y + bw2, 0.0), (cur_x, cur_y + bw2, z),
                                                      (cur_x, cur_y, z), (cur_x, cur_y, 0.0)])
                            cur_x += bl2
                            self.append_all(self.vs, [(cur_x, cur_y + bw2, 0.0), (cur_x, cur_y + bw2, z),
                                                      (cur_x, cur_y, z), (cur_x, cur_y, 0.0)])
                            cur_x -= bl2
                            cur_y += bw2 + self.spacing

                            self.append_all(self.fs, [(p, p + 3, p + 2, p + 1), (p + 4, p + 5, p + 6, p + 7),
                                                      (p, p + 4, p + 7, p + 3), (p + 3, p + 7, p + 6, p + 2),
                                                      (p + 1, p + 2, p + 6, p + 5), (p, p + 1, p + 5, p + 4)])
                            self.append_all(self.ms, [0]*6)

                orient_length = not orient_length

            start_orient_length = not start_orient_length
            cur_x += bl + self.spacing

    def wood_herringbone(self):
        sp = self.spacing
        boundaries = [[(0, 0), (0, self.length)], [(0, 0), (self.width, 0)],
                      [(self.width, 0), (self.width, self.length)], [(self.width, self.length), (0, self.length)]]

        width_dif = self.board_width / cos(radians(45))
        x_dif = self.short_board_length * cos(radians(45))
        y_dif = self.short_board_length * sin(radians(45))
        total_y_dif = width_dif + y_dif

        cur_y = 0
        while cur_y < self.length:
            cur_x = 0

            while cur_x < self.width:
                print("--------------------")
                # left side
                self.create_board_from_boundaries(
                    boundaries + [[(cur_x, cur_y), (cur_x + x_dif, cur_y + y_dif)],
                                  [(cur_x + x_dif, cur_y + y_dif), (cur_x + x_dif, cur_y + total_y_dif)],
                                  [(cur_x + x_dif, cur_y + total_y_dif), (cur_x, cur_y + width_dif)],
                                  [(cur_x, cur_y + width_dif), (cur_x, cur_y)]],
                    [(cur_x, cur_y), (cur_x + x_dif, cur_y + y_dif), (cur_x + x_dif, cur_y + total_y_dif),
                     (cur_x, cur_y + width_dif)],
                    self.thickness
                )

                cur_x = self.width

                # right side
                # if cur_x < self.width:
                #     self.board_from_boundary_lines(
                #         boundaries + [[(cur_x, cur_y + y_dif), (cur_x + x_dif, cur_y)],
                #                       [(cur_x + x_dif, cur_y), (cur_x + x_dif, cur_y + width_dif)],
                #                       [(cur_x + x_dif, cur_y + width_dif), (cur_x, cur_y + total_y_dif)],
                #                       [(cur_x, cur_y + total_y_dif), (cur_x, cur_y + y_dif)]],
                #         [(cur_x, cur_y + y_dif), (cur_x + x_dif, cur_y), (cur_x + x_dif, cur_y + width_dif),
                #          (cur_x, cur_y + total_y_dif)], self.thickness)
                #
                #     cur_x += x_dif + sp

            cur_y += width_dif + sp / cos(radians(45))  # adjust spacing amount for 45 degree angle

    def wood_herringbone_parquet(self):
        pass

    def update_data(self):
        # clear data before refreshing it
        self.vs, self.fs, self.ms = [], [], []

        if self.floor_material == "wood":
            if self.wood_style == "regular":
                self.wood_regular()
            elif self.wood_style == "parquet":
                self.wood_parquet()
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

    @property
    def verts(self):
        """
            Object vertices coords
        """
        return self.vs

    @property
    def faces(self):
        """
            Object faces vertices index
        """
        return self.fs

    @property
    def uvs(self):
        """
            Object faces uv coords
        """
        return []

    @property
    def matids(self):
        """
            Object material indexes
        """
        return []

    def update(self, context):

        old = context.active_object

        o, props = ARCHIPACK_PT_floor.params(old)
        if props != self:
            return

        o.select = True
        context.scene.objects.active = o

        self.update_data()  # update vertices and faces
        BmeshEdit.buildmesh(context, o, self.verts, self.faces)  # , matids=self.matids, uvs=self.uvs)

        # setup 3d points for gl manipulators
        self.manipulators[0].set_pts([(0, 0, 0), (self.width, 0, 0), (0.5, 0, 0)])
        self.manipulators[1].set_pts([(0, 0, 0), (0, self.length, 0), (-0.5, 0, 0)])

        if self.floor_material == "wood":
            self.manipulators[2].prop1_name = "board_length"
            self.manipulators[2].set_pts([(0, 0, 0), (0, self.board_length, 0), (-0.2, 0, 0)])

            self.manipulators[3].prop1_name = "board_width"
            self.manipulators[3].set_pts([(0, 0, self.thickness), (self.board_width, 0, self.thickness), (-0.2, 0, 0)])
        else:
            self.manipulators[2].prop1_name = "tile_length"
            self.manipulators[2].set_pts([(0, 0, 0), (0, self.tile_length, 0), (-0.2, 0, 0)])

            self.manipulators[3].prop1_name = "tile_width"
            self.manipulators[3].set_pts([(0, 0, self.thickness), (self.tile_width, 0, self.thickness), (-0.2, 0, 0)])

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

        layout.prop(props, 'floor_material')

        if props.floor_material == "wood":
            layout.prop(props, 'wood_style')
        elif props.floor_material == 'tile':
            layout.prop(props, 'tile_style')

        layout.prop(props, 'width')
        layout.prop(props, 'length')
        layout.prop(props, 'thickness')
        layout.operator("archipack.floor_manipulate")

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

        # setup manipulators for on screen editing
        s = d.manipulators.add()
        s.prop1_name = "width"

        s = d.manipulators.add()
        s.prop1_name = "length"

        # these will be used for length and width respectively, but the property they link to will change based
        # on whether the floor material is tile or wood, whether we are using short_board_length or the normal, etc.
        # these are changed in archipack_floor.update()
        s = d.manipulators.add()
        s.prop1_name = "board_length"

        s = d.manipulators.add()
        s.prop1_name = "board_width"

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
# Define operator class to manipulate object
# ------------------------------------------------------------------


class ARCHIPACK_OT_floor_manipulate(Operator):
    bl_idname = "archipack.floor_manipulate"
    bl_label = "Manipulate"
    bl_description = "Manipulate"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
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
    bpy.utils.register_class(ARCHIPACK_OT_floor)
    bpy.utils.register_class(ARCHIPACK_PT_floor)
    bpy.utils.register_class(TOOLS_PT_parametric_object)
    Mesh.archipack_floor = CollectionProperty(type=archipack_floor)


def unregister():
    bpy.utils.unregister_class(archipack_floor)
    bpy.utils.unregister_class(ARCHIPACK_OT_floor_manipulate)
    bpy.utils.unregister_class(ARCHIPACK_OT_floor)
    bpy.utils.unregister_class(ARCHIPACK_PT_floor)
    bpy.utils.unregister_class(TOOLS_PT_parametric_object)
    del Mesh.archipack_floor


if __name__ == "__main__":
    register()
