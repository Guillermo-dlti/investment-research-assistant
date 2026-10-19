# Stage 2 Notes: Text Preprocessing

## Scope

Step 9 creates deterministic normalized text, token arrays, and a vocabulary for the 2,458 chunks in `data/chunks/collection.json`. It does not modify the consolidated collection, extracted documents, or individual chunk files. It also does not implement the planned C++ Trie, inverted index, or matching and similarity algorithms.

## Decisions and Rationale

Normalization uses Unicode NFKC so compatibility characters such as full-width letters have a consistent representation. Common Unicode apostrophe and dash/minus variants are converted to their ASCII equivalents before case normalization with `casefold()`. Whitespace runs are collapsed to a single ASCII space. These rules reduce superficial variations while retaining a normalized copy separate from the original chunk text.

Tokenization uses a deterministic Python regular expression. Its policy is:

- Ordinary Unicode words and case-folded stock tickers are tokens.
- Currency signs stay attached to their amounts, including comma separators and decimals.
- Signs, thousands separators, decimal points, and percentage signs stay attached to numbers.
- Hyphenated compounds and apostrophe compounds stay intact.
- Ampersand terms remain intact, while an adjacent number is separate: `S&P 500` becomes `s&p` and `500`.
- Multi-period abbreviations such as `U.S.` remain intact.
- Stopwords and numbers are retained, and no stemming or lemmatization is applied.

This conservative approach keeps financially meaningful surface forms available for later exact matching, approximate matching, n-gram comparison, Trie lookup, and inverted indexing. The policy is embedded in both generated JSON outputs so consumers can identify how the data was produced.

## Observed Results

The complete real collection produced:

- Processed chunks: 2,458
- Total token occurrences: 579,089
- Unique tokens: 14,180
- Duplicate chunk IDs: 0
- Empty normalized chunks: 0

The 15 most frequent tokens, ordered by descending frequency and then token for ties, are:

| Rank | Token | Frequency |
| ---: | --- | ---: |
| 1 | `and` | 27,407 |
| 2 | `the` | 22,047 |
| 3 | `of` | 20,171 |
| 4 | `to` | 14,629 |
| 5 | `our` | 11,570 |
| 6 | `in` | 11,119 |
| 7 | `or` | 7,100 |
| 8 | `for` | 5,823 |
| 9 | `we` | 5,514 |
| 10 | `a` | 5,309 |
| 11 | `as` | 5,126 |
| 12 | `on` | 4,764 |
| 13 | `are` | 3,867 |
| 14 | `that` | 3,451 |
| 15 | `other` | 3,253 |

All input chunk IDs were preserved exactly once and in their original order. The token-frequency records exactly matched frequencies recomputed from the output chunks. Running the pipeline twice produced byte-identical files. The source collection's SHA-256 remained `54840f7ab9d9be4ae79729d8ab9d4f2ad6d73af4504c2c4538a17e93c7283442` before and after preprocessing.

## Complexity

Let `C` be the total number of input characters, `T` the total number of emitted token occurrences, and `V` the number of unique tokens.

- Unicode, case, whitespace, and token processing are linear in the input size: **O(C)** time.
- Frequency counting is **O(T)** expected time with a hash-based counter.
- Lexicographically sorting the vocabulary is **O(V log V)** time.
- The implementation retains normalized records and their token arrays for JSON output, using **O(C + T + V)** memory in addition to the parsed input and serialized output. A future streaming format could reduce peak memory, but JSON's single collection container currently favors a complete in-memory build.

## Limitations

- Regex tokenization is intentionally lexical and does not infer financial meaning or context.
- Equivalent values with different spellings, such as `$1,000` and `$1000`, remain distinct tokens.
- Case distinctions are absent from normalized tokens, though the original text remains unchanged in the Stage 1 collection.
- Stopwords dominate the most frequent terms because this stage explicitly retains them.
- Overlap between adjacent Stage 1 chunks repeats some source text, so collection-wide token frequencies include those repeated passages.
- The generated vocabulary is prepared for later C++ consumption, but no Trie, inverted index, search, ranking, or pybind11 integration exists at this stage.
