# Investment Research Assistant

Investment Research Assistant is an educational project for an Advanced Algorithms university course. The project will explore how advanced string-matching algorithms and data structures can support an AI-powered system that retrieves relevant information from financial documents and uses it to answer research questions.

The initial scope covers five technology companies:

- NVIDIA
- AMD
- Microsoft
- Apple
- Alphabet

## Technology Stack

- **Python:** Document processing, application logic, and AI integration.
- **C++:** Custom implementations of algorithms and data structures.
- **pybind11:** Integration of the C++ implementations with Python.
- **Hugging Face:** Pretrained language model support.
- **Streamlit:** User interface.

## Planned Algorithms and Data Structures

- **Knuth-Morris-Pratt (KMP):** Exact pattern matching within document text.
- **Z-function:** Efficient pattern-search and string-analysis operations.
- **Levenshtein Distance:** Approximate matching based on edit distance.
- **N-grams and Jaccard Similarity:** Similarity measurement between queries and document passages.
- **Trie:** Efficient storage and lookup of terms and prefixes.
- **Inverted Index:** Mapping terms to the document passages in which they occur.

## Planned Workflow

Financial reports will be collected and converted into clean text. The text will then be divided into searchable chunks and enriched with metadata such as company, document type, and reporting period. The custom C++ algorithms and data structures, exposed to Python through pybind11, will help find and rank chunks relevant to a user's question. Selected context will be passed to a pretrained Hugging Face language model, which will generate a response grounded in the retrieved documents. Streamlit will eventually provide the interface for submitting questions and viewing answers and supporting sources.

## Current Status

**Stage 1 — Document Selection and Preparation: Complete**

The ten selected SEC filings have been downloaded, extracted, chunked, and consolidated. Stage 2 preprocessing, retrieval algorithms, AI integration, and the user interface have not yet been implemented.

## Development Setup

The project requires Python 3.11 or newer. Python 3.11 or 3.12 is recommended for consistent package compatibility. A compiler with C++17 support is also required; Apple Clang, included with the Xcode Command Line Tools, is suitable on macOS.

From the project root, create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install the project dependencies inside the environment:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify Python, the required imports, CMake, and the C++ compiler:

```bash
python --version
python -c "import pymupdf, pybind11, pytest; print('Python dependencies are available')"
cmake --version
clang++ --version
```

If `clang++` is unavailable on macOS, install Apple's command-line developer tools with `xcode-select --install`. The `cmake` command is installed in the virtual environment by `requirements.txt`; if a system-wide CMake installation is needed separately, install it manually with Homebrew using `brew install cmake`.

When finished, leave the virtual environment:

```bash
deactivate
```

## Document Preparation

The tracked manifest at `config/document_manifest.json` records the verified FY2024 and FY2025 SEC Form 10-K filings for NVIDIA, AMD, Microsoft, Apple, and Alphabet. Original SEC filings are stored in `data/raw/`, while readable text and structured JSON results are stored in `data/processed/`. Keeping source HTML separate preserves an auditable copy of each official filing and allows extraction to be repeated without downloading it again.

Activate the virtual environment and provide your real contact email for the SEC request header:

```bash
source .venv/bin/activate
export SEC_CONTACT_EMAIL="your_actual_email@university.edu"
```

Download the complete ten-document collection:

```bash
python src/python/download_documents.py --all
```

Download one filing by its manifest ID when needed:

```bash
python src/python/download_documents.py --document-id NVDA_2025_10K
```

The downloader reuses valid existing files, waits between SEC requests, and does not overwrite files unless `--force` is supplied. Extract all available filings:

```bash
python src/python/extract_text.py --all
```

Each filing produces a readable `.txt` file and a structured `.json` file under `data/processed/`. Raw filings and generated outputs are ignored by Git; the manifest remains tracked so another student can reproduce the collection from the official sources.

## Document Chunking

Large financial filings are split into smaller passages so later retrieval stages can work with focused, readable context. The initial strategy targets 250 words per chunk, preserves paragraph or sentence boundaries when practical, and repeats the preceding 40 words to maintain context between consecutive chunks.

Generate 250-word chunks with 40 words of overlap for the full collection:

```bash
python src/python/chunk_documents.py --all --chunk-size 250 --overlap 40
```

Generate chunks for one manifest document with `--document-id`, or retain the direct-file interface when experimenting:

```bash
python src/python/chunk_documents.py \
  --input data/processed/nvidia_2025.json \
  --output data/chunks/nvidia_2025_chunks.json \
  --chunk-size 250 \
  --overlap 40
```

Chunk JSON files are stored under `data/chunks/`. Change `--chunk-size` and `--overlap` to experiment with other valid values; overlap must be smaller than the chunk size.

## Consolidated Collection

Build and strictly validate the complete collection from the ten individual chunk files:

```bash
python src/python/build_collection.py
```

The command reads `config/document_manifest.json`, the document JSON files in `data/processed/`, and the individual chunk files in `data/chunks/`. It generates:

- `data/chunks/collection.json`: manifest-ordered document summaries and the complete chunk array.
- `data/metadata/collection_statistics.json`: collection and per-document statistics with counting methodology.

Every consolidated chunk retains its original text, identifier, position, paragraph references, and filing metadata. The build fails if a manifest document is missing, metadata is inconsistent, chunk counts disagree, text is empty, or a chunk ID is duplicated. Output order is deterministic: manifest order followed by original chunk position.

To reproduce and validate all of Stage 1 from a fresh checkout:

```bash
source .venv/bin/activate
export SEC_CONTACT_EMAIL="your_actual_email@university.edu"
python src/python/download_documents.py --all
python src/python/extract_text.py --all
python src/python/chunk_documents.py --all --chunk-size 250 --overlap 40
python src/python/build_collection.py
python -m pytest tests -q
```

## Disclaimer

This application is intended solely for educational and research purposes. It does not provide personalized financial advice, investment recommendations, or a substitute for professional financial guidance.
