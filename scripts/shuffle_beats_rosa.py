#!/usr/bin/env python
# shuffle beats in a song with rosabeats

import sys, random
from rosabeats import rosabeats

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("require one argument that is a file containing music", flush=True)
        sys.exit(1)

    infile = sys.argv[1]
    outfile = infile[0:-4] + "_shuf.wav"

    song = rosabeats(infile, debug=True)
    song.divide_bars(8, 2)
    song.track_beats()

    beatlist = [x for x in range(song.total_beats)]
    random.shuffle(beatlist)

    song.enable_output_play()
    song.setup_playback()

    song.enable_output_save(outfile)
    song.reset_remix()

    song.play_beats(beatlist)
    song.save_remix()
