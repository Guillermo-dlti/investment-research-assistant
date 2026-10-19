"""Tests for the multi-document SEC filing collection pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from src.python.chunk_documents import chunk_document
from src.python.document_manifest import DEFAULT_MANIFEST, DocumentRecord, load_manifest
from src.python.download_documents import download_filing, validate_filing
from src.python.extract_text import build_document, process_filing


class MockResponse:
    def __init__(self, content: bytes, status: int = 200) -> None:
        self.content = content
        self.status = status

    def __enter__(self) -> "MockResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def getcode(self) -> int:
        return self.status

    def read(self) -> bytes:
        return self.content


def valid_html(record: DocumentRecord) -> bytes:
    body = (
        f"<html><body><h1>{record.company}</h1><p>FORM {record.document_type}</p>"
        f"<p>Fiscal year ended {record.fiscal_year_end}</p>"
        f"<p>{'financial reporting text ' * 6_000}</p></body></html>"
    )
    return body.encode("utf-8")


def test_official_manifest_contains_two_fiscal_years_for_five_companies() -> None:
    records = load_manifest(DEFAULT_MANIFEST)

    assert len(records) == 10
    assert {(record.ticker, record.fiscal_year) for record in records} == {
        (ticker, year)
        for ticker in ("NVDA", "AMD", "MSFT", "AAPL", "GOOGL")
        for year in (2024, 2025)
    }
    assert all(record.source_url.startswith("https://www.sec.gov/Archives/") for record in records)


def test_manifest_rejects_fiscal_year_mismatch(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    payload["documents"][0]["fiscal_year"] = 2023
    path = tmp_path / "invalid_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="fiscal year does not match"):
        load_manifest(path)


def test_download_uses_mocked_http_and_contact_user_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = load_manifest(DEFAULT_MANIFEST)[0]
    observed: dict[str, object] = {}

    def opener(request: object, timeout: float) -> MockResponse:
        observed["user_agent"] = request.get_header("User-agent")
        observed["url"] = request.full_url
        observed["timeout"] = timeout
        return MockResponse(valid_html(record))

    monkeypatch.setenv("SEC_CONTACT_EMAIL", "student@university.edu")
    output = tmp_path / "filing.html"
    result = download_filing(record, output, 12.0, False, opener=opener)

    assert result.success and result.requested
    assert output.read_bytes() == valid_html(record)
    assert observed["url"] == record.source_url
    assert observed["timeout"] == 12.0
    assert "student@university.edu" in str(observed["user_agent"])


def test_download_handles_mocked_rate_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = load_manifest(DEFAULT_MANIFEST)[0]

    def opener(request: object, timeout: float) -> MockResponse:
        raise HTTPError(record.source_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setenv("SEC_CONTACT_EMAIL", "student@university.edu")
    result = download_filing(record, tmp_path / "filing.html", 10.0, False, opener)

    assert not result.success
    assert result.requested
    assert "429" in result.status


def test_validation_rejects_a_different_manifest_filing() -> None:
    records = load_manifest(DEFAULT_MANIFEST)
    nvidia = next(record for record in records if record.document_id == "NVDA_2024_10K")
    apple = next(record for record in records if record.document_id == "AAPL_2024_10K")

    valid, _ = validate_filing(valid_html(nvidia), nvidia)
    mismatched, reason = validate_filing(valid_html(nvidia), apple)

    assert valid
    assert not mismatched
    assert "Apple" in reason


def test_multi_document_extraction_preserves_manifest_metadata(tmp_path: Path) -> None:
    records = load_manifest(DEFAULT_MANIFEST)[:2]
    sample_html = b"""
        <html><body><h1>Business</h1>
        <p>Revenue increased 25% to $1,250 million.</p>
        <h2>Risk Factors</h2><p>Competition may affect results.</p>
        </body></html>
    """

    for record in records:
        input_path = tmp_path / f"{record.file_stem}.html"
        text_path = tmp_path / f"{record.file_stem}.txt"
        json_path = tmp_path / f"{record.file_stem}.json"
        input_path.write_bytes(sample_html)
        document = process_filing(
            input_path,
            text_path,
            json_path,
            record.metadata(),
            require_substantial_filing=False,
        )

        assert document["document_id"] == record.document_id
        assert document["accession_number"] == record.accession_number
        assert document["fiscal_year_end"] == record.fiscal_year_end
        assert "$1,250" in text_path.read_text(encoding="utf-8")
        assert json.loads(json_path.read_text(encoding="utf-8"))["ticker"] == record.ticker


def test_manifest_metadata_produces_consistent_chunks() -> None:
    record = load_manifest(DEFAULT_MANIFEST)[2]
    paragraphs = [
        " ".join(f"word{offset + number}" for number in range(100)) + "."
        for offset in (0, 100, 200)
    ]
    document = build_document(paragraphs, record.metadata())

    first = chunk_document(document, 120, 20)
    second = chunk_document(document, 120, 20)

    assert first == second
    assert first["chunks"][0]["chunk_id"] == "AMD_2024_10K_0001"
    assert all(chunk["accession_number"] == record.accession_number for chunk in first["chunks"])
