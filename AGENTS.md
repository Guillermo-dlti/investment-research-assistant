# Investment Research Assistant

Advanced Algorithms course project (Tec de Monterrey). You ask a question, the system finds the most relevant chunks of 10 SEC 10-K filings (NVDA, AMD, MSFT, AAPL, GOOGL, FY2024 and FY2025), and a Hugging Face model answers from those chunks. The full course brief (6 stages, deliverables, bonus) is in [docs/assignment.md](docs/assignment.md). The detailed technical handoff is [reports/DEVELOPER_HANDOFF.md](reports/DEVELOPER_HANDOFF.md); read it before changing code.

## Stack

- **Language / Runtime**: Python 3.11+ (3.14.7 verified) and C++17 (Apple Clang)
- **Framework**: pybind11 module `investment_engine`, built with CMake into `build/python/`
- **Key dependencies**: pymupdf, beautifulsoup4, pybind11, matplotlib, pytest, torch and transformers (Stage 5 model `Qwen/Qwen2.5-3B-Instruct`, about 6 GB, downloaded on first answer); a GUI library is still to be chosen
- **Package manager**: pip inside `.venv`

## Build approach

Tracer Bullet (each stage is built end to end: C++ algorithm, pybind11 binding, Python wiring, tests, and report evidence).

## Commands

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Regenerate data (gitignored; needs a real contact email for SEC EDGAR)
export SEC_CONTACT_EMAIL="you@tec.mx"
python src/python/download_documents.py --all && python src/python/extract_text.py --all
python src/python/chunk_documents.py --all --chunk-size 250 --overlap 40 && python src/python/build_collection.py
python src/python/preprocess_text.py --input data/chunks/collection.json --output data/processed/preprocessed_collection.json --vocabulary data/metadata/vocabulary.json

# Build (configure AFTER data exists, so data tests register)
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE="$PWD/.venv/bin/python" && cmake --build build --parallel

# Test (expect 101 C++ and 123 Python passing with data present; Python tests use a fake model)
ctest --test-dir build --output-on-failure && PYTHONPATH=build/python python -m pytest tests -q

# Demos
PYTHONPATH=build/python python -m src.python.exact_search_demo
PYTHONPATH=build/python python -m src.python.search_demo
PYTHONPATH=build/python python -m src.python.approximate_search_demo  # exact vs approximate, Stage 4 evidence
PYTHONPATH=build/python python -m src.python.ask "What was NVIDIA data center revenue in fiscal 2025?"
PYTHONPATH=build/python python -m src.python.run_questions  # 21 questions → reports/stage5_results.{json,md}
```

## Specs

Stored in `docs/specs/`. Format: `docs/specs/NNNN-title.md`.

## Rules

- Every algorithm and data structure is written from scratch in C++17 under `src/cpp/`. Python only orchestrates: data pipeline, query normalization, calling bindings, filters, formatting, and later the model and GUI. Never reimplement a C++ algorithm in Python.
- New C++ code gets its own library target, a CTest executable with named cases, a demo, a pybind11 binding, and Python tests in `tests/`.
- Do not change finished Stage 1 to 3 code (Trie, inverted index, KMP, Z function, `SearchEngine` API) unless a real bug demands it; extend compatibly.
- Text is normalized by the Python `normalize_text()` and `tokenize()` policy; C++ treats strings as UTF-8 bytes, so offsets are byte offsets.
- `chunk_id` is the join key across every representation; keep source metadata for citations.
- Keep ordering and tie breaking deterministic so tests and benchmarks are reproducible.
- Never commit `data/` outputs, `build/`, `.venv`, `.so` files, emails, or API keys.
- Reports go in `reports/`; the final report must not contain code (course rule).

## Context files

- [src/cpp/AGENTS.md](src/cpp/AGENTS.md): C++ algorithms, CMake targets, CTest and pybind11 conventions
- [docs/assignment.md](docs/assignment.md): course brief and teammate handoff message
- [docs/scope/scope.md](docs/scope/scope.md): stage by stage scope and what is left

_Drafted by /audit from the repo, worth a quick human pass. Edit freely: once a line stops matching this draft, later runs treat it as curated and will flag rather than overwrite it._
