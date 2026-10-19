# 0002 · N gram Jaccard similarity

**Status**: Assumed
**Date**: 2026-10-19
**Authorized by**: Santiago Fernandez Somellera, during /develop

## Owed decision
Which n grams to build (characters or words, and which n), what the Jaccard score compares, how chunks are ranked by it, and how it is exposed to search.

## Assumption built on
- C++17 builds n gram sets as sorted, duplicate free `std::vector<std::string>`:
  - `wordNgrams(tokens, min_n, max_n)`: consecutive tokens joined by one space.
  - `characterNgrams(text, n)`: byte n grams (UTF-8 bytes, like the rest of the C++ code). A nonempty text shorter than `n` yields itself as its only gram. `n = 0` is rejected.
- Jaccard similarity J(A, B) = |A ∩ B| / |A ∪ B|, computed with a linear merge of two sorted sets: O(|A| + |B|) time, O(1) extra memory. Two empty sets score 0.
- Chunk ranking: `JaccardIndex` stores each chunk's word 1 and 2 gram set (built once at load from the preprocessed tokens). A query is tokenized with the existing Python policy, turned into the same 1 and 2 gram set, and compared with every chunk (full scan, so "chunks examined" equals the chunk count, useful for Stage 6). Chunks scoring 0 are dropped.
- Order: score descending (compared as exact fractions, not floats), then `chunk_id` ascending. `top_k` cuts after sorting.
- Known bias: Jaccard divides by the union, so shorter chunks score higher for the same shared grams. Worth a line in the report; feature 7 can combine it with other signals.
- Character trigrams are exposed for comparing single words (for example in feature 7), not used for chunk ranking here.
- Exposed through pybind11 as `character_ngrams`, `word_ngrams`, `jaccard_similarity`, `JaccardIndex`, `load_jaccard_index`, and in Python as `SearchEngine.jaccard_search(query, ticker=None, fiscal_year=None, top_k=None)`.

## Code area
`src/cpp/ngram_jaccard.*`, `src/cpp/tests/ngram_jaccard_tests.cpp`, `src/cpp/ngram_jaccard_demo.cpp`, `src/cpp/python_bindings.cpp`, `CMakeLists.txt`, `src/python/search_engine.py`, `tests/`

## Requirements
- AC-1: each candidate chunk gets a 0 to 1 similarity score against the query, and results are ranked by it.
- AC-2: n gram and Jaccard results match hand computed examples (identical sets = 1, disjoint = 0, partial overlap exact).
- AC-3: C++ tests, a demo, a binding and Python tests exist; all existing tests still pass.
- AC-4: the n gram choice and complexity are written down for the report.

## Ratify
This decision was recorded by /develop, not deliberated. Run `/architect n gram jaccard similarity`
to deliberate and ratify it. Until then it stays flagged as an owed decision; it does not block marking the feature `done`.
