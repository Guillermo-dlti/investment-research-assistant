# Stage 2 Final Validation

## 1. Objectives

Stage 2 converts the prepared SEC filing chunks into a deterministic normalized corpus, builds custom C++17 retrieval structures, and makes those structures available to Python. Its completed scope is text preprocessing, vocabulary generation, Trie lookup and autocomplete, chunk-level inverted indexing, Boolean retrieval, raw term-frequency ranking, and pybind11 integration. No Stage 3 matching algorithms, language model, or frontend is included.

## 2. Implemented Components

- Python Unicode, case, whitespace, and punctuation normalization using the Step 9 policy.
- Python financial-text tokenization without stopword removal, stemming, lemmatization, or numeric removal.
- A C++17 byte-oriented Trie with insertion, exact search, prefix search, and deterministic autocomplete.
- A C++17 inverted index using `token -> {chunk_id -> term_frequency}` postings.
- AND and OR postings operations with deterministic chunk-ID ordering.
- Ranking by the sum of term frequencies for unique query terms, with chunk ID as the tie-breaker.
- Standard-library C++ JSON loaders for the vocabulary and preprocessed collection.
- A pybind11 module named `investment_engine` and a thin Python `SearchEngine` wrapper.

## 3. Architecture Overview

The verified path is:

```text
SEC filings
  -> Stage 1 extracted text and chunks
  -> data/chunks/collection.json
  -> Python normalization and tokenization
  -> preprocessed_collection.json + vocabulary.json
  -> C++ Trie + C++ inverted index
  -> pybind11 investment_engine module
  -> Python SearchEngine queries and metadata results
```

The C++ vocabulary loader inserts normalized tokens into the Trie. The C++ collection loader inserts each chunk's tokens and metadata into the inverted index. The Python wrapper invokes these bound C++ components and only normalizes queries and formats returned metadata; it does not reimplement Trie traversal, postings operations, or ranking.

## 4. Dataset Statistics and Integrity

Final validation against the real generated files confirmed:

- Financial documents: **10 declared and 10 present**.
- Companies: **5 declared and 5 distinct tickers**.
- Consolidated chunks: **2,458**.
- Preprocessed chunks: **2,458**.
- Indexed chunks: **2,458**.
- Total token occurrences: **579,089**, including overlap between chunks.
- Unique normalized tokens: **14,180** in the computed corpus, vocabulary, Trie, and inverted index.
- Duplicate chunk IDs: **0**.
- Empty AND and OR queries: both return an empty result.

Every consolidated chunk ID has exactly one preprocessed record. `document_id`, `ticker`, and `fiscal_year` match the source collection for all 2,458 chunks. Vocabulary frequencies recomputed from preprocessed token arrays exactly match `vocabulary.json`. Every postings list contains unique, ascending chunk IDs, and its length matches the index's document-frequency value.

The compiled module was loaded from `build/python/investment_engine.cpython-314-darwin.so`, confirming that Python used the native extension. Source and generated-data hashes remained unchanged during validation:

- `collection.json`: `54840f7ab9d9be4ae79729d8ab9d4f2ad6d73af4504c2c4538a17e93c7283442`
- `preprocessed_collection.json`: `312a4b8f39e40c52a6722d0444cfd89ac0fb1ab49d275826f1a355067df45c00`
- `vocabulary.json`: `27c81f1015f3dcc71d36cf2ae0eb388d0ffc1bdc8b2d17fe34840cb298c3f006`

## 5. Representative Search Results

The following validation uses ranked **AND** retrieval: every matching chunk contains every normalized query token. Ranking is lexical and equals the sum of raw term frequencies for the unique query terms.

### NVIDIA revenue

Normalized tokens: `nvidia`, `revenue`. Matching chunks: **45**.

| Rank | Chunk ID | Document ID | Ticker | Fiscal year | Score |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `NVDA_2024_10K_0228` | `NVDA_2024_10K` | NVDA | 2024 | 14 |
| 2 | `NVDA_2024_10K_0147` | `NVDA_2024_10K` | NVDA | 2024 | 12 |
| 3 | `NVDA_2024_10K_0146` | `NVDA_2024_10K` | NVDA | 2024 | 11 |
| 4 | `NVDA_2024_10K_0249` | `NVDA_2024_10K` | NVDA | 2024 | 11 |
| 5 | `NVDA_2025_10K_0232` | `NVDA_2025_10K` | NVDA | 2025 | 10 |

