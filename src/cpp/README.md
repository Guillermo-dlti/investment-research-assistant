# C++ Algorithms and Data Structures

This directory contains custom C++17 data structures and algorithms for the normalized financial corpus: a Trie for vocabulary lookup, an inverted index for chunk retrieval, and KMP and Z-function exact matchers.

## Components

- `trie.h` and `trie.cpp`: insertion, exact search, prefix search, autocomplete, and unique-token count.
- `vocabulary_loader.h` and `vocabulary_loader.cpp`: a standard-library-only reader for the generated `vocabulary.json` schema.
- `trie_demo.cpp`: loads the real vocabulary and demonstrates all public Trie operations.
- `tests/trie_tests.cpp`: portable synthetic tests and local full-vocabulary tests.
- `inverted_index.h` and `inverted_index.cpp`: postings, Boolean queries, metadata, and raw term-frequency ranking.
- `preprocessed_collection_loader.h` and `preprocessed_collection_loader.cpp`: validated loading of chunk IDs, tokens, and filing metadata.
- `inverted_index_demo.cpp`: indexes the real preprocessed collection and demonstrates retrieval and ranking.
- `tests/inverted_index_tests.cpp`: eleven portable tests and one local real-collection integration test.
- `json_reader.h` and `json_reader.cpp`: the shared standard-library-only JSON reader used by both loaders.
- `python_bindings.cpp`: pybind11 definitions for the Trie, inverted index, KMP, Z-function, metadata, rankings, and C++ file loaders.
- `kmp.h` and `kmp.cpp`: LPS construction, exact KMP search, and match counting.
- `kmp_demo.cpp`: synthetic and real normalized-chunk matching examples.
- `tests/kmp_tests.cpp`: fifteen portable KMP test cases.
- `z_function.h` and `z_function.cpp`: linear Z-array construction, exact search, and match counting.
- `z_function_demo.cpp`: Z-array, synthetic matching, and real normalized-chunk examples compared with KMP.
- `tests/z_function_tests.cpp`: seventeen portable Z-function test categories, including fixed-seed KMP comparisons.

No external Trie or JSON library is used. Nodes own their children with `std::unique_ptr`, and each node uses `std::map<unsigned char, ...>` so traversal is deterministic and bytewise lexicographic.

## Build and Run

