# Mark sequence, copyright (C) 2020-2024 Les Fées Spéciales
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
    "version": (1, 1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > View Menu",
    "description": "Playblast with right info",
    "wiki_url": "https://gitlab.com/lfs.coop/mark-sequence",
    "tracker_url": "https://gitlab.com/lfs.coop/mark-sequence/-/issues",
    "category": "LFS"}


import bpy
import os
import tempfile
import json
from time import time

from .mark_sequence import SequenceMarker



def find_area(context):
    if (context.area is not None
            and context.area.type == 'VIEW_3D'):
        return context.area
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            return area
    return None


def find_region_3d(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            return area.spaces[0].region_3d
    return None


def find_space(context):
    if (context.space_data is not None
            and context.space_data.type == 'VIEW_3D'):
        return context.space_data
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            return area.spaces[0]
    return None


def proxify(img, target_width):
    if 'is_proxy' in img:
        if img['is_proxy'] and img.size[0] != target_width:
            deproxify(img)
        else:
            return

    img['is_proxy'] = True

    dest = target_width
    w, h = img.size
    h *= dest / w
    w = dest
    img.scale(w, h)
    img.gl_free()  # Force image update?


def proxify_images(context, target_width):
    images_to_process = {img for img in bpy.data.images if img.source in {'TILED', 'FILE'} and img.size[0] > target_width}

    number_imgs = len(images_to_process)
    context.window_manager.progress_begin(1, number_imgs)

    for i, img in enumerate(images_to_process):
        print("Proxy: processing image {:03} of {:03} : {}".format(
            i + 1, number_imgs, img.name))
        context.window_manager.progress_update(i + 1)
        proxify(img, target_width)

    print("Proxy: done.")
    context.window_manager.progress_end()


class LFS_OT_Playblast(bpy.types.Operator):
    '''Group multiple plane layers from current camera into one'''
    bl_idname = "lfs.playblast"
    bl_label = "Playblast"
    bl_options = {'REGISTER', 'PRESET'}

    filepath: bpy.props.StringProperty(maxlen=1024, subtype='FILE_PATH',
                             options={'HIDDEN', 'SKIP_SAVE'})
    filename_ext = ".mov"
    filter_glob: bpy.props.StringProperty(
        default="*.mov",
        options={'HIDDEN'})

    do_render: bpy.props.BoolProperty(name="Do Render", description="Use real render instead of viewport preview")
    do_hide_overlays: bpy.props.BoolProperty(name="Hide Overlays", description="Hide overlays in the viewport preview", default=True)
    do_export_audio: bpy.props.BoolProperty(name="Export Audio", description="Export the audio from the VSE as audio track", default=True)
    quality: bpy.props.EnumProperty(name="Quality", items=(('PREVIEW', "Preview", ""),
                                                           ('FINAL', "Final", "")),
                                    description="Use quality presets for the render settings", default='FINAL')

    do_single_layer: bpy.props.BoolProperty(name="Single Layer", description="Disable all layers but the one called View Layer, or the active one. If it is not found, keep the current one only", default=False)
    do_reduce_textures: bpy.props.BoolProperty(name="Reduce Textures", description="Reduce texture sizes before render, to reduce memory footprint", default=False)
    target_texture_width: bpy.props.IntProperty(name="Target Texture Width", description="Reduce textures greater than this width, to this width", default=4096)
    resolution_percentage: bpy.props.IntProperty(name="Resolution Percentage", description="Scale the render resolution according to this percentage", default=100)

    studio: bpy.props.StringProperty(name="Studio", description="Studio name")
    project: bpy.props.StringProperty(name="Project", description="Project name")
    sequence: bpy.props.StringProperty(name="Sequence", description="Sequence number")
    scene: bpy.props.StringProperty(name="Shot", description="Shot number")
    version: bpy.props.StringProperty(name="Version", description="Version of the shot")

    template_path: bpy.props.StringProperty(name="Template", description="Custom marking field template", maxlen=1024)

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        start_time = time()
        with tempfile.TemporaryDirectory() as tmpdir:
            render = context.scene.render
            area = find_area(context)
            space = area.spaces[0]

            if hasattr(space, 'region_3d'):
                region_3d = space.region_3d
            else:
                region_3d = find_region_3d(context)

            # Reduce texture sizes
            if self.do_reduce_textures:
                print("Reducing textures")
                proxify_images(context, self.target_texture_width)

            # Store original render settings
            orig_filepath = render.filepath
            orig_use_file_extension = render.use_file_extension
            orig_file_format = render.image_settings.file_format
            orig_color_depth = render.image_settings.color_depth
            orig_resolution_percentage = render.resolution_percentage
            orig_simplify = render.use_simplify
            orig_simplify_subdivision = render.simplify_subdivision
            orig_simplify_subdivision_render = render.simplify_subdivision_render
            orig_taa_render_samples = context.scene.eevee.taa_render_samples
            orig_taa_samples = context.scene.eevee.taa_samples

            # TODO: Store workbench settings in preview quality mode

            orig_gl_texture_limit = context.preferences.system.gl_texture_limit
            if space is not None:
                orig_overlay = space.overlay.show_overlays
            view_layer_visibilities = {}
            collection_viewport_visibility = {}
            object_viewport_visibility = {}
            if self.do_render:
                if self.do_single_layer:
                    for layer in context.scene.view_layers:
                        view_layer_visibilities[layer.name] = layer.use
            else:
                for c in bpy.data.collections:
                    collection_viewport_visibility[c.name] = c.hide_viewport
                for o in bpy.data.objects:
                    object_viewport_visibility[o.name] = o.hide_viewport

            orig_use_stamp = context.scene.render.use_stamp

            # Setup render settings
            render.filepath = os.path.join(tmpdir, "tmp_image.")
            render.resolution_percentage = 100
            render.use_file_extension = True
            render.image_settings.file_format = 'TIFF'
            render.image_settings.color_depth = '8'
            render.resolution_percentage = self.resolution_percentage
            render.use_simplify = (self.quality == 'PREVIEW')
            render.simplify_subdivision = 1
            render.simplify_subdivision_render = 1
            render.simplify_child_particles_render = 0.0

            if self.quality == 'PREVIEW':
                render.engine = 'BLENDER_EEVEE'
                # Take camera's point of view
                space.region_3d.view_perspective = 'CAMERA'
                # Set shading to material preview
                space.shading.type = 'MATERIAL'
                # Disable overlays
                space.overlay.show_overlays = True
                space.overlay.show_ortho_grid = False
                space.overlay.show_floor = False
                space.overlay.show_axis_x = False
                space.overlay.show_axis_y = False
                space.overlay.show_axis_z = False
                space.overlay.show_cursor = False
                space.overlay.show_extras = False
                space.overlay.show_bones = False
                space.overlay.show_relationship_lines = False
                space.overlay.show_motion_paths = False
                space.overlay.show_outline_selected = False
                space.overlay.show_object_origins = False
                # Configure camera background image
                context.scene.camera.data.show_background_images = True
                if len(context.scene.camera.data.background_images) > 0:
                    img = context.scene.camera.data.background_images[0]
                    img.alpha = 1.0
                    img.display_depth = 'BACK'
                    img.frame_method = 'STRETCH'

                # Transfer render visibility to viewport visibility
                for c in bpy.data.collections:
                    c.hide_viewport = c.hide_render
                for o in bpy.data.objects:
                    o.hide_viewport = o.hide_render

                # Use a low number of samples
                context.scene.eevee.taa_samples = 4

            # Disable metadata burning
            context.scene.render.use_stamp = False

            if self.do_render and self.do_hide_overlays and space is not None:
                space.overlay.show_overlays = False
            if self.do_render and self.do_single_layer:
                for layer in context.scene.view_layers:
                    if "View Layer" in context.scene.view_layers:
                        layer.use = (layer.name == 'View Layer')
                    else:
                        layer.use = (layer == context.view_layer)

            out_name = self.filepath
            dir_path = os.path.dirname(out_name)

            os.makedirs(dir_path, exist_ok=True)

            # Set current frame to first frame. Workaround GP bug at
            # https://developer.blender.org/T85035
            context.scene.frame_set(context.scene.frame_end)

            # Get animated lens and f-stop, store it into a dict
            lens = {}
            fstop = {}
            previous_frame = context.scene.frame_current
            for f in range(context.scene.frame_start, context.scene.frame_end+1):
                context.scene.frame_set(f)
                # Focal length is dependent upon 3D view state
                fstop[f] = f"{context.scene.camera.data.dof.aperture_fstop:.3}"
                if self.do_render:
                    lens[f] = context.scene.camera.data.lens
                else:
                    lens[f] = (context.scene.camera.data.lens
                               if region_3d is not None
                                  and region_3d.view_perspective == 'CAMERA'
                               else space.lens)
                # Skip decimal precision, we probably don't need that
                lens[f] = round(lens[f])
            context.scene.frame_set(previous_frame)


            # Define marker data
            data = {"video_output": out_name,
                    "resolution_x": render.resolution_x * render.resolution_percentage // 100,
                    "resolution_y": render.resolution_y * render.resolution_percentage // 100,
                    "start_frame": context.scene.frame_start,
                    "end_frame": context.scene.frame_end,
                    "offset": 0,
                    "project": "",
                    "version": "",
                    "resolution": "%s×%s" % (render.resolution_x * render.resolution_percentage // 100,
                                             render.resolution_y * render.resolution_percentage // 100),
                    "focal_length": lens,
                    "fstop": fstop,
                    "file_name": os.path.basename(bpy.data.filepath),
                    "audio_file": None,
                    "frame_rate": render.fps / render.fps_base,
                    "quality": "Quality: " + self.quality
            }

            # Get data from environment variables
            # TODO automate list of vars to look up
            for field in ("studio", "project", "sequence", "scene", "version"):
                if getattr(self, field):
                    data[field] = getattr(self, field)
                elif field in os.environ:
                    data[field] = os.environ[field]

            # Load in template from supplied json file. If none given, use default one.
            if self.template_path:
                with open(os.path.abspath(self.template_path), 'r') as f:
                    template = json.load(f)
            else:
                template = None

            # Render animation from viewport
            if self.do_render:
                bpy.ops.render.render(animation=True)
            else:
                # bpy.ops.render.opengl(animation=True, view_context=False)
                with bpy.context.temp_override(area=area):
                    bpy.ops.render.opengl(animation=True)

            # Export Audio if needed
            if self.do_export_audio:
                print("Exporting Audio")
                audio_path = os.path.join(tmpdir, "sound.mp3")
                bpy.ops.sound.mixdown(filepath=audio_path,
                    relative_path=False,
                    container='MP3',
                    codec='MP3',
                    format='S32',
                    bitrate=256,
                    accuracy=512)
                data["audio_file"] = audio_path

            # Start sequence marker and movie creation

            sequence_marker = SequenceMarker(os.path.join(tmpdir, "tmp_image.0000.tif"),
                                             data, template)
            sequence_marker.mark_sequence()

            # Restore original render settings
            render.filepath = orig_filepath
            render.use_file_extension = orig_use_file_extension
            render.image_settings.file_format = orig_file_format
            render.image_settings.color_depth = orig_color_depth
            render.resolution_percentage = orig_resolution_percentage
            render.use_simplify = orig_simplify
            render.simplify_subdivision = orig_simplify_subdivision
            render.simplify_subdivision_render = orig_simplify_subdivision_render
            context.scene.eevee.taa_render_samples = orig_taa_render_samples
            context.scene.eevee.taa_samples = orig_taa_samples
            context.preferences.system.gl_texture_limit = orig_gl_texture_limit
            if self.do_render and space is not None:
                space.overlay.show_overlays = orig_overlay
            if self.do_render:
                if self.do_single_layer:
                    for layer in context.scene.view_layers:
                        layer.use = view_layer_visibilities[layer.name]
            else:
                for c in bpy.data.collections:
                    c.hide_viewport = collection_viewport_visibility[c.name]
                for o in bpy.data.objects:
                    o.hide_viewport = object_viewport_visibility[o.name]

            context.scene.render.use_stamp = orig_use_stamp

            print("Rendered playblast in %01.1fs" % (time() - start_time))
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "do_render")
        row = col.row()
        row.active = self.do_render
        row.prop(self, "do_single_layer")
        col.prop(self, "do_hide_overlays")
        # col.prop(self, "do_simplify")
        col.prop(self, "quality")
        col.prop(self, "do_reduce_textures")
        col.prop(self, "do_export_audio")
        col.prop(self, "resolution_percentage")

        col = layout.column(align=True)
        col.prop(self, "studio")
        col.prop(self, "project")
        col.prop(self, "sequence")
        col.prop(self, "scene")
        col.prop(self, "version")
        col.prop(self, "template_path")

    # TODO execute marking in modal in background?
    # def modal(self, context):
    #     return {'FINISHED'}


class LFS_OT_Viewport_Playblast(bpy.types.Operator):
    '''Quick render in the viewport'''
    bl_idname = "lfs.viewport_playblast"
    bl_label = "Playblast"
    bl_options = {'REGISTER', 'PRESET'}

    filepath: bpy.props.StringProperty(maxlen=1024, subtype='FILE_PATH',
                             options={'HIDDEN', 'SKIP_SAVE'})
    filename_ext = ".mov"
    filter_glob: bpy.props.StringProperty(
        default="*.mov",
        options={'HIDDEN'})

    do_render: bpy.props.BoolProperty(name="Do Render", description="Use real render instead of viewport preview")
    do_single_layer: bpy.props.BoolProperty(name="Single Layer", description="Disable all layers but the one called View Layer, or the active one. If it is not found, keep the current one only", default=False)
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )

    def invoke(self, context, _event):
        self.filepath = bpy.data.filepath.replace(".blend", "_movie.mov").replace("_blend", "_movie_mov")
        os.makedirs(os.path.dirname(os.path.abspath(bpy.path.abspath(self.filepath))), exist_ok=True)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        render = context.scene.render
        space = find_space(context)

        if hasattr(space, 'region_3d'):
            region_3d = space.region_3d
        else:
            region_3d = find_region_3d(context)

        overlay_settings = [
            # 'show_overlays', 'show_extras',
            'show_annotation', 'show_axis_x', 'show_axis_y',
            'show_axis_z', 'show_bones', 'show_cursor', 'show_curve_normals',
            'show_edge_bevel_weight', 'show_edge_crease', 'show_edge_seams',
            'show_edge_sharp', 'show_edges', 'show_extra_edge_angle',
            'show_extra_edge_length', 'show_extra_face_angle',
            'show_extra_face_area', 'show_extra_indices',
            'show_face_center', 'show_face_normals', 'show_face_orientation',
            'show_faces', 'show_fade_inactive', 'show_floor',
            'show_freestyle_edge_marks', 'show_freestyle_face_marks',
            'show_light_colors', 'show_look_dev', 'show_motion_paths',
            'show_object_origins', 'show_object_origins_all',
            'show_onion_skins', 'show_ortho_grid', 'show_outline_selected',
            'show_paint_wire', 'show_relationship_lines',
            'show_retopology', 'show_sculpt_curves_cage',
            'show_sculpt_face_sets', 'show_sculpt_mask', 'show_split_normals',
            'show_stats', 'show_statvis', 'show_text', 'show_vertex_normals',
            'show_viewer_attribute', 'show_weight', 'show_wireframes',
            'show_wpaint_contours', 'show_xray_bone',
        ]

        show_settings = [
            # 'show_object_viewport_mesh', 'show_object_viewport_curve',
            # 'show_object_viewport_curves', 'show_object_viewport_empty',
            'show_object_viewport_armature', 'show_object_viewport_camera',
            'show_object_viewport_font', 'show_object_viewport_grease_pencil',
            'show_object_viewport_lattice', 'show_object_viewport_light',
            'show_object_viewport_light_probe', 'show_object_viewport_meta',
            'show_object_viewport_pointcloud', 'show_object_viewport_speaker',
            'show_object_viewport_surf', 'show_object_viewport_volume',
        ]

        # Store original render settings
        orig_filepath = render.filepath
        orig_use_file_extension = render.use_file_extension
        orig_file_format = render.image_settings.file_format
        orig_color_depth = render.image_settings.color_depth
        orig_simplify = render.use_simplify
        orig_simplify_subdivision = render.simplify_subdivision
        orig_simplify_subdivision_render = render.simplify_subdivision_render
        orig_taa_render_samples = context.scene.eevee.taa_render_samples
        orig_taa_samples = context.scene.eevee.taa_samples
        orig_gl_texture_limit = context.preferences.system.gl_texture_limit
        orig_overlay_settings = {}
        orig_show_settings = {}
        if space is not None:
            orig_shading_light = space.shading.light
            orig_view_perspective = space.region_3d.view_perspective
            for setting in overlay_settings:
                orig_overlay_settings[setting] = getattr(space.overlay, setting)
            for setting in show_settings:
                orig_show_settings[setting] = getattr(space, setting)

        # Store original output settings
        orig_file_format = bpy.context.scene.render.image_settings.file_format
        orig_color_management = bpy.context.scene.render.image_settings.color_management
        orig_ffmpeg_format = bpy.context.scene.render.ffmpeg.format
        orig_ffmpeg_codec = bpy.context.scene.render.ffmpeg.codec
        orig_ffmpeg_constant_rate_factor = bpy.context.scene.render.ffmpeg.constant_rate_factor
        orig_ffmpeg_ffmpeg_preset = bpy.context.scene.render.ffmpeg.ffmpeg_preset
        orig_ffmpeg_audio_codec = bpy.context.scene.render.ffmpeg.audio_codec

        view_layer_visibilities = {}
        if self.do_render and self.do_single_layer:
            for layer in context.scene.view_layers:
                view_layer_visibilities[layer.name] = layer.use

        # Setup render settings
        render.filepath = self.filepath
        render.use_file_extension = True
        render.image_settings.color_depth = '8'
        render.simplify_subdivision = 0
        render.simplify_subdivision_render = 0
        context.scene.eevee.taa_render_samples = 16
        context.scene.eevee.taa_samples = 16
        if space is not None:
            space.shading.light = 'FLAT'
            space.region_3d.view_perspective = 'CAMERA'
            for setting in overlay_settings:
                setattr(space.overlay, setting, False)
            for setting in show_settings:
                setattr(space, setting, False)
        if self.do_render and self.do_single_layer:
            for layer in context.scene.view_layers:
                layer.use = (layer == context.view_layer)

        # Setup output settings
        render.image_settings.file_format = 'FFMPEG'
        render.image_settings.color_management = 'FOLLOW_SCENE'
        render.ffmpeg.format = 'QUICKTIME'
        render.ffmpeg.codec = 'H264'
        render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
        render.ffmpeg.ffmpeg_preset = 'GOOD'
        render.ffmpeg.audio_codec = 'AAC'

        out_name = self.filepath
        dir_path = os.path.dirname(out_name)

        # Render animation from viewport
        bpy.ops.render.opengl(animation=True)

        # Run animation playback
        bpy.ops.render.play_rendered_anim()

        # Restore original render settings
        render.filepath = orig_filepath
        render.use_file_extension = orig_use_file_extension
        render.image_settings.file_format = orig_file_format
        render.image_settings.color_depth = orig_color_depth
        render.use_simplify = orig_simplify
        render.simplify_subdivision = orig_simplify_subdivision
        render.simplify_subdivision_render = orig_simplify_subdivision_render
        context.scene.eevee.taa_render_samples = orig_taa_render_samples
        context.scene.eevee.taa_samples = orig_taa_samples
        context.preferences.system.gl_texture_limit = orig_gl_texture_limit
        if space is not None:
            space.shading.light = orig_shading_light
            space.region_3d.view_perspective = orig_view_perspective
            for setting in overlay_settings:
                setattr(space.overlay, setting, orig_overlay_settings[setting])
            for setting in show_settings:
                setattr(space, setting, orig_show_settings[setting])
        if self.do_render and self.do_single_layer:
            for layer in context.scene.view_layers:
                layer.use = view_layer_visibilities[layer.name]

        # Restore original output settings
        bpy.context.scene.render.image_settings.file_format = orig_file_format
        bpy.context.scene.render.image_settings.color_management = orig_color_management
        bpy.context.scene.render.ffmpeg.format = orig_ffmpeg_format
        bpy.context.scene.render.ffmpeg.codec = orig_ffmpeg_codec
        bpy.context.scene.render.ffmpeg.constant_rate_factor = orig_ffmpeg_constant_rate_factor
        bpy.context.scene.render.ffmpeg.ffmpeg_preset = orig_ffmpeg_ffmpeg_preset
        bpy.context.scene.render.ffmpeg.audio_codec = orig_ffmpeg_audio_codec
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "do_render")
        row = col.row()
        row.active = self.do_render
        row.prop(self, "do_single_layer")


def playblast_button(self, context):
    row = self.layout.row()
    self.layout.operator(LFS_OT_Viewport_Playblast.bl_idname, text="LFS Viewport Playblast", icon="RENDER_ANIMATION")
    self.layout.separator()

def register():
    bpy.utils.register_class(LFS_OT_Playblast)
    bpy.utils.register_class(LFS_OT_Viewport_Playblast)
    bpy.types.VIEW3D_MT_view.prepend(playblast_button)

def unregister():
    bpy.types.VIEW3D_MT_view.remove(playblast_button)
    bpy.utils.unregister_class(LFS_OT_Viewport_Playblast)
    bpy.utils.unregister_class(LFS_OT_Playblast)

if __name__ == '__main__':
    register()
