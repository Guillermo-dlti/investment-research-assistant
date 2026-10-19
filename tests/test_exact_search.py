"""Tests for the bound exact matchers and SearchEngine phrase integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import investment_engine
from src.python.preprocess_text import preprocess_collection
from src.python.search_engine import SearchEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_VOCABULARY = PROJECT_ROOT / "data/metadata/vocabulary.json"
REAL_COLLECTION = PROJECT_ROOT / "data/processed/preprocessed_collection.json"
HAS_REAL_DATA = REAL_VOCABULARY.exists() and REAL_COLLECTION.exists()


def source_collection() -> dict[str, Any]:
    texts = [
        (
            "CHUNK_B",
            "DOC_B",
            "BETA",
            2025,
            "Café café and aaaaa.",
        ),
        (
            "CHUNK_A",
            "DOC_A",
            "ALFA",
            2024,
            "Paid AI and artificial intelligence. "
            "Artificial intelligence cost $97,858.",
        ),
        (
            "CHUNK_C",
            "DOC_C",
            "CHARLIE",
            2023,
            "Artificial intelligence supports revenue, growth.",
        ),
    ]
    chunks = []
    for position, (chunk_id, document_id, ticker, year, text) in enumerate(texts, 1):
        chunks.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "position": position,
                "company": f"{ticker} Corporation",
                "ticker": ticker,
                "fiscal_year": year,
                "document_type": "10-K",
                "filing_date": f"{year + 1}-02-01",
                "fiscal_year_end": f"{year}-12-31",
                "source_url": f"https://www.sec.gov/{chunk_id.lower()}",
                "paragraph_start_id": position,
                "paragraph_end_id": position,
                "text": text,
            }
        )
    return {"collection_version": 1, "total_chunks": len(chunks), "chunks": chunks}


@pytest.fixture
def engine(tmp_path: Path) -> SearchEngine:
    collection, vocabulary = preprocess_collection(source_collection())
    collection_path = tmp_path / "preprocessed_collection.json"
    vocabulary_path = tmp_path / "vocabulary.json"
    collection_path.write_text(json.dumps(collection), encoding="utf-8")
    vocabulary_path.write_text(json.dumps(vocabulary), encoding="utf-8")
    return SearchEngine(vocabulary_path, collection_path)


def comparable(results: list[dict[str, Any]]) -> list[tuple[str, int, list[int]]]:
    return [
        (result["chunk_id"], result["match_count"], result["match_byte_offsets"])
        for result in results
    ]


def test_kmp_bindings_import_and_execute() -> None:
    assert investment_engine.compute_lps("ababaca") == [0, 0, 1, 2, 3, 0, 1]
    assert investment_engine.kmp_search("revenue revenue", "revenue") == [0, 8]
    assert investment_engine.kmp_count("revenue revenue", "revenue") == 2


def test_z_bindings_import_and_execute() -> None:
    assert investment_engine.compute_z("abacaba") == [0, 0, 1, 0, 3, 0, 1]
    assert investment_engine.z_search("revenue revenue", "revenue") == [0, 8]
    assert investment_engine.z_count("revenue revenue", "revenue") == 2


def test_algorithms_are_equivalent() -> None:
    text = "artificial intelligence and artificial intelligence"
    assert investment_engine.kmp_search(text, "artificial intelligence") == (
        investment_engine.z_search(text, "artificial intelligence")
    )


def test_multiple_matches() -> None:
    assert investment_engine.kmp_search("nvda nvda nvda", "nvda") == [0, 5, 10]
    assert investment_engine.z_count("nvda nvda nvda", "nvda") == 3


def test_overlapping_matches() -> None:
    assert investment_engine.kmp_search("aaaaa", "aaa") == [0, 1, 2]
    assert investment_engine.z_search("aaaaa", "aaa") == [0, 1, 2]


def test_empty_patterns() -> None:
    assert investment_engine.kmp_search("revenue", "") == []
    assert investment_engine.kmp_count("revenue", "") == 0
    assert investment_engine.z_search("revenue", "") == []
    assert investment_engine.z_count("revenue", "") == 0


def test_utf8_uses_byte_offsets() -> None:
    assert investment_engine.kmp_search("café café", "é") == [3, 9]
    assert investment_engine.z_search("café café", "é") == [3, 9]


def test_embedded_null_characters_are_preserved() -> None:
    text = "a\0b\0a\0b"
    pattern = "a\0b"
    assert investment_engine.kmp_search(text, pattern) == [0, 4]
    assert investment_engine.z_search(text, pattern) == [0, 4]


def test_financial_punctuation(engine: SearchEngine) -> None:
    results = engine.exact_phrase_search("$97,858", algorithm="z")
    assert [(result["chunk_id"], result["match_count"]) for result in results] == [
        ("CHUNK_A", 1)
    ]


def test_token_boundary_behavior(engine: SearchEngine) -> None:
    bounded = engine.exact_phrase_search("ai", algorithm="kmp")
    unbounded = engine.exact_phrase_search(
        "ai", algorithm="kmp", token_boundaries=False
    )
    assert bounded[0]["match_byte_offsets"] == [5]
    assert unbounded[0]["match_byte_offsets"] == [1, 5]


def test_safe_candidate_fallback(engine: SearchEngine) -> None:
    assert engine.index.lookup("$97") == []
    results = engine.exact_phrase_search(
        "$97", algorithm="z", token_boundaries=False
    )
    assert results[0]["chunk_id"] == "CHUNK_A"
    assert results[0]["match_count"] == 1
    punctuated = engine.exact_phrase_search("revenue, growth", algorithm="kmp")
    assert [result["chunk_id"] for result in punctuated] == ["CHUNK_C"]


def test_chunk_metadata_is_preserved(engine: SearchEngine) -> None:
    result = engine.exact_phrase_search("$97,858", algorithm="kmp")[0]
    assert result == {
        "chunk_id": "CHUNK_A",
        "document_id": "DOC_A",
        "ticker": "ALFA",
        "fiscal_year": 2024,
        "match_count": 1,
        "match_byte_offsets": [66],
        "algorithm": "kmp",
    }


def test_results_have_deterministic_chunk_order(engine: SearchEngine) -> None:
    first = engine.exact_phrase_search("artificial intelligence", algorithm="z")
    second = engine.exact_phrase_search("artificial intelligence", algorithm="z")
    assert [result["chunk_id"] for result in first] == ["CHUNK_A", "CHUNK_C"]
    assert first == second


@pytest.mark.skipif(
    not HAS_REAL_DATA,
    reason="generated real collection is unavailable",
)
def test_real_collection_integration() -> None:
    engine = SearchEngine(REAL_VOCABULARY, REAL_COLLECTION)
    kmp = engine.exact_phrase_search("artificial intelligence", algorithm="kmp")
    z_function = engine.exact_phrase_search("artificial intelligence", algorithm="z")
    assert comparable(kmp) == comparable(z_function)
    nvidia = next(
        result for result in kmp
        if result["chunk_id"] == "NVDA_2024_10K_0009"
    )
    assert nvidia["match_byte_offsets"] == [468]
    assert nvidia["ticker"] == "NVDA"
    assert nvidia["fiscal_year"] == 2024


def test_existing_search_engine_behavior_is_unchanged(engine: SearchEngine) -> None:
    assert engine.contains_token("AI")
    results = engine.and_search("artificial intelligence")
    assert [item["chunk_id"] for item in results] == [
        "CHUNK_A",
        "CHUNK_C",
    ]
    assert engine.ranked_or_search("café missing")[0]["chunk_id"] == "CHUNK_B"
