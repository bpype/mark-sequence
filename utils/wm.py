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


def find_area(context):
    if context.area is not None and context.area.type == "VIEW_3D":
        return context.area
    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            return area
    return None


def find_region_3d(context):
    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            return area.spaces[0].region_3d
    return None


def find_space(context):
    if context.space_data is not None and context.space_data.type == "VIEW_3D":
        return context.space_data
    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            return area.spaces[0]
    return None
