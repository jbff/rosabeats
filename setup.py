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
        version = '0.1.3'

# Read the long description from README.md
with open("README.md", "r") as fh:
    long_description = fh.read()

# Get the base requirements
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f.readlines() if line.strip()]

setup(
    name="rosabeats",
    version=version,
    author="John Fleming",
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
    extras_require={
        'ffms2': ['ffms2'],  # Optional dependency for audio file handling
        'vamp': ['vamp'],    # Optional dependency for Vamp plugin support
        'all': ['ffms2', 'vamp'],  # Install all optional dependencies
    },
    entry_points={
        "console_scripts": [
            "beatrecipe-processor=rosabeats.beatrecipe_processor:main",
            "segment-song=rosabeats.segment_song:main",
            "beatswitch=rosabeats.beatswitch:main",
            "rosabeats-shell=rosabeats.rosabeats_shell:main",
        ],
    },
)

