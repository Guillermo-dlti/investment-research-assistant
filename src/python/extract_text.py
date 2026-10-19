"""Extract readable text and metadata from the NVIDIA FY2025 Form 10-K."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag


DEFAULT_INPUT = Path("data/raw/nvidia_2025.html")
DEFAULT_TEXT_OUTPUT = Path("data/processed/nvidia_2025.txt")
DEFAULT_JSON_OUTPUT = Path("data/processed/nvidia_2025.json")
SOURCE_URL = (
    "https://www.sec.gov/Archives/edgar/data/1045810/"
    "000104581025000023/nvda-20250126.htm"
)
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


def read_html(path: Path) -> bytes:
    """Read an HTML filing without assuming that its declaration is perfect."""
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Could not read {path}: {exc}") from exc
    if not content.strip():
        raise ValueError(f"Input file is empty: {path}")
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


def build_document(paragraphs: list[str]) -> dict[str, object]:
    """Build the required structured representation and actual text statistics."""
    text = "\n\n".join(paragraphs)
    return {
        "document_id": "NVDA_2025_10K",
        "company": "NVIDIA Corporation",
        "ticker": "NVDA",
        "fiscal_year": 2025,
        "document_type": "10-K",
        "filing_date": "2025-02-26",
        "fiscal_year_end": "2025-01-26",
        "source_url": SOURCE_URL,
        "word_count": count_words(text),
        "character_count": len(text),
        "paragraphs": [
            {"paragraph_id": index, "text": paragraph}
            for index, paragraph in enumerate(paragraphs, start=1)
        ],
    }


def process_filing(
    input_path: Path, text_output: Path, json_output: Path
) -> dict[str, object]:
    """Extract a filing and write UTF-8 text and JSON outputs."""
    paragraphs = extract_paragraphs(read_html(input_path))
    if not paragraphs:
        raise ValueError("No readable text was extracted from the filing.")

    document = build_document(paragraphs)
    text = "\n\n".join(paragraphs)
    text_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    text_output.write_text(f"{text}\n", encoding="utf-8")
    json_output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract readable text from NVIDIA's FY2025 Form 10-K HTML."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--text-output", type=Path, default=DEFAULT_TEXT_OUTPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        document = process_filing(args.input, args.text_output, args.json_output)
    except ValueError as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 1

    paragraphs = document["paragraphs"]
    sample = paragraphs[0]["text"][:300] if paragraphs else ""
    print(f"Extracted text: {args.text_output}")
    print(f"Structured metadata: {args.json_output}")
    print(f"Words: {document['word_count']:,}")
    print(f"Characters: {document['character_count']:,}")
    print(f"Paragraphs: {len(paragraphs):,}")
    print(f"Sample: {sample}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
