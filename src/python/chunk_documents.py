"""Split extracted financial documents into overlapping, metadata-rich chunks."""

from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .document_manifest import DEFAULT_MANIFEST, load_manifest, select_documents
except ImportError:
    from document_manifest import DEFAULT_MANIFEST, load_manifest, select_documents


DEFAULT_INPUT = Path("data/processed/nvidia_2025.json")
DEFAULT_OUTPUT = Path("data/chunks/nvidia_2025_chunks.json")
DEFAULT_PROCESSED_DIR = Path("data/processed")
DEFAULT_CHUNKS_DIR = Path("data/chunks")
DEFAULT_CHUNK_SIZE = 250
DEFAULT_OVERLAP = 40
# Count whitespace-delimited tokens that contain at least one letter or number.
# Matching the complete token prevents splits inside values such as "$97,858".
WORD_PATTERN = re.compile(r"(?<!\S)(?=\S*[\w])\S+", flags=re.UNICODE)
SENTENCE_END_PATTERN = re.compile(r"[.!?][\"')\]]*(?:\s+|$)")
REQUIRED_METADATA = (
    "document_id",
    "company",
    "ticker",
    "fiscal_year",
    "document_type",
    "filing_date",
    "source_url",
)


@dataclass(frozen=True)
class PreparedDocument:
    """Text plus source-position information used during chunk construction."""

    text: str
    word_matches: tuple[re.Match[str], ...]
    word_paragraph_ids: tuple[Any, ...]
    preferred_boundaries: tuple[int, ...]


def validate_parameters(chunk_size: int, overlap: int) -> None:
    """Validate chunking parameters before processing document content."""
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk size must be a positive integer")
    if isinstance(overlap, bool) or not isinstance(overlap, int) or overlap < 0:
        raise ValueError("overlap must be a non-negative integer")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk size")


def load_document(path: Path) -> dict[str, Any]:
    """Load and validate an extracted-document JSON file."""
    try:
        with path.open(encoding="utf-8") as source:
            document = json.load(source)
    except FileNotFoundError as exc:
        raise ValueError(f"input file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"input file is not valid JSON: {path} "
            f"(line {exc.lineno}, column {exc.colno})"
        ) from exc
    except OSError as exc:
        raise ValueError(f"could not read input file {path}: {exc}") from exc

    if not isinstance(document, dict):
        raise ValueError("input JSON must contain an object at the top level")
    missing = [
        field
        for field in REQUIRED_METADATA
        if field not in document or document[field] in (None, "")
    ]
    if missing:
        raise ValueError(f"missing required metadata: {', '.join(missing)}")
    if not isinstance(document.get("paragraphs"), list):
        raise ValueError("input JSON must contain a 'paragraphs' array")
    return document


def _clean_paragraphs(document: dict[str, Any]) -> list[tuple[Any, str]]:
    paragraphs: list[tuple[Any, str]] = []
    for position, paragraph in enumerate(document["paragraphs"], start=1):
        if not isinstance(paragraph, dict):
            raise ValueError(f"paragraph {position} must be a JSON object")
        text = paragraph.get("text")
        if not isinstance(text, str):
            raise ValueError(f"paragraph {position} must contain a string 'text' field")
        text = text.strip()
        if text:
            paragraphs.append((paragraph.get("paragraph_id", position), text))
    if not paragraphs:
        raise ValueError("document contains no readable paragraph text")
    return paragraphs


def _word_boundary_at(character_offset: int, word_ends: list[int]) -> int:
    return bisect.bisect_right(word_ends, character_offset)


def prepare_document(document: dict[str, Any]) -> PreparedDocument:
    """Create a continuous text view while retaining paragraph provenance."""
    paragraphs = _clean_paragraphs(document)
    parts: list[str] = []
    paragraph_spans: list[tuple[int, int, Any, str]] = []
    cursor = 0

    for paragraph_id, paragraph_text in paragraphs:
        if parts:
            parts.append("\n\n")
            cursor += 2
        start = cursor
        parts.append(paragraph_text)
        cursor += len(paragraph_text)
        paragraph_spans.append((start, cursor, paragraph_id, paragraph_text))

    text = "".join(parts)
    word_matches = tuple(WORD_PATTERN.finditer(text))
    if not word_matches:
        raise ValueError("document contains no countable words")
    word_ends = [match.end() for match in word_matches]

    paragraph_ids: list[Any] = []
    span_index = 0
    for match in word_matches:
        while (
            span_index + 1 < len(paragraph_spans)
            and match.start() >= paragraph_spans[span_index][1]
        ):
            span_index += 1
        paragraph_ids.append(paragraph_spans[span_index][2])

    boundaries: set[int] = set()
    for start, end, _paragraph_id, paragraph_text in paragraph_spans:
        boundaries.add(_word_boundary_at(end, word_ends))
        for sentence_end in SENTENCE_END_PATTERN.finditer(paragraph_text):
            absolute_end = start + sentence_end.end()
            boundary = _word_boundary_at(absolute_end, word_ends)
            if boundary:
                boundaries.add(boundary)

    return PreparedDocument(
        text=text,
        word_matches=word_matches,
        word_paragraph_ids=tuple(paragraph_ids),
        preferred_boundaries=tuple(sorted(boundaries)),
    )


