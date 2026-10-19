# Scope: Investment Research Assistant

A question answering assistant over 10 SEC 10-K filings (NVDA, AMD, MSFT, AAPL, GOOGL, FY2024 and FY2025). Classic string algorithms in C++ find the best chunks, and a Hugging Face model answers from them. Built for the Advanced Algorithms course; the brief is in [docs/assignment.md](../assignment.md).

**Build approach:** Tracer Bullet (each stage is built end to end: C++ algorithm, pybind11 binding, Python wiring, tests, and report evidence).
**Workflow:** Beta (after `/develop`, run `/check verify`, then `/test`). The project default level of rigor. `/architect` is the recommended first stop for a feature with a real decision, but skippable when you already know the build. Any feature can carry its own tag (e.g. `· Prototype`) to do more or less.
**Deadline:** due 2026-10-19 (today). Work top to bottom. Stages 4, 5, 6, the report and the video are required. The GUI bonus counts only when everything else is complete, so it comes last among the code features.

_These are recommendations to keep your build orderly, not requirements. Skip anything that does not fit: if you already know how to build a feature, use `/develop` and skip `/architect`. You decide when a feature is `done`._

## At a glance

| # | Feature | Phase | Status |
|---|---------|-------|--------|
| 1 | Document collection and chunking (Stage 1) | Foundation | existing |
| 2 | Preprocessing, Trie and inverted index (Stage 2) | Foundation | existing |
| 3 | Python and C++ bridge | Foundation | existing |
| 4 | Exact search with KMP and Z function (Stage 3) | Foundation | existing |
| 5 | Levenshtein fuzzy term matching | Slice 1: Stage 4 | in-progress |
| 6 | N gram Jaccard similarity | Slice 1: Stage 4 | in-progress |
| 7 | Approximate retrieval and reranking | Slice 1: Stage 4 | in-progress |
| 8 | Context selection | Slice 2: Stage 5 | planned |
| 9 | Language model answers | Slice 2: Stage 5 | planned |
| 10 | Twenty question run | Slice 2: Stage 5 | planned |
| 11 | Exact vs approximate comparison (Stage 6) | Slice 3: Stage 6 | planned |
| 12 | GUI with Trie autocomplete (bonus) | Slice 4: Bonus | planned |
| 13 | Final report | Deliverables | planned |
| 14 | Demo video | Deliverables | planned |

## Foundations (already built)

### 1. Document collection and chunking (Stage 1) · existing
Downloads, extracts and chunks the 10 filings into 2,458 chunks of about 250 words with 40 words of overlap. code in `src/python/` (download, extract, chunk, build_collection), notes in `reports/stage1_notes.md`

### 2. Preprocessing, Trie and inverted index (Stage 2) · existing
NFKC normalization, casefolding and a tokenizer (14,180 unique tokens), plus a C++ Trie with autocomplete and an inverted index with AND/OR queries and term frequency ranking. code in `src/python/preprocess_text.py`, `src/cpp/trie.*`, `src/cpp/inverted_index.*`

### 3. Python and C++ bridge · existing
pybind11 module `investment_engine` and the Python `SearchEngine` wrapper. code in `src/cpp/python_bindings.cpp`, `src/python/search_engine.py`

### 4. Exact search with KMP and Z function (Stage 3) · existing
Ranked exact phrase search with top k, ticker and year filters, and Release benchmarks. 56 C++ and 83 Python tests pass. code in `src/cpp/kmp.*`, `src/cpp/z_function.*`, results in `reports/benchmarks/`

## Slice 1: Stage 4, approximate search

### 5. Levenshtein fuzzy term matching · in-progress · assumed decision (spec 0001)
A C++ edit distance that maps misspelled or varied query words to real vocabulary words (for example `nvidea` to `nvidia`).
**Done when:** a query word with a typo finds its closest vocabulary words within a set distance; C++ tests, a binding and Python tests exist; complexity is written down.
- [ ] Design it (spec): `/architect levenshtein fuzzy term matching` (ratify the assumed spec)
- [x] Build it: `/develop levenshtein fuzzy term matching`
   - [x] C++ distance, bounded distance and `FuzzyMatcher`, with 16 CTests and a demo
   - [x] pybind11 binding plus `SearchEngine.fuzzy_terms()` and `correct_query()`, with Python tests
- [ ] Verify it: `/check verify levenshtein fuzzy term matching`
- [ ] Test it: `/test levenshtein fuzzy term matching`
Spec [0001](../specs/0001-levenshtein-fuzzy-term-matching.md) · code in `src/cpp/levenshtein.*`, `src/python/search_engine.py`

### 6. N gram Jaccard similarity · in-progress · assumed decision (spec 0002)
C++ n gram sets and Jaccard similarity to score how close a query is to each chunk, even when the words are not exact.
**Done when:** each candidate chunk gets a 0 to 1 similarity score against the query; C++ tests, a binding and Python tests exist; the n gram choice (characters or words) is explained.
- [ ] Design it (spec): `/architect n gram jaccard similarity` (ratify the assumed spec)
- [x] Build it: `/develop n gram jaccard similarity`
   - [x] C++ character and word n grams, Jaccard, and `JaccardIndex`, with 11 CTests and a demo
   - [x] pybind11 binding plus `SearchEngine.jaccard_search()`, with Python tests
