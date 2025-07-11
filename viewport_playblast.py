# SPDX-FileCopyrightText: 2020-2025 Les Fées Spéciales
#
# SPDX-License-Identifier: GPL-2.0-or-later


import bpy
import os

from .utils.wm import find_region_3d, find_space


class LFS_OT_Viewport_Playblast(bpy.types.Operator):
    """Quick render in the viewport"""

    bl_idname = "lfs.viewport_playblast"
    bl_label = "Viewport Playblast"
    bl_options = {'REGISTER', 'PRESET'}

    filepath: bpy.props.StringProperty(
        maxlen=1024, subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'}
    )
    filter_glob: bpy.props.StringProperty(default="*.mov", options={'HIDDEN'})
    filename_ext = ".mov"
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )

    do_render: bpy.props.BoolProperty(
        name="Do Render", description="Use real render instead of viewport preview"
    )
    do_single_layer: bpy.props.BoolProperty(
        name="Single Layer",
        description="Disable all layers but the one called View Layer, or the active one. If it is not found, keep the current one only",
        default=False,
    )
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )

    @staticmethod
    def update(scene):
        scene.render.stamp_note_text = (
            f"F-Stop: {scene.camera.data.dof.aperture_fstop:3.3}"
        )

    def invoke(self, context, _event):
        self.filepath = bpy.data.filepath.replace(".blend", "_movie.mov").replace(
            "_blend", "_movie_mov"
        )
        os.makedirs(
            os.path.dirname(os.path.abspath(bpy.path.abspath(self.filepath))),
            exist_ok=True,
        )
        return self.execute(context)

    def execute(self, context):
        render = context.scene.render
        space = find_space(context)

        if hasattr(space, "region_3d"):
            region_3d = space.region_3d
        else:
            region_3d = find_region_3d(context)

        overlay_settings = [
            # 'show_overlays', 'show_extras',
            "show_annotation",
            "show_axis_x",
            "show_axis_y",
            "show_axis_z",
            "show_bones",
            "show_cursor",
            "show_curve_normals",
            "show_edge_bevel_weight",
            "show_edge_crease",
            "show_edge_seams",
            "show_edge_sharp",
            "show_extra_edge_angle",
            "show_extra_edge_length",
            "show_extra_face_angle",
            "show_extra_face_area",
            "show_extra_indices",
            "show_face_center",
            "show_face_normals",
            "show_face_orientation",
            "show_faces",
            "show_fade_inactive",
            "show_floor",
            "show_freestyle_edge_marks",
            "show_freestyle_face_marks",
            "show_light_colors",
            "show_look_dev",
            "show_motion_paths",
            "show_object_origins",
            "show_object_origins_all",
            "show_onion_skins",
            "show_ortho_grid",
            "show_outline_selected",
            "show_paint_wire",
            "show_relationship_lines",
            "show_retopology",
            "show_sculpt_curves_cage",
            "show_sculpt_face_sets",
            "show_sculpt_mask",
            "show_split_normals",
            "show_stats",
            "show_statvis",
            "show_text",
            "show_vertex_normals",
            "show_viewer_attribute",
            "show_weight",
            "show_wireframes",
            "show_wpaint_contours",
            "show_xray_bone",
        ]

        show_settings = [
            # 'show_object_viewport_mesh', 'show_object_viewport_curve',
            # 'show_object_viewport_curves', 'show_object_viewport_empty',
            "show_object_viewport_armature",
            "show_object_viewport_camera",
            "show_object_viewport_font",
            "show_object_viewport_grease_pencil",
            "show_object_viewport_lattice",
            "show_object_viewport_light",
            "show_object_viewport_light_probe",
            "show_object_viewport_meta",
            "show_object_viewport_pointcloud",
            "show_object_viewport_speaker",
            "show_object_viewport_surf",
            "show_object_viewport_volume",
        ]

        # Store original render settings
        orig_filepath = render.filepath
        orig_use_file_extension = render.use_file_extension
        orig_file_format = render.image_settings.file_format
        orig_color_depth = render.image_settings.color_depth
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

        orig_use_sequencer = render.use_sequencer
        orig_use_stamp = render.use_stamp
        orig_stamp_note_text = render.stamp_note_text

        # Store original output settings
        orig_file_format = render.image_settings.file_format
        orig_color_management = render.image_settings.color_management
        orig_ffmpeg_format = render.ffmpeg.format
        orig_ffmpeg_codec = render.ffmpeg.codec
        orig_ffmpeg_constant_rate_factor = render.ffmpeg.constant_rate_factor
        orig_ffmpeg_ffmpeg_preset = render.ffmpeg.ffmpeg_preset
        orig_ffmpeg_audio_codec = render.ffmpeg.audio_codec

        # # Store original animatic statuses
        # for sequence in context.scene.sequence_editor.sequences:
        #     if sequence.type == 'MOVIE':
        #         sequence["_muted"] = sequence.mute
        #         sequence.mute = True

        view_layer_visibilities = {}
        if self.do_render and self.do_single_layer:
            for layer in context.scene.view_layers:
                view_layer_visibilities[layer.name] = layer.use

        # Setup render settings
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
        render.filepath = self.filepath
        render.use_file_extension = True
        render.image_settings.file_format = 'FFMPEG'
        render.image_settings.color_management = 'FOLLOW_SCENE'
        render.ffmpeg.format = 'QUICKTIME'
        render.ffmpeg.codec = 'H264'
        render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
        render.ffmpeg.ffmpeg_preset = 'GOOD'
        render.ffmpeg.audio_codec = 'AAC'
        render.use_sequencer = False
        render.use_stamp = True

        render.image_settings.color_depth = '8'

        out_name = self.filepath
        dir_path = os.path.dirname(out_name)

        bpy.app.handlers.frame_change_pre.append(self.update)

        # Render animation from viewport
        bpy.ops.render.opengl(animation=True)

        bpy.app.handlers.frame_change_pre.remove(self.update)

        # Run animation playback
        bpy.ops.render.play_rendered_anim()

        # Restore original render settings
        render.filepath = orig_filepath
        render.use_file_extension = orig_use_file_extension
        render.image_settings.file_format = orig_file_format
        render.image_settings.color_depth = orig_color_depth
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
        render.image_settings.file_format = orig_file_format
        render.image_settings.color_management = orig_color_management
        render.ffmpeg.format = orig_ffmpeg_format
        render.ffmpeg.codec = orig_ffmpeg_codec
        render.ffmpeg.constant_rate_factor = orig_ffmpeg_constant_rate_factor
        render.ffmpeg.ffmpeg_preset = orig_ffmpeg_ffmpeg_preset
        render.ffmpeg.audio_codec = orig_ffmpeg_audio_codec

        # # Restore original animatic statuses
        # for sequence in context.scene.sequence_editor.sequences:
        #     if sequence.type == 'MOVIE':
        #         sequence.mute = sequence["_muted"]
        #         del sequence["_muted"]

        render.use_sequencer = orig_use_sequencer
        render.use_stamp = orig_use_stamp
        render.stamp_note_text = orig_stamp_note_text

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
    self.layout.operator(
        LFS_OT_Viewport_Playblast.bl_idname,
        text="LFS Viewport Playblast",
        icon='RENDER_ANIMATION',
    )
    self.layout.separator()


def register():
    bpy.utils.register_class(LFS_OT_Viewport_Playblast)
    bpy.types.VIEW3D_MT_view.prepend(playblast_button)


def unregister():
    bpy.types.VIEW3D_MT_view.remove(playblast_button)
    bpy.utils.unregister_class(LFS_OT_Viewport_Playblast)


if __name__ == "__main__":
    register()
