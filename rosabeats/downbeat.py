"""
Downbeat detection using Dynamic Bayesian Network approach.

This module implements downbeat detection inspired by madmom's DBNDownBeatTrackingProcessor,
but using pure Python/numpy without Cython dependencies. It uses librosa for audio features
and a simple HMM with Viterbi decoding for beat/downbeat inference.

Based on the approach described in:
- Böck, Krebs, Widmer: "A Multi-Model Approach to Beat Tracking Considering Heterogeneous Music Styles" (2014)
- Krebs, Böck, Widmer: "An Efficient State Space Model for Joint Tempo and Meter Tracking" (2015)
"""

import numpy as np
from collections.abc import MutableSequence


class TransitionModel:
    """Sparse transition model for HMM.

    Stores transitions in compressed sparse row (CSR) format for efficient access.
    """

    def __init__(self, states, pointers, probabilities):
        """
        Args:
            states: Array of destination states for each transition
            pointers: Array of pointers into states array for each source state
            probabilities: Array of transition probabilities (log domain)
        """
        self.states = np.asarray(states, dtype=np.int32)
        self.pointers = np.asarray(pointers, dtype=np.int32)
        self.log_probabilities = np.asarray(probabilities, dtype=np.float64)
        self.num_states = len(pointers) - 1

    @classmethod
    def from_dense(cls, matrix):
        """Create TransitionModel from dense probability matrix.

        Args:
            matrix: Dense transition matrix of shape (num_states, num_states)
                    where matrix[i, j] = P(state_j | state_i)
        """
        num_states = matrix.shape[0]
        states = []
        pointers = [0]
        probabilities = []

        for i in range(num_states):
            for j in range(num_states):
                if matrix[i, j] > 0:
                    states.append(j)
                    probabilities.append(np.log(matrix[i, j]))
            pointers.append(len(states))

        return cls(states, pointers, probabilities)


class BarStateSpace:
    """State space for bar-aware beat tracking.

    Each state represents a position within a bar at a specific tempo.
    States are indexed as: state = tempo_idx * positions_per_bar + position

    This models beats within bars, where position 0 is the downbeat.
    """

    def __init__(self, beats_per_bar, min_bpm=55, max_bpm=215, num_tempi=60,
                 observation_lambda=16):
        """
        Args:
            beats_per_bar: Number of beats per bar (e.g., 4 for 4/4 time)
            min_bpm: Minimum tempo in BPM
            max_bpm: Maximum tempo in BPM
            num_tempi: Number of tempo bins
            observation_lambda: Subdivisions per beat for finer resolution
        """
        self.beats_per_bar = beats_per_bar
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.num_tempi = num_tempi
        self.observation_lambda = observation_lambda

        # Positions within a bar (subdivided beats)
        self.positions_per_beat = observation_lambda
        self.positions_per_bar = beats_per_bar * observation_lambda

        # Total number of states
        self.num_states = num_tempi * self.positions_per_bar

        # Tempo values for each tempo bin (in BPM)
        self.tempi = np.linspace(min_bpm, max_bpm, num_tempi)

        # Frames per beat for each tempo (at 100 fps)
        self.fps = 100
        self.frames_per_beat = 60.0 * self.fps / self.tempi

    def state_to_position(self, state):
        """Get bar position (0 to positions_per_bar-1) from state index."""
        return state % self.positions_per_bar

    def state_to_tempo_idx(self, state):
        """Get tempo index from state index."""
        return state // self.positions_per_bar

    def state_to_beat_in_bar(self, state):
        """Get beat number within bar (0 = downbeat)."""
        position = self.state_to_position(state)
        return position // self.positions_per_beat

    def is_downbeat_state(self, state):
        """Check if state represents a downbeat (first beat of bar)."""
        return self.state_to_beat_in_bar(state) == 0

    def is_beat_state(self, state):
        """Check if state represents any beat (not just downbeat)."""
        position = self.state_to_position(state)
        return position % self.positions_per_beat == 0


