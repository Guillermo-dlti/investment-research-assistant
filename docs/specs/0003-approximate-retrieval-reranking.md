# 0003. Approximate retrieval and reranking with corrected terms and scaled Jaccard

**Date**: 2026-10-19
**Status**: In Progress

## Summary

This adds an approximate search mode next to the existing exact search. It fixes typos in the question with Levenshtein (spec 0001), drops filler words like "what" and "the", gathers every chunk that contains at least one of the remaining words, then scores those chunks again in C++. Each score mixes how many of the question's words a chunk contains (typo words count less) with how similar its word pairs are to the question (Jaccard, spec 0002). A single `compare_search` call returns both rankings side by side with timings, which feeds the Stage 4 report and the Stage 6 comparison directly.

## Context

The course brief (Stage 4) asks for a second retrieval mechanism that tolerates typos, word variations and partial matches, uses at least two approximate techniques to compute relevance again, and produces a new order. The report must name the algorithms, explain how similarity is computed, show the retrieved chunks and the run times, and describe how the results differ from exact search. Stage 6 then compares the two modes on one question set (time, chunks examined, usefulness, model answers).

The two techniques already exist as building blocks. `FuzzyMatcher` (spec 0001) maps an unknown query word to its closest vocabulary word, and its spec asks that corrected words weigh less than exact ones because some corrections are wrong (`say` becomes `may`). `JaccardIndex` (spec 0002) scores a chunk's word 1 and 2 gram set against the query's, but it scans all 2,458 chunks and favors short chunks. Neither one alone gives a candidate set, a combined score, or a comparison.

Three facts about the data shape the problem. The tokenizer keeps stopwords (`stopword_removal: False`), so an OR lookup for "what was nvidia revenue" already touches about 1,000 chunks, mostly because of "what" and "was". A chunk's n gram set holds roughly 250 words plus their pairs, while a question holds a handful, so raw Jaccard values are tiny (around 0.01). And project rules require every ranking algorithm to live in C++ under `src/cpp/`, with Python only orchestrating, and forbid changing the finished Stage 1 to 3 code.

Without a decision here, `/develop` would have to invent the candidate set, the formula and its weights, and every ranking it produced would be unexplainable in the report.

## Requirements

**User stories**:
- As a student writing the report, I want the same question ranked by exact and by approximate search, with scores and timings, so I can show how and why they differ.
- As a user, I want a question with a typo (`nvidea`) to still find the right chunks.
- As the Stage 5 and Stage 6 code, I want one stable call that returns ranked chunks with their metadata, so context selection and the comparison can build on it.

**Acceptance criteria**:
- **AC-1**: `SearchEngine.compare_search(query)` returns, for the same question, an exact ranking and an approximate ranking, each with per chunk scores, a candidate count, and timings in milliseconds (exact total; approximate total plus correction, candidate lookup and rerank steps).
- **AC-2**: For the single word typo query `nvidea`, the exact ranking is empty, the approximate ranking is not empty, every returned chunk contains `nvidia`, and the reported corrections show `nvidea → nvidia` at distance 1.
- **AC-3**: Every approximate score equals `alpha · coverage + (1 − alpha) · (J / J_max)` and lies in [0, 1]; a C++ test checks it against a hand computed example. `alpha` defaults to 0.6 and is a parameter.
- **AC-4**: A corrected term counts `1 / (1 + distance)` in coverage while an exact term counts 1, so the same chunk scores strictly lower coverage when it is reached through a corrected word than through the exact word.
- **AC-5**: Candidates are exactly the chunks (after filters) containing at least one content term. Stopwords are dropped in approximate mode only; a query made only of stopwords falls back to all its tokens and `compare_search` reports `stopword_fallback: true`.
- **AC-6**: `ticker` and `fiscal_year` filters apply before scoring, so `J_max` and every score are relative to the filtered candidates only. In `compare_search` the exact side applies the same filters before `top_k`, and both `candidate_count` values mean the same thing: matching chunks after filters, before `top_k`.
- **AC-7**: Order is score descending, then `chunk_id` ascending; `top_k` defaults to 10, `None` returns all, 0 returns `[]`. Validation runs before any work: a non integer or bool `top_k` raises `TypeError`, a negative one `ValueError`; a non numeric `alpha` raises `TypeError`, one outside [0, 1] `ValueError`.
- **AC-8**: Existing behavior is unchanged: exact phrase search, ranked AND/OR, fuzzy and Jaccard APIs return the same results as before, and every existing C++ and Python test still passes.
- **AC-9**: The new C++ code follows the area convention: its own library target, a CTest executable with named cases, a demo, a pybind11 binding, and Python tests in `tests/`.
- **AC-10**: `reports/stage4_notes.md` records the algorithms, the similarity formula, the top 5 chunks per mode, the timings (median of 5 runs after one warm up run), and the differences from exact search for three fixed questions: `nvidea data center revenue` (typo), `data center revenue` (expected to agree), `what risks come from export restrictions` (expected to differ). It also says when approximate search helps and when it adds noise. This is report evidence only: whether the modes actually agree or differ is reported, not asserted by a test. No code in it.