From the repository root, with the Python virtual environment activated so its CMake executable is available:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/trie_demo data/metadata/vocabulary.json
./build/inverted_index_demo data/processed/preprocessed_collection.json
./build/kmp_demo data/processed/preprocessed_collection.json
./build/z_function_demo data/processed/preprocessed_collection.json
PYTHONPATH=build/python python -m src.python.search_demo
PYTHONPATH=build/python python -m src.python.exact_search_demo
ctest --test-dir build --output-on-failure
```

The local vocabulary and preprocessed collection are generated and ignored by Git. If either is absent when CMake is configured, its integration tests are not registered, while all synthetic tests remain available. Generate both with `src/python/preprocess_text.py`, then configure CMake again. Alternate paths can be selected with `-DTRIE_VOCABULARY_PATH=/absolute/path/to/vocabulary.json` and `-DPREPROCESSED_COLLECTION_PATH=/absolute/path/to/preprocessed_collection.json`.

## Token and Ordering Policy

The Trie consumes tokens already normalized by Python. It does not lowercase, case-fold, normalize Unicode, or otherwise modify input. A C++ `std::string` is traversed one unsigned UTF-8 byte at a time. Valid UTF-8 tokens are stored and recovered unchanged, although the Trie does not understand Unicode character boundaries. A malformed or partial byte prefix is therefore still treated as a byte sequence. Autocomplete uses unsigned-byte lexicographic order rather than locale-aware or frequency-based ranking.

The loader reads the actual object schema and validates `unique_tokens` against the `token_frequencies` array. Each array item must contain a token string and a positive integer frequency, and duplicate token strings are rejected. Its schema-aware JSON reader supports UTF-8 and escaped JSON strings without adding a third-party dependency.

## Complexity

Let `L` be the input token or prefix length in bytes, `d_i` the number of children at the node visited for byte `i`, and `B <= 256` the byte alphabet size.

- Insertion, exact search, and prefix search take `O(sum(log d_i))`, bounded by `O(L log B)`. Since `B` is fixed, this is commonly described as `O(L)`.
- Autocomplete takes `O(L log B + S + R)`, where `S` is the number of Trie nodes visited while enumerating at most `k` matches and `R` is the total number of bytes copied into returned strings. It is output-sensitive and is not always `O(L)`.
- Memory is `O(N)` Trie nodes in the worst case, where `N` is the sum of byte lengths of all distinct inserted tokens, plus ordered-map and ownership overhead at each node. Shared prefixes reduce the actual node count.

Current Trie limitations include bytewise rather than Unicode-aware traversal, ordered-map overhead, lexicographic rather than frequency-ranked autocomplete, and an in-memory vocabulary load.

## Inverted Index Behavior

The inverted index uses `token -> {chunk_id -> term_frequency}`. The outer token table is hash-based for average constant-time term access; each postings list is an ordered map so chunk IDs are unique and deterministic. AND queries intersect sorted postings lists, starting with the shortest. OR queries merge sorted postings lists. Empty queries return no results and absent terms behave normally: an absent AND term empties the result, while absent OR terms contribute nothing.

For `q` unique query terms, let `df_i` be each term's postings length, `P = sum(df_i)`, `M` the number of matched chunks, `C` the total chunks, and `V` the vocabulary size. Under average hash-table behavior, a copied single-token lookup costs `O(1 + df)`; AND costs `O(q log q + P)` after ordering lists by size; and sequential OR merging costs up to `O(qC + P)`. Ranking after matching costs `O(Mq log C + M log M)` with ordered postings lookups and final score sorting. With adversarial collisions, each outer token-table lookup can degrade from `O(1)` average to `O(V)` worst case, adding `O(qV)` to Boolean lookup or `O(MqV)` to scoring. Index memory is `O(C + V + P_total)`, where `P_total` is the total number of distinct token/chunk pairs.

Raw term-frequency ranking sums occurrences of unique query terms. It can overvalue repetition and overlapping chunks and does not normalize for chunk length or token rarity. The index holds the complete collection in memory. Exact matching is not yet integrated with ranking; approximate matching, n-grams, Jaccard similarity, and benchmarks remain future work.

## Python Extension

CMake uses the selected Python interpreter to locate pybind11 and writes the `investment_engine` extension to `build/python/`. To guarantee that configuration uses the project environment, pass the interpreter explicitly:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python"
cmake --build build --parallel
PYTHONPATH=build/python .venv/bin/python -c "import investment_engine"
```

The module exposes:

- `Trie`: `insert`, `search`, `starts_with`, `autocomplete`, and `size`.
- `InvertedIndex`: `add_chunk`, `lookup`, `and_query`, `or_query`, term/document frequency, ranked AND/OR, metadata, chunk count, and vocabulary size.
- `RankedChunk`: read-only `chunk_id` and `score` fields.
- `load_trie(path)` and `load_inverted_index(path)`: factories backed by the existing C++ JSON loaders.
- `compute_lps`, `kmp_search`, and `kmp_count`: direct calls to the C++ KMP implementation.
- `compute_z`, `z_search`, and `z_count`: direct calls to the C++ Z-function implementation.

Python strings are converted to length-aware UTF-8 `std::string` values by pybind11 and remain subject to the C++ components' byte-oriented behavior. Embedded NUL characters are preserved. Direct exact-matcher calls do not normalize input; the Python `SearchEngine` wrapper applies the existing preprocessing functions when accepting raw query text.

Interop converts Python strings and token lists into C++ values and copies C++ result vectors back into Python objects. For input size `I` and returned data size `O`, this adds approximately `O(I + O)` conversion work and corresponding temporary allocations. It does not change Trie lookup, postings intersection/union, or ranking complexity. Fine-grained calls can incur noticeable fixed interpreter-boundary overhead even when the C++ operation is small.

