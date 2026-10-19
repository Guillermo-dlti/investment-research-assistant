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

**Stage 2 — Text Preprocessing and Indexing: Step 11 complete**

The ten selected SEC filings have been downloaded, extracted, chunked, consolidated, and preprocessed. The C++17 Trie and chunk-level inverted index can now load and query the generated data. Matching and similarity algorithms, Python/C++ integration, AI integration, and the user interface have not yet been implemented.

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

## Text Preprocessing

Preprocessing creates a separate normalized representation of every consolidated chunk; it does not alter the source collection or replace the original text. The normalization procedure is deterministic:

- Apply Unicode NFKC normalization.
- Convert common Unicode apostrophes to `'` and dash/minus variants to `-`.
- Normalize case with Python's `casefold()`.
- Collapse each whitespace run to one ASCII space and remove surrounding whitespace.
- Retain stopwords, accents, and numeric information; do not stem or lemmatize words.

The regular-expression tokenizer keeps monetary amounts, percentages, signed numbers, decimal values, comma-separated numbers, hyphenated compounds, possessives, ampersand terms, and multi-period abbreviations intact. For example, `$97,858`, `12.5%`, `ai-powered`, `year-over-year`, `nvidia's`, and `u.s.` each form one token. `S&P 500` becomes the two tokens `s&p` and `500`. Company names and stock tickers are case-folded like other words, so `NVIDIA`, `nvidia`, and `NVDA` become `nvidia`, `nvidia`, and `nvda`.

Run preprocessing from the project root:

```bash
python src/python/preprocess_text.py \
  --input data/chunks/collection.json \
  --output data/processed/preprocessed_collection.json \
  --vocabulary data/metadata/vocabulary.json
```

The preprocessed collection stores each original chunk ID and useful filing metadata alongside `normalized_text`, `tokens`, and `token_count`. The vocabulary stores lexicographically sorted token-frequency records plus the normalization and tokenization policies. These generated files are ignored by Git and can be reproduced from the consolidated collection. The C++ Trie uses the vocabulary now; a later stage will use the token arrays to build the inverted index.

## C++ Trie

The custom C++17 Trie stores complete normalized vocabulary tokens and supports insertion, exact search, prefix checks, and lexicographically ordered autocomplete. It is useful for quickly checking whether a query term exists and for suggesting known financial terms by prefix. Autocomplete does not use token frequencies yet.

The Trie treats each `std::string` as UTF-8 encoded bytes. This safely preserves punctuation and non-ASCII tokens such as `s&p`, `$97,858`, `12.5%`, `ai-powered`, and `chávez`, but it does not interpret Unicode code points or perform normalization. Callers must therefore supply text normalized by the Python preprocessing policy. Autocomplete order is deterministic unsigned-byte lexicographic order, not locale-aware dictionary order.

Configure, build, demonstrate, and test from the project root:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/trie_demo data/metadata/vocabulary.json
ctest --test-dir build --output-on-failure
```

The demonstration loader parses the generated vocabulary's `unique_tokens` and `token_frequencies` fields using a small standard-library-only JSON reader, so no additional C++ dependency is required. It validates the declared size, token-frequency records, and duplicate tokens before insertion. The ten synthetic tests are portable. Two additional CTests load and validate the complete 14,180-token vocabulary when `data/metadata/vocabulary.json` exists during CMake configuration; regenerate it with the preprocessing command before configuring if those local tests are absent.

## C++ Inverted Index

An inverted index maps each normalized token to an ordered postings list of chunk IDs and the token's frequency within each chunk. This allows the project to retrieve chunks containing one term, all terms in an AND query, or at least one term in an OR query without scanning every chunk. Chunk metadata retains the document ID, ticker, and fiscal year. Duplicate chunk IDs are rejected, repeated tokens increase term frequency, and repeated query terms are deduplicated.

Results are ordered lexicographically by chunk ID. Ranked queries use a deliberately simple score: the sum of term frequencies for the unique query tokens in each matching chunk. Results are sorted by descending score and then ascending chunk ID. This favors repetition and does not account for document length, term rarity, adjacent chunk overlap, or semantic relevance; TF-IDF, BM25, and semantic ranking are outside Step 11.

Build and run the real-collection demonstration from the project root:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/inverted_index_demo data/processed/preprocessed_collection.json
ctest --test-dir build --output-on-failure
```

The reusable collection loader reads only the preprocessed fields needed by the index: `chunk_id`, `tokens`, `document_id`, `ticker`, and `fiscal_year`. It shares the standard-library JSON reader with the vocabulary loader and validates collection counts, token counts, required metadata, and unique chunk IDs. Eleven inverted-index tests use synthetic data and remain portable. One additional integration test is registered when the ignored preprocessed collection exists at CMake configuration time.

## Disclaimer

This application is intended solely for educational and research purposes. It does not provide personalized financial advice, investment recommendations, or a substitute for professional financial guidance.
