# Stage 2 Notes: Text Preprocessing

## Scope

Step 9 creates deterministic normalized text, token arrays, and a vocabulary for the 2,458 chunks in `data/chunks/collection.json`. It does not modify the consolidated collection, extracted documents, or individual chunk files. Step 9 itself did not implement the planned C++ structures or matching and similarity algorithms; Step 10 now adds only the Trie.

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
- The generated vocabulary is consumed by the Step 10 Trie. No inverted index, document search, ranking, or pybind11 integration exists at this stage.

## Step 10: C++17 Trie

### Design

The Trie stores one normalized token per terminal path. Each node owns its descendants with `std::unique_ptr`, providing automatic recursive cleanup through RAII. Children use `std::map<unsigned char, std::unique_ptr<Node>>`; the ordered unsigned-byte keys make depth-first autocomplete deterministic without a separate sorting pass. Repeated insertion marks the same terminal node and does not increase the unique-token count.

The public operations are:

- `insert(word)`: add a complete token.
- `search(word)`: require a matching path whose final node is terminal.
- `startsWith(prefix)`: require only a matching path.
- `autocomplete(prefix, k)`: enumerate no more than `k` terminal paths in bytewise lexicographic order.

An empty prefix refers to the root and can enumerate the entire vocabulary subject to `k`. A zero limit and missing prefixes return an empty result. The empty string itself is treated consistently as a possible complete token if explicitly inserted, although the generated financial vocabulary does not contain it.

### UTF-8 Handling

The Trie walks `std::string` values as unsigned bytes rather than decoding Unicode code points. This supports arbitrary normalized UTF-8 and financial punctuation without restricting children to `a-z`, and valid strings are recovered unchanged. Prefixes and ordering are nevertheless byte-based: the structure does not recognize character boundaries or apply locale collation. C++ performs no normalization, case conversion, or punctuation conversion, preventing a second policy from diverging from Python preprocessing.

### Vocabulary Loading and Verification

A schema-aware JSON reader implemented with the C++ standard library loads `unique_tokens` and every `{token, frequency}` object from `token_frequencies`. It handles raw UTF-8, JSON escapes, and Unicode escapes; validates required fields, positive frequencies, declared size, and uniqueness; and requires no external JSON dependency.

The real demonstration loaded and inserted all **14,180** declared tokens. Verified examples included successful exact searches for `nvidia`, `nvda`, and `s&p`; a missing synthetic term and unnormalized `NVIDIA` returned false. Prefix checks and autocomplete were exercised for financial terms, an empty prefix, a missing prefix, and `k = 0`.

CMake/CTest registered ten portable synthetic tests and two tests that depend on the locally generated, Git-ignored vocabulary. All **12 of 12 C++ tests passed**. The local tests verify both real-file loading and the full 14,180-token Trie size.

### Complexity

Let `L` be the token or prefix length in bytes, `d_i` the child count at the node reached for byte `i`, `B <= 256` the byte alphabet, `S` the number of nodes visited during completion enumeration, `R` the total bytes copied into returned strings, and `N` the sum of byte lengths of all distinct inserted tokens.

- Insertion: `O(sum(log d_i))`, with worst-case bound `O(L log B)` because children use ordered maps.
- Exact search: `O(sum(log d_i))`, bounded by `O(L log B)`.
- Prefix search: `O(sum(log d_i))`, bounded by `O(L log B)`.
- Autocomplete: `O(L log B + S + R)` for prefix traversal, subtree enumeration, and result copying. Its cost depends on the explored/output subtree and is not simply `O(L)`.
- Memory: `O(N)` nodes in the worst case plus the per-node ordered-map and smart-pointer overhead. Shared prefixes reduce node count.

Because the alphabet contains at most 256 byte values, `log B` is a fixed bound, so lookup operations are often summarized as linear in input bytes. The more precise map-based bounds above describe this implementation.

### Limitations

- Autocomplete is bytewise lexicographic and does not use vocabulary frequencies.
- The Trie is byte-oriented rather than Unicode-code-point-aware or locale-aware.
- The schema-aware loader intentionally targets the generated vocabulary structure rather than serving as a general-purpose JSON library.
- The entire vocabulary and Trie are held in memory.
- Step 10 did not add an inverted index or later matching features. Step 11 now adds only the custom inverted index; KMP, Z-function, Levenshtein distance, n-gram/Jaccard similarity, pybind11 integration, and benchmarking remain unimplemented.

## Step 11: C++17 Inverted Index

### Structure and Policies

