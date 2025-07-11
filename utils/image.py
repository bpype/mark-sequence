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


def proxify(img, target_width):
    if "is_proxy" in img:
        if img["is_proxy"] and img.size[0] != target_width:
            deproxify(img)
        else:
            return

    img["is_proxy"] = True

    dest = target_width
    w, h = img.size
    h *= dest / w
    w = dest
    img.scale(w, h)
    img.gl_free()  # Force image update?


def proxify_images(context, target_width):
    images_to_process = {
        img
        for img in bpy.data.images
        if img.source in {"TILED", "FILE"} and img.size[0] > target_width
    }

    number_imgs = len(images_to_process)
    context.window_manager.progress_begin(1, number_imgs)

    for i, img in enumerate(images_to_process):
        print(
            "Proxy: processing image {:03} of {:03} : {}".format(
                i + 1, number_imgs, img.name
            )
        )
        context.window_manager.progress_update(i + 1)
        proxify(img, target_width)

    print("Proxy: done.")
    context.window_manager.progress_end()
