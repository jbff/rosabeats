#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from setuptools import setup, find_packages

# Read the package version from the __init__.py file
with open("rosabeats/__init__.py", "r") as f:
    init_content = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", init_content, re.M)
    if version_match:
        version = version_match.group(1)
    else:
        version = '0.1.0'

# Read the long description from README.md
with open("README.md", "r") as fh:
    long_description = fh.read()

# Get the requirements
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f.readlines() if line.strip()]

setup(
    name="rosabeats",
    version=version,
    author="John Fleming",
    author_email="john@example.com",  # Replace with actual email if available
    description="Audio beat detection, segmentation, and remixing library using librosa",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jbff/rosabeats",
    packages=find_packages(),
    package_data={
        "rosabeats": ["docs/*"],
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
    ],
    python_requires=">=3.6",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "beatrecipe-processor=rosabeats.beatrecipe_processor:main",
            "segment-song=rosabeats.segment_song:main",
            "segment-song-segmentino=rosabeats.segment_song_segmentino:main",
        ],
    },
)

