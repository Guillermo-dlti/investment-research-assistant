"""Local web GUI: Trie autocomplete while typing, and cited answers with their sources.

Run with ``PYTHONPATH=build/python python -m src.python.gui_server`` and open
the printed address. Only the Python standard library is used for the server.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.python.preprocess_text import tokenize
from src.python.research_assistant import (
    DEFAULT_MODEL,
    DEFAULT_SOURCE_COLLECTION,
    MODES,
    HuggingFaceGenerator,
    ResearchAssistant,
    infer_filters,
)
from src.python.search_engine import DEFAULT_COLLECTION, DEFAULT_VOCABULARY


INDEX_HTML = Path(__file__).resolve().parents[1] / "gui" / "index.html"
TICKERS = ("NVDA", "AMD", "MSFT", "AAPL", "GOOGL")
FISCAL_YEARS = (2024, 2025)
SUGGESTION_LIMIT = 8
# Completions fetched from the Trie before ranking them by corpus frequency.
TRIE_CANDIDATES = 5000
MAX_QUESTION_CHARS = 500


class GuiApp:
    """The GUI's backend logic, separate from HTTP so it can be tested directly."""

    def __init__(self, assistant: ResearchAssistant, vocabulary_path: Path | str) -> None:
        self.assistant = assistant
        self.frequencies = self._load_frequencies(vocabulary_path)
        # One question at a time: the model is not safe to call concurrently.
        self._answer_lock = threading.Lock()

    def suggest(self, text: str, limit: int = SUGGESTION_LIMIT) -> dict[str, Any]:
        """Complete the word being typed at the end of ``text``.

        The C++ Trie returns every vocabulary word with the typed prefix; they
        are shown most frequent first (ties alphabetical). When the prefix has
        no completion, Levenshtein corrections are offered instead.
        """
        empty = {"prefix": "", "suggestions": [], "corrections": []}
        if not text or text[-1].isspace():
            return empty
        fragment = re.search(r"\S+$", text)
        tokens = tokenize(fragment.group(0)) if fragment else []
        if not tokens:
            return empty
        prefix = tokens[-1]
        words = self.assistant.engine.autocomplete(prefix, TRIE_CANDIDATES)
        ranked = sorted(words, key=lambda word: (-self.frequencies.get(word, 0), word))
        suggestions = [
            {"word": word, "frequency": self.frequencies.get(word, 0)}
            for word in ranked[:limit]
        ]
        corrections: list[dict[str, Any]] = []
        if not suggestions and len(prefix) >= 3:
            corrections = self.assistant.engine.fuzzy_terms(prefix, limit=3)
        return {"prefix": prefix, "suggestions": suggestions, "corrections": corrections}

    def answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate a GUI request and answer it.

        ``ticker`` and ``fiscal_year`` are ``"auto"`` (detect from the
        question), ``"all"`` (no filter) or a concrete value.
        """
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        if len(question) > MAX_QUESTION_CHARS:
            raise ValueError(f"question must be at most {MAX_QUESTION_CHARS} characters")
        mode = payload.get("mode", "approximate")
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")

        inferred = infer_filters(question)
        ticker = self._choose(payload.get("ticker", "auto"), inferred["ticker"], TICKERS, "ticker")
        fiscal_year = self._choose(
            payload.get("fiscal_year", "auto"), inferred["fiscal_year"], FISCAL_YEARS, "fiscal_year"
        )
        with self._answer_lock:
            result = self.assistant.ask(
                question.strip(), mode=mode, ticker=ticker, fiscal_year=fiscal_year, auto_filters=False
            )
        result.pop("messages", None)
        result["filter_origin"] = {
            "ticker": self._origin(payload.get("ticker", "auto"), ticker),
            "fiscal_year": self._origin(payload.get("fiscal_year", "auto"), fiscal_year),
        }
        return result

    def health(self) -> dict[str, Any]:
        generator = self.assistant.generator
        return {
            "model": generator.name,
            "model_loaded": bool(getattr(generator, "loaded", True)),
            "chunks": self.assistant.engine.indexed_chunk_count,
            "vocabulary": self.assistant.engine.vocabulary_size,
        }

    @staticmethod
    def _choose(value: Any, inferred: Any, allowed: tuple[Any, ...], name: str) -> Any:
        if value == "auto":
            return inferred
        if value == "all" or value is None:
            return None
        if name == "fiscal_year" and isinstance(value, str) and value.isdigit():
            value = int(value)
        if value not in allowed:
            raise ValueError(f"{name} must be 'auto', 'all' or one of {allowed}")
        return value

    @staticmethod
    def _origin(requested: Any, chosen: Any) -> str:
        if chosen is None:
            return "none"
        return "detected" if requested == "auto" else "selected"

    @staticmethod
    def _load_frequencies(path: Path | str) -> dict[str, int]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return {
            entry["token"]: int(entry["frequency"])
            for entry in payload.get("token_frequencies", [])
        }


def make_handler(app: GuiApp, index_html: Path = INDEX_HTML) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server naming)
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                self._send(HTTPStatus.OK, index_html.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/suggest":
                text = parse_qs(url.query).get("text", [""])[0]
                self._json(HTTPStatus.OK, app.suggest(text))
            elif url.path == "/api/health":
                self._json(HTTPStatus.OK, app.health())
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/ask":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(payload, dict):
                    raise ValueError("request body must be a JSON object")
                self._json(HTTPStatus.OK, app.answer(payload))
            except (ValueError, json.JSONDecodeError) as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            if not self.path.startswith("/api/suggest"):
                super().log_message(format, *args)

        def _json(self, status: HTTPStatus, body: dict[str, Any]) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self._send(status, data, "application/json; charset=utf-8")

        def _send(self, status: HTTPStatus, data: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the local research assistant GUI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    assistant = ResearchAssistant(
        DEFAULT_VOCABULARY,
        DEFAULT_COLLECTION,
        DEFAULT_SOURCE_COLLECTION,
        generator=HuggingFaceGenerator(args.model),
    )
    app = GuiApp(assistant, DEFAULT_VOCABULARY)
    # Load the model in the background so the page opens right away.
    threading.Thread(target=assistant.generator.load, daemon=True).start()

    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    address = f"http://{args.host}:{server.server_address[1]}"
    print(f"Investment Research Assistant running at {address} (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
