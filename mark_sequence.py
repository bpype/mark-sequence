#!/usr/bin/env python3

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


import subprocess
import getpass
import datetime
import argparse
import os
from tempfile import TemporaryDirectory
import fileseq


default_template = {
    # "settings": {
    #     ...
    # },
    "output_fields": [
        {
            "field": "shot_name",
            "direction": "NorthWest",
            "string": '%s  '
        },
        {
            "field": "frame_number",
            "direction": "NorthWest",
            "string": '%s'
        },
        {
            "field": "normalized_frame_number",
            "direction": "North",
            "string": '%04s / '
        },
        {
            "field": "total_images",
            "direction": "North",
            "string": '%s'
        },
        {
            "field": "user",
            "direction": "SouthEast",
            "string": '%10s '
        },
        {
            "field": "hostname",
            "direction": "SouthEast",
            "string": '%10s '
        },
        {
            "field": "date",
            "direction": "SouthEast",
            "string": '%s'
        },
        {
            "field": "copyright",
            "direction": "SouthWest",
            "string": '%s'
        },
        {
            "field": "comment",
            "direction": "South",
            "string": '%s'
        },
    ]
}

def mark_image(path, output_path, data):
    args = ['convert']
    args += ['%s' % path]

    # Add gray band overlay
    args.extend(['-fill', 'rgba(0,0,0,0.3)'])
    args.extend(['-draw', 'rectangle 0,0 %s,%s' % (
        data['resolution_x'],
        data['font_size'])])
    args.extend(['-fill', 'rgba(0,0,0,0.3)'])
    args.extend(['-draw', 'rectangle 0,%s %s,%s' % (
        data['resolution_y'] - data['font_size'] - 2,
        data['resolution_x'],
        data['resolution_y'])])

    # Setting text color and size
    args.extend(['-fill', 'white', '-pointsize', str(data['font_size'])])

    directions = {}

    # Add annotations for each field to the list of directions
    # This has the effect of concatenating various fields for a given direction
    for field in data['template']['output_fields']:
        direction = field['direction']
        value = field['string'] % data[field['field']]
        if not direction in directions:
            directions[direction] = ''
        directions[direction] += (value)

    # Add annotations for each field
    for direction, value in directions.items():
        args.extend(['-gravity', direction,
                     '-annotate', '0',
                     value])

    # Debug alpha channel
    args.extend(['-alpha', 'remove'])
    args.extend(['-compress', 'Piz'])  # TODO : remettre DWAA quand ffmpeg le permettra

    # Output
    args.append('%s' % output_path)  # Output path
    proc = subprocess.run(args, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Make an annotated movie output from a list of images')
    parser.add_argument('sequence', type=str,
                        help='file sequence, typically a frame in the sequence')
    parser.add_argument('--mark-dir', type=str,
                        help='intermediate directory, leave blank for tmp dir')

    parser.add_argument('--template', type=str,
                        help='template file for marking the sequence')

    parser.add_argument('--offset', type=int, default=0,
                        help='offset for renaming frames')

    parser.add_argument('--comment', type=str, default="",
                        help='comment added underneath the video')
    parser.add_argument('--shot', type=str,
                        help='shot name in top left corner of the video')
    parser.add_argument('--user', type=str, default=getpass.getuser(),
                        help='user responsible for the render')
    parser.add_argument('--hostname', type=str, default="",
                        help='render run from this hostname')
    parser.add_argument('--source', type=str, default="",
                        help='file used to generate this sequence')
    parser.add_argument('--date', type=str, default=datetime.datetime.now().strftime("%d-%m-%y %H:%M"),
                        help='override date')
    parser.add_argument('--copyright', metavar='date', type=str, default="(C) Ne pas diffuser",
                        help='copyright information')
    args = parser.parse_args()

    if args.mark_dir:
        mark_dir = args.mark_dir
        os.makedirs(mark_dir, exist_ok=True)
    else:
        mark_dir = TemporaryDirectory().name

    data = {'font_size': 16,}
    data.update(vars(args))

    resolution_x = None
    resolution_y = None

    file_sequence = fileseq.findSequenceOnDisk(os.path.abspath(args.sequence))
    frame_set = file_sequence.frameSet()

    data['total_images'] = len(frame_set)

    # Load in template from supplied file. If none given, use default one.
    if args.template is None:
        data['template'] = default_template
    else:
        with open(args.template, 'r') as f:
            data['template'] = json.load(f)

    # for i in range(args.start_frame, args.end_frame + 1):
    for i, image_number in enumerate(file_sequence.frameSet()):
        image_source = file_sequence.frame(image_number)
        image_marked = os.path.join(mark_dir, "marked.%04i.exr" % (i - args.offset + 1))
        print("Processing %s" % image_source)
        res = subprocess.check_output(['identify', '-format', '%wx%h', image_source])
        res_x, res_y = res.decode('ascii').split("x")
        if resolution_x is None:
            resolution_x = res_x
            data['resolution_x'] = int(res_x)
        if resolution_y is None:
            resolution_y = res_y
            data['resolution_y'] = int(res_y)

        data['normalized_frame_number'] = i - args.offset + 1
        data['frame_number'] = image_number
        mark_image(image_source, image_marked, data)
