"""Demonstrate Python access to the C++ Trie and inverted index."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.python.search_engine import (
    DEFAULT_COLLECTION,
    DEFAULT_VOCABULARY,
    SearchEngine,
)


def show_results(label: str, results: list[dict[str, Any]], limit: int = 5) -> None:
    print(f"{label} ({len(results)} matches):")
    for result in results[:limit]:
        details = [result["chunk_id"]]
        if "score" in result:
            details.append(f"score={result['score']}")
        details.append(f"ticker={result.get('ticker', '')}")
        details.append(f"fiscal_year={result.get('fiscal_year', '')}")
        print("  " + " ".join(details))
    if not results:
        print("  <no matches>")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run real-data searches through the bound C++ engine."
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

    print(f"Trie vocabulary tokens: {engine.vocabulary_size}")
    print(f"Inverted-index chunks: {engine.indexed_chunk_count}")
    print(f"Trie contains NVIDIA: {engine.contains_token('NVIDIA')}")
    print(f"Autocomplete 'nv': {engine.autocomplete('nv', 8)}")
    print()

    show_results("Single token: revenue", engine.single_token_search("Revenue"))
    print()
    show_results(
        "AND: artificial intelligence",
        engine.and_search("Artificial intelligence"),
    )
    print()
    show_results("OR: nvidia amd", engine.or_search("NVIDIA AMD"))
    print()
    show_results(
        "Ranked AND: artificial intelligence",
        engine.ranked_and_search("Artificial intelligence"),
    )
    print()
    show_results(
        "Ranked OR: nvidia amd",
        engine.ranked_or_search("NVIDIA AMD"),
    )
    print()
    show_results(
        "Missing token",
        engine.single_token_search("definitely-missing-token"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
