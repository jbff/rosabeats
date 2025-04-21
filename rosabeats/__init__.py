"""
rosabeats: Audio beat detection, segmentation, and remixing library

This package provides tools for audio beat detection, segmentation, and remixing.
It leverages the power of librosa and other audio processing libraries to enable
precise beat tracking, song segmentation, and creative audio manipulation.

Main features:
- Beat Detection: Automatically detect beats and tempo in audio files
- Bar Analysis: Group beats into bars with configurable beats-per-bar
- Audio Segmentation: Segment songs into structural parts
- Audio Remixing: Create remixes by manipulating beats and bars
- Beat Recipe Files: Save and load beat patterns as reusable recipes
"""

__version__ = '0.1.0'

# Import main classes and functions from the module
from .rosabeats import rosabeats

# Expose key functionality at package level
__all__ = ['rosabeats']

