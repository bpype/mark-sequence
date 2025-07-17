# SPDX-FileCopyrightText: 2020-2025 Les Fées Spéciales
#
# SPDX-License-Identifier: GPL-2.0-or-later


bl_info = {
    "name": "LFS Playblast",
    "author": "Les Fées Spéciales",
    "version": (2, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > View Menu",
    "description": "Playblast with right info",
    "wiki_url": "https://gitlab.com/lfs.coop/mark-sequence",
    "tracker_url": "https://gitlab.com/lfs.coop/mark-sequence/-/issues",
    "category": "LFS",
}


import bpy
from bpy.app.translations import pgettext_data as data_
import os
import tempfile
import json
from time import time

from . import viewport_playblast
from .mark_sequence import SequenceMarker
from .utils.wm import find_area, find_region_3d, find_space
from .utils.image import proxify, proxify_images
from .utils.anim import get_frame_markers


class LFS_OT_Playblast(bpy.types.Operator):
    """Render playblast inside Blender"""
    bl_idname = "lfs.playblast"
    bl_label = "Playblast"
    bl_options = {'REGISTER', 'PRESET'}

    filepath: bpy.props.StringProperty(
        maxlen=1024, subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'}
    )
    filename_ext = ".mov"
    filter_glob: bpy.props.StringProperty(default="*.mov", options={'HIDDEN'})
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )

    do_render: bpy.props.BoolProperty(
        name="Do Render", description="Use real render instead of viewport preview"
    )
    do_hide_overlays: bpy.props.BoolProperty(
        name="Hide Overlays",
        description="Hide overlays in the viewport preview",
        default=True,
    )
    do_export_audio: bpy.props.BoolProperty(
        name="Export Audio",
        description="Export the audio from the VSE as audio track",
        default=True,
    )
    quality: bpy.props.EnumProperty(
        name="Quality",
        items=(('PREVIEW', "Preview", ""), ('FINAL', "Final", "")),
        description="Use quality presets for the render settings",
        default='FINAL',
    )

    do_single_layer: bpy.props.BoolProperty(
        name="Single Layer",
        description="Disable all layers but the one called View Layer, or the active one. If it is not found, keep the current one only",
        default=False,
    )
    do_reduce_textures: bpy.props.BoolProperty(
        name="Reduce Textures",
        description="Reduce texture sizes before render, to reduce memory footprint",
        default=False,
    )
    target_texture_width: bpy.props.IntProperty(
        name="Target Texture Width",
        description="Reduce textures greater than this width, to this width",
        default=4096,
    )
    resolution_percentage: bpy.props.IntProperty(
        name="Resolution Percentage",
        description="Scale the render resolution according to this percentage",
        default=100,
    )
    do_autoplay: bpy.props.BoolProperty(
        name="Autoplay",
        description="Auto Play playblast when render is finished",
        default=True,
    )

    studio: bpy.props.StringProperty(name="Studio", description="Studio name")
    project: bpy.props.StringProperty(name="Project", description="Project name")
    sequence: bpy.props.StringProperty(name="Sequence", description="Sequence number")
    scene: bpy.props.StringProperty(name="Shot", description="Shot number")
    version: bpy.props.StringProperty(name="Version", description="Version of the shot")
    frame_count: bpy.props.IntProperty(
        name="Kitsu Frames Count",
        description="Minimum number of frames for the shot as set on Kitsu",
        default=1,
    )

    template_path: bpy.props.StringProperty(name="Template", description="Custom marking field template", maxlen=1024)

    def invoke(self, context, _event):
        """Copied from ExportHelper"""
        import os
        if not self.filepath:
            blend_filepath = context.blend_data.filepath
            if not blend_filepath:
                blend_filepath = data_("Untitled")
            else:
                blend_filepath = os.path.splitext(blend_filepath)[0]

            self.filepath = bpy.path.ensure_ext(blend_filepath, ".mov")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        start_time = time()
        with tempfile.TemporaryDirectory() as tmpdir:
            render = context.scene.render
            area = find_area(context)
            space = area.spaces[0]

            if hasattr(space, "region_3d"):
                region_3d = space.region_3d
            else:
                region_3d = find_region_3d(context)

            # Reduce texture sizes
            if self.do_reduce_textures:
                print("Reducing textures")
                proxify_images(context, self.target_texture_width)

            # Compare scene frame count and frame count set on Kitsu
            frame_total = context.scene.frame_end - context.scene.frame_start + 1
            if self.frame_count > frame_total:
                self.report(
                    {'WARNING'},
                    f"File is missing {self.frame_count - frame_total} frames to render (Expected : {self.frame_count})",
                )

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

            orig_use_preview_range = context.scene.use_preview_range

            orig_use_sequencer = render.use_sequencer
            orig_use_stamp = render.use_stamp

            # Store original animatic statuses
            for sequence in context.scene.sequence_editor.sequences:
                if sequence.type == 'MOVIE':
                    sequence["_muted"] = sequence.mute
                    sequence.mute = True

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

            # Setup render settings
            render.filepath = os.path.join(tmpdir, "tmp_image.")
            render.resolution_percentage = 100
            render.use_file_extension = True
            render.image_settings.file_format = 'TIFF'
            render.image_settings.color_depth = '8'
            render.resolution_percentage = self.resolution_percentage
            render.use_simplify = self.quality == 'PREVIEW'
            render.simplify_subdivision = 1
            render.simplify_subdivision_render = 1
            render.simplify_child_particles_render = 0.0

            if self.quality == 'PREVIEW':
                render.engine = 'BLENDER_EEVEE_NEXT'
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
            render.use_sequencer = False
            render.use_stamp = False

            if self.do_render and self.do_hide_overlays and space is not None:
                space.overlay.show_overlays = False
            if self.do_render and self.do_single_layer:
                for layer in context.scene.view_layers:
                    if "View Layer" in context.scene.view_layers:
                        layer.use = (layer.name == "View Layer")
                    else:
                        layer.use = (layer == context.view_layer)

            out_name = self.filepath
            dir_path = os.path.dirname(out_name)

            os.makedirs(dir_path, exist_ok=True)

            context.scene.use_preview_range = False

            # Get animated properties, store them in a dict
            lens = {}
            fstop = {}
            markers = get_frame_markers(context)
            previous_frame = context.scene.frame_current
            for f in range(context.scene.frame_start, context.scene.frame_end + 1):
                context.scene.frame_set(f)
                # Focal length is dependent upon 3D view state
                fstop[f] = f"{context.scene.camera.data.dof.aperture_fstop:.3}"
                if self.do_render:
                    lens[f] = context.scene.camera.data.lens
                else:
                    lens[f] = (
                        context.scene.camera.data.lens
                        if region_3d is not None
                        and region_3d.view_perspective == 'CAMERA'
                        else space.lens
                    )
                # Skip decimal precision, we probably don't need that
                lens[f] = round(lens[f])

            context.scene.frame_set(previous_frame)

            # Define marker data
            data = {
                "video_output": out_name,
                "resolution_x": render.resolution_x * render.resolution_percentage // 100,
                "resolution_y": render.resolution_y * render.resolution_percentage // 100,
                "start_frame": context.scene.frame_start,
                "end_frame": context.scene.frame_end,
                "offset": 0,
                "project": "",
                "version": "",
                "resolution": "%s×%s" % (render.resolution_x * render.resolution_percentage // 100,
                                         render.resolution_y * render.resolution_percentage // 100,
                ),
                "focal_length": lens,
                "fstop": fstop,
                "timeline_marker": markers,
                "file_name": os.path.basename(bpy.data.filepath),
                "audio_file": None,
                "frame_rate": render.fps / render.fps_base,
                "quality": "Quality: " + self.quality,
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
                with open(os.path.abspath(self.template_path), "r") as f:
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
                bpy.ops.sound.mixdown(
                    filepath=audio_path,
                    relative_path=False,
                    container='MP3',
                    codec='MP3',
                    format='S32',
                    bitrate=256,
                    accuracy=512,
                )
                data["audio_file"] = audio_path

            # Start sequence marker and movie creation

            sequence_marker = SequenceMarker(
                os.path.join(tmpdir, "tmp_image.0000.tif"), data, template
            )
            sequence_marker.mark_sequence()

            if self.do_autoplay:
                sequence_marker.play_movie()

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
            context.scene.use_preview_range = orig_use_preview_range

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

            # Restore original animatic statuses
            for sequence in context.scene.sequence_editor.sequences:
                if sequence.type == 'MOVIE':
                    sequence.mute = sequence["_muted"]
                    del sequence["_muted"]

            render.use_sequencer = orig_use_sequencer
            render.use_stamp = orig_use_stamp

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

        col = layout.column(align=True)
        col.prop(self, "template_path")

    # TODO execute marking in modal in background?
    # def modal(self, context):
    #     return {'FINISHED'}


def register():
    bpy.utils.register_class(LFS_OT_Playblast)
    viewport_playblast.register()


def unregister():
    viewport_playblast.unregister()
    bpy.utils.unregister_class(LFS_OT_Playblast)


if __name__ == "__main__":
    register()
