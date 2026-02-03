# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rosabeats is a Python library for audio beat detection, segmentation, and remixing. It uses librosa for beat tracking and provides tools for creative audio manipulation through a beat recipe DSL.

## Commands

### Installation
```bash
pip install -e .              # Basic install
pip install -e .[ffms2]       # With ffms2 for additional audio formats
```

#### Installing with uv
```bash
uv sync                       # Basic install
uv sync --extra ffms2         # With ffms2
```

### CLI Tools (available after install)
- `beatrecipe-processor <file.br>` - Execute beat recipe files
- `segment-song <audio> [options]` - Segment audio and track beats, outputs `.bri` files
- `beatswitch <audio> [options]` - Generate beat recipes with alternating patterns
- `rosabeats-shell` - Interactive shell for beat manipulation

### Testing
```bash
pip install -e .[dev]         # Install with test dependencies
pytest                        # Run all tests
pytest -v                     # Verbose output
pytest tests/test_shell.py    # Run specific test file
pytest -k "downbeat"          # Run tests matching pattern
pytest --cov=rosabeats        # Run with coverage report
```

## Architecture

```
rosabeats/
├── rosabeats.py              # Core engine (~1000 lines): beat tracking, segmentation,
│                             # playback buffering, remix operations
├── downbeat.py               # DBN-based downbeat detection (pure Python HMM)
├── beatrecipe_processor.py   # Parses and executes .br files (extends rosabeats class)
├── beatswitch.py             # Generates beat recipes with forward/backward patterns
├── segment_song.py           # CLI for segmentation, outputs .bri metadata files
└── rosabeats_shell.py        # cmd.Cmd-based interactive shell
```

The `rosabeats` class in `rosabeats.py` is the core engine. Other tools either extend it (`beatrecipe_processor`) or instantiate it directly.

## Beat Recipe DSL (.br files)

Required header:
```
file <audio.wav>
beats_bar <beats_per_bar> <downbeat>
```

Commands:
- `beats N` / `beats N-M` - Play beat(s), reverse if N>M
- `bars N` / `bars N-M` - Play bar(s)
- `beats_shuf N-M` / `bars_shuf N-M` - Shuffle before playing
- `bars_rev N-M` - Play bars with beats reversed within each bar
- `beat_div <beat> <divisor> <times>` - Subdivide and repeat a beat
- `rest N` - Insert N beats of silence (float allowed)
- `def <name> bars/beats N-M` - Define reusable segment
- `play <name>` / `play <name> N` - Play defined segment (N times)

Full syntax: `docs/beatrecipe.md`

## Key Implementation Details

- Beat/bar indices are 0-based
- `downbeat` in beats_bar specifies the beat index where the first full bar begins (0 = no pickup beats)
- Downbeat auto-detection available via `--auto-downbeat` flag (uses DBN/HMM approach)
- Segmentation uses Laplacian spectral clustering (via librosa/sklearn)
- Audio loaded via librosa; ffms2 optional for additional format support
- Debug mode: set `rosabeats_instance.debug = True` or use `--debug` CLI flags

## Optional Dependencies

- `ffms2` - Additional audio format support beyond librosa defaults
