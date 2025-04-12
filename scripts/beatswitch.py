#!/usr/bin/env python

import sys, random, os.path
import rosabeats


class beatswitcher(rosabeats.rosabeats):
    def __init__(self, infile, debug=False):
        self.infile = infile
        self.debug = debug

        super().__init__(self.infile, debug=self.debug)

        self.outfile = None
        self.beatsfile = None
        self.firstfull = None

        self.fmin = None
        self.fmax = None
        self.bmin = None
        self.bmax = None

    def setup(self, outfile, beatsfile, firstfull):
        self.outfile = outfile
        self.enable_output_save(self.outfile)
        self.reset_remix()

        self.beatsfile = beatsfile
        self.enable_output_beats(self.beatsfile)

        self.firstfull = firstfull
        self.track_beats(firstfull=firstfull)

        self.disable_output_play()

    def play_byswitchingbeatdirection(self, fmin=8, fmax=16, bmin=4, bmax=8):
        if self.beat_samples is None:
            self.gen_beat_samples()

        # don't start on beat 0, but wherever we've determined first beat is
        curr_beat = self.firstfullbar
        song_over = False
        direction = "r"

        if curr_beat > 0:
            for b in range(curr_beat):
                print(">%d" % curr_beat, end="", flush=True)
                self.play_beat(b)

        while not song_over:
            if direction == "r":
                direction = "f"
                num_beats = random.randint(int(fmin / 2), int(fmax / 2)) * 2
                self.write_out("# %d forward beats" % num_beats)
            elif direction == "f":
                direction = "r"
                num_beats = random.randint(int(bmin / 2), int(bmax / 2)) * 2
                self.write_out("# %d reverse beats" % num_beats)

            print(
                "(%.02f%%) [%d%s] "
                % ((curr_beat / (self.total_beats - 1)) * 100, num_beats, direction),
                end="",
                flush=True,
            )

            # play num_beats in the appropriate direction
            for x in range(num_beats):
                if direction == "f":
                    curr_beat += 1
                    if curr_beat >= self.total_beats - 1:
                        song_over = True
                        break
                    print(">%d" % curr_beat, end="", flush=True)

                elif direction == "r":
                    curr_beat -= 1
                    if curr_beat < 0:
                        break
                    print("<%d" % curr_beat, end="", flush=True)

                self.play_beat(curr_beat)

            print(flush=True)

        self.shutdown()
        self.save_remix()

    def set_parameters(self, fmin=8, fmax=16, bmin=4, bmax=8):
        self.fmin = fmin
        self.fmax = fmax
        self.bmin = bmin
        self.bmax = bmax

    def run(self):
        self.play_byswitchingbeatdirection(self.fmin, self.fmax, self.bmin, self.bmax)


if __name__ == "__main__":
    try:
        infile = sys.argv[1]
    except:
        print("Must supply valid input file")
        sys.exit(1)
    try:
        outfile = sys.argv[2]
    except:
        print("Must supply valid output file")
        sys.exit(1)
    try:
        fmin = int(sys.argv[3])
    except:
        fmin = 8
        print("fmin = %d" % fmin)
    try:
        fmax = int(sys.argv[4])
    except:
        fmax = 16
        print("fmax = %d" % fmax)
    try:
        bmin = int(sys.argv[5])
    except:
        bmin = 4
        print("bmin = %d" % bmin)
    try:
        bmax = int(sys.argv[6])
    except:
        bmax = 8
        print("bmax = %d" % bmax)
    try:
        firstfull = int(sys.argv[7])
    except:
        firstfull = 0
        print("firstfull = %d" % firstfull)

    stub, ext = os.path.splitext(outfile)
    beatsfile = stub + ".br"
    print("beatsfile = %s" % beatsfile)

    bs = beatswitcher(infile, debug=False)
    bs.setup(outfile, beatsfile, firstfull)
    bs.set_parameters(fmin, fmax, bmin, bmax)
    bs.run()