The index maps each normalized token to an ordered map from chunk ID to term frequency: `token -> {chunk_id -> term_frequency}`. The outer token map uses `std::unordered_map` for average constant-time token access. Each postings map uses `std::map`, which guarantees unique chunk IDs and ascending deterministic order. Chunk metadata is stored separately by chunk ID and preserves `document_id`, `ticker`, and `fiscal_year`.

Adding a chunk first counts its tokens locally. Repeated occurrences therefore increase that token's frequency without producing duplicate postings. A repeated chunk ID throws `std::invalid_argument` before the index is changed. Empty token lists are valid index inputs, although the real preprocessed chunks are nonempty.

Query terms must already follow the Python normalization policy. Repeated terms are deduplicated before Boolean evaluation or scoring. Empty AND and OR queries return no results. An absent AND term makes the intersection empty; an absent OR term contributes no chunks. Single-token and Boolean results use ascending chunk-ID order.

AND evaluation intersects sorted postings lists and starts with the shortest list. OR evaluation repeatedly merges sorted postings lists with set union. Both strategies avoid scanning unrelated collection chunks.

### Ranking

For unique normalized query terms `Q`, the implemented score is:

`score(chunk, Q) = sum(tf(term, chunk) for term in Q)`

AND ranking considers only chunks containing every term; OR ranking considers chunks containing at least one term. Results are sorted by descending score, then ascending chunk ID. Raw term frequency is transparent but biased toward repeated wording, longer passages, and text repeated by Stage 1 chunk overlap. It does not account for corpus rarity, length normalization, phrase proximity, or semantic relevance.

### Real-Collection Results

The loader read and indexed all **2,458 chunks** and reproduced all **14,180 unique normalized tokens**. It validated required metadata, per-chunk token counts, the declared collection size, and unique chunk IDs.

Observed demonstration results:

- `revenue`: 521 matching chunks.
- `artificial AND intelligence`: 30 matching chunks.
- `nvidia OR amd`: 354 matching chunks.
- Highest-ranked `artificial AND intelligence` result: `GOOGL_2025_10K_0067`, score 4.
- Highest-ranked `nvidia OR amd` result: `AMD_2025_10K_0027`, score 18.

The demonstration prints up to five lexicographically ordered IDs for each Boolean query and the top five ranked results with ticker, fiscal year, and document ID.

### Complexity

Let:

- `T` be total indexed token occurrences.
- `U_c` be the unique tokens in one chunk.
- `C` be indexed chunks.
- `V` be indexed vocabulary size.
- `P_total` be distinct token/chunk postings.
- `q` be unique query terms.
- `df_i` be the postings length of query term `i`.
- `P = sum(df_i)`.
- `M` be matching chunks.

Construction counts a chunk's tokens in expected `O(t_c)` time with a hash table, then inserts each distinct token into an outer hash table and an ordered postings map in `O(log df)` time. Across the corpus, expected construction time is `O(T + sum(log(df_posting + 1)))`, bounded more simply by `O(T + P_total log C)`. Adversarial hash collisions can degrade hash operations from expected constant time to linear time.

A single-token postings lookup takes expected `O(1)` to locate the token plus `O(df)` to copy the returned chunk IDs; outer hash lookup is `O(V)` in the collision-heavy worst case. A term-frequency lookup adds `O(log df)` for the ordered postings map.

AND query evaluation copies `P` postings, orders the `q` lists by size in `O(q log q)`, and performs sorted intersections starting with the shortest. The merge work is `O(P)` under this order, for expected `O(q + q log q + P)` including average token lookup. OR uses sequential sorted unions; its merge work can reach `O(qC)` because the accumulated result can be revisited for every term, although sparse queries are usually closer to their postings volume.

Ranking evaluates `q` term frequencies for each of `M` matches and sorts the results, costing expected `O(Mq log C + M log M)` with the ordered postings representation. Index memory is `O(C + V + P_total)` plus stored strings and container overhead. The schema loader also holds the parsed token arrays in memory while the demonstration builds the index.

### Verification and Limitations

Step 11 adds eleven portable synthetic CTests and one local real-collection integration CTest. Together with the twelve existing Trie tests, all **24 of 24 C++ tests passed**. All **45 Python tests passed** unchanged.

The index is entirely in memory, OR union is sequential rather than a heap-based multiway merge, and ranking uses only raw frequency. It does not store token positions, so it cannot answer phrase or proximity queries. No KMP, Z-function, Levenshtein distance, n-gram/Jaccard similarity, BM25, TF-IDF, semantic retrieval, pybind11 integration, or user interface was added.
