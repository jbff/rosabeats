#!/usr/bin/env python
# shuffle bars in a song with rosabeats

import sys

from rosabeats import rosabeats

if __name__ == "__main__":
    try:
        infile = str(sys.argv[1])
    except:
        print("must specify input and output file", flush=True)
        sys.exit(1)
    try:
        outfile = str(sys.argv[2])
    except:
        print("must specify input and output file", flush=True)
        sys.exit(1)
    try:
        first_bar = int(sys.argv[3])
    except:
        first_bar = 0
    try:
        beats_per = int(sys.argv[4])
    except:
        beats_per = 8

    song = rosabeats(infile, debug=True)
    song.divide_bars()
    song.track_beats()

    bar_count = int(song.total_beats / beats_per)

    barlist = [x for x in range(bar_count + 1)]

    song.enable_output_play()
    song.setup_playback()

    song.enable_output_save(outfile)
    song.reset_remix()

    song.play_beats([x for x in range(first_bar)])
    for count, bar in enumerate(barlist):
        first_b = (count * 8) + first_bar
        beatlist = [x for x in range(first_b, first_b + beats_per)]
        beatlist.reverse()
        song.play_beats(beatlist)
    song.save_remix()
