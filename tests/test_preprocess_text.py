"""Tests for deterministic financial-text preprocessing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.python.preprocess_text import (
    count_token_frequencies,
    load_collection,
    normalize_text,
    normalize_unicode,
    preprocess_collection,
    tokenize,
)


def make_collection() -> dict[str, object]:
    return {
        "collection_version": 1,
        "total_chunks": 2,
        "chunks": [
            {
                "chunk_id": "TEST_2024_10K_0001",
                "document_id": "TEST_2024_10K",
                "position": 1,
                "company": "Test Corporation",
                "ticker": "TEST",
                "fiscal_year": 2024,
                "document_type": "10-K",
                "filing_date": "2025-02-01",
                "fiscal_year_end": "2024-12-31",
                "source_url": "https://www.sec.gov/example-one",
                "paragraph_start_id": 1,
                "paragraph_end_id": 2,
                "text": "NVIDIA reported $97,858 and growth of 12.5%.",
            },
            {
                "chunk_id": "TEST_2024_10K_0002",
                "document_id": "TEST_2024_10K",
                "position": 2,
                "company": "Test Corporation",
                "ticker": "TEST",
                "fiscal_year": 2024,
                "document_type": "10-K",
                "filing_date": "2025-02-01",
                "fiscal_year_end": "2024-12-31",
                "source_url": "https://www.sec.gov/example-one",
                "paragraph_start_id": 2,
                "paragraph_end_id": 3,
                "text": "NVDA uses AI-powered systems year-over-year.",
            },
        ],
    }


def test_case_normalization_uses_casefold() -> None:
    assert normalize_text("NVIDIA nvidia Straße") == "nvidia nvidia strasse"


def test_unicode_normalization_uses_nfkc() -> None:
    assert normalize_unicode("ＮＶＩＤＩＡ") == "NVIDIA"
    assert normalize_text("NVIDIA’s AI‑powered platform") == "nvidia's ai-powered platform"


def test_whitespace_is_collapsed() -> None:
    assert normalize_text("  NVIDIA\n\t  revenue   grew ") == "nvidia revenue grew"


def test_financial_values_and_percentages_remain_whole() -> None:
    assert tokenize("Revenue was $97,858, up 12.5% from -$1,250.") == [
        "revenue",
        "was",
        "$97,858",
        "up",
        "12.5%",
        "from",
        "-$1,250",
    ]


def test_stock_tickers_and_ampersand_terms() -> None:
    assert tokenize("NVDA joined the S&P 500.") == ["nvda", "joined", "the", "s&p", "500"]


def test_hyphenated_words_remain_whole() -> None:
    assert tokenize("AI-powered year-over-year growth") == [
        "ai-powered",
        "year-over-year",
        "growth",
    ]


def test_possessive_expression_remains_whole() -> None:
    assert tokenize("NVIDIA's and NVIDIA’s platforms") == [
        "nvidia's",
        "and",
        "nvidia's",
        "platforms",
    ]


def test_tokenization_is_deterministic() -> None:
    text = "S&P 500 — NVIDIA's 12.5% year-over-year growth"
    assert tokenize(text) == tokenize(text) == tokenize(normalize_text(text), already_normalized=True)


def test_token_frequency_counting() -> None:
    frequencies = count_token_frequencies([["nvidia", "ai"], ["nvidia", "nvda"]])
    assert frequencies == {"nvidia": 2, "ai": 1, "nvda": 1}


def test_preprocessing_preserves_chunk_ids_and_metadata() -> None:
    preprocessed, vocabulary = preprocess_collection(make_collection())

    assert [chunk["chunk_id"] for chunk in preprocessed["chunks"]] == [
        "TEST_2024_10K_0001",
        "TEST_2024_10K_0002",
    ]
    assert all(chunk["ticker"] == "TEST" for chunk in preprocessed["chunks"])
    assert vocabulary["processed_chunks"] == 2
    assert vocabulary["token_frequencies"] == sorted(
        vocabulary["token_frequencies"], key=lambda item: item["token"]
    )


def test_duplicate_chunk_ids_are_rejected() -> None:
    collection = make_collection()
    collection["chunks"][1]["chunk_id"] = collection["chunks"][0]["chunk_id"]

    with pytest.raises(ValueError, match="duplicate chunk_id"):
        preprocess_collection(collection)


@pytest.mark.parametrize("contents", ["{invalid", "[]", '{"total_chunks": 0, "chunks": []}'])
def test_invalid_input_is_rejected(tmp_path: Path, contents: str) -> None:
    path = tmp_path / "collection.json"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError):
        load_collection(path)


def test_missing_input_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        load_collection(tmp_path / "missing.json")


def test_vocabulary_frequencies_match_record_token_counts() -> None:
    preprocessed, vocabulary = preprocess_collection(make_collection())
    total_from_records = sum(chunk["token_count"] for chunk in preprocessed["chunks"])
    total_from_vocabulary = sum(
        item["frequency"] for item in vocabulary["token_frequencies"]
    )

    assert vocabulary["total_token_occurrences"] == total_from_records
    assert total_from_vocabulary == total_from_records
    assert vocabulary["unique_tokens"] == len(vocabulary["token_frequencies"])
