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

def get_segment_letter(cluster_num):
    """Convert cluster number to letter (0->A, 1->B, ..., 25->Z, 26->AA, etc.)"""
    if cluster_num < 26:
        return chr(ord('A') + cluster_num)
    else:
        # For clusters beyond 25, use AA, AB, etc.
        first = cluster_num // 26 - 1
        second = cluster_num % 26
        return chr(ord('A') + first) + chr(ord('A') + second)

def generate_segment_names(segments):
    """Generate letter-based names for segments with repeat markers.

    First occurrence of cluster 0 -> "A"
    Second occurrence of cluster 0 -> "A2"
    Third occurrence -> "A3"
    First occurrence of cluster 1 -> "B", etc.

    Returns:
        list: List of segment names in order
    """
    # Track how many times we've seen each cluster label
    cluster_counts = {}
    names = []

    for seg in segments:
        cluster = seg['label']
        if cluster not in cluster_counts:
            cluster_counts[cluster] = 0

        # Get base letter for this cluster
        letter = get_segment_letter(cluster)

        # Add number suffix for repeats (A, A2, A3, ...)
        repeat_count = cluster_counts[cluster]
        if repeat_count > 0:
            name = letter + str(repeat_count + 1)
        else:
            name = letter

        names.append(name)
        cluster_counts[cluster] += 1

    return names

def main(args=None):
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description='Segment audio file and track beats using Laplacian spectral clustering',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('audiofile', help='Audio file to process')
    parser.add_argument('--max-clusters', type=int, default=12,
                       help='Maximum number of clusters for segmentation')
    parser.add_argument('--beatsper', type=int, default=8,
                       help='Number of beats per bar')
    parser.add_argument('--downbeat', type=int, default=None,
                       help='Beat index of first downbeat (default: 0)')
    parser.add_argument('--auto-downbeat', action='store_true',
                       help='Auto-detect downbeat using heuristics (or madmom if available)')
    parser.add_argument('--output', help='Output file path (default: input filename with .bri extension)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode for detailed processing information')

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
    print(f"  Max clusters: {args.max_clusters}")
    print(f"  Beats per bar: {args.beatsper}")
    if args.downbeat is not None:
        downbeat_str = str(args.downbeat)
    elif args.auto_downbeat:
        downbeat_str = "auto-detect"
    else:
        downbeat_str = "0 (default)"
    print(f"  Downbeat: {downbeat_str}")
    print(f"  Output file: {output}")
    if args.debug:
        print_warning("Debug mode enabled - detailed processing information will be shown")

    # Process the audio file
    print_step("Loading audio file")
    s = rosabeats(args.audiofile, debug=args.debug)
    print_success(f"Loaded {os.path.basename(args.audiofile)}")

    print_step("Tracking beats")
    # Determine downbeat value
    if args.downbeat is not None:
        downbeat = args.downbeat
    elif args.auto_downbeat:
        # Auto-detect using DBN approach
        s.track_beats(args.beatsper, downbeat=0)  # Track first to get beat timings
        print_step("Auto-detecting downbeat using DBN")
        downbeat = s.detect_downbeat_dbn(args.beatsper)
        s.downbeat = downbeat
        s.total_bars = int((s.total_beats - s.downbeat) / s.beatsperbar)
    else:
        downbeat = 0

    if not args.auto_downbeat:
        s.track_beats(args.beatsper, downbeat)
    print_success(f"Found {s.total_beats} beats in {s.total_bars} bars")

    print_step("Segmenting audio")
    s.segment(max_clusters=args.max_clusters)
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
        f.write(f"beats_bar {s.beatsperbar} {s.downbeat}\n")
        f.write(f"# total beats = {s.total_beats}\n")
        f.write(f"# total bars = {s.total_bars} (beats {s.downbeat}-{s.downbeat + (s.beatsperbar * s.total_bars)})\n")

        # Generate letter-based segment names
        segment_names = generate_segment_names(s.segments)

        # Process and write segment information
        bars_defs = []
        beats_defs = []
        for idx, seg in enumerate(s.segments):
            seg_name = segment_names[idx]

            # Print segment information to console
            print(f"\n{Colors.BOLD}Segment {seg_name}:{Colors.ENDC}")
            print(f"  Cluster: {seg['label']}")
            print(f"  Duration: {seg['duration']:.2f} seconds")

            if len(seg["bars"]) >= 1:
                # Filter out negative bars (pickup beats before downbeat)
                valid_bars = [b for b in seg["bars"] if b >= 0]
                if len(valid_bars) >= 1:
                    print(f"  Bars: {valid_bars[0]}-{valid_bars[-1]}")
                    bars_defs.append(f"def {seg_name} bars {valid_bars[0]}-{valid_bars[-1]}")
                elif len(seg["bars"]) >= 1:
                    # All bars are negative (pickup section)
                    print(f"  Bars: (pickup) {seg['bars'][0]}-{seg['bars'][-1]}")

            if len(seg["beats"]) >= 1:
                print(f"  Beats: {seg['beats'][0]}-{seg['beats'][-1]}")
                beats_defs.append(f"def {seg_name}_beats beats {seg['beats'][0]}-{seg['beats'][-1]}\t# dur = {seg['duration']:.2f}s")

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
