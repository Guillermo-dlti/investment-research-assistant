"""Tests for the Stage 6 comparison with a fake generator (no model download)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.python import compare_strategies as cs
from src.python.research_assistant import NO_CONTEXT_ANSWER, NOT_FOUND_ANSWER
from tests.test_research_assistant import FakeGenerator, make_assistant


NVIDIA_QUESTION = "What was NVIDIA data center revenue in fiscal 2025?"


def test_question_set_has_at_least_twenty_and_evidence_is_known() -> None:
    questions = [question for question, _ in cs.QUESTIONS]
    assert len(questions) >= 20
    assert len(set(questions)) == len(questions)
    assert set(cs.EVIDENCE) <= set(questions)
    assert set(cs.EXPECTED_ANSWERS) <= set(questions)
    assert cs.EXPECTED_REFUSALS <= set(questions) - set(cs.EVIDENCE)


def test_usefulness() -> None:
    assert cs.usefulness(["a", "b", "c", "d"], {"b", "d", "z"}) == {
        "hit": True, "precision": 0.5, "first_rank": 2, "useful": ["b", "d"],
    }
    assert cs.usefulness(["a"], set()) == {"hit": False, "precision": 0.0, "first_rank": None, "useful": []}
    assert cs.usefulness([], {"a"})["precision"] == 0.0
    assert cs.usefulness(["a"], None)["hit"] is None


def test_overlap() -> None:
    assert cs.overlap(["a", "b"], ["b", "c"]) == pytest.approx(1 / 3)
    assert cs.overlap([], []) == 1.0
    assert cs.overlap(["a"], []) == 0.0


def test_judge_answer() -> None:
    assert cs.judge_answer(NVIDIA_QUESTION, "It was $115,186 million [1].") == "correct"
    assert cs.judge_answer(NVIDIA_QUESTION, "It was $60,922 million [1].") == "missed fact"
    assert cs.judge_answer(NVIDIA_QUESTION, NOT_FOUND_ANSWER) == "refused"
    assert cs.judge_answer("Who does NVIDIA consider its main competitors?", "AMD [1].") == "answered"
    tesla = "What is Tesla revenue from electric vehicles?"
    assert cs.judge_answer(tesla, NOT_FOUND_ANSWER) == "correct refusal"
    assert cs.judge_answer(tesla, NO_CONTEXT_ANSWER) == "correct refusal"
    assert cs.judge_answer(tesla, "Tesla made $1 [1].") == "should refuse"


def test_evidence_chunks_apply_ticker_year_and_every_pattern(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path, FakeGenerator())
    assert cs.evidence_chunks(assistant.sources, "What is the outlook?") is None
    original = dict(cs.EVIDENCE)
    try:
        cs.EVIDENCE["q"] = ("NVDA", 2025, [r"data center", r"hopper|china"])
        assert cs.evidence_chunks(assistant.sources, "q") == {"NVDA_2025_10K_0001", "NVDA_2025_10K_0002"}
        cs.EVIDENCE["q"] = (None, None, [r"data center", r"epyc"])
        assert cs.evidence_chunks(assistant.sources, "q") == {"AMD_2025_10K_0001"}
    finally:
        cs.EVIDENCE.clear()
        cs.EVIDENCE.update(original)


def test_compare_question_runs_both_modes(tmp_path: Path) -> None:
    fake = FakeGenerator("Revenue grew [1].")
    assistant = make_assistant(tmp_path, fake)
    entry = cs.compare_question(assistant, "nvidea data center revenue", "typo", repeats=2)

    assert entry["evidence_count"] is None
    assert entry["filters"] == {"ticker": None, "fiscal_year": None}
    assert len(fake.calls) == 2  # one answer per mode
    for mode in ("exact", "approximate"):
        side = entry[mode]
        assert side["retrieval_ms"] >= 0
        assert side["verdict"] == "answered"
        assert set(side["selected"]) <= set(side["retrieved"])
        assert side["selected_usefulness"]["hit"] is None
    # The typo hides NVIDIA from exact search; approximate corrects it.
    assert any(chunk.startswith("NVDA") for chunk in entry["approximate"]["selected"])
    assert 0.0 <= entry["retrieved_overlap"] <= 1.0
    assert entry["same_context"] == (entry["exact"]["selected"] == entry["approximate"]["selected"])

    summary = cs.summarize([entry])
    assert summary["agreement"]["questions"] == 1
    assert summary["exact"]["judged_questions"] == 0
    assert summary["exact"]["verdicts"] == {"answered": 1}


def test_scaled_collection() -> None:
    payload = {"version": 1, "total_chunks": 4, "chunks": [{"chunk_id": f"C{i}"} for i in range(4)]}
    half = cs.scaled_collection(payload, 0.5)
    assert [chunk["chunk_id"] for chunk in half["chunks"]] == ["C0", "C2"]
    assert half["total_chunks"] == 2 and half["version"] == 1
    double = cs.scaled_collection(payload, 2.0)
    ids = [chunk["chunk_id"] for chunk in double["chunks"]]
    assert double["total_chunks"] == 8 and len(set(ids)) == 8
    assert ids[4] == "C0_COPY1"
    assert payload["chunks"][0] == {"chunk_id": "C0"}  # input left unchanged


def test_scaling_benchmark_and_report(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path, FakeGenerator("Revenue grew [1]."))
    rows = cs.scaling_benchmark(
        tmp_path / "vocabulary.json",
        tmp_path / "preprocessed_collection.json",
        ["data center revenue"],
        factors=(0.5, 1.0, 2.0),
        repeats=1,
    )
    assert [row["chunks"] for row in rows] == [3, 5, 10]
    assert rows[2]["approximate"]["mean_candidates"] == 2 * rows[1]["approximate"]["mean_candidates"]

    entries = [cs.compare_question(assistant, "NVIDIA data center revenue", "", repeats=1)]
    summary = cs.summarize(entries)
    figures = cs.plot_figures(entries, rows, tmp_path / "figures")
    assert all(path.exists() and path.stat().st_size > 0 for path in figures)

    settings = {"model": "fake", "repeats": 1, "max_chunks": 4, "word_budget": 1100, "redundancy_threshold": 0.5}
    markdown = cs.to_markdown(entries, summary, rows, settings)
    assert "| Mean retrieval time (ms) |" in markdown
    assert "NVIDIA data center revenue" in markdown
    assert "## Collection size" in markdown
    json.dumps({"summary": summary, "scaling": rows, "results": entries})  # serializable
