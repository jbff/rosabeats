"""Tests for beat_explorer_cli module."""

import pytest
from unittest.mock import Mock, patch

from rosabeats.beat_explorer_cli import BeatExplorerCLI


class MockRosabeats:
    """Mock rosabeats instance for testing."""

    def __init__(
        self,
        total_beats: int = 32,
        beatsperbar: int = 4,
        downbeat: int = 0
    ):
        self.total_beats = total_beats
        self.beatsperbar = beatsperbar
        self.downbeat = downbeat
        self.total_bars = (total_beats - downbeat) // beatsperbar
        self.played_beats = []

    def play_beat(self, b: int, silent: bool = False) -> None:
        """Track which beats were played."""
        self.played_beats.append(b)


@pytest.fixture
def mock_rb():
    """Create a mock rosabeats instance."""
    return MockRosabeats(total_beats=32, beatsperbar=4, downbeat=0)


@pytest.fixture
def mock_rb_with_pickup():
    """Create a mock rosabeats instance with pickup beats."""
    return MockRosabeats(total_beats=34, beatsperbar=4, downbeat=2)


@pytest.fixture
def explorer(mock_rb):
    """Create a BeatExplorerCLI instance."""
    return BeatExplorerCLI(mock_rb)


@pytest.fixture
def explorer_with_pickup(mock_rb_with_pickup):
    """Create a BeatExplorerCLI instance with pickup beats."""
    return BeatExplorerCLI(mock_rb_with_pickup)


class TestBeatExplorerCLIInit:
    """Tests for BeatExplorerCLI initialization."""

    def test_init_sets_rb(self, mock_rb):
        """Should store rosabeats instance."""
        explorer = BeatExplorerCLI(mock_rb)
        assert explorer.rb is mock_rb

    def test_init_sets_current_beat_to_downbeat(self, mock_rb):
        """Should initialize current beat to downbeat."""
        explorer = BeatExplorerCLI(mock_rb)
        assert explorer.current_beat_index == 0

    def test_init_with_nonzero_downbeat(self, mock_rb_with_pickup):
        """Should initialize current beat to downbeat when nonzero."""
        explorer = BeatExplorerCLI(mock_rb_with_pickup)
        assert explorer.current_beat_index == 2


class TestBeatExplorerCLIProperties:
    """Tests for BeatExplorerCLI properties."""

    def test_total_beats(self, explorer, mock_rb):
        """total_beats should match rosabeats."""
        assert explorer.total_beats == mock_rb.total_beats

    def test_total_bars(self, explorer, mock_rb):
        """total_bars should match rosabeats."""
        assert explorer.total_bars == mock_rb.total_bars

    def test_beatsperbar(self, explorer, mock_rb):
        """beatsperbar should match rosabeats."""
        assert explorer.beatsperbar == mock_rb.beatsperbar

    def test_downbeat(self, explorer, mock_rb):
        """downbeat should match rosabeats."""
        assert explorer.downbeat == mock_rb.downbeat


class TestBeatExplorerCLICurrentBeat:
    """Tests for current_beat method."""

    def test_current_beat_returns_index(self, explorer):
        """current_beat should return current index."""
        assert explorer.current_beat() == 0

    def test_current_beat_after_navigation(self, explorer):
        """current_beat should reflect navigation."""
        explorer.goto_beat(10)
        assert explorer.current_beat() == 10


class TestBeatExplorerCLICurrentBar:
    """Tests for current_bar method."""

    def test_current_bar_at_start(self, explorer):
        """current_bar should be 0 when at beat 0 with downbeat 0."""
        assert explorer.current_bar() == 0

    def test_current_bar_in_second_bar(self, explorer):
        """current_bar should be 1 when in second bar."""
        explorer.goto_beat(4)
        assert explorer.current_bar() == 1

    def test_current_bar_before_downbeat(self, explorer_with_pickup):
        """current_bar should be None when before downbeat."""
        explorer_with_pickup.goto_beat(0)
        assert explorer_with_pickup.current_bar() is None

    def test_current_bar_at_downbeat(self, explorer_with_pickup):
        """current_bar should be 0 at downbeat."""
        explorer_with_pickup.goto_beat(2)
        assert explorer_with_pickup.current_bar() == 0


