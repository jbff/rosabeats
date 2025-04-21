#!/usr/bin/env python

import re
import sys
import os.path
import random
import time
import joblib

import vamp
import ffms2
import numpy as np
import scipy
import sklearn
import librosa
import soundfile as sf
import sounddevice as sd

class rosabeats:
    debug = False

    @classmethod
    def d_print(cls, *args, **kwargs):
        if cls.debug:
            print("-> ", "".join(map(str, args)), **kwargs, flush=True)

    def __init__(self, infile=None, debug=False):
        rosabeats.debug = debug

        self.ffms_source = None
        self.data = None
        self.sr = None
        self.channels = None
        self.dtype = None
        self.mono = None
        self.beat_timings = None
        self.tempo = None
        self.beat_slices = None
        self.total_beats = None
        self.bars = None
        self.total_segments = None
        self.segments = None
        self.beatsperbar = None
        self.firstfullbar = None
        self.pulse_device = None
        self.stream = None
        self.remix = None
        self.remix_index = None
        self.remix_output_file = None
        self.beats_output_file = None
        self.beats_output = None
        self.output_play = False
        self.output_save = False
        self.output_beats = False
        self.sourcefile = None

        # things get confusing when you are experimenting a lot and forgetting
        # that it's using old features/settings that are pickled away out of sight
        self.saved_features_enabled = False

        if not infile is None:
            self.setfile(infile)

    def beat_starts_bar(self, beatnum):
        if (beatnum - self.firstfullbar) % self.beatsperbar == 0:
            return (beatnum - self.firstfullbar) / self.beatsperbar
        else:
            return None

    def bar_containing_beat(self, beatnum):
        if beatnum > self.total_beats - 1 or beatnum < 0:
            raise Exception("%d is outside possible range" % beatnum)

        bar = int((beatnum - self.firstfullbar) / self.beatsperbar)

        if bar > self.total_bars - 1 or bar < 0:
            raise Exception(
                "got %d in bar %d but bar %d shouldn't exist" % (beatnum, bar)
            )

        rem = (beatnum - self.firstfullbar) % self.beatsperbar

        # returns the bar and the beat # in the bar
        return bar, rem

    def set_remix_output_file(self, wavfile):
        self.remix_output_file = wavfile

    def disable_output_beats(self):
        self.output_beats = False

    def disable_output_save(self):
        self.output_save = False

    def disable_output_play(self):
        self.output_play = False

    def enable_output_beats(self, beatsfile):
        self.set_beats_output_file(beatsfile)
        self.output_beats = True

    def enable_output_save(self, wavfile):
        self.set_remix_output_file(wavfile)
        self.output_save = True

    def enable_output_play(self):
        self.output_play = True

    def reset_remix(self):
        if self.sr is None:
            self.load()

        if self.remix is not None:
            del self.remix

        # initializes an array that will hold 30 minutes of audio samples
        length = 30 * 60 * self.sr
        self.remix = np.zeros(shape=(self.channels, length), dtype=self.dtype)
        self.remix_index = 0

    def extend_remix(self):
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

    def save_remix(self):
        yt, index = librosa.effects.trim(self.remix)
        sf.write(self.remix_output_file, yt.T, self.sr, "PCM_16")

    def setfile(self, infile):
        self.sourcefile = os.path.abspath(infile)
        dname = os.path.dirname(self.sourcefile)
        bname = os.path.basename(self.sourcefile)
        stem, _ = os.path.splitext(bname)
        self.saved_features = os.path.join(dname, "." + stem + ".pkl")

    def find_pulseaudio_device(self):
        dev_count = 0
        for dev_name in [x["name"] for x in sd.query_devices()]:
            if dev_name == "pulse":
                self.pulse_device = dev_count
                break
            dev_count += 1

        if not self.pulse_device is None:
            sd.default.device = self.pulse_device

    def setup_playback(self):
        if self.sr is None:
            self.load()

        sd.default.channels = self.channels
        sd.default.samplerate = self.sr
        sd.default.dtype = self.dtype

        self.find_pulseaudio_device()

        self.stream = sd.OutputStream()
        self.stream.start()

    def init_outputs(self):
        if self.output_play:
            self.setup_playback()
        if self.output_save:
            self.reset_remix()
        if self.output_beats:
            self.start_writing_beats_output()

    def load_ffms(self):
        self.ffms_source = ffms2.AudioSource(self.sourcefile)
        self.ffms_source.init_buffer(count=self.ffms_source.properties.NumSamples)
        self.data = self.ffms_source.get_audio(start=0).T
        self.sr = self.ffms_source.properties.SampleRate
        self.channels = self.ffms_source.properties.Channels
        self.dtype = type(self.data[0][0])

    def load_soundfile(self):
        self.data, self.sr = sf.read(self.sourcefile, dtype="float32")
        self.data = self.data.T
        self.channels = self.data.ndim
        self.dtype = "float32"

    def load_librosa(self):
        self.data, self.sr = librosa.load(self.sourcefile, sr=None, mono=False)
        self.channels = self.data.ndim
        self.dtype = type(self.data[0][0])

    def load(self):
        base, ext = os.path.splitext(self.sourcefile)
        if ext == ".wav":
            rosabeats.d_print("loading via librosa")
            self.load_librosa()

        elif ext == ".ogg":
            rosabeats.d_print("loading via soundfile")
            self.load_soundfile()
        else:
            rosabeats.d_print("loading via ffms")
            self.load_ffms()

        self.data, _ = librosa.effects.trim(self.data)

    def mix_to_mono(self):
        if self.data is None:
            self.load()

        self.mono = librosa.to_mono(self.data)

    def has_saved_features(self):
        return self.saved_features_enabled and os.path.isfile(self.saved_features)

    def remove_features_file(self):
        if os.path.isfile(self.saved_features):
            rosabeats.d_print("removing %s" % self.saved_features)
            os.unlink(self.saved_features)
        else:
            rosabeats.d_print("no features file found")

    def save_features(self):
        rosabeats.d_print("saving features...")

        features = dict()
        features["tempo"] = self.tempo
        features["beatsperbar"] = self.beatsperbar
        features["firstfullbar"] = self.firstfullbar
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

    def load_saved_features(self):
        rosabeats.d_print("loading features...")

        with open(self.saved_features, "rb") as f:
            features = joblib.load(f)

        self.tempo = features["tempo"]
        self.beatsperbar = features["beatsperbar"]
        self.firstfullbar = features["firstfullbar"]
        self.total_beats = features["total_beats"]
        self.total_bars = features["total_bars"]
        self.total_segments = features["total_segments"]
        self.beat_timings = features["beat_timings"]
        self.beat_samples = features["beat_samples"]
        self.beat_slices = features["beat_slices"]
        self.segments = features["segments"]

    def track_beats(self, beatsper=8, firstfull=0):
        if self.has_saved_features():
            self.load_saved_features()
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
        self.firstfullbar = firstfull
        self.total_bars = int((self.total_beats - self.firstfullbar) / self.beatsperbar)

        self.save_features()

    def segment(self, redo=False):
        self.segment_laplacian(redo=redo)

    def segment_laplacian(self, redo=False):
        if self.beat_timings is None:
            self.track_beats()

        seg_letters = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z', 'AA','BB','CC','DD','EE','FF','GG','HH','II','JJ','KK','LL','MM','NN','OO','PP','QQ','RR','SS','TT','UU','VV','WW','XX','YY','ZZ']

        if not self.total_segments is None and redo is False:
            rosabeats.d_print(
                "warning: you already have segment data and did not specify a redo"
            )
            return

        rosabeats.d_print("segmenting song...")
        duration = librosa.get_duration(y=self.mono,sr=self.sr)

        beat_frames = librosa.time_to_frames(self.beat_timings, sr=self.sr)

        BINS_PER_OCTAVE = 12 * 3
        N_OCTAVES = 7

        cqt = librosa.cqt(y=self.mono, sr=self.sr, bins_per_octave=BINS_PER_OCTAVE, n_bins=N_OCTAVES * BINS_PER_OCTAVE)
        C = librosa.amplitude_to_db( np.abs(cqt), ref=np.max)

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

        for n_clusters in range(48, 2, -1):
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
                    segment_length +=1

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
        for sample, label in zip(bound_samples,bound_segs):
            segment_boundaries = (prev, sample-1)
            prev = sample
            segment_time_boundaries = librosa.samples_to_time(segment_boundaries,sr=self.sr)
            start, end = segment_time_boundaries
            duration = end - start
            segment = {}
            try:
                segment['label'] = seg_labels[int(label)]
            except:
                segment['label'] = label

            segment['start'] = start
            segment['duration'] = duration
            segment['samples'] = segment_boundaries
            segment['beats'] = []
            segment['bars'] = []

            self.segments.append(segment)

        self.total_segments = len(self.segments)
        self.save_features()

    def segment_segmentino(self, redo=False):
        if self.data is None:
            self.load()

        if not self.total_segments is None and redo is False:
            rosabeats.d_print(
                "warning: you already have segment data and did not specify a redo"
            )
            return

        rosabeats.d_print("segmenting song...")
        segmented = vamp.collect(self.data, self.sr, "segmentino:segmentino")

        self.total_segments = len(segmented["list"])
        self.segments = self.total_segments * [None]

        for count, result in enumerate(segmented["list"]):
            label = result["label"]
            start = float(result["timestamp"])
            duration = float(result["duration"])
            end = start + duration

            self.segments[count] = dict()
            self.segments[count]["label"] = label
            self.segments[count]["start"] = start
            self.segments[count]["duration"] = duration
            self.segments[count]["samples"] = librosa.time_to_samples(
                (start, end), sr=self.sr
            )
            self.segments[count]["beats"] = []
            self.segments[count]["bars"] = []

        self.save_features()

    def segmentize_beats(self):
        if self.segments is None or self.beat_timings is None:
            raise Exception("must segment() and track beats before segmentizing beats")

        rosabeats.d_print("segmentizing beats/bars...")

        for idx, seg in enumerate(self.segments):
            rosabeats.d_print("segmentizing beats for segment %d" % idx)

            seg_first = seg["samples"][0]
            seg_last = seg["samples"][1]

            # for each beat in the song...
            for beat_num in range(self.total_beats - 1):
