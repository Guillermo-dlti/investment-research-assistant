# Stage 3 Notes: Exact String Matching

## Scope

Step 14 added a custom C++17 Knuth-Morris-Pratt implementation. Step 15 adds a custom C++17 Z-function implementation and compares its exact matches with KMP. These steps do not add approximate matching, similarity algorithms, ranking integration, or Python bindings for either matcher.

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

KMP is exact and case-sensitive. It does not tokenize, normalize, rank, interpret Unicode code points, or constrain matches to token boundaries. It is currently available only through the C++ API and executable.

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

The implementation is exact and case-sensitive, is not Unicode-code-point aware, and does not enforce token boundaries. It has not been exposed through pybind11 or integrated into retrieval and ranking. No performance benchmark was performed in Step 15.

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