## Options considered

### Option 1: Corrected content words, OR candidates, weighted coverage plus scaled Jaccard (C++ reranker)

Tokenize, drop stopwords, correct each remaining word with `FuzzyMatcher`, look up the OR of those words in the inverted index for candidates, filter, then score each candidate in a new C++ module: weighted term coverage (typos discounted) mixed with Jaccard scaled by the best Jaccard among the candidates.

**Pros**:
- Uses both Stage 4 techniques in a way where each really moves the order, and honors spec 0001's request to discount corrected words.
- The candidate set is much smaller than the corpus, which gives Stage 6 a real "chunks examined" contrast.
- Every number in a result is explainable in one line of the report.

**Cons**:
- New C++ module and one additive method on `JaccardIndex`, so more code than reusing `jaccard_search`.
- Scaling by `J_max` makes scores relative to the candidate set: the same chunk can score differently under different filters.
- A hand maintained stopword list.

### Option 2: Full scan, Jaccard on the corrected query

Correct the query, then call the existing `jaccard_search` on it.

**Pros**:
- Almost no new code; reuses a tested path.

**Cons**:
- Corrected words weigh the same as exact ones, against spec 0001.
- Always examines all 2,458 chunks, so Stage 6 shows no pruning.
- Raw Jaccard rewards short chunks and stopword overlap, so rankings are noisy.

### Option 3: Rerank only the exact top N

Run exact ranked search, then reorder its top N by an approximate score.

**Pros**:
- Cheapest; the purest reading of "rerank".

**Cons**:
- A typo query that exact search misses has no candidates at all, so it fails the scope's Done when and AC-2.

### Option 4: Combine scores in Python

Fetch coverage and Jaccard parts from C++ and do the weighted sum and sort in Python.

**Pros**:
- Easier to tweak the formula.

**Cons**:
- Breaks the project rule that ranking algorithms live in C++, and splits the algorithm the report must describe across two languages.

## Decision

**Chosen option**: Option 1: Corrected content words, OR candidates, weighted coverage plus scaled Jaccard (C++ reranker)

Approximate search corrects and filters the query in Python, takes OR candidates from the inverted index, and reranks them in a new C++ `approximate_rerank` module by `0.6 · coverage + 0.4 · J / J_max`.

## Rationale

The brief grades approximate search on two things: that it finds what exact search misses, and that the report can explain how relevance was computed again. Option 3 fails the first outright. Option 2 passes it but makes the second weak, because a ranking driven by raw Jaccard over stopword heavy sets is hard to defend, and it ignores the discount spec 0001 asked for. Option 1 is the smallest design where both techniques visibly matter: Levenshtein decides which words the query really means and how much each counts, and Jaccard reorders chunks that contain those words by how close their phrasing is.

Scaling Jaccard by `J_max` is the key detail. With raw values near 0.01, a 0.4 weight would add at most about 0.004, so Jaccard would only break ties. Dividing by the best Jaccard among the candidates puts both parts on the same 0 to 1 range, at the cost of scores being relative to the candidate set. That is acceptable because scores are only ever compared within one query's results, and filtering before scoring keeps them relative to what you actually asked about. Coverage leads (0.6) so a chunk that contains the asked words beats a short chunk that merely shares phrasing.

Putting the reranker in its own C++ module keeps to the one algorithm per target convention and the "never reimplement in Python" rule, and leaves every Stage 1 to 3 and spec 0001/0002 API untouched; the only change to existing C++ is one additive method on `JaccardIndex`. Dropping stopwords in approximate mode only keeps exact search byte for byte as before, which Stage 6 needs as a stable baseline.

## Feature design

**Data model sketch**:
No persistence. Everything is computed per query from the loaded indexes.
- `WeightedTerm` (C++ struct): `term: string` (required, normalized), `weight: double` (required, in (0, 1]).
- `ApproximateResult` (C++ struct): `chunk_id: string`, `score: double`, `coverage: double`, `jaccard: double` (raw), `jaccard_scaled: double`, `matched_terms: size_t`.
- Query term record (Python dict): `original`, `corrected`, `distance` (int, or `None` when no vocabulary word was within the cutoff or the token has a digit), `weight`.
- `chunk_id` stays the join key to metadata, as everywhere else.

