"""Unit tests for strict consolidated collection construction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.python.build_collection import build_collection
from src.python.document_manifest import DocumentRecord


def make_record(identifier: str, ticker: str, year: int, stem: str) -> DocumentRecord:
    return DocumentRecord(
        document_id=identifier,
        company=f"Synthetic {ticker} Corporation",
        ticker=ticker,
        cik=f"{year:010d}",
        fiscal_year=year,
        document_type="10-K",
        fiscal_year_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-01",
        accession_number=f"{year:010d}-{str(year + 1)[-2:]}-000001",
        primary_document=f"{stem}.htm",
        source_url=f"https://www.sec.gov/Archives/{stem}.htm",
        file_stem=stem,
    )


def create_fixture(
    root: Path, records: list[DocumentRecord]
) -> tuple[Path, Path, dict[str, list[dict[str, object]]]]:
    chunk_dir = root / "chunks"
    processed_dir = root / "processed"
    chunk_dir.mkdir()
    processed_dir.mkdir()
    chunks_by_document: dict[str, list[dict[str, object]]] = {}

    for record_index, record in enumerate(records, start=1):
        paragraphs = [
            {
                "paragraph_id": 1,
                "text": f"Synthetic report {record_index} preserves $1,250 and 25%.",
            },
            {"paragraph_id": 2, "text": "A second factual test paragraph."},
        ]
        text = "\n\n".join(paragraph["text"] for paragraph in paragraphs)
        processed = {
            **record.metadata(),
            "word_count": 13,
            "character_count": len(text),
            "paragraphs": paragraphs,
        }
        chunks = [
            {
                "chunk_id": f"{record.document_id}_0001",
                "position": 1,
                **record.metadata(),
                "paragraph_start_id": 1,
                "paragraph_end_id": 1,
                "word_count": 8,
                "text": paragraphs[0]["text"],
            },
            {
                "chunk_id": f"{record.document_id}_0002",
                "position": 2,
                **record.metadata(),
                "paragraph_start_id": 2,
                "paragraph_end_id": 2,
                "word_count": 5,
                "text": paragraphs[1]["text"],
            },
        ]
        chunk_payload = {
            **record.metadata(),
            "word_count": processed["word_count"],
            "character_count": processed["character_count"],
            "chunk_size": 250,
            "overlap": 40,
            "total_chunks": len(chunks),
            "chunks": chunks,
        }
        (processed_dir / f"{record.file_stem}.json").write_text(
            json.dumps(processed), encoding="utf-8"
        )
        (chunk_dir / f"{record.file_stem}_chunks.json").write_text(
            json.dumps(chunk_payload), encoding="utf-8"
        )
        chunks_by_document[record.document_id] = chunks
    return chunk_dir, processed_dir, chunks_by_document


@pytest.fixture
def records() -> list[DocumentRecord]:
    return [
        make_record("AAA_2024_10K", "AAA", 2024, "aaa_2024"),
        make_record("BBB_2025_10K", "BBB", 2025, "bbb_2025"),
    ]


def test_successful_consolidation(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)

    collection, statistics = build_collection(records, chunk_dir, processed_dir)

    assert collection["complete"] is True
    assert collection["document_count"] == 2
    assert collection["company_count"] == 2
    assert collection["total_chunks"] == 4
    assert statistics["total_documents"] == 2


def test_missing_document_is_rejected(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)
    (chunk_dir / "bbb_2025_chunks.json").unlink()

    with pytest.raises(ValueError, match="required documents are missing"):
        build_collection(records, chunk_dir, processed_dir)


def test_duplicate_global_chunk_ids_are_rejected(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)
    second_path = chunk_dir / "bbb_2025_chunks.json"
    second = json.loads(second_path.read_text(encoding="utf-8"))
    second["chunks"][0]["chunk_id"] = "AAA_2024_10K_0001"
    second_path.write_text(json.dumps(second), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate global chunk_id"):
        build_collection(records, chunk_dir, processed_dir)


def test_missing_chunk_metadata_is_rejected(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)
    path = chunk_dir / "aaa_2024_chunks.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["chunks"][0]["source_url"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing metadata"):
        build_collection(records, chunk_dir, processed_dir)


def test_empty_chunk_text_is_rejected(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)
    path = chunk_dir / "aaa_2024_chunks.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["chunks"][0]["text"] = "   "
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="empty text"):
        build_collection(records, chunk_dir, processed_dir)


def test_invalid_json_is_rejected(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)
    (chunk_dir / "aaa_2024_chunks.json").write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON"):
        build_collection(records, chunk_dir, processed_dir)


def test_incorrect_declared_chunk_count_is_rejected(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)
    path = chunk_dir / "aaa_2024_chunks.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["total_chunks"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="chunk count mismatch"):
        build_collection(records, chunk_dir, processed_dir)


def test_output_order_is_deterministic_manifest_then_position(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)
    path = chunk_dir / "aaa_2024_chunks.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["chunks"].reverse()
    path.write_text(json.dumps(payload), encoding="utf-8")

    first, _ = build_collection(records, chunk_dir, processed_dir)
    second, _ = build_collection(records, chunk_dir, processed_dir)

    assert first == second
    assert [chunk["chunk_id"] for chunk in first["chunks"]] == [
        "AAA_2024_10K_0001",
        "AAA_2024_10K_0002",
        "BBB_2025_10K_0001",
        "BBB_2025_10K_0002",
    ]


def test_original_chunk_text_is_preserved_exactly(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, source_chunks = create_fixture(tmp_path, records)

    collection, _ = build_collection(records, chunk_dir, processed_dir)

    expected = source_chunks["AAA_2024_10K"][0]["text"]
    assert collection["chunks"][0]["text"] == expected
    assert "$1,250" in collection["chunks"][0]["text"]
    assert "25%" in collection["chunks"][0]["text"]


def test_generated_statistics_use_non_overlapping_document_totals(
    tmp_path: Path, records: list[DocumentRecord]
) -> None:
    chunk_dir, processed_dir, _ = create_fixture(tmp_path, records)

    _, statistics = build_collection(records, chunk_dir, processed_dir)

    assert statistics["total_extracted_words"] == 26
    assert statistics["total_extracted_paragraphs"] == 4
    assert statistics["total_chunk_tokens_with_overlap"] == 26
    assert statistics["minimum_chunk_size"] == 5
    assert statistics["maximum_chunk_size"] == 8
    assert statistics["average_chunks_per_document"] == 2.0
    assert statistics["raw_vocabulary_size_casefolded"] > 0
