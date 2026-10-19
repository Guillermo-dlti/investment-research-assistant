"""Compare exact and approximate search on the three Stage 4 report questions."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path
from typing import Any

from src.python.search_engine import (
    DEFAULT_COLLECTION,
    DEFAULT_VOCABULARY,
    SearchEngine,
)


QUESTIONS = [
    "nvidea data center revenue",
    "data center revenue",
    "what risks come from export restrictions",
]
TOP_K = 5
TIMING_RUNS = 5


def print_ranking(
    engine: SearchEngine, label: str, side: dict[str, Any], excerpt_chars: int
) -> None:
    print(f"  {label}: {side['candidate_count']} candidate chunks")
    for rank, result in enumerate(side["results"], 1):
        details = f"score={result['score']:.4f}"
        if result["algorithm"] == "approximate":
            details += (
                f" coverage={result['coverage']:.3f}"
                f" jaccard={result['jaccard']:.4f}"
                f" scaled={result['jaccard_scaled']:.3f}"
            )
        print(
            f"    {rank}. {result['chunk_id']} {result['ticker']} "
            f"FY{result['fiscal_year']} {details}"
        )
        if excerpt_chars:
            text = engine._normalized_chunks[result["chunk_id"]][:excerpt_chars]
            print(f"       \"{text}...\"")
    if not side["results"]:
        print("    <no matches>")


def median_timings(engine: SearchEngine, question: str) -> dict[str, float]:
    engine.compare_search(question, top_k=TOP_K)  # warm up
    runs = [engine.compare_search(question, top_k=TOP_K) for _ in range(TIMING_RUNS)]
    timings = {
        "exact": [run["exact"]["time_ms"] for run in runs],
        "approximate": [run["approximate"]["time_ms"] for run in runs],
    }
    for step in ("correction", "candidates", "rerank"):
        timings[step] = [run["approximate"]["steps_ms"][step] for run in runs]
    return {name: statistics.median(values) for name, values in timings.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare exact and approximate rankings with timings."
    )
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--collection", type=Path, default=DEFAULT_COLLECTION)
    parser.add_argument("--excerpt", type=int, default=0, help="characters of chunk text to show")
    parser.add_argument("questions", nargs="*", default=QUESTIONS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        engine = SearchEngine(args.vocabulary, args.collection)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Could not load search data: {error}")
        return 1

    print(f"Chunks: {engine.indexed_chunk_count}, top {TOP_K}, alpha 0.6")
    print(f"Timings: median of {TIMING_RUNS} runs after one warm up run, in ms\n")
    for question in args.questions:
        report = engine.compare_search(question, top_k=TOP_K)
        print(f"Question: {question}")
        terms = ", ".join(
            f"{term['original']}->{term['corrected']} (d={term['distance']}, w={term['weight']:.2f})"
            for term in report["terms"]
        )
        print(f"  content terms: {terms or '<none>'}")
        print(f"  stopword fallback: {report['stopword_fallback']}")
        print(f"  exact mode: {report['exact']['mode']}")
        print_ranking(engine, "Exact (term frequency)", report["exact"], args.excerpt)
        print_ranking(engine, "Approximate (coverage + scaled Jaccard)", report["approximate"], args.excerpt)
        print(f"  shared in both top {TOP_K}: {report['shared_chunk_ids'] or '<none>'}")
        timings = median_timings(engine, question)
        print(
            f"  time: exact {timings['exact']:.3f} ms, approximate {timings['approximate']:.3f} ms "
            f"(correction {timings['correction']:.3f}, candidates {timings['candidates']:.3f}, "
            f"rerank {timings['rerank']:.3f})"
        )
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
