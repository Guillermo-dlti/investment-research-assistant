"""Tests for the bound approximate reranker and SearchEngine approximate/compare search."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import investment_engine
from src.python.preprocess_text import preprocess_collection
from src.python.search_engine import STOPWORDS, SearchEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_VOCABULARY = PROJECT_ROOT / "data/metadata/vocabulary.json"
REAL_COLLECTION = PROJECT_ROOT / "data/processed/preprocessed_collection.json"
HAS_REAL_DATA = REAL_VOCABULARY.exists() and REAL_COLLECTION.exists()
needs_real_data = pytest.mark.skipif(
    not HAS_REAL_DATA, reason="generated real collection is unavailable"
)


def source_collection() -> dict[str, Any]:
    texts = [
        ("CHUNK_B", "AMD", 2024, "AMD data center revenue grew."),
        ("CHUNK_A", "NVDA", 2025, "NVIDIA data center revenue grew strongly."),
        ("CHUNK_C", "AAPL", 2025, "iPhone net sales declined."),
        ("CHUNK_D", "NVDA", 2024, "Data center revenue."),
        ("CHUNK_E", "MSFT", 2025, "What is it and what was it."),
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


@pytest.fixture(scope="module")
def real_engine() -> SearchEngine:
    return SearchEngine(REAL_VOCABULARY, REAL_COLLECTION)


def ids(results: list[dict[str, Any]]) -> list[str]:
    return [result["chunk_id"] for result in results]


def test_rerank_binding_hand_computed() -> None:
    index = investment_engine.InvertedIndex()
    jaccard = investment_engine.JaccardIndex()
    for chunk_id, tokens in [
        ("C1", ["nvidia", "revenue", "grew"]),
        ("C2", ["amd", "revenue"]),
        ("C3", ["nvidia", "cloud", "chips"]),
    ]:
        index.add_chunk(chunk_id, tokens)
        jaccard.add_chunk(chunk_id, tokens)
    terms = [
        investment_engine.WeightedTerm("nvidia", 1.0),
        investment_engine.WeightedTerm("revenue", 0.5),
    ]
    results = investment_engine.rerank_candidates(
        index, jaccard, ["C1", "C2", "C3"], terms, ["nvidia", "revenue"], 0.6
    )
    assert [r.chunk_id for r in results] == ["C1", "C3", "C2"]
    assert results[0].score == pytest.approx(0.85)
    assert results[0].coverage == pytest.approx(0.75)
    assert results[0].jaccard_scaled == 1.0
    assert results[0].matched_terms == 2
    assert [r.chunk_id for r in jaccard.score_chunks(["C3", "C1"], ["nvidia"])] == ["C3", "C1"]
    with pytest.raises(ValueError):
        investment_engine.rerank_candidates(index, jaccard, ["C1", "C1"], terms, ["nvidia"], 0.6)
    with pytest.raises(ValueError):
        investment_engine.rerank_candidates(index, jaccard, ["C1"], terms, ["nvidia"], 1.5)
    with pytest.raises(ValueError):
        jaccard.score_chunks(["C9"], ["nvidia"])


def test_approximate_search_scores_follow_formula(engine: SearchEngine) -> None:
    results = engine.approximate_search("data center revenue", top_k=None)
    assert ids(results)[:1] == ["CHUNK_D"]
    assert {result["chunk_id"] for result in results} == {"CHUNK_A", "CHUNK_B", "CHUNK_D"}
    assert max(result["jaccard_scaled"] for result in results) == 1.0
    for result in results:
        assert result["algorithm"] == "approximate"
        assert 0.0 <= result["score"] <= 1.0
        assert result["score"] == pytest.approx(
            0.6 * result["coverage"] + 0.4 * result["jaccard_scaled"]
        )
    alpha_one = engine.approximate_search("data center revenue", alpha=1)
    assert all(result["score"] == result["coverage"] for result in alpha_one)


def test_typo_term_counts_less(engine: SearchEngine) -> None:
    exact = engine.approximate_search("nvidia")
    corrected = engine.approximate_search("nvidea")
    assert ids(exact) == ids(corrected) == ["CHUNK_A"]
    assert exact[0]["coverage"] == 1.0
    assert corrected[0]["coverage"] == 0.5
    assert corrected[0]["score"] < exact[0]["score"]


def test_stopwords_are_dropped_with_fallback(engine: SearchEngine) -> None:
    report = engine.compare_search("what was nvidia revenue")
    assert [term["corrected"] for term in report["terms"]] == ["nvidia", "revenue"]
    assert not any(term["corrected"] in STOPWORDS for term in report["terms"])
    assert report["stopword_fallback"] is False

    fallback = engine.compare_search("what is it")
    assert fallback["stopword_fallback"] is True
    assert ids(fallback["approximate"]["results"]) == ["CHUNK_E"]


def test_unmatched_and_digit_terms_count_in_coverage(engine: SearchEngine) -> None:
    report = engine.compare_search("nvidia zzzzzzzz 2025")
    assert report["unmatched_terms"] == ["zzzzzzzz"]
    assert [term["weight"] for term in report["terms"]] == [1.0, 1.0, 1.0]
    assert report["approximate"]["results"][0]["coverage"] == pytest.approx(1 / 3)


def test_filters_apply_before_scoring(engine: SearchEngine) -> None:
    nvda = engine.approximate_search("data center revenue", ticker=" nvda ", top_k=None)
    assert ids(nvda) == ["CHUNK_D", "CHUNK_A"]
    assert max(result["jaccard_scaled"] for result in nvda) == 1.0
    amd = engine.approximate_search("data center revenue", ticker="AMD", top_k=None)
    assert ids(amd) == ["CHUNK_B"]
    assert amd[0]["jaccard_scaled"] == 1.0
    assert ids(engine.approximate_search("revenue", fiscal_year=2024)) == ["CHUNK_D", "CHUNK_B"]
    assert engine.approximate_search("revenue", ticker="ZZZ") == []

    report = engine.compare_search("data center revenue", ticker="NVDA", top_k=1)
    assert report["exact"]["candidate_count"] == 2
    assert report["approximate"]["candidate_count"] == 2
    assert len(report["exact"]["results"]) == 1
    assert all(r["ticker"] == "NVDA" for r in report["exact"]["results"])


def test_top_k_and_validation(engine: SearchEngine) -> None:
    assert len(engine.approximate_search("revenue", top_k=1)) == 1
    assert engine.approximate_search("revenue", top_k=0) == []
    assert len(engine.approximate_search("revenue", top_k=None)) == 3
    assert engine.approximate_search("") == []
    for bad_kwargs, error in [
        ({"top_k": -1}, ValueError),
        ({"top_k": 1.5}, TypeError),
        ({"top_k": True}, TypeError),
        ({"alpha": 1.5}, ValueError),
        ({"alpha": -0.1}, ValueError),
        ({"alpha": "0.5"}, TypeError),
        ({"alpha": True}, TypeError),
        ({"fiscal_year": "2024"}, TypeError),
        ({"fiscal_year": True}, TypeError),
        ({"ticker": 5}, TypeError),
    ]:
        with pytest.raises(error):
            engine.approximate_search("revenue", **bad_kwargs)
        with pytest.raises(error):
            engine.compare_search("revenue", **bad_kwargs)


def test_compare_search_shape(engine: SearchEngine) -> None:
    report = engine.compare_search("data center revenue")
    assert report["query"] == "data center revenue"
    assert report["exact"]["mode"] == "and"
    assert report["exact"]["candidate_count"] == 3
    assert all(r["algorithm"] == "term_frequency" for r in report["exact"]["results"])
    assert report["approximate"]["candidate_count"] == 3
    assert set(report["approximate"]["steps_ms"]) == {"correction", "candidates", "rerank"}
    assert report["exact"]["time_ms"] >= 0.0
    assert report["approximate"]["time_ms"] >= 0.0
    assert report["shared_chunk_ids"] == ["CHUNK_A", "CHUNK_B", "CHUNK_D"]

    assert engine.compare_search("nvidia sales")["exact"]["mode"] == "or"
    assert engine.compare_search("zzzzzzzz")["exact"]["mode"] == "none"

    empty = engine.compare_search("  ")
    assert empty["exact"] == {"mode": "none", "results": [], "candidate_count": 0, "time_ms": 0.0}
    assert empty["approximate"]["results"] == []
    assert empty["approximate"]["steps_ms"] == {"correction": 0.0, "candidates": 0.0, "rerank": 0.0}
    assert empty["terms"] == [] and empty["stopword_fallback"] is False


def test_correct_query_unchanged(engine: SearchEngine) -> None:
    assert engine.correct_query("nvidea 2025") == [
        {"original": "nvidea", "corrected": "nvidia", "distance": 1},
        {"original": "2025", "corrected": "2025", "distance": None},
    ]


@needs_real_data
def test_real_compare_search(real_engine: SearchEngine) -> None:
    report = real_engine.compare_search("nvidia data center revenue")
    for side in ("exact", "approximate"):
        assert report[side]["results"]
        assert report[side]["candidate_count"] >= len(report[side]["results"])
        assert report[side]["time_ms"] > 0.0
    assert all(value >= 0.0 for value in report["approximate"]["steps_ms"].values())


@needs_real_data
def test_real_typo_found_only_by_approximate(real_engine: SearchEngine) -> None:
    report = real_engine.compare_search("nvidea", top_k=None)
    assert report["exact"]["results"] == []
    results = report["approximate"]["results"]
    assert results
    assert all(real_engine.index.term_frequency("nvidia", r["chunk_id"]) > 0 for r in results)
    assert [(t["original"], t["corrected"], t["distance"]) for t in report["terms"]] == [
        ("nvidea", "nvidia", 1)
    ]


@needs_real_data
def test_real_stopword_cases(real_engine: SearchEngine) -> None:
    fallback = real_engine.compare_search("what is it")
    assert fallback["stopword_fallback"] is True
    assert fallback["approximate"]["results"]
    # "thw" corrects to the stopword "the", so nothing is left to search.
    corrected_away = real_engine.compare_search("thw")
    assert corrected_away["terms"] == []
    assert corrected_away["approximate"]["results"] == []
    assert corrected_away["stopword_fallback"] is False


@needs_real_data
def test_real_ticker_filter(real_engine: SearchEngine) -> None:
    results = real_engine.approximate_search("data center revenue", ticker="AMD", top_k=None)
    assert results
    assert all(result["ticker"] == "AMD" for result in results)
    assert max(result["jaccard_scaled"] for result in results) == 1.0
