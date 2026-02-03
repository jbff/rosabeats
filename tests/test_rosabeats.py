"""Tests for core rosabeats module."""

import pytest
import numpy as np
import os

from rosabeats.rosabeats import rosabeats


class TestRosabeatsInit:
    """Tests for rosabeats initialization."""

    def test_init_without_file(self):
        """Should initialize without a file."""
        r = rosabeats()
        assert r.sourcefile is None
        assert r.data is None
        assert r.sr is None

    def test_init_with_file(self, temp_audio_file):
        """Should initialize with a file path."""
        r = rosabeats(temp_audio_file)
        assert r.sourcefile is not None
        assert temp_audio_file in r.sourcefile

    def test_debug_mode(self):
        """Should set debug mode."""
        r = rosabeats(debug=True)
        assert rosabeats.debug is True

        # Reset
        rosabeats.debug = False


class TestRosabeatsSetfile:
    """Tests for setfile method."""

    def test_setfile_sets_sourcefile(self, temp_audio_file):
        """setfile should set sourcefile to absolute path."""
        r = rosabeats()
        r.setfile(temp_audio_file)

        assert r.sourcefile is not None
        assert os.path.isabs(r.sourcefile)

    def test_setfile_sets_saved_features_path(self, temp_audio_file):
        """setfile should set saved_features path."""
        r = rosabeats()
        r.setfile(temp_audio_file)

        assert r.saved_features is not None
        assert r.saved_features.endswith(".pkl")


class TestRosabeatsLoad:
    """Tests for audio loading."""

    def test_load_wav_file(self, temp_audio_file):
        """Should load a WAV file."""
        r = rosabeats(temp_audio_file)
        r.load()

        assert r.data is not None
        assert r.sr is not None
        assert r.channels is not None

    def test_load_creates_stereo_data(self, temp_audio_file):
        """Loaded data should have channel dimension."""
        r = rosabeats(temp_audio_file)
        r.load()

        # Data should be (channels, samples)
        assert r.data.ndim >= 1


class TestRosabeatsMixToMono:
    """Tests for mix_to_mono method."""

    def test_mix_to_mono(self, temp_audio_file):
        """Should create mono mix of audio."""
        r = rosabeats(temp_audio_file)
        r.load()
        r.mix_to_mono()

        assert r.mono is not None
        assert r.mono.ndim == 1


class TestRosabeatsTrackBeats:
    """Tests for beat tracking."""

    def test_track_beats_basic(self, temp_audio_file):
        """Should track beats and set related attributes."""
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=0)

        assert r.beat_timings is not None
        assert r.beat_samples is not None
        assert r.beat_slices is not None
        assert r.total_beats is not None
        assert r.total_beats > 0
        assert r.beatsperbar == 4
        assert r.downbeat == 0

    def test_track_beats_sets_total_bars(self, temp_audio_file):
        """Should calculate total bars."""
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=0)

        assert r.total_bars is not None
        expected_bars = (r.total_beats - r.downbeat) // r.beatsperbar
        assert r.total_bars == expected_bars

    def test_track_beats_with_downbeat(self, temp_audio_file):
        """Should handle non-zero downbeat."""
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=2)

        assert r.downbeat == 2


class TestRosabeatsBeatStartsBar:
    """Tests for beat_starts_bar method."""

    @pytest.fixture
    def tracked_rosabeats(self, temp_audio_file):
        """Create rosabeats instance with beats tracked."""
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=0)
        return r

    def test_downbeat_starts_bar(self, tracked_rosabeats):
        """Beat 0 should start bar 0 when downbeat is 0."""
        result = tracked_rosabeats.beat_starts_bar(0)
        assert result == 0

    def test_non_downbeat_returns_none(self, tracked_rosabeats):
        """Non-downbeat beats should return None."""
        result = tracked_rosabeats.beat_starts_bar(1)
        assert result is None

        result = tracked_rosabeats.beat_starts_bar(2)
        assert result is None

    def test_subsequent_downbeats(self, tracked_rosabeats):
        """Beats at bar boundaries should return bar numbers."""
        result = tracked_rosabeats.beat_starts_bar(4)
        assert result == 1

        result = tracked_rosabeats.beat_starts_bar(8)
        assert result == 2


class TestRosabeatsOutputControl:
    """Tests for output enable/disable methods."""

    def test_enable_disable_play(self):
        """Should enable and disable playback output."""
        r = rosabeats()

        r.enable_output_play()
        assert r.output_play is True

        r.disable_output_play()
        assert r.output_play is False

    def test_enable_disable_save(self, tmp_path):
        """Should enable and disable save output."""
        r = rosabeats()
        outfile = str(tmp_path / "out.wav")

        r.enable_output_save(outfile)
        assert r.output_save is True
        assert r.remix_output_file == outfile

        r.disable_output_save()
        assert r.output_save is False

    def test_enable_disable_beats(self, tmp_path):
        """Should enable and disable beats output."""
        r = rosabeats()
        outfile = str(tmp_path / "out.br")

        r.enable_output_beats(outfile)
        assert r.output_beats is True
        assert r.beats_output_file == outfile

        r.disable_output_beats()
        assert r.output_beats is False


class TestRosabeatsDetectDownbeat:
    """Tests for detect_downbeat method."""

    def test_detect_downbeat_returns_int(self, temp_audio_file):
        """detect_downbeat should return an integer."""
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=0)

        result = r.detect_downbeat(4)

        assert isinstance(result, (int, np.integer))
        assert 0 <= result < 4

    def test_detect_downbeat_dbn(self, temp_audio_file):
        """detect_downbeat_dbn should work."""
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=0)

        result = r.detect_downbeat_dbn(4)

        assert isinstance(result, (int, np.integer))
        assert 0 <= result < 4


class TestRosabeatsRest:
    """Tests for rest method."""

    @pytest.fixture
    def output_rosabeats(self, temp_audio_file, tmp_path):
        """Create rosabeats with save output enabled."""
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=0)
        r.enable_output_save(str(tmp_path / "out.wav"))
        r.reset_remix()
        return r

    def test_rest_adds_silence(self, output_rosabeats):
        """rest should add silence to remix buffer."""
        initial_index = output_rosabeats.remix_index

        output_rosabeats.rest(1.0)  # 1 beat of silence

        assert output_rosabeats.remix_index > initial_index
