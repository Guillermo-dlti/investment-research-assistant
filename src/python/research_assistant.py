"""Stage 5 pipeline: question → search → context selection → language model → answer."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Protocol

import investment_engine

from src.python.search_engine import DEFAULT_COLLECTION, DEFAULT_VOCABULARY, SearchEngine


DEFAULT_SOURCE_COLLECTION = Path("data/chunks/collection.json")
DEFAULT_MODEL = "Qwen/Qwen2.5-3B-Instruct"
RETRIEVAL_TOP_K = 10
MAX_CHUNKS = 4
WORD_BUDGET = 1100
REDUNDANCY_THRESHOLD = 0.5
MAX_NEW_TOKENS = 300
MODES = ("approximate", "exact")

NOT_FOUND_ANSWER = "The provided filings do not contain this information."
NO_CONTEXT_ANSWER = (
    "No relevant passages were found in the filings for this question, "
    "so no answer was generated."
)
SYSTEM_PROMPT = (
    "You are a financial research assistant. Answer the question using only the "
    "numbered sources, which are excerpts from SEC 10-K filings. Cite every fact "
    "with its source number in square brackets, like [1]. Keep numbers and fiscal "
    "years exactly as written in the sources, and give the exact amounts "
    "(dollars and percentages) when a source states them. Tables are written on "
    "one line with cells separated by |, and their dollar values are usually in "
    "millions. If the sources do not contain the "
    f'answer, reply exactly: "{NOT_FOUND_ANSWER}" Answer in at most five plain '
    "sentences, without lists or headings."
)
ANSWER_INSTRUCTION = (
    "Answer in full sentences using only the sources above. Write each fact "
    "first and end its sentence with the source number in square brackets, "
    "such as [1] or [2]. Do not repeat the source headings, and never reply "
    "with source numbers alone."
)

# Whole-word aliases, matched on the casefolded question.
COMPANY_ALIASES = {
    "NVDA": ("nvidia", "nvda"),
    "AMD": ("amd", "advanced micro devices"),
    "MSFT": ("microsoft", "msft"),
    "AAPL": ("apple", "aapl"),
    "GOOGL": ("alphabet", "google", "googl", "goog"),
}
FISCAL_YEAR_PATTERN = re.compile(r"\b(?:fiscal(?:\s+year)?\s+|fy\s*)(20\d\d)\b")
CITATION_PATTERN = re.compile(r"\[(\d+)\]")
# Variants small models write instead of [n]: [N1], [Source 1], [Source [1]].
CITATION_VARIANT_PATTERN = re.compile(r"\[\s*(?:n|source)\s*\[?\s*(\d+)\s*\]?\s*\]", re.IGNORECASE)


class Generator(Protocol):
    """Anything that turns chat messages into an answer string."""

    name: str

    def generate(self, messages: list[dict[str, str]]) -> str: ...


class HuggingFaceGenerator:
    """A pretrained Hugging Face chat model, loaded on first use, greedy decoding."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        max_new_tokens: int = MAX_NEW_TOKENS,
        device: str | None = None,
    ) -> None:
        self.name = model_name
        self.max_new_tokens = max_new_tokens
        self.device = device
        self._tokenizer: Any = None
        self._model: Any = None
        self._load_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        with self._load_lock:
            if self._model is None:
                self._load()

    def _load(self) -> None:
        # Quiet import time and loading noise from torch and transformers.
        logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").setLevel(logging.ERROR)
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from transformers.utils import logging as transformers_logging

        transformers_logging.set_verbosity_error()
        transformers_logging.disable_progress_bar()

        if self.device is None:
            self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        dtype = torch.float32 if self.device == "cpu" else torch.float16
        self._tokenizer = AutoTokenizer.from_pretrained(self.name)
        self._model = AutoModelForCausalLM.from_pretrained(self.name, dtype=dtype)
        self._model.to(self.device)
        self._model.eval()
        # Greedy decoding: clear the sampling defaults shipped with the model.
        config = self._model.generation_config
        config.do_sample = False
        config.temperature = None
        config.top_p = None
        config.top_k = None

    def generate(self, messages: list[dict[str, str]]) -> str:
        import torch

        self.load()
        prompt = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def infer_filters(question: str) -> dict[str, Any]:
    """Guess ticker and fiscal year filters from explicit mentions in a question.

    A ticker is set only when exactly one company is named, and a fiscal year
    only when exactly one year follows "fiscal", "fiscal year" or "FY".
    """
    text = question.casefold()
    tickers = [
        ticker
        for ticker, aliases in COMPANY_ALIASES.items()
        if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases)
    ]
    years = {int(year) for year in FISCAL_YEAR_PATTERN.findall(text)}
    return {
        "ticker": tickers[0] if len(tickers) == 1 else None,
        "fiscal_year": years.pop() if len(years) == 1 else None,
    }


