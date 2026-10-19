"""Normalize and tokenize consolidated financial-document chunks."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


DEFAULT_INPUT = Path("data/chunks/collection.json")
DEFAULT_OUTPUT = Path("data/processed/preprocessed_collection.json")
DEFAULT_VOCABULARY = Path("data/metadata/vocabulary.json")
REQUIRED_CHUNK_FIELDS = (
    "chunk_id",
    "document_id",
    "ticker",
    "fiscal_year",
    "text",
)
PRESERVED_FIELDS = (
    "chunk_id",
    "document_id",
    "position",
    "company",
    "ticker",
    "fiscal_year",
    "document_type",
    "filing_date",
    "fiscal_year_end",
    "source_url",
    "paragraph_start_id",
    "paragraph_end_id",
)
APOSTROPHE_TRANSLATION = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
DASH_TRANSLATION = str.maketrans(
    {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-"}
)
TOKEN_PATTERN = re.compile(
    r"""
    (?<!\w)
    (?:
        -?[$€£¥](?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?
        | [^\W_]+(?:['-][^\W_]+)+
        | [+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?
        | (?:[^\W_]+\.){2,}
        | [^\W_]+(?:&[^\W_]+)+
        | [^\W_]+
    )
    (?!\w)
    """,
    flags=re.UNICODE | re.VERBOSE,
)


def normalization_policy() -> dict[str, Any]:
    """Return machine-readable documentation for deterministic normalization."""
    return {
        "unicode_form": "NFKC",
        "case_normalization": "casefold",
        "apostrophes": "Unicode apostrophe variants are mapped to ASCII apostrophe.",
        "dashes": "Unicode dash and minus variants are mapped to ASCII hyphen.",
        "whitespace": "All whitespace runs are collapsed to one ASCII space.",
        "accent_removal": False,
        "stopword_removal": False,
        "stemming": False,
        "lemmatization": False,
    }


def tokenization_policy() -> dict[str, Any]:
    """Return the explicit token policy stored with the vocabulary."""
    return {
        "method": "deterministic Python regular expression over normalized text",
        "ordinary_words": "Unicode letter/number words are individual tokens.",
        "monetary_values": "Currency symbol and numeric amount remain one token.",
        "numbers": "Signs, thousands separators, decimal points, and percent signs are retained.",
        "hyphenated_words": "Hyphenated compounds remain one token.",
        "possessives": "Apostrophe compounds such as nvidia's remain one token.",
        "ampersand_terms": "Terms such as s&p remain one token; adjacent numbers are separate.",
        "abbreviations": "Multi-period abbreviations such as u.s. remain one token.",
        "examples": {
            "NVIDIA": ["nvidia"],
            "NVDA": ["nvda"],
            "$97,858": ["$97,858"],
            "12.5%": ["12.5%"],
            "S&P 500": ["s&p", "500"],
            "AI-powered": ["ai-powered"],
            "year-over-year": ["year-over-year"],
            "NVIDIA's": ["nvidia's"],
        },
    }


def normalize_unicode(text: str) -> str:
    """Apply compatibility normalization and punctuation canonicalization."""
    normalized = unicodedata.normalize("NFKC", text)
    return normalized.translate(APOSTROPHE_TRANSLATION).translate(DASH_TRANSLATION)


def normalize_text(text: str) -> str:
    """Return deterministic case-folded text with normalized whitespace."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    normalized = normalize_unicode(text).casefold()
    return " ".join(normalized.split())


def tokenize(text: str, *, already_normalized: bool = False) -> list[str]:
    """Tokenize financial and ordinary English expressions without information loss."""
    normalized = text if already_normalized else normalize_text(text)
    return [match.group(0) for match in TOKEN_PATTERN.finditer(normalized)]


def count_token_frequencies(token_sequences: Iterable[Iterable[str]]) -> Counter[str]:
    """Count token occurrences across any iterable of token sequences."""
    frequencies: Counter[str] = Counter()
    for tokens in token_sequences:
        frequencies.update(tokens)
    return frequencies


def load_collection(path: Path) -> dict[str, Any]:
    """Load and validate the consolidated collection container."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"input collection does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"input collection is not valid JSON: {path} "
            f"(line {exc.lineno}, column {exc.colno})"
        ) from exc
    except OSError as exc:
        raise ValueError(f"could not read input collection {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("input collection must contain a JSON object")
    chunks = payload.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("input collection must contain a non-empty chunks array")
    if payload.get("total_chunks") != len(chunks):
        raise ValueError(
            "input collection total_chunks does not match the chunks array length"
        )
    return payload


def preprocess_collection(
    collection: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize every chunk and build a deterministic vocabulary."""
    chunks = collection.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("collection must contain a non-empty chunks array")
    if collection.get("total_chunks") != len(chunks):
        raise ValueError("collection chunk count does not match total_chunks")

    seen_ids: set[str] = set()
    records: list[dict[str, Any]] = []
    frequencies: Counter[str] = Counter()
    for position, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            raise ValueError(f"chunk {position} must be a JSON object")
        missing = [
            field
            for field in REQUIRED_CHUNK_FIELDS
            if field not in chunk or chunk[field] is None
        ]
        if missing:
            raise ValueError(
                f"chunk {position} is missing required metadata: {', '.join(missing)}"
            )
        chunk_id = chunk["chunk_id"]
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError(f"chunk {position} has an invalid chunk_id")
        if chunk_id in seen_ids:
            raise ValueError(f"duplicate chunk_id: {chunk_id}")
        seen_ids.add(chunk_id)
        if not isinstance(chunk["document_id"], str) or not chunk["document_id"]:
            raise ValueError(f"chunk {chunk_id} has an invalid document_id")
        if not isinstance(chunk["ticker"], str) or not chunk["ticker"]:
            raise ValueError(f"chunk {chunk_id} has an invalid ticker")
        if (
            not isinstance(chunk["fiscal_year"], int)
            or isinstance(chunk["fiscal_year"], bool)
        ):
            raise ValueError(f"chunk {chunk_id} has an invalid fiscal_year")
        if not isinstance(chunk["text"], str) or not chunk["text"].strip():
            raise ValueError(f"chunk {chunk_id} has empty text")

        normalized = normalize_text(chunk["text"])
        tokens = tokenize(normalized, already_normalized=True)
        if not tokens:
            raise ValueError(f"chunk {chunk_id} produced no tokens")
        frequencies.update(tokens)
        metadata = {
            field: chunk[field] for field in PRESERVED_FIELDS if field in chunk
        }
        records.append(
            {
                **metadata,
                "normalized_text": normalized,
                "tokens": tokens,
                "token_count": len(tokens),
            }
        )

    normalization = normalization_policy()
    tokenization = tokenization_policy()
    preprocessed = {
        "preprocessing_version": 1,
        "source_collection_version": collection.get("collection_version"),
        "total_chunks": len(records),
        "normalization_policy": normalization,
        "tokenization_policy": tokenization,
        "chunks": records,
    }
    vocabulary_entries = [
        {"token": token, "frequency": frequencies[token]}
        for token in sorted(frequencies)
    ]
    vocabulary = {
        "vocabulary_version": 1,
        "processed_chunks": len(records),
        "total_token_occurrences": sum(frequencies.values()),
        "unique_tokens": len(frequencies),
        "normalization_policy": normalization,
        "tokenization_policy": tokenization,
        "token_frequencies": vocabulary_entries,
    }
    return preprocessed, vocabulary


def write_json(payload: dict[str, Any], path: Path) -> None:
    """Write deterministic, human-readable UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize and tokenize the consolidated chunk collection."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        collection = load_collection(args.input)
        preprocessed, vocabulary = preprocess_collection(collection)
        write_json(preprocessed, args.output)
        write_json(vocabulary, args.vocabulary)
    except ValueError as exc:
        print(f"Preprocessing failed: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Preprocessing failed while writing output: {exc}", file=sys.stderr)
        return 1

    print(
        f"Preprocessed {preprocessed['total_chunks']:,} chunks with "
        f"{vocabulary['total_token_occurrences']:,} token occurrences and "
        f"{vocabulary['unique_tokens']:,} unique tokens"
    )
    print(f"Preprocessed collection: {args.output}")
    print(f"Vocabulary: {args.vocabulary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
