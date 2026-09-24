from app.core.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("", max_chars=100) == []


def test_whitespace_only_text_returns_no_chunks():
    assert chunk_text("   \n\n   ", max_chars=100) == []


def test_short_text_fits_in_a_single_chunk():
    text = "Primeiro paragrafo.\n\nSegundo paragrafo."

    result = chunk_text(text, max_chars=1000)

    assert result == ["Primeiro paragrafo.\n\nSegundo paragrafo."]


def test_paragraphs_are_greedily_packed_without_exceeding_max_chars():
    text = "AAAAAAAAAA\n\nBBBBBBBBBB\n\nCCCCCCCCCC"

    result = chunk_text(text, max_chars=25)

    assert result == ["AAAAAAAAAA\n\nBBBBBBBBBB", "CCCCCCCCCC"]
    assert all(len(chunk) <= 25 for chunk in result)


def test_a_paragraph_longer_than_max_chars_is_hard_split():
    text = "A" * 30

    result = chunk_text(text, max_chars=10)

    assert result == ["A" * 10, "A" * 10, "A" * 10]


def test_no_chunk_is_ever_empty():
    text = "AAAAAAAAAA\n\n\n\nBBBBBBBBBB"

    result = chunk_text(text, max_chars=1000)

    assert all(chunk.strip() for chunk in result)