### AMD competition

Normalized tokens: `amd`, `competition`. Matching chunks: **3**.

| Rank | Chunk ID | Document ID | Ticker | Fiscal year | Score |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `AMD_2024_10K_0041` | `AMD_2024_10K` | AMD | 2024 | 3 |
| 2 | `AMD_2025_10K_0042` | `AMD_2025_10K` | AMD | 2025 | 2 |
| 3 | `NVDA_2024_10K_0030` | `NVDA_2024_10K` | NVDA | 2024 | 2 |

The NVIDIA result is valid lexical behavior: the NVIDIA filing chunk contains both the token `amd` and the token `competition`. The query is not a company metadata filter.

### Microsoft artificial intelligence

Normalized tokens: `microsoft`, `artificial`, `intelligence`. Matching chunks: **5**.

| Rank | Chunk ID | Document ID | Ticker | Fiscal year | Score |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `MSFT_2024_10K_0122` | `MSFT_2024_10K` | MSFT | 2024 | 4 |
| 2 | `MSFT_2025_10K_0104` | `MSFT_2025_10K` | MSFT | 2025 | 4 |
| 3 | `MSFT_2024_10K_0006` | `MSFT_2024_10K` | MSFT | 2024 | 3 |
| 4 | `MSFT_2024_10K_0203` | `MSFT_2024_10K` | MSFT | 2024 | 3 |
| 5 | `MSFT_2025_10K_0006` | `MSFT_2025_10K` | MSFT | 2025 | 3 |

### Apple services

Normalized tokens: `apple`, `services`. Matching chunks: **57**.

| Rank | Chunk ID | Document ID | Ticker | Fiscal year | Score |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `AAPL_2024_10K_0008` | `AAPL_2024_10K` | AAPL | 2024 | 14 |
| 2 | `AAPL_2025_10K_0008` | `AAPL_2025_10K` | AAPL | 2025 | 14 |
| 3 | `AAPL_2024_10K_0009` | `AAPL_2024_10K` | AAPL | 2024 | 13 |
| 4 | `AAPL_2025_10K_0009` | `AAPL_2025_10K` | AAPL | 2025 | 13 |
| 5 | `AAPL_2025_10K_0085` | `AAPL_2025_10K` | AAPL | 2025 | 13 |

### Google cloud

Normalized tokens: `google`, `cloud`. Matching chunks: **72**.

| Rank | Chunk ID | Document ID | Ticker | Fiscal year | Score |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `GOOGL_2024_10K_0114` | `GOOGL_2024_10K` | GOOGL | 2024 | 19 |
| 2 | `GOOGL_2025_10K_0106` | `GOOGL_2025_10K` | GOOGL | 2025 | 19 |
| 3 | `GOOGL_2025_10K_0242` | `GOOGL_2025_10K` | GOOGL | 2025 | 19 |
| 4 | `GOOGL_2024_10K_0125` | `GOOGL_2024_10K` | GOOGL | 2024 | 17 |
| 5 | `GOOGL_2024_10K_0251` | `GOOGL_2024_10K` | GOOGL | 2024 | 16 |

These results indicate token co-occurrence, not semantic relevance or factual conclusions about the companies.

## 6. Autocomplete Results

Autocomplete was called twice for each normalized prefix with `k = 10`; every repeated call returned the same result.

| Prefix | Suggestions |
| --- | --- |
| `nv` | `nvda`, `nvestment`, `nveu`, `nvidia`, `nvidia's`, `nvidia-accelerated`, `nvidia-based`, `nvl` |
| `artif` | `artificial` |
| `reven` | `revenue`, `revenue-based`, `revenue-generating`, `revenue-sharing`, `revenues` |
| `micro` | `micro`, `microelectronics`, `micron`, `microprocessor`, `microprocessors`, `microsemi`, `microsoft`, `microsoft's`, `microsystems` |
| `compet` | `compete`, `competence`, `competes`, `competing`, `competition`, `competition-related`, `competitive`, `competitively`, `competitiveness`, `competitor` |

Suggestions use unsigned-byte lexicographic order, not vocabulary frequency or semantic relevance. Unusual entries such as `nvestment` and `nveu` are tokens present in the extracted corpus; autocomplete intentionally reports stored vocabulary rather than correcting it.

## 7. Complexity Analysis

Let:

