"""Demonstrate KMP and Z-function exact search on real financial chunks."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.python.search_engine import (
    DEFAULT_COLLECTION,
    DEFAULT_VOCABULARY,
    SearchEngine,
)


def print_results(label: str, results: list[dict[str, Any]], limit: int = 5) -> None:
    print(f"{label}: {len(results)} returned chunks")
    for result in results[:limit]:
        print(
            f"  {result['chunk_id']} document={result['document_id']} "
            f"ticker={result['ticker']} fiscal_year={result['fiscal_year']} "
            f"score={result['score']} count={result['match_count']} "
            f"byte_offsets={result['match_byte_offsets']}"
        )
    if not results:
        print("  <no matches>")


def comparable(
    results: list[dict[str, Any]],
) -> list[tuple[str, int, int, list[int]]]:
    return [
        (
            result["chunk_id"],
            result["score"],
            result["match_count"],
            result["match_byte_offsets"],
        )
        for result in results
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run exact phrase searches through the bound C++ algorithms."
    )
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--collection", type=Path, default=DEFAULT_COLLECTION)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        engine = SearchEngine(args.vocabulary, args.collection)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Could not load search data: {error}")
        return 1

    phrase = "artificial intelligence"
    kmp_results = engine.exact_phrase_search(phrase, algorithm="kmp")
    z_results = engine.exact_phrase_search(phrase, algorithm="z")
    print_results("Ranked KMP: artificial intelligence", kmp_results)
    print()
    print_results("Ranked Z-function: artificial intelligence", z_results)
    print(
        "Identical rankings: "
        f"{comparable(kmp_results) == comparable(z_results)}"
    )
    print()

    top_five = engine.exact_phrase_search(phrase, algorithm="kmp", top_k=5)
    print_results("Top 5", top_five)
    print()
    print_results(
        "Ticker filter: NVDA",
        engine.exact_phrase_search(phrase, ticker="nvda", top_k=5),
    )
    print()
    print_results(
        "Fiscal-year filter: 2025",
        engine.exact_phrase_search(phrase, fiscal_year=2025, top_k=5),
    )
    print()
    print_results(
        "Combined filter: NVDA FY2025",
        engine.exact_phrase_search(
            phrase,
            algorithm="z",
            ticker="NVDA",
            fiscal_year=2025,
            top_k=5,
        ),
    )
    print()

    punctuation = engine.exact_phrase_search("$0.001", algorithm="kmp", top_k=5)
    print_results("Financial punctuation: $0.001", punctuation)
    print()
    print_results(
        "No match",
        engine.exact_phrase_search("definitely absent exact phrase", algorithm="z"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
