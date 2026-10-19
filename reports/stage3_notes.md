# Stage 3 Notes: Exact String Matching

## Scope

Step 14 added a custom C++17 Knuth-Morris-Pratt implementation. Step 15 added a custom C++17 Z-function implementation and compared its exact matches with KMP. Step 16 exposed both implementations through pybind11 and added exact phrase retrieval to the existing Python `SearchEngine`. Step 17 adds occurrence-count ranking, top-k selection, and optional ticker/year filtering to that exact retrieval path. Stage 3 does not add approximate matching, similarity algorithms, TF-IDF, BM25, or AI integration.

## KMP Design

`computeLps` preprocesses the pattern into the longest-proper-prefix/suffix table. During search, a mismatch after a partial match falls back to the previous LPS length instead of restarting the pattern or moving the text cursor backward. After a complete match, the same fallback preserves overlapping occurrences. `kmpSearch` returns every ascending zero-based position, and `kmpCount` counts matches without allocating a position vector.

The empty-pattern policy is no matches and count zero. Patterns longer than the text also return no matches. Matching uses exact `std::string` byte equality with no implicit normalization. UTF-8 input is supported as bytes, so offsets are byte positions rather than Unicode code-point positions.

## Verified Examples

- `research` in `investment research assistant`: position `[11]`.
- `revenue` in `revenue and revenue growth`: positions `[0, 12]`.
- `aaa` in `aaaaa`: overlapping positions `[0, 1, 2]`.
- `artificial intelligence` in the synthetic phrase: position `[0]`.
- `$97,858` in `revenue increased 12.5% to $97,858`: position `[27]`.
- `artificial intelligence` in the reconstructed normalized token stream of real chunk `NVDA_2024_10K_0009`: byte position `[461]` and count 1.

The real demonstration joins the chunk's already-normalized tokens with single spaces. Its offsets therefore refer to that reconstructed normalized token stream, not the original SEC HTML or extracted source text.

## Complexity

Let `n` be the text length in bytes and `m` the pattern length in bytes.

- LPS construction: `O(m)` time.
- KMP scan: `O(n)` time because neither mismatch fallback nor matching moves the text cursor backward, and pattern fallback is bounded across the scan.
- Combined preprocessing and search: `O(n + m)` time.
- Auxiliary space: `O(m)` for the LPS table.
- Search output: an additional `O(z)` space for `z` returned match positions; counting uses only `O(1)` beyond the LPS table.

## Testing and Limitations

Fifteen CTests cover basic and absent matches, multiple and overlapping matches, boundaries, full-text equality, long and empty patterns, empty text, repeated prefixes, financial punctuation, UTF-8, LPS correctness, and byte offsets. The expected LPS array for `ABABCABAB` is `[0, 0, 1, 2, 0, 1, 2, 3, 4]`.

KMP is exact and case-sensitive. It does not tokenize, normalize, rank, interpret Unicode code points, or constrain matches to token boundaries. Step 16 exposes this unchanged implementation through pybind11; normalization and optional boundary filtering belong to the Python retrieval layer.

## Z-function Design

`computeZ` uses the standard linear Z-box `[l, r)`. For each position inside the current box, the algorithm copies a previously computed prefix-match length up to the remaining box boundary; it then compares further bytes only if the match can extend `r`. Each successful extension advances the right boundary, preventing repeated comparison of already established ranges. `Z[0]` is defined as zero.

`zSearch` and `zCount` compute the Z-array over `pattern + separator + text`. They convert each input byte through `unsigned char` to an integer in `0..255` and use `256` as a dedicated separator. The separator cannot collide with punctuation, embedded null bytes, byte 255, or any UTF-8 byte. All returned offsets are therefore exact byte offsets, and C++ applies no normalization. Empty patterns return no positions and count zero; empty text and patterns longer than the text also have no matches. Overlaps are retained.

## Z-function Verified Examples

- `computeZ("abacaba")`: `[0, 0, 1, 0, 3, 0, 1]`.
- `computeZ("aaaaa")`: `[0, 4, 3, 2, 1]`.
- `research` in `investment research assistant`: position `[11]`.
- `revenue` in `revenue and revenue growth`: positions `[0, 12]`.
- `aaa` in `aaaaa`: overlapping positions `[0, 1, 2]`.
- `$97,858` in `revenue increased 12.5% to $97,858`: position `[27]`.
- `é` in `café café`: byte positions `[3, 9]`.
- `artificial intelligence` in real normalized chunk `NVDA_2024_10K_0009`: byte position `[461]`.

The Z-function and KMP demonstrations agreed on every shared synthetic example and on the real NVIDIA chunk. As with the KMP example, the real offset refers to tokens reconstructed with single spaces rather than to the original filing.

## Z-function Complexity and Comparison

For `n` text bytes, `m` pattern bytes, and `z` matches:

