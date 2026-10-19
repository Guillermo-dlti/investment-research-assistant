"""Python interface to the bound C++ retrieval, exact, and fuzzy matching algorithms."""

from __future__ import annotations

import json
import time
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
# Dropped in approximate mode only. "may" and "us" are left out on purpose:
# in 10-K filings they can be content (the month May, U.S.).
STOPWORDS = frozenset(
    """
    a about after all also an and any are as at be been being but by can could
    did do does each for from had has have how i if in into is it its me might
    more most my no not of on or our so such than that the their them then there
    these they this those to was we were what when where which who whom whose
    why will with would you your
    """.split()
)
DEFAULT_ALPHA = 0.6


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
        return [self._correct_token(token) for token in normalize_query(query)]

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

    def approximate_search(
        self,
        query: str,
        *,
        ticker: str | None = None,
        fiscal_year: int | None = None,
        top_k: int | None = 10,
        alpha: float = DEFAULT_ALPHA,
    ) -> list[dict[str, Any]]:
        """Rank chunks that contain a corrected content word of the query.

        Stopwords are dropped, each remaining token is corrected with the C++
        Levenshtein matcher, and the OR candidates (after metadata filters)
        are reranked in C++ by ``alpha * coverage + (1 - alpha) * J / J_max``.
        A corrected term counts ``1 / (1 + distance)`` in coverage. Order is
        descending score, then ascending chunk ID.
        """
        self._validate_approximate_args(ticker, fiscal_year, top_k, alpha)
        results, _ = self._approximate(query, ticker, fiscal_year, top_k, alpha)
        return results

    def compare_search(
        self,
        query: str,
        *,
        ticker: str | None = None,
        fiscal_year: int | None = None,
        top_k: int | None = 10,
        alpha: float = DEFAULT_ALPHA,
    ) -> dict[str, Any]:
        """Run exact and approximate search on one question, with timings.

        The exact side is ranked AND search, falling back to ranked OR when
        AND finds nothing. Both sides apply the same filters before ``top_k``,
        and each ``candidate_count`` is the number of matches after filters.
        """
        self._validate_approximate_args(ticker, fiscal_year, top_k, alpha)
        if not normalize_query(query):
            return {
                "query": query,
                "terms": [],
                "stopword_fallback": False,
                "unmatched_terms": [],
                "exact": {"mode": "none", "results": [], "candidate_count": 0, "time_ms": 0.0},
                "approximate": {
                    "results": [],
                    "candidate_count": 0,
                    "time_ms": 0.0,
                    "steps_ms": {"correction": 0.0, "candidates": 0.0, "rerank": 0.0},
                },
                "shared_chunk_ids": [],
            }

        start = time.perf_counter()
        mode = "and"
        ranked = self.ranked_and_search(query)
        if not ranked:
            mode = "or"
            ranked = self.ranked_or_search(query)
        if not ranked:
            mode = "none"
        exact_matches = [
            {**result, "algorithm": "term_frequency"}
            for result in ranked
            if self._passes_filters(result, ticker, fiscal_year)
        ]
        exact_results = exact_matches if top_k is None else exact_matches[:top_k]
        exact_time = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        approximate_results, details = self._approximate(
            query, ticker, fiscal_year, top_k, alpha
        )
        approximate_time = (time.perf_counter() - start) * 1000

        shared = {result["chunk_id"] for result in exact_results} & {
            result["chunk_id"] for result in approximate_results
        }
        return {
            "query": query,
            "terms": details["terms"],
            "stopword_fallback": details["stopword_fallback"],
            "unmatched_terms": details["unmatched_terms"],
            "exact": {
                "mode": mode,
                "results": exact_results,
                "candidate_count": len(exact_matches),
                "time_ms": exact_time,
            },
            "approximate": {
                "results": approximate_results,
                "candidate_count": details["candidate_count"],
                "time_ms": approximate_time,
                "steps_ms": details["steps_ms"],
            },
            "shared_chunk_ids": sorted(shared),
        }

    def _approximate(
        self,
        query: str,
        ticker: str | None,
        fiscal_year: int | None,
        top_k: int | None,
        alpha: float,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Correct, gather OR candidates, and rerank them in C++."""
        start = time.perf_counter()
        tokens = normalize_query(query)
        content = [token for token in tokens if token not in STOPWORDS]
        stopword_fallback = bool(tokens) and not content
        if stopword_fallback:
            content = tokens

        records: list[dict[str, Any]] = []
        for token in content:
            record = self._correct_token(token)
            if not stopword_fallback and record["corrected"] in STOPWORDS:
                continue
            distance = record["distance"]
            record["weight"] = 1.0 if distance is None else 1.0 / (1 + distance)
            records.append(record)

        ngram_tokens = [record["corrected"] for record in records]
        weights: dict[str, float] = {}
        for record in records:
            word = record["corrected"]
            weights[word] = max(weights.get(word, 0.0), record["weight"])
        terms = [investment_engine.WeightedTerm(word, weight) for word, weight in weights.items()]
        correction_time = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        chunk_results: dict[str, dict[str, Any]] = {}
        for chunk_id in self.index.or_query(list(weights)):
            chunk_result = self._chunk_result(chunk_id)
            if self._passes_filters(chunk_result, ticker, fiscal_year):
                chunk_results[chunk_id] = chunk_result
        candidates_time = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        results = [
            {
                **chunk_results[ranked.chunk_id],
                "score": ranked.score,
                "coverage": ranked.coverage,
                "jaccard": ranked.jaccard,
                "jaccard_scaled": ranked.jaccard_scaled,
                "matched_terms": ranked.matched_terms,
                "algorithm": "approximate",
            }
            for ranked in investment_engine.rerank_candidates(
                self.index,
                self.jaccard_index,
                list(chunk_results),
                terms,
                ngram_tokens,
                float(alpha),
                top_k,
            )
        ]
        rerank_time = (time.perf_counter() - start) * 1000

        details = {
            "terms": records,
            "stopword_fallback": stopword_fallback,
            "unmatched_terms": [
                record["original"]
                for record in records
                if record["distance"] is None
                and not any(character.isdigit() for character in record["original"])
            ],
            "candidate_count": len(chunk_results),
            "steps_ms": {
                "correction": correction_time,
                "candidates": candidates_time,
                "rerank": rerank_time,
            },
        }
        return results, details

    def _correct_token(self, token: str) -> dict[str, Any]:
        if any(character.isdigit() for character in token):
            return {"original": token, "corrected": token, "distance": None}
        matches = self.fuzzy_matcher.match(token, 1, None)
        if matches:
            return {
                "original": token,
                "corrected": matches[0].word,
                "distance": matches[0].distance,
            }
        return {"original": token, "corrected": token, "distance": None}

    @staticmethod
    def _validate_approximate_args(
        ticker: str | None,
        fiscal_year: int | None,
        top_k: int | None,
        alpha: float,
    ) -> None:
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
        if not isinstance(alpha, (int, float)) or isinstance(alpha, bool):
            raise TypeError("alpha must be a number")
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be in [0, 1]")

    @staticmethod
    def _passes_filters(
        chunk_result: dict[str, Any],
        ticker: str | None,
        fiscal_year: int | None,
    ) -> bool:
        if ticker is not None and (
            chunk_result.get("ticker", "").casefold() != ticker.strip().casefold()
        ):
            return False
        return fiscal_year is None or chunk_result.get("fiscal_year") == fiscal_year

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
