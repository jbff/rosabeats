#!/usr/bin/env python

import sys
import os.path
import argparse
from rosabeats import rosabeats

# Check if terminal supports colors
def supports_color():
    """Check if the terminal supports color output"""
    if sys.platform == 'win32':
        return False
    if not sys.stdout.isatty():
        return False
    try:
        import curses
        curses.setupterm()
        return curses.tigetnum("colors") > 0
    except:
        return False

# Check if terminal supports emojis
def supports_emojis():
    """Check if the terminal supports emoji output"""
    if sys.platform == 'win32':
        return False
    if not sys.stdout.isatty():
        return False
    try:
        # Try to print an emoji and check if it's displayed correctly
        print("\U0001F44D", end='', flush=True)
        return True
    except:
        return False

# ANSI color codes for terminal output
class Colors:
    if supports_color():
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
    else:
        HEADER = BLUE = CYAN = GREEN = YELLOW = RED = ENDC = BOLD = UNDERLINE = ''

# Emoji symbols
class Symbols:
    if supports_emojis():
        CHECK = '✓'
        BULLET = '•'
        WARNING = '⚠'
    else:
        CHECK = '[OK]'
        BULLET = '*'
        WARNING = '[!]'

def print_header(text):
    """Print a formatted header message"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}== {text} =={Colors.ENDC}\n")

def print_step(text):
    """Print a formatted step message"""
    print(f"{Colors.CYAN}{Symbols.BULLET} {text}...{Colors.ENDC}")

def print_success(text):
    """Print a formatted success message"""
    print(f"{Colors.GREEN}{Symbols.CHECK} {text}{Colors.ENDC}")

def print_warning(text):
    """Print a formatted warning message"""
    print(f"{Colors.YELLOW}{Symbols.WARNING} {text}{Colors.ENDC}")

def main(args=None):
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description='Segment audio file and track beats using either laplacian or segmentino methods',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('audiofile', help='Audio file to process')
    parser.add_argument('--method', choices=['laplacian', 'segmentino'], 
                       default='laplacian', help='Segmentation method to use')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug mode for detailed processing information')
    parser.add_argument('--output', help='Output file path (default: input filename with .bri extension)')
    parser.add_argument('--beatsper', type=int, default=8,
                       help='Number of beats per bar')
    parser.add_argument('--firstfull', type=int, default=0,
                       help='First full bar number')
    
    args = parser.parse_args()
    
    # Set output file if not specified
    if args.output is None:
        basename = os.path.basename(args.audiofile)
        stub, _ = os.path.splitext(basename)
        output = stub + ".bri"
    else:
        output = args.output

    # Print processing information
    print_header("Audio Segmentation and Beat Tracking")
    print(f"{Colors.BOLD}Input:{Colors.ENDC}")
    print(f"  Audio file: {args.audiofile}")
    print(f"  Method: {args.method}")
    print(f"  Beats per bar: {args.beatsper}")
    print(f"  First full bar: {args.firstfull}")
    print(f"  Output file: {output}")
    if args.debug:
        print_warning("Debug mode enabled - detailed processing information will be shown")

    # Process the audio file
    print_step("Loading audio file")
    s = rosabeats(args.audiofile, debug=args.debug)
    print_success(f"Loaded {os.path.basename(args.audiofile)}")

    print_step("Tracking beats")
    s.track_beats(args.beatsper, args.firstfull)
    print_success(f"Found {s.total_beats} beats in {s.total_bars} bars")

    print_step(f"Segmenting with {args.method} method")
    s.segment(method=args.method)
    print_success(f"Identified {s.total_segments} segments")

    print_step("Assigning beats and bars to segments")
    s.segmentize_beats()
    print_success("Completed beat and bar assignment")

    # Write results to output file
    print_step(f"Writing results to {output}")
    with open(output, "w") as f:
        # Write header information
        f.write("##BEATS## This was segmented and tracked using librosa's beat tracker\n\n")
        f.write(f"file {s.sourcefile}\n")
        f.write(f"beats_bar {s.beatsperbar} {s.firstfullbar}\n")
        f.write(f"# total beats = {s.total_beats}\n")
        f.write(f"# total bars = {s.total_bars} (beats {s.firstfullbar}-{s.firstfullbar + (s.beatsperbar * s.total_bars)})\n")

        # Process and write segment information
        bars_defs = []
        beats_defs = []
        for idx, seg in enumerate(s.segments):
            # Print segment information to console
            print(f"\n{Colors.BOLD}Segment {idx}:{Colors.ENDC}")
            print(f"  Label: {seg['label']}")
            print(f"  Duration: {seg['duration']:.2f} seconds")
            
            if len(seg["bars"]) >= 1:
                print(f"  Bars: {seg['bars'][0]}-{seg['bars'][-1]}")
                bars_defs.append(f"def {seg['label']}_{idx} bars {seg['bars'][0]}-{seg['bars'][-1]}")
            
            if len(seg["beats"]) >= 1:
                print(f"  Beats: {seg['beats'][0]}-{seg['beats'][-1]}")
                beats_defs.append(f"def {seg['label']}_{idx}_beats beats {seg['beats'][0]}-{seg['beats'][-1]}\t# dur = {seg['duration']:.2f}s, beats {seg['beats'][0]}-{seg['beats'][-1]}")

        # Write segment definitions to file
        for d in bars_defs:
            f.write(f"{d}\n")
        f.write("\n")
        for d in beats_defs:
            f.write(f"{d}\n")
        f.write("\n")

    print_success(f"Results written to {output}")
    print_header("Processing Complete")

if __name__ == "__main__":
    main()
