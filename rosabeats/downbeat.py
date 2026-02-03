"""
Downbeat detection for beat-tracked audio.

This module finds the first downbeat (beat 1 of bar 1) given beat times from
a beat tracker. It uses spectral features that distinguish downbeats:
- Low-frequency energy (bass/kick drum often hits on downbeats)
- Onset strength patterns
- Spectral contrast
"""

import numpy as np


def compute_beat_features(audio_data, sr, beat_times):
    """Compute features at each beat position for downbeat detection.

    Args:
        audio_data: Mono audio time series
        sr: Sample rate
        beat_times: Beat times in seconds

    Returns:
        dict with feature arrays, each of shape (num_beats,)
    """
    import librosa

    n_beats = len(beat_times)
    if n_beats == 0:
        return {}

    # Convert beat times to samples
    beat_samples = librosa.time_to_samples(beat_times, sr=sr)

    # Compute spectrograms
    # Standard spectrogram for onset strength
    hop_length = 512
    S = np.abs(librosa.stft(audio_data, hop_length=hop_length))

    # Mel spectrogram for low-frequency analysis
    mel_S = librosa.feature.melspectrogram(S=S**2, sr=sr, n_mels=128)

    # Low frequency energy (roughly 20-200 Hz, first ~10 mel bands)
    low_freq_energy = np.sum(mel_S[:10, :], axis=0)

    # Mid frequency energy (roughly 200-2000 Hz)
    mid_freq_energy = np.sum(mel_S[10:60, :], axis=0)

    # Onset strength
    onset_env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S, ref=np.max), sr=sr)

    # Spectral flux (change in spectrum)
    spectral_flux = np.sqrt(np.sum(np.diff(S, axis=1)**2, axis=0))
    spectral_flux = np.concatenate([[0], spectral_flux])

    # Convert beat samples to frames
    beat_frames = librosa.samples_to_frames(beat_samples, hop_length=hop_length)
    beat_frames = np.minimum(beat_frames, len(onset_env) - 1)

    # Extract features at each beat
    features = {
        'onset_strength': onset_env[beat_frames],
        'low_freq_energy': low_freq_energy[beat_frames],
        'mid_freq_energy': mid_freq_energy[beat_frames],
        'spectral_flux': spectral_flux[np.minimum(beat_frames, len(spectral_flux) - 1)],
    }

    # Normalize each feature
    for key in features:
        f = features[key]
        if f.max() > f.min():
            features[key] = (f - f.min()) / (f.max() - f.min())
        else:
            features[key] = np.zeros_like(f)

    # Compute low-to-mid ratio (high on kick drums)
    low = features['low_freq_energy']
    mid = features['mid_freq_energy']
    # Avoid division by zero
    features['low_mid_ratio'] = low / (mid + 0.1)
    if features['low_mid_ratio'].max() > 0:
        features['low_mid_ratio'] /= features['low_mid_ratio'].max()

    return features


def score_offset(features, offset, beats_per_bar, weights=None):
    """Score a particular beat offset for being the downbeat.

    Args:
        features: Dict of feature arrays from compute_beat_features
        offset: Beat offset to test (0 to beats_per_bar-1)
        beats_per_bar: Number of beats per bar
        weights: Optional dict of feature weights

    Returns:
        float: Score for this offset (higher = more likely downbeat)
    """
    if weights is None:
        # Default weights emphasizing low frequency (bass drum)
        weights = {
            'onset_strength': 1.0,
            'low_freq_energy': 2.0,
            'low_mid_ratio': 1.5,
            'spectral_flux': 0.5,
        }

    n_beats = len(features['onset_strength'])
    if n_beats < beats_per_bar:
        return 0.0

    # Get indices of would-be downbeats with this offset
    downbeat_indices = np.arange(offset, n_beats, beats_per_bar)

    if len(downbeat_indices) == 0:
        return 0.0

    # Weight earlier downbeats more (they're more reliable, less affected by
    # song structure changes like drops/breakdowns)
    position_weights = np.exp(-0.02 * np.arange(len(downbeat_indices)))

    # Compute weighted score for each feature
    total_score = 0.0
    for feature_name, feature_weight in weights.items():
        if feature_name not in features:
            continue

        feature_values = features[feature_name][downbeat_indices]

        # Also compute contrast with non-downbeat positions
        non_downbeat_mask = np.ones(n_beats, dtype=bool)
        non_downbeat_mask[downbeat_indices] = False

        if non_downbeat_mask.any():
            non_downbeat_mean = features[feature_name][non_downbeat_mask].mean()
        else:
            non_downbeat_mean = 0

        # Score = weighted sum of (downbeat values - non-downbeat mean)
        contrast = feature_values - non_downbeat_mean
        feature_score = np.sum(contrast * position_weights) / position_weights.sum()

        total_score += feature_weight * feature_score

    return total_score


def detect_downbeat(audio_data, sr, beat_times, beats_per_bar=4, debug=False):
    """Detect the first downbeat given audio and beat times.

    This finds which beat offset (0 to beats_per_bar-1) best aligns with
    musical downbeats based on spectral features.

    Args:
        audio_data: Mono audio time series
        sr: Sample rate
        beat_times: Beat times in seconds from beat tracker
        beats_per_bar: Number of beats per bar
        debug: Print debug information

    Returns:
        int: Index of the first downbeat in beat_times array
    """
    n_beats = len(beat_times)

    if n_beats < beats_per_bar:
        return 0

    # Compute features at each beat
    features = compute_beat_features(audio_data, sr, beat_times)

    if not features:
        return 0

    # Score each possible offset
    best_offset = 0
    best_score = -np.inf

    for offset in range(beats_per_bar):
        score = score_offset(features, offset, beats_per_bar)

        if debug:
            print(f"  Offset {offset}: score = {score:.4f}")

        if score > best_score:
            best_score = score
            best_offset = offset

    if debug:
        print(f"  Best offset: {best_offset} (score = {best_score:.4f})")

    return best_offset


# Alias for compatibility
def detect_downbeat_dbn(audio_data, sr, beat_times, beats_per_bar=4):
    """Detect the first downbeat (alias for detect_downbeat).

    Args:
        audio_data: Mono audio time series
        sr: Sample rate
        beat_times: Beat times in seconds
        beats_per_bar: Number of beats per bar

    Returns:
        int: Index of the first downbeat
    """
    return detect_downbeat(audio_data, sr, beat_times, beats_per_bar)
