# Stage 3 Notes: Knuth-Morris-Pratt

## Scope

Step 14 adds only a custom C++17 Knuth-Morris-Pratt implementation. It does not add Z-function, approximate matching, similarity algorithms, ranking integration, or Python bindings.

## Design

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

KMP is exact and case-sensitive. It does not tokenize, normalize, rank, interpret Unicode code points, or constrain matches to token boundaries. It is currently available only through the C++ API and executable. Z-function and all later Stage 3 algorithms remain unimplemented.
