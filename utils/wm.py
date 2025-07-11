# SPDX-FileCopyrightText: 2020-2025 Les Fées Spéciales
#
# SPDX-License-Identifier: GPL-2.0-or-later


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