**Pipeline** (approximate mode, in order):
Both public methods share one private `_approximate(query, ticker, fiscal_year, top_k, alpha)` that returns `(results, details)`; `approximate_search` returns `results`, `compare_search` also uses `details`.

1. `tokens = normalize_query(query)` (existing policy). Empty → no results, empty `terms`.
2. `content = [t for t in tokens if t not in STOPWORDS]`; if empty, `content = tokens` and `stopword_fallback = True`.
3. Correct each content token with the same rules as `correct_query()` (best match only; digits kept; unmatched kept as typed). Weight = `1 / (1 + distance)`, or 1 when `distance` is 0 or `None`. Drop any corrected word that is itself a stopword (unless in fallback). If nothing is left (for example `teh` became `the`), return no results with empty `terms`; fallback is not triggered a second time.
4. `ngram_tokens` = the corrected words left after step 3, in query order, duplicates kept (the n gram set collapses them). `terms` = those words deduplicated, keeping the highest weight per word. Unmatched and digit terms stay in both, at weight 1.
5. Candidates = `index.or_query(terms)` (unmatched terms simply have no postings), then drop chunks failing the filters. `candidate_count` = the size of this filtered set.
6. C++ `rerank_candidates(index, jaccard_index, candidates, terms, ngram_tokens, alpha, top_k)`:
   - `coverage(c) = Σ weight(t) · [termFrequency(t, c) > 0] / len(terms)`, where `len(terms)` counts every distinct term including unmatched and digit ones. Presence is `InvertedIndex::termFrequency`, a map lookup, so O(log df) per term and chunk.
   - `J(c)` = Jaccard of the word 1 and 2 gram set of `ngram_tokens` with the chunk's stored set; `J_max` = max over all candidates (before `top_k`); `jaccard_scaled = J / J_max`, or 0 for all when `J_max = 0`
   - `score = alpha · coverage + (1 − alpha) · jaccard_scaled`, clamped to [0, 1] against floating point overshoot
   - sort by score descending, then `chunk_id` ascending; cut at `top_k`.

**Filters** (one private helper used by the new code only; existing methods keep their own inline checks): the ticker is stripped and casefolded and compared with the chunk's casefolded `ticker`; `fiscal_year` must be an `int` and not a `bool` (else `TypeError`) and is compared with the chunk's `fiscal_year`; an unknown value simply matches nothing, so the result is empty.

**Exact side of the comparison**: `ranked_and_search(query)` on the full token list; if empty, `ranked_or_search(query)`. Mode reported as `"and"`, `"or"` or `"none"` (empty query or no matches). Filters apply after ranking and before `top_k` (term frequency scores do not depend on the other chunks, so order is unaffected); `candidate_count` = matches after filters, before `top_k`. Each exact result is the existing `_ranked_results` dict (chunk metadata plus `score` = summed term frequency) with `algorithm: "term_frequency"` added.

**Timing** (`time.perf_counter()`, milliseconds): exact `time_ms` runs from `normalize_query` to the finished result dicts, including the AND then OR fallback and filters. Approximate `steps_ms`: `correction` = tokenize, stopword drops, correction and weights; `candidates` = OR lookup plus filters; `rerank` = the C++ call plus building the result dicts. Approximate `time_ms` is measured separately over the whole `_approximate` call, not summed from the steps. Validation happens before any timer starts.

**Empty query in `compare_search`**: the same dict shape with empty lists, zero counts and times, `exact.mode = "none"`, `stopword_fallback = False`.

**STOPWORDS** (frozenset in `src/python/search_engine.py`, approximate mode only):
`a about after all also an and any are as at be been being but by can could did do does each for from had has have how i if in into is it its me might more most my no not of on or our so such than that the their them then there these they this those to was we were what when where which who whom whose why will with would you your`
(`may` and `us` are deliberately left out: in 10-K filings they can be content, the month May and U.S.)

