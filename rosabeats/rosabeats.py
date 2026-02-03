#!/usr/bin/env python
"""Core rosabeats module for audio beat tracking, segmentation, and remixing."""

from __future__ import annotations

import os.path
import random
from typing import Any, Optional

import joblib
import librosa
import numpy as np
import scipy
import scipy.ndimage
import scipy.sparse.csgraph
import sklearn
import sklearn.cluster
import sklearn.metrics
import sounddevice as sd
import soundfile as sf

# Optional import for ffms2
try:
    import ffms2
    FFMS2_AVAILABLE = True
except ImportError:
    FFMS2_AVAILABLE = False
    ffms2 = None


class rosabeats:
    """A class for analyzing and manipulating audio files, particularly focused on beat tracking and segmentation.

    This class provides functionality for:
    - Loading and processing audio files
    - Beat tracking and tempo analysis
    - Audio segmentation
    - Playback and remixing capabilities
    - Beat and bar manipulation

    Attributes:
        debug (bool): Class-level debug flag for controlling debug output
        ffms_source: FFMS2 audio source object
        data: Audio data array
        sr: Sample rate
        channels: Number of audio channels
        dtype: Data type of audio samples
        mono: Mono version of audio data
        beat_timings: Array of beat timings
        tempo: Estimated tempo in BPM
        beat_slices: List of beat slice boundaries
        total_beats: Total number of beats detected
        bars: Bar information
        total_segments: Total number of segments
        segments: List of segment information
        beatsperbar: Number of beats per bar
        downbeat: Beat index of first downbeat (start of first full bar)
        pulse_device: PulseAudio device index
        stream: Audio output stream
        remix: Remix buffer
        remix_index: Current position in remix buffer
        remix_output_file: Output file for remix
        beats_output_file: Output file for beat information
        beats_output: File handle for beat output
        output_play: Flag for enabling playback
        output_save: Flag for enabling saving
        output_beats: Flag for enabling beat output
        sourcefile: Path to source audio file
        saved_features_enabled: Flag for saved features functionality
    """

    debug: bool = False

    # -------------------------------------------------------------------------
    # Class methods
    # -------------------------------------------------------------------------

    @classmethod
    def d_print(cls, *args: Any, **kwargs: Any) -> None:
        """Print debug messages if debug mode is enabled.

        Args:
            *args: Variable length argument list to print
            **kwargs: Arbitrary keyword arguments passed to print()
        """
        if cls.debug:
            print("-> ", "".join(map(str, args)), **kwargs, flush=True)

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self, infile: Optional[str] = None, debug: bool = False) -> None:
        """Initialize the rosabeats object.

        Args:
            infile: Path to input audio file
            debug: Enable debug mode
        """
        rosabeats.debug = debug

        self.ffms_source: Any = None
        self.data: Optional[np.ndarray] = None
        self.sr: Optional[int] = None
        self.channels: Optional[int] = None
        self.dtype: Any = None
        self.mono: Optional[np.ndarray] = None
        self.beat_timings: Optional[np.ndarray] = None
        self.beat_samples: Optional[np.ndarray] = None
        self.tempo: Optional[float] = None
        self.beat_slices: Optional[list] = None
        self.total_beats: Optional[int] = None
        self.total_bars: Optional[int] = None
        self.bars: Any = None
        self.total_segments: Optional[int] = None
        self.segments: Optional[list] = None
        self.beatsperbar: Optional[int] = None
        self.downbeat: Optional[int] = None
        self.pulse_device: Optional[int] = None
        self.stream: Any = None
        self.remix: Optional[np.ndarray] = None
        self.remix_index: Optional[int] = None
        self.remix_output_file: Optional[str] = None
        self.beats_output_file: Optional[str] = None
        self.beats_output: Any = None
        self.output_play: bool = False
        self.output_save: bool = False
        self.output_beats: bool = False
        self.sourcefile: Optional[str] = None
        self.saved_features: Optional[str] = None

        # things get confusing when you are experimenting a lot and forgetting
        # that it's using old features/settings that are pickled away out of sight
        self.saved_features_enabled: bool = False

        if infile is not None:
            self.setfile(infile)

    # -------------------------------------------------------------------------
    # Property aliases for consistent naming
    # -------------------------------------------------------------------------

    @property
    def beats_per_bar(self) -> Optional[int]:
        """Alias for beatsperbar for consistent naming."""
        return self.beatsperbar

    @beats_per_bar.setter
    def beats_per_bar(self, value: int) -> None:
        self.beatsperbar = value

    # -------------------------------------------------------------------------
    # File and path methods
    # -------------------------------------------------------------------------

    def setfile(self, infile: str) -> None:
        """Set the input audio file and initialize related paths.

        Args:
            infile: Path to input audio file
        """
        self.sourcefile = os.path.abspath(infile)
        dname = os.path.dirname(self.sourcefile)
        bname = os.path.basename(self.sourcefile)
        stem, _ = os.path.splitext(bname)
        self.saved_features = os.path.join(dname, "." + stem + ".pkl")

    # -------------------------------------------------------------------------
    # Audio loading methods
    # -------------------------------------------------------------------------

    def _load_ffms(self) -> None:
        """Load audio file using FFMS2 library."""
        self.ffms_source = ffms2.AudioSource(self.sourcefile)
        self.ffms_source.init_buffer(count=self.ffms_source.properties.NumSamples)
        self.data = self.ffms_source.get_audio(start=0).T
        self.sr = self.ffms_source.properties.SampleRate
        self.channels = self.ffms_source.properties.Channels
        self.dtype = type(self.data[0][0])

    def _load_soundfile(self) -> None:
        """Load audio file using soundfile library."""
        self.data, self.sr = sf.read(self.sourcefile, dtype="float32")
        self.data = self.data.T
        self.channels = self.data.ndim
        self.dtype = "float32"

    def _load_librosa(self) -> None:
        """Load audio file using librosa library."""
        self.data, self.sr = librosa.load(self.sourcefile, sr=None, mono=False)
        self.channels = self.data.ndim
        self.dtype = type(self.data[0][0])

    def load(self) -> None:
        """Load audio file using appropriate library based on file extension.

        Raises:
            ImportError: If FFMS2 is required but not available
        """
        base, ext = os.path.splitext(self.sourcefile)
        if ext == ".wav":
            rosabeats.d_print("loading via librosa")
            self._load_librosa()
        elif ext == ".ogg":
            rosabeats.d_print("loading via soundfile")
            self._load_soundfile()
        else:
            if not FFMS2_AVAILABLE:
                raise ImportError("ffms2 is required for loading non-wav/ogg files. Please install ffms2.")
            rosabeats.d_print("loading via ffms")
            self._load_ffms()

        self.data, _ = librosa.effects.trim(self.data)

    def mix_to_mono(self) -> None:
        """Convert audio data to mono."""
        if self.data is None:
            self.load()

        self.mono = librosa.to_mono(self.data)

    # -------------------------------------------------------------------------
    # Beat tracking methods
    # -------------------------------------------------------------------------

    def track_beats(self, beatsper: int = 8, downbeat: int = 0) -> None:
        """Track beats in the audio file.

        Args:
            beatsper: Number of beats per bar (default: 8)
            downbeat: Beat index of first downbeat (default: 0).
                Use detect_downbeat() for auto-detection.
        """
        if self._has_saved_features():
            self._load_saved_features()
            return

        if self.mono is None:
            self.mix_to_mono()

        rosabeats.d_print("tracking beats...")
        self.tempo, self.beat_timings = librosa.beat.beat_track(y=self.mono, sr=self.sr, units='time')
        self.beat_samples = librosa.time_to_samples(self.beat_timings, sr=self.sr)
        self.beat_slices = [
            (start, end)
            for (start, end) in zip(self.beat_samples, self.beat_samples[1:])
        ]
        self.total_beats = len(self.beat_timings)

        self.beatsperbar = beatsper
        self.downbeat = downbeat

        self.total_bars = int((self.total_beats - self.downbeat) / self.beatsperbar)

        self._save_features()

    def detect_downbeat(self, beatsper: int) -> int:
        """Detect downbeat using Dynamic Bayesian Network approach.

        This uses a DBN/HMM approach for downbeat detection,
        implemented in pure Python.

        Args:
            beatsper: Number of beats per bar

        Returns:
            Beat index of the detected first downbeat
        """
        from rosabeats.downbeat import detect_downbeat_dbn

        if self.mono is None:
            self.mix_to_mono()

        if self.beat_timings is None:
            raise Exception("must call track_beats first to get beat timings")

        rosabeats.d_print("detecting downbeat using DBN...")

        downbeat_idx = detect_downbeat_dbn(
            self.mono, self.sr, self.beat_timings, beats_per_bar=beatsper
        )

        rosabeats.d_print(f"DBN detected downbeat at beat {downbeat_idx}")
        return downbeat_idx

    # Backward compatibility alias
    detect_downbeat_dbn = detect_downbeat

    # -------------------------------------------------------------------------
    # Segmentation methods
    # -------------------------------------------------------------------------

    def segment(self, redo: bool = False, max_clusters: int = 48) -> None:
        """Segment the audio file using Laplacian spectral clustering.

        Args:
            redo: Force re-segmentation even if segments exist
            max_clusters: Maximum clusters (default: 48)
        """
        self.segment_laplacian(redo, max_clusters)

    def segment_laplacian(self, redo: bool = False, max_clusters: int = 48) -> None:
        """Segment audio using Laplacian segmentation method.

        Args:
            redo: Force re-segmentation even if segments exist
            max_clusters: Maximum number of clusters to use
        """
        if self.beat_timings is None:
            self.track_beats()

        if self.total_segments is not None and redo is False:
            rosabeats.d_print(
                "warning: you already have segment data and did not specify a redo"
            )
            return

        rosabeats.d_print("segmenting song...")
        duration = librosa.get_duration(y=self.mono, sr=self.sr)

        beat_frames = librosa.time_to_frames(self.beat_timings, sr=self.sr)

        BINS_PER_OCTAVE = 12 * 3
        N_OCTAVES = 7

        cqt = librosa.cqt(y=self.mono, sr=self.sr, bins_per_octave=BINS_PER_OCTAVE, n_bins=N_OCTAVES * BINS_PER_OCTAVE)
        C = librosa.amplitude_to_db(np.abs(cqt), ref=np.max)

        Csync = librosa.util.sync(C, beat_frames, aggregate=np.median)

        beat_times = librosa.frames_to_time(librosa.util.fix_frames(beat_frames,
                                                                    x_min=0,
                                                                    x_max=C.shape[1]),
                                            sr=self.sr)

        R = librosa.segment.recurrence_matrix(Csync, width=3, mode='affinity',
                                              sym=True)

        df = librosa.segment.timelag_filter(scipy.ndimage.median_filter)
        Rf = df(R, size=(1, 7))

        mfcc = librosa.feature.mfcc(y=self.mono, sr=self.sr)
        Msync = librosa.util.sync(mfcc, beat_frames)

        path_distance = np.sum(np.diff(Msync, axis=1)**2, axis=0)
        sigma = np.median(path_distance)
        path_sim = np.exp(-path_distance / sigma)

        R_path = np.diag(path_sim, k=1) + np.diag(path_sim, k=-1)

        deg_path = np.sum(R_path, axis=1)
        deg_rec = np.sum(Rf, axis=1)

        mu = deg_path.dot(deg_path + deg_rec) / np.sum((deg_path + deg_rec)**2)

        A = mu * Rf + (1 - mu) * R_path
        L = scipy.sparse.csgraph.laplacian(A, normed=True)
        _, evecs = scipy.linalg.eigh(L)

        evecs = scipy.ndimage.median_filter(evecs, size=(9, 1))

        Cnorm = np.cumsum(evecs**2, axis=1)**0.5

        ####
        _clusters_list = []

        best_cluster_size = 0
        best_labels = None
        best_cluster_score = 0

        # we need at least 3 clusters for any song and shouldn't need to calculate more than
        # 48 clusters for even a really complicated piece of music.

        for n_clusters in range(max_clusters, 2, -1):
            rosabeats.d_print("Testing a cluster value of %d..." % n_clusters)

            # compute a matrix of the Eigen-vectors / their normalized values
            X = evecs[:, :n_clusters] / Cnorm[:, n_clusters-1:n_clusters]

            # create the candidate clusters and fit them
            clusterer = sklearn.cluster.KMeans(n_clusters=n_clusters, max_iter=300,
                                               random_state=0, n_init=20)

            cluster_labels = clusterer.fit_predict(X)

            silhouette_avg = sklearn.metrics.silhouette_score(X, cluster_labels)

            labels = cluster_labels.tolist()
            segment_count = 0.0
            segment_length = 0
            clusters = max(labels) + 1

            previous_label = -1

            segment_lengths = []

            for label in labels:
                if label != previous_label:
                    previous_label = label
                    segment_count += 1.0

                    if segment_length > 0:
                        segment_lengths.append(segment_length)

                    segment_length = 1
                else:
                    segment_length += 1

            ratio = float(segment_count) / float(clusters)
            min_segment_len = min(segment_lengths)

            orphan_scaler = .8 if min_segment_len == 1 else 1

            cluster_score = n_clusters * silhouette_avg * ratio * orphan_scaler

            if cluster_score >= best_cluster_score:
                best_cluster_score = cluster_score
                best_cluster_size = n_clusters
                best_labels = cluster_labels

        k = best_cluster_size

        rosabeats.d_print("using best cluster size %d" % k)

        X = evecs[:, :k] / Cnorm[:, k-1:k]
        seg_ids = sklearn.cluster.KMeans(n_clusters=k, max_iter=1000,
                                         random_state=0, n_init=1000).fit_predict(X)

        bound_beats = 1 + np.flatnonzero(seg_ids[:-1] != seg_ids[1:])

        bound_beats = librosa.util.fix_frames(bound_beats, x_min=0)
        bound_segs = list(seg_ids[bound_beats])
        bound_frames = beat_frames[bound_beats]

        bound_frames = librosa.util.fix_frames(bound_frames,
                                               x_min=None,
                                               x_max=C.shape[1]-1)

        bound_samples = librosa.frames_to_samples(bound_frames)

        self.segments = []
        prev = 0
        for sample, label in zip(bound_samples, bound_segs):
            segment_boundaries = (prev, sample - 1)
            prev = sample
            segment_time_boundaries = librosa.samples_to_time(segment_boundaries, sr=self.sr)
            start, end = segment_time_boundaries
            duration = end - start
            segment = {
                'label': int(label),
                'start': start,
                'duration': duration,
                'samples': segment_boundaries,
                'beats': [],
                'bars': [],
            }
            self.segments.append(segment)

        # Add final segment from last boundary to end of audio
        total_samples = len(self.mono)
        if prev < total_samples:
            final_label = int(seg_ids[-1])
            segment_boundaries = (prev, total_samples - 1)
            segment_time_boundaries = librosa.samples_to_time(segment_boundaries, sr=self.sr)
            start, end = segment_time_boundaries
            duration = end - start
            segment = {
                'label': final_label,
                'start': start,
                'duration': duration,
                'samples': segment_boundaries,
                'beats': [],
                'bars': [],
            }
            self.segments.append(segment)

        self.total_segments = len(self.segments)
        self._save_features()

    def segmentize_beats(self) -> None:
        """Associate beats and bars with segments.

        Raises:
            Exception: If segments or beat timings are not available
        """
        if self.segments is None or self.beat_timings is None:
            raise Exception("must segment() and track beats before segmentizing beats")

        rosabeats.d_print("segmentizing beats/bars...")

        for idx, seg in enumerate(self.segments):
            rosabeats.d_print("segmentizing beats for segment %d" % idx)

            seg_first = seg["samples"][0]
            seg_last = seg["samples"][1]

            # for each beat in the song...
            for beat_num in range(self.total_beats - 1):
                # obtain sample where beat starts
                beat_first = self.beat_slices[beat_num][0]

                # see if the beat starts inside the segment boundaries
                if beat_first >= seg_first and beat_first <= seg_last:
                    # the beat starts firmly within the segment
                    # so save this beat to the list of beats associated with this segment
                    seg["beats"].append(beat_num)

                # now let's see if this beat starts a bar
                bar_num = self.beat_starts_bar(beat_num)

                # if it does start a bar...
                if bar_num is not None:
                    # determine the beat number of the last beat in the bar (i.e. 0 + (8-1) = 7, so 0-7)
                    beat_num_final = int(beat_num + (self.beatsperbar - 1))

                    # obtain sample where final beat in bar starts
                    try:
                        beat_final_first = self.beat_slices[beat_num_final][0]
                    except:
                        rosabeats.d_print(
                            "warning: beat %d does not exist" % beat_num_final
                        )
                        continue

                    # see if the final beat in bar starts inside the segment boundaries
                    if beat_final_first >= seg_first and beat_final_first <= seg_last:
                        # last beat starts in segment
                        seg["bars"].append(int(bar_num))

        self._save_features()

    # -------------------------------------------------------------------------
    # Bar/beat calculation methods
    # -------------------------------------------------------------------------

    def beat_starts_bar(self, beatnum: int) -> Optional[int]:
        """Check if a beat number starts a new bar.

        Args:
            beatnum: Beat number to check

        Returns:
            Bar number if beat starts a bar, None otherwise
        """
        if (beatnum - self.downbeat) % self.beatsperbar == 0:
            return (beatnum - self.downbeat) // self.beatsperbar
        else:
            return None

    def bar_containing_beat(self, beatnum: int) -> tuple[int, int]:
        """Get the bar number and beat position within bar for a given beat number.

        Args:
            beatnum: Beat number to analyze

        Returns:
            Tuple of (bar_number, beat_position_in_bar)

        Raises:
            Exception: If beat number is out of range
        """
        if beatnum > self.total_beats - 1 or beatnum < 0:
            raise Exception("%d is outside possible range" % beatnum)

        bar = int((beatnum - self.downbeat) / self.beatsperbar)

        if bar > self.total_bars - 1 or bar < 0:
            raise Exception(
                "got %d in bar %d but bar %d shouldn't exist" % (beatnum, bar, bar)
            )

        rem = (beatnum - self.downbeat) % self.beatsperbar

        # returns the bar and the beat # in the bar
        return bar, rem

    # -------------------------------------------------------------------------
    # Output configuration methods
    # -------------------------------------------------------------------------

    def _set_remix_output_file(self, wavfile: str) -> None:
        """Set the output file for the remix.

        Args:
            wavfile: Path to output WAV file
        """
        self.remix_output_file = wavfile

    def _set_beats_output_file(self, beatsfile: str) -> None:
        """Set the output file for beat information.

        Args:
            beatsfile: Path to output beats file
        """
        self.beats_output_file = beatsfile

    def _set_default_beats_output_file(self) -> None:
        """Set default beats output file based on source filename."""
        basename = os.path.basename(self.sourcefile)
        stub, ext = os.path.splitext(basename)
        self._set_beats_output_file(stub + "_beats.br")

    def _start_writing_beats_output(self) -> None:
        """Initialize beat output file and write header information."""
        if self.beats_output_file is None:
            self._set_default_beats_output_file()

        self.beats_output = open(self.beats_output_file, "w")
        self.beats_output.write("file %s\n" % self.sourcefile)
        self.beats_output.write(
            "beats_bar %d %d\n" % (self.beatsperbar, self.downbeat)
        )

    def enable_output_play(self) -> None:
        """Enable playback functionality."""
        self.output_play = True

    def disable_output_play(self) -> None:
        """Disable playback functionality."""
        self.output_play = False

    def enable_output_save(self, wavfile: str) -> None:
        """Enable save output functionality and set output file.

        Args:
            wavfile: Path to output WAV file
        """
        self._set_remix_output_file(wavfile)
        self.output_save = True

    def disable_output_save(self) -> None:
        """Disable save output functionality."""
        self.output_save = False

    def enable_output_beats(self, beatsfile: str) -> None:
        """Enable beat output functionality and set output file.

        Args:
            beatsfile: Path to output beats file
        """
        self._set_beats_output_file(beatsfile)
        self.output_beats = True

    def disable_output_beats(self) -> None:
        """Disable beat output functionality."""
        self.output_beats = False

    def init_outputs(self) -> None:
        """Initialize all enabled output methods."""
        if self.output_play:
            self.setup_playback()
        if self.output_save:
            self.reset_remix()
        if self.output_beats:
            self._start_writing_beats_output()

    # -------------------------------------------------------------------------
    # Playback methods
    # -------------------------------------------------------------------------

    def _find_pulseaudio_device(self) -> None:
        """Find and set the PulseAudio device for playback."""
        dev_count = 0
        for dev_name in [x["name"] for x in sd.query_devices()]:
            if dev_name == "pulse":
                self.pulse_device = dev_count
                break
            dev_count += 1

        if self.pulse_device is not None:
            sd.default.device = self.pulse_device

    def setup_playback(self) -> None:
        """Set up audio playback configuration."""
        if self.sr is None:
            self.load()

        sd.default.channels = self.channels
        sd.default.samplerate = self.sr
        sd.default.dtype = self.dtype

        self._find_pulseaudio_device()

        self.stream = sd.OutputStream()
        self.stream.start()

    def play_beat(self, b: int, silent: bool = False, divisor: int = 1) -> None:
        """Play a single beat.

        Args:
            b: Beat number to play
            silent: Suppress console output
            divisor: Beat division factor

        Raises:
            Exception: If beat tracking has not been performed
        """
        if self.beat_slices is None:
            raise Exception("must track beats before playing beats")

        try:
            first, last = self.beat_slices[b]
        except:
            if not silent:
                print("*NOB* ", end="", flush=True)
            print(flush=True)
            print("error: beat %d does not exist" % b)
            return

        if divisor > 1:
            beat_len = last - first
            beat_len = int(beat_len / divisor)
            last = first + beat_len

        if not silent:
            print("%d" % b, end="", flush=True)
            if divisor > 1:
                print("/%d" % divisor, flush=True)
            print(" ", end="", flush=True)

        if self.output_play:
            self.stream.write(
                np.ascontiguousarray(
                    np.array((self.data[0][first:last], self.data[1][first:last])).T
                )
            )

        if self.output_save:
            self._copy_to_remix(0, self.data[0][first:last])
            self._copy_to_remix(1, self.data[1][first:last])
            self.remix_index += len(self.data[0][first:last])

        if self.output_beats:
            if divisor > 1:
                self.write_out("beat_div %d %d 1" % (b, divisor))
            else:
                self.write_out("beats %d" % b)

    def play_beats(self, beats: list[int]) -> None:
        """Play a sequence of beats.

        Args:
            beats: List of beat numbers to play
        """
        for beat in beats:
            self.play_beat(beat)
        print(flush=True)

    def play_bar(self, m: int, reverse: bool = False, silent: bool = False) -> None:
        """Play a single bar.

        Args:
            m: Bar number to play
            reverse: Play bar in reverse order
            silent: Suppress console output

        Raises:
            Exception: If beat tracking has not been performed
        """
        if self.beatsperbar is None or self.beat_slices is None:
            raise Exception("must track beats before you can play bar")

        if self.output_beats:
            self.write_out("# bar %d" % m)

        if not silent:
            print("[%d]" % m, end="", flush=True)

        first_beat = int(m * self.beatsperbar) + self.downbeat
        last_beat = int(first_beat + self.beatsperbar) - 1
        if last_beat > self.total_beats - 1:
            last_beat = int(self.total_beats) - 1

        beats = [x for x in range(first_beat, last_beat + 1)]
        if reverse:
            if not silent:
                print("[rev] ", end="", flush=True)
            beats.reverse()

        for beat in beats:
            if beat == first_beat:
                if not silent:
                    print("*", end="", flush=True)
            self.play_beat(beat)
        if not silent:
            print(flush=True)

    def play_bars(self, bars: list[int], reverse: bool = False) -> None:
        """Play a sequence of bars.

        Args:
            bars: List of bar numbers to play
            reverse: Play bars in reverse order
        """
        for bar in bars:
            self.play_bar(bar, reverse=reverse)

    def rest(self, beats: float) -> None:
        """Add silence for specified number of beats.

        Args:
            beats: Number of beats to rest
        """
        sec_per_beat = float(1 / (self.tempo / 60))
        sec_of_silence = sec_per_beat * beats
        samples_of_silence = int(sec_of_silence * self.sr)
        silence = np.zeros(shape=(samples_of_silence,), dtype=self.dtype)
        rosabeats.d_print(
            "resting %02g sec (%02g beats at %02g seconds per beat)"
            % (sec_of_silence, beats, sec_per_beat)
        )
        if self.output_play:
            self.stream.write(
                np.zeros(shape=(samples_of_silence, self.channels), dtype=self.dtype)
            )

        if self.output_save:
            for x in range(self.channels):
                self.remix[
                    x, self.remix_index : self.remix_index + len(silence)
                ] += silence
            self.remix_index += len(silence)

        if self.output_beats:
            self.write_out("rest %g" % beats)

    # -------------------------------------------------------------------------
    # Remix buffer methods
    # -------------------------------------------------------------------------

    def reset_remix(self) -> None:
        """Reset the remix buffer to initial state."""
        if self.sr is None:
            self.load()

        if self.remix is not None:
            del self.remix

        # initializes an array that will hold 30 minutes of audio samples
        length = 30 * 60 * self.sr
        self.remix = np.zeros(shape=(self.channels, length), dtype=self.dtype)
        self.remix_index = 0

    def _extend_remix(self) -> None:
        """Extend the remix buffer by adding more space."""
        if self.sr is None:
            self.load()

        rosabeats.d_print()
        rosabeats.d_print("***********extending available space for remixed beats")
        rosabeats.d_print("***********len(remix[0]) before: %s" % len(self.remix[0]))
        # add another 30 minutes
        length = 30 * 60 * self.sr
        extended_array = np.concatenate(
            (self.remix.T, np.zeros(shape=(length, self.channels), dtype=self.dtype)),
            axis=0,
        )
        self.remix = extended_array.T
        rosabeats.d_print("***********len(remix[0]) after: %s" % len(self.remix[0]))
        rosabeats.d_print("******done extending available space for remixed beats")

    def _copy_to_remix(self, channel: int, data: np.ndarray) -> None:
        """Copy audio data to remix buffer, extending if necessary.

        Args:
            channel: Channel index (0 or 1 for stereo)
            data: Audio data to copy
        """
        try:
            self.remix[channel, self.remix_index:self.remix_index + len(data)] += data
        except ValueError:
            self._extend_remix()
            self.remix[channel, self.remix_index:self.remix_index + len(data)] += data

    def save_remix(self) -> None:
        """Save the remix to the output file."""
        yt, index = librosa.effects.trim(self.remix)
        sf.write(self.remix_output_file, yt.T, self.sr, "PCM_16")

    # -------------------------------------------------------------------------
    # Feature caching methods
    # -------------------------------------------------------------------------

    def _has_saved_features(self) -> bool:
        """Check if saved features file exists.

        Returns:
            True if saved features file exists and is enabled
        """
        return self.saved_features_enabled and os.path.isfile(self.saved_features)

    def _save_features(self) -> None:
        """Save extracted features to file."""
        rosabeats.d_print("saving features...")

        features = dict()
        features["tempo"] = self.tempo
        features["beatsperbar"] = self.beatsperbar
        features["downbeat"] = self.downbeat
        features["total_beats"] = self.total_beats
        features["total_bars"] = self.total_bars if self.total_bars else None
        features["total_segments"] = self.total_segments
        features["beat_timings"] = self.beat_timings
        features["beat_samples"] = self.beat_samples
        features["beat_slices"] = self.beat_slices
        features["segments"] = self.segments
        # write features
        with open(self.saved_features, "wb") as f:
            joblib.dump(features, f)

    def _load_saved_features(self) -> None:
        """Load saved features from file."""
        rosabeats.d_print("loading features...")

        with open(self.saved_features, "rb") as f:
            features = joblib.load(f)

        self.tempo = features["tempo"]
        self.beatsperbar = features["beatsperbar"]
        self.downbeat = features["downbeat"]
        self.total_beats = features["total_beats"]
        self.total_bars = features["total_bars"]
        self.total_segments = features["total_segments"]
        self.beat_timings = features["beat_timings"]
        self.beat_samples = features["beat_samples"]
        self.beat_slices = features["beat_slices"]
        self.segments = features["segments"]

    def remove_features_file(self) -> None:
        """Remove the saved features file if it exists."""
        if os.path.isfile(self.saved_features):
            rosabeats.d_print("removing %s" % self.saved_features)
            os.unlink(self.saved_features)
        else:
            rosabeats.d_print("no features file found")

    # -------------------------------------------------------------------------
    # Convenience methods (merged from scripts)
    # -------------------------------------------------------------------------

    def shuffle_all_beats(self, output_file: Optional[str] = None) -> None:
        """Shuffle all beats and optionally save to file.

        Args:
            output_file: Optional path to save output WAV file
        """
        if self.beat_slices is None:
            self.track_beats()

        beatlist = list(range(self.total_beats))
        random.shuffle(beatlist)

        if output_file:
            self.enable_output_save(output_file)
            self.reset_remix()

        self.play_beats(beatlist)

        if output_file:
            self.save_remix()

    def shuffle_all_bars(self, output_file: Optional[str] = None) -> None:
        """Shuffle all bars and optionally save to file.

        Args:
            output_file: Optional path to save output WAV file
        """
        if self.beat_slices is None:
            self.track_beats()

        barlist = list(range(self.total_bars))
        random.shuffle(barlist)

        if output_file:
            self.enable_output_save(output_file)
            self.reset_remix()

        self.play_bars(barlist)

        if output_file:
            self.save_remix()

    def reverse_beats_in_all_bars(self, output_file: Optional[str] = None) -> None:
        """Play all bars with beats reversed within each bar.

        Args:
            output_file: Optional path to save output WAV file
        """
        if self.beat_slices is None:
            self.track_beats()

        if output_file:
            self.enable_output_save(output_file)
            self.reset_remix()

        for bar in range(self.total_bars):
            self.play_bar(bar, reverse=True)

        if output_file:
            self.save_remix()

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    def write_out(self, text: str) -> None:
        """Write text to beats output file.

        Args:
            text: Text to write
        """
        if self.beats_output is None:
            self._start_writing_beats_output()

        self.beats_output.write("%s\n" % text)

    def shutdown(self) -> None:
        """Clean up and close all output streams."""
        if self.output_play:
            self.stream.close()
        if self.output_save:
            self.save_remix()
        if self.output_beats:
            self.beats_output.close()

    def divide_bars(self) -> None:
        """Deprecated method that no longer performs any action."""
        rosabeats.d_print("warning: divide_bars() no longer does anything")
