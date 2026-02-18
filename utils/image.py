# SPDX-FileCopyrightText: 2020-2026 Les Fées Spéciales
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy


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