**API surface** (Python, local library; no network):
| Function | Kind | Key inputs | Key outputs | Auth | Key errors |
|---|---|---|---|---|---|
| `SearchEngine.approximate_search` | method | `query: str` (req), `ticker: str \| None`, `fiscal_year: int \| None`, `top_k: int \| None = 10`, `alpha: float = 0.6` | list of chunk dicts: metadata + `score`, `coverage`, `jaccard`, `jaccard_scaled`, `matched_terms`, `algorithm="approximate"` | none (local) | `TypeError` for non int or bool `top_k`, non numeric `alpha`, or bad filter types; `ValueError` for negative `top_k` or `alpha` outside [0, 1] |
| `SearchEngine.compare_search` | method | same as above | dict: `query`, `terms` (query term records), `stopword_fallback`, `unmatched_terms`, `exact {mode, results, candidate_count, time_ms}`, `approximate {results, candidate_count, time_ms, steps_ms {correction, candidates, rerank}}`, `shared_chunk_ids` | none (local) | same as above |
| `investment_engine.WeightedTerm` | C++ struct binding | `WeightedTerm(term: str, weight: float)` constructor | readable and writable `term`, `weight` | none | none |
| `investment_engine.rerank_candidates` | C++ binding | `InvertedIndex`, `JaccardIndex`, `candidate_ids: list[str]`, `terms: list[WeightedTerm]`, `ngram_tokens: list[str]`, `alpha: float`, `top_k: int \| None` | list of `ApproximateResult` | none | `ValueError` (from `std::invalid_argument`) for unknown or duplicate chunk id, `alpha` outside [0, 1], or a weight outside (0, 1] |
| `JaccardIndex.score_chunks` (additive) | C++ method + binding | `chunk_ids`, `query_tokens` | one `JaccardResult` per id, input order | none | unknown chunk id |

**Value sourcing**:
| Action | Value produced / displayed | Source |
|---|---|---|
| approximate | content terms | `normalize_query(query)` minus `STOPWORDS` (this spec) |
| approximate | corrected word, distance | `FuzzyMatcher.match(token, 1, None)` (spec 0001 cutoffs) |
| approximate | term weight | `1 / (1 + distance)`, 1 for exact or unmatched (this spec) |
| approximate | candidate ids, `candidate_count` | `InvertedIndex.or_query(terms)` after Python metadata filters |
| approximate | `ngram_tokens` | corrected words after both stopword drops, query order, duplicates kept |
| approximate | coverage denominator | number of distinct `terms`, including unmatched and digit terms |
| approximate | term present in chunk | `InvertedIndex::termFrequency(term, chunk) > 0` |
| approximate | `jaccard` | `JaccardIndex.score_chunks` over word 1 and 2 grams (spec 0002) |
| approximate | `J_max`, `jaccard_scaled` | derived: max `jaccard` over the filtered candidates |
| approximate | `score` | derived: `alpha · coverage + (1 − alpha) · jaccard_scaled`; `alpha` input, default 0.6 |
| approximate | chunk metadata (ticker, year, source) | `InvertedIndex.get_metadata` via `_chunk_result` |
| compare | exact results, `mode` | `ranked_and_search`, else `ranked_or_search` (existing) |
| compare | exact `candidate_count` | AND (or OR) matches after filters, before `top_k` |
| compare | exact result `score`, `algorithm` | existing `_ranked_results` term frequency score; `"term_frequency"` |
| compare | `stopword_fallback` | `details` from `_approximate` (step 2) |
| compare | `time_ms`, `steps_ms` | `time.perf_counter()` windows defined under Timing above |
| compare | `unmatched_terms` | content tokens whose `distance` is `None` and contain no digit |
| compare | `shared_chunk_ids` | intersection of the two returned `top_k` id lists, sorted (so it depends on `top_k`) |

**Key invariants**:
- Exact mode never sees the stopword list or corrections.
- Every approximate `score`, `coverage` and `jaccard_scaled` lies in [0, 1] (score clamped); `coverage` reaches 1 only when every term has weight 1 and occurs in the chunk, so a query with a corrected or unmatched term never reaches 1.
- `J_max` is taken over all filtered candidates, never only the `top_k` returned.
- Without stopword fallback, no term in `terms` is a stopword.
- Same inputs give the same order (no floating sort without the `chunk_id` tie break).
- C++ never normalizes text; Python passes normalized tokens.

**Security model**:
Not applicable beyond the project rules. It runs locally on public SEC filings, holds no user data, and needs no credentials.

**Critical test scenarios**:
- Happy path: `compare_search("nvidia data center revenue")` returns both rankings with timings and candidate counts, verifies **AC-1**.
- Typo: `nvidea` gives an empty exact ranking and an approximate ranking where every chunk contains `nvidia`, verifies **AC-2**.
- Formula: a C++ fixture with three tiny chunks checks coverage, raw and scaled Jaccard and the final score by hand; `J_max = 0` is tested by calling C++ directly (it cannot happen through Python, since every candidate shares a term with the query), verifies **AC-3**.
- Typo discount: the single word queries `nvidia` and `nvidea` give the same chunk coverage 1 and 0.5, verifies **AC-4**.
- Stopwords: `"what is it"` sets `stopword_fallback` and still returns results; `"what was nvidia revenue"` has no stopword in `terms`; `"teh"` (corrected into a stopword) returns no results with empty `terms`, verifies **AC-5**.
- Filters: with `ticker="AMD"`, every result is AMD and `J_max` comes from AMD chunks only, verifies **AC-6**.
- Bad input: `alpha=1.5`, `top_k=-1`, a duplicate candidate id in C++ all raise; `top_k=0` returns `[]`, verifies **AC-7**.
- Regression: the full existing C++ and Python suites pass unchanged, verifies **AC-8**.

