#!/usr/bin/env python

import re, sys, os.path, random, logging

from rosabeats import rosabeats


class beatrecipe_processor(rosabeats):
    @staticmethod
    def ilist(indices):
        start, stop, step = indices

        r = range(start, (stop + 1) if step >= 0 else (stop - 1), step)
        return [x for x in r]

    @staticmethod
    def parse_first_last(args):
        first = None
        last = None
        step = None

        try:
            if re.match(r"[0-9]+\-[0-9]+", args):
                beatrecipe_processor.d_print("parsed target range")
                first, last = args.split("-", maxsplit=1)
                first = int(first)
                last = int(last)

            elif re.match(r"^[0-9]+$", args):
                beatrecipe_processor.d_print("parsed single target")
                first = int(args)
                last = first
        except Exception as e:
            raise e

        if first > last:
            step = -1
        else:
            step = 1

        return (first, last, step)

    #### instance methods ####

    def __init__(self, recipe, interactive=False, loglevel=logging.INFO, debug=False):
        super().__init__(debug=debug)

        self.recipe = recipe
        self.interactive = interactive
        self.recipe_lines = None
        self.macros = dict()

        logging.basicConfig(level=loglevel)
        self.log = logging.getLogger(__name__)
        self.log.setLevel(loglevel)
        self.log.debug("logging activated")

        if interactive:
            # set up our outputs
            self.disable_output_beats()
            self.disable_output_save()
            self.enable_output_play()

        self.read_beatrecipe()

    def parse_error(self, error_info):
        self.log.error("%s" % error_info)

    def read_beatrecipe(self):
        self.recipe_lines = list()
        with open(self.recipe, "r") as f:
            for line in f:
                lines = self.preprocess(line)
                if lines is None:
                    continue

                for cmd in lines:
                    self.recipe_lines.append(cmd)

    def define_macro(self, name, value):
        if self.macros.get(name) is not None:
            self.parse_error("macro %s already defined" % name)
            return False
        self.macros[name] = value
        return True

    def play_macro(self, name, times):
        macro = self.macros.get(name)
        if macro is None:
            self.parse_error("macro %s not defined" % name)

        self.log.info("[*] %d * %s [%s]" % (times, name, macro))

        for x in range(times):
            if self.output_beats:
                self.write_out("# === macro %s ===" % name)
            self.execute_command(macro)

    def is_defined_macro(self, name):
        for key in self.macros:
            if name == key:
                return True

        return False

    def preprocess(self, line):
        line = line.strip()

        # remove leading and trailing whitespace
        line = re.sub(r"^\s+", "", line)
        line = re.sub(r"\s+$", "", line)

        # skip blank lines
        if re.match(r"^$", line):
            return None

        # skip lines that start with hash
        if line.startswith("#"):
            return None

        # remove same line comments but process rest of line
        try:
            line, comment = line.split("#", maxsplit=2)
            line = line.rstrip()
        except:
            # do nothing if no comments to strip
            pass

        # split multiple commands separated by semicolons
        lines = []
        for l in line.split(";"):
            lines.append(l.strip())

        return lines

    def execute_command(self, cmd):
        cmd_elements = cmd.split()

        verb = cmd_elements[0]
        cmd_elements = cmd_elements[1:]

        if verb == "rest":
            try:
                rest = float(cmd_elements[0])
                cmd_elements = cmd_elements[1:]
            except:
                self.parse_error("could not determine decimal value for rest")
                if self.interactive:
                    return True
                else:
                    raise e
            try:
                times = int(cmd_elements[0])
            except:
                times = 1

            print("[*] %d * %g beat(s) of rest" % (times, rest), flush=True)

            for x in range(times):
                self.rest(rest)

        elif verb == "beats":
            try:
                args = cmd_elements[0]
                cmd_elements = cmd_elements[1:]

                beats = beatrecipe_processor.ilist(
                    beatrecipe_processor.parse_first_last(args)
                )
            except Exception as e:
                self.parse_error("could not derive first/last from %s" % args)
                if self.interactive:
                    return True
                else:
                    raise e
            try:
                times = int(cmd_elements[0])
            except:
                times = 1

            print("[*] %d * " % (times), end="", flush=True)

            if len(beats) > 1:
                print("(beats %d-%d) " % (beats[0], beats[-1]), flush=True)
            else:
                print("(beat %d) " % beats[0], flush=True)

            for x in range(times):
                self.play_beats(beats)

        elif verb == "beat_div":
            try:
                beat = int(cmd_elements[0])
                divisor = int(cmd_elements[1])
                cmd_elements = cmd_elements[2:]
            except:
                self.parse_error("invalid beat/divisor")
            try:
                times = int(cmd_elements[0])
            except:
                times = 1

            print("[*] %d * (1/%d beats) " % (times, divisor), flush=True)

            for x in range(times):
                print("%d/%d " % (beat, divisor), end="", flush=True)
                self.play_beat(beat, divisor=divisor, silent=True)

            print(flush=True)

        elif verb == "beats_shuf":
            try:
                args = cmd_elements[0]
                cmd_elements = cmd_elements[1:]

                beats = beatrecipe_processor.ilist(
                    beatrecipe_processor.parse_first_last(args)
                )
            except Exception as e:
                self.parse_error("could not derive first/last from %s" % args)
                if self.interactive:
                    return True
                else:
                    raise e
            try:
                times = int(cmd_elements[0])
            except:
                times = 1

            print("[*] %d * " % times, end="", flush=True)
            print("(shuffled beats %d-%d] " % (beats[0], beats[-1]), flush=True)

            for x in range(times):
                random.shuffle(beats)
                self.play_beats(beats)

        elif verb == "bars":
            try:
                args = cmd_elements[0]
                cmd_elements = cmd_elements[1:]

                bars = beatrecipe_processor.ilist(
                    beatrecipe_processor.parse_first_last(args)
                )
            except Exception as e:
                self.parse_error("could not derive first/last from %s" % args)
                if self.interactive:
                    return True
                else:
                    raise e
            try:
                times = int(cmd_elements[0])
            except:
                times = 1

            print("[*] %d * " % times, end="", flush=True)
            if len(bars) > 1:
                print("(bars %d-%d) " % (bars[0], bars[-1]), flush=True)
            else:
                print("(bar %d) " % bars[0], flush=True)

            for x in range(times):
                self.play_bars(bars)

        elif verb == "bars_rev":
            try:
                args = cmd_elements[0]
                cmd_elements = cmd_elements[1:]

                bars = beatrecipe_processor.ilist(
                    beatrecipe_processor.parse_first_last(args)
                )
            except Exception as e:
                self.parse_error("could not derive first/last from %s" % args)
                if self.interactive:
                    return True
                else:
                    raise e
            try:
                times = int(cmd_elements[0])
            except:
                times = 1

            print("[*] %d * " % times, end="", flush=True)
            if len(bars) > 1:
                print("(rev bars %d-%d) " % (bars[0], bars[-1]), flush=True)
            else:
                print("(rev bar %d) " % bars[0], flush=True)

            for x in range(times):
                self.play_bars(bars, reverse=True)

        elif verb == "bars_shuf":
            try:
                args = cmd_elements[0]
                cmd_elements = cmd_elements[1:]

                bars = beatrecipe_processor.ilist(
                    beatrecipe_processor.parse_first_last(args)
                )
            except Exception:
                self.parse_error("could not derive first/last from %s" % args)
            try:
                times = int(cmd_elements[0])
            except:
                times = 1

            print("[*] %d * " % times, end="", flush=True)
            print("(shuffled bars %d-%d) " % (bars[0], bars[-1]), flush=True)

            for x in range(times):
                random.shuffle(bars)
                self.play_bars(bars)

        elif verb == "play":
            try:
                name = str(cmd_elements[0])
                cmd_elements = cmd_elements[1:]
            except Exception:
                self.parse_error("could not parse name of macro to play")
                if self.interactive:
                    return True
                else:
                    raise e
            try:
                times = int(cmd_elements[0])
            except:
                times = 1

            self.play_macro(name, times)

        elif verb == "def":
            try:
                name = cmd_elements[0]
                value = " ".join(cmd_elements[1:])
                cmd_elements = []
            except:
                self.parse_error("unable to parse macro definition")
                if self.interactive:
                    return True
                else:
                    raise e
            print("[*] (def seg: %s = %s)" % (name, value))

            self.define_macro(name, value)
            print("defined %s => %s" % (name, value))

        elif self.interactive and verb == "help":
            print("valid commands are:")
            print("  beats, bars, beats_shuf, bars_shuf, beat_div, bars_rev, rest")
            print("  for predefined macros: ls, lsdef, play, or just type the def name")
            print("  and finally: help, quit, next")

        elif self.interactive and verb == "lsdef":
            for name, value in self.macros.items():
                print("%15s %15s" % (name, value))

        elif self.interactive and verb == "ls":
            print(", ".join(list(self.macros.keys())))

        elif self.interactive and verb == "quit":
            self.shutdown()
            sys.exit(0)

        elif self.interactive and verb == "next":
            self.shutdown()
            return False

        elif self.is_defined_macro(verb):
            print("[*] cmd '%s' resolves to defined macro" % verb)
            try:
                times = int(cmd_elements[0])
            except:
                times = 1
            self.play_macro(verb, times)

        else:
            self.parse_error("verb %s not recognized" % verb)

        if self.interactive:
            return True

    def process(self):
        for cmd in self.recipe_lines:
            self.execute_command(cmd)

        print("[the end - shutting down outputs]", flush=True)
        self.shutdown()

    def process_interactive(self):
        KeepProcessing = True
        while KeepProcessing:
            print("")
            print("enter beatrecipe command => ", end="", flush=True)

            lines = self.preprocess(input())

            for cmd in lines:
                print(cmd)
                KeepProcessing = self.execute_command(cmd)

    def prepare_file_and_macros(self):
        # this goes through the preprocessd/stored recipe that was loaded
        # and only processes file, beats_bar, and macro deinitions lines
        # all else is ignored
        unprocessed_lines = []
        for line in self.recipe_lines:
            try:
                verb, args = line.split(maxsplit=1)
            except Exception:
                verb = line
                args = ""
            #               self.parse_error("could not split line into verb and args")
            #               sys.exit(1)

            if verb == "file":
                filename = str(args)
                self.setfile(filename)
                # don't actually load until we have beats/bar info

            elif verb == "beats_bar":
                try:
                    per, first = args.split(maxsplit=1)
                    per = int(per)
                    first = int(first)
                except:
                    self.parse_error("could not parse two arguments for beats_bar")
                    sys.exit(1)

                # if we know our audio source, load it, analyze it, and init outputs
                if self.sourcefile:
                    print("One moment as we track your beats for you, madame...")
                    self.track_beats(beatsper=per, downbeat=first)
                    self.init_outputs()
                else:
                    self.parse_error(
                        "a file directive must come before a beats_bar directive"
                    )
                    sys.exit(1)

            elif verb == "def":
                try:
                    name, value = args.split(maxsplit=1)
                except:
                    self.parse_error("unable to parse macro definition")
                    sys.exit(1)

                self.define_macro(name, value)
                print("defined macro %s -=> %s" % (name, value))

            else:
                # these are the only commands we process noninteractively
                unprocessed_lines.append(line)

            self.recipe_lines = unprocessed_lines


