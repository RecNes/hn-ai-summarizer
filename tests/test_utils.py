"""Unit tests for utility functions."""
from app.utils.keywords import extract_keywords, match_keywords, highlight_text


class TestExtractKeywords:
    """Test extract_keywords function."""

    def test_empty_text(self):
        """Empty text returns empty set."""
        assert extract_keywords("") == set()

    def test_stop_words_excluded(self):
        """Common stop words are filtered out."""
        result = extract_keywords("the and or but")
        assert result == set()

    def test_short_words_excluded(self):
        """Words with 2 or fewer characters excluded."""
        result = extract_keywords("a an in on at to by")
        assert result == set()

    def test_meaningful_words_extracted(self):
        """Meaningful words are extracted."""
        result = extract_keywords("python programming machine learning")
        assert "python" in result
        assert "programming" in result
        assert "machine" in result
        assert "learning" in result

    def test_case_insensitive(self):
        """Keywords are lowercased."""
        result = extract_keywords("Python AI ML")
        assert "python" in result
        assert "ai" not in result  # 2 chars
        assert "ml" not in result   # 2 chars

    def test_punctuation_removed(self):
        """Punctuation does not affect extraction."""
        result = extract_keywords("hello, world! testing...")
        assert "hello" in result
        assert "world" in result
        assert "testing" in result


class TestMatchKeywords:
    """Test match_keywords function."""

    def test_empty_text(self):
        """Empty text returns False."""
        assert match_keywords("", "ai,ml") is False

    def test_empty_keywords_list(self):
        """Empty keywords list returns False."""
        assert match_keywords("hello world", "") is False

    def test_match_found(self):
        """Match when keyword appears in text."""
        assert match_keywords("machine learning is great", "learning") is True

    def test_multiple_keywords_match(self):
        """Match with comma-separated keywords."""
        assert match_keywords("python programming", "java,python,ruby") is True

    def test_no_match(self):
        """No match when keyword is not in text."""
        assert match_keywords("hello world", "python") is False

    def test_case_insensitive_match(self):
        """Match is case insensitive."""
        assert match_keywords("Machine Learning", "machine") is True

    def test_keyword_partial_word_no_match(self):
        """No match for partial word unless full word matches."""
        text = "machine learning"
        assert match_keywords(text, "mach") is False
        assert match_keywords(text, "machine") is True


class TestHighlightText:
    """Test highlight_text function."""

    def test_empty_text(self):
        """Empty text returns as-is."""
        assert highlight_text("", "ai") == ""

    def test_empty_keywords(self):
        """Empty keywords returns original text."""
        assert highlight_text("hello world", "") == "hello world"

    def test_keyword_highlighted(self):
        """Keyword is wrapped in <mark> tag."""
        result = highlight_text("machine learning", "machine")
        assert "<mark>machine</mark>" in result
        assert "learning" in result

    def test_case_insensitive_highlight(self):
        """Highlight is case insensitive."""
        result = highlight_text("Machine Learning", "machine")
        assert "<mark>Machine</mark>" in result

    def test_multiple_keywords(self):
        """Multiple keywords are highlighted."""
        result = highlight_text("python and java", "python,java")
        assert "<mark>python</mark>" in result
        assert "<mark>java</mark>" in result
        assert "and" in result