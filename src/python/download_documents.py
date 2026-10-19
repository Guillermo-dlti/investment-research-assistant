"""Download verified Form 10-K filings from the SEC document manifest."""

from __future__ import annotations

import argparse
import html
import os
import re
import socket
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_REQUEST_DELAY_SECONDS = 0.15
MINIMUM_EXPECTED_BYTES = 100_000
OpenFunction = Callable[..., object]


@dataclass(frozen=True)
class DownloadResult:
    document_id: str
    success: bool
    status: str
    requested: bool


def build_user_agent() -> str:
    """Build an SEC-compatible User-Agent using user-supplied contact details."""
    email = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if not _is_plausible_contact_email(email):
        raise ValueError(
            "SEC_CONTACT_EMAIL must contain a real contact email address. "
            "Example: export SEC_CONTACT_EMAIL='your_address@university.edu'"
        )
    description = os.environ.get(
        "SEC_USER_AGENT", "InvestmentResearchAssistant/1.0"
    ).strip() or "InvestmentResearchAssistant/1.0"
    if email.lower() not in description.lower():
        description = f"{description} ({email})"
    return description


def _is_plausible_contact_email(value: str) -> bool:
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        return False
    domain = value.rsplit("@", 1)[1].lower()
    return domain not in {"example.com", "example.org", "example.net", "localhost"}


def validate_filing(content: bytes, document: DocumentRecord) -> tuple[bool, str]:
    """Check that content resembles the specific manifest filing."""
    if len(content) < MINIMUM_EXPECTED_BYTES:
        return False, f"content is unexpectedly small ({len(content):,} bytes)"
    decoded = html.unescape(content.decode("utf-8", errors="replace"))
    normalized = " ".join(decoded.lower().split())
    error_markers = (
        "your request originates from an undeclared automated tool",
        "request rate threshold exceeded",
        "access denied",
    )
    if any(marker in normalized for marker in error_markers):
        return False, "response appears to be an SEC access or error page"
    if "<html" not in normalized:
        return False, "response does not appear to be HTML"
    company_terms = [term for term in re.findall(r"[a-z0-9]+", document.company.lower()) if len(term) > 2]
    if not company_terms or not all(term in normalized for term in company_terms):
        return False, f"{document.company} was not identified in the response"
    if document.document_type.lower() not in normalized:
        return False, f"Form {document.document_type} was not identified in the response"
    period = date.fromisoformat(document.fiscal_year_end)
    period_markers = (
        document.fiscal_year_end,
        document.fiscal_year_end.replace("-", ""),
        f"{period.strftime('%B')} {period.day}, {period.year}".lower(),
    )
    if not any(marker in normalized for marker in period_markers):
        return False, f"fiscal year end {document.fiscal_year_end} was not identified"
    return True, f"validated as {document.document_id}"


def download_filing(
    document: DocumentRecord,
    output_path: Path,
    timeout: float,
    force: bool,
    opener: OpenFunction = urlopen,
    user_agent: str | None = None,
) -> DownloadResult:
    """Download one filing, preserving a valid existing copy."""
    if output_path.exists() and not force:
        valid, reason = validate_filing(output_path.read_bytes(), document)
        if valid:
            return DownloadResult(document.document_id, True, "existing valid file", False)
        return DownloadResult(
            document.document_id,
            False,
            f"existing file is invalid ({reason}); review it and use --force to replace",
            False,
        )

    try:
        request_user_agent = user_agent or build_user_agent()
    except ValueError as exc:
        return DownloadResult(document.document_id, False, str(exc), False)

    request = Request(
        document.source_url,
        headers={
            "User-Agent": request_user_agent,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            status = response.getcode()
            if status != 200:
                return DownloadResult(
                    document.document_id, False, f"HTTP status {status}", True
                )
            content = response.read()
    except HTTPError as exc:
        if exc.code in {403, 429}:
            message = (
                f"SEC returned HTTP {exc.code}; verify the contact User-Agent "
                "and wait before retrying"
            )
        else:
            message = f"SEC returned HTTP {exc.code}: {exc.reason}"
        return DownloadResult(document.document_id, False, message, True)
    except (URLError, TimeoutError, socket.timeout) as exc:
        return DownloadResult(document.document_id, False, f"connection failed: {exc}", True)

    valid, reason = validate_filing(content, document)
    if not valid:
        return DownloadResult(
            document.document_id, False, f"downloaded content rejected: {reason}", True
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output_path.parent, delete=False
        ) as temporary_file:
            temporary_file.write(content)
            temporary_name = temporary_file.name
        Path(temporary_name).replace(output_path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
    return DownloadResult(
        document.document_id, True, f"downloaded {len(content):,} bytes", True
    )


def download_documents(
    documents: list[DocumentRecord],
    raw_dir: Path,
    timeout: float,
    force: bool,
    request_delay: float,
    opener: OpenFunction = urlopen,
) -> list[DownloadResult]:
    """Download selected filings sequentially at an SEC-safe request rate."""
    missing_paths = [raw_dir / f"{document.file_stem}.html" for document in documents]
    needs_request = force or any(not path.exists() for path in missing_paths)
    user_agent: str | None = None
    if needs_request:
        try:
            user_agent = build_user_agent()
        except ValueError as exc:
            return [
                DownloadResult(document.document_id, False, str(exc), False)
                if force or not path.exists()
                else download_filing(document, path, timeout, False, opener)
                for document, path in zip(documents, missing_paths)
            ]

    results: list[DownloadResult] = []
    last_request_time: float | None = None
    for document, output_path in zip(documents, missing_paths):
        if last_request_time is not None:
            elapsed = time.monotonic() - last_request_time
            if elapsed < request_delay:
                time.sleep(request_delay - elapsed)
        result = download_filing(
            document, output_path, timeout, force, opener, user_agent
        )
        results.append(result)
        if result.requested:
            last_request_time = time.monotonic()
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download verified Form 10-K filings from SEC EDGAR."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--document-id", help="download one manifest document")
    selection.add_argument("--all", action="store_true", help="download all documents")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--request-delay", type=float, default=DEFAULT_REQUEST_DELAY_SECONDS
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        print("Download failed: timeout must be greater than zero.", file=sys.stderr)
        return 2
    if args.request_delay < 0.1:
        print(
            "Download failed: request delay must be at least 0.1 seconds.",
            file=sys.stderr,
        )
        return 2
    try:
        documents = select_documents(
            load_manifest(args.manifest), args.document_id, args.all
        )
    except ValueError as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 2

    results = download_documents(
        documents, args.raw_dir, args.timeout, args.force, args.request_delay
    )
    for result in results:
        stream = sys.stdout if result.success else sys.stderr
        label = "OK" if result.success else "FAILED"
        print(f"[{label}] {result.document_id}: {result.status}", file=stream)
    successes = sum(result.success for result in results)
    print(f"Download summary: {successes}/{len(results)} successful")
    if successes != len(results) and not os.environ.get("SEC_CONTACT_EMAIL", "").strip():
        print(
            "Set SEC_CONTACT_EMAIL to your real contact email before retrying. "
            "No placeholder contact is accepted.",
            file=sys.stderr,
        )
    return 0 if successes == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
