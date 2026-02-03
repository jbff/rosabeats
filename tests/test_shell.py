"""Tests for rosabeats_shell module."""

import pytest
from io import StringIO
import sys

from rosabeats.rosabeats_shell import (
    parse_range,
    parse_int,
    parse_float,
    rosabeats_shell,
)


class TestParseRange:
    """Tests for parse_range function."""

    def test_single_number(self):
        """Should parse single number as single-element list."""
        result = parse_range("5")
        assert result == [5]

    def test_ascending_range(self):
        """Should parse ascending range correctly."""
        result = parse_range("3-7")
        assert result == [3, 4, 5, 6, 7]

    def test_descending_range(self):
        """Should parse descending range correctly."""
        result = parse_range("7-3")
        assert result == [7, 6, 5, 4, 3]

    def test_same_number_range(self):
        """Should handle range where start equals end."""
        result = parse_range("5-5")
        assert result == [5]

    def test_whitespace_handling(self):
        """Should handle leading/trailing whitespace."""
        result = parse_range("  3-5  ")
        assert result == [3, 4, 5]

    def test_empty_string(self):
        """Should return None for empty string."""
        result = parse_range("")
        assert result is None

    def test_invalid_format(self, capsys):
        """Should return None and print error for invalid format."""
        result = parse_range("abc")
        assert result is None
        captured = capsys.readouterr()
        assert "invalid range" in captured.out

    def test_negative_numbers(self):
        """Should handle negative numbers."""
        result = parse_range("-3-2")
        assert result == [-3, -2, -1, 0, 1, 2]


class TestParseInt:
    """Tests for parse_int function."""

    def test_valid_integer(self):
        """Should parse valid integer string."""
        assert parse_int("42") == 42

    def test_negative_integer(self):
        """Should parse negative integer."""
        assert parse_int("-5") == -5

    def test_whitespace(self):
        """Should handle whitespace."""
        assert parse_int("  10  ") == 10

    def test_invalid_integer(self, capsys):
        """Should return None for invalid integer."""
        result = parse_int("abc")
        assert result is None
        captured = capsys.readouterr()
        assert "must be an integer" in captured.out

    def test_float_string(self, capsys):
        """Should return None for float string."""
        result = parse_int("3.14")
        assert result is None

    def test_custom_name(self, capsys):
        """Should use custom name in error message."""
        parse_int("abc", "beat_count")
        captured = capsys.readouterr()
        assert "beat_count must be an integer" in captured.out


class TestParseFloat:
    """Tests for parse_float function."""

    def test_valid_float(self):
        """Should parse valid float string."""
        assert parse_float("3.14") == pytest.approx(3.14)

    def test_integer_as_float(self):
        """Should parse integer string as float."""
        assert parse_float("42") == 42.0

    def test_negative_float(self):
        """Should parse negative float."""
        assert parse_float("-2.5") == -2.5

    def test_whitespace(self):
        """Should handle whitespace."""
        assert parse_float("  1.5  ") == 1.5

    def test_invalid_float(self, capsys):
        """Should return None for invalid float."""
        result = parse_float("abc")
        assert result is None
        captured = capsys.readouterr()
        assert "must be a number" in captured.out


