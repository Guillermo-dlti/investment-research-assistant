"""Download the official NVIDIA FY2025 Form 10-K from SEC EDGAR."""

from __future__ import annotations

import argparse
import html
import os
import re
import socket
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SOURCE_URL = (
    "https://www.sec.gov/Archives/edgar/data/1045810/"
    "000104581025000023/nvda-20250126.htm"
)
DEFAULT_OUTPUT = Path("data/raw/nvidia_2025.html")
DEFAULT_TIMEOUT_SECONDS = 30.0
MINIMUM_EXPECTED_BYTES = 100_000


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
    ).strip()
    if not description:
        description = "InvestmentResearchAssistant/1.0"
    if email.lower() not in description.lower():
        description = f"{description} ({email})"
    return description


def _is_plausible_contact_email(value: str) -> bool:
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        return False
    domain = value.rsplit("@", 1)[1].lower()
    return domain not in {"example.com", "example.org", "example.net", "localhost"}


def validate_filing(content: bytes) -> tuple[bool, str]:
    """Check that bytes resemble the specified NVIDIA FY2025 Form 10-K."""
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
        return False, "the response appears to be an SEC access or error page"
    if "<html" not in normalized:
        return False, "the response does not appear to be HTML"
    if "nvidia corporation" not in normalized and "nvidia corp" not in normalized:
        return False, "NVIDIA Corporation was not identified in the response"
    if "10-k" not in normalized:
        return False, "Form 10-K was not identified in the response"
    fiscal_year_end_markers = ("2025-01-26", "20250126", "january 26, 2025")
    if not any(marker in normalized for marker in fiscal_year_end_markers):
        return False, "the January 26, 2025 fiscal year end was not identified"
    return True, "validated as the NVIDIA FY2025 Form 10-K"


def download_filing(output_path: Path, timeout: float, force: bool) -> bool:
    """Download and validate the filing, preserving a valid existing copy."""
    if output_path.exists() and not force:
        valid, reason = validate_filing(output_path.read_bytes())
        if valid:
            print(f"Existing filing is valid; no download needed: {output_path}")
            return True
        print(
            f"Existing file is not valid ({reason}). "
            "Use --force to replace it after reviewing the file.",
            file=sys.stderr,
        )
        return False

    try:
        user_agent = build_user_agent()
    except ValueError as exc:
        print(f"Download not attempted: {exc}", file=sys.stderr)
        print_manual_instructions(output_path)
        return False

    request = Request(
        SOURCE_URL,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            if status != 200:
                print(f"Download failed with HTTP status {status}.", file=sys.stderr)
                return False
            content = response.read()
    except HTTPError as exc:
        if exc.code in {403, 429}:
            print(
                f"SEC returned HTTP {exc.code}. Check the contact User-Agent and "
                "wait before trying again; do not repeatedly retry.",
                file=sys.stderr,
            )
        else:
            print(f"SEC download failed with HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        return False
    except (URLError, TimeoutError, socket.timeout) as exc:
        print(f"SEC connection failed: {exc}", file=sys.stderr)
        return False

    valid, reason = validate_filing(content)
    if not valid:
        print(f"Downloaded content was rejected: {reason}.", file=sys.stderr)
        return False

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

    print(
        f"Downloaded and validated NVIDIA FY2025 Form 10-K "
        f"({len(content):,} bytes): {output_path}"
    )
    return True


def print_manual_instructions(output_path: Path) -> None:
    """Explain the approved alternatives when contact information is unavailable."""
    print(
        "Set SEC_CONTACT_EMAIL to your real contact email and run this command again.\n"
        "Alternatively, open the official filing URL in a browser, save the page source "
        f"as {output_path}, and then run the extraction script.\n"
        f"Official filing: {SOURCE_URL}",
        file=sys.stderr,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download NVIDIA's official FY2025 Form 10-K from SEC EDGAR."
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="destination HTML path"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--force", action="store_true", help="replace an existing filing after validation"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        print("The timeout must be greater than zero.", file=sys.stderr)
        return 2
    return 0 if download_filing(args.output, args.timeout, args.force) else 1


if __name__ == "__main__":
    raise SystemExit(main())
