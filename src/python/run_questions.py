"""Run the Stage 5 question set end to end and save the evidence under reports/."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.python.research_assistant import (
    DEFAULT_MODEL,
    DEFAULT_SOURCE_COLLECTION,
    HuggingFaceGenerator,
    ResearchAssistant,
)
from src.python.search_engine import DEFAULT_COLLECTION, DEFAULT_VOCABULARY


# (question, note). Notes mark the cases picked to show weak retrieval.
QUESTIONS = [
    ("What was NVIDIA data center revenue in fiscal 2025?", ""),
    ("How much did NVIDIA spend on research and development in fiscal 2024?", ""),
    ("Who does NVIDIA consider its main competitors?", ""),
    ("nvidea gaming revenue", "typo in the company name"),
    ("What risks does AMD describe about export restrictions to China?", ""),
    ("How does AMD describe its data center segment?", ""),
    ("What does AMD say about the acquisition of ZT Systems?", ""),
    ("How much did Microsoft Azure and other cloud services revenue grow in fiscal 2025?", ""),
    ("What does Microsoft say about its investments in artificial intelligence?", ""),
    ("microsft cloud revenue", "typo in the company name"),
    ("What does Apple say about iPhone net sales in fiscal 2025?", ""),
    ("How does Apple describe its services revenue?", ""),
    ("How many employees does Apple have?", "the filing says 'the Company', not 'Apple'"),
    ("What risks does Apple describe about manufacturing in China?", ""),
    ("What are Alphabet's main sources of revenue?", ""),
    ("What does Google say about YouTube advertising revenue?", ""),
    ("What legal or antitrust matters does Alphabet describe?", ""),
    ("Which companies depend on TSMC to manufacture their chips?", "no company filter, cross filing"),
    ("What is Tesla revenue from electric vehicles?", "out of corpus: no Tesla filing"),
    ("What is the outlook?", "vague question"),
    ("How did share repurchases change in fiscal 2025?", "fiscal year filter but no company"),
]
DEFAULT_JSON = Path("reports/stage5_results.json")
DEFAULT_MARKDOWN = Path("reports/stage5_results.md")
EXCERPT_WORDS = 60


def compact(result: dict[str, Any], note: str) -> dict[str, Any]:
    """Drop the raw prompt and keep what the report needs."""
    return {
        "note": note,
        **{key: value for key, value in result.items() if key != "messages"},
    }


def excerpt(text: str) -> str:
    words = text.split()
    return " ".join(words[:EXCERPT_WORDS]) + (" ..." if len(words) > EXCERPT_WORDS else "")


def to_markdown(entries: list[dict[str, Any]], settings: dict[str, Any]) -> str:
    lines = [
        "# Stage 5 results: questions answered from selected filing chunks",
        "",
        f"Model `{settings['model']}` (greedy decoding), {settings['mode']} retrieval, "
        f"top {settings['retrieval_top_k']} candidates, at most {settings['max_chunks']} chunks "
        f"and {settings['word_budget']} words of context, chunks with Jaccard "
        f">= {settings['redundancy_threshold']} against a kept chunk dropped as redundant.",
        "Times are milliseconds on an Apple M4 Pro. Retrieval time covers search only; "
        "selection and generation are listed separately.",
        "",
        "## Summary",
        "",
        "| # | Question | Filters | Retrieval ms | Candidates | Selected | Cited | Generation ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for number, entry in enumerate(entries, 1):
        filters = ", ".join(
            f"{key}={value}" for key, value in entry["filters"].items() if value is not None
        ) or "none"
        cited = ", ".join(f"[{n}]" for n in entry["cited_sources"]) or "none"
        lines.append(
            f"| {number} | {entry['question']} | {filters} | {entry['retrieval']['time_ms']:.2f} "
            f"| {entry['retrieval']['candidate_count']} | {len(entry['context']['selected'])} "
            f"| {cited} | {entry['generation_ms']:.0f} |"
        )
    for number, entry in enumerate(entries, 1):
        lines += ["", f"## {number}. {entry['question']}", ""]
        if entry["note"]:
            lines += [f"*Why this question:* {entry['note']}.", ""]
        filters = entry["filters"]
        lines += [
            f"- Filters: ticker `{filters['ticker']}`, fiscal year `{filters['fiscal_year']}`",
            f"- Retrieval: {entry['retrieval']['time_ms']:.2f} ms, "
            f"{entry['retrieval']['candidate_count']} candidate chunks; "
            f"selection {entry['context']['time_ms']:.3f} ms, "
            f"{entry['context']['total_words']} words selected",
            "- Selection decisions: "
            + (", ".join(
                f"{d['chunk_id']} {d['status']}"
                + (f" (copy of {d['redundant_with']}, J={d['max_similarity']:.2f})" if d["redundant_with"] else "")
                for d in entry["context"]["decisions"]
            ) or "no candidates"),
            "",
            "**Selected context**",
            "",
        ]
        for index, source in enumerate(entry["context"]["selected"], 1):
            lines.append(
                f"{index}. `{source['chunk_id']}`, {source['company']} FY{source['fiscal_year']}, "
                f"score {source['score']:.3f}: \"{excerpt(source['text'])}\""
            )
        if not entry["context"]["selected"]:
            lines.append("None.")
        lines += [
            "",
            f"**Answer** ({entry['generation_ms']:.0f} ms)",
            "",
            "> " + entry["answer"].replace("\n", "\n> "),
        ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Answer the Stage 5 question set.")
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--collection", type=Path, default=DEFAULT_COLLECTION)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCE_COLLECTION)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--mode", choices=("approximate", "exact"), default="approximate")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assistant = ResearchAssistant(
        args.vocabulary,
        args.collection,
        args.sources,
        generator=HuggingFaceGenerator(args.model),
    )
    settings = {
        "model": args.model,
        "mode": args.mode,
        "retrieval_top_k": assistant.retrieval_top_k,
        "max_chunks": assistant.max_chunks,
        "word_budget": assistant.word_budget,
        "redundancy_threshold": assistant.redundancy_threshold,
    }
    # Load the model before timing anything, so question 1 is not penalized.
    assistant.generator.load()

    entries = []
    for number, (question, note) in enumerate(QUESTIONS, 1):
        result = assistant.ask(question, mode=args.mode)
        entries.append(compact(result, note))
        print(
            f"{number:2}. {question}\n    retrieval {result['retrieval']['time_ms']:.2f} ms, "
            f"{len(result['context']['selected'])} chunks, generation "
            f"{result['generation_ms']:.0f} ms\n    {result['answer'][:160]}"
        )

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps({"settings": settings, "results": entries}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(to_markdown(entries, settings), encoding="utf-8")
    print(f"Wrote {args.json} and {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