def main(args=None):
    output_play = False
    output_save = False
    output_beats = False
    loglevel = logging.INFO
    recipes = []

    # If no args provided, use sys.argv (skipping the script name at index 0)
    if args is None:
        args = sys.argv[1:]

    for arg in args:
        if arg == "-p" or arg == "--play":
            output_play = True

        elif arg == "-s" or arg == "--save":
            output_save = True

        elif arg == "-b" or arg == "--beats":
            output_beats = True

        elif arg == "-d" or arg == "--debug":
            loglevel = logging.DEBUG

        else:
            recipes.append(arg)

    if len(recipes) < 1:
        print("no recipes to process were found on command line")
        sys.exit(1)

    if not (output_play or output_save or output_beats):
        print("must specify one or more of --play, --save, or --beats for output")
        sys.exit(1)

    for recipe in recipes:
        print("processing %s..." % recipe, flush=True)

        stub, ext = os.path.splitext(os.path.basename(recipe))

        p = beatrecipe_processor(
            recipe, interactive=False, loglevel=loglevel, debug=True
        )

        if output_play:
            p.enable_output_play()

        if output_save:
            # /path/to/thisfile.br -> $PWD/thisfile.wav
            wavfile = stub + ".wav"
            p.enable_output_save(wavfile)

        if output_beats:
            # /path/to/thisfile.br -> $PWD/thisfile_beats.br
            beatsfile = stub + "_beats.br"
            p.enable_output_beats(beatsfile)

        # will skip ahead to next one if problem arises
        try:
            p.prepare_file_and_macros()
            p.process()
        except Exception as e:
            print("error processing %s: %s" % (recipe, e), flush=True)
            raise e


if __name__ == "__main__":
    main()
