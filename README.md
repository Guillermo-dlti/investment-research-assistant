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

**Stage 3 — Exact String Matching: complete (Steps 14–18)**

Stage 2 and Stage 3 are complete and validated. Stage 3 includes C++17 implementations of Knuth-Morris-Pratt and the Z-function, Python bindings, ranked exact phrase retrieval, top-k selection, optional ticker/year filtering, and reproducible Release benchmarks. Approximate and similarity matching, AI integration, and the user interface remain unimplemented.

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

The preprocessed collection stores each original chunk ID and useful filing metadata alongside `normalized_text`, `tokens`, and `token_count`. The vocabulary stores lexicographically sorted token-frequency records plus the normalization and tokenization policies. These generated files are ignored by Git and can be reproduced from the consolidated collection. The C++ Trie consumes the vocabulary, and the C++ inverted index consumes the chunk token arrays.

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

## Python/C++ Integration

The `investment_engine` extension exposes the C++ Trie, inverted index, KMP, and Z-function through pybind11; it does not reimplement their algorithms in Python. The binding provides `Trie`, `InvertedIndex`, ranked result objects, C++ factory functions for loading generated data, and the functions `compute_lps`, `kmp_search`, `kmp_count`, `compute_z`, `z_search`, and `z_count`. Direct exact-matching calls accept Python strings and return zero-based UTF-8 byte offsets. The length-aware pybind11 conversion preserves embedded NUL characters, as verified by the integration tests.

`src/python/search_engine.py` reuses the Step 9 `normalize_text()` and `tokenize()` functions for queries and attaches metadata stored by the C++ index. Existing Trie, Boolean retrieval, and term-frequency ranking behavior is unchanged.

Activate `.venv`, then configure CMake with that exact interpreter and build:

```bash
source .venv/bin/activate
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python"
cmake --build build --parallel
```

The compiled module is written to `build/python/`. Add that directory to `PYTHONPATH` when importing it from the repository root:

```bash
PYTHONPATH=build/python python -c \
  "import investment_engine; print(investment_engine.__doc__)"

PYTHONPATH=build/python python -m src.python.search_demo
```

Run all C++ and Python tests after building the extension:

```bash
ctest --test-dir build --output-on-failure
PYTHONPATH=build/python python -m pytest tests -q
```

Direct Trie and index calls expect normalized tokens, while direct exact-matcher calls compare their strings unchanged. The `SearchEngine` wrapper accepts ordinary user query strings and applies the existing Python preprocessing rules before calling C++. Autocomplete normalizes case, Unicode punctuation, and whitespace but intentionally keeps the supplied text as a prefix instead of tokenizing it as a complete term.

The build discovers pybind11 through the selected Python interpreter using `python -m pybind11 --cmakedir`; no system-wide installation or hardcoded package path is used. Python 3.14.7, pybind11 3.1.0, CMake 4.4.4, and Apple Clang 21 were verified. Python/UTF-8 string conversion and conversion of vectors, dictionaries, and ranked results add boundary overhead proportional to the transferred input and output sizes, but do not change the underlying algorithms' theoretical complexity.

## Knuth-Morris-Pratt Exact Matching

The custom C++17 KMP implementation builds an LPS (longest proper prefix that is also a suffix) table and uses it to find every exact occurrence without restarting at the beginning of the pattern after a mismatch. It supports overlapping matches and returns ascending, zero-based byte offsets. An empty pattern, empty text with a nonempty pattern, or a pattern longer than the text produces no matches; an empty pattern has count zero.

KMP treats `std::string` values as UTF-8 bytes, consistent with the Trie. It performs no case folding or Unicode normalization, so callers must provide the exact representation they want to match. Positions are byte offsets rather than Unicode character indices.

Build, run the demonstration, and execute tests:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python"
cmake --build build --parallel
./build/kmp_demo data/processed/preprocessed_collection.json
ctest --test-dir build --output-on-failure
```

For text length `n` bytes and pattern length `m` bytes, LPS construction is `O(m)`, searching is `O(n)`, and the combined operation is `O(n + m)`. The LPS table requires `O(m)` auxiliary space; the returned positions require `O(z)` output space for `z` matches. KMP is exposed through `investment_engine`; Python ranks exact-search results from its returned occurrence count without changing the algorithm or Stage 2 ranking.

## Z-function Exact Matching

The custom C++17 Z-function records at each position the length of the prefix that matches the sequence beginning there. Its linear Z-box algorithm maintains a known matching interval `[l, r)`: positions inside that interval reuse an earlier Z value, and only comparisons that extend beyond `r` advance the right boundary. Pattern search computes the array for `pattern + separator + text`; an entry at least as long as the pattern identifies a match. This is useful for locating exact financial phrases, identifiers, percentages, and currency values while retaining overlapping occurrences.

The combined sequence stores every input byte as an unsigned integer in `0` through `255` and uses `256` as the separator. That value cannot collide with punctuation, embedded null bytes, byte 255, or bytes in valid UTF-8. Matching performs no normalization and returns ascending, zero-based byte offsets. `Z[0]` is defined as zero. Empty patterns, empty text with a nonempty pattern, and patterns longer than the text produce no matches; an empty pattern has count zero.

Build, run both exact-matching demonstrations, and execute the focused Z-function tests:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python"
cmake --build build --parallel
./build/kmp_demo data/processed/preprocessed_collection.json
./build/z_function_demo data/processed/preprocessed_collection.json
ctest --test-dir build -L z_function --output-on-failure
```

