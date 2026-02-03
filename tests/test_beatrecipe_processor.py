"""Tests for beatrecipe_processor module."""

import pytest

from rosabeats.beatrecipe_processor import beatrecipe_processor


class TestBeatrecipeProcessorIlist:
    """Tests for ilist static method."""

    def test_ascending_range(self):
        """Should create list from ascending range tuple."""
        result = beatrecipe_processor.ilist((3, 7, 1))
        assert result == [3, 4, 5, 6, 7]

    def test_descending_range(self):
        """Should create list from descending range tuple."""
        result = beatrecipe_processor.ilist((7, 3, -1))
        assert result == [7, 6, 5, 4, 3]

    def test_single_element(self):
        """Should handle single element range."""
        result = beatrecipe_processor.ilist((5, 5, 1))
        assert result == [5]


class TestBeatrecipeProcessorParseFirstLast:
    """Tests for parse_first_last static method."""

    def test_single_number(self):
        """Should parse single number."""
        result = beatrecipe_processor.parse_first_last("5")
        assert result == (5, 5, 1)

    def test_ascending_range(self):
        """Should parse ascending range."""
        result = beatrecipe_processor.parse_first_last("3-7")
        assert result == (3, 7, 1)

    def test_descending_range(self):
        """Should parse descending range with negative step."""
        result = beatrecipe_processor.parse_first_last("7-3")
        assert result == (7, 3, -1)


class TestBeatrecipeProcessorPreprocess:
    """Tests for preprocess method."""

    @pytest.fixture
    def processor(self, tmp_path, sample_br_content):
        """Create a processor instance with a recipe file."""
        recipe_file = tmp_path / "test.br"
        recipe_file.write_text(sample_br_content)
        return beatrecipe_processor(str(recipe_file))

    def test_empty_line(self, processor):
        """Should return None for empty line."""
        result = processor.preprocess("")
        assert result is None

    def test_whitespace_only(self, processor):
        """Should return None for whitespace only."""
        result = processor.preprocess("   ")
        assert result is None

    def test_comment_line(self, processor):
        """Should return None for comment line."""
        result = processor.preprocess("# this is a comment")
        assert result is None

    def test_simple_command(self, processor):
        """Should return list with single command."""
        result = processor.preprocess("beats 0-7")
        assert result == ["beats 0-7"]

    def test_inline_comment_stripped(self, processor):
        """Should strip inline comments."""
        result = processor.preprocess("beats 0-7 # play intro")
        assert result == ["beats 0-7"]

    def test_semicolon_splits_commands(self, processor):
        """Should split commands on semicolons."""
        result = processor.preprocess("beats 0-3; beats 4-7")
        assert result == ["beats 0-3", "beats 4-7"]

    def test_multiple_semicolons(self, processor):
        """Should handle multiple semicolons."""
        result = processor.preprocess("a; b; c")
        assert result == ["a", "b", "c"]


class TestBeatrecipeProcessorMacros:
    """Tests for macro functionality."""

    @pytest.fixture
    def processor(self, tmp_path, sample_br_content):
        """Create a processor instance with a recipe file."""
        recipe_file = tmp_path / "test.br"
        recipe_file.write_text(sample_br_content)
        return beatrecipe_processor(str(recipe_file))

    def test_define_macro(self, processor):
        """Should define a macro."""
        processor.define_macro("test", "beats 0-7")
        assert processor.is_defined_macro("test")
        assert processor.macros["test"] == "beats 0-7"

    def test_is_defined_macro_false(self, processor):
        """Should return False for undefined macro."""
        assert not processor.is_defined_macro("undefined")

    def test_redefine_macro(self, processor):
        """Should allow redefining a macro."""
        processor.define_macro("test", "beats 0-7")
        processor.define_macro("test", "bars 0-3")
        assert processor.macros["test"] == "bars 0-3"


class TestBeatrecipeProcessorParseCommand:
    """Tests for parse_command method."""

    @pytest.fixture
    def processor(self, tmp_path, sample_br_content):
        """Create a processor instance with a recipe file."""
        recipe_file = tmp_path / "test.br"
        recipe_file.write_text(sample_br_content)
        p = beatrecipe_processor(str(recipe_file))
        p.interactive = False
        return p

    def test_parse_beats_command(self, processor):
        """Should parse beats command."""
        verb, args = processor.parse_command("beats 0-7")
        assert verb == "beats"
        assert args == ["0-7"]

    def test_parse_bars_command(self, processor):
        """Should parse bars command."""
        verb, args = processor.parse_command("bars 0-3")
        assert verb == "bars"
        assert args == ["0-3"]

    def test_parse_def_command(self, processor):
        """Should parse def command."""
        verb, args = processor.parse_command("def intro beats 0-7")
        assert verb == "def"
        assert args == ["intro", "beats", "0-7"]

    def test_parse_play_command(self, processor):
        """Should parse play command."""
        verb, args = processor.parse_command("play intro 2")
        assert verb == "play"
        assert args == ["intro", "2"]

    def test_parse_rest_command(self, processor):
        """Should parse rest command."""
        verb, args = processor.parse_command("rest 1.5")
        assert verb == "rest"
        assert args == ["1.5"]

    def test_parse_file_command(self, processor):
        """Should parse file command."""
        verb, args = processor.parse_command("file /path/to/audio.wav")
        assert verb == "file"
        assert args == ["/path/to/audio.wav"]

    def test_parse_beats_bar_command(self, processor):
        """Should parse beats_bar command."""
        verb, args = processor.parse_command("beats_bar 4 0")
        assert verb == "beats_bar"
        assert args == ["4", "0"]


class TestBeatrecipeProcessorInit:
    """Tests for processor initialization."""

    def test_init_with_recipe(self, tmp_path, sample_br_content):
        """Should initialize with recipe file."""
        recipe_file = tmp_path / "test.br"
        recipe_file.write_text(sample_br_content)
        p = beatrecipe_processor(str(recipe_file))
        assert p.macros is not None
        assert p.interactive is False

    def test_loads_macros_from_recipe(self, tmp_path, sample_br_content):
        """Should load macro definitions from recipe file."""
        recipe_file = tmp_path / "test.br"
        recipe_file.write_text(sample_br_content)
        p = beatrecipe_processor(str(recipe_file))
        # The sample_br_content defines 'intro', 'verse', 'chorus'
        assert p.is_defined_macro("intro")
        assert p.is_defined_macro("verse")
        assert p.is_defined_macro("chorus")
