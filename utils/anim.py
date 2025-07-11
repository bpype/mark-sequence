# SPDX-FileCopyrightText: 2020-2025 Les Fées Spéciales
#
# SPDX-License-Identifier: GPL-2.0-or-later


def get_frame_markers(context):
    markers = {m.frame: m.name for m in context.scene.timeline_markers}

    frame_markers = {
        f: None
        for f in range(context.scene.frame_start, context.scene.frame_end+1)
    }
    for f in range(context.scene.frame_start, context.scene.frame_end+1):
        for m_f in sorted(markers, reverse=True):
            if f >= m_f:
                frame_markers[f] = markers[m_f]
                break
    return frame_markers