def build_messages(question: str, sources: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Chat messages with the selected chunks as numbered sources."""
    blocks = [
        f"[{number}] {source['company']} ({source['ticker']}) 10-K, fiscal year "
        f"{source['fiscal_year']}:\n{source['text']}"
        for number, source in enumerate(sources, 1)
    ]
    user = (
        "Sources:\n\n" + "\n\n".join(blocks)
        + f"\n\nQuestion: {question}\n\n{ANSWER_INSTRUCTION}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def normalize_citations(answer: str) -> str:
    """Rewrite citation variants such as [N1] or [Source [1]] as [1]."""
    return CITATION_VARIANT_PATTERN.sub(r"[\1]", answer)


def cited_sources(answer: str, source_count: int) -> list[int]:
    """Distinct source numbers cited as [n] in the answer, in range, ascending."""
    numbers = {int(number) for number in CITATION_PATTERN.findall(answer)}
    return sorted(number for number in numbers if 1 <= number <= source_count)


class ResearchAssistant:
    """Answers questions about the filings from retrieved, selected chunks."""

    def __init__(
        self,
        vocabulary_path: Path | str = DEFAULT_VOCABULARY,
        collection_path: Path | str = DEFAULT_COLLECTION,
        source_collection_path: Path | str = DEFAULT_SOURCE_COLLECTION,
        *,
        generator: Generator | None = None,
        retrieval_top_k: int = RETRIEVAL_TOP_K,
        max_chunks: int = MAX_CHUNKS,
        word_budget: int = WORD_BUDGET,
        redundancy_threshold: float = REDUNDANCY_THRESHOLD,
    ) -> None:
        self.engine = SearchEngine(vocabulary_path, collection_path)
        self.sources = self._load_sources(source_collection_path)
        self.generator: Generator = generator or HuggingFaceGenerator()
        self.retrieval_top_k = retrieval_top_k
        self.max_chunks = max_chunks
        self.word_budget = word_budget
        self.redundancy_threshold = redundancy_threshold

    def retrieve(
        self,
        question: str,
        *,
        mode: str = "approximate",
        ticker: str | None = None,
        fiscal_year: int | None = None,
    ) -> dict[str, Any]:
        """Run one search mode and time it."""
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        start = time.perf_counter()
        if mode == "approximate":
            results = self.engine.approximate_search(
                question, ticker=ticker, fiscal_year=fiscal_year, top_k=None
            )
            candidate_count = len(results)
            results = results[: self.retrieval_top_k]
        else:
            results, _, candidate_count = self.engine.exact_ranked_search(
                question, ticker=ticker, fiscal_year=fiscal_year, top_k=self.retrieval_top_k
            )
        elapsed = (time.perf_counter() - start) * 1000
        return {"results": results, "candidate_count": candidate_count, "time_ms": elapsed}

    def select(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Choose the context chunks in C++ and attach their original text."""
        start = time.perf_counter()
        candidates = [
            investment_engine.ContextCandidate(
                result["chunk_id"],
                float(result["score"]),
                self.sources[result["chunk_id"]]["word_count"],
            )
            for result in results
        ]
        selection = investment_engine.select_context(
            self.engine.jaccard_index,
            candidates,
            self.max_chunks,
            self.word_budget,
            self.redundancy_threshold,
        )
        elapsed = (time.perf_counter() - start) * 1000
        scores = {result["chunk_id"]: result["score"] for result in results}
        return {
            "selected": [
                {**self.sources[chunk_id], "score": scores[chunk_id]}
                for chunk_id in selection.selected_ids
            ],
            "decisions": [
                {
                    "chunk_id": decision.chunk_id,
                    "rank": decision.rank,
                    "score": decision.score,
                    "word_count": decision.word_count,
                    "status": decision.status,
                    "redundant_with": decision.redundant_with or None,
                    "max_similarity": decision.max_similarity,
                }
                for decision in selection.decisions
            ],
            "total_words": selection.total_words,
            "time_ms": elapsed,
        }

    def ask(
        self,
        question: str,
        *,
        mode: str = "approximate",
        ticker: str | None = None,
        fiscal_year: int | None = None,
        auto_filters: bool = True,
    ) -> dict[str, Any]:
        """Answer a question end to end and return every intermediate step."""
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        inferred = infer_filters(question) if auto_filters else {}
        filters = {
            "ticker": ticker if ticker is not None else inferred.get("ticker"),
            "fiscal_year": fiscal_year if fiscal_year is not None else inferred.get("fiscal_year"),
        }

        retrieval = self.retrieve(question, mode=mode, **filters)
        context = self.select(retrieval["results"])
        sources = context["selected"]

        if sources:
            messages = build_messages(question, sources)
            start = time.perf_counter()
            answer = normalize_citations(self.generator.generate(messages))
            generation_ms = (time.perf_counter() - start) * 1000
        else:
            messages = []
            answer = NO_CONTEXT_ANSWER
            generation_ms = 0.0

        return {
            "question": question,
            "mode": mode,
            "filters": filters,
            "inferred_filters": inferred,
            "retrieval": {
                "time_ms": retrieval["time_ms"],
                "candidate_count": retrieval["candidate_count"],
                "results": [
                    {
                        "chunk_id": result["chunk_id"],
                        "ticker": result.get("ticker"),
                        "fiscal_year": result.get("fiscal_year"),
                        "score": result["score"],
                    }
                    for result in retrieval["results"]
                ],
            },
            "context": {
                "selected": sources,
                "decisions": context["decisions"],
                "total_words": context["total_words"],
                "time_ms": context["time_ms"],
            },
            "messages": messages,
            "answer": answer,
            "cited_sources": cited_sources(answer, len(sources)),
            "model": self.generator.name,
            "generation_ms": generation_ms,
        }

    @staticmethod
    def _load_sources(path: Path | str) -> dict[str, dict[str, Any]]:
        """Original chunk text and citation metadata, keyed by chunk_id."""
        source_path = Path(path)
        try:
            payload = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"could not load source chunks from {source_path}: {error}") from error
        chunks = payload.get("chunks") if isinstance(payload, dict) else None
        if not isinstance(chunks, list):
            raise ValueError("source collection has no chunks array")
        sources: dict[str, dict[str, Any]] = {}
        for chunk in chunks:
            text = " ".join(str(chunk.get("text", "")).split())
            sources[chunk["chunk_id"]] = {
                "chunk_id": chunk["chunk_id"],
                "company": chunk.get("company"),
                "ticker": chunk.get("ticker"),
                "fiscal_year": chunk.get("fiscal_year"),
                "filing_date": chunk.get("filing_date"),
                "source_url": chunk.get("source_url"),
                "word_count": int(chunk.get("word_count") or len(text.split())),
                "text": text,
            }
        return sources
