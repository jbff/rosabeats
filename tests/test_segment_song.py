"""Tests for segment_song module."""

import pytest

from rosabeats.segment_song import (
    get_segment_letter,
    generate_segment_names,
)


class TestGetSegmentLetter:
    """Tests for get_segment_letter function."""

    def test_single_letters(self):
        """Should return single letters for 0-25."""
        assert get_segment_letter(0) == "A"
        assert get_segment_letter(1) == "B"
        assert get_segment_letter(25) == "Z"

    def test_double_letters(self):
        """Should return double letters for 26+."""
        assert get_segment_letter(26) == "AA"
        assert get_segment_letter(27) == "AB"
        assert get_segment_letter(51) == "AZ"
        assert get_segment_letter(52) == "BA"


class TestGenerateSegmentNames:
    """Tests for generate_segment_names function."""

    def test_unique_clusters(self):
        """Should assign unique letters to unique clusters."""
        segments = [
            {'label': 0},
            {'label': 1},
            {'label': 2},
        ]

        names = generate_segment_names(segments)

        assert names == ["A", "B", "C"]

    def test_repeated_clusters_get_numbers(self):
        """Repeated clusters should get numeric suffixes."""
        segments = [
            {'label': 0},
            {'label': 1},
            {'label': 0},  # Second occurrence of cluster 0
            {'label': 1},  # Second occurrence of cluster 1
        ]

        names = generate_segment_names(segments)

        assert names == ["A", "B", "A2", "B2"]

    def test_multiple_repeats(self):
        """Multiple repeats should get incrementing numbers."""
        segments = [
            {'label': 0},
            {'label': 0},
            {'label': 0},
            {'label': 0},
        ]

        names = generate_segment_names(segments)

        assert names == ["A", "A2", "A3", "A4"]

    def test_complex_pattern(self):
        """Should handle complex patterns correctly."""
        # Simulating A B A C A B pattern
        segments = [
            {'label': 0},  # A
            {'label': 1},  # B
            {'label': 0},  # A2
            {'label': 2},  # C
            {'label': 0},  # A3
            {'label': 1},  # B2
        ]

        names = generate_segment_names(segments)

        assert names == ["A", "B", "A2", "C", "A3", "B2"]

    def test_empty_segments(self):
        """Should return empty list for empty input."""
        names = generate_segment_names([])
        assert names == []

    def test_single_segment(self):
        """Should handle single segment."""
        segments = [{'label': 0}]
        names = generate_segment_names(segments)
        assert names == ["A"]

    def test_many_unique_clusters(self):
        """Should handle many unique clusters."""
        # 30 unique clusters
        segments = [{'label': i} for i in range(30)]

        names = generate_segment_names(segments)

        assert len(names) == 30
        assert names[0] == "A"
        assert names[25] == "Z"
        assert names[26] == "AA"
        assert names[27] == "AB"

    def test_no_apostrophes_in_names(self):
        """Names should not contain apostrophes."""
        segments = [
            {'label': 0},
            {'label': 0},
            {'label': 0},
        ]

        names = generate_segment_names(segments)

        for name in names:
            assert "'" not in name, f"Name '{name}' contains apostrophe"