The extension has no stable binary compatibility across unrelated Python versions; rebuild it with the exact interpreter that will import it. The verified environment used Python 3.14.7 with pybind11 3.1.0 and Apple Clang 21. Approximate matching, AI integration, and the frontend remain absent.

## KMP Exact Matching

`computeLps(pattern)` records, for each pattern byte, the length of the longest proper prefix that is also a suffix. On mismatch, `kmpSearch(text, pattern)` uses this table to retain known prefix information instead of moving the text cursor backward. `kmpCount` uses the same scan without storing positions. Overlapping matches are retained by falling back through the LPS table after every match.

Matching is byte-oriented. Valid UTF-8, currency symbols, percentages, punctuation, and hyphenated text are preserved, but returned positions are byte offsets and C++ performs no normalization. Empty patterns intentionally return no positions and count zero.

For `n` text bytes and `m` pattern bytes, LPS construction takes `O(m)` time and search takes `O(n)` time, for `O(n + m)` total. Auxiliary space is `O(m)` for LPS, plus `O(z)` output space for `z` returned positions. The demo found `artificial intelligence` in the real normalized token stream for `NVDA_2024_10K_0009` at byte offset 461.

## Z-function Exact Matching

`computeZ(text)` computes the bytewise Z-array, where each entry is the length of the longest prefix also beginning at that position and `Z[0] = 0`. The linear algorithm maintains a known matching Z-box `[l, r)`. For an index inside the box it reuses a previously computed value up to the remaining box length, then performs new comparisons only when extending past `r`. `zSearch(text, pattern)` returns every ascending zero-based byte offset, including overlaps, while `zCount` performs the same scan without storing offsets.

Search constructs an integer sequence from the pattern, a separator, and the text. Input bytes are converted through `unsigned char` to values `0..255`; the separator is the distinct value `256`. It therefore cannot collide with arbitrary punctuation, embedded nulls, byte 255, or UTF-8 bytes. Matching is exact and performs no normalization or Unicode decoding, so returned offsets count bytes. Empty patterns intentionally produce no positions and count zero; empty text and patterns longer than the text also produce no matches.

Run the demonstration and focused tests from the repository root:

```bash
./build/z_function_demo data/processed/preprocessed_collection.json
ctest --test-dir build -L z_function --output-on-failure
```

For text length `n` and pattern length `m`, search takes `O(n + m)` time. Its combined sequence and Z-array require `O(n + m)` auxiliary space, with another `O(z)` when returning `z` positions. A direct Z-array for a sequence of length `n` takes `O(n)` time and space. KMP provides the same `O(n + m)` total time but uses an `O(m)` LPS table instead of materializing the combined input and Z-array. KMP responds to mismatches using prefix/suffix fallback lengths; the Z-function reuses known prefix matches inside its Z-box. Both demos agree on the synthetic examples and find `artificial intelligence` in real normalized chunk `NVDA_2024_10K_0009` at byte offset 461.

## Python Exact Search Integration

`SearchEngine.exact_phrase_search` normalizes a query with the existing Python policy, then calls either the bound C++ KMP or Z-function implementation against stored `normalized_text`. It returns chunk metadata, match count, ascending UTF-8 byte offsets, selected algorithm, and an occurrence-count score. Results rank by descending score and ascending chunk ID; Python applies optional top-k, ticker, and fiscal-year filters without changing either C++ matcher or the inverted index. Optional token-boundary filtering requires the match to span complete tokens according to the existing tokenizer.

For canonical token phrases in boundary mode, the inverted index first selects chunks containing every unique phrase token. The matcher verifies the exact order and intervening characters. Unbounded substring searches and patterns not identical to their space-joined token sequence scan all chunks, because index filtering could otherwise miss a substring embedded in a larger financial token. The Python layer retains normalized text in memory in addition to the C++ index; this simplifies exact verification but increases memory use. It does not change the inverted-index implementation or term-frequency ranking.

The Python integration searches stored `normalized_text`, so its offsets can differ from the standalone C++ demos, which join token arrays with spaces. For example, `artificial intelligence` begins at byte 468 in the stored text of `NVDA_2024_10K_0009`, while it begins at byte 461 in that demo's joined-token representation.
