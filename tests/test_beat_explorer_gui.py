"""Tests for beat_explorer_gui module."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from rosabeats.beat_explorer_gui import (
    LoadWorker,
    PlaybackWorker,
    BeatExplorerWindow,
    main,
)


class MockRosabeats:
    """Mock rosabeats instance for testing."""

    def __init__(
        self,
        total_beats: int = 32,
        beatsperbar: int = 4,
        downbeat: int = 0,
    ):
        self.total_beats = total_beats
        self.beatsperbar = beatsperbar
        self.downbeat = downbeat
        self.total_bars = (total_beats - downbeat) // beatsperbar
        self.tempo = 120.0
        self.played_beats = []
        self.beat_slices = [(i * 100, (i + 1) * 100) for i in range(total_beats)]
        self.output_play = True
        self.stream = Mock()
        self.data = [[0.0] * (total_beats * 100 + 100)] * 2

    def play_beat(self, b: int, silent: bool = False) -> None:
        self.played_beats.append(b)

    def shutdown(self) -> None:
        pass

    def detect_downbeat(self, beatsper: int) -> int:
        return 0


@pytest.fixture
def mock_rb():
    return MockRosabeats()


@pytest.fixture
def mock_rb_pickup():
    return MockRosabeats(total_beats=34, beatsperbar=4, downbeat=2)


class TestLoadWorker:
    """Tests for LoadWorker."""

    def test_init_stores_params(self):
        worker = LoadWorker("test.wav", 4, 0, False, False)
        assert worker.audio_file == "test.wav"
        assert worker.beats_per_bar == 4
        assert worker.downbeat == 0
        assert worker.auto_downbeat is False
        assert worker.debug is False

    @patch("rosabeats.beat_explorer_gui.rosabeats")
    def test_run_emits_finished_on_success(self, mock_rb_class):
        rb_instance = MockRosabeats()
        mock_rb_class.return_value = rb_instance
        mock_rb_class.return_value.track_beats = Mock()
        mock_rb_class.return_value.enable_output_play = Mock()
        mock_rb_class.return_value.init_outputs = Mock()

        worker = LoadWorker("test.wav", 4, 0, False, False)
        worker.progress = Mock()
        worker.finished = Mock()

        worker.run()

        worker.finished.emit.assert_called_once()
        args = worker.finished.emit.call_args[0]
        assert args[1] == ""  # no error

    @patch("rosabeats.beat_explorer_gui.rosabeats")
    def test_run_emits_error_on_failure(self, mock_rb_class):
        mock_rb_class.side_effect = FileNotFoundError("not found")

        worker = LoadWorker("nonexistent.wav", 4, 0, False, False)
        worker.progress = Mock()
        worker.finished = Mock()

        worker.run()

        worker.finished.emit.assert_called_once()
        args = worker.finished.emit.call_args[0]
        assert args[0] is None
        assert "not found" in args[1]

    @patch("rosabeats.beat_explorer_gui.rosabeats")
    def test_run_with_auto_downbeat(self, mock_rb_class):
        rb_instance = Mock()
        rb_instance.total_beats = 32
        rb_instance.detect_downbeat.return_value = 2
        mock_rb_class.return_value = rb_instance

        worker = LoadWorker("test.wav", 4, 0, True, False)
        worker.progress = Mock()
        worker.finished = Mock()

        worker.run()

        rb_instance.detect_downbeat.assert_called_once_with(4)
        assert rb_instance.downbeat == 2


class TestPlaybackWorker:
    """Tests for PlaybackWorker."""

    def test_init_stores_rb(self, mock_rb):
        worker = PlaybackWorker(mock_rb)
        assert worker.rb is mock_rb

    def test_play_beat_calls_rb(self, mock_rb):
        worker = PlaybackWorker(mock_rb)
        worker.started = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        worker._play_beat(5)

        assert 5 in mock_rb.played_beats
        worker.started.emit.assert_called_once()
        worker.finished.emit.assert_called_once()

    def test_play_bar_calls_rb_for_each_beat(self, mock_rb):
        worker = PlaybackWorker(mock_rb)
        worker.started = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        worker._play_bar(4, 8, 32)

        assert mock_rb.played_beats == [4, 5, 6, 7]
        worker.started.emit.assert_called_once()
        worker.finished.emit.assert_called_once()

    def test_play_bar_clamps_to_total_beats(self, mock_rb):
        worker = PlaybackWorker(mock_rb)
        worker.started = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        worker._play_bar(30, 34, 32)

        assert mock_rb.played_beats == [30, 31]

    def test_play_beat_emits_error_on_exception(self):
        rb = Mock()
        rb.play_beat.side_effect = RuntimeError("audio error")

        worker = PlaybackWorker(rb)
        worker.started = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        worker._play_beat(0)

        worker.error.emit.assert_called_once_with("audio error")


@pytest.fixture
def qapp():
    """Create or get QApplication instance for testing."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestBeatExplorerWindow:
    """Tests for BeatExplorerWindow."""

    def test_window_creates_without_file(self, qapp):
        """Window should open file dialog when no file given."""
        with patch.object(BeatExplorerWindow, "_open_file_dialog") as mock_dialog:
            window = BeatExplorerWindow()
            mock_dialog.assert_called_once()
            window.close()

    def test_window_creates_with_file(self, qapp):
        """Window should start loading when file is given."""
        with patch.object(BeatExplorerWindow, "_start_loading") as mock_load:
            window = BeatExplorerWindow(audio_file="test.wav")
            mock_load.assert_called_once_with("test.wav")
            window.close()

    def test_playback_buttons_disabled_initially(self, qapp):
        """Playback buttons should be disabled before loading."""
        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            assert not window.btn_prev_beat.isEnabled()
            assert not window.btn_this_beat.isEnabled()
            assert not window.btn_next_beat.isEnabled()
            assert not window.btn_prev_bar.isEnabled()
            assert not window.btn_this_bar.isEnabled()
            assert not window.btn_next_bar.isEnabled()
            window.close()

    def test_update_display_with_explorer(self, qapp, mock_rb):
        """_update_display should update labels from explorer state."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb)
            window.explorer.goto_beat(5)
            window._update_display()

            assert "5" in window.lbl_beat.text()
            assert "1" in window.lbl_bar.text()
            assert "32" in window.lbl_total_beats.text()
            assert "120" in window.lbl_tempo.text()
            window.close()

    def test_update_display_pickup_beats(self, qapp, mock_rb_pickup):
        """_update_display should show 'pickup' for beats before downbeat."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb_pickup)
            window.explorer.goto_beat(0)
            window._update_display()

            assert "pickup" in window.lbl_bar.text()
            window.close()

    def test_on_next_beat_navigates(self, qapp, mock_rb):
        """_on_next_beat should advance beat and update display."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb)
            window._playback_worker = Mock()
            window.explorer.goto_beat(5)

            window._on_next_beat()

            assert window.explorer.current_beat() == 6
            window.close()

    def test_on_prev_beat_navigates(self, qapp, mock_rb):
        """_on_prev_beat should go back one beat."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb)
            window._playback_worker = Mock()
            window.explorer.goto_beat(5)

            window._on_prev_beat()

            assert window.explorer.current_beat() == 4
            window.close()

    def test_on_next_bar_navigates(self, qapp, mock_rb):
        """_on_next_bar should advance by one bar."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb)
            window._playback_worker = Mock()
            window.explorer.goto_beat(4)

            window._on_next_bar()

            assert window.explorer.current_beat() == 8
            window.close()

    def test_on_prev_bar_navigates(self, qapp, mock_rb):
        """_on_prev_bar should go back by one bar."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb)
            window._playback_worker = Mock()
            window.explorer.goto_beat(8)

            window._on_prev_bar()

            assert window.explorer.current_beat() == 4
            window.close()

    def test_on_goto_beat(self, qapp, mock_rb):
        """_on_goto_beat should jump to spinbox value."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb)
            window._playback_worker = Mock()
            window.spin_goto_beat.setMaximum(31)
            window.spin_goto_beat.setValue(15)

            window._on_goto_beat()

            assert window.explorer.current_beat() == 15
            window.close()

    def test_on_goto_bar(self, qapp, mock_rb):
        """_on_goto_bar should jump to first beat of bar."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb)
            window._playback_worker = Mock()
            window.spin_goto_bar.setMaximum(7)
            window.spin_goto_bar.setValue(3)

            window._on_goto_bar()

            assert window.explorer.current_beat() == 12
            window.close()

    def test_on_apply_settings(self, qapp, mock_rb):
        """_on_apply_settings should update beats per bar."""
        from rosabeats.beat_explorer_cli import BeatExplorerCLI

        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window.explorer = BeatExplorerCLI(mock_rb)
            window._playback_worker = Mock()
            window.spin_bpb.setValue(8)
            window.spin_downbeat.setValue(0)

            window._on_apply_settings()

            assert window.explorer.beatsperbar == 8
            assert window.explorer.total_bars == 4  # 32 / 8
            window.close()

    def test_on_load_finished_success(self, qapp, mock_rb):
        """_on_load_finished should set up explorer on success."""
        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window._load_thread = Mock()

            window._on_load_finished(mock_rb, "")

            assert window.explorer is not None
            assert window.explorer.total_beats == 32
            assert window.btn_prev_beat.isEnabled()
            # Clean up
            if window._playback_thread is not None:
                window._playback_thread.quit()
                window._playback_thread.wait()
            window.close()

    def test_on_load_finished_error(self, qapp):
        """_on_load_finished should show error on failure."""
        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window._load_thread = Mock()

            with patch.object(BeatExplorerWindow, "_set_playback_enabled"):
                window._on_load_finished(None, "file not found")

            assert window.explorer is None
            assert "Error" in window.status_bar.currentMessage()
            window.close()

    def test_on_playback_started_disables_buttons(self, qapp):
        """_on_playback_started should disable buttons."""
        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window._on_playback_started()
            assert not window.btn_this_beat.isEnabled()
            window.close()

    def test_on_playback_finished_enables_buttons(self, qapp):
        """_on_playback_finished should re-enable buttons."""
        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window._on_playback_finished()
            assert window.btn_this_beat.isEnabled()
            window.close()

    def test_no_crash_when_no_explorer(self, qapp):
        """Navigation methods should be no-ops when explorer is None."""
        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            # These should not raise
            window._on_next_beat()
            window._on_prev_beat()
            window._on_this_beat()
            window._on_next_bar()
            window._on_prev_bar()
            window._on_this_bar()
            window._on_goto_beat()
            window._on_goto_bar()
            window._on_apply_settings()
            window.close()

    def test_close_event_cleanup(self, qapp, mock_rb):
        """closeEvent should clean up threads and shutdown rb."""
        with patch.object(BeatExplorerWindow, "_open_file_dialog"):
            window = BeatExplorerWindow()
            window._load_thread = Mock()
            window._on_load_finished(mock_rb, "")

            # Spy on shutdown
            mock_rb.shutdown = Mock()
            window.close()
            mock_rb.shutdown.assert_called_once()


