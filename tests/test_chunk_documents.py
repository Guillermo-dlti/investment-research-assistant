"""Focused tests for paragraph-aware document chunking."""

from __future__ import annotations

import pytest

from src.python.chunk_documents import WORD_PATTERN, chunk_document


def make_document(paragraphs: list[str]) -> dict[str, object]:
    return {
        "document_id": "TEST_2025_10K",
        "company": "Test Corporation",
        "ticker": "TEST",
        "fiscal_year": 2025,
        "document_type": "10-K",
        "filing_date": "2025-02-26",
        "fiscal_year_end": "2025-01-26",
        "source_url": "https://example.test/filing.htm",
        "word_count": sum(len(WORD_PATTERN.findall(text)) for text in paragraphs),
        "character_count": sum(len(text) for text in paragraphs),
        "paragraphs": [
            {"paragraph_id": index, "text": text}
            for index, text in enumerate(paragraphs, start=1)
        ],
    }


def numbered_words(start: int, count: int, final: str = ".") -> str:
    words = [f"word{number}" for number in range(start, start + count)]
    words[-1] += final
    return " ".join(words)


def words(text: str) -> list[str]:
    return WORD_PATTERN.findall(text)


def test_short_document_fits_in_one_chunk() -> None:
    result = chunk_document(make_document(["A short financial paragraph."]), 250, 40)

    assert result["total_chunks"] == 1
    assert result["chunks"][0]["text"] == "A short financial paragraph."


def test_long_document_produces_multiple_nonempty_chunks() -> None:
    document = make_document([numbered_words(index * 70, 70) for index in range(5)])
    result = chunk_document(document, chunk_size=120, overlap=20)

    assert result["total_chunks"] > 1
    assert all(chunk["text"].strip() for chunk in result["chunks"])
    assert all(chunk["word_count"] <= 120 for chunk in result["chunks"])


def test_consecutive_chunks_have_exact_requested_overlap() -> None:
    document = make_document([numbered_words(0, 90), numbered_words(90, 90)])
    result = chunk_document(document, chunk_size=100, overlap=15)

    for previous, current in zip(result["chunks"], result["chunks"][1:]):
        assert words(previous["text"])[-15:] == words(current["text"])[:15]


def test_paragraph_longer_than_chunk_size_is_split() -> None:
    result = chunk_document(make_document([numbered_words(0, 275)]), 80, 10)

    assert result["total_chunks"] > 1
    assert max(chunk["word_count"] for chunk in result["chunks"]) <= 80
    assert all(chunk["paragraph_start_id"] == 1 for chunk in result["chunks"])


def test_metadata_and_paragraph_positions_are_preserved() -> None:
    result = chunk_document(make_document(["First paragraph.", "Second paragraph."]), 20, 2)
    chunk = result["chunks"][0]

    assert chunk["document_id"] == "TEST_2025_10K"
    assert chunk["company"] == "Test Corporation"
    assert chunk["ticker"] == "TEST"
    assert chunk["fiscal_year_end"] == "2025-01-26"
    assert chunk["paragraph_start_id"] == 1
    assert chunk["paragraph_end_id"] == 2


def test_chunk_ids_are_stable_and_sequential() -> None:
    document = make_document([numbered_words(0, 240)])

    first = chunk_document(document, 75, 10)
    second = chunk_document(document, 75, 10)

    assert [chunk["chunk_id"] for chunk in first["chunks"]] == [
        chunk["chunk_id"] for chunk in second["chunks"]
    ]
    assert first["chunks"][0]["chunk_id"] == "TEST_2025_10K_0001"


def test_no_empty_or_unnecessary_duplicate_chunks() -> None:
    result = chunk_document(make_document([numbered_words(0, 310)]), 90, 15)
    texts = [chunk["text"] for chunk in result["chunks"]]

    assert all(texts)
    assert len(texts) == len(set(texts))
    assert result["total_chunks"] == len(texts)


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (20, -1), (20, 20), (20, 21)],
)
def test_invalid_parameters_raise_clear_errors(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_document(make_document(["Valid text."]), chunk_size, overlap)
