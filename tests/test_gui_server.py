"""Tests for the GUI backend and its HTTP routes, with a fake model."""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from src.python.gui_server import GuiApp, make_handler
from test_research_assistant import FakeGenerator, make_assistant


@pytest.fixture
def app(tmp_path: Path) -> GuiApp:
    assistant = make_assistant(tmp_path, FakeGenerator("Revenue grew [1]."))
    return GuiApp(assistant, tmp_path / "vocabulary.json")


@pytest.fixture
def server(app: GuiApp) -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def get_json(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        return json.loads(response.read())


def post_json(url: str, body: Any) -> tuple[int, dict[str, Any]]:
    request = Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def test_suggest_completes_last_word_by_frequency(app: GuiApp) -> None:
    # "data" (5 times) outranks "declined" (1 time) for the prefix "d".
    result = app.suggest("NVIDIA d")
    assert result["prefix"] == "d"
    words = [entry["word"] for entry in result["suggestions"]]
    assert words[0] == "data"
    assert "declined" in words
    frequencies = [entry["frequency"] for entry in result["suggestions"]]
    assert frequencies == sorted(frequencies, reverse=True)
    assert result["corrections"] == []


def test_suggest_edge_cases(app: GuiApp) -> None:
    assert app.suggest("")["suggestions"] == []
    assert app.suggest("data ")["suggestions"] == []  # word finished
    assert app.suggest("Rev")["suggestions"][0]["word"] == "revenue"  # normalized
    assert len(app.suggest("d", limit=2)["suggestions"]) == 2


def test_suggest_offers_corrections_for_typos(app: GuiApp) -> None:
    result = app.suggest("nvidea")
    assert result["suggestions"] == []
    assert result["corrections"][0]["word"] == "nvidia"
    assert result["corrections"][0]["distance"] == 1


def test_answer_filter_choices(app: GuiApp) -> None:
    detected = app.answer({"question": "NVIDIA data center revenue"})
    assert detected["filters"] == {"ticker": "NVDA", "fiscal_year": None}
    assert detected["filter_origin"] == {"ticker": "detected", "fiscal_year": "none"}
    assert "messages" not in detected

    chosen = app.answer({"question": "data center revenue", "ticker": "AMD", "fiscal_year": "2025"})
    assert chosen["filters"] == {"ticker": "AMD", "fiscal_year": 2025}
    assert chosen["filter_origin"] == {"ticker": "selected", "fiscal_year": "selected"}

    everything = app.answer({"question": "NVIDIA data center revenue", "ticker": "all"})
    assert everything["filters"]["ticker"] is None
    tickers = {result["ticker"] for result in everything["retrieval"]["results"]}
    assert tickers == {"NVDA", "AMD"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": "   "},
        {"question": "x" * 501},
        {"question": "revenue", "mode": "fuzzy"},
        {"question": "revenue", "ticker": "TSLA"},
        {"question": "revenue", "fiscal_year": 2019},
    ],
)
def test_answer_rejects_bad_requests(app: GuiApp, payload: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        app.answer(payload)


def test_http_routes(server: str) -> None:
    with urlopen(server + "/") as response:
        page = response.read().decode()
    assert response.headers["Content-Type"].startswith("text/html")
    assert "Investment Research Assistant" in page and "/api/suggest" in page

    assert get_json(server + "/api/suggest?text=NVIDIA%20d")["suggestions"][0]["word"] == "data"
    health = get_json(server + "/api/health")
    assert health["model"] == "fake-model" and health["model_loaded"] is True
    assert health["chunks"] == 5

    status, body = post_json(server + "/api/ask", {"question": "NVIDIA data center revenue", "mode": "exact"})
    assert status == 200
    assert body["answer"] == "Revenue grew [1]." and body["mode"] == "exact"
    assert body["context"]["selected"][0]["ticker"] == "NVDA"

    status, body = post_json(server + "/api/ask", {"question": ""})
    assert status == 400 and "question" in body["error"]
    status, body = post_json(server + "/api/ask", ["not", "an", "object"])
    assert status == 400

    with pytest.raises(HTTPError) as missing:
        urlopen(server + "/nope")
    assert missing.value.code == 404
