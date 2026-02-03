# Beat Recipe DSL Reference

Beat recipes (`.br` files) describe how to remix audio by specifying which beats and bars to play in what order.

## Required Header

Every beat recipe must start with these two lines:

```
file <audio_file>
beats_bar <beats_per_bar> <downbeat>
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `file` | Path to the source audio file |
| `beats_bar` | Two integers: beats per bar and downbeat offset |

The `beats_bar` directive takes two arguments:
- **beats_per_bar**: Number of beats in each bar (commonly 4 or 8)
- **downbeat**: Beat index of the first downbeat (often 0, but may be non-zero depending on the track)

Use `control_beats.py` or the interactive shell to experiment and discover the correct downbeat value for a given track.

## Commands

### Basic Playback

| Command | Description |
|---------|-------------|
| `beats N` | Play single beat N |
| `beats N-M` | Play beats N through M (forward if N < M, reverse if N > M) |
| `bars N` | Play single bar N |
| `bars N-M` | Play bars N through M (forward if N < M, reverse if N > M) |

**Examples:**
```
beats 3          # Play beat 3
beats 3-3        # Same as above
beats 3-8        # Play beats 3, 4, 5, 6, 7, 8
beats 8-3        # Play beats 8, 7, 6, 5, 4, 3 (reversed)
bars 4           # Play bar 4
bars 4-4         # Same as above
bars 4-12        # Play bars 4 through 12
bars 12-4        # Play bars 12 through 4 (reversed)
```

### Silence

| Command | Description |
|---------|-------------|
| `rest N` | Insert N beats of silence (float values allowed) |

**Examples:**
```
rest 1           # 1 beat of silence
rest 0.5         # Half a beat of silence
rest 2.5         # 2.5 beats of silence
```

### Shuffled Playback

| Command | Description |
|---------|-------------|
| `beats_shuf N-M` | Play beats N through M in random order |
| `bars_shuf N-M` | Play bars N through M in random order |

The beats or bars are randomly shuffled before playing. If only a single beat or bar is specified, it behaves the same as `beats` or `bars`.

**Examples:**
```
beats_shuf 0-15   # Play beats 0-15 in random order
bars_shuf 0-7     # Play bars 0-7 in random order
bars_shuf 8       # Same as "bars 8" (single item)
```

### Reversed Bar Playback

| Command | Description |
|---------|-------------|
| `bars_rev N` | Play bar N with beats in reverse order |
| `bars_rev N-M` | Play bars N through M, each with beats reversed |

This plays the beats within each bar in reverse order. For example, if bar 0 contains beats 0-7, `bars_rev 0` plays beats 7, 6, 5, 4, 3, 2, 1, 0.

**Examples:**
```
bars_rev 0        # Play bar 0 with beats reversed
bars_rev 0-3      # Play bars 0, 1, 2, 3, each with beats reversed
```

### Beat Subdivision

| Command | Description |
|---------|-------------|
| `beat_div <beat> <divisor> <times>` | Subdivide a beat and play it multiple times |

This divides a beat into equal segments and plays the first segment multiple times.

**Arguments:**
- `beat`: The beat number to subdivide
- `divisor`: How many pieces to divide the beat into
- `times`: How many times to play the subdivided beat

**Examples:**
```
beat_div 540 2 2   # Play first half of beat 540 twice
beat_div 300 3 12  # Play first third of beat 300, 12 times (sounds like 4 beats of triplets)
```

### Macros

| Command | Description |
|---------|-------------|
| `def <name> <command>` | Define a reusable macro |
| `play <name>` | Play a defined macro once |
| `play <name> N` | Play a defined macro N times |

Macros allow you to define reusable segments that can be played multiple times.

**Examples:**
```
def intro bars 0-7
def verse bars 8-23
def chorus bars 24-31

play intro
play verse 2
play chorus
play verse
play chorus 2
```

## Comments

Lines starting with `#` are comments and are ignored:

```
# This is a comment
file song.wav
beats_bar 8 0

# Play the intro
bars 0-7
```

## Repetition

Most commands accept an optional repeat count as the last argument:

```
beats 0-7 4       # Play beats 0-7 four times
bars 0-3 2        # Play bars 0-3 twice
rest 1 4          # Rest for 1 beat, four times (4 beats total)
```

## Multiple Commands

Commands can be separated by semicolons on a single line:

```
bars 0-3; rest 1; bars 4-7
```

## Full Example

```
# Example beat recipe for a remix
file mysong.wav
beats_bar 8 0

# Define sections
def intro bars 0-3
def verse bars 4-11
def chorus bars 12-19

# Build the remix
play intro
play verse
play chorus 2
bars_rev 12-15        # Reversed chorus first half
play verse
beats_shuf 96-127     # Scrambled beats for outro
rest 2
```
