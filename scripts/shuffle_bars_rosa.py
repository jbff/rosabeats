#!/usr/bin/env python
# shuffle bars in a song with rosabeats

import sys, random
from rosabeats import rosabeats

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("require one argument that is a file containing music", flush=True)
        sys.exit(1)

    infile = sys.argv[1]
    outfile = infile[0:-4] + "_barshuf.wav"

    song = rosabeats(infile, debug=True)
    song.divide_bars(8, 2)
    song.track_beats()

    bar_count = int(song.total_beats / 8)

    barlist = [x for x in range(1, bar_count)]

    random.shuffle(barlist)

    song.enable_output_play()
    song.setup_playback()

    song.enable_output_save(outfile)
    song.reset_remix()

    song.play_beats([0, 1])
    song.play_bar(0)
    song.play_bars(barlist)
    song.play_bar(bar_count)
    song.save_remix()
