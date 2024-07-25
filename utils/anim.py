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
