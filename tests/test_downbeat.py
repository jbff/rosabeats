"""Tests for downbeat detection module."""

import pytest
import numpy as np

from rosabeats.downbeat import (
    compute_beat_features,
    score_offset,
    detect_downbeat,
    detect_downbeat_dbn,
)


class TestComputeBeatFeatures:
    """Tests for compute_beat_features function."""

    def test_empty_beat_times(self, mono_audio, sample_rate):
        """Should return empty dict for empty beat times."""
        features = compute_beat_features(mono_audio, sample_rate, np.array([]))
        assert features == {}

    def test_returns_expected_features(self, synthetic_audio_with_beats):
        """Should return dict with expected feature keys."""
        audio, sr = synthetic_audio_with_beats
        beat_times = np.arange(0, 10, 0.5)  # 120 BPM

        features = compute_beat_features(audio, sr, beat_times)

        assert 'onset_strength' in features
        assert 'low_freq_energy' in features
        assert 'mid_freq_energy' in features
        assert 'spectral_flux' in features
        assert 'low_mid_ratio' in features

    def test_feature_array_lengths(self, synthetic_audio_with_beats):
        """Feature arrays should have same length as beat_times."""
        audio, sr = synthetic_audio_with_beats
        beat_times = np.arange(0, 10, 0.5)
        n_beats = len(beat_times)

        features = compute_beat_features(audio, sr, beat_times)

        for key, values in features.items():
            assert len(values) == n_beats, f"{key} has wrong length"

    def test_features_are_normalized(self, synthetic_audio_with_beats):
        """Features should be normalized to 0-1 range."""
        audio, sr = synthetic_audio_with_beats
        beat_times = np.arange(0, 10, 0.5)

        features = compute_beat_features(audio, sr, beat_times)

        for key in ['onset_strength', 'low_freq_energy', 'mid_freq_energy', 'spectral_flux']:
            assert features[key].min() >= 0, f"{key} min should be >= 0"
            assert features[key].max() <= 1, f"{key} max should be <= 1"


class TestScoreOffset:
    """Tests for score_offset function."""

    def test_returns_float(self):
        """Should return a float score."""
        features = {
            'onset_strength': np.array([1.0, 0.5, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5]),
            'low_freq_energy': np.array([1.0, 0.2, 0.2, 0.2, 1.0, 0.2, 0.2, 0.2]),
            'low_mid_ratio': np.array([1.0, 0.3, 0.3, 0.3, 1.0, 0.3, 0.3, 0.3]),
            'spectral_flux': np.array([0.8, 0.4, 0.4, 0.4, 0.8, 0.4, 0.4, 0.4]),
        }

        score = score_offset(features, offset=0, beats_per_bar=4)
        assert isinstance(score, float)

    def test_correct_offset_scores_higher(self):
        """Offset 0 should score higher when downbeats have stronger features."""
        # Simulate features where beat 0, 4, 8 have strong low freq (downbeats)
        features = {
            'onset_strength': np.array([1.0, 0.3, 0.3, 0.3, 1.0, 0.3, 0.3, 0.3, 1.0, 0.3, 0.3, 0.3]),
            'low_freq_energy': np.array([1.0, 0.1, 0.1, 0.1, 1.0, 0.1, 0.1, 0.1, 1.0, 0.1, 0.1, 0.1]),
            'low_mid_ratio': np.array([1.0, 0.2, 0.2, 0.2, 1.0, 0.2, 0.2, 0.2, 1.0, 0.2, 0.2, 0.2]),
            'spectral_flux': np.array([0.8, 0.3, 0.3, 0.3, 0.8, 0.3, 0.3, 0.3, 0.8, 0.3, 0.3, 0.3]),
        }

        score_0 = score_offset(features, offset=0, beats_per_bar=4)
        score_1 = score_offset(features, offset=1, beats_per_bar=4)
        score_2 = score_offset(features, offset=2, beats_per_bar=4)
        score_3 = score_offset(features, offset=3, beats_per_bar=4)

        assert score_0 > score_1, "Offset 0 should score higher than offset 1"
        assert score_0 > score_2, "Offset 0 should score higher than offset 2"
        assert score_0 > score_3, "Offset 0 should score higher than offset 3"

    def test_too_few_beats(self):
        """Should return 0 if fewer beats than beats_per_bar."""
        features = {
            'onset_strength': np.array([1.0, 0.5]),
            'low_freq_energy': np.array([1.0, 0.5]),
            'low_mid_ratio': np.array([1.0, 0.5]),
            'spectral_flux': np.array([1.0, 0.5]),
        }

        score = score_offset(features, offset=0, beats_per_bar=4)
        assert score == 0.0


class TestDetectDownbeat:
    """Tests for detect_downbeat function."""

    def test_returns_valid_offset(self, synthetic_audio_with_beats):
        """Should return an integer offset within valid range."""
        audio, sr = synthetic_audio_with_beats
        beat_times = np.arange(0, 10, 0.5)
        beats_per_bar = 4

        result = detect_downbeat(audio, sr, beat_times, beats_per_bar)

        assert isinstance(result, (int, np.integer))
        assert 0 <= result < beats_per_bar

    def test_few_beats_returns_zero(self, mono_audio, sample_rate):
        """Should return 0 when there are very few beats."""
        beat_times = np.array([0.0, 0.5])  # Only 2 beats

        result = detect_downbeat(mono_audio, sample_rate, beat_times, beats_per_bar=4)

        assert result == 0

    def test_detects_correct_downbeat_synthetic(self, synthetic_audio_with_beats):
        """Should detect offset 0 for synthetic audio with kicks on downbeats."""
        audio, sr = synthetic_audio_with_beats
        beat_times = np.arange(0, 10, 0.5)

        result = detect_downbeat(audio, sr, beat_times, beats_per_bar=4)

        # The synthetic audio has kicks on beat 0, 4, 8, etc. so offset should be 0
        assert result == 0, f"Expected offset 0 but got {result}"


class TestDetectDownbeatDbn:
    """Tests for detect_downbeat_dbn (alias function)."""

    def test_is_alias_for_detect_downbeat(self, synthetic_audio_with_beats):
        """detect_downbeat_dbn should produce same results as detect_downbeat."""
        audio, sr = synthetic_audio_with_beats
        beat_times = np.arange(0, 10, 0.5)

        result1 = detect_downbeat(audio, sr, beat_times, beats_per_bar=4)
        result2 = detect_downbeat_dbn(audio, sr, beat_times, beats_per_bar=4)

        assert result1 == result2
