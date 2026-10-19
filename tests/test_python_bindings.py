"""Tests for the pybind11 module and its thin Python integration layer."""

from __future__ import annotations

from pathlib import Path

import pytest

import investment_engine
from src.python.search_engine import SearchEngine, normalize_query, normalize_single_token


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOCABULARY_PATH = PROJECT_ROOT / "data/metadata/vocabulary.json"
COLLECTION_PATH = PROJECT_ROOT / "data/processed/preprocessed_collection.json"
HAS_REAL_DATA = VOCABULARY_PATH.exists() and COLLECTION_PATH.exists()


def make_index() -> investment_engine.InvertedIndex:
    index = investment_engine.InvertedIndex()
    index.add_chunk(
        "CHUNK_B",
        ["revenue", "growth"],
        document_id="DOC_1",
        ticker="TEST",
        fiscal_year=2025,
    )
    index.add_chunk(
        "CHUNK_A",
        ["revenue", "revenue", "artificial", "intelligence"],
        document_id="DOC_2",
        ticker="DEMO",
        fiscal_year=2024,
    )
    index.add_chunk("CHUNK_C", ["artificial", "growth"])
    return index


def test_compiled_module_imports() -> None:
    assert investment_engine.__doc__
    assert investment_engine.Trie is not None
    assert investment_engine.InvertedIndex is not None


def test_trie_insertion_and_lookup() -> None:
    trie = investment_engine.Trie()
    trie.insert("nvidia")
    assert trie.search("nvidia")
    assert not trie.search("nvda")
    assert trie.size == 1


def test_prefix_search_and_autocomplete() -> None:
    trie = investment_engine.Trie()
    for token in ["apply", "apple", "app"]:
        trie.insert(token)
    assert trie.starts_with("app")
    assert trie.autocomplete("app", 10) == ["app", "apple", "apply"]
    assert trie.autocomplete("app", 0) == []


def test_financial_punctuation_and_utf8_tokens() -> None:
    trie = investment_engine.Trie()
    tokens = ["s&p", "$97,858", "12.5%", "ai-powered", "chávez", "€1.5"]
    for token in tokens:
        trie.insert(token)
    assert all(trie.search(token) for token in tokens)
    assert trie.starts_with("chá")


def test_inverted_index_insertion_and_metadata() -> None:
    index = make_index()
    assert index.chunk_count == 3
    assert index.vocabulary_size == 4
    assert index.get_metadata("CHUNK_A") == {
        "document_id": "DOC_2",
        "ticker": "DEMO",
        "fiscal_year": 2024,
    }


def test_single_token_lookup() -> None:
    index = make_index()
    assert index.lookup("revenue") == ["CHUNK_A", "CHUNK_B"]
    assert index.lookup("missing") == []


def test_and_and_or_queries() -> None:
    index = make_index()
    assert index.and_query(["artificial", "intelligence"]) == ["CHUNK_A"]
    assert index.or_query(["revenue", "artificial"]) == [
        "CHUNK_A",
        "CHUNK_B",
        "CHUNK_C",
    ]
    assert index.and_query(["revenue", "missing"]) == []


def test_term_and_document_frequency() -> None:
    index = make_index()
    assert index.term_frequency("revenue", "CHUNK_A") == 2
    assert index.term_frequency("revenue", "CHUNK_C") == 0
    assert index.document_frequency("revenue") == 2


def test_ranking_and_deterministic_tie_breaking() -> None:
    ranked = make_index().ranked_or(["revenue", "growth"])
    assert [(item.chunk_id, item.score) for item in ranked] == [
        ("CHUNK_A", 2),
        ("CHUNK_B", 2),
        ("CHUNK_C", 1),
    ]


def test_empty_and_invalid_inputs() -> None:
    index = make_index()
    assert index.and_query([]) == []
    assert index.or_query([]) == []
    with pytest.raises(ValueError, match="duplicate chunk_id"):
        index.add_chunk("CHUNK_A", ["duplicate"])
    with pytest.raises(ValueError, match="chunk_id must not be empty"):
        index.add_chunk("", ["invalid"])
    with pytest.raises(TypeError):
        investment_engine.Trie().insert(None)


def test_query_normalization_reuses_preprocessing_policy() -> None:
    assert normalize_query("NVIDIA’s AI‑powered growth of 12.5%") == [
        "nvidia's",
        "ai-powered",
        "growth",
        "of",
        "12.5%",
    ]
    assert normalize_single_token("Ｓ＆Ｐ") == "s&p"
    with pytest.raises(ValueError, match="exactly one token"):
        normalize_single_token("artificial intelligence")


@pytest.mark.skipif(not HAS_REAL_DATA, reason="generated real collection is unavailable")
def test_loading_and_querying_real_collection() -> None:
    engine = SearchEngine(VOCABULARY_PATH, COLLECTION_PATH)
    assert engine.vocabulary_size == 14180
    assert engine.indexed_chunk_count == 2458
    assert engine.contains_token("NVIDIA")
    assert engine.autocomplete("nv", 3) == ["nvda", "nvestment", "nveu"]
    assert len(engine.single_token_search("Revenue")) == 521
    assert len(engine.and_search("Artificial intelligence")) == 30
    assert len(engine.or_search("NVIDIA AMD")) == 354
    assert engine.ranked_and_search("Artificial intelligence")[0] == {
        "chunk_id": "GOOGL_2025_10K_0067",
        "document_id": "GOOGL_2025_10K",
        "ticker": "GOOGL",
        "fiscal_year": 2025,
        "score": 4,
    }
    assert engine.single_token_search("definitely-missing-token") == []
