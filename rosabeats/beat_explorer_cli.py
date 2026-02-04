#!/usr/bin/env python
"""Interactive CLI for exploring beats and bars in audio files.

This module provides a keyboard-driven interface for navigating through
beats and bars in audio files using the rosabeats beat tracking engine.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from rosabeats.rosabeats import rosabeats


class BeatExplorerCLI:
    """Interactive beat explorer with keyboard navigation.

    This class wraps a rosabeats instance and adds state tracking for
    the current beat position, along with navigation methods.

    Attributes:
        rb: The underlying rosabeats instance
        current_beat_index: Current beat position (0-indexed)
    """

    def __init__(self, rb: rosabeats) -> None:
        """Initialize the beat explorer.

        Args:
            rb: A rosabeats instance with beats already tracked
        """
        self.rb = rb
        self.current_beat_index: int = rb.downbeat if rb.downbeat else 0

    @property
    def total_beats(self) -> int:
        """Total number of beats in the track."""
        return self.rb.total_beats

    @property
    def total_bars(self) -> int:
        """Total number of complete bars in the track."""
        return self.rb.total_bars

    @property
    def beatsperbar(self) -> int:
        """Number of beats per bar."""
        return self.rb.beatsperbar

    @property
    def downbeat(self) -> int:
        """Beat index of the first downbeat."""
        return self.rb.downbeat

    def current_beat(self) -> int:
        """Get the current beat index.

        Returns:
            Current beat index (0-indexed)
        """
        return self.current_beat_index

    def current_bar(self) -> Optional[int]:
        """Get the bar number containing the current beat.

        Returns:
            Bar number, or None if current beat is before the first full bar
        """
        if self.current_beat_index < self.downbeat:
            return None
        return (self.current_beat_index - self.downbeat) // self.beatsperbar

    def goto_beat(self, n: int) -> None:
        """Set current position to beat n.

        Args:
            n: Beat index to go to (clamped to valid range)
        """
        self.current_beat_index = max(0, min(n, self.total_beats - 1))

    def goto_bar(self, m: int) -> None:
        """Set current position to the first beat of bar m.

        Args:
            m: Bar number to go to (clamped to valid range)
        """
        m = max(0, min(m, self.total_bars - 1))
        self.current_beat_index = m * self.beatsperbar + self.downbeat

    def first_beat_of_current_bar(self) -> int:
        """Get the first beat index of the current bar.

        Returns:
            Beat index of the first beat in the current bar
        """
        bar = self.current_bar()
        if bar is None:
            return 0
        return bar * self.beatsperbar + self.downbeat

    def next_beat(self, step: int = 1) -> bool:
        """Move forward by step beats.

        Args:
            step: Number of beats to advance

        Returns:
            True if moved, False if at end of track
        """
        new_pos = self.current_beat_index + step
        if new_pos >= self.total_beats:
            self.current_beat_index = self.total_beats - 1
            return False
        self.current_beat_index = new_pos
        return True

    def prev_beat(self, step: int = 1) -> bool:
        """Move backward by step beats.

        Args:
            step: Number of beats to go back

        Returns:
            True if moved, False if at beginning of track
        """
        new_pos = self.current_beat_index - step
        if new_pos < 0:
            self.current_beat_index = 0
            return False
        self.current_beat_index = new_pos
        return True

    def next_bar(self) -> bool:
        """Move forward by one bar.

        Returns:
            True if moved, False if at end of track
        """
        return self.next_beat(self.beatsperbar)

    def prev_bar(self) -> bool:
        """Move backward by one bar.

        Returns:
            True if moved, False if at beginning of track
        """
        return self.prev_beat(self.beatsperbar)

    def play_current_beat(self, silent: bool = False) -> None:
        """Play the current beat.

        Args:
            silent: Suppress console output
        """
        self.rb.play_beat(self.current_beat_index, silent=silent)

    def play_current_bar(self, silent: bool = False) -> None:
        """Play all beats in the current bar.

        Args:
            silent: Suppress console output
        """
        first = self.first_beat_of_current_bar()
        for b in range(first, min(first + self.beatsperbar, self.total_beats)):
            self.rb.play_beat(b, silent=silent)

    def play_manually_by_step(self) -> None:
        """Run the interactive keyboard navigation loop.

        Requires easy_getch to be installed (pip install rosabeats[explorer]).
        """
        try:
            from easy_getch import getch
        except ImportError:
            print("Error: easy_getch is required for interactive mode.")
            print("Install with: pip install rosabeats[explorer]")
            print("         or: uv sync --extra explorer")
            sys.exit(1)

        step = 1

        while True:
            print("i - prev beat")
            print("o - this beat")
            print("p - next beat")
            print("s - change step for prev/next [%d]" % step)
            print("g - go to beat n")
            print(" ---")
            print("q - prev bar")
            print("w - this bar")
            print("e - next bar")
            print("m - go to bar n")
            print(" ---")
            print("Q = quit")
            bar = self.current_bar()
            bar_str = str(bar) if bar is not None else "pickup"
            print("[beat %d / %d, bar %s / %d]" % (
                self.current_beat(),
                self.total_beats,
                bar_str,
                self.total_bars
            ))
            print("==> ", end="", flush=True)
            choice = getch()
            print(choice, flush=True)

            if choice == 'Q':
                print("!! quitting", flush=True)
                break

            if choice == 's':
                try:
                    step = int(input("step = "))
                except ValueError:
                    print("Invalid step value")
                    continue

            elif choice == 'g':
                try:
                    beat_num = int(input("beat = "))
                    self.goto_beat(beat_num)
                    self.play_current_beat(silent=True)
                except ValueError:
                    print("Invalid beat number")

            elif choice == 'm':
                try:
                    bar_num = int(input("bar = "))
                    self.goto_bar(bar_num)
                    self.play_current_beat(silent=True)
                except ValueError:
                    print("Invalid bar number")

            elif choice == 'i':
                if not self.prev_beat(step):
                    print("** beginning of song **", flush=True)
                    continue
                self.play_current_beat(silent=True)

            elif choice == 'o':
                self.play_current_beat(silent=True)

            elif choice == 'p':
                if not self.next_beat(step):
                    print("** end of song **", flush=True)
                    continue
                self.play_current_beat(silent=True)

            elif choice == 'q':
                if not self.prev_bar():
                    print("** beginning of song **", flush=True)
                    continue
                self.play_current_bar(silent=True)

            elif choice == 'w':
                self.play_current_bar(silent=True)

            elif choice == 'e':
                if not self.next_bar():
                    print("** end of song **", flush=True)
                    continue
                self.play_current_bar(silent=True)


def main() -> None:
    """Entry point for beat-explorer CLI."""
    parser = argparse.ArgumentParser(
        description="Interactive beat explorer for audio files"
    )
    parser.add_argument("audio_file", help="Audio file to explore")
    parser.add_argument(
        "--beats-per-bar", "-b",
        type=int,
        default=4,
        help="Number of beats per bar (default: 4)"
    )
    parser.add_argument(
        "--downbeat", "-d",
        type=int,
        default=0,
        help="Beat index of first downbeat (default: 0)"
    )
    parser.add_argument(
        "--auto-downbeat", "-a",
        action="store_true",
        help="Auto-detect downbeat using DBN"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )

    args = parser.parse_args()

    song = rosabeats(args.audio_file, debug=args.debug)
    song.track_beats(beatsper=args.beats_per_bar, downbeat=args.downbeat)

    if args.auto_downbeat:
        detected = song.detect_downbeat(args.beats_per_bar)
        print(f"Auto-detected downbeat at beat {detected}")
        song.downbeat = detected
        song.total_bars = (song.total_beats - detected) // args.beats_per_bar

    song.enable_output_play()
    song.init_outputs()

    explorer = BeatExplorerCLI(song)
    try:
        explorer.play_manually_by_step()
    finally:
        song.shutdown()


if __name__ == "__main__":
    main()