class TestBeatExplorerCLIGotoBeat:
    """Tests for goto_beat method."""

    def test_goto_beat_sets_position(self, explorer):
        """goto_beat should set current position."""
        explorer.goto_beat(15)
        assert explorer.current_beat() == 15

    def test_goto_beat_clamps_negative(self, explorer):
        """goto_beat should clamp negative values to 0."""
        explorer.goto_beat(-5)
        assert explorer.current_beat() == 0

    def test_goto_beat_clamps_over_max(self, explorer):
        """goto_beat should clamp values beyond total beats."""
        explorer.goto_beat(100)
        assert explorer.current_beat() == 31  # total_beats - 1


class TestBeatExplorerCLIGotoBar:
    """Tests for goto_bar method."""

    def test_goto_bar_sets_position(self, explorer):
        """goto_bar should set position to first beat of bar."""
        explorer.goto_bar(2)
        assert explorer.current_beat() == 8  # bar 2 * 4 beats/bar

    def test_goto_bar_with_downbeat(self, explorer_with_pickup):
        """goto_bar should account for downbeat offset."""
        explorer_with_pickup.goto_bar(1)
        # bar 1 * 4 + downbeat 2 = 6
        assert explorer_with_pickup.current_beat() == 6

    def test_goto_bar_clamps_negative(self, explorer):
        """goto_bar should clamp negative values to 0."""
        explorer.goto_bar(-1)
        assert explorer.current_beat() == 0

    def test_goto_bar_clamps_over_max(self, explorer):
        """goto_bar should clamp values beyond total bars."""
        explorer.goto_bar(100)
        # Should go to last valid bar (bar 7 = beat 28)
        assert explorer.current_beat() == 28


class TestBeatExplorerCLIFirstBeatOfCurrentBar:
    """Tests for first_beat_of_current_bar method."""

    def test_first_beat_at_bar_start(self, explorer):
        """Should return same beat when at bar start."""
        explorer.goto_beat(8)
        assert explorer.first_beat_of_current_bar() == 8

    def test_first_beat_mid_bar(self, explorer):
        """Should return bar start when mid-bar."""
        explorer.goto_beat(10)  # bar 2, beat 2
        assert explorer.first_beat_of_current_bar() == 8

    def test_first_beat_before_downbeat(self, explorer_with_pickup):
        """Should return 0 when before downbeat."""
        explorer_with_pickup.goto_beat(1)
        assert explorer_with_pickup.first_beat_of_current_bar() == 0


class TestBeatExplorerCLINextBeat:
    """Tests for next_beat method."""

    def test_next_beat_advances(self, explorer):
        """next_beat should advance position."""
        explorer.goto_beat(5)
        result = explorer.next_beat()
        assert result is True
        assert explorer.current_beat() == 6

    def test_next_beat_with_step(self, explorer):
        """next_beat should advance by step."""
        explorer.goto_beat(5)
        result = explorer.next_beat(3)
        assert result is True
        assert explorer.current_beat() == 8

    def test_next_beat_at_end(self, explorer):
        """next_beat should return False at end."""
        explorer.goto_beat(31)  # last beat
        result = explorer.next_beat()
        assert result is False
        assert explorer.current_beat() == 31

    def test_next_beat_clamps_at_end(self, explorer):
        """next_beat should clamp to last beat."""
        explorer.goto_beat(30)
        result = explorer.next_beat(5)
        assert result is False
        assert explorer.current_beat() == 31