def _chunk_end(prepared: PreparedDocument, start: int, chunk_size: int, overlap: int) -> int:
    total_words = len(prepared.word_matches)
    ideal_end = min(start + chunk_size, total_words)
    if ideal_end == total_words:
        return total_words

    minimum_useful_size = max(overlap + 1, int(chunk_size * 0.6))
    minimum_end = start + minimum_useful_size
    boundary_position = bisect.bisect_right(prepared.preferred_boundaries, ideal_end)
    if boundary_position:
        candidate = prepared.preferred_boundaries[boundary_position - 1]
        if candidate >= minimum_end:
            return candidate
    return ideal_end


def _slice_text(prepared: PreparedDocument, start: int, end: int) -> str:
    character_start = prepared.word_matches[start].start()
    character_end = prepared.word_matches[end - 1].end()
    return prepared.text[character_start:character_end].strip()


def chunk_document(
    document: dict[str, Any], chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP
) -> dict[str, Any]:
    """Return deterministic overlapping chunks for one extracted document."""
    validate_parameters(chunk_size, overlap)
    missing = [field for field in REQUIRED_METADATA if document.get(field) in (None, "")]
    if missing:
        raise ValueError(f"missing required metadata: {', '.join(missing)}")
    if not isinstance(document.get("paragraphs"), list):
        raise ValueError("input document must contain a 'paragraphs' array")

    prepared = prepare_document(document)
    metadata_for_chunks = {
        key: value
        for key, value in document.items()
        if key not in {"paragraphs", "word_count", "character_count"}
        and isinstance(value, (str, int, float, bool, type(None)))
    }

    chunks: list[dict[str, Any]] = []
    start = 0
    total_words = len(prepared.word_matches)
    while start < total_words:
        end = _chunk_end(prepared, start, chunk_size, overlap)
        text = _slice_text(prepared, start, end)
        if not text:
            raise ValueError("chunking produced an empty chunk")

        position = len(chunks) + 1
        chunk = {
            "chunk_id": f"{document['document_id']}_{position:04d}",
            "position": position,
            **metadata_for_chunks,
            "paragraph_start_id": prepared.word_paragraph_ids[start],
            "paragraph_end_id": prepared.word_paragraph_ids[end - 1],
            "word_count": len(WORD_PATTERN.findall(text)),
            "text": text,
        }
        chunks.append(chunk)

        if end == total_words:
            break
        next_start = end - overlap
        if next_start <= start:
            raise ValueError("chunking parameters did not allow forward progress")
        start = next_start

    source_metadata = {key: value for key, value in document.items() if key != "paragraphs"}
    return {
        **source_metadata,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "total_chunks": len(chunks),
        "chunks": chunks,
    }


def write_chunks(document: dict[str, Any], output_path: Path) -> None:
    """Write chunk data as human-readable UTF-8 JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split an extracted financial document into overlapping chunks."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--document-id", help="chunk one manifest document")
    selection.add_argument("--all", action="store_true", help="chunk all documents")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--chunks-dir", type=Path, default=DEFAULT_CHUNKS_DIR)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_parameters(args.chunk_size, args.overlap)
    except ValueError as exc:
        print(f"Chunking failed: {exc}", file=sys.stderr)
        return 2

    jobs: list[tuple[str, Path, Path]]
    if args.all or args.document_id:
        try:
            records = select_documents(
                load_manifest(args.manifest), args.document_id, args.all
            )
        except ValueError as exc:
            print(f"Chunking failed: {exc}", file=sys.stderr)
            return 2
        jobs = [
            (
                record.document_id,
                args.processed_dir / f"{record.file_stem}.json",
                args.chunks_dir / f"{record.file_stem}_chunks.json",
            )
            for record in records
        ]
    else:
        jobs = [("input document", args.input, args.output)]

    successes = 0
    for label, input_path, output_path in jobs:
        try:
            source_document = load_document(input_path)
            result = chunk_document(source_document, args.chunk_size, args.overlap)
            write_chunks(result, output_path)
        except ValueError as exc:
            print(f"[FAILED] {label}: {exc}", file=sys.stderr)
            continue
        except OSError as exc:
            print(f"[FAILED] {label}: could not write {output_path}: {exc}", file=sys.stderr)
            continue
        sizes = [chunk["word_count"] for chunk in result["chunks"]]
        print(
            f"[OK] {result['document_id']}: {result['total_chunks']:,} chunks "
            f"(min={min(sizes)}, max={max(sizes)}, "
            f"average={sum(sizes) / len(sizes):.2f})"
        )
        successes += 1
    print(f"Chunking summary: {successes}/{len(jobs)} successful")
    return 0 if successes == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