- Direct Z-array construction is `O(n)` time.
- Search and count are `O(n + m)` time.
- The combined integer sequence and Z-array use `O(n + m)` auxiliary space.
- Returning positions adds `O(z)` output space; counting does not store positions.

KMP and the Z-function both provide `O(n + m)` total exact-search time. KMP stores an `O(m)` LPS table and uses it to select the next pattern prefix after a mismatch. This Z-function implementation stores an `O(n + m)` combined sequence and Z-array and reuses prefix-match lengths within the Z-box.

## Z-function Testing and Limitations

Seventeen CTests cover basic, repeated-prefix, and empty Z-arrays; basic, absent, multiple, overlapping, boundary, full-text, longer-pattern, and empty-input matches; punctuation; UTF-8; embedded nulls; collision safety including byte 255; determinism; and 500 reproducible random byte-string comparisons against KMP using seed `20261019`.

The implementation is exact and case-sensitive, is not Unicode-code-point aware, and does not enforce token boundaries internally. Step 16 exposes it through pybind11 and performs optional boundary filtering in Python without integrating exact matches into ranking. No performance benchmark was performed in Step 15 or Step 16.

## Step 15 Verification

The Release build and complete regression suites were run with:

```bash
.venv/bin/cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python"
.venv/bin/cmake --build build --parallel
.venv/bin/ctest --test-dir build --output-on-failure
PYTHONPATH=build/python .venv/bin/python -m pytest tests -q
./build/kmp_demo data/processed/preprocessed_collection.json
./build/z_function_demo data/processed/preprocessed_collection.json
PYTHONPATH=build/python .venv/bin/python -m src.python.search_demo
```

All 17 Z-function tests passed as part of 56/56 C++ tests, and all 57/57 Python tests passed. The existing search demonstration still loaded 14,180 vocabulary tokens and 2,458 indexed chunks. Hashes of all 48 files under the four data directories were unchanged across final validation. The previously recorded SHA-256 values also remained unchanged for `collection.json` (`54840f7ab9d9be4ae79729d8ab9d4f2ad6d73af4504c2c4538a17e93c7283442`), `preprocessed_collection.json` (`312a4b8f39e40c52a6722d0444cfd89ac0fb1ab49d275826f1a355067df45c00`), and `vocabulary.json` (`27c81f1015f3dcc71d36cf2ae0eb388d0ffc1bdc8b2d17fe34840cb298c3f006`).

## Step 16 Python Bindings

The `investment_engine` extension now links the existing `kmp_core` and `z_function_core` targets. It exposes:

- `compute_lps(pattern)`, `kmp_search(text, pattern)`, and `kmp_count(text, pattern)`.
- `compute_z(text)`, `z_search(text, pattern)`, and `z_count(text, pattern)`.

The search functions return ascending, zero-based byte offsets and preserve overlapping matches and the empty-pattern policy. pybind11 converts Python `str` objects to length-aware UTF-8 `std::string` values. Tests verified that non-ASCII strings and embedded NUL characters survive this conversion. Direct binding calls do not normalize either string.

## Exact Retrieval Semantics

`SearchEngine.exact_phrase_search` accepts `algorithm="kmp"` or `algorithm="z"` and returns dictionaries containing the chunk ID, document ID, ticker, fiscal year, match count, match byte offsets, and algorithm. It normalizes the query with the existing NFKC, apostrophe/dash mapping, case-folding, and whitespace policy, then searches each chunk's stored `normalized_text`. This representation preserves normalized punctuation and is canonical for Step 16. Offsets refer to its UTF-8 encoding—not the original SEC source, Python character indexes, or a joined-token reconstruction.

Token-boundary filtering is enabled by default. A retained match must begin at a tokenizer token start and end at a tokenizer token end, so `ai` does not match within `paid` or the larger token `ai-powered`. Callers can disable this filter for ordinary substring behavior; the underlying C++ algorithms always remain substring matchers.

When boundary matching is enabled and the normalized pattern is exactly its tokenizer tokens joined with single spaces, AND retrieval over the unique tokens supplies candidates. This is safe because every accepted exact match necessarily contains those indexed tokens. The following cases use a deterministic full scan instead:

- Token boundaries are disabled, because a requested substring may occur inside a larger indexed token.
- The normalized query differs from its space-joined tokens, including punctuation arrangements that the tokenizer discards or separates.
- The query produces no tokens.

The fallback avoids false negatives such as searching for `$97` inside the indexed token `$97,858`. Exact retrieval does not alter the inverted index or its term-frequency ranking.

## Step 16 Verified Examples

- Both algorithms found `artificial intelligence` in 30 real chunks with identical counts and offsets.
- In stored `normalized_text`, `NVDA_2024_10K_0009` has that phrase at byte offset `[468]`. The Step 14/15 offset `[461]` remains correct for the separate joined-token demo representation.
- `$0.001` matched four chunks: `GOOGL_2024_10K_0001` and `GOOGL_2025_10K_0001` twice each at `[1014, 1118]`, and `NVDA_2024_10K_0001` and `NVDA_2025_10K_0001` once each at `[886]`.
- The no-match query in the demonstration returned no chunks.