For `n` text bytes and `m` pattern bytes, Z-array construction is linear in its input length and a search takes `O(n + m)` time. This implementation requires `O(n + m)` auxiliary space for the combined integer sequence and its Z-array, plus `O(z)` for `z` returned positions; counting does not allocate the positions. KMP has the same `O(n + m)` search bound but needs only `O(m)` auxiliary space for its LPS table. Conceptually, KMP uses pattern fallback information after mismatches, whereas the Z-function reuses prefix matches within its Z-box. The Z-function is exposed through `investment_engine`; Python applies the same occurrence-count ranking to its exact-search results.

## Python Exact Phrase Search

`SearchEngine.exact_phrase_search(query, algorithm="kmp", token_boundaries=True, ticker=None, fiscal_year=None, top_k=None)` searches each chunk's stored `normalized_text`. The query is processed with the existing NFKC, punctuation canonicalization, case-folding, and whitespace policy; the chunk data is not re-normalized or changed. Results contain `chunk_id`, `document_id`, `ticker`, `fiscal_year`, `match_count`, `match_byte_offsets`, the canonical algorithm name (`kmp` or `z`), and `score`. Offsets count UTF-8 bytes in `normalized_text`, not Python characters, original filing bytes, or joined tokens.

With token boundaries enabled, a match must begin at a tokenizer token start and end at a tokenizer token end, preventing `ai` from matching inside `paid` or `ai-powered`. When the normalized query is exactly its tokens joined by single spaces, the inverted index first applies AND retrieval over the unique query tokens; exact C++ matching then verifies those candidates. If token boundaries are disabled or the query cannot be proven equivalent to that token sequence, the engine scans every chunk. This fallback preserves substring and punctuation correctness when an index token could differ from the requested pattern.

Exact results use the deliberately simple score `score(chunk, query) = exact phrase occurrences in the chunk`, which is also the returned `match_count`. Results sort by descending score and then ascending chunk ID. `top_k` is applied after this ordering; `None` returns every match, zero returns none, values larger than the result count return all matches, and negative values raise `ValueError`. Optional `ticker` and `fiscal_year` filters use stored chunk metadata and run before C++ matching. Ticker comparison is case-insensitive, unknown tickers return no results, and either filter can be used independently or together. These options do not modify Stage 2 ranking.

Run the real-data demonstration and the exact-search tests:

```bash
PYTHONPATH=build/python .venv/bin/python -m src.python.exact_search_demo
PYTHONPATH=build/python .venv/bin/python -m pytest tests/test_exact_search.py -q
```

The verified demonstration found `artificial intelligence` in 30 chunks with identical KMP and Z-function rankings. `GOOGL_2025_10K_0067` ranked first with score 2 and byte offsets `[723, 1000]`; other displayed results scored 1. Combined `ticker="NVDA"` and `fiscal_year=2025` filtering returned `NVDA_2025_10K_0009` at `[468]` and `NVDA_2025_10K_0121` at `[397]`. The earlier standalone C++ demo offset 461 refers to a different representation—normalized tokens reconstructed with single spaces. The punctuation query `$0.001` ranked the two Alphabet chunks first with score 2, followed by two NVIDIA chunks with score 1.

If `C` chunks survive candidate and metadata filtering, their byte lengths are `n_i`, the pattern has `m` bytes, and `M` chunks match, invoking either exact matcher across the candidates costs `O(sum(n_i + m))`. This does not change the `O(n_i + m)` complexity of an individual KMP or Z-function call. Metadata filtering costs `O(C)`, collecting scores costs `O(M)`, sorting costs `O(M log M)`, and slicing a top-k prefix costs `O(min(k, M))` after the full deterministic sort. Frequency-only ranking does not measure relevance, term rarity, document length, recency, or semantic meaning; no TF-IDF or BM25 behavior is implied.

## Stage 3 Evaluation and Benchmarks

The Release benchmark calls the production KMP and Z-function implementations directly. It verifies position-vector equivalence before timing, performs warm-ups, alternates algorithm order, and reports median, mean, minimum, and maximum execution time. Loading, JSON parsing, Python startup, and index construction are excluded. Scenarios cover 1–250 KiB financial-text prefixes, four pattern lengths, four match distributions, and unfiltered scans of all 2,458 normalized chunks.

Reproduce the benchmark and graphs from the project root:

```bash
.venv/bin/cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python"
.venv/bin/cmake --build build --parallel
./build/exact_matching_benchmark \
  data/processed/preprocessed_collection.json \
  reports/benchmarks/exact_matching_results.csv \
  reports/benchmarks/exact_matching_summary.json
MPLCONFIGDIR=/tmp/investment-research-matplotlib \
  .venv/bin/python -m src.python.plot_exact_matching_benchmarks
```

On the verified Apple M5 Pro environment, KMP had the lower median in all 17 scenarios. For the 3,949,059-byte full collection, `artificial intelligence` produced 31 raw substring matches with medians of 4.667 ms for KMP and 7.977 ms for the Z-function. These are environment-specific empirical results, not a general guarantee. See [the Stage 3 validation report](reports/stage3_validation.md), [raw CSV](reports/benchmarks/exact_matching_results.csv), and [JSON summary](reports/benchmarks/exact_matching_summary.json).

## Disclaimer

This application is intended solely for educational and research purposes. It does not provide personalized financial advice, investment recommendations, or a substitute for professional financial guidance.
