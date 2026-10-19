# C++ algorithms

## Overview

From scratch C++17 implementations of every algorithm the course grades: Trie, inverted index, KMP, Z function, and next Levenshtein, n grams and Jaccard (Stage 4). They are exposed to Python through one pybind11 module, `investment_engine`.

## Key files

| File | Owns |
|---|---|
| `trie.h/.cpp` | Vocabulary Trie: insert, search, prefix check, autocomplete (feeds the GUI autocomplete bonus) |
| `inverted_index.h/.cpp` | Token to chunk postings, AND/OR queries, term frequency ranking |
| `kmp.h/.cpp`, `z_function.h/.cpp` | Exact matching, overlapping matches, byte offsets |
| `json_reader.h/.cpp` | Small standard library JSON reader shared by all loaders |
| `vocabulary_loader.*`, `preprocessed_collection_loader.*` | Load and validate the generated JSON files |
| `python_bindings.cpp` | The whole pybind11 surface of `investment_engine` |
| `tests/*_tests.cpp` | One test executable per algorithm, case chosen by argv name |
| `exact_matching_benchmark.cpp` | Release benchmark, writes to `reports/benchmarks/` |

## Conventions

- Adding an algorithm: `<name>.h/.cpp` here, a `<name>_core` library in root `CMakeLists.txt` with `-Wall -Wextra -Wpedantic`, link it into `investment_engine`, add `tests/<name>_tests.cpp`, register each case with `add_test` plus labels (`portable;<name>`), and add a `<name>_demo`.
- Standard library only. No external JSON, Trie or string libraries.
- Use `std::map` (not unordered) where output order matters, so results are deterministic.
- Strings are raw UTF-8 bytes: no case folding or Unicode work in C++. Callers pass normalized text.
- Empty pattern means no matches and count zero; keep this edge case behavior consistent for new matchers.

## Gotchas

- Tests that need real data only register if `data/metadata/vocabulary.json` and `data/processed/preprocessed_collection.json` exist when CMake configures. Regenerate data, then reconfigure.
- The built `.so` is tied to the exact Python version and CPU; rebuild after changing interpreter.
- Always pass `-DPython_EXECUTABLE="$PWD/.venv/bin/python"` so pybind11 is found inside `.venv`.

_Drafted by /audit from the repo, worth a quick human pass. Edit freely: once a line stops matching this draft, later runs treat it as curated and will flag rather than overwrite it._
