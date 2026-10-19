"""Tests for the bound n-gram/Jaccard functions and SearchEngine integration."""

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
        ("CHUNK_B", "AMD", 2024, "AMD data center revenue grew."),
        ("CHUNK_A", "NVDA", 2025, "NVIDIA data center revenue grew strongly."),
        ("CHUNK_C", "AAPL", 2025, "iPhone net sales declined."),
        ("CHUNK_D", "NVDA", 2024, "Data center revenue."),
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


def test_ngram_bindings() -> None:
    assert investment_engine.character_ngrams("banana", 3) == ["ana", "ban", "nan"]
    assert investment_engine.character_ngrams("ab", 3) == ["ab"]
    assert investment_engine.word_ngrams(["data", "center"], 1, 2) == [
        "center",
        "data",
        "data center",
    ]
    with pytest.raises(ValueError):
        investment_engine.character_ngrams("abc", 0)


def test_jaccard_binding_values() -> None:
    assert investment_engine.jaccard_similarity(["a", "b"], ["a", "b"]) == 1.0
    assert investment_engine.jaccard_similarity(["a"], ["b"]) == 0.0
    assert investment_engine.jaccard_similarity(["a", "b", "c"], ["b", "c", "d"]) == 0.5
    assert investment_engine.jaccard_similarity([], []) == 0.0


def test_jaccard_index_binding() -> None:
    index = investment_engine.JaccardIndex()
    index.add_chunk("C1", ["nvidia", "revenue", "grew"])
    index.add_chunk("C2", ["amd", "revenue"])
    results = index.rank(["nvidia", "revenue"])
    assert [(r.chunk_id, r.shared_ngrams, r.union_size) for r in results] == [
        ("C1", 3, 5),
        ("C2", 1, 5),
    ]
    assert index.rank(["nvidia", "revenue"], top_k=0) == []
    with pytest.raises(ValueError):
        index.add_chunk("C1", ["x"])


def test_jaccard_search_ranks_by_score(engine: SearchEngine) -> None:
    results = engine.jaccard_search("data center revenue")
    assert [result["chunk_id"] for result in results] == ["CHUNK_D", "CHUNK_B", "CHUNK_A"]
    assert results[0]["score"] == 1.0
    assert all(0.0 < result["score"] <= 1.0 for result in results)
    assert results[0]["algorithm"] == "jaccard"
    assert results[0]["ticker"] == "NVDA"


def test_jaccard_search_filters_and_top_k(engine: SearchEngine) -> None:
    assert [r["chunk_id"] for r in engine.jaccard_search("data center revenue", ticker="nvda")] == [
        "CHUNK_D",
        "CHUNK_A",
    ]
    assert [
        r["chunk_id"] for r in engine.jaccard_search("data center revenue", fiscal_year=2024)
    ] == ["CHUNK_D", "CHUNK_B"]
    assert len(engine.jaccard_search("data center revenue", top_k=1)) == 1
    assert engine.jaccard_search("data center revenue", top_k=0) == []
    assert engine.jaccard_search("") == []
    assert engine.jaccard_search("unrelated words") == []
    with pytest.raises(ValueError):
        engine.jaccard_search("revenue", top_k=-1)


@pytest.mark.skipif(not HAS_REAL_DATA, reason="generated real collection is unavailable")
def test_real_collection_jaccard() -> None:
    engine = SearchEngine(REAL_VOCABULARY, REAL_COLLECTION)
    assert engine.jaccard_index.chunk_count == engine.indexed_chunk_count
    results = engine.jaccard_search("iPhone net sales", top_k=3)
    assert len(results) == 3
    assert all(result["ticker"] == "AAPL" for result in results)
