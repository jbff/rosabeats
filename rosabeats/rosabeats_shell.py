#!/usr/bin/env python

import re, sys, os.path, random
import cmd, rosabeats


class rosabeats_shell(cmd.Cmd, rosabeats.rosabeats):
    intro = "welcome to the rosabeats shell"
    prompt = "R@; "

    def define_macro(self, name, value):
        if self.is_defined_macro(name):
            print("redefining macro %s" % name)
        self.macros[name] = value
        return True

    def play_macro(self, name, times):
        if not self.is_defined_macro(name):
            print("macro %s not defined" % name)
            return False

        macro = self.macros[name]

        print("[*] %d * %s [%s]" % (times, name, macro))

        for x in range(times):
            print("-> %s" % macro)
            self.onecmd(self.precmd(macro))

    def is_defined_macro(self, name):
        if self.macros.get(name, None) is not None:
            return True
        else:
            return False

    def arg1_parse_range(self):
        start = None
        stop = None
        step = None

        try:
            if "-" in self.cmd_args[0]:
                start, stop = self.cmd_args[0].split("-", maxsplit=1)
                start = int(start)
                stop = int(stop)

            else:
                start = int(self.cmd_args[0])
                stop = start
        except:
            print("first argument must be valid range, e.g. '8' or '8-10'")
            return None

        if start > stop:
            step = -1
        else:
            step = 1

        return [x for x in range(start, (stop + 1) if step >= 0 else (stop - 1), step)]

    # constructor
    def __init__(self):
        cmd.Cmd.__init__(self)
        rosabeats.rosabeats.__init__(self)
        #       super(cmd.Cmd, self)
        #       super(rosabeats.rosabeats, self)
        #       super().__init__()
        self.macros = dict()
        self.cmd_args = None

    # pre & post hooks
    def precmd(self, line):
        if line.strip() != '':
            print("precmd: saving cmd as %s" % line)
            self.prev_cmd = line
            self.cmd_args = line.split()[1:]
        return line

    def preloop(self):
        self.enable_output_play()
        self.disable_output_beats()
        self.disable_output_save()

    def arg1_float(self):
        try:
            arg1 = float(self.cmd_args[0])
        except:
            print("arg1 must be float")
            return None
        return arg1

    def arg1_string(self):
        try:
            arg1 = str(self.cmd_args[0])
        except:
            print("arg1 must be string")
            return None
        return arg1

    def arg1_int(self):
        try:
            arg1 = int(self.cmd_args[0])
        except:
            print("arg1 must be int")
            return None
        return arg1

    def arg2_int(self):
        try:
            arg1 = int(self.cmd_args[1])
        except:
            print("arg2 must be int")
            return None
        return arg1

    def arg3_int(self):
        try:
            arg3 = int(self.cmd_args[2])
        except:
            print("arg3 must be int")
            return None
        return arg3

    def arg2_valid_repeat(self):
        # no second arg so 1 by default
        if len(self.cmd_args) < 2:
            return 1

        return self.arg2_int()

    def arg3_valid_repeat(self):
        # no third arg so 1 by default
        if len(self.cmd_args) < 3:
            return 1

        return self.arg3_int()

    # command handlers
    def do_rest(self, arg):
        rest = self.arg1_float()
        times = self.arg2_valid_repeat()

        if rest is None or times is None:
            return False

        print("[*] %d * %g beat(s) of rest" % (times, rest))

        for x in range(times):
            self.rest(rest)

    def do_beats(self, arg):
        beats = self.arg1_parse_range()
        times = self.arg2_valid_repeat()

        if beats is None or times is None:
            return False

        print("[*] %d * " % times, end="", flush=True)

        if len(beats) > 1:
            print("(beats %d-%d) " % (beats[0], beats[-1]))
        else:
            print("(beat %d) " % beats[0])

        for x in range(times):
            self.play_beats(beats)

    def do_beat_div(self, arg):
        beat = self.arg1_int()
        divisor = self.arg2_int()
        times = self.arg3_valid_repeat()

        if beats is None or divisor is None or times is None:
            return False

        print("[*] %d * (1/%d beats) " % (times, divisor), flush=True)

        for x in range(times):
            print("%d/%d " % (beat, divisor), end="", flush=True)
            self.play_beat(beat, divisor=divisor, silent=True)

        print(flush=True)

    def do_beats_shuf(self, arg):
        beats = self.arg1_parse_range()
        times = self.arg2_valid_repeat()

        if beats is None or times is None:
            return False

        print("[*] %d * " % times, end="", flush=True)
        print("(shuffled beats %d-%d] " % (beats[0], beats[-1]), flush=True)

        for x in range(times):
            random.shuffle(beats)
            self.play_beats(beats)

    def do_bars(self, arg):
        bars = self.arg1_parse_range()
        times = self.arg2_valid_repeat()

        if bars is None or times is None:
            return False

        print("[*] %d * " % times, end="", flush=True)
        if len(bars) > 1:
            print("(bars %d-%d) " % (bars[0], bars[-1]), flush=True)
        else:
            print("(bar %d) " % bars[0], flush=True)

        for x in range(times):
            self.play_bars(bars)

    def do_bars_rev(self, arg):
        bars = self.arg1_parse_range()
        times = self.arg2_valid_repeat()

        if bars is None or times is None:
            return False

        print("[*] %d * " % times, end="", flush=True)
        if len(bars) > 1:
            print("(rev bars %d-%d) " % (bars[0], bars[-1]), flush=True)
        else:
            print("(rev bar %d) " % bars[0], flush=True)

        for x in range(times):
            self.play_bars(bars, reverse=True)

    def do_bars_shuf(self, arg):
        bars = self.arg1_parse_range()
        times = self.arg2_valid_repeat()

        if bars is None or times is None:
            return False

        print("[*] %d * " % times, end="", flush=True)
        print("(shuffled bars %d-%d) " % (bars[0], bars[-1]), flush=True)

        for x in range(times):
            random.shuffle(bars)
            self.play_bars(bars)

    def do_play(self, arg):
        name = self.arg1_string()
        times = self.arg2_valid_repeat()

        if name is None or times is None:
            return False

        self.play_macro(name, times)

    def args_valid_value(self):
        try:
            args = " ".join(self.cmd_args[1:])
        except:
            print("this cmd requires the value to assign")
            return None
        return args

    def do_def(self, arg):
        name = self.arg1_string()
        value = self.args_valid_value()

        if name is None or value is None:
            return False

        print("[*] (def seg: %s = %s)" % (name, value))

        self.define_macro(name, value)
        print("defined %s => %s" % (name, value))

    def do_help(self, arg):
        print("valid commands are:")
        print("  beats, bars, beats_shuf, bars_shuf, beat_div, bars_rev, rest")
        print("  for predefined macros: ls, lsdef, play, or just type the def name")
        print("  and finally: save, help, quit")

    def do_lsdef(self, arg):
        for name, value in self.macros.items():
            print("%15s %15s" % (name, value))

    def do_ls(self, arg):
        print(", ".join(list(self.macros.keys())))

    def do_quit(self, arg):
        self.shutdown()
        sys.exit(0)

    def do_file(self, arg):
        filename = self.arg1_string()

        if filename is None:
            return False

        print("setting filename to %s" % filename)
        self.setfile(filename)

    def do_beats_bar(self, arg):
        per = self.arg1_int()
        first = self.arg2_int()

        if per is None or first is None:
            return False

        # if we know our audio source, load it, analyze it, and init outputs
        if self.sourcefile:
            print("One moment as we track your beats for you, madame...")
            self.track_beats(beatsper=per, firstfull=first)
            print("%d beats, %d bars" % (self.total_beats, self.total_bars))
            self.init_outputs()
        else:
            print("specify file before beats_bar")
            return False

    def do_save(self, arg):
        filename = self.arg1_string()
        print("saving %s" % filename)
        with open(filename, "w") as f:
            print("file %s" % self.sourcefile, file=f)
            print("beats_bar %d %d" % (self.beatsperbar, self.firstfullbar), file=f)
            for name, value in self.macros.items():
                print("def %s %s" % (name, value), file=f)

    def default(self, line):
        self.cmd_args = line.split()
        self.do_play(line)


