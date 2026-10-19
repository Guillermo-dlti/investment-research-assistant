"""Tests for the bound Levenshtein matcher and SearchEngine fuzzy integration."""

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
        ("CHUNK_A", "NVDA", 2025, "NVIDIA revenue grew. NVIDIA revenue and revenues rose."),
        ("CHUNK_B", "MSFT", 2024, "Microsoft cloud revenue was $97,858 million."),
        ("CHUNK_C", "AMD", 2025, "AMD government semiconductor sales could grow."),
    ]
    chunks = []
    for position, (chunk_id, ticker, year, text) in enumerate(texts, 1):
        chunks.append(
            {
                "chunk_id": chunk_id,
                "document_id": f"{ticker}_{year}_10K",
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


def test_distance_bindings() -> None:
    assert investment_engine.levenshtein_distance("kitten", "sitting") == 3
    assert investment_engine.levenshtein_distance("", "amd") == 3
    assert investment_engine.levenshtein_distance("café", "cafe") == 2
    assert investment_engine.bounded_levenshtein("kitten", "sitting", 2) == 3
    assert investment_engine.bounded_levenshtein("kitten", "sitting", 3) == 3
    assert investment_engine.default_max_distance("amd") == 1
    assert investment_engine.default_max_distance("nvidia") == 2


def test_matcher_binding() -> None:
    matcher = investment_engine.FuzzyMatcher()
    matcher.add_word("nvidia", 10)
    matcher.add_word("nvda", 3)
    assert matcher.size == 2
    matches = matcher.match("nvidea")
    assert [(m.word, m.distance, m.frequency) for m in matches] == [
        ("nvidia", 1, 10),
        ("nvda", 2, 3),
    ]
    assert matcher.match("nvidxx", max_distance=1) == []
    assert matcher.match("nvidia", limit=0) == []
    with pytest.raises(ValueError):
        matcher.add_word("nvda", 1)


def test_fuzzy_terms_finds_typos(engine: SearchEngine) -> None:
    assert engine.fuzzy_terms("nvidea")[0] == {"word": "nvidia", "distance": 1, "frequency": 2}
    assert [match["word"] for match in engine.fuzzy_terms("Revenu")] == ["revenue", "revenues"]


def test_fuzzy_terms_exact_hit_and_limits(engine: SearchEngine) -> None:
    assert engine.fuzzy_terms("Microsoft") == [
        {"word": "microsoft", "distance": 0, "frequency": 1}
    ]
    assert len(engine.fuzzy_terms("revenu", limit=1)) == 1
    assert engine.fuzzy_terms("revenu", limit=0) == []
    assert engine.fuzzy_terms("revenuxx", max_distance=1) == []
    with pytest.raises(ValueError):
        engine.fuzzy_terms("revenu", limit=-1)
    with pytest.raises(ValueError):
        engine.fuzzy_terms("revenu", max_distance=-1)
    with pytest.raises(ValueError):
        engine.fuzzy_terms("two words")


def test_correct_query(engine: SearchEngine) -> None:
    corrections = engine.correct_query("NVIDEA goverment revenue $97,868 zzzzzz")
    assert corrections == [
        {"original": "nvidea", "corrected": "nvidia", "distance": 1},
        {"original": "goverment", "corrected": "government", "distance": 1},
        {"original": "revenue", "corrected": "revenue", "distance": 0},
        {"original": "$97,868", "corrected": "$97,868", "distance": None},
        {"original": "zzzzzz", "corrected": "zzzzzz", "distance": None},
    ]


def test_exact_search_still_works(engine: SearchEngine) -> None:
    results = engine.exact_phrase_search("nvidia revenue")
    assert [result["chunk_id"] for result in results] == ["CHUNK_A"]


@pytest.mark.skipif(not HAS_REAL_DATA, reason="generated real collection is unavailable")
def test_real_vocabulary_corrections() -> None:
    engine = SearchEngine(REAL_VOCABULARY, REAL_COLLECTION)
    assert engine.fuzzy_matcher.size == engine.vocabulary_size
    corrected = [item["corrected"] for item in engine.correct_query("nvidea semiconducter goverment")]
    assert corrected == ["nvidia", "semiconductor", "government"]
