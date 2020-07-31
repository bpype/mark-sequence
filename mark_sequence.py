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


def mark_image(path, output_path, data):
    print("Frame %i" % data['frame_number'])

    args = ['F:\\TECH\\libs\\ImageMagick_Custom\\convert.exe']
    args += ['"%s"' % path]

    # Add gray band overlay
    args.extend(['-fill "rgba(0,0,0,0.3)"'])
    args.extend(['-draw "rectangle 0,0 %s,%s"' % (
        data['resolution_x'],
        data['font_size'])])
    args.extend(['-fill "rgba(0,0,0,0.3)"'])
    args.extend(['-draw "rectangle 0,%s %s,%s"' % (
        data['resolution_y'] - data['font_size'] - 2,
        data['resolution_x'],
        data['resolution_y'])])

    # Setting text color and size
    args.extend(['-fill', 'white', '-pointsize', str(data['font_size'])])

    # Shot name / Frame number
    args.extend(['-gravity', 'NorthWest', '-annotate', "0", '"%s   %s"' % (data['shot_name'], data['frame_number'])])
    # Normalized current frame
    args.extend(['-gravity',
                 'North',
                 '-annotate',
                 "0",
                 '"%04s  /  %s "' % (str(data['normalized_frame_number']), data["total_images"])])
    # Resolution and lens information
    args.extend(['-gravity',
                 'NorthEast',
                 '-annotate',
                 '0',
                 '"%s    %ix%i"' % (data["source"], data['resolution_x'], data['resolution_y'])])
    # Date
    args.extend(['-gravity',
                 'SouthEast',
                 '-annotate',
                 '0',
                 '"LFS %10s %10s %s"' % (data['user'], data['hostname'], data['date'])])
    # Copryright / Status
    args.extend(['-gravity',
                 'SouthWest',
                 '-annotate',
                 '0',
                 '"%s"' % (data['copyright'])])
                 # '"%s - Current status : %s"' % (data["copyright"], data['status'])])
    # Comment

    if data['commentaire']:
        args.extend(['-gravity',
                     'South',
                     '-annotate',
                     '0',
                     '"%s"' % data['commentaire']])

    # Debug alpha channel
    args.extend(['-alpha', 'remove'])
    args.extend(['-compress', 'Piz'])  # TODO : remettre DWAA quand ffmpeg le permettra

    # Output
    args.append('"%s"' % output_path)  # Output path
    j = " ".join(args)
    print(j)
    proc = subprocess.check_output(j, shell=True)
    print(proc)
    #os.system('%s' % j)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Make a movie output of a list of images.')
    parser.add_argument('--image_dir', metavar='image_dir', type=str, default="",
                        help='Folder containing the images')
    parser.add_argument('--comment', metavar='comment', type=str, default="",
                        help='Comment added underneath the video')
    parser.add_argument('--shot', metavar='shot', type=str,
                        help='Shot name in top left corner of the video')
    parser.add_argument('--user', metavar='user', type=str, default=getpass.getuser(),
                        help='User responsible for the render')
    parser.add_argument('--hostname', metavar='hostname', type=str, default="",
                        help='Render run from this hostname')
    parser.add_argument('--source', metavar='source', type=str, default="",
                        help='Aep/blender or any source filename')
    parser.add_argument('--start_frame', metavar='start_frame', type=int,
                        help='Start frame')
    parser.add_argument('--end_frame', metavar='end_frame', type=int,
                        help='End_frame')
    parser.add_argument('--offset', metavar='offset', type=int, default=0,
                        help='Offset for renaming frames')
    # parser.add_argument('--bits', metavar='bits', type=str, default="8",
    #                     help='Bits: 8 (default) or 16')
    parser.add_argument('--duration', metavar='duration', type=int, default=0,
                        help='Total number of images of sequence')
    # parser.add_argument('--status', metavar='status', type=str, default="WIP",
    #                     help='Shot current status')
    parser.add_argument('--date', metavar='date', type=str, default=datetime.datetime.now().strftime("%d-%m-%y %H:%M"),
                        help='Override date')
    parser.add_argument('--copyright', metavar='date', type=str, default="(C) Ne pas Diffuser",
                        help='Override date')
    parser.add_argument('--mark_folder', metavar='mark_folder', type=str,
                        help='Leave blank for tmp folder')
    parser.add_argument('--current', action='store_true',
                        help="Set the output also as current")
    parser.add_argument('--output', metavar='output', type=str, help="the output .mov MOVIE destination")
    args = parser.parse_args()

    mark_folder = args.mark_folder
    if not os.path.exists(mark_folder):
        os.makedirs(mark_folder)

    # Clean mark folder if needed

    data = {
        'resolution_x': 0,
        'resolution_y': 0,
        'frame_number': 0,
        'normalized_frame_number': 0,
        'font_size': 16,
        'user': args.user,  # getpass.getuser(),
        'hostname': args.hostname,
        'source': args.source,
        'copyright': args.copyright,
        'offset': args.offset,
        'date': args.date,
        'shot_name': args.shot,
        'commentaire': args.commentaire,
        'total_images': args.duration,
        # 'status': args.status,
        # 'bits': args.bits,
    }

    film, seq, shot = args.shot.split()
    resolution_x = None
    resolution_y = None

    for i in range(args.start_frame, args.end_frame + 1):
        # Remove marked frames
        image_source = os.path.join(args.image_dir, "%s_%s.%04i.exr" % (seq, shot, i))
        image_marked = os.path.join(args.mark_folder, "marked.%04i.exr" % (i - args.offset + 1))
        # Get resolution
        print("Processing %s" % image_source)
        res = subprocess.check_output(['F:\\TECH\\libs\\ImageMagick_Custom\\identify.exe', '-format', '%wx%h', image_source])
        res_x, res_y = res.decode('ascii').split("x")
        if not resolution_x:
            resolution_x = res_x
            data['resolution_x'] = int(res_x)
        if not resolution_y:
            resolution_y = res_y
            data['resolution_y'] = int(res_y)

        data['normalized_frame_number'] = i - args.offset + 1
        data['frame_number'] = i
        mark_image(image_source, image_marked, data)