#   def emptyline(self):
#       print("repeating: %s" % self.prev_cmd)
#       self.onecmd(self.precmd(self.prev_cmd))


def main():
    """
    Main function for rosabeats-shell command-line tool.
    
    Usage: rosabeats-shell [audio_file [beats_per_bar first_full_bar]]
    
    Args:
        audio_file: Optional audio file to analyze
        beats_per_bar: Number of beats per bar (if audio_file is provided)
        first_full_bar: First full bar number (if audio_file is provided)
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        load_file = False
        try:
            filename = sys.argv[1]
            beats_bar = " ".join(sys.argv[2:])
            load_file = True
            print(f"Audio file: {filename}")
            print(f"Beats/bar settings: {beats_bar}")
        except IndexError:
            # No command line arguments is valid
            pass

        s = rosabeats_shell()
        if load_file:
            s.preloop()
            s.onecmd(s.precmd(f"file {filename}"))
            s.onecmd(s.precmd(f"beats_bar {beats_bar}"))

        s.cmdloop()
        return 0
    except KeyboardInterrupt:
        print("\nShutting down...")
        if 's' in locals() and hasattr(s, 'shutdown'):
            s.shutdown()
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    finally:
        # Ensure we clean up resources even if there's an error
        if 's' in locals() and hasattr(s, 'shutdown'):
            try:
                s.shutdown()
            except:
                pass


if __name__ == "__main__":
    sys.exit(main())
