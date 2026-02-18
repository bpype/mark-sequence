#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020-2026 Les Fées Spéciales
#
# SPDX-License-Identifier: GPL-2.0-or-later


import argparse
import fileseq
import json
import os
import platform
import re
import shutil
import subprocess
import textwrap
from concurrent.futures import ThreadPoolExecutor
from math import inf
from tempfile import mkstemp


__all__ = ["default_template", "SequenceMarker"]


default_template = {
    "settings": {
        "font_size": 24,
        "color": "&H00FFFFFF",
    },
    "fields": [
        {
            "name": "project",
            "direction": "NorthWest",
            "string": " %s ",
        },
        {
            "name": "seq",
            "direction": "NorthWest",
            "string": "%s ",
        },
        {
            "name": "scene",
            "direction": "NorthWest",
            "string": "%s ",
        },
        {
            "name": "frame_number",
            "direction": "NorthWest",
            "string": "%s",
        },
        {
            "name": "normalized_frame_number",
            "direction": "North",
            "string": "%04i / ",
        },
        {
            "name": "total_images",
            "direction": "North",
            "string": "%s",
        },
        {
            "name": "tc",
            "direction": "North",
            "string": " - %s",
        },
        {
            "name": "file_name",
            "direction": "NorthEast",
            "string": " %s ",
        },
        {
            "name": "version",
            "direction": "NorthEast",
            "string": " %s ",
        },
        {
            "name": "resolution",
            "direction": "NorthEast",
            "string": " %s ",
        },
        {
            "name": "copyright",
            "direction": "SouthWest",
            "string": " %s ",
        },
        {
            "name": "focal_length",
            "direction": "SouthWest",
            "string": " Focal length: %d mm ",
        },
        {
            "name": "fstop",
            "direction": "SouthWest",
            "string": " F-Stop: %s  ",
        },
        {
            "name": "timeline_marker",
            "direction": "South",
            "string": " ▲ %s ",
        },
        {
            "name": "studio",
            "direction": "SouthEast",
            "string": " %s ",
        },
        {
            "name": "user",
            "direction": "SouthEast",
            "string": " %s ",
        },
        {
            "name": "hostname",
            "direction": "SouthEast",
            "string": " %s ",
        },
        {
            "name": "date",
            "direction": "SouthEast",
            "string": " %s ",
        },
    ],
    "image_fields": [
        # {
        #     "name": "circle",
        #     "direction": "SouthWest",
        #     "geometry": "10x10+20+4"
        # }
    ],
}


def frame_to_timecode(frame, fps=24, use_frame_cents=False):
    """
    Adapted from github gist:
    https://gist.github.com/schiffty/c838db504b9a1a7c23a30c366e8005e8
    """
    h = int(frame / 86400)
    m = int(frame / 1440) % 60
    s = int((frame % 1440) / fps)
    f = frame % 1440 % fps
    if use_frame_cents:
        f = int(f * 100 / fps)
        return "%01d:%02d:%02d.%02d" % (h, m, s, f)
    return "%02d:%02d:%02d" % (m, s, f)


