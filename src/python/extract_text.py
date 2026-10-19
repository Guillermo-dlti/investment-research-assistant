"""Extract readable text and metadata from SEC HTML financial filings."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

try:
    from .document_manifest import (
        DEFAULT_MANIFEST,
        DocumentRecord,
        load_manifest,
        select_documents,
    )
except ImportError:
    from document_manifest import (
        DEFAULT_MANIFEST,
        DocumentRecord,
        load_manifest,
        select_documents,
    )


DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_PROCESSED_DIR = Path("data/processed")
MINIMUM_EXTRACTED_WORDS = 5_000
MINIMUM_EXTRACTED_PARAGRAPHS = 100
PRIMARY_BLOCK_TAGS = {
    "address",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "p",
    "pre",
    "tr",
}
REMOVABLE_TAGS = {
    "head",
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "ix:header",
    "ix:hidden",
    "ix:references",
    "ix:resources",
}
LEGACY_METADATA: dict[str, Any] = {
    "document_id": "NVDA_2025_10K",
    "company": "NVIDIA Corporation",
    "ticker": "NVDA",
    "fiscal_year": 2025,
    "document_type": "10-K",
    "filing_date": "2025-02-26",
    "fiscal_year_end": "2025-01-26",
    "source_url": (
        "https://www.sec.gov/Archives/edgar/data/1045810/"
        "000104581025000023/nvda-20250126.htm"
    ),
}


def read_html(path: Path) -> bytes:
    """Read an HTML filing without assuming that its declaration is perfect."""
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"could not read {path}: {exc}") from exc
    if not content.strip():
        raise ValueError(f"input file is empty: {path}")
    return content


def normalize_text(value: str) -> str:
    """Normalize layout whitespace while retaining financial punctuation and values."""
    value = value.replace("\u00a0", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", value).strip()


def _is_hidden(tag: Tag) -> bool:
    style = re.sub(r"\s+", "", str(tag.get("style", "")).lower())
    return (
        tag.has_attr("hidden")
        or str(tag.get("aria-hidden", "")).lower() == "true"
        or "display:none" in style
        or "visibility:hidden" in style
    )


def _inside_named_ancestor(tag: Tag, names: set[str]) -> bool:
    return any(
        isinstance(parent, Tag) and parent.name in names for parent in tag.parents
    )


def _table_row_text(row: Tag) -> str:
    cells = row.find_all(["th", "td"], recursive=False)
    if not cells:
        cells = row.find_all(["th", "td"])
    values = [normalize_text(cell.get_text(" ", strip=True)) for cell in cells]
    return " | ".join(value for value in values if value)


def extract_paragraphs(content: bytes | str) -> list[str]:
    """Return readable semantic blocks, including financial table rows."""
    try:
        soup = BeautifulSoup(content, "html.parser")
    except Exception as exc:
        raise ValueError(f"BeautifulSoup could not parse the HTML: {exc}") from exc

    for tag in list(soup.find_all(REMOVABLE_TAGS)):
        tag.decompose()
    for tag in list(soup.find_all(_is_hidden)):
        if tag.parent is not None:
            tag.decompose()

    paragraphs: list[str] = []
    for tag in soup.find_all([*PRIMARY_BLOCK_TAGS, "div"]):
        if not isinstance(tag, Tag):
            continue
        if tag.name == "div":
            if _inside_named_ancestor(tag, PRIMARY_BLOCK_TAGS):
                continue
            if tag.find(PRIMARY_BLOCK_TAGS | {"div"}):
                continue
            text = normalize_text(tag.get_text(" ", strip=True))
        else:
            if _inside_named_ancestor(tag, PRIMARY_BLOCK_TAGS):
                continue
            text = (
                _table_row_text(tag)
                if tag.name == "tr"
                else normalize_text(tag.get_text(" ", strip=True))
            )
        if text:
            paragraphs.append(text)

    if not paragraphs:
        fallback = normalize_text(soup.get_text(" ", strip=True))
        if fallback:
            paragraphs.append(fallback)
    return paragraphs


def count_words(text: str) -> int:
    """Count human-readable word and number tokens in extracted text."""
    return len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", text, flags=re.UNICODE))


def build_document(
    paragraphs: list[str], metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build a structured document while preserving manifest metadata."""
    text = "\n\n".join(paragraphs)
    document_metadata = dict(metadata or LEGACY_METADATA)
    return {
        **document_metadata,
        "word_count": count_words(text),
        "character_count": len(text),
        "paragraphs": [
            {"paragraph_id": index, "text": paragraph}
            for index, paragraph in enumerate(paragraphs, start=1)
        ],
    }


def process_filing(
    input_path: Path,
    text_output: Path,
    json_output: Path,
    metadata: dict[str, Any] | None = None,
    require_substantial_filing: bool = True,
) -> dict[str, Any]:
    """Extract a filing and write UTF-8 text and JSON outputs."""
    paragraphs = extract_paragraphs(read_html(input_path))
    if not paragraphs:
        raise ValueError("no readable text was extracted from the filing")
    document = build_document(paragraphs, metadata)
    if require_substantial_filing:
        if document["word_count"] < MINIMUM_EXTRACTED_WORDS:
            raise ValueError(
                f"extraction produced only {document['word_count']:,} words; "
                "refusing to silently accept an incomplete Form 10-K"
            )
        if len(paragraphs) < MINIMUM_EXTRACTED_PARAGRAPHS:
            raise ValueError(
                f"extraction produced only {len(paragraphs):,} paragraphs; "
                "refusing to silently accept an incomplete Form 10-K"
            )

    text = "\n\n".join(paragraphs)
    text_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    text_output.write_text(f"{text}\n", encoding="utf-8")
    json_output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return document


def _existing_outputs_are_current(
    record: DocumentRecord, text_path: Path, json_path: Path
) -> bool:
    if not text_path.exists() or not json_path.exists():
        return False
    try:
        existing = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    metadata = record.metadata()
    return (
        isinstance(existing, dict)
        and all(existing.get(key) == value for key, value in metadata.items())
        and isinstance(existing.get("paragraphs"), list)
        and existing.get("word_count", 0) >= MINIMUM_EXTRACTED_WORDS
        and len(existing["paragraphs"]) >= MINIMUM_EXTRACTED_PARAGRAPHS
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract readable text from SEC Form 10-K HTML filings."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--document-id", help="extract one manifest document")
    selection.add_argument("--all", action="store_true", help="extract all documents")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        records = select_documents(
            load_manifest(args.manifest), args.document_id, args.all
        )
    except ValueError as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 2

    successes = 0
    for record in records:
        input_path = args.raw_dir / f"{record.file_stem}.html"
        text_path = args.processed_dir / f"{record.file_stem}.txt"
        json_path = args.processed_dir / f"{record.file_stem}.json"
        if not args.force and _existing_outputs_are_current(record, text_path, json_path):
            existing = json.loads(json_path.read_text(encoding="utf-8"))
            print(
                f"[OK] {record.document_id}: existing output "
                f"({existing['word_count']:,} words, {len(existing['paragraphs']):,} paragraphs)"
            )
            successes += 1
            continue
        try:
            document = process_filing(
                input_path, text_path, json_path, record.metadata()
            )
        except ValueError as exc:
            print(f"[FAILED] {record.document_id}: {exc}", file=sys.stderr)
            continue
        print(
            f"[OK] {record.document_id}: {document['word_count']:,} words, "
            f"{len(document['paragraphs']):,} paragraphs"
        )
        successes += 1

    print(f"Extraction summary: {successes}/{len(records)} successful")
    return 0 if successes == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
