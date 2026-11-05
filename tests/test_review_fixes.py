"""Regression tests for the review-fix commit: mono support, tempo scalar,
final-beat playback, meter validation, shell debug flag, and CLI meter checks."""

import os

import numpy as np
import pytest
import soundfile as sf
from unittest.mock import Mock

from rosabeats.rosabeats import rosabeats
from rosabeats.beat_explorer_cli import BeatExplorerCLI


@pytest.fixture
def mono_wav_file(tmp_path, synthetic_audio_with_beats):
    """Create a temporary mono WAV file for testing."""
    audio, sr = synthetic_audio_with_beats
    filepath = tmp_path / "mono_audio.wav"
    sf.write(filepath, audio, sr)
    return str(filepath)


class FakeStream:
    """Recording stand-in for sounddevice.OutputStream."""

    def __init__(self):
        self.written = []

    def write(self, buf):
        self.written.append(np.asarray(buf))

    def close(self):
        pass


class FakePlaybackRosabeats(rosabeats):
    """rosabeats subclass with a recording stream instead of real audio out."""

    def setup_playback(self):
        self.stream = FakeStream()


class TestMonoAudio:
    """Mono audio must load and play (finding: mono crashes every entry point)."""

    def test_load_mono_wav(self, mono_wav_file):
        r = rosabeats(mono_wav_file)
        r.load()

        assert r.channels == 1
        assert r.data.ndim == 2, "data should normalize to (channels, samples)"
        assert r.dtype == "float32"

    def test_track_beats_on_mono(self, mono_wav_file):
        r = rosabeats(mono_wav_file)
        r.load()
        r.track_beats(beatsper=4, downbeat=0)

        assert r.total_beats > 0

    def test_play_beat_on_mono(self, mono_wav_file):
        r = FakePlaybackRosabeats(mono_wav_file)
        r.load()
        r.setup_playback()
        r.output_play = True
        r.track_beats(beatsper=4, downbeat=0)

        r.play_beat(0, silent=True)

        assert len(r.stream.written) == 1
        buf = r.stream.written[0]
        assert buf.ndim == 2
        assert buf.shape[1] == 1  # mono: one channel of frames

    def test_rest_on_mono(self, mono_wav_file):
        r = FakePlaybackRosabeats(mono_wav_file)
        r.load()
        r.setup_playback()
        r.output_play = True
        r.track_beats(beatsper=4, downbeat=0)

        r.rest(1.0)

        buf = r.stream.written[0]
        assert buf.shape[1] == 1
        assert np.all(buf == 0)


class TestTempoScalar:
    """tempo must be a plain float, not a shape-(1,) ndarray (finding:
    rest() crashes with TypeError on numpy >= 2.4)."""

    def test_tempo_is_float(self, temp_audio_file):
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=0)

        assert isinstance(r.tempo, float)

    def test_rest_works(self, output_rosabeats_like):
        # rest() previously crashed raising TypeError on float(ndarray/60)
        output_rosabeats_like.rest(0.5)  # must not raise


@pytest.fixture
def output_rosabeats_like(temp_audio_file, tmp_path):
    r = rosabeats(temp_audio_file)
    r.track_beats(beatsper=4, downbeat=0)
    r.enable_output_save(str(tmp_path / "out.wav"))
    r.reset_remix()
    return r


class TestLastBeatPlayable:
    """The last beat of a track must have a slice (finding: beats yields
    total_beats-1 slices so the final beat is unplayable)."""

    def test_beat_slices_length_matches_total_beats(self, temp_audio_file):
        r = rosabeats(temp_audio_file)
        r.track_beats(beatsper=4, downbeat=0)

        assert len(r.beat_slices) == r.total_beats

    def test_play_last_beat(self, temp_audio_file):
        r = FakePlaybackRosabeats(temp_audio_file)
        r.load()
        r.setup_playback()
        r.output_play = True
        r.track_beats(beatsper=4, downbeat=0)

        last = r.total_beats - 1
        r.play_beat(last, silent=True)  # must not raise or print errors

        assert len(r.stream.written) == 1


