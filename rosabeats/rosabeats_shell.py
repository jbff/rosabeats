#!/usr/bin/env python

import sys
import os.path
import random
import cmd
import rosabeats


def parse_range(arg):
    """Parse a range argument like '8' or '8-16' into a list of integers.

    Returns list of ints, or None on error.
    """
    arg = arg.strip()
    if not arg:
        return None

    try:
        if "-" in arg:
            parts = arg.split("-", maxsplit=1)
            start = int(parts[0])
            stop = int(parts[1])
        else:
            start = int(arg)
            stop = start
    except (ValueError, IndexError):
        print(f"invalid range: '{arg}' - use e.g. '8' or '8-16'")
        return None

    if start > stop:
        step = -1
    else:
        step = 1

    return list(range(start, (stop + 1) if step >= 0 else (stop - 1), step))


def parse_int(arg, name="argument"):
    """Parse an integer argument. Returns int or None on error."""
    try:
        return int(arg.strip())
    except (ValueError, AttributeError):
        print(f"{name} must be an integer")
        return None


def parse_float(arg, name="argument"):
    """Parse a float argument. Returns float or None on error."""
    try:
        return float(arg.strip())
    except (ValueError, AttributeError):
        print(f"{name} must be a number")
        return None


class rosabeats_shell(cmd.Cmd, rosabeats.rosabeats):
    intro = "Welcome to the rosabeats shell. Type 'help' for commands."
    prompt = "R> "

    def __init__(self):
        cmd.Cmd.__init__(self)
        rosabeats.rosabeats.__init__(self)
        self.macros = {}

    def preloop(self):
        self.enable_output_play()
        self.disable_output_beats()
        self.disable_output_save()

    # --- Macro management ---

    def define_macro(self, name, value):
        if name in self.macros:
            print(f"redefining macro '{name}'")
        self.macros[name] = value

    def play_macro(self, name, times=1):
        if name not in self.macros:
            print(f"macro '{name}' not defined")
            return False

        macro = self.macros[name]
        print(f"[*] {times} x {name} [{macro}]")

        for _ in range(times):
            print(f"-> {macro}")
            self.onecmd(macro)
        return True

    # --- Commands ---

    def do_file(self, arg):
        """Load an audio file: file <path>"""
        if not arg.strip():
            print("usage: file <path>")
            return

        filename = arg.strip()
        print(f"loading {filename}")
        self.setfile(filename)

    def do_beats_bar(self, arg):
        """Set beats per bar and downbeat: beats_bar <beats_per_bar> <downbeat>"""
        args = arg.split()
        if len(args) < 2:
            print("usage: beats_bar <beats_per_bar> <downbeat>")
            return

        beatsper = parse_int(args[0], "beats_per_bar")
        downbeat = parse_int(args[1], "downbeat")

        if beatsper is None or downbeat is None:
            return

        if not self.sourcefile:
            print("error: load a file first with 'file <path>'")
            return

        print("Tracking beats...")
        self.track_beats(beatsper=beatsper, downbeat=downbeat)
        print(f"Found {self.total_beats} beats in {self.total_bars} bars")
        self.init_outputs()

    def do_beats(self, arg):
        """Play beats: beats <N> or beats <N-M> [times]"""
        args = arg.split()
        if not args:
            print("usage: beats <N> or beats <N-M> [times]")
            return

        beats = parse_range(args[0])
        if beats is None:
            return

        times = 1
        if len(args) > 1:
            times = parse_int(args[1], "times")
            if times is None:
                return

        if len(beats) > 1:
            print(f"[*] {times} x beats {beats[0]}-{beats[-1]}")
        else:
            print(f"[*] {times} x beat {beats[0]}")

        for _ in range(times):
            self.play_beats(beats)

    def do_bars(self, arg):
        """Play bars: bars <N> or bars <N-M> [times]"""
        args = arg.split()
        if not args:
            print("usage: bars <N> or bars <N-M> [times]")
            return

        bars = parse_range(args[0])
        if bars is None:
            return

        times = 1
        if len(args) > 1:
            times = parse_int(args[1], "times")
            if times is None:
                return

        if len(bars) > 1:
            print(f"[*] {times} x bars {bars[0]}-{bars[-1]}")
        else:
            print(f"[*] {times} x bar {bars[0]}")

        for _ in range(times):
            self.play_bars(bars)

    def do_bars_rev(self, arg):
        """Play bars with beats reversed: bars_rev <N-M> [times]"""
        args = arg.split()
        if not args:
            print("usage: bars_rev <N-M> [times]")
            return

        bars = parse_range(args[0])
        if bars is None:
            return

        times = 1
        if len(args) > 1:
            times = parse_int(args[1], "times")
            if times is None:
                return

        if len(bars) > 1:
            print(f"[*] {times} x bars_rev {bars[0]}-{bars[-1]}")
        else:
            print(f"[*] {times} x bar_rev {bars[0]}")

        for _ in range(times):
            self.play_bars(bars, reverse=True)

    def do_beats_shuf(self, arg):
        """Play beats in shuffled order: beats_shuf <N-M> [times]"""
        args = arg.split()
        if not args:
            print("usage: beats_shuf <N-M> [times]")
            return

        beats = parse_range(args[0])
        if beats is None:
            return

        times = 1
        if len(args) > 1:
            times = parse_int(args[1], "times")
            if times is None:
                return

        print(f"[*] {times} x beats_shuf {beats[0]}-{beats[-1]}")

        for _ in range(times):
            random.shuffle(beats)
            self.play_beats(beats)

    def do_bars_shuf(self, arg):
        """Play bars in shuffled order: bars_shuf <N-M> [times]"""
        args = arg.split()
        if not args:
            print("usage: bars_shuf <N-M> [times]")
            return

        bars = parse_range(args[0])
        if bars is None:
            return

        times = 1
        if len(args) > 1:
            times = parse_int(args[1], "times")
            if times is None:
                return

        print(f"[*] {times} x bars_shuf {bars[0]}-{bars[-1]}")

        for _ in range(times):
            random.shuffle(bars)
            self.play_bars(bars)

    def do_beat_div(self, arg):
        """Play subdivided beat: beat_div <beat> <divisor> [times]"""
        args = arg.split()
        if len(args) < 2:
            print("usage: beat_div <beat> <divisor> [times]")
            return

        beat = parse_int(args[0], "beat")
        divisor = parse_int(args[1], "divisor")
        if beat is None or divisor is None:
            return

        times = 1
        if len(args) > 2:
            times = parse_int(args[2], "times")
            if times is None:
                return

        print(f"[*] {times} x beat {beat}/{divisor}")

        for _ in range(times):
            self.play_beat(beat, divisor=divisor, silent=True)
        print()

    def do_rest(self, arg):
        """Insert silence: rest <beats> [times]"""
        args = arg.split()
        if not args:
            print("usage: rest <beats> [times]")
            return

        rest_beats = parse_float(args[0], "beats")
        if rest_beats is None:
            return

        times = 1
        if len(args) > 1:
            times = parse_int(args[1], "times")
            if times is None:
                return

        print(f"[*] {times} x rest({rest_beats})")

        for _ in range(times):
            self.rest(rest_beats)

    def do_def(self, arg):
        """Define a macro: def <name> <command>"""
        args = arg.split(None, 1)  # Split into name and rest
        if len(args) < 2:
            print("usage: def <name> <command>")
            return

        name = args[0]
        value = args[1]

        self.define_macro(name, value)
        print(f"defined {name} => {value}")

    def do_play(self, arg):
        """Play a macro: play <name> [times]"""
        args = arg.split()
        if not args:
            print("usage: play <name> [times]")
            return

        name = args[0]
        times = 1
        if len(args) > 1:
            times = parse_int(args[1], "times")
            if times is None:
                return

        self.play_macro(name, times)

    def do_ls(self, arg):
        """List defined macros"""
        if self.macros:
            print(", ".join(self.macros.keys()))
        else:
            print("(no macros defined)")

    def do_lsdef(self, arg):
        """List macros with their definitions"""
        if not self.macros:
            print("(no macros defined)")
            return
        for name, value in self.macros.items():
            print(f"  {name}: {value}")

    def do_save(self, arg):
        """Save current session to a .br file: save <filename>"""
        if not arg.strip():
            print("usage: save <filename>")
            return

        filename = arg.strip()

        if not self.sourcefile:
            print("error: no audio file loaded")
            return

        print(f"saving to {filename}")
        with open(filename, "w") as f:
            f.write(f"file {self.sourcefile}\n")
            f.write(f"beats_bar {self.beatsperbar} {self.downbeat}\n")
            for name, value in self.macros.items():
                f.write(f"def {name} {value}\n")
        print("saved")

    def do_load(self, arg):
        """Load a .br or .bri file: load <filename>"""
        if not arg.strip():
            print("usage: load <filename>")
            return

        filename = arg.strip()
        self.load_recipe_file(filename)

    def load_recipe_file(self, filename):
        """Load and execute commands from a .br or .bri file."""
        try:
            with open(filename, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"error: file not found: {filename}")
            return False
        except Exception as e:
            print(f"error reading {filename}: {e}")
            return False

        print(f"loading {filename}...")
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Execute the command
            self.onecmd(line)

        print(f"loaded {filename}")
        if self.sourcefile:
            print(f"  audio: {self.sourcefile}")
        if self.total_beats:
            print(f"  {self.total_beats} beats, {self.total_bars} bars")
        if self.macros:
            print(f"  {len(self.macros)} macros defined")
        return True

    def do_quit(self, arg):
        """Exit the shell"""
        print("goodbye")
        self.shutdown()
        return True  # Signals cmd.Cmd to exit

    def do_exit(self, arg):
        """Exit the shell"""
        return self.do_quit(arg)

    def do_EOF(self, arg):
        """Handle Ctrl+D"""
        print()
        return self.do_quit(arg)

    def default(self, line):
        """Try to play a macro if command not recognized"""
        args = line.split()
        if not args:
            return

        name = args[0]
        if name in self.macros:
            times = 1
            if len(args) > 1:
                times = parse_int(args[1], "times")
                if times is None:
                    return
            self.play_macro(name, times)
        else:
            print(f"unknown command or macro: '{name}'")

    def emptyline(self):
        """Do nothing on empty line (don't repeat last command)"""
        pass


def main():
    """Main entry point for rosabeats-shell."""
    shell = rosabeats_shell()
    shell.preloop()

    # Handle command-line arguments
    if len(sys.argv) > 1:
        filename = sys.argv[1]

        # Check if it's a recipe file (.br or .bri) or an audio file
        if filename.endswith(".br") or filename.endswith(".bri"):
            shell.load_recipe_file(filename)
        else:
            # Treat as audio file
            shell.onecmd(f"file {filename}")

            if len(sys.argv) > 3:
                beatsper = sys.argv[2]
                downbeat = sys.argv[3]
                shell.onecmd(f"beats_bar {beatsper} {downbeat}")

    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        try:
            shell.shutdown()
        except:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