class SequenceMarker:
    def __init__(self, image_filepath, data, template=default_template):
        self.data = data
        self.template = template or default_template

        match = re.search(r"(\d+)[^\d]*$", image_filepath)
        if match is None:
            print(f"No frame padding found for {image_filepath}.")
            return

        # Get file sequence by replacing last occuring number with @-padding.
        padding = len(match.group(1))
        image_filepath = re.sub(r"\d+([^\d]*)$", f"{'@' * padding}\g<1>", image_filepath)

        self.file_sequence = fileseq.findSequenceOnDisk(image_filepath, strictPadding=True)
        self.frame_set = self.file_sequence.frameSet()

    def generate_ass_file(self):
        settings = self.template["settings"]
        font_path = os.path.join(
            os.path.dirname(__file__),
            "data", "fonts", "LiberationMono-Regular.ttf"
        )
        ass_text = textwrap.dedent("""
            [Script Info]
            Title: Default Aegisub file
            ScriptType: v4.00+
            WrapStyle: 0
            ScaledBorderAndShadow: yes
            YCbCr Matrix: TV.709
            PlayResX: {res_x}
            PlayResY: {res_y}

            [V4+ Styles]
            Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
            Style: North,{font_path},{font_size},{color},&H000000FF,&H9F000000,&HFF000000,0,0,0,0,100,100,0,0,1,2,2,8,2,2,2,1
            Style: NorthEast,{font_path},{font_size},{color},&H000000FF,&H9F000000,&HFF000000,0,0,0,0,100,100,0,0,1,2,2,9,2,2,2,1
            Style: East,{font_path},{font_size},{color},&H000000FF,&H9F000000,&HFF000000,0,0,0,0,100,100,0,0,1,2,2,6,2,2,2,1
            Style: SouthEast,{font_path},{font_size},{color},&H000000FF,&H9F000000,&HFF000000,0,0,0,0,100,100,0,0,1,1,1.5,3,2,2,2,1
            Style: South,{font_path},{font_size},{color},&H000000FF,&H9F000000,&HFF000000,0,0,0,0,100,100,0,0,1,2,2,2,2,2,2,1
            Style: SouthWest,{font_path},{font_size},{color},&H000000FF,&H9F000000,&HFF000000,0,0,0,0,100,100,0,0,1,2,2,1,2,2,2,1
            Style: West,{font_path},{font_size},{color},&H000000FF,&H9F000000,&HFF000000,0,0,0,0,100,100,0,0,1,2,2,4,2,2,2,1
            Style: NorthWest,{font_path},{font_size},{color},&H000000FF,&H9F000000,&HFF000000,0,0,0,0,100,100,0,0,1,2,2,7,2,2,2,1

            [Events]
            Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
            """
        ).format(
            res_x=self.data["resolution_x"],
            res_y=self.data["resolution_y"],
            font_size=settings["font_size"],
            color=settings["color"],
            font_path=font_path,
        )

        # Special fields: for each special field, give a default if it is
        # specified in the template but not passed as data
        for field in self.template["fields"]:
            if field["name"] == "date":
                import datetime

                self.data["date"] = datetime.datetime.now().strftime("%d-%m-%y %H:%M")
            if field["name"] == "user":
                import getpass

                self.data["user"] = getpass.getuser()
            if field["name"] == "hostname":
                import platform

                self.data["hostname"] = platform.node()
            if field["name"] == "total_images":
                self.data["total_images"] = len(self.frame_set)
            if field["name"] == "total_tc":
                self.data["total_tc"] = frame_to_timecode(len(self.frame_set))

        frame_rate = self.data["frame_rate"]
        for i, image_number in enumerate(self.frame_set):
            if image_number < self.data["start_frame"] or image_number > self.data["end_frame"]:
                continue
            image_data = self.data.copy()

            # Special fields evaluated at each frame
            for field in self.template["fields"]:
                if field["name"] == "frame_number":
                    image_data["frame_number"] = image_number
                elif field["name"] == "normalized_frame_number":
                    image_data["normalized_frame_number"] = i - self.data["offset"] + 1
                elif field["name"] == "tc":
                    image_data["tc"] = frame_to_timecode(i - self.data["offset"] + 1, self.data["frame_rate"])
                elif field["name"] in self.data and type(self.data[field["name"]]) is dict:
                    image_data[field["name"]] = self.data[field["name"]][image_number]

            # Add annotations for each field to the list of directions
            # This has the effect of concatenating various fields for a given direction
            directions = {}
            for field in self.template["fields"]:
                direction = field["direction"]
                field_string = field["string"]
                # Try formatting the string with the value from the passed data
                if field["name"] not in image_data:
                    print(f"Could not evaluate field {field['name']}")
                    continue
                field_value = image_data[field["name"]]
                if not field_value:
                    continue
                field_string %= field_value
                if direction not in directions:
                    directions[direction] = ""
                directions[direction] += field_string

            start_time = frame_to_timecode(
                i - image_data["offset"], frame_rate, use_frame_cents=True
            )
            end_time = frame_to_timecode(
                i - image_data["offset"] + 1, frame_rate, use_frame_cents=True
            )
            # Add annotations for each field
            for direction, value in directions.items():
                ass_text += f"Dialogue: 0,{start_time},{end_time},{direction},,0,0,0,,{value}\n"

            # # FIXME Add image annotations
            # for image in self.template["image_fields"]:
            #     convert_args.append("(")

            #     # File path, either from template or from command line
            #     if image["field"] and image_data[image["field"]]:
            #         convert_args.append(os.path.abspath(image_data[image["field"]]))
            #     else:
            #         convert_args.append(image["path"])
            #     convert_args.extend(
            #         [
            #             "-gravity", image["direction"],
            #             "-geometry", image["geometry"],
            #             ")",
            #             "-composite",
            #         ]
            #     )

        ass_descriptor, ass_path = mkstemp(suffix=".ass", text=True)
        with os.fdopen(ass_descriptor, 'w') as ass_file:
            ass_file.write(ass_text)
        if platform.system() == "Windows":
            ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
        return ass_path

    def render_video(self, do_mark_images=True):
        if not self.data["video_output"]:
            return

        img_sources = self.get_sequence_path(self.file_sequence)
        first_frame = self.data.get("start_frame")
        frame_rate = self.data.get("frame_rate", 25)
        audio_file = self.data.get("audio_file")
        settings = self.template["settings"]

        ffmpeg_args = ["ffmpeg", "-y", "-loglevel", "error"]
        ffmpeg_args.extend(["-r", str(frame_rate)])
        ffmpeg_args.extend(["-start_number", str(first_frame)])
        ffmpeg_args.extend(["-i", img_sources])

        if audio_file is not None:
            ffmpeg_args.extend(["-i", audio_file])
            ffmpeg_args.extend(["-c:a", "aac", "-b:a", "160k"])
            ffmpeg_args.extend(["-map", "0:0", "-map", "1:0"])

        video_filter = "[0]"

        # If image res is odd, pad it by one pixel to allow h.264 encoding.
        # https://stackoverflow.com/q/20847674
        video_filter += "pad=ceil(iw/2)*2:ceil(ih/2)*2[p], "

        # Overlay video on alpha
        # https://stackoverflow.com/a/52804884
        video_filter += ("color=black, format=rgb24[c], "
                         "[c][p]scale2ref[c][i],"
                         "[c][i]overlay=format=auto:shortest=1, setsar=1[o]")

        # # Background color
        # # FIXME: lookup ASS' way to calculate text height.
        # height = self.template["settings"]["font_size"] * 2
        # video_filter += f"drawbox=w=in_w:h={height}:c=0x00000088:t=fill, "
        # video_filter += f"drawbox=y=in_h-{height}:w=in_w:h={height}:c=0x00000088:t=fill, "

        if do_mark_images:
            # Subtitles
            ass_path = self.generate_ass_file()
            video_filter += f",[o]ass='{ass_path}'"

        ffmpeg_args.extend(["-vf", video_filter])

        # Video codec
        ffmpeg_args.extend(["-c:v", "mjpeg", "-q:v", "3"])
        # ffmpeg_args.extend(["-c:v", "h264", "-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])

        destination = os.path.abspath(self.data["video_output"])
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        ffmpeg_args.extend(["%s" % (destination)])

        print("FFmpeg command:")
        print(" ".join(ffmpeg_args))

        print("Generating video...")
        try:
            proc = subprocess.run(ffmpeg_args, check=True, shell=platform.system() == "Windows")
        except subprocess.CalledProcessError as e:
            print(e.returncode, e.cmd, e.stderr)
            raise e

    @staticmethod
    def get_sequence_path(sequence):
        padding = sequence.getPaddingNum(sequence.padding())
        return sequence.format("{dirname}{basename}%0" + str(padding) + "d{extension}")

    def play_movie(self):
        if platform.system() == "Windows" and os.path.exists(self.data["video_output"]):
            os.startfile(self.data["video_output"])

    # verifier si le nom du fichier contient "anim"


