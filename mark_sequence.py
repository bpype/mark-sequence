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


import os
import subprocess
import json
import argparse
import fileseq
from tempfile import mkdtemp
from math import inf
import textwrap

default_template = {
    "settings": {
        "font_size": 16,
        "color": "chartreuse"
    },
    "fields": [
        {
            "field": "frame_number",
            "direction": "NorthWest",
            "string": "%s"
        },
        {
            "field": "normalized_frame_number",
            "direction": "North",
            "string": "%04s / "
        },
        {
            "field": "total_images",
            "direction": "North",
            "string": "%s"
        },
        {
            "field": "user",
            "direction": "SouthEast",
            "string": "%10s "
        },
        {
            "field": "hostname",
            "direction": "SouthEast",
            "string": "%10s "
        },
        {
            "field": "date",
            "direction": "NorthEast",
            "string": "%s"
        }
    ],
    "images": [
        {
            "field": "circle",
            "direction": "SouthWest",
            "geometry": "10x10+20+4"
        }
    ]
}


def mark_image(path, output_path, data):
    args = ['convert']
    args += ['%s' % path]

    settings = data['template']['settings']

    # Add gray band overlay
    args.extend(['-fill', 'rgba(0,0,0,0.3)'])
    args.extend(['-draw', 'rectangle 0,0 %s,%s' % (data['resolution_x'],
                                                   settings['font_size'])])
    args.extend(['-fill', 'rgba(0,0,0,0.3)'])
    args.extend(['-draw', 'rectangle 0,%s %s,%s' % (data['resolution_y'] -
                                                    settings['font_size'] - 2,
                                                    data['resolution_x'],
                                                    data['resolution_y'])])

    # Setting text color and size
    args.extend(['-fill', settings['color'], '-pointsize', str(settings['font_size'])])

    directions = {}

    # Add annotations for each field to the list of directions
    # This has the effect of concatenating various fields for a given direction
    for field in data['template']['fields']:
        direction = field['direction']
        value = field['string']
        # Try formatting the string with the value from the command line
        try:
            value %= data[field['field']]
        except TypeError:
            pass
        if not direction in directions:
            directions[direction] = ''
        directions[direction] += (value)

    # Add annotations for each field
    for direction, value in directions.items():
        args.extend(['-gravity', direction,
                     '-annotate', '0',
                     value])

        # Add image annotations
    for image in data['template']['images']:
        args.append('(')

        # File path, either from template or from command line
        if image['field'] and data[image['field']]:
            args.append(os.path.abspath(data[image['field']]))
        else:
            args.append(image['path'])
        args.extend([
            '-gravity', image['direction'],
            '-geometry', image['geometry'],
            ')',
            '-composite'])

    # Debug alpha channel
    args.extend(['-alpha', 'remove'])
    args.extend(['-compress', 'Piz'])  # TODO : remettre DWAA quand ffmpeg le permettra

    # Output
    args.append('%s' % output_path)
    proc = subprocess.run(args, check=True)


def render_video(img_sources, destination, audio_file=None, frame_rate=25):
    args = ['ffmpeg', '-y']
    args.extend(['-r', str(frame_rate)])
    args.extend(['-i', img_sources])

    if audio_file is not None:
        args.extend(['-i', 'audio_file'])
        args.extend(['-c:a', 'copy'])

    args.extend(['-c:v', 'mjpeg', '-q:v', '3'])

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    args.extend(['%s' % (destination)])

    proc = subprocess.run(args)


def get_sequence_path(sequence):
    padding = file_sequence.getPaddingNum(file_sequence.padding())
    return file_sequence.format('{dirname}{basename}%0' + str(padding) + 'd{extension}')