class TestRosabeatsShell:
    """Tests for rosabeats_shell class."""

    @pytest.fixture
    def shell(self):
        """Create a shell instance for testing."""
        s = rosabeats_shell()
        # Don't enable audio output for tests
        s.output_play = False
        s.output_save = False
        s.output_beats = False
        return s

    def test_init(self, shell):
        """Shell should initialize with empty macros."""
        assert shell.macros == {}

    def test_define_macro(self, shell):
        """Should define a macro."""
        shell.define_macro("test", "beats 0-7")
        assert "test" in shell.macros
        assert shell.macros["test"] == "beats 0-7"

    def test_redefine_macro(self, shell, capsys):
        """Should allow redefining a macro."""
        shell.define_macro("test", "beats 0-7")
        shell.define_macro("test", "bars 0-3")
        assert shell.macros["test"] == "bars 0-3"
        captured = capsys.readouterr()
        assert "redefining" in captured.out

    def test_do_def_basic(self, shell, capsys):
        """do_def should define a macro from command."""
        shell.do_def("intro beats 0-15")
        assert "intro" in shell.macros
        assert shell.macros["intro"] == "beats 0-15"

    def test_do_def_strips_comments(self, shell):
        """do_def should strip inline comments."""
        shell.do_def("intro beats 0-15  # this is the intro")
        assert shell.macros["intro"] == "beats 0-15"

    def test_do_def_missing_args(self, shell, capsys):
        """do_def should show usage if missing arguments."""
        shell.do_def("onlyname")
        captured = capsys.readouterr()
        assert "usage:" in captured.out

    def test_do_ls_empty(self, shell, capsys):
        """do_ls should show message when no macros defined."""
        shell.do_ls("")
        captured = capsys.readouterr()
        assert "no macros defined" in captured.out

    def test_do_ls_with_macros(self, shell, capsys):
        """do_ls should list macro names."""
        shell.define_macro("intro", "beats 0-7")
        shell.define_macro("verse", "bars 0-3")
        shell.do_ls("")
        captured = capsys.readouterr()
        assert "intro" in captured.out
        assert "verse" in captured.out

    def test_do_lsdef_shows_definitions(self, shell, capsys):
        """do_lsdef should show macro names and definitions."""
        shell.define_macro("intro", "beats 0-7")
        shell.do_lsdef("")
        captured = capsys.readouterr()
        assert "intro" in captured.out
        assert "beats 0-7" in captured.out

    def test_do_file_sets_sourcefile(self, shell, temp_audio_file):
        """do_file should set the source file."""
        shell.do_file(temp_audio_file)
        assert shell.sourcefile is not None
        assert temp_audio_file in shell.sourcefile

    def test_do_file_missing_arg(self, shell, capsys):
        """do_file should show usage if no argument."""
        shell.do_file("")
        captured = capsys.readouterr()
        assert "usage:" in captured.out

    def test_do_beats_bar_missing_file(self, shell, capsys):
        """do_beats_bar should error if no file loaded."""
        shell.do_beats_bar("4 0")
        captured = capsys.readouterr()
        assert "load a file first" in captured.out

    def test_do_quit_returns_true(self, shell):
        """do_quit should return True to exit cmdloop."""
        # Mock shutdown to avoid errors
        shell.shutdown = lambda: None
        result = shell.do_quit("")
        assert result is True

    def test_default_unknown_command(self, shell, capsys):
        """default should print error for unknown command."""
        shell.default("unknowncommand")
        captured = capsys.readouterr()
        assert "unknown command or macro" in captured.out

    def test_default_plays_macro(self, shell, capsys):
        """default should play a macro if name matches."""
        shell.define_macro("test", "ls")  # ls is a safe command
        shell.default("test")
        captured = capsys.readouterr()
        # Should attempt to play the macro
        assert "test" in captured.out

    def test_emptyline_does_nothing(self, shell, capsys):
        """emptyline should not produce output or execute anything."""
        shell.emptyline()
        captured = capsys.readouterr()
        assert captured.out == ""


class TestShellLoadRecipeFile:
    """Tests for load_recipe_file functionality."""

    @pytest.fixture
    def shell(self):
        """Create a shell instance for testing."""
        s = rosabeats_shell()
        s.output_play = False
        s.output_save = False
        s.output_beats = False
        return s

    def test_load_recipe_file_defines_macros(self, shell, tmp_path, sample_bri_content):
        """load_recipe_file should define macros from file."""
        filepath = tmp_path / "test.bri"
        filepath.write_text(sample_bri_content)

        # Mock setfile to avoid actual file loading
        shell.setfile = lambda x: setattr(shell, 'sourcefile', x)
        # Mock track_beats
        shell.track_beats = lambda **kwargs: None
        shell.total_beats = 100
        shell.total_bars = 24
        shell.beatsperbar = 4
        shell.downbeat = 0
        shell.init_outputs = lambda: None

        shell.load_recipe_file(str(filepath))

        # Check that macros were defined
        assert "A" in shell.macros
        assert "B" in shell.macros
        assert "A2" in shell.macros
        assert "A_beats" in shell.macros

    def test_load_recipe_file_strips_comments(self, shell, tmp_path):
        """load_recipe_file should handle inline comments in defs."""
        content = """def test beats 0-7	# inline comment
"""
        filepath = tmp_path / "test.br"
        filepath.write_text(content)

        shell.load_recipe_file(str(filepath))

        assert "test" in shell.macros
        assert shell.macros["test"] == "beats 0-7"

    def test_load_recipe_file_not_found(self, shell, capsys):
        """load_recipe_file should handle missing file gracefully."""
        result = shell.load_recipe_file("/nonexistent/path.bri")
        assert result is False
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_load_recipe_file_skips_comments(self, shell, tmp_path):
        """load_recipe_file should skip comment lines."""
        content = """# This is a comment
def test beats 0-7
# Another comment
"""
        filepath = tmp_path / "test.br"
        filepath.write_text(content)

        shell.load_recipe_file(str(filepath))

        assert "test" in shell.macros
        assert len(shell.macros) == 1  # Only one macro defined