class TestMain:
    """Tests for main entry point."""

    @patch("rosabeats.beat_explorer_gui.QApplication")
    @patch("rosabeats.beat_explorer_gui.BeatExplorerWindow")
    def test_main_creates_app_and_window(self, mock_window_class, mock_qapp_class):
        mock_app = Mock()
        mock_app.exec.return_value = 0
        mock_qapp_class.return_value = mock_app

        with patch("sys.argv", ["beat-explorer-gui", "test.wav"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        mock_window_class.assert_called_once()
        call_kwargs = mock_window_class.call_args[1]
        assert call_kwargs["audio_file"] == "test.wav"
        assert call_kwargs["beats_per_bar"] == 4

    @patch("rosabeats.beat_explorer_gui.QApplication")
    @patch("rosabeats.beat_explorer_gui.BeatExplorerWindow")
    def test_main_no_audio_file(self, mock_window_class, mock_qapp_class):
        mock_app = Mock()
        mock_app.exec.return_value = 0
        mock_qapp_class.return_value = mock_app

        with patch("sys.argv", ["beat-explorer-gui"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        call_kwargs = mock_window_class.call_args[1]
        assert call_kwargs["audio_file"] is None

    @patch("rosabeats.beat_explorer_gui.QApplication")
    @patch("rosabeats.beat_explorer_gui.BeatExplorerWindow")
    def test_main_with_all_flags(self, mock_window_class, mock_qapp_class):
        mock_app = Mock()
        mock_app.exec.return_value = 0
        mock_qapp_class.return_value = mock_app

        with patch("sys.argv", [
            "beat-explorer-gui", "test.wav",
            "-b", "8", "-d", "2", "-a", "--debug",
        ]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        call_kwargs = mock_window_class.call_args[1]
        assert call_kwargs["beats_per_bar"] == 8
        assert call_kwargs["downbeat"] == 2
        assert call_kwargs["auto_downbeat"] is True
        assert call_kwargs["debug"] is True
