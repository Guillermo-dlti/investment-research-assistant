"""Convenient Python interface to the bound C++ Trie and inverted index."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import investment_engine

from src.python.preprocess_text import normalize_text, tokenize


DEFAULT_VOCABULARY = Path("data/metadata/vocabulary.json")
DEFAULT_COLLECTION = Path("data/processed/preprocessed_collection.json")


def normalize_query(query: str) -> list[str]:
    """Tokenize a user query with the existing Step 9 normalization policy."""
    return tokenize(query)


def normalize_single_token(value: str) -> str:
    """Normalize a value that must produce exactly one complete token."""
    tokens = normalize_query(value)
    if len(tokens) != 1:
        raise ValueError("query must normalize to exactly one token")
    return tokens[0]


class SearchEngine:
    """Load real processed files into and query the existing C++ components."""

    def __init__(
        self,
        vocabulary_path: Path | str = DEFAULT_VOCABULARY,
        collection_path: Path | str = DEFAULT_COLLECTION,
    ) -> None:
        self.trie = investment_engine.load_trie(str(vocabulary_path))
        self.index = investment_engine.load_inverted_index(str(collection_path))

    @property
    def vocabulary_size(self) -> int:
        return self.trie.size

    @property
    def indexed_chunk_count(self) -> int:
        return self.index.chunk_count

    def contains_token(self, value: str) -> bool:
        return self.trie.search(normalize_single_token(value))

    def autocomplete(self, prefix: str, k: int = 10) -> list[str]:
        if k < 0:
            raise ValueError("k must be non-negative")
        return self.trie.autocomplete(normalize_text(prefix), k)

    def single_token_search(self, query: str) -> list[dict[str, Any]]:
        token = normalize_single_token(query)
        return [self._chunk_result(chunk_id) for chunk_id in self.index.lookup(token)]

    def and_search(self, query: str) -> list[dict[str, Any]]:
        tokens = normalize_query(query)
        return [
            self._chunk_result(chunk_id)
            for chunk_id in self.index.and_query(tokens)
        ]

    def or_search(self, query: str) -> list[dict[str, Any]]:
        tokens = normalize_query(query)
        return [
            self._chunk_result(chunk_id)
            for chunk_id in self.index.or_query(tokens)
        ]

    def ranked_and_search(self, query: str) -> list[dict[str, Any]]:
        return self._ranked_results(self.index.ranked_and(normalize_query(query)))

    def ranked_or_search(self, query: str) -> list[dict[str, Any]]:
        return self._ranked_results(self.index.ranked_or(normalize_query(query)))

    def _chunk_result(self, chunk_id: str) -> dict[str, Any]:
        metadata = self.index.get_metadata(chunk_id) or {}
        return {"chunk_id": chunk_id, **metadata}

    def _ranked_results(self, results: list[Any]) -> list[dict[str, Any]]:
        return [
            {**self._chunk_result(result.chunk_id), "score": result.score}
            for result in results
        ]
