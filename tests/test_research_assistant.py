"""Tests for the Stage 5 pipeline with a fake generator (no model download)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.python.preprocess_text import preprocess_collection
from src.python.research_assistant import (
    NO_CONTEXT_ANSWER,
    ResearchAssistant,
    build_messages,
    cited_sources,
    infer_filters,
    normalize_citations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_VOCABULARY = PROJECT_ROOT / "data/metadata/vocabulary.json"
REAL_COLLECTION = PROJECT_ROOT / "data/processed/preprocessed_collection.json"
REAL_SOURCES = PROJECT_ROOT / "data/chunks/collection.json"
needs_real_data = pytest.mark.skipif(
    not (REAL_VOCABULARY.exists() and REAL_COLLECTION.exists() and REAL_SOURCES.exists()),
    reason="generated real collection is unavailable",
)

REPEATED = "NVIDIA data center revenue grew on strong Hopper demand from cloud providers."


class FakeGenerator:
    name = "fake-model"

    def __init__(self, answer: str = "Data center revenue grew [1] [9].") -> None:
        self.answer = answer
        self.calls: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.answer


def source_collection() -> dict[str, Any]:
    texts = [
        ("NVDA_2025_10K_0001", "NVDA", "NVIDIA Corporation", 2025, REPEATED),
        ("NVDA_2024_10K_0001", "NVDA", "NVIDIA Corporation", 2024, REPEATED),
        ("NVDA_2025_10K_0002", "NVDA", "NVIDIA Corporation", 2025, "Export controls limit data center sales to China."),
        ("AMD_2025_10K_0001", "AMD", "Advanced Micro Devices, Inc.", 2025, "AMD data center revenue  grew\n\nfrom EPYC."),
        ("AAPL_2025_10K_0001", "AAPL", "Apple Inc.", 2025, "iPhone net sales declined."),
    ]
    chunks = []
    for position, (chunk_id, ticker, company, year, text) in enumerate(texts, 1):
        chunks.append(
            {
                "chunk_id": chunk_id,
                "document_id": chunk_id.rsplit("_", 1)[0],
                "position": position,
                "company": company,
                "ticker": ticker,
                "fiscal_year": year,
                "document_type": "10-K",
                "filing_date": f"{year}-02-01",
                "fiscal_year_end": f"{year}-01-31",
                "source_url": f"https://www.sec.gov/{chunk_id.lower()}",
                "paragraph_start_id": position,
                "paragraph_end_id": position,
                "word_count": len(text.split()),
                "text": text,
            }
        )
    return {"collection_version": 1, "total_chunks": len(chunks), "chunks": chunks}


def make_assistant(tmp_path: Path, generator: FakeGenerator, **options: Any) -> ResearchAssistant:
    source = source_collection()
    collection, vocabulary = preprocess_collection(source)
    paths = {
        "collection": tmp_path / "preprocessed_collection.json",
        "vocabulary": tmp_path / "vocabulary.json",
        "source": tmp_path / "collection.json",
    }
    paths["collection"].write_text(json.dumps(collection), encoding="utf-8")
    paths["vocabulary"].write_text(json.dumps(vocabulary), encoding="utf-8")
    paths["source"].write_text(json.dumps(source), encoding="utf-8")
    return ResearchAssistant(
        paths["vocabulary"], paths["collection"], paths["source"], generator=generator, **options
    )


@pytest.fixture
def fake() -> FakeGenerator:
    return FakeGenerator()


@pytest.fixture
def assistant(tmp_path: Path, fake: FakeGenerator) -> ResearchAssistant:
    return make_assistant(tmp_path, fake)


def test_infer_filters() -> None:
    assert infer_filters("What was NVIDIA revenue in fiscal 2025?") == {"ticker": "NVDA", "fiscal_year": 2025}
    assert infer_filters("Google cloud growth in FY2024") == {"ticker": "GOOGL", "fiscal_year": 2024}
    assert infer_filters("Compare Apple and Microsoft") == {"ticker": None, "fiscal_year": None}
    assert infer_filters("revenue in 2025 vs fiscal year 2024") == {"ticker": None, "fiscal_year": 2024}
    assert infer_filters("fiscal 2024 and fiscal 2025") == {"ticker": None, "fiscal_year": None}
    assert infer_filters("pineapple sales")["ticker"] is None


def test_cited_sources() -> None:
    assert cited_sources("A [2] and B [1][2], not [7] or [0].", 3) == [1, 2]
    assert cited_sources("no citations", 3) == []


def test_normalize_citations() -> None:
    assert normalize_citations("[N1] Revenue rose [Source [3]] and [source 2].") == (
        "[1] Revenue rose [3] and [2]."
    )
    assert normalize_citations("Plain [4] stays.") == "Plain [4] stays."


def test_ask_normalizes_model_citations(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path, FakeGenerator("[N1] Revenue grew."))
    result = assistant.ask("NVIDIA data center revenue")
    assert result["answer"] == "[1] Revenue grew."
    assert result["cited_sources"] == [1]


def test_build_messages_numbers_sources() -> None:
    source = {
        "chunk_id": "X_1", "company": "X Corp", "ticker": "X", "fiscal_year": 2025, "text": "Body.",
    }
    messages = build_messages("Why?", [source, {**source, "chunk_id": "X_2"}])
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "only the" in messages[0]["content"]
    user = messages[1]["content"]
    assert "[1] X Corp (X) 10-K, fiscal year 2025:\nBody." in user
    assert "[2] X Corp (X) 10-K, fiscal year 2025:" in user
    assert "Question: Why?" in user


def test_ask_end_to_end(assistant: ResearchAssistant, fake: FakeGenerator) -> None:
    result = assistant.ask("NVIDIA data center revenue")
    assert result["filters"] == {"ticker": "NVDA", "fiscal_year": None}
    assert result["inferred_filters"] == {"ticker": "NVDA", "fiscal_year": None}
    assert all(r["ticker"] == "NVDA" for r in result["retrieval"]["results"])
    assert result["retrieval"]["time_ms"] >= 0
    selected = result["context"]["selected"]
    ids = [source["chunk_id"] for source in selected]
    # The FY2024 copy of the same paragraph is dropped as redundant.
    assert len(ids) == len(set(ids)) == 2
    statuses = {d["chunk_id"]: d["status"] for d in result["context"]["decisions"]}
    assert sorted(statuses.values()) == ["redundant", "selected", "selected"]
    assert result["context"]["total_words"] == sum(source["word_count"] for source in selected)
    for source in selected:
        assert source["source_url"].startswith("https://www.sec.gov/")
        assert source["company"] == "NVIDIA Corporation"
        assert source["text"] and "\n" not in source["text"]
    assert len(fake.calls) == 1 and fake.calls[0] == result["messages"]
    assert result["answer"] == fake.answer
    assert result["cited_sources"] == [1]
    assert result["model"] == "fake-model"


def test_explicit_filters_win_and_auto_off(assistant: ResearchAssistant) -> None:
    result = assistant.ask("NVIDIA data center revenue", ticker="AMD")
    assert result["filters"]["ticker"] == "AMD"
    assert [s["chunk_id"] for s in result["context"]["selected"]] == ["AMD_2025_10K_0001"]
    unfiltered = assistant.ask("NVIDIA data center revenue", auto_filters=False)
    assert unfiltered["filters"] == {"ticker": None, "fiscal_year": None}
    assert unfiltered["inferred_filters"] == {}


def test_budget_and_limit(tmp_path: Path, fake: FakeGenerator) -> None:
    small = make_assistant(tmp_path, fake, max_chunks=1)
    result = small.ask("data center revenue", auto_filters=False)
    assert len(result["context"]["selected"]) == 1
    tight = make_assistant(tmp_path, fake, word_budget=8)
    result = tight.ask("data center revenue", auto_filters=False)
    assert result["context"]["total_words"] <= 8


def test_no_context_skips_model(assistant: ResearchAssistant, fake: FakeGenerator) -> None:
    result = assistant.ask("quantum teleportation zzzz", auto_filters=False)
    assert result["context"]["selected"] == []
    assert result["answer"] == NO_CONTEXT_ANSWER
    assert result["messages"] == [] and fake.calls == []
    assert result["generation_ms"] == 0.0


def test_exact_mode_and_bad_mode(assistant: ResearchAssistant) -> None:
    result = assistant.ask("export controls", mode="exact")
    assert result["mode"] == "exact"
    assert [s["chunk_id"] for s in result["context"]["selected"]] == ["NVDA_2025_10K_0002"]
    with pytest.raises(ValueError):
        assistant.ask("export controls", mode="fuzzy")


@needs_real_data
def test_real_data_nvidia_question() -> None:
    assistant = ResearchAssistant(
        REAL_VOCABULARY, REAL_COLLECTION, REAL_SOURCES, generator=FakeGenerator("ok")
    )
    result = assistant.ask("What was NVIDIA data center revenue in fiscal 2025?")
    selected = result["context"]["selected"]
    assert 1 <= len(selected) <= 4
    assert result["context"]["total_words"] <= 1100
    assert all(s["ticker"] == "NVDA" and s["fiscal_year"] == 2025 for s in selected)
