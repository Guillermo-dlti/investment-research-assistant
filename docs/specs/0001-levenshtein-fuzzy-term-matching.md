# 0001 · Levenshtein fuzzy term matching

**Status**: Assumed
**Date**: 2026-10-19
**Authorized by**: Santiago Fernandez Somellera, during /develop

## Owed decision
Which words a query word is compared against, what edit distance cutoff counts as a match, how candidates are ordered, and how fuzzy matches are exposed to search.

## Assumption built on
- Classic dynamic programming Levenshtein distance in C++17 (insert, delete, substitute, each cost 1), using two rolling rows so memory is O(min(n, m)) and time is O(n·m). Strings are compared as UTF-8 bytes, like the rest of the C++ code.
- A bounded variant stops early once every cell in a row is above the cutoff, so far away words cost less.
- Candidates are the normalized vocabulary words (the same 14,180 tokens the Trie holds), with their corpus frequencies.
- Default cutoff: 1 edit for query words of 4 bytes or fewer, 2 edits for longer words. Callers may pass their own cutoff.
- A vocabulary word is skipped without computing distance when its length differs from the query by more than the cutoff.
- An exact vocabulary hit returns only that word at distance 0.
- Order: distance ascending, then corpus frequency descending, then word ascending (deterministic).
- `correct_query()` never changes tokens that contain a digit (a near miss number like `$97,868` is a different fact, not a typo). Tokens with no word within the cutoff are kept as typed.
- Known limit: a real English word missing from the filings' vocabulary is still "corrected" (for example `say` becomes `may`). Feature 7 should weight corrected terms below exact ones, and the report should mention it.
- Exposed through pybind11 as `levenshtein_distance`, `bounded_levenshtein` and a `FuzzyMatcher` class, plus `SearchEngine.fuzzy_terms()` / `SearchEngine.correct_query()` in Python. Using the corrected terms to rank chunks again is feature 7, not this one.

## Code area
`src/cpp/levenshtein.*`, `src/cpp/tests/levenshtein_tests.cpp`, `src/cpp/levenshtein_demo.cpp`, `src/cpp/python_bindings.cpp`, `CMakeLists.txt`, `src/python/search_engine.py`, `tests/`

## Requirements
- AC-1: a query word with a typo (for example `nvidea`, `revenu`) returns its closest vocabulary words within the cutoff.
- AC-2: distance matches the textbook definition (`kitten`/`sitting` = 3, empty string cases, symmetry).
- AC-3: C++ tests, a demo, a binding and Python tests exist; all existing tests still pass.
- AC-4: time and space complexity are written down for the report.

## Ratify
This decision was recorded by /develop, not deliberated. Run `/architect levenshtein fuzzy term matching`
to deliberate and ratify it. Until then it stays flagged as an owed decision; it does not block marking the feature `done`.