class TestBeatExplorerCLIPrevBeat:
    """Tests for prev_beat method."""

    def test_prev_beat_goes_back(self, explorer):
        """prev_beat should go back."""
        explorer.goto_beat(5)
        result = explorer.prev_beat()
        assert result is True
        assert explorer.current_beat() == 4

    def test_prev_beat_with_step(self, explorer):
        """prev_beat should go back by step."""
        explorer.goto_beat(10)
        result = explorer.prev_beat(3)
        assert result is True
        assert explorer.current_beat() == 7

    def test_prev_beat_at_start(self, explorer):
        """prev_beat should return False at start."""
        explorer.goto_beat(0)
        result = explorer.prev_beat()
        assert result is False
        assert explorer.current_beat() == 0

    def test_prev_beat_clamps_at_start(self, explorer):
        """prev_beat should clamp to first beat."""
        explorer.goto_beat(2)
        result = explorer.prev_beat(5)
        assert result is False
        assert explorer.current_beat() == 0


class TestBeatExplorerCLINextBar:
    """Tests for next_bar method."""

    def test_next_bar_advances_by_beatsperbar(self, explorer):
        """next_bar should advance by beatsperbar."""
        explorer.goto_beat(4)
        result = explorer.next_bar()
        assert result is True
        assert explorer.current_beat() == 8

    def test_next_bar_at_end(self, explorer):
        """next_bar should return False near end."""
        explorer.goto_beat(28)  # last bar
        result = explorer.next_bar()
        assert result is False


class TestBeatExplorerCLIPrevBar:
    """Tests for prev_bar method."""

    def test_prev_bar_goes_back_by_beatsperbar(self, explorer):
        """prev_bar should go back by beatsperbar."""
        explorer.goto_beat(8)
        result = explorer.prev_bar()
        assert result is True
        assert explorer.current_beat() == 4

    def test_prev_bar_at_start(self, explorer):
        """prev_bar should return False at start."""
        explorer.goto_beat(0)
        result = explorer.prev_bar()
        assert result is False


class TestBeatExplorerCLIPlayCurrentBeat:
    """Tests for play_current_beat method."""

    def test_play_current_beat_calls_rb(self, explorer, mock_rb):
        """play_current_beat should call rb.play_beat."""
        explorer.goto_beat(5)
        explorer.play_current_beat(silent=True)
        assert 5 in mock_rb.played_beats


class TestBeatExplorerCLIPlayCurrentBar:
    """Tests for play_current_bar method."""

    def test_play_current_bar_plays_all_beats(self, explorer, mock_rb):
        """play_current_bar should play all beats in bar."""
        explorer.goto_beat(4)  # bar 1
        explorer.play_current_bar(silent=True)
        assert mock_rb.played_beats == [4, 5, 6, 7]

    def test_play_current_bar_at_partial_bar(self, mock_rb):
        """play_current_bar should handle partial bars at end."""
        # 33 beats with 4 per bar = bar 8 only has 1 beat
        mock_rb.total_beats = 33
        mock_rb.total_bars = 8
        explorer = BeatExplorerCLI(mock_rb)
        explorer.goto_beat(32)  # bar 8, only beat 32 exists
        explorer.play_current_bar(silent=True)
        assert mock_rb.played_beats == [32]


class TestBeatExplorerCLIWithRealRosabeats:
    """Integration tests using real rosabeats instance."""

    def test_with_real_rosabeats(self, temp_audio_file):
        """Should work with real rosabeats instance."""
        from rosabeats.rosabeats import rosabeats

        rb = rosabeats(temp_audio_file)
        rb.track_beats(beatsper=4, downbeat=0)

        explorer = BeatExplorerCLI(rb)

        assert explorer.total_beats == rb.total_beats
        assert explorer.total_bars == rb.total_bars

        # Test navigation
        explorer.goto_bar(1)
        assert explorer.current_beat() == 4

        explorer.next_beat()
        assert explorer.current_beat() == 5

        explorer.prev_bar()
        assert explorer.current_beat() == 1
