"""Load and validate the tracked SEC filing manifest."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_MANIFEST = Path("config/document_manifest.json")
REQUIRED_FIELDS = (
    "document_id",
    "company",
    "ticker",
    "cik",
    "fiscal_year",
    "document_type",
    "fiscal_year_end",
    "filing_date",
    "accession_number",
    "primary_document",
    "source_url",
    "file_stem",
)


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    company: str
    ticker: str
    cik: str
    fiscal_year: int
    document_type: str
    fiscal_year_end: str
    filing_date: str
    accession_number: str
    primary_document: str
    source_url: str
    file_stem: str

    def metadata(self) -> dict[str, Any]:
        return asdict(self) | {"source_url": self.source_url}


def _validate_record(raw: object, position: int) -> DocumentRecord:
    if not isinstance(raw, dict):
        raise ValueError(f"manifest document {position} must be a JSON object")
    missing = [field for field in REQUIRED_FIELDS if raw.get(field) in (None, "")]
    if missing:
        raise ValueError(
            f"manifest document {position} is missing: {', '.join(missing)}"
        )
    unexpected = set(raw) - set(REQUIRED_FIELDS)
    if unexpected:
        raise ValueError(
            f"manifest document {position} has unsupported fields: "
            f"{', '.join(sorted(unexpected))}"
        )
    if not isinstance(raw["fiscal_year"], int) or isinstance(raw["fiscal_year"], bool):
        raise ValueError(f"manifest document {position} has an invalid fiscal_year")
    if not re.fullmatch(r"\d{10}", str(raw["cik"])):
        raise ValueError(f"manifest document {position} has an invalid 10-digit CIK")
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(raw["accession_number"])):
        raise ValueError(f"manifest document {position} has an invalid accession number")
    for field in ("fiscal_year_end", "filing_date"):
        try:
            date.fromisoformat(str(raw[field]))
        except ValueError as exc:
            raise ValueError(
                f"manifest document {position} has an invalid {field}"
            ) from exc
    if int(str(raw["fiscal_year_end"])[:4]) != raw["fiscal_year"]:
        raise ValueError(
            f"manifest document {position} fiscal year does not match its period end"
        )
    if raw["document_type"] != "10-K":
        raise ValueError(f"manifest document {position} must be a Form 10-K")
    if not re.fullmatch(r"[a-z0-9_]+", str(raw["file_stem"])):
        raise ValueError(f"manifest document {position} has an unsafe file_stem")

    parsed = urlparse(str(raw["source_url"]))
    accession_compact = str(raw["accession_number"]).replace("-", "")
    expected_path = (
        f"/Archives/edgar/data/{int(str(raw['cik']))}/"
        f"{accession_compact}/{raw['primary_document']}"
    )
    if parsed.scheme != "https" or parsed.netloc != "www.sec.gov" or parsed.path != expected_path:
        raise ValueError(
            f"manifest document {position} source_url does not match its SEC identifiers"
        )

    return DocumentRecord(**{field: raw[field] for field in REQUIRED_FIELDS})


def load_manifest(path: Path = DEFAULT_MANIFEST) -> list[DocumentRecord]:
    """Read a manifest and return validated, uniquely identified records."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"manifest does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"manifest is not valid JSON: {path} "
            f"(line {exc.lineno}, column {exc.colno})"
        ) from exc
    except OSError as exc:
        raise ValueError(f"could not read manifest {path}: {exc}") from exc

    if not isinstance(payload, dict) or payload.get("manifest_version") != 1:
        raise ValueError("manifest must be an object with manifest_version 1")
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise ValueError("manifest must contain a non-empty documents array")

    records = [
        _validate_record(raw, position)
        for position, raw in enumerate(raw_documents, start=1)
    ]
    for attribute in ("document_id", "source_url", "file_stem"):
        values = [getattr(record, attribute) for record in records]
        if len(values) != len(set(values)):
            raise ValueError(f"manifest contains duplicate {attribute} values")
    return records


def select_documents(
    records: list[DocumentRecord], document_id: str | None, all_documents: bool
) -> list[DocumentRecord]:
    if all_documents:
        return records
    selected_id = document_id or "NVDA_2025_10K"
    matches = [record for record in records if record.document_id == selected_id]
    if not matches:
        raise ValueError(f"document_id is not present in the manifest: {selected_id}")
    return matches
