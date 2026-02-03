"""Shared pytest fixtures for rosabeats tests."""

import pytest
import numpy as np


@pytest.fixture
def sample_rate():
    """Standard sample rate for tests."""
    return 22050


@pytest.fixture
def mono_audio(sample_rate):
    """Generate a simple mono audio signal (1 second of sine wave)."""
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    # 440 Hz sine wave
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    return audio


@pytest.fixture
def beat_times():
    """Sample beat times at 120 BPM (0.5s intervals)."""
    return np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5])


@pytest.fixture
def synthetic_audio_with_beats(sample_rate):
    """Generate synthetic audio with clear beats for testing.

    Creates a 10-second audio clip at 120 BPM with kicks on downbeats
    (every 4 beats) and lighter hits on other beats.
    """
    duration = 10.0
    n_samples = int(sample_rate * duration)
    audio = np.zeros(n_samples, dtype=np.float32)

    bpm = 120
    beat_interval = 60.0 / bpm  # 0.5 seconds
    beats_per_bar = 4

    # Create a simple kick drum sound (low frequency pulse)
    kick_duration = 0.05
    kick_samples = int(sample_rate * kick_duration)
    t_kick = np.linspace(0, kick_duration, kick_samples)
    kick = np.sin(2 * np.pi * 60 * t_kick) * np.exp(-t_kick * 40)

    # Create a lighter hi-hat sound (high frequency noise burst)
    hat_duration = 0.02
    hat_samples = int(sample_rate * hat_duration)
    t_hat = np.linspace(0, hat_duration, hat_samples)
    hat = np.random.randn(hat_samples).astype(np.float32) * 0.1 * np.exp(-t_hat * 100)

    # Place beats
    beat_num = 0
    current_time = 0.0
    while current_time < duration:
        sample_idx = int(current_time * sample_rate)

        if beat_num % beats_per_bar == 0:
            # Downbeat - kick drum
            end_idx = min(sample_idx + len(kick), n_samples)
            audio[sample_idx:end_idx] += kick[:end_idx - sample_idx]
        else:
            # Other beat - hi-hat
            end_idx = min(sample_idx + len(hat), n_samples)
            audio[sample_idx:end_idx] += hat[:end_idx - sample_idx]

        beat_num += 1
        current_time += beat_interval

    # Normalize
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio)) * 0.8

    return audio, sample_rate


@pytest.fixture
def temp_audio_file(tmp_path, synthetic_audio_with_beats):
    """Create a temporary WAV file for testing.

    This creates a stereo file for better compatibility with rosabeats.
    """
    import soundfile as sf

    audio, sr = synthetic_audio_with_beats
    # Convert to stereo
    stereo_audio = np.column_stack([audio, audio])
    filepath = tmp_path / "test_audio.wav"
    sf.write(filepath, stereo_audio, sr)
    return str(filepath)


@pytest.fixture
def sample_br_content():
    """Sample beat recipe file content."""
    return """file test.wav
beats_bar 4 0
# This is a comment
def intro beats 0-15
def verse bars 0-3
def chorus bars 4-7

# Play commands
play intro
play verse 2
"""


@pytest.fixture
def sample_bri_content():
    """Sample .bri file content (from segment-song output)."""
    return """##BEATS## This was segmented and tracked using librosa's beat tracker

file /path/to/audio.wav
beats_bar 4 0
# total beats = 100
# total bars = 24 (beats 0-96)
def A bars 0-3
def B bars 4-7
def A2 bars 8-11
def C bars 12-15

def A_beats beats 0-15	# dur = 8.00s
def B_beats beats 16-31	# dur = 8.00s
def A2_beats beats 32-47	# dur = 8.00s
def C_beats beats 48-63	# dur = 8.00s
"""
