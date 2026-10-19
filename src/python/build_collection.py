"""Consolidate validated document chunks and produce Stage 1 statistics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .document_manifest import (
        DEFAULT_MANIFEST,
        DocumentRecord,
        load_manifest,
    )
except ImportError:
    from document_manifest import DEFAULT_MANIFEST, DocumentRecord, load_manifest


DEFAULT_CHUNK_DIR = Path("data/chunks")
DEFAULT_PROCESSED_DIR = Path("data/processed")
DEFAULT_COLLECTION_OUTPUT = DEFAULT_CHUNK_DIR / "collection.json"
DEFAULT_STATISTICS_OUTPUT = Path("data/metadata/collection_statistics.json")
REQUIRED_CHUNK_FIELDS = (
    "chunk_id",
    "document_id",
    "company",
    "ticker",
    "fiscal_year",
    "document_type",
    "filing_date",
    "source_url",
    "position",
    "word_count",
    "text",
)
MANIFEST_CHUNK_FIELDS = (
    "document_id",
    "company",
    "ticker",
    "fiscal_year",
    "document_type",
    "filing_date",
    "fiscal_year_end",
    "source_url",
)
VOCABULARY_PATTERN = re.compile(
    r"\b[\w]+(?:[’'-][\w]+)*\b", flags=re.UNICODE
)


def read_json_object(path: Path, description: str) -> dict[str, Any]:
    """Read a UTF-8 JSON object and raise a contextual validation error."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing {description}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in {description} {path} "
            f"(line {exc.lineno}, column {exc.colno})"
        ) from exc
    except OSError as exc:
        raise ValueError(f"could not read {description} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{description} must contain a JSON object: {path}")
    return payload


def _validate_manifest_metadata(
    payload: dict[str, Any], record: DocumentRecord, description: str
) -> None:
    for field in MANIFEST_CHUNK_FIELDS:
        expected = getattr(record, field)
        if payload.get(field) != expected:
            raise ValueError(
                f"{description} has incorrect {field!r} for {record.document_id}: "
                f"expected {expected!r}, found {payload.get(field)!r}"
            )


def _validate_processed_document(
    payload: dict[str, Any], record: DocumentRecord
) -> dict[str, int]:
    _validate_manifest_metadata(payload, record, "processed document")
    word_count = payload.get("word_count")
    character_count = payload.get("character_count")
    paragraphs = payload.get("paragraphs")
    if not isinstance(word_count, int) or isinstance(word_count, bool) or word_count <= 0:
        raise ValueError(f"processed document {record.document_id} has invalid word_count")
    if (
        not isinstance(character_count, int)
        or isinstance(character_count, bool)
        or character_count <= 0
    ):
        raise ValueError(
            f"processed document {record.document_id} has invalid character_count"
        )
    if not isinstance(paragraphs, list) or not paragraphs:
        raise ValueError(f"processed document {record.document_id} has no paragraphs")
    for position, paragraph in enumerate(paragraphs, start=1):
        if (
            not isinstance(paragraph, dict)
            or not isinstance(paragraph.get("text"), str)
            or not paragraph["text"].strip()
        ):
            raise ValueError(
                f"processed document {record.document_id} has invalid paragraph {position}"
            )
    return {
        "extracted_word_count": word_count,
        "extracted_character_count": character_count,
        "extracted_paragraph_count": len(paragraphs),
    }


