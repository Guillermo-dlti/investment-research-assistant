"""Python interface to the bound C++ retrieval, exact, and fuzzy matching algorithms."""

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
        self.fuzzy_matcher = investment_engine.load_fuzzy_matcher(str(vocabulary_path))
        self.index = investment_engine.load_inverted_index(str(collection_path))
        self.jaccard_index = investment_engine.load_jaccard_index(str(collection_path))
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

    def fuzzy_terms(
        self,
        word: str,
        *,
        max_distance: int | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return vocabulary words within a Levenshtein distance of ``word``.

        Ordered by distance, then corpus frequency, then word. An exact
        vocabulary hit returns only itself at distance 0.
        """
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be non-negative")
        if limit < 0:
            raise ValueError("limit must be non-negative")
        token = normalize_single_token(word)
        return [
            {
                "word": match.word,
                "distance": match.distance,
                "frequency": match.frequency,
            }
            for match in self.fuzzy_matcher.match(token, limit, max_distance)
        ]

    def correct_query(self, query: str) -> list[dict[str, Any]]:
        """Map each query token to its closest vocabulary word.

        Tokens containing digits are kept as typed, because a near-miss number
        such as ``$97,858`` vs ``$97,868`` is a different fact, not a typo.
        Tokens with no vocabulary word within the cutoff are kept unchanged
        with ``distance`` set to ``None``.
        """
        corrections: list[dict[str, Any]] = []
        for token in normalize_query(query):
            if any(character.isdigit() for character in token):
                corrections.append({"original": token, "corrected": token, "distance": None})
                continue
            matches = self.fuzzy_matcher.match(token, 1, None)
            if matches:
                corrections.append(
                    {
                        "original": token,
                        "corrected": matches[0].word,
                        "distance": matches[0].distance,
                    }
                )
            else:
                corrections.append({"original": token, "corrected": token, "distance": None})
        return corrections

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
        ticker: str | None = None,
        fiscal_year: int | None = None,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find and rank an exact normalized phrase with a bound C++ matcher.

        Results use byte offsets into each chunk's stored ``normalized_text``.
        Token-boundary mode accepts matches spanning complete tokenizer tokens.
        Candidate filtering is used only when that mode and the normalized query
        make an AND-index lookup provably safe; all other cases scan every chunk.
        Metadata filters run before matching. Results rank by descending exact
        occurrence count and then ascending chunk ID before ``top_k`` is applied.
        """
        if not isinstance(algorithm, str):
            raise TypeError("algorithm must be a string")
        selected = EXACT_ALGORITHMS.get(algorithm.casefold())
        if selected is None:
            raise ValueError("algorithm must be 'kmp' or 'z'")
        if ticker is not None and not isinstance(ticker, str):
            raise TypeError("ticker must be a string or None")
        if fiscal_year is not None and (
            not isinstance(fiscal_year, int) or isinstance(fiscal_year, bool)
        ):
            raise TypeError("fiscal_year must be an integer or None")
        if top_k is not None and (
            not isinstance(top_k, int) or isinstance(top_k, bool)
        ):
            raise TypeError("top_k must be a non-negative integer or None")
        if top_k is not None and top_k < 0:
            raise ValueError("top_k must be non-negative")
        if top_k == 0:
            return []

        algorithm_name, matcher = selected
        pattern = normalize_text(query)
        if not pattern:
            return []
        normalized_ticker = ticker.strip().casefold() if ticker is not None else None

        tokens = tokenize(pattern, already_normalized=True)
        can_filter = token_boundaries and bool(tokens) and pattern == " ".join(tokens)
        if can_filter:
            candidate_ids = self.index.and_query(list(dict.fromkeys(tokens)))
        else:
            candidate_ids = sorted(self._normalized_chunks)

        pattern_size = len(pattern.encode("utf-8"))
        results: list[dict[str, Any]] = []
        for chunk_id in candidate_ids:
            chunk_result = self._chunk_result(chunk_id)
            if normalized_ticker is not None and (
                chunk_result.get("ticker", "").casefold() != normalized_ticker
            ):
                continue
            if (
                fiscal_year is not None
                and chunk_result.get("fiscal_year") != fiscal_year
            ):
                continue

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
                score = len(offsets)
                results.append(
                    {
                        **chunk_result,
                        "match_count": score,
                        "match_byte_offsets": offsets,
                        "algorithm": algorithm_name,
                        "score": score,
                    }
                )
        results.sort(key=lambda result: (-result["score"], result["chunk_id"]))
        return results if top_k is None else results[:top_k]

    def jaccard_search(
        self,
        query: str,
        *,
        ticker: str | None = None,
        fiscal_year: int | None = None,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Rank chunks by Jaccard similarity of word 1-2 gram sets.

        Every chunk is compared with the query in C++; chunks sharing no
        n-gram are omitted. Metadata filters run after ranking and before
        ``top_k``. Order is descending score, then ascending chunk ID.
        """
        if top_k is not None and (
            not isinstance(top_k, int) or isinstance(top_k, bool)
        ):
            raise TypeError("top_k must be a non-negative integer or None")
        if top_k is not None and top_k < 0:
            raise ValueError("top_k must be non-negative")
        if top_k == 0:
            return []
        normalized_ticker = ticker.strip().casefold() if ticker is not None else None

        results: list[dict[str, Any]] = []
        for ranked in self.jaccard_index.rank(normalize_query(query)):
            chunk_result = self._chunk_result(ranked.chunk_id)
            if normalized_ticker is not None and (
                chunk_result.get("ticker", "").casefold() != normalized_ticker
            ):
                continue
            if (
                fiscal_year is not None
                and chunk_result.get("fiscal_year") != fiscal_year
            ):
                continue
            results.append(
                {
                    **chunk_result,
                    "score": ranked.score,
                    "shared_ngrams": ranked.shared_ngrams,
                    "union_size": ranked.union_size,
                    "algorithm": "jaccard",
                }
            )
            if top_k is not None and len(results) == top_k:
                break
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