class BarTransitionModel(TransitionModel):
    """Transition model for bar-aware beat tracking.

    Models transitions between states, allowing tempo changes only at beat
    boundaries with exponential probability decay for larger tempo jumps.
    """

    def __init__(self, state_space, transition_lambda=100):
        """
        Args:
            state_space: BarStateSpace instance
            transition_lambda: Controls tempo change probability (higher = more stable)
        """
        self.state_space = state_space
        self.transition_lambda = transition_lambda

        # Build transition matrix
        states, pointers, probs = self._build_transitions()
        super().__init__(states, pointers, probs)

    def _build_transitions(self):
        """Build sparse transition matrix."""
        ss = self.state_space
        states = []
        pointers = [0]
        log_probs = []

        # Precompute tempo transition probabilities
        tempo_trans = self._tempo_transition_probs()

        for src_state in range(ss.num_states):
            src_pos = ss.state_to_position(src_state)
            src_tempo = ss.state_to_tempo_idx(src_state)

            # Next position (wrap around at bar boundary)
            next_pos = (src_pos + 1) % ss.positions_per_bar

            # At beat boundaries, allow tempo changes
            if next_pos % ss.positions_per_beat == 0:
                # Transition to same position in different tempo states
                for dst_tempo in range(ss.num_tempi):
                    prob = tempo_trans[src_tempo, dst_tempo]
                    if prob > 1e-10:
                        dst_state = dst_tempo * ss.positions_per_bar + next_pos
                        states.append(dst_state)
                        log_probs.append(np.log(prob))
            else:
                # Within beat, must stay at same tempo
                dst_state = src_tempo * ss.positions_per_bar + next_pos
                states.append(dst_state)
                log_probs.append(0.0)  # log(1)

            pointers.append(len(states))

        return states, pointers, log_probs

    def _tempo_transition_probs(self):
        """Compute tempo transition probability matrix."""
        n = self.state_space.num_tempi
        probs = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                # Exponential decay based on tempo difference
                diff = abs(i - j)
                probs[i, j] = np.exp(-self.transition_lambda * diff / n)

        # Normalize rows
        probs /= probs.sum(axis=1, keepdims=True)
        return probs


class DownbeatObservationModel:
    """Observation model for downbeat tracking.

    Maps onset strength observations to state probabilities, giving higher
    probability to beat states (especially downbeats) when onset strength is high.
    """

    def __init__(self, state_space, downbeat_weight=1.5):
        """
        Args:
            state_space: BarStateSpace instance
            downbeat_weight: Extra weight for downbeat observations
        """
        self.state_space = state_space
        self.downbeat_weight = downbeat_weight

    def log_densities(self, observation):
        """Compute log observation densities for all states.

        Args:
            observation: Tuple of (beat_activation, downbeat_activation) or single value

        Returns:
            Array of log probabilities for each state
        """
        ss = self.state_space

        if isinstance(observation, (tuple, list)) and len(observation) == 2:
            beat_act, downbeat_act = observation
        else:
            # Single activation - use for both
            beat_act = observation
            downbeat_act = observation

        log_densities = np.full(ss.num_states, -10.0)  # Low probability for non-beat states

        for state in range(ss.num_states):
            pos = ss.state_to_position(state)

            if ss.is_downbeat_state(state):
                # Downbeat state - high probability if strong activation
                log_densities[state] = np.log(max(downbeat_act * self.downbeat_weight, 1e-10))
            elif ss.is_beat_state(state):
                # Beat state - moderate probability if activation present
                log_densities[state] = np.log(max(beat_act, 1e-10))
            else:
                # Non-beat state - low probability if any activation
                log_densities[state] = np.log(max(1 - beat_act, 1e-10))

        return log_densities


def viterbi(transition_model, observation_model, observations, initial_distribution=None):
    """Viterbi algorithm for finding most likely state sequence.

    Args:
        transition_model: TransitionModel instance
        observation_model: ObservationModel instance with log_densities method
        observations: Sequence of observations
        initial_distribution: Initial state probabilities (uniform if None)

    Returns:
        Array of most likely states for each observation
    """
    num_states = transition_model.num_states
    num_obs = len(observations)

    if num_obs == 0:
        return np.array([], dtype=np.int32)

    # Initialize
    if initial_distribution is None:
        log_init = np.full(num_states, -np.log(num_states))
    else:
        log_init = np.log(np.maximum(initial_distribution, 1e-10))

    # Viterbi tables
    viterbi_prob = np.full((num_obs, num_states), -np.inf)
    backpointer = np.zeros((num_obs, num_states), dtype=np.int32)

    # First observation
    obs_log_prob = observation_model.log_densities(observations[0])
    viterbi_prob[0] = log_init + obs_log_prob

    # Forward pass
    for t in range(1, num_obs):
        obs_log_prob = observation_model.log_densities(observations[t])

        for dst_state in range(num_states):
            best_prob = -np.inf
            best_src = 0

            # Check all possible source states (using sparse format)
            # We need to find states that can transition TO dst_state
            # For efficiency, we iterate differently
            pass

        # More efficient: iterate over source states
        for src_state in range(num_states):
            src_prob = viterbi_prob[t-1, src_state]
            if src_prob == -np.inf:
                continue

            # Get transitions from this state
            start = transition_model.pointers[src_state]
            end = transition_model.pointers[src_state + 1]

            for idx in range(start, end):
                dst_state = transition_model.states[idx]
                trans_prob = transition_model.log_probabilities[idx]

                prob = src_prob + trans_prob
                if prob > viterbi_prob[t, dst_state] - obs_log_prob[dst_state]:
                    viterbi_prob[t, dst_state] = prob + obs_log_prob[dst_state]
                    backpointer[t, dst_state] = src_state

    # Backtrack
    path = np.zeros(num_obs, dtype=np.int32)
    path[-1] = np.argmax(viterbi_prob[-1])

    for t in range(num_obs - 2, -1, -1):
        path[t] = backpointer[t + 1, path[t + 1]]

    return path


