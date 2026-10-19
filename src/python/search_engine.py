"""Python interface to the bound C++ retrieval and exact-matching algorithms."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import investment_engine

from src.python.preprocess_text import TOKEN_PATTERN, normalize_text, tokenize


DEFAULT_VOCABULARY = Path("data/metadata/vocabulary.json")
DEFAULT_COLLECTION = Path("data/processed/preprocessed_collection.json")
EXACT_ALGORITHMS = {
    "kmp": ("kmp", investment_engine.kmp_search),
    "z": ("z", investment_engine.z_search),
    "z-function": ("z", investment_engine.z_search),
    "z_function": ("z", investment_engine.z_search),
}


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
        self._normalized_chunks = self._load_normalized_chunks(collection_path)

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

    def exact_phrase_search(
        self,
        query: str,
        *,
        algorithm: str = "kmp",
        token_boundaries: bool = True,
    ) -> list[dict[str, Any]]:
        """Find an exact normalized phrase with a bound C++ matcher.

        Results use byte offsets into each chunk's stored ``normalized_text``.
        Token-boundary mode accepts matches spanning complete tokenizer tokens.
        Candidate filtering is used only when that mode and the normalized query
        make an AND-index lookup provably safe; all other cases scan every chunk.
        """
        if not isinstance(algorithm, str):
            raise TypeError("algorithm must be a string")
        selected = EXACT_ALGORITHMS.get(algorithm.casefold())
        if selected is None:
            raise ValueError("algorithm must be 'kmp' or 'z'")
        algorithm_name, matcher = selected
        pattern = normalize_text(query)
        if not pattern:
            return []

        tokens = tokenize(pattern, already_normalized=True)
        can_filter = token_boundaries and bool(tokens) and pattern == " ".join(tokens)
        if can_filter:
            candidate_ids = self.index.and_query(list(dict.fromkeys(tokens)))
        else:
            candidate_ids = sorted(self._normalized_chunks)

        pattern_size = len(pattern.encode("utf-8"))
        results: list[dict[str, Any]] = []
        for chunk_id in candidate_ids:
            text = self._normalized_chunks[chunk_id]
            offsets = list(matcher(text, pattern))
            if token_boundaries and offsets:
                starts, ends = self._token_boundaries(text)
                offsets = [
                    offset
                    for offset in offsets
                    if offset in starts and offset + pattern_size in ends
                ]
            if offsets:
                results.append(
                    {
                        **self._chunk_result(chunk_id),
                        "match_count": len(offsets),
                        "match_byte_offsets": offsets,
                        "algorithm": algorithm_name,
                    }
                )
        return results

    def _chunk_result(self, chunk_id: str) -> dict[str, Any]:
        metadata = self.index.get_metadata(chunk_id) or {}
        return {"chunk_id": chunk_id, **metadata}

    def _ranked_results(self, results: list[Any]) -> list[dict[str, Any]]:
        return [
            {**self._chunk_result(result.chunk_id), "score": result.score}
            for result in results
        ]

    @staticmethod
    def _load_normalized_chunks(collection_path: Path | str) -> dict[str, str]:
        path = Path(collection_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"could not load normalized chunks from {path}: {error}"
            ) from error
        chunks = payload.get("chunks") if isinstance(payload, dict) else None
        if not isinstance(chunks, list) or payload.get("total_chunks") != len(chunks):
            raise ValueError("preprocessed collection has an invalid chunks array")
        normalized_chunks: dict[str, str] = {}
        for chunk in chunks:
            if not isinstance(chunk, dict):
                raise ValueError("preprocessed collection contains a non-object chunk")
            chunk_id = chunk.get("chunk_id")
            normalized_text = chunk.get("normalized_text")
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError("preprocessed collection contains an invalid chunk_id")
            if chunk_id in normalized_chunks:
                raise ValueError(f"duplicate chunk_id: {chunk_id}")
            if not isinstance(normalized_text, str):
                raise ValueError(f"chunk {chunk_id} has no normalized_text")
            normalized_chunks[chunk_id] = normalized_text
        return normalized_chunks

    @staticmethod
    def _token_boundaries(text: str) -> tuple[set[int], set[int]]:
        byte_positions = [0]
        for character in text:
            byte_positions.append(
                byte_positions[-1] + len(character.encode("utf-8"))
            )
        starts: set[int] = set()
        ends: set[int] = set()
        for match in TOKEN_PATTERN.finditer(text):
            starts.add(byte_positions[match.start()])
            ends.add(byte_positions[match.end()])
        return starts, ends
