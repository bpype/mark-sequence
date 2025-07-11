_Mark Sequence_, a command line script to stamp text information on
image sequences.

## Installation
### Dependencies
This script uses FFmpeg. On Linux, use your package manager.
Debian-based distributions users can use:
``` bash
apt install ffmpeg
```

On Windows, download and install one of the builds linked to from the
[official website](https://ffmpeg.org/download.html#build-windows).

The script also depends on the
[Fileseq](https://pypi.org/project/Fileseq/) Python library. You can
install it with pip:

``` bash
pip install fileseq
```

## Usage
Make an annotated movie output from a list of images. A JSON template
may be specified, which will contain fields such as:

{
    "name": "scene",
    "direction": "NorthWest",
    "string": ' sc%s '
},

The `mark_sequence.py` file may be used either as a command-line
progam, or as a Python module.


### Command-line arguments
``` bash
./mark_sequence.py -t my_template.json -o converted_sequence.mov --scene 24 test_sequence.001.png
```

The basic idea is to specify a template, an input image sequence and
an output video file name. Additionnally, each field defined in the
template can be overridden on the command line. In the previous
example, you can specify the option --scene, and the text will appear
in the top left.

Warning: underscores in the template are replaced by dashes, so
"my_field" becomes "my-field", to respect the customary option format.

The direction uses ImageMagick’s convention: Center, North, NorthEast,
East, SouthEast, South, SouthWest, West, NorthWest. If a direction is
specified multiple times, the corresponding fields will be
concatenated.


### Python module

``` python
import os
from mark_sequence import SequenceMarker

data = {"video_output": os.path.join(os.getcwd(), 'playblast.mov'),
        "resolution_x": 1920,
        "resolution_y": 1080,
        "start_frame": 1,
        "end_frame": 42,
        "offset": 0,
        "project": "A fine project",

sequence_marker = SequenceMarker("my_sequence.0000.tif", data)
sequence_marker.mark_sequence()
```

This will call FFmpeg to generate a `playblast.mov` sequence in the
current directory, with some options from the default template
overridden.


## License
This script is licensed under the GPLv2 license. Please see the
LICENSE file for more information.