#               rosabeats.d_print("examining beat %d" % beat_num)

                # obtain sample where beat starts
                beat_first = self.beat_slices[beat_num][0]
#               rosabeats.d_print("beat %d, %d <= %d <= %d ?" % (beat_num, seg_first, beat_first, seg_last))

                # see if the beat starts inside the segment boundaries
                if beat_first >= seg_first and beat_first <= seg_last:
                    # the beat starts firmly within the segment
                    # so save this beat to the list of beats associated with this segment
                    seg["beats"].append(beat_num)
                #                   rosabeats.d_print("BEAT %d is in segment %d" % (beat_num, idx))

                # now let's see if this beat starts a bar
                bar_num = self.beat_starts_bar(beat_num)

                # if it does start a bar...
                if not bar_num is None:
                    #                   rosabeats.d_print("beat %d starts bar %d" % (beat_num, bar_num))

                    # determine the beat number of the last beat in the bar (i.e. 0 + (8-1) = 7,k so 0-7)
                    beat_num_final = int(beat_num + (self.beatsperbar - 1))
                    #                   print("bar %d starts with beat %d and ends with beat %d" % (bar_num, beat_num, beat_num_final))

                    # obtain sample where final beat in bar starts
                    try:
                        beat_final_first = self.beat_slices[beat_num_final][0]
                    #                       rosabeats.d_print("beat %d stats on sample %d" % (beat_num_final, beat_final_first))
                    #                       rosabeats.d_print("segment starts sample %d and ends sample %d" % (seg_first, seg_last))
                    except:
                        rosabeats.d_print(
                            "warning: beat %d does not exist" % beat_num_final
                        )
                        continue

                    # see if the final beat in bar starts inside the segment boundaries
                    if beat_final_first >= seg_first and beat_final_first <= seg_last:
                        # last beat starts in segment
                        #                       rosabeats.d_print(" BAR %d is in segment %d" % (bar_num, idx))
                        seg["bars"].append(bar_num)

                        # alternatively, bar_beat_First = eslf.beat_slices[beat_num_final][0]
                        # and then check that that is <= segmente, meaning last beat of bar STARTS inside segment

        self.save_features()

    def divide_bars(self):
        rosabeats.d_print("warning: divide_bars() no longer does anything")

    def set_beats_output_file(self, beatsfile):
        self.beats_output_file = beatsfile

    def set_default_beats_output_file(self):
        basename = os.path.basename(self.sourcefile)
        stub, ext = os.path.splitext(basename)
        self.set_beats_output_file(stub + "_beats.br")

    def start_writing_beats_output(self):
        if self.beats_output_file == None:
            self.set_default_beats_output_file()

        self.beats_output = open(self.beats_output_file, "w")
        self.beats_output.write("file %s\n" % self.sourcefile)
        self.beats_output.write(
            "beats_bar %d %d\n" % (self.beatsperbar, self.firstfullbar)
        )

    def shutdown(self):
        if self.output_play:
            self.stream.close()
        if self.output_save:
            self.save_remix()
        if self.output_beats:
            self.beats_output.close()

    def write_out(self, text):
        if self.beats_output == None:
            self.start_writing_beats_output()

        self.beats_output.write("%s\n" % text)

    def play_beat(self, b, silent=False, divisor=1):
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
            try:
                # try copying the beat data into the existing remix buffer
                self.remix[
                    0,
                    self.remix_index : self.remix_index + len(self.data[0][first:last]),
                ] += self.data[0][first:last]
                self.remix[
                    1,
                    self.remix_index : self.remix_index + len(self.data[1][first:last]),
                ] += self.data[1][first:last]
            except ValueError:
                # if it fails, extend the buffer and try again
                self.extend_remix()
                self.remix[
                    0,
                    self.remix_index : self.remix_index + len(self.data[0][first:last]),
                ] += self.data[0][first:last]
                self.remix[
                    1,
                    self.remix_index : self.remix_index + len(self.data[1][first:last]),
                ] += self.data[1][first:last]

            self.remix_index += len(self.data[0][first:last])

        if self.output_beats:
            if divisor > 1:
                self.write_out("beat_div %d %d 1" % (b, divisor))
            else:
                self.write_out("beats %d" % b)

    def play_beats(self, beats):
        for beat in beats:
            self.play_beat(beat)
        print(flush=True)

    def play_bars(self, bars, reverse=False):
        for bar in bars:
            self.play_bar(bar, reverse=reverse)

    def rest(self, beats):
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

    def play_bar(self, m, reverse=False, silent=False):
        if self.beatsperbar is None or self.beat_slices is None:
            raise Exception("must track beats before you can play bar")

        if self.output_beats:
            self.write_out("# bar %d" % m)

        if not silent:
            print("[%d]" % m, end="", flush=True)

        first_beat = int(m * self.beatsperbar) + self.firstfullbar
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
