# Investment Research Assistant

An Advanced Algorithms course project (Tecnológico de Monterrey). You ask a question about the FY2024 and FY2025 SEC 10-K filings of NVIDIA, AMD, Microsoft, Apple and Alphabet. Classic string algorithms written from scratch in C++17 find the most relevant passages, and a pretrained Hugging Face model (`Qwen/Qwen2.5-3B-Instruct`) answers from them with citations.

**Question → search → retrieved chunks → context selection → language model → answer**

## Stages

| Stage | What it does | Code | Evidence |
|---|---|---|---|
| 1. Documents | Downloads 10 filings from SEC EDGAR, extracts the text, splits it into 2,458 chunks of up to 250 tokens with 40 tokens of overlap | `src/python/download_documents.py`, `extract_text.py`, `chunk_documents.py`, `build_collection.py` | `reports/stage1_notes.md` |
| 2. Preprocessing and indexing | NFKC normalization, case folding, tokenization, a 14,180-word vocabulary; a C++ Trie and inverted index | `src/python/preprocess_text.py`, `src/cpp/trie.*`, `src/cpp/inverted_index.*` | `reports/stage2_notes.md`, `stage2_validation.md` |
| 3. Exact search | KMP and Z function phrase search, occurrence-count ranking, filters, benchmark | `src/cpp/kmp.*`, `src/cpp/z_function.*`, `src/python/search_engine.py` | `reports/stage3_notes.md`, `stage3_validation.md`, `reports/benchmarks/` |
| 4. Approximate search | Levenshtein typo correction, word n-gram Jaccard similarity, reranking | `src/cpp/levenshtein.*`, `ngram_jaccard.*`, `approximate_rerank.*` | `reports/stage4_notes.md` |
| 5. Context and model | Greedy context selection (4 chunks, 1,100 words, near duplicates removed) and cited answers for 21 questions | `src/cpp/context_selection.*`, `src/python/research_assistant.py` | `reports/stage5_notes.md`, `stage5_results.md` |
| 6. Comparison | Exact vs approximate on 24 questions: time, candidates, chunk usefulness, answers, collection size | `src/python/compare_strategies.py` | `reports/stage6_notes.md`, `stage6_results.md`, `stage6_*.png` |
| Bonus: GUI | Question window with Trie autocomplete and cited answers | `src/python/gui_server.py`, `src/gui/index.html` | |

Every algorithm and data structure lives in `src/cpp/` and is exposed to Python through the pybind11 module `investment_engine`. Python only orchestrates: the data pipeline, query normalization, filters, the model and the GUI. [src/cpp/README.md](src/cpp/README.md) describes the C++ modules.

## Setup

Requires Python 3.11 or newer and a C++17 compiler (on macOS, Apple Clang from `xcode-select --install`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Build the data

The filings and everything generated from them are not committed. SEC EDGAR requires a real contact email.

```bash
export SEC_CONTACT_EMAIL="you@tec.mx"
python src/python/download_documents.py --all
python src/python/extract_text.py --all
python src/python/chunk_documents.py --all --chunk-size 250 --overlap 40
python src/python/build_collection.py
python src/python/preprocess_text.py \
  --input data/chunks/collection.json \
  --output data/processed/preprocessed_collection.json \
  --vocabulary data/metadata/vocabulary.json
```

## Build and test

Configure CMake after the data exists, so the tests that use the real collection are registered.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE="$PWD/.venv/bin/python"
cmake --build build --parallel
ctest --test-dir build --output-on-failure        # 101 C++ tests
PYTHONPATH=build/python python -m pytest tests -q  # 142 Python tests (they use a fake model)
```

If the project path contains a space and CMake cannot find pybind11, also pass `-Dpybind11_DIR="$PWD/.venv/lib/python3.X/site-packages/pybind11/share/cmake/pybind11"` with your Python version. The compiled module is tied to that Python version; rebuild after changing interpreter.

## Run

```bash
# GUI with Trie autocomplete at http://127.0.0.1:8765
PYTHONPATH=build/python python -m src.python.gui_server

# One question from the terminal (--mode exact for exact search)
PYTHONPATH=build/python python -m src.python.ask "What was NVIDIA data center revenue in fiscal 2025?"

# Regenerate the stage evidence
PYTHONPATH=build/python python -m src.python.search_demo              # Stage 2
PYTHONPATH=build/python python -m src.python.exact_search_demo        # Stage 3
PYTHONPATH=build/python python -m src.python.approximate_search_demo  # Stage 4
PYTHONPATH=build/python python -m src.python.run_questions            # Stage 5
PYTHONPATH=build/python python -m src.python.compare_strategies       # Stage 6
```

The first answer downloads the model (about 6 GB) and runs it on the Apple GPU (MPS) or the CPU.

## Disclaimer

This project is for education only. It does not give financial advice, and the filings describe past results, not future performance.