class TestMeterValidation:
    """Beats per bar and downbeat must be validated (finding: unvalidated
    values divide by zero or produce negative state)."""

    @pytest.mark.parametrize("beatsper", ["zero", "negative"])
    def test_invalid_beats_per_bar(self, temp_audio_file, beatsper):
        r = rosabeats(temp_audio_file)
        r.load()
        with pytest.raises(ValueError):
            r.track_beats(beatsper=0 if beatsper == "zero" else -2, downbeat=0)

    def test_negative_downbeat_rejected(self, temp_audio_file):
        r = rosabeats(temp_audio_file)
        r.load()
        with pytest.raises(ValueError):
            r.track_beats(beatsper=4, downbeat=-1)

    def test_downbeat_beyond_track_rejected(self, temp_audio_file):
        r = rosabeats(temp_audio_file)
        r.load()
        r.track_beats(beatsper=4, downbeat=0)
        total = r.total_beats
        with pytest.raises(ValueError):
            r.track_beats(beatsper=4, downbeat=total + 100)


class TestShellDebugFlag:
    """rosabeats-shell --debug must not be reset by shell construction
    (finding: __init__ unconditionally resets the class-level flag)."""

    def test_debug_survives_shell_construction(self):
        from rosabeats.rosabeats_shell import rosabeats_shell
        from rosabeats.rosabeats import rosabeats as rb_class

        rb_class.debug = True
        try:
            rosabeats_shell()
            assert rb_class.debug is True
        finally:
            rb_class.debug = False


class TestWindowsGetchBytes:
    """easy_getch returns bytes (msvcrt.getch) on Windows and str elsewhere;
    the explorer loop must handle both (finding: CLI inert on Windows)."""

    def test_handles_bytes_from_getch(self, monkeypatch, capsys):
        import easy_getch
        from unittest.mock import Mock as _Mock

        called = {"n": 0}

        def fake_getch():
            called["n"] += 1
            if called["n"] >= 5:  # bound: an unfixed loop would spin forever
                raise AssertionError("getch loop spun forever: bytes never matched")
            if called["n"] == 1:
                return b'p'  # next beat, Windows bytes
            return b'Q'  # quit, Windows bytes

        monkeypatch.setattr(easy_getch, "getch", fake_getch)
        rb = _Mock()
        rb.total_beats = 32
        rb.beatsperbar = 4
        rb.downbeat = 0
        rb.total_bars = 8
        rb.current_beat_index = 0

        explorer = BeatExplorerCLI(rb)

        played = []

        def play_beat(b, silent=False):
            played.append(b)

        rb.play_beat = play_beat

        explorer.play_manually_by_step()

        assert played == [1]
        out = capsys.readouterr().out
        assert "quitting" in out


class TestCLIMeterValidation:
    """beat-explorer rejects invalid meter values at the argparse layer
    (finding: --beats-per-bar 0 / negative downbeat accepted silently)."""

    def _run_main(self, argv, monkeypatch):
        from rosabeats import beat_explorer_cli

        constructed = []

        class Boom:
            def __init__(self, *a, **k):
                constructed.append(1)
                raise AssertionError("should not construct engine for bad meter")

        monkeypatch.setattr(beat_explorer_cli, "rosabeats", Boom)
        monkeypatch.setattr("sys.argv", argv)
        with pytest.raises(SystemExit) as exc_info:
            beat_explorer_cli.main()
        return exc_info.value, constructed

    def test_rejects_zero_beats_per_bar(self, monkeypatch):
        result, constructed = self._run_main(
            ["beat-explorer", "song.wav", "--beats-per-bar", "0"], monkeypatch
        )
        assert result.code not in (0, None)
        assert constructed == []

    def test_rejects_negative_downbeat(self, monkeypatch):
        result, constructed = self._run_main(
            ["beat-explorer", "song.wav", "--downbeat", "-1"], monkeypatch
        )
        assert result.code not in (0, None)
        assert constructed == []
