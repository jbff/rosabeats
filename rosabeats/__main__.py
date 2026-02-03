#!/usr/bin/env python
"""
Entry point for running rosabeats as a module.

Usage:
    python -m rosabeats [command]

Commands:
    shell       Launch interactive shell (default)
    segment     Segment audio file and track beats
    beatswitch  Generate beat recipe with alternating patterns
    recipe      Process beat recipe files

Examples:
    python -m rosabeats                     # Launch interactive shell
    python -m rosabeats shell               # Same as above
    python -m rosabeats segment song.wav    # Segment audio file
    python -m rosabeats beatswitch song.wav # Generate beat recipe
    python -m rosabeats recipe file.br      # Process beat recipe
"""

import sys


def main():
    """Main entry point for python -m rosabeats."""
    if len(sys.argv) < 2:
        # Default to shell
        from rosabeats.rosabeats_shell import main as shell_main
        sys.exit(shell_main())

    command = sys.argv[1]

    # Remove the command from argv so subcommands see correct args
    sys.argv = [f"rosabeats {command}"] + sys.argv[2:]

    if command in ("shell", "sh"):
        from rosabeats.rosabeats_shell import main as shell_main
        sys.exit(shell_main())
    elif command in ("segment", "seg"):
        from rosabeats.segment_song import main as segment_main
        sys.exit(segment_main() or 0)
    elif command in ("beatswitch", "bs"):
        from rosabeats.beatswitch import main as beatswitch_main
        sys.exit(beatswitch_main() or 0)
    elif command in ("recipe", "br"):
        from rosabeats.beatrecipe_processor import main as recipe_main
        sys.exit(recipe_main() or 0)
    elif command in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0)
    else:
        print(f"Unknown command: {command}")
        print("Use 'python -m rosabeats --help' for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