class DBNDownbeatTracker:
    """Downbeat tracker using Dynamic Bayesian Network approach.

    This is a simplified, pure-Python implementation inspired by madmom's
    DBNDownBeatTrackingProcessor. It uses librosa for audio features instead
    of pre-trained RNN models.
    """

    def __init__(self, beats_per_bar=4, min_bpm=55, max_bpm=215, num_tempi=60,
                 transition_lambda=100, observation_lambda=16):
        """
        Args:
            beats_per_bar: Number of beats per bar
            min_bpm: Minimum tempo
            max_bpm: Maximum tempo
            num_tempi: Number of tempo bins
            transition_lambda: Tempo stability (higher = more stable)
            observation_lambda: Beat subdivisions for state resolution
        """
        self.beats_per_bar = beats_per_bar
        self.state_space = BarStateSpace(
            beats_per_bar=beats_per_bar,
            min_bpm=min_bpm,
            max_bpm=max_bpm,
            num_tempi=num_tempi,
            observation_lambda=observation_lambda
        )
        self.transition_model = BarTransitionModel(
            self.state_space,
            transition_lambda=transition_lambda
        )
        self.observation_model = DownbeatObservationModel(self.state_space)

    def track(self, onset_envelope, beat_frames, sr=22050, hop_length=512):
        """Track downbeats given onset envelope and detected beats.

        Args:
            onset_envelope: Onset strength envelope from librosa
            beat_frames: Beat frame indices from librosa beat tracker
            sr: Sample rate
            hop_length: Hop length used for onset envelope

        Returns:
            int: Index of the first downbeat in beat_frames
        """
        if len(beat_frames) < self.beats_per_bar:
            return 0

        # Get onset strength at each beat
        beat_strengths = onset_envelope[np.minimum(beat_frames, len(onset_envelope) - 1)]

        # Normalize
        if beat_strengths.max() > 0:
            beat_strengths = beat_strengths / beat_strengths.max()

        # Create observations - use beat strengths directly
        # We'll process at beat resolution, not frame resolution
        observations = [(s, s) for s in beat_strengths]

        # Run Viterbi to find most likely state sequence
        path = viterbi(self.transition_model, self.observation_model, observations)

        # Find first downbeat in the path
        for i, state in enumerate(path):
            if self.state_space.is_downbeat_state(state):
                return i

        return 0


def detect_downbeat_dbn(audio_data, sr, beat_times, beats_per_bar=4):
    """Detect the first downbeat using DBN approach.

    This function provides a simple interface for downbeat detection.

    Args:
        audio_data: Audio time series (mono)
        sr: Sample rate
        beat_times: Beat times in seconds from librosa beat tracker
        beats_per_bar: Number of beats per bar

    Returns:
        int: Index of the first downbeat in beat_times array
    """
    import librosa

    if len(beat_times) < beats_per_bar:
        return 0

    # Compute onset envelope
    onset_env = librosa.onset.onset_strength(y=audio_data, sr=sr)

    # Convert beat times to frames
    beat_frames = librosa.time_to_frames(beat_times, sr=sr)

    # Create tracker and run
    tracker = DBNDownbeatTracker(beats_per_bar=beats_per_bar)
    downbeat_idx = tracker.track(onset_env, beat_frames, sr=sr)

    return downbeat_idx
