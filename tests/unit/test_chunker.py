"""Tests for document chunking."""

from kgraph.infrastructure.chunker import chunk_text


class TestChunkText:
    """Tests for the chunk_text function."""

    def test_empty_text_returns_no_chunks(self) -> None:
        result = chunk_text("", "test.md")
        assert result == []

    def test_whitespace_only_returns_no_chunks(self) -> None:
        result = chunk_text("   \n\n  ", "test.md")
        assert result == []

    def test_short_text_returns_single_chunk(self) -> None:
        text = "This is a short paragraph."
        result = chunk_text(text, "test.md")
        assert len(result) == 1
        assert result[0].text == text
        assert result[0].source_file == "test.md"
        assert result[0].chunk_index == 0
        assert result[0].total_chunks == 1

    def test_long_text_splits_into_multiple_chunks(self) -> None:
        # Create text that exceeds chunk size
        paragraphs = [f"Paragraph {i} with enough content. " * 50 for i in range(10)]
        text = "\n\n".join(paragraphs)
        result = chunk_text(text, "test.md", chunk_size=200, overlap=50)
        assert len(result) > 1

    def test_chunk_provenance_is_correct(self) -> None:
        text = "Hello world."
        result = chunk_text(text, "my-file.md")
        assert result[0].source_file == "my-file.md"
        assert result[0].source_reference == "my-file.md [chunk 1/1]"

    def test_total_chunks_is_set_correctly(self) -> None:
        paragraphs = [f"Paragraph {i}. " * 100 for i in range(5)]
        text = "\n\n".join(paragraphs)
        result = chunk_text(text, "test.md", chunk_size=100, overlap=20)
        for chunk in result:
            assert chunk.total_chunks == len(result)
