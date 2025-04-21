#!/usr/bin/env python

import sys
import os.path

from rosabeats import rosabeats

def main(args):
    # the next 17 lines should be replaced with an argsparser
    try:
        infile = args[0]
    except:
        print("Must supply valid input file")
        sys.exit(1)
    try:
        beatsper = int(args[1])
    except:
        beatsper = 8
    try:
        firstfull = int(args[2])
    except:
        firstfull = 0

    basename = os.path.basename(infile)
    stub, ext = os.path.splitext(basename)
    output = stub + ".brd"

    ######################################

    print("infile = %s" % infile)
    print("beatsper = %d" % beatsper)
    print("firstfull = %d" % firstfull)
    print("outfile = %s" % output)
    print()

    ######################################

    print("loading..")
    s = rosabeats(infile, debug=True)
    print("beat tracking..")
    s.track_beats(beatsper, firstfull)
    print("segmenting...")
    s.segment_segmentino()
    print("assigning beats/bars to segments...")
    s.segmentize_beats()
    print()

    ######################################

    with open(output, "w") as f:
        print("%s has %d segments, %d full bars, and %d beats" % (infile, s.total_segments, s.total_bars, s.total_beats))
        f.write("##BEATS## This was segmented and tracked using librosa's beat tracker\n\n")

        f.write("file %s\n" % s.sourcefile)
        f.write("beats_bar %d %d\n" % (s.beatsperbar, s.firstfullbar))
        f.write("# total beats = %d\n" % s.total_beats)
        f.write("# total bars = %d (beats %d-%d)\n" % (s.total_bars, s.firstfullbar, (s.firstfullbar + (s.beatsperbar * s.total_bars))))

        bars_defs = []
        beats_defs = []
        for idx, seg in enumerate(s.segments):
            print("seg #%d - %s - (%0.2f)" % (idx, seg["label"], seg["duration"]), end="", flush=True)

            if len(seg["bars"]) >= 1:
                print(" [bars %d-%d]" % (seg["bars"][0],seg["bars"][-1]), end="", flush=True)
                bars_defs.append("def %s_%d bars %d-%d" % (seg["label"], idx, seg["bars"][0], seg["bars"][-1]))

            if len(seg["beats"]) >= 1:
                print(" [beats %d-%d]" % (seg["beats"][0],seg["beats"][-1]))
                beats_defs.append("def %s_%d_beats beats %d-%d\t# dur = %fs, beats %d-%d" % (seg["label"], idx, seg["beats"][0], seg["beats"][-1], seg["duration"], seg["beats"][0], seg["beats"][-1]))

        for d in bars_defs:
            f.write("%s\n" % d)

        f.write("\n")

        for d in beats_defs:
            f.write("%s\n" % d)

        f.write("\n")

#       for idx, seg in enumerate(s.segments):
#           f.write("%s_%d\n" % (seg["label"], idx))
#           f.write("rest 4\n")
#           f.write("%s_%d_beats\n" % (seg["label"], idx))
#           f.write("rest 8\n")

if __name__ == "__main__":
    main(sys.argv[1:])
