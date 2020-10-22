# Mark sequence, copyright (C) 2020 Les Fées Spéciales
# voeu@les-fees-speciales.coop
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


bl_info = {
    "name": "LFS Layout Render",
    "author": "Les Fées Spéciales",
    "version": (1, 0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Tools > LFS",
    "description": "Layout playblast with right info",
    "category": "LFS"}


import bpy
import os
import tempfile
from mark_sequence import SequenceMarker


class LFS_OT_Playblast(bpy.types.Operator):
    '''Group multiple plane layers from current camera into one'''
    bl_idname = "lfs.playblast"
    bl_label = "Playblast"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        with tempfile.TemporaryDirectory() as tmpdir:
            render = context.scene.render

            # Store original render settings
            orig_filepath = render.filepath
            orig_use_file_extension = render.use_file_extension
            orig_file_format = render.image_settings.file_format
            orig_color_depth = render.image_settings.color_depth

            # Setup render settings
            render.filepath = os.path.join(tmpdir, "tmp_image.")
            render.use_file_extension = True
            render.image_settings.file_format = 'TIFF'
            render.image_settings.color_depth = '8'
            space = context.space_data
            region_3d = space.region_3d

            # Define marker data
            data = {"video_output": os.path.join(bpy.path.abspath('//'), 'playblast.mov'),
                    "resolution_x": render.resolution_x,
                    "resolution_y": render.resolution_y,
                    "start_frame": context.scene.frame_start,
                    "end_frame": context.scene.frame_end,
                    "offset": 0,
                    "project": "The Siren",
                    "resolution": "%s×%s" % (render.resolution_x, render.resolution_y),
                    # Focal length is dependent upon 3D view state
                    "focal_length": (context.scene.camera.data.lens
                                     if region_3d.view_perspective == 'CAMERA'
                                     else space.lens),
                    "file_name": os.path.basename(bpy.data.filepath),
            }

            # Render animation from viewport
            bpy.ops.render.opengl(animation=True)

            sequence_marker = SequenceMarker(os.path.join(tmpdir, "tmp_image.0000.tif"),
                                             data)
            sequence_marker.mark_sequence()

            # Restore original render settings
            render.filepath = orig_filepath
            render.use_file_extension = orig_use_file_extension
            render.image_settings.file_format = orig_file_format
            render.image_settings.color_depth = orig_color_depth

        return {'FINISHED'}

    # TODO execute marking in modal in background?
    # def modal(self, context):
    #     return {'FINISHED'}


class LFS_PT_Playblast(bpy.types.Panel):
    ''''''
    bl_label = "Playblast"
    bl_category = 'Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LFS"

    def draw(self, context):
        col = self.layout.column()
        col.operator("lfs.playblast", icon="RENDER_ANIMATION")


classes = (LFS_OT_Playblast, LFS_PT_Playblast)


register, unregister = bpy.utils.register_classes_factory(classes)


if __name__ == '__main__':
    register()