- [ ] Verify it: `/check verify n gram jaccard similarity`
- [ ] Test it: `/test n gram jaccard similarity`
Spec [0002](../specs/0002-ngram-jaccard-similarity.md) · code in `src/cpp/ngram_jaccard.*`, `src/python/search_engine.py`

### 7. Approximate retrieval and reranking · in-progress
Adds an approximate search mode to `SearchEngine` that uses features 5 and 6 to score chunks again and return a new order, without breaking exact search.
**Done when:** the same question returns an exact ranking and an approximate ranking with scores and timings; a typo query that exact search misses is found by approximate search.
- [x] Design it (spec): `/architect approximate retrieval and reranking`
- [x] Build it: `/develop approximate retrieval and reranking`
   - [x] C++ `approximate_rerank` module plus `JaccardIndex::scoreChunks`, with CTests, a demo and bindings (AC-3, AC-4, AC-7, AC-8, AC-9)
   - [x] `SearchEngine.approximate_search` with stopwords, corrections, OR candidates and filters, with Python tests (AC-2, AC-4, AC-5, AC-6, AC-7)
   - [x] `SearchEngine.compare_search` with timings and candidate counts, plus a full regression run (AC-1, AC-6, AC-8)
   - [x] Python demo and `reports/stage4_notes.md` evidence (AC-10)
- [ ] Verify it: `/check verify approximate retrieval and reranking`
- [ ] Test it: `/test approximate retrieval and reranking`
Spec [0003](../specs/0003-approximate-retrieval-reranking.md) · code in `src/cpp/approximate_rerank.*`, `src/python/search_engine.py`

## Slice 2: Stage 5, answers from a language model

### 8. Context selection
Picks which retrieved chunks go to the model: top k, a word budget, and dropping near duplicates caused by chunk overlap.
**Done when:** for any question the selected context stays under the budget, has no duplicate chunks, and keeps `chunk_id` and filing metadata for citations.
- [ ] Build it: `/develop context selection`

### 9. Language model answers · needs a decision
A pretrained Hugging Face model (no training) answers using only the selected context.
**Done when:** question → search → chunks → context → model → answer runs locally and the answer cites its chunks; the model choice and why are recorded.
- [ ] Design it (spec): `/architect language model answers`

### 10. Twenty question run
A script that runs at least 20 questions and saves the question, the selected chunks, the answer and the retrieval time for the report.
**Done when:** a results file under `reports/` holds 20 or more full entries, including a few where retrieval was weak.
- [ ] Build it: `/develop twenty question run`

## Slice 3: Stage 6, comparison

### 11. Exact vs approximate comparison (Stage 6)
Runs one test question set through both search modes and compares average time, chunks examined or returned, chunk usefulness and the model's answers.
**Done when:** a table and charts under `reports/` show both modes side by side, with at least one case where they agree and one where they differ strongly.
- [ ] Build it: `/develop exact vs approximate comparison`

## Slice 4: Bonus

### 12. GUI with Trie autocomplete (bonus) · Alpha
A window where you type a question, get word suggestions from the C++ Trie as you type, and see the answer with its source chunks. Worth 10 points only if the whole project is complete.
**Done when:** typing a prefix shows Trie suggestions, submitting shows the answer plus sources, and it shows the educational, not financial advice disclaimer.
- [ ] Build it: `/develop gui with trie autocomplete`

## Deliverables

### 13. Final report
Covers the introduction, every stage's required answers, each algorithm's design technique and complexity, and personal conclusions. No code inside (course rule).
**Done when:** every bullet the brief asks for in Stages 1 to 6 is answered, using the stage notes and benchmark files already in `reports/`.
- [ ] Write it (outside this repo's code workflow)

### 14. Demo video
A short video showing how to use the app and what the results look like. No algorithm or code explanation needed.
**Done when:** the video shows a few questions end to end, including autocomplete if feature 12 is done.
- [ ] Record it

## Legend

**The decision box.** Every feature carries exactly one, the sub task whose label ends with `(spec)`. Skills locate it by that `(spec)` suffix, never by an exact label. Every other box is an execution box and `/architect` never ticks one.

- **Next step** = the first unticked box.
- **needs a decision** = run `/architect` first; otherwise straight to `/develop`. The tag drops once the spec is captured.
- **Atomic build tasks live in the spec's `## Build plan`, not here**: the scope carries only the milestone rollup.
- **Status** `planned` → `in-progress` → `done`, plus `existing` (built before this workflow) and `dropped` (de scoped, kept for history).
- **Workflow tier tag** beside a heading (e.g. `· Alpha`) sets that one feature's rigor; no tag inherits the project default (Beta = `/check verify`, then `/test`).
- **Pointer line** (`spec <n> · code in <path>`): the spec link added by `/architect`, the code path by `/develop`.