def _validate_chunk_file(
    payload: dict[str, Any], record: DocumentRecord
) -> list[dict[str, Any]]:
    _validate_manifest_metadata(payload, record, "chunk file")
    chunks = payload.get("chunks")
    declared_count = payload.get("total_chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError(f"chunk file {record.document_id} contains no chunks")
    if declared_count != len(chunks):
        raise ValueError(
            f"chunk count mismatch for {record.document_id}: "
            f"declared {declared_count!r}, found {len(chunks)}"
        )

    validated: list[dict[str, Any]] = []
    positions: set[int] = set()
    for source_position, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            raise ValueError(
                f"chunk {source_position} in {record.document_id} is not an object"
            )
        missing = [
            field for field in REQUIRED_CHUNK_FIELDS if field not in chunk
        ]
        if missing:
            raise ValueError(
                f"chunk {source_position} in {record.document_id} is missing metadata: "
                f"{', '.join(missing)}"
            )
        _validate_manifest_metadata(chunk, record, f"chunk {chunk.get('chunk_id')}")
        if not isinstance(chunk["chunk_id"], str) or not chunk["chunk_id"].strip():
            raise ValueError(f"chunk {source_position} has an invalid chunk_id")
        if (
            not isinstance(chunk["position"], int)
            or isinstance(chunk["position"], bool)
            or chunk["position"] <= 0
        ):
            raise ValueError(f"chunk {chunk['chunk_id']} has an invalid position")
        if chunk["position"] in positions:
            raise ValueError(
                f"duplicate chunk position {chunk['position']} in {record.document_id}"
            )
        positions.add(chunk["position"])
        if (
            not isinstance(chunk["word_count"], int)
            or isinstance(chunk["word_count"], bool)
            or chunk["word_count"] <= 0
        ):
            raise ValueError(f"chunk {chunk['chunk_id']} has an invalid word_count")
        if not isinstance(chunk["text"], str) or not chunk["text"].strip():
            raise ValueError(f"chunk {chunk['chunk_id']} has empty text")
        validated.append(chunk)

    expected_positions = set(range(1, len(validated) + 1))
    if positions != expected_positions:
        raise ValueError(
            f"chunk positions for {record.document_id} must be consecutive from 1"
        )
    return sorted(validated, key=lambda chunk: chunk["position"])


def _document_vocabulary(processed: dict[str, Any]) -> set[str]:
    vocabulary: set[str] = set()
    for paragraph in processed["paragraphs"]:
        vocabulary.update(
            token.casefold() for token in VOCABULARY_PATTERN.findall(paragraph["text"])
        )
    return vocabulary


def build_collection(
    records: list[DocumentRecord], chunk_dir: Path, processed_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate every manifest document and return collection plus statistics."""
    if not records:
        raise ValueError("manifest contains no documents")
    missing_files: list[str] = []
    for record in records:
        chunk_path = chunk_dir / f"{record.file_stem}_chunks.json"
        processed_path = processed_dir / f"{record.file_stem}.json"
        if not chunk_path.exists():
            missing_files.append(f"{record.document_id} chunks ({chunk_path})")
        if not processed_path.exists():
            missing_files.append(f"{record.document_id} processed data ({processed_path})")
    if missing_files:
        raise ValueError("required documents are missing: " + "; ".join(missing_files))

    all_chunks: list[dict[str, Any]] = []
    chunk_ids: set[str] = set()
    collection_vocabulary: set[str] = set()
    document_statistics: list[dict[str, Any]] = []
    document_summaries: list[dict[str, Any]] = []

    for record in records:
        chunk_path = chunk_dir / f"{record.file_stem}_chunks.json"
        processed_path = processed_dir / f"{record.file_stem}.json"
        chunk_payload = read_json_object(chunk_path, "chunk file")
        processed_payload = read_json_object(processed_path, "processed document")
        processed_counts = _validate_processed_document(processed_payload, record)
        chunks = _validate_chunk_file(chunk_payload, record)

        root_word_count = chunk_payload.get("word_count")
        root_character_count = chunk_payload.get("character_count")
        if root_word_count != processed_counts["extracted_word_count"]:
            raise ValueError(
                f"extracted word count mismatch for {record.document_id}"
            )
        if root_character_count != processed_counts["extracted_character_count"]:
            raise ValueError(
                f"extracted character count mismatch for {record.document_id}"
            )

        for chunk in chunks:
            if chunk["chunk_id"] in chunk_ids:
                raise ValueError(f"duplicate global chunk_id: {chunk['chunk_id']}")
            chunk_ids.add(chunk["chunk_id"])
            all_chunks.append(dict(chunk))

        chunk_sizes = [chunk["word_count"] for chunk in chunks]
        vocabulary = _document_vocabulary(processed_payload)
        collection_vocabulary.update(vocabulary)
        stats = {
            "document_id": record.document_id,
            "company": record.company,
            "ticker": record.ticker,
            "fiscal_year": record.fiscal_year,
            **processed_counts,
            "chunk_count": len(chunks),
            "chunk_tokens_with_overlap": sum(chunk_sizes),
            "minimum_chunk_size": min(chunk_sizes),
            "maximum_chunk_size": max(chunk_sizes),
            "average_chunk_size": round(sum(chunk_sizes) / len(chunk_sizes), 2),
            "raw_vocabulary_size_casefolded": len(vocabulary),
        }
        document_statistics.append(stats)
        document_summaries.append(
            {
                **record.metadata(),
                "chunk_count": len(chunks),
                "chunk_file": str(chunk_path),
            }
        )

    if len(all_chunks) != sum(item["chunk_count"] for item in document_statistics):
        raise ValueError("consolidated chunk total does not match document chunk totals")

    total_chunk_tokens = sum(chunk["word_count"] for chunk in all_chunks)
    collection = {
        "collection_version": 1,
        "complete": True,
        "document_count": len(records),
        "company_count": len({record.ticker for record in records}),
        "total_chunks": len(all_chunks),
        "documents": document_summaries,
        "chunks": all_chunks,
    }
    statistics = {
        "collection_version": 1,
        "complete": True,
        "counting_methodology": {
            "extracted_document_counts": (
                "Sums of word_count, character_count, and paragraph counts from the "
                "non-overlapping processed document JSON files."
            ),
            "chunk_counts": (
                "Chunk word_count values use the chunker's whitespace-delimited token "
                "method. Their sum includes the configured overlap and is not used as "
                "the original collection word count."
            ),
            "raw_vocabulary": (
                "Unique case-folded Unicode word and number tokens from processed "
                "paragraphs; punctuation is not included in vocabulary tokens."
            ),
        },
        "total_documents": len(records),
        "total_companies": len({record.ticker for record in records}),
        "total_chunks": len(all_chunks),
        "total_extracted_words": sum(
            item["extracted_word_count"] for item in document_statistics
        ),
        "total_extracted_characters": sum(
            item["extracted_character_count"] for item in document_statistics
        ),
        "total_extracted_paragraphs": sum(
            item["extracted_paragraph_count"] for item in document_statistics
        ),
        "average_chunks_per_document": round(len(all_chunks) / len(records), 2),
        "minimum_chunk_size": min(chunk["word_count"] for chunk in all_chunks),
        "maximum_chunk_size": max(chunk["word_count"] for chunk in all_chunks),
        "average_chunk_size": round(total_chunk_tokens / len(all_chunks), 2),
        "total_chunk_tokens_with_overlap": total_chunk_tokens,
        "raw_vocabulary_size_casefolded": len(collection_vocabulary),
        "documents": document_statistics,
    }
    return collection, statistics


def write_json(payload: dict[str, Any], path: Path) -> None:
    """Write deterministic, human-readable UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and validate the consolidated Stage 1 document collection."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--chunk-dir", type=Path, default=DEFAULT_CHUNK_DIR)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_COLLECTION_OUTPUT
    )
    parser.add_argument(
        "--statistics-output", type=Path, default=DEFAULT_STATISTICS_OUTPUT
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        records = load_manifest(args.manifest)
        collection, statistics = build_collection(
            records, args.chunk_dir, args.processed_dir
        )
        write_json(collection, args.output)
        write_json(statistics, args.statistics_output)
    except ValueError as exc:
        print(f"Collection build failed: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Collection build failed while writing output: {exc}", file=sys.stderr)
        return 1

    print(
        f"Built complete collection: {collection['document_count']} documents, "
        f"{collection['company_count']} companies, {collection['total_chunks']:,} chunks"
    )
    print(f"Collection: {args.output}")
    print(f"Statistics: {args.statistics_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