- `L` be a token or prefix length in UTF-8 bytes.
- `B <= 256` be the byte alphabet and `d_i` a visited node's child count.
- `S` be Trie nodes visited during autocomplete and `R` returned string bytes.
- `T` be total indexed token occurrences.
- `U_max` be the maximum unique-token count in one chunk.
- `C` be indexed chunks, `V` indexed tokens, and `P_total` distinct token/chunk postings.
- `q` be unique query terms, `df_i` each postings length, `P = sum(df_i)`, and `M` matched chunks.

Trie insertion, exact search, and prefix search use ordered child maps and take `O(sum(log d_i))`, bounded by `O(L log B)`. This bound is worst-case for the map operations; because `B` is fixed, it is commonly summarized as `O(L)`. Autocomplete costs `O(L log B + S + R)` and is output-sensitive; in the worst case its subtree traversal can approach the number of stored Trie nodes.

Expected index construction is `O(T + P_total log C)`: per-chunk frequency counting and outer token lookup use hash tables, while posting insertion uses ordered maps. With adversarial hash collisions, a conservative worst-case bound is `O(T U_max + P_total V + P_total log C)`. Memory is `O(C + V + P_total)` plus stored strings and container overhead.

A copied single-token lookup costs expected `O(1 + df)` and worst-case `O(V + df)` because the outer hash lookup can degrade. AND lookup orders lists by length and performs sorted intersections in expected `O(q log q + P)`; its collision-heavy worst case adds `O(qV)`. Sequential OR union costs expected `O(q + P + qC)` in the worst merge pattern, with another `O(qV)` possible from adversarial hash lookup.

After matching, ranking performs `Mq` term-frequency lookups and sorts `M` results. Expected cost is `O(Mq log C + M log M)`. Collision-heavy worst case is `O(Mq(V + log C) + M log M)`. The cost of the preceding AND or OR matching step must also be included.

pybind11 preserves these algorithmic bounds. It adds fixed call overhead and approximately `O(I + O)` conversion time for total transferred input bytes/items `I` and output bytes/items `O`.

## 8. Testing and Validation

The verified commands were:

```bash
.venv/bin/cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python"
.venv/bin/cmake --build build --clean-first --parallel
.venv/bin/ctest --test-dir build --output-on-failure
PYTHONPATH=build/python .venv/bin/python -m pytest tests -q
PYTHONPATH=build/python .venv/bin/python -m src.python.search_demo
```

Results:

- CMake configuration and Apple Clang C++17 compilation: successful.
- Native `investment_engine` extension compilation and import: successful.
- C++ tests: **24 of 24 passed**.
- Python tests: **57 of 57 passed**.
- Real-data Python demonstration: successful.
- Representative query and autocomplete runs: successful and deterministic.

Tests and source inspection confirmed that Trie operations call `trie.cpp`, index operations call `inverted_index.cpp`, and Python only delegates through `python_bindings.cpp`. Repeated terms increase frequency without duplicate postings. Financial punctuation and UTF-8 values are accepted safely. In the real vocabulary, `s&p`, `ai-powered`, and `nvidia's` exist; the valid normalized example tokens `$97,858` and `12.5%` do not occur in this particular corpus and therefore correctly return no vocabulary match.

## 9. Limitations

- Retrieval is lexical token matching, not semantic search.
- Query company names are terms, not ticker or company metadata filters.
- Ranking uses raw term frequency and favors repetition, longer passages, and overlapping chunks.
- The index stores no positions, so phrase and proximity queries are unavailable.
- Autocomplete is bytewise lexicographic and can expose extraction artifacts.
- The full vocabulary, processed collection, Trie, and index are loaded in memory; Python/C++ result conversion creates additional copies.
- C++ direct calls expect normalized tokens. Raw queries should use the Python wrapper.
- Python extension modules are ABI-specific and must be rebuilt for another Python version or architecture.
- No KMP, Z-function, Levenshtein distance, n-gram/Jaccard similarity, TF-IDF, BM25, language-model integration, or frontend is implemented.

## 10. Conclusion

Stage 2 is ready to be considered complete. The real ten-document corpus is deterministically preprocessed, all 2,458 chunks and 14,180 tokens are represented consistently across Python and C++, metadata is preserved, native retrieval is accessible from Python, representative lexical queries return reproducible results, and all automated tests pass. The observed limitations are explicit design boundaries for later stages rather than validation failures.