## Step 16 Commands and Limitations

```bash
.venv/bin/cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python"
.venv/bin/cmake --build build --parallel
.venv/bin/ctest --test-dir build --output-on-failure
PYTHONPATH=build/python .venv/bin/python -m pytest tests -q
PYTHONPATH=build/python .venv/bin/python -m src.python.exact_search_demo
```

At the end of Step 16, exact retrieval was deterministic but not yet ranked or filterable by company/year. It was not Unicode-code-point aware, and no benchmark was performed. The Python layer retained every normalized chunk string in memory in addition to the C++ inverted index, while full-scan fallback ran the selected linear matcher once per chunk.

Final verification passed 56/56 C++ tests and 72/72 Python tests, including all 15 new exact-search tests. The existing search demonstration still reported 14,180 vocabulary tokens, 2,458 indexed chunks, and the same Boolean and ranked results. All 48 files under `data/raw`, `data/processed`, `data/chunks`, and `data/metadata` retained identical before/after hashes. The three previously recorded collection hashes also remained unchanged.

## Step 17 Exact Match Ranking

Exact phrase results now define:

`score(chunk, query) = number of exact phrase occurrences in the chunk`

The score is computed as the length of the byte-offset list returned by the selected C++ matcher after optional token-boundary filtering. It therefore equals `match_count` and cannot diverge from the actual accepted matches. Results sort by descending score, then ascending chunk ID for deterministic ties. KMP and the Z-function use the same Python ranking path and produce identical rankings when their offsets agree.

The optional `top_k` argument is applied after the complete ranking. Omitting it returns all matching chunks, zero returns an empty list, a value larger than the available result count returns every match, and a negative value raises `ValueError`.

## Step 17 Metadata Filters

The optional `ticker` and `fiscal_year` arguments compare against actual chunk metadata from the C++ index. Tickers are stripped and compared case-insensitively. Unknown tickers return an empty list without error. Ticker-only, year-only, combined, and unfiltered searches are supported.

Filtering occurs after safe inverted-index candidate selection but before the selected KMP or Z-function call. It therefore avoids matching text from excluded chunks while preserving both candidate modes: canonical token phrases use AND candidates, while unsafe tokenization cases continue to use the full-scan fallback before metadata pruning. Filters never inspect query keywords and do not affect Stage 2 term-frequency ranking.

The implemented API is:

```python
engine.exact_phrase_search(
    query,
    algorithm="kmp",       # "kmp" or "z"
    token_boundaries=True,
    ticker=None,            # case-insensitive when provided
    fiscal_year=None,
    top_k=None,
)
```

Every result preserves the previous fields and adds `score`.

## Step 17 Verified Results

- `artificial intelligence` matched 30 chunks with identical KMP and Z-function rankings.
- `GOOGL_2025_10K_0067` ranked first with score/count 2 and offsets `[723, 1000]`.
- The remaining displayed top-five results each scored 1 and were tie-broken by chunk ID.
- Case-insensitive ticker filtering for `nvda` returned NVIDIA chunks only.
- Fiscal-year filtering for 2025 ranked the same Alphabet chunk first with score 2.
- Combined NVDA/FY2025 filtering returned `NVDA_2025_10K_0009` at `[468]` and `NVDA_2025_10K_0121` at `[397]`, each with score 1.
- `$0.001` ranked both Alphabet chunks at score 2 before both NVIDIA chunks at score 1.
- The demonstration's absent phrase returned no results.

## Step 17 Complexity and Limitations

Let `C` be the number of chunks remaining after candidate selection, `n_i` each candidate's byte length, `m` the pattern byte length, and `M` the number of matching chunks.

- Metadata filtering is `O(C)` time and occurs before exact matching.
- Running either matcher across candidates costs `O(sum(n_i + m))`; each individual invocation remains `O(n_i + m)`.
- Recording scores is `O(M)` because each score is the already-known offset count.
- Deterministic sorting is `O(M log M)` time and `O(M)` result storage.
- Applying top-k after sorting copies/slices at most `O(min(k, M))` result references; the implementation deliberately performs the full sort first.

Frequency-only ranking rewards phrase repetition but does not account for document length, phrase rarity, financial importance, recency, context quality, or semantics. The Python layer still retains normalized chunk text alongside the C++ index. Full-scan fallback can examine the entire collection, no company/year lookup table is maintained, and no benchmark was performed.

Final Step 17 verification passed 56/56 C++ tests and 83/83 Python tests, including 26 exact-search tests. The updated exact-search demonstration and the existing Stage 2 search demonstration both completed successfully. All 48 files under the four data directories retained identical before/after hashes; the recorded hashes for `collection.json`, `preprocessed_collection.json`, and `vocabulary.json` also remained unchanged.
