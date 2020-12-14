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
    "name": "LFS Playblast",
    "author": "Les Fées Spéciales",
    "version": (1, 0, 2),
    "blender": (2, 80, 0),
    "location": "View3D > Tools > LFS",
    "description": "Playblast with right info",
    "wiki_url": "https://gitlab.com/lfs.coop/mark-sequence",
    "tracker_url": "https://gitlab.com/lfs.coop/mark-sequence/-/issues",
    "category": "LFS"}


import bpy
import os
import tempfile
from .mark_sequence import SequenceMarker
from time import time



def find_space(context):
    if context.space_data == 'VIEW_3D':
        return context.space_data
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            return area.spaces[0]
    return None


def find_region_3d(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            return area.spaces[0].region_3d
    return None


class LFS_OT_Playblast(bpy.types.Operator):
    '''Group multiple plane layers from current camera into one'''
    bl_idname = "lfs.playblast"
    bl_label = "Playblast"
    bl_options = {'REGISTER', 'UNDO'}

    do_render: bpy.props.BoolProperty(name="Do Render", description="Use real render instead of viewport preview")

    studio: bpy.props.StringProperty(name="Studio", description="Studio name")
    project: bpy.props.StringProperty(name="Project", description="Project name")
    scene: bpy.props.StringProperty(name="Scene", description="Scene number")
    sequence: bpy.props.StringProperty(name="Sequence", description="Sequence number")

    def execute(self, context):
        start_time = time()
        with tempfile.TemporaryDirectory() as tmpdir:
            render = context.scene.render
            space = find_space(context)

            if hasattr(space, 'region_3d'):
                region_3d = space.region_3d
            else:
                region_3d = find_region_3d(context)

            # Store original render settings
            orig_filepath = render.filepath
            orig_use_file_extension = render.use_file_extension
            orig_file_format = render.image_settings.file_format
            orig_color_depth = render.image_settings.color_depth
            orig_overlay = space.overlay.show_overlays
            orig_taa_render_samples = context.scene.eevee.taa_render_samples
            orig_taa_samples = context.scene.eevee.taa_samples

            # Setup render settings
            render.filepath = os.path.join(tmpdir, "tmp_image.")
            render.use_file_extension = True
            render.image_settings.file_format = 'TIFF'
            render.image_settings.color_depth = '8'
            space.overlay.show_overlays = False
            context.scene.eevee.taa_render_samples = 4
            context.scene.eevee.taa_samples = 4

            # Get output filepath
            dir_path, file_name = os.path.split(bpy.data.filepath)
            dir_path += "-movie"
            out_name, _ext = os.path.splitext(file_name)
            out_name += ".mov"

            os.makedirs(dir_path, exist_ok=True)

            # Define marker data
            data = {"video_output": os.path.join(dir_path, out_name),
                    "resolution_x": render.resolution_x * render.resolution_percentage // 100,
                    "resolution_y": render.resolution_y * render.resolution_percentage // 100,
                    "start_frame": context.scene.frame_start,
                    "end_frame": context.scene.frame_end,
                    "offset": 0,
                    "project": "",
                    "resolution": "%s×%s" % (render.resolution_x * render.resolution_percentage // 100,
                                             render.resolution_y * render.resolution_percentage // 100),
                    # Focal length is dependent upon 3D view state
                    "focal_length": (context.scene.camera.data.lens
                                     if region_3d is not None and region_3d.view_perspective == 'CAMERA'
                                     else space.lens),
                    "file_name": os.path.basename(bpy.data.filepath),
            }

            # Get data from environment variables
            # TODO automate list of vars to look up
            for field in ("studio", "project", "sequence", "scene"):
                if getattr(self, field):
                    data[field] = getattr(self, field)
                elif field in os.environ:
                    data[field] = os.environ[field]

            # Render animation from viewport
            if self.do_render:
                bpy.ops.render.render(animation=True)
            else:
                # bpy.ops.render.opengl(animation=True, view_context=False)
                bpy.ops.render.opengl(animation=True)

            sequence_marker = SequenceMarker(os.path.join(tmpdir, "tmp_image.0000.tif"),
                                             data)
            sequence_marker.mark_sequence()

            # Restore original render settings
            render.filepath = orig_filepath
            render.use_file_extension = orig_use_file_extension
            render.image_settings.file_format = orig_file_format
            render.image_settings.color_depth = orig_color_depth
            space.overlay.show_overlays = orig_overlay
            context.scene.eevee.taa_render_samples = orig_taa_render_samples
            context.scene.eevee.taa_samples = orig_taa_samples

            print("Rendered playblast in %01.1fs" % (time() - start_time))
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
        row = self.layout.row(align=True)
        row.operator("lfs.playblast", icon="RENDER_ANIMATION")
        # row.operator("lfs.playblast", icon="RENDER_ANIMATION", text="Render").do_render = True


classes = (LFS_OT_Playblast, LFS_PT_Playblast)


register, unregister = bpy.utils.register_classes_factory(classes)


if __name__ == '__main__':
    register()
