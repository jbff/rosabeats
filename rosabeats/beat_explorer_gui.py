#!/usr/bin/env python
"""PyQt6 GUI for exploring beats and bars in audio files.

Provides a graphical interface for navigating through beats and bars
using the rosabeats beat tracking engine, with non-blocking playback
via QThread workers.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from rosabeats.beat_explorer_cli import BeatExplorerCLI
from rosabeats.rosabeats import rosabeats


class LoadWorker(QObject):
    """Worker that loads and initializes a rosabeats instance off the main thread."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object, str)

    def __init__(
        self,
        audio_file: str,
        beats_per_bar: int,
        downbeat: int,
        auto_downbeat: bool,
        debug: bool,
    ) -> None:
        super().__init__()
        self.audio_file = audio_file
        self.beats_per_bar = beats_per_bar
        self.downbeat = downbeat
        self.auto_downbeat = auto_downbeat
        self.debug = debug

    def run(self) -> None:
        try:
            self.progress.emit("Loading audio file...")
            rb = rosabeats(self.audio_file, debug=self.debug)

            self.progress.emit("Tracking beats...")
            rb.track_beats(beatsper=self.beats_per_bar, downbeat=self.downbeat)

            if self.auto_downbeat:
                self.progress.emit("Detecting downbeat...")
                detected = rb.detect_downbeat(self.beats_per_bar)
                rb.downbeat = detected
                rb.total_bars = (rb.total_beats - detected) // self.beats_per_bar

            self.progress.emit("Initializing playback...")
            rb.enable_output_play()
            rb.init_outputs()

            self.finished.emit(rb, "")
        except Exception as e:
            self.finished.emit(None, str(e))


class DetectWorker(QObject):
    """Worker that runs downbeat detection on a dedicated thread."""

    finished = pyqtSignal(object, str)  # (detected downbeat index or None, error)

    def __init__(self, rb: rosabeats, beats_per_bar: int) -> None:
        super().__init__()
        self.rb = rb
        self.beats_per_bar = beats_per_bar

    def run(self) -> None:
        try:
            detected = self.rb.detect_downbeat(self.beats_per_bar)
            self.finished.emit(int(detected), "")
        except Exception as e:
            self.finished.emit(None, str(e))


class PlaybackWorker(QObject):
    """Worker that executes blocking playback calls on a dedicated thread."""

    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(str)

    play_beat_signal = pyqtSignal(int)
    play_bar_signal = pyqtSignal(int, int, int)

    def __init__(self, rb: rosabeats) -> None:
        super().__init__()
        self.rb = rb
        # NOTE: do NOT connect play_beat_signal/play_bar_signal here. This
        # object is still on the GUI thread during construction; a
        # self-connection made now would run playback as a direct call on
        # the GUI thread instead of queueing it on the worker thread.
        # Connections are made in _on_load_finished after moveToThread()
        # (queued), so playback truly runs off the GUI thread.

    def _play_beat(self, beat_index: int) -> None:
        self.started.emit()
        try:
            self.rb.play_beat(beat_index, silent=True)
        except Exception as e:
            self.error.emit(str(e))
        self.finished.emit()

    def _play_bar(self, first_beat: int, last_beat: int, total_beats: int) -> None:
        self.started.emit()
        try:
            for b in range(first_beat, min(last_beat, total_beats)):
                self.rb.play_beat(b, silent=True)
        except Exception as e:
            self.error.emit(str(e))
        self.finished.emit()


