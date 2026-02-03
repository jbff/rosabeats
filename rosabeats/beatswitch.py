#!/usr/bin/env python

import sys
import random
import os.path
import argparse
import rosabeats


class BeatSwitcher(rosabeats.rosabeats):
    """A class for generating beat recipes by switching between forward and backward playback of beats.
    
    This class extends rosabeats to generate beat recipes (`.br` files) that describe
    a dynamic remix by alternating between playing beats forward and backward in random lengths.
    The resulting `.br` file can be processed using beatrecipe-processor to create the actual
    audio remix.
    
    The beat recipe maintains the original beat structure while creating new rhythmic
    patterns through alternating forward and backward playback of beat segments.
    
    Attributes:
        infile (str): Path to input audio file
        outfile (str): Path to output beat recipe file (.br)
        firstfull (int): Index of first full bar
        fmin (int): Minimum number of forward beats
        fmax (int): Maximum number of forward beats
        bmin (int): Minimum number of backward beats
        bmax (int): Maximum number of backward beats
    """
    
    def __init__(self, infile, debug=False):
        """Initialize the BeatSwitcher.
        
        Args:
            infile (str): Path to input audio file
            debug (bool, optional): Enable debug mode
        """
        self.infile = infile
        self.debug = debug

        # Initialize parent class
        super().__init__(self.infile, debug=self.debug)

        # Initialize instance variables
        self.outfile = None
        self.firstfull = None
        self.fmin = None
        self.fmax = None
        self.bmin = None
        self.bmax = None

    def setup(self, outfile, firstfull):
        """Set up the beat recipe configuration.
        
        Args:
            outfile (str): Path to output beat recipe file (.br)
            firstfull (int): Index of first full bar
        """
        # Configure output file
        self.outfile = outfile
        self.enable_output_beats(self.outfile)

        # Configure beat tracking
        self.firstfull = firstfull
        self.track_beats(firstfull=firstfull)

        # Disable WAV output and playback
        self.disable_output_save()
        self.disable_output_play()

    def play_byswitchingbeatdirection(self, fmin=8, fmax=16, bmin=4, bmax=8):
        """Generate a beat recipe by alternating between forward and backward playback.
        
        This method generates a beat recipe by:
        1. Starting from the first full bar
        2. Alternating between playing beats forward and backward
        3. Using random lengths for each direction
        4. Continuing until the end of the song
        
        The resulting beat recipe can be processed using beatrecipe-processor
        to create the actual audio remix.
        
        Args:
            fmin (int, optional): Minimum number of forward beats
            fmax (int, optional): Maximum number of forward beats
            bmin (int, optional): Minimum number of backward beats
            bmax (int, optional): Maximum number of backward beats
        """
        if self.beat_samples is None:
            self.gen_beat_samples()

        # Start from first full bar
        curr_beat = self.firstfullbar
        song_over = False
        direction = "r"  # Start with reverse direction

        # Write initial beats up to first full bar
        if curr_beat > 0:
            for b in range(curr_beat):
                print(">%d " % curr_beat, end="", flush=True)
                self.play_beat(b, silent=True)

        # Main recipe generation loop
        while not song_over:
            # Switch direction and determine number of beats
            if direction == "r":
                direction = "f"
                num_beats = random.randint(int(fmin / 2), int(fmax / 2)) * 2
                self.write_out("# %d forward beats" % num_beats)
            else:
                direction = "r"
                num_beats = random.randint(int(bmin / 2), int(bmax / 2)) * 2
                self.write_out("# %d reverse beats" % num_beats)

            # Print progress
            print(
                "(%.02f%%) [%d%s] "
                % ((curr_beat / (self.total_beats - 1)) * 100, num_beats, direction),
                end="",
                flush=True,
            )

            # Generate beats in current direction
            for x in range(num_beats):
                if direction == "f":
                    curr_beat += 1
                    if curr_beat >= self.total_beats - 1:
                        song_over = True
                        break
                    print(">%d " % curr_beat, end="", flush=True)
                else:
                    curr_beat -= 1
                    if curr_beat < 0:
                        break
                    print("<%d " % curr_beat, end="", flush=True)

                self.play_beat(curr_beat, silent=True)

            print(flush=True)

        # Clean up
        self.shutdown()

    def set_parameters(self, fmin=8, fmax=16, bmin=4, bmax=8):
        """Set the beat switching parameters.
        
        Args:
            fmin (int, optional): Minimum number of forward beats
            fmax (int, optional): Maximum number of forward beats
            bmin (int, optional): Minimum number of backward beats
            bmax (int, optional): Maximum number of backward beats
        """
        self.fmin = fmin
        self.fmax = fmax
        self.bmin = bmin
        self.bmax = bmax

    def run(self):
        """Run the beat recipe generation process."""
        self.play_byswitchingbeatdirection(self.fmin, self.fmax, self.bmin, self.bmax)


def get_default_output_path(input_file):
    """Generate default output path based on input file.
    
    Args:
        input_file (str): Path to input file
        
    Returns:
        str: Default output path with _bs.br suffix
    """
    base, _ = os.path.splitext(input_file)
    return f"{base}_bs.br"


def parse_args():
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="""Generate a beat recipe (.br file) by switching between forward and backward playback of beats.
        
        The generated beat recipe can be processed using beatrecipe-processor to create the actual audio remix.
        This tool only generates the recipe, not the final audio file.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "input_file",
        help="Input audio file to process"
    )
    
    # Optional arguments
    parser.add_argument(
        "-o", "--output",
        help="Output beat recipe file (.br) - defaults to input filename with _bs.br suffix"
    )
    parser.add_argument(
        "--fmin", type=int, default=8,
        help="Minimum number of forward beats"
    )
    parser.add_argument(
        "--fmax", type=int, default=16,
        help="Maximum number of forward beats"
    )
    parser.add_argument(
        "--bmin", type=int, default=4,
        help="Minimum number of backward beats"
    )
    parser.add_argument(
        "--bmax", type=int, default=8,
        help="Maximum number of backward beats"
    )
    parser.add_argument(
        "--firstfull", type=int, default=0,
        help="First full bar index"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug mode"
    )
    
    return parser.parse_args()


def main():
    """Main function for beatswitch command-line tool.
    
    Example:
        # Generate a beat recipe with default output name
        beatswitch input.wav
        
        # Generate a beat recipe with custom output name
        beatswitch input.wav -o custom.br
        
        # Convert the recipe to audio using beatrecipe-processor
        beatrecipe-processor input.wav output.br output.wav
    """
    args = parse_args()
    
    # Determine output file path
    output_file = args.output if args.output else get_default_output_path(args.input_file)
    print(f"Output file: {output_file}")
    
    # Create and run beat switcher
    bs = BeatSwitcher(args.input_file, debug=args.debug)
    bs.setup(output_file, args.firstfull)
    bs.set_parameters(args.fmin, args.fmax, args.bmin, args.bmax)
    bs.run()


if __name__ == "__main__":
    main()