if __name__ == "__main__":
    data = {}

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.indent(
            textwrap.dedent('''\

            Make an annotated movie output from a list of images. A JSON
            template may be specified, which will contain fields such as:

            {
                "field": "shot_name",
                "direction": "NorthWest",
                "string": '%s  '
            },

            You can then specify the option --shot-name on the command line,
            and the text will appear in the top left.

            The direction uses ImageMagick’s convention: Center, North,
            NorthEast, East, SouthEast, South, SouthWest, West, NorthWest. If a
            direction is specified multiple times, the corresponding fields
            will be concatenated.

            '''
            ), '  '
        )
    )

    group = parser.add_argument_group('file options')
    group.add_argument('-t', '--template', type=str,
                        help='template file containing field descriptions')

    group.add_argument('sequence', type=str,
                        help='input image sequence, typically a frame in the sequence')
    group.add_argument('-d', '--mark-dir', type=str,
                        help='intermediate directory, leave blank for tmp dir')
    group.add_argument('-v', '--video-output', type=str,
                        help='render video to this destination')
    group.add_argument('-a', '--audio-file', type=str,
                        help='if rendering video, use this file as audio track')

    group = parser.add_argument_group('frame options')
    group.add_argument('-o', '--offset', type=int, default=0,
                        help='offset for renaming frames')
    group.add_argument('-s', '--start-frame', type=int, default=-inf,
                        help="don't mark images lower than this number")
    group.add_argument('-e', '--end-frame', type=int, default=inf,
                        help="don't mark images higher than this number")

    args = parser.parse_known_args()[0]

    # Load in template from supplied file. If none given, use default one.
    if args.template is None:
        print(None)
        template = default_template
    else:
        with open(os.path.abspath(args.template), 'r') as f:
            template = json.load(f)

    # Add text fields
    group = parser.add_argument_group('Template text field arguments')
    for field in template['fields']:
        field = field['field'].replace('_', '-')
        group.add_argument('--' + field, type=str, default='')

    # Add image fields
    group = parser.add_argument_group('Template image field arguments')
    for image in template['images']:
        image = image['field'].replace('_', '-')
        group.add_argument('--' + image, type=str, default='')

    args = parser.parse_args()

    # Create temporary directory for images
    if args.mark_dir:
        mark_dir = args.mark_dir
        os.makedirs(mark_dir, exist_ok=True)
    else:
        mark_dir = mkdtemp()

    data.update(vars(args))
    data['template'] = template

    file_sequence = fileseq.findSequenceOnDisk(os.path.abspath(args.sequence))
    frame_set = file_sequence.frameSet()

    # Get first image resolution
    res = subprocess.check_output(['identify', '-format', '%wx%h', file_sequence.frame(2)])
    res_x, res_y = res.decode('ascii').split("x")
    data['resolution_x'] = int(res_x)
    data['resolution_y'] = int(res_y)

    # Special fields: for each special field, give a default if it is
    # specified in the template but not overriden on command line
    for field in template['fields']:
        if field['field'] == 'date' and not args.date:
            import datetime
            data['date'] = datetime.datetime.now().strftime("%d-%m-%y %H:%M")
        if field['field'] == 'user' and not args.user:
            import getpass
            data['user'] = getpass.getuser()
        if field['field'] == 'hostname' and not args.hostname:
            import platform
            data['hostname'] = platform.node()
        if field['field'] == 'total_images' and not args.total_images:
            data['total_images'] = len(frame_set)

    for i, image_number in enumerate(file_sequence.frameSet()):
        if (image_number < args.start_frame
            or image_number > args.end_frame):
            continue
        image_source = file_sequence.frame(image_number)
        image_marked = os.path.join(mark_dir, "marked.%04i.png" % (i - args.offset + 1))
        print("Processing %s" % image_source)

        # Special fields: for each special field, give a default if it is
        # specified in the template but not overriden on command line
        for field in template['fields']:
            if field['field'] == 'frame_number' and not args.frame_number:
                data['frame_number'] = image_number
            if field['field'] == 'normalized_frame_number' and not args.normalized_frame_number:
                data['normalized_frame_number'] = i - args.offset + 1
        mark_image(image_source, image_marked, data)

    if args.video_output:
        render_video(get_sequence_path(file_sequence), os.path.abspath(args.video_output))

    if not args.mark_dir:
        from shutil import rmtree
        rmtree(mark_dir)