## Build plan

Tracer Bullet: first a thin thread from C++ to `approximate_search`, then thicken it with the comparison, edge cases and report evidence.

1. Add `JaccardIndex::scoreChunks(chunk_ids, query_tokens)` (additive, existing methods untouched) with CTests for input order and unknown ids, satisfies **AC-3**, **AC-8**
2. Create `src/cpp/approximate_rerank.h/.cpp` with `WeightedTerm`, `ApproximateResult` and `rerankCandidates` (coverage via postings, scaled Jaccard, deterministic sort, input validation), an `approximate_rerank_core` library target, satisfies **AC-3**, **AC-4**, **AC-7**, **AC-9**
3. Add `src/cpp/tests/approximate_rerank_tests.cpp` with named cases (hand computed formula, `J_max = 0`, typo weight, tie break, top_k, invalid alpha/weight, duplicate and unknown ids), registered with `add_test` and labels `portable;approximate_rerank`, satisfies **AC-3**, **AC-4**, **AC-7**, **AC-9**
4. Bind `rerank_candidates`, `WeightedTerm`, `ApproximateResult` and `JaccardIndex.score_chunks` in `python_bindings.cpp`, satisfies **AC-9**
5. Add `STOPWORDS`, the private filter helper, `_approximate` and `SearchEngine.approximate_search` (pipeline steps 1 to 6, validation first, filters before scoring), satisfies **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**
6. Add `SearchEngine.compare_search` (exact AND then OR with filters before `top_k`, timing windows, candidate counts, `terms`, `stopword_fallback`, `unmatched_terms`, `shared_chunk_ids`, empty query shape), satisfies **AC-1**, **AC-2**, **AC-6**
7. Add `tests/test_approximate_search.py` covering the critical scenarios on the real data, satisfies **AC-1**, **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**, **AC-9**
8. Add `approximate_rerank_demo` (C++) and `src/python/approximate_search_demo.py` printing both rankings and timings for a few questions, satisfies **AC-9**, **AC-10**
9. Run the full C++ and Python suites and confirm the existing tests pass unchanged, satisfies **AC-8**
10. Write `reports/stage4_notes.md` from the demo output (algorithms, formula, chunks, timings, differences, when it helps or adds noise; no code), satisfies **AC-10**

## Consequences

**Positive**:
- Typo and variant questions now find relevant chunks, and the report can explain each score in one line.
- Stage 5 context selection and Stage 6 comparison get one stable call with metadata, scores, counts and timings.
- Exact search and all Stage 1 to 3 and spec 0001/0002 APIs stay unchanged.

**Negative / tradeoffs**:
- Scores are relative to the candidate set (through `J_max`), so they cannot be compared across different queries or filters.
- Questions full of common content words (`revenue`, `company`) still produce large candidate sets, since only stopwords are removed.
- Wrong corrections still pull in noise (a discounted weight limits it but does not remove it), and Jaccard still leans toward short chunks.
- Coverage is present or absent per term with no IDF (inverse document frequency, which would down weight common words), so `revenue` counts as much as `nvidia`; among large candidate sets Jaccard does much of the ordering.
- A lone candidate always gets `jaccard_scaled = 1`, which inflates its score.
- Part of any exact vs approximate difference comes from dropping stopwords, not from fuzzy matching; the report should say so.
- A stopword list to maintain, and `alpha = 0.6` and the `1 / (1 + d)` weight are reasoned defaults, not tuned against labeled data.

**Neutral**:
- One additive method on `JaccardIndex`; a new C++ module, binding and test file.
- Specs 0001 and 0002 are still `Assumed`; this spec builds on their behavior as recorded.

## Follow-up

- [ ] Ratify specs 0001 and 0002 (`/architect levenshtein fuzzy term matching`, `/architect n gram jaccard similarity`); this design depends on their cutoffs and n gram choice.
- [ ] Stage 6 may want to sweep `alpha` (for example 0.4, 0.6, 0.8) on the test question set and report the effect.
