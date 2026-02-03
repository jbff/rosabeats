# rosabeats

This repository contains the rosabeats Python library that allows for audio beat detection, segmentation, and remixing. It leverages the power of librosa and other audio processing libraries to enable precise beat tracking, song segmentation, and creative audio manipulation. This repository contains the core library code and various tools including scripts to segment songs, create and play/save beat "recipes", and a command line interpreter for interactive beat manipulation.

I wrote this because for some reason I was too dense to figure out how to use [Amen](https://github.com/algorithmic-music-exploration/amen) to replicate in Python something like the Infinite Jukebox. That was the initial impetus, anyway. This code is not elegant. If I was too dense to figure out how to use amen, even with the code and examples in front of me, you can bet that I did not write elegant code. But it does work and I have enjoyed playing with it.

A short mp3 that is in the public domain is included and an example beat recipe that references it. The track used for this example was obtained from [Free Music Archive](https://freemusicarchive.org/music/play-house/single/random-drop/) - "Random Drop" by Play House - and is distributed under the Creative Commons Public Domain License (CC0), which allows for unrestricted use, modification, and distribution without any copyright restrictions. Many thanks to the creator.

I wrote most of this code in 2018-2019 and made some additions through 2021. I created this public repo to hold the most useful bits on April 12, 2025. I intend to improve the code. It almost certainly contains bugs that I don't ever hit. It was cobbled together a feature at a time and thus, looks and probably acts that way.

## Features

- **Beat Detection**: Automatically detect beats and tempo in audio files
- **Bar Analysis**: Group beats into bars with configurable beats-per-bar
- **Audio Segmentation**: Segment songs into structural parts using Laplacian spectral clustering 
- **Audio Remixing**: Create remixes by manipulating beats and bars:
  - Play individual beats or ranges of beats
  - Play entire bars or ranges of bars
  - Shuffle beats or bars randomly
  - Reverse the order of beats within bars
  - Create precise rests with beat-accurate timing
- **Beat Recipe Files**: Save and load beat patterns as reusable recipes
- **Interactive Shell**: Command-line interface for experimenting with beat patterns
- **Segment Analysis**: Identify structurally similar sections in songs
- **Output Options**: Play remixes in real-time, save to files, or generate beat recipes

## Installation

### Prerequisites

- Python 3.11+ (Tested most recently with Python 3.11.12 and 3.13.2)
- ffms2 libraries (On Fedora: `dnf install ffms2`; tested most recently with ffms-5.0)

### Installing from PyPI

```bash
# Basic install
pip install rosabeats

# With optional dependencies
pip install rosabeats[all]
```

Or with [uv](https://docs.astral.sh/uv/):
```bash
uv pip install rosabeats
uv pip install rosabeats[all]
```

### Installing from Source

1. Clone the repository:
```bash
git clone https://github.com/jbff/rosabeats.git
cd rosabeats
```

2. Install the package:
```bash
pip install .
```

Or for development (editable install):
```bash
pip install -e .
```

3. Installing optional dependencies:

```bash
# Install with ffms2 support for additional audio formats
pip install .[ffms2]
```

This will install the package and its dependencies, and make the following command-line tools available:
- `beatrecipe-processor`: Process beat recipes
- `segment-song`: Segment songs and track beats
- `beatswitch`: Generate beat recipes with alternating patterns
- `rosabeats-shell`: Interactive shell for beat manipulation

### Using rosabeats

The package can be imported in Python as:
```python
import rosabeats
```

Documentation for beat recipes can be found in the `docs/` directory of the package. The main tools (`beatrecipe_processor.py` and `segment_song.py`) have been tested and are functional. Additional scripts in the `scripts/` directory may be of interest but have not been recently tested.

## License

## ISC License

Copyright © 2025 [John Fleming](https://github.com/jbff)

Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

## Acknowledgments

- [librosa](https://librosa.org/) for audio analysis
- [Amen](https://github.com/algorithmic-music-exploration/amen) was the original inspiration

