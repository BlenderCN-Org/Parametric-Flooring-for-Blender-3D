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
from bpy.props import FloatProperty, CollectionProperty
from mathutils import Vector
from .bmesh_utils import BmeshEdit
from .simple_manipulator import Manipulable


# ------------------------------------------------------------------
# Define property class to store object parameters and update mesh
# ------------------------------------------------------------------


def update(self, context):
    self.update(context)


class archipack_floor(Manipulable, PropertyGroup):

    x = FloatProperty(
            name='width',
            min=0.25, max=10000,
            default=100.0, precision=2,
            description='Width', update=update,
            )
    y = FloatProperty(
            name='depth',
            min=0.1, max=10000,
            default=0.80, precision=2,
            description='Depth', update=update,
            )
    z = FloatProperty(
            name='height',
            min=0.1, max=10000,
            default=2.0, precision=2,
            description='Height', update=update,
            )

    @property
    def verts(self):
        """
            Object vertices coords
        """
        x = self.x
        y = self.y
        z = self.z
        return [
            (0, y, 0),
            (0, 0, 0),
            (x, 0, 0),
            (x, y, 0),
            (0, y, z),
            (0, 0, z),
            (x, 0, z),
            (x, y, z)
        ]

    @property
    def faces(self):
        """
            Object faces vertices index
        """
        return [
            (0, 1, 2, 3),
            (7, 6, 5, 4),
            (7, 4, 0, 3),
            (4, 5, 1, 0),
            (5, 6, 2, 1),
            (6, 7, 3, 2)
        ]

    @property
    def uvs(self):
        """
            Object faces uv coords
        """
        return [
            [(0, 0), (0, 1), (1, 1), (1, 0)],
            [(0, 0), (0, 1), (1, 1), (1, 0)],
            [(0, 0), (0, 1), (1, 1), (1, 0)],
            [(0, 0), (0, 1), (1, 1), (1, 0)],
            [(0, 0), (0, 1), (1, 1), (1, 0)],
            [(0, 0), (0, 1), (1, 1), (1, 0)]
        ]

    @property
    def matids(self):
        """
            Object material indexes
        """
        return [0, 0, 0, 0, 0, 0]

    def update(self, context):

        old = context.active_object

        o, props = ARCHIPACK_PT_floor.params(old)
        if props != self:
            return

        o.select = True
        context.scene.objects.active = o

        BmeshEdit.buildmesh(context, o, self.verts, self.faces, matids=self.matids, uvs=self.uvs)

        # setup 3d points for gl manipulators
        self.manipulators[0].set_pts([(0, 0, 0), (self.x, 0, 0), (1, 0, 0)])
        self.manipulators[1].set_pts([(0, 0, 0), (0, self.y, 0), (-1, 0, 0)])
        self.manipulators[2].set_pts([(self.x, 0, 0), (self.x, 0, self.z), (-1, 0, 0)])

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
        layout.prop(props, 'x')
        layout.prop(props, 'y')
        layout.prop(props, 'z')
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

    x = FloatProperty(
            name='width',
            min=0.1, max=10000,
            default=0.80, precision=2,
            description='Width'
            )
    y = FloatProperty(
            name='depth',
            min=0.1, max=10000,
            default=0.80, precision=2,
            description='Depth'
            )
    z = FloatProperty(
            name='height',
            min=0.1, max=10000,
            default=2.0, precision=2,
            description='height'
            )

    def create(self, context):
        """
            expose only basic params in operator
            use object property for other params
        """
        m = bpy.data.meshes.new("Floor")
        o = bpy.data.objects.new("Floor", m)

        # attach parametric datablock
        d = m.archipack_floor.add()

        # update params
        d.x = self.x
        d.y = self.y
        d.z = self.z

        # setup manipulators for on screen editing
        s = d.manipulators.add()
        s.prop1_name = "x"
        s = d.manipulators.add()
        s.prop1_name = "y"
        s = d.manipulators.add()
        s.normal = Vector((0, 1, 0))
        s.prop1_name = "z"

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