if __name__ == "__main__":
    # Parse command line arguments
    width = min(80, shutil.get_terminal_size().columns - 2)
    formatter_class = lambda prog: argparse.RawDescriptionHelpFormatter(prog, width=width)
    parser = argparse.ArgumentParser(
        formatter_class=formatter_class,
        description=textwrap.indent(
            textwrap.dedent(
                """\

            Make an annotated movie output from a list of images. A JSON
            template may be specified, which will contain fields such as:

            {
                "name": "scene",
                "direction": "NorthWest",
                "string": ' sc%s '
            },

            You can then specify the option --scene on the command line, and
            the text will appear in the top left. Warning: underscores are
            replaced by dashes, so "my_field" becomes "my-field", to respect
            the customary option format.

            The direction uses ImageMagick’s convention: Center, North,
            NorthEast, East, SouthEast, South, SouthWest, West, NorthWest. If a
            direction is specified multiple times, the corresponding fields
            will be concatenated.

            """
            ),
            "  ",
        ),
    )

    group = parser.add_argument_group("file options")
    group.add_argument("-t", "--template", type=str, help="template file containing field descriptions")

    group.add_argument(
        "sequence",
        type=str,
        help="input image sequence, typically a frame in the sequence",
    )
    group.add_argument(
        "-d",
        "--mark-dir",
        type=str,
        help="intermediate directory, leave blank for tmp dir",
    )
    group.add_argument("-o", "--video-output", type=str, help="render video to this destination")
    group.add_argument(
        "-a",
        "--audio-file",
        type=str,
        help="if rendering video, use this file as audio track",
    )

    group.add_argument("-r", "--frame_rate", type=float, default=25.0, help="playback speed")

    group = parser.add_argument_group("frame options")
    group.add_argument("-O", "--offset", type=int, default=0, help="offset for renaming frames")
    group.add_argument(
        "-s",
        "--start-frame",
        type=int,
        default=-inf,
        help="don't mark images lower than this number",
    )
    group.add_argument(
        "-e",
        "--end-frame",
        type=int,
        default=inf,
        help="don't mark images higher than this number",
    )

    args = parser.parse_known_args()[0]

    # Load in template from supplied json file. If none given, use default one.
    if args.template is None:
        template = default_template
    else:
        with open(os.path.abspath(args.template), "r") as f:
            template = json.load(f)

    # Add text fields to argument parser
    group = parser.add_argument_group("Template text field arguments")
    for field in template["fields"]:
        field = field["name"].replace("_", "-")
        group.add_argument("--" + field, type=str, default="")

    # Add image fields to argument parser
    group = parser.add_argument_group("Template image field arguments")
    for image in template["image_fields"]:
        image = image["name"].replace("_", "-")
        group.add_argument("--" + image, type=str, default="")

    args = parser.parse_args()

    sequence_marker = SequenceMarker(os.path.abspath(args.sequence), vars(args), template=template)

    # Get resolution from first image
    # https://stackoverflow.com/a/29585066
    res = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            sequence_marker.file_sequence.frame(sequence_marker.frame_set[0]),
        ]
    )
    res_x, res_y = res.decode("ascii").split("x")
    sequence_marker.data["resolution_x"] = int(res_x)
    sequence_marker.data["resolution_y"] = int(res_y)

    # Get first frame from sequence if not specified manually
    if sequence_marker.data["start_frame"] == -inf:
        sequence_marker.data["start_frame"] = sequence_marker.frame_set[0]

    sequence_marker.render_video()
