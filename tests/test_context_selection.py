"""Tests for the bound C++ greedy context selector and the Jaccard additions."""

from __future__ import annotations

import pytest

import investment_engine


def sample_index() -> investment_engine.JaccardIndex:
    index = investment_engine.JaccardIndex()
    index.add_chunk("A", ["data", "center", "revenue", "grew"])
    index.add_chunk("A_COPY", ["data", "center", "revenue", "grew"])
    index.add_chunk("B", ["export", "controls", "china"])
    index.add_chunk("C", ["iphone", "net", "sales"])
    return index


def candidate(chunk_id: str, score: float, words: int) -> investment_engine.ContextCandidate:
    return investment_engine.ContextCandidate(chunk_id, score, words)


def test_chunk_similarity_binding() -> None:
    index = sample_index()
    assert index.chunk_similarity("A", "A_COPY") == 1.0
    assert index.chunk_similarity("A", "B") == 0.0
    assert index.has_chunk("A") and not index.has_chunk("Z")
    with pytest.raises(ValueError):
        index.chunk_similarity("A", "Z")


def test_selection_drops_copy_and_respects_budget() -> None:
    selection = investment_engine.select_context(
        sample_index(),
        [candidate("C", 0.5, 300), candidate("A_COPY", 0.8, 250), candidate("A", 0.9, 250),
         candidate("B", 0.7, 600)],
        4,
        600,
        0.5,
    )
    assert list(selection.selected_ids) == ["A", "C"]
    assert selection.total_words == 550
    assert [(d.chunk_id, d.status) for d in selection.decisions] == [
        ("A", "selected"),
        ("A_COPY", "redundant"),
        ("B", "over_budget"),
        ("C", "selected"),
    ]
    assert selection.decisions[1].redundant_with == "A"
    assert [d.rank for d in selection.decisions] == [1, 2, 3, 4]


def test_selection_limit_and_validation() -> None:
    index = sample_index()
    selection = investment_engine.select_context(
        index, [candidate("A", 0.9, 1), candidate("B", 0.8, 1), candidate("C", 0.7, 1)], 2, 100, 0.5
    )
    assert [d.status for d in selection.decisions] == ["selected", "selected", "limit"]
    with pytest.raises(ValueError):
        investment_engine.select_context(index, [candidate("A", 1.0, 1)], 0, 100, 0.5)
    with pytest.raises(ValueError):
        investment_engine.select_context(index, [candidate("A", 1.0, 1)], 4, 100, 0.0)
    with pytest.raises(ValueError):
        investment_engine.select_context(index, [candidate("Z", 1.0, 1)], 4, 100, 0.5)
    with pytest.raises(ValueError):
        investment_engine.select_context(
            index, [candidate("A", 1.0, 1), candidate("A", 0.5, 1)], 4, 100, 0.5
        )