class BeatExplorerWindow(QMainWindow):
    """Main window for the beat explorer GUI."""

    def __init__(
        self,
        audio_file: Optional[str] = None,
        beats_per_bar: int = 4,
        downbeat: int = 0,
        auto_downbeat: bool = False,
        debug: bool = False,
    ) -> None:
        super().__init__()
        self.explorer: Optional[BeatExplorerCLI] = None
        self._playback_thread: Optional[QThread] = None
        self._playback_worker: Optional[PlaybackWorker] = None
        self._load_thread: Optional[QThread] = None
        self._load_worker: Optional[LoadWorker] = None
        self._detect_thread: Optional[QThread] = None
        self._detect_worker: Optional[DetectWorker] = None
        self._busy: bool = False
        self._apply_beats_per_bar: int = 0
        self._apply_old_index: int = 0
        self._beats_per_bar = beats_per_bar
        self._downbeat = downbeat
        self._auto_downbeat = auto_downbeat
        self._debug = debug

        self.setWindowTitle("Beat Explorer")
        self.setMinimumWidth(500)

        self._build_ui()
        self._setup_shortcuts()

        if audio_file:
            self._start_loading(audio_file)
        else:
            self._open_file_dialog()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Row 1: Navigation buttons
        nav_row = QHBoxLayout()

        bar_nav = QHBoxLayout()
        self.btn_prev_bar = QPushButton("< Prev Bar")
        self.btn_this_bar = QPushButton("This Bar")
        self.btn_next_bar = QPushButton("Next Bar >")
        for btn in (self.btn_prev_bar, self.btn_this_bar, self.btn_next_bar):
            bar_nav.addWidget(btn)

        beat_nav = QHBoxLayout()
        self.btn_prev_beat = QPushButton("< Prev Beat")
        self.btn_this_beat = QPushButton("This Beat")
        self.btn_next_beat = QPushButton("Next Beat >")
        for btn in (self.btn_prev_beat, self.btn_this_beat, self.btn_next_beat):
            beat_nav.addWidget(btn)

        nav_row.addLayout(bar_nav)
        nav_row.addSpacing(20)
        nav_row.addLayout(beat_nav)
        layout.addLayout(nav_row)

        # Row 2: Go-to controls
        goto_row = QHBoxLayout()

        goto_bar_layout = QHBoxLayout()
        goto_bar_layout.addWidget(QLabel("Go to bar:"))
        self.spin_goto_bar = QSpinBox()
        self.spin_goto_bar.setMinimum(0)
        goto_bar_layout.addWidget(self.spin_goto_bar)
        self.btn_goto_bar = QPushButton("Go")
        goto_bar_layout.addWidget(self.btn_goto_bar)

        goto_beat_layout = QHBoxLayout()
        goto_beat_layout.addWidget(QLabel("Go to beat:"))
        self.spin_goto_beat = QSpinBox()
        self.spin_goto_beat.setMinimum(0)
        goto_beat_layout.addWidget(self.spin_goto_beat)
        self.btn_goto_beat = QPushButton("Go")
        goto_beat_layout.addWidget(self.btn_goto_beat)

        goto_row.addLayout(goto_bar_layout)
        goto_row.addSpacing(20)
        goto_row.addLayout(goto_beat_layout)
        layout.addLayout(goto_row)

        # Row 3: Current position group
        pos_group = QGroupBox("Current Position")
        pos_layout = QHBoxLayout(pos_group)
        self.lbl_beat = QLabel("Beat: -")
        self.lbl_bar = QLabel("Bar: -")
        self.lbl_in_bar = QLabel("In bar: -")
        for lbl in (self.lbl_beat, self.lbl_bar, self.lbl_in_bar):
            pos_layout.addWidget(lbl)
        layout.addWidget(pos_group)

        # Row 4: Beats per bar / downbeat settings
        settings_row = QHBoxLayout()
        settings_row.addWidget(QLabel("Beats/bar:"))
        self.spin_bpb = QSpinBox()
        self.spin_bpb.setRange(1, 32)
        self.spin_bpb.setValue(self._beats_per_bar)
        settings_row.addWidget(self.spin_bpb)

        settings_row.addSpacing(10)
        settings_row.addWidget(QLabel("Downbeat:"))
        self.spin_downbeat = QSpinBox()
        self.spin_downbeat.setMinimum(0)
        self.spin_downbeat.setValue(self._downbeat)
        settings_row.addWidget(self.spin_downbeat)

        self.btn_apply = QPushButton("Apply")
        settings_row.addWidget(self.btn_apply)

        self.chk_auto_downbeat = QCheckBox("Auto-detect")
        self.chk_auto_downbeat.setChecked(self._auto_downbeat)
        settings_row.addWidget(self.chk_auto_downbeat)

        settings_row.addStretch()
        layout.addLayout(settings_row)

        # Row 5: Track info
        info_row = QHBoxLayout()
        self.lbl_total_beats = QLabel("Total beats: -")
        self.lbl_total_bars = QLabel("Total bars: -")
        self.lbl_tempo = QLabel("Tempo: - BPM")
        for lbl in (self.lbl_total_beats, self.lbl_total_bars, self.lbl_tempo):
            info_row.addWidget(lbl)
        layout.addLayout(info_row)

        # Row 6: Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Connect signals
        self.btn_prev_bar.clicked.connect(self._on_prev_bar)
        self.btn_this_bar.clicked.connect(self._on_this_bar)
        self.btn_next_bar.clicked.connect(self._on_next_bar)
        self.btn_prev_beat.clicked.connect(self._on_prev_beat)
        self.btn_this_beat.clicked.connect(self._on_this_beat)
        self.btn_next_beat.clicked.connect(self._on_next_beat)
        self.btn_goto_bar.clicked.connect(self._on_goto_bar)
        self.btn_goto_beat.clicked.connect(self._on_goto_beat)
        self.btn_apply.clicked.connect(self._on_apply_settings)

        self._set_playback_enabled(False)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._on_prev_beat)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._on_next_beat)
        QShortcut(
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Left),
            self,
            self._on_prev_bar,
        )
        QShortcut(
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Right),
            self,
            self._on_next_bar,
        )
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._on_this_beat)
        QShortcut(QKeySequence(Qt.Key.Key_B), self, self._on_this_bar)
        QShortcut(
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Q),
            self,
            self.close,
        )

    def _set_playback_enabled(self, enabled: bool) -> None:
        for btn in (
            self.btn_prev_bar,
            self.btn_this_bar,
            self.btn_next_bar,
            self.btn_prev_beat,
            self.btn_this_beat,
            self.btn_next_beat,
            self.btn_goto_bar,
            self.btn_goto_beat,
            self.btn_apply,
        ):
            btn.setEnabled(enabled)

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.wav *.ogg *.mp3 *.flac *.m4a);;All Files (*)",
        )
        if path:
            self._start_loading(path)
        else:
            self.status_bar.showMessage("No file selected")

    def _start_loading(self, audio_file: str) -> None:
        self._set_playback_enabled(False)
        self.status_bar.showMessage("Loading...")
        self.setWindowTitle(f"Beat Explorer - {audio_file}")

        self._load_thread = QThread()
        self._load_worker = LoadWorker(
            audio_file,
            self.spin_bpb.value(),
            self.spin_downbeat.value(),
            self.chk_auto_downbeat.isChecked(),
            self._debug,
        )
        self._load_worker.moveToThread(self._load_thread)
        self._load_thread.started.connect(self._load_worker.run)
        self._load_worker.progress.connect(self._on_load_progress)
        self._load_worker.finished.connect(self._on_load_finished)
        self._load_thread.start()

    def _on_load_progress(self, message: str) -> None:
        self.status_bar.showMessage(message)

    def _on_load_finished(self, rb: Optional[rosabeats], error: str) -> None:
        self._load_thread.quit()
        self._load_thread.wait()

        if error:
            self.status_bar.showMessage(f"Error: {error}")
            QMessageBox.critical(self, "Load Error", error)
            return

        self.explorer = BeatExplorerCLI(rb)

        # Set up playback worker thread
        self._playback_thread = QThread()
        self._playback_worker = PlaybackWorker(rb)
        # Connect only after moveToThread(): connections created on the GUI
        # thread before the worker's affinity changes can dispatch as direct
        # calls on the GUI thread rather than queueing on the worker thread.
        self._playback_worker.moveToThread(self._playback_thread)
        queued = Qt.ConnectionType.QueuedConnection
        self._playback_worker.play_beat_signal.connect(
            self._playback_worker._play_beat, queued
        )
        self._playback_worker.play_bar_signal.connect(
            self._playback_worker._play_bar, queued
        )
        self._playback_worker.started.connect(self._on_playback_started)
        self._playback_worker.finished.connect(self._on_playback_finished)
        self._playback_worker.error.connect(self._on_playback_error)
        self._playback_thread.start()

        # Update spinbox ranges (guarded so short/zero-beat tracks keep
        # spinboxes at a valid [0, 0] state instead of a negative range)
        self.spin_goto_beat.setMaximum(max(0, self.explorer.total_beats - 1))
        self.spin_goto_bar.setMaximum(max(0, self.explorer.total_bars - 1))
        self.spin_downbeat.setMaximum(max(0, self.explorer.total_beats - 1))
        self.spin_bpb.setValue(self.explorer.beatsperbar)
        self.spin_downbeat.setValue(self.explorer.downbeat)

        self._update_display()
        self._set_playback_enabled(True)
        self.status_bar.showMessage("Ready")

    def _on_playback_started(self) -> None:
        self._busy = True
        self._set_playback_enabled(False)
        self.status_bar.showMessage("Playing...")

    def _on_playback_finished(self) -> None:
        self._busy = False
        self._set_playback_enabled(True)
        self.status_bar.showMessage("Ready")

    def _on_playback_error(self, message: str) -> None:
        self._busy = False
        self._set_playback_enabled(True)
        self.status_bar.showMessage(f"Error: {message}")

    def _update_display(self) -> None:
        if self.explorer is None:
            return

        beat = self.explorer.current_beat()
        bar = self.explorer.current_bar()
        bar_str = str(bar) if bar is not None else "pickup"

        beat_in_bar = "-"
        if bar is not None:
            beat_in_bar = str(beat - self.explorer.first_beat_of_current_bar())

        self.lbl_beat.setText(f"Beat: {beat}")
        self.lbl_bar.setText(f"Bar: {bar_str}")
        self.lbl_in_bar.setText(f"In bar: {beat_in_bar}")

        self.lbl_total_beats.setText(f"Total beats: {self.explorer.total_beats}")
        self.lbl_total_bars.setText(f"Total bars: {self.explorer.total_bars}")
        tempo = self.explorer.rb.tempo
        if tempo is not None:
            tempo = float(tempo)
            self.lbl_tempo.setText(f"Tempo: {tempo:.1f} BPM")

    def _request_play_beat(self, beat_index: int) -> None:
        if self._playback_worker is None or self._busy:
            return
        self._playback_worker.play_beat_signal.emit(beat_index)

    def _request_play_bar(self) -> None:
        if self._playback_worker is None or self._busy:
            return
        first = self.explorer.first_beat_of_current_bar()
        last = first + self.explorer.beatsperbar
        self._playback_worker.play_bar_signal.emit(
            first, last, self.explorer.total_beats
        )

    def _guard_busy(self) -> bool:
        """Return True when a navigation/playback request must be skipped:
        explorer not loaded or playback already in flight. Keyboard
        shortcuts bypass the disabled buttons, so this check, not the
        button state, is what keeps requests from queueing up."""
        return self.explorer is None or self._playback_worker is None or self._busy

    def _on_prev_beat(self) -> None:
        if self._guard_busy():
            return
        self.explorer.prev_beat()
        self._update_display()
        self._request_play_beat(self.explorer.current_beat())

    def _on_this_beat(self) -> None:
        if self._guard_busy():
            return
        self._request_play_beat(self.explorer.current_beat())

    def _on_next_beat(self) -> None:
        if self._guard_busy():
            return
        self.explorer.next_beat()
        self._update_display()
        self._request_play_beat(self.explorer.current_beat())

    def _on_prev_bar(self) -> None:
        if self._guard_busy():
            return
        self.explorer.prev_bar()
        self._update_display()
        self._request_play_bar()

    def _on_this_bar(self) -> None:
        if self._guard_busy():
            return
        self._request_play_bar()

    def _on_next_bar(self) -> None:
        if self._guard_busy():
            return
        self.explorer.next_bar()
        self._update_display()
        self._request_play_bar()

    def _on_goto_bar(self) -> None:
        if self._guard_busy():
            return
        self.explorer.goto_bar(self.spin_goto_bar.value())
        self._update_display()
        self._request_play_beat(self.explorer.current_beat())

    def _on_goto_beat(self) -> None:
        if self._guard_busy():
            return
        self.explorer.goto_beat(self.spin_goto_beat.value())
        self._update_display()
        self._request_play_beat(self.explorer.current_beat())

    def _on_apply_settings(self) -> None:
        if self.explorer is None or self._busy:
            return

        new_bpb = self.spin_bpb.value()
        auto = self.chk_auto_downbeat.isChecked()

        # capture playback position so it survives the rebuild
        self._apply_beats_per_bar = new_bpb
        self._apply_old_index = self.explorer.current_beat()

        if auto:
            # Detection runs a full STFT/melspectrogram pass that can take
            # seconds; do it on a thread. rb is not touched until detection
            # succeeds so a failure can never leave a mixed-meter state.
            self._busy = True
            self._set_playback_enabled(False)
            self.status_bar.showMessage("Detecting downbeat...")

            self._detect_thread = QThread()
            self._detect_worker = DetectWorker(self.explorer.rb, new_bpb)
            self._detect_worker.moveToThread(self._detect_thread)
            self._detect_thread.started.connect(self._detect_worker.run)
            self._detect_worker.finished.connect(
                self._on_detect_finished, Qt.ConnectionType.QueuedConnection
            )
            self._detect_thread.start()
        else:
            rb = self.explorer.rb
            self._finish_apply(new_bpb, self.spin_downbeat.value())

    def _finish_apply(self, new_bpb: int, downbeat: int) -> None:
        """Apply the meter to rb and rebuild the explorer state."""
        rb = self.explorer.rb
        rb.beatsperbar = new_bpb
        rb.downbeat = downbeat
        rb.total_bars = (rb.total_beats - downbeat) // new_bpb

        # Rebuild explorer to pick up new settings, keeping the user's
        # position rather than teleporting back to the downbeat
        self.explorer = BeatExplorerCLI(rb)
        self.explorer.current_beat_index = max(
            0, min(self._apply_old_index, rb.total_beats - 1)
        )

        self.spin_goto_bar.setMaximum(max(0, self.explorer.total_bars - 1))
        self._update_display()
        self.status_bar.showMessage("Ready")

    def _on_detect_finished(self, detected, error) -> None:
        """Handle downbeat detection completion (GUI thread)."""
        if self._detect_thread is not None:
            self._detect_thread.quit()
            self._detect_thread.wait()
            self._detect_thread = None
            self._detect_worker = None
        self._busy = False
        self._set_playback_enabled(True)

        new_bpb = self._apply_beats_per_bar
        if error or detected is None:
            self.status_bar.showMessage(f"Error: {error}")
            return

        try:
            self._finish_apply(new_bpb, int(detected))
            self.spin_downbeat.setValue(int(detected))
        except Exception as e:
            self.status_bar.showMessage(f"Error: {e}")
            return

    def closeEvent(self, event) -> None:
        for thread in (
            self._playback_thread,
            self._detect_thread,
            self._load_thread,
        ):
            if thread is not None:
                thread.quit()
                thread.wait()
        if self.explorer is not None:
            try:
                self.explorer.rb.shutdown()
            except Exception:
                pass
        event.accept()


def main() -> None:
    """Entry point for beat-explorer-gui."""
    parser = argparse.ArgumentParser(
        description="GUI beat explorer for audio files"
    )
    parser.add_argument("audio_file", nargs="?", default=None, help="Audio file to explore")
    parser.add_argument(
        "--beats-per-bar", "-b", type=int, default=4,
        help="Number of beats per bar (default: 4)",
    )
    parser.add_argument(
        "--downbeat", "-d", type=int, default=0,
        help="Beat index of first downbeat (default: 0)",
    )
    parser.add_argument(
        "--auto-downbeat", "-a", action="store_true",
        help="Auto-detect downbeat using DBN",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    if args.beats_per_bar < 1:
        parser.error("--beats-per-bar must be at least 1")
    if args.downbeat < 0:
        parser.error("--downbeat must be a non-negative integer")

    app = QApplication(sys.argv)
    window = BeatExplorerWindow(
        audio_file=args.audio_file,
        beats_per_bar=args.beats_per_bar,
        downbeat=args.downbeat,
        auto_downbeat=args.auto_downbeat,
        debug=args.debug,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
