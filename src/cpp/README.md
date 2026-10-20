# C++ algorithms and data structures

Every algorithm the project uses is written from scratch in C++17 with the standard library only, and exposed to Python through one pybind11 module, `investment_engine`. Design, complexity and results for each one are in the stage notes under `reports/`.

| Files | Stage | What it does |
|---|---|---|
| `trie.*` | 2 | Vocabulary Trie: insert, search, prefix check, autocomplete (also feeds the GUI) |
| `inverted_index.*` | 2 | Token to chunk postings, AND / OR queries, term-frequency ranking |
| `kmp.*` | 3 | KMP exact matching with the LPS table; overlapping matches, byte offsets |
| `z_function.*` | 3 | Z array and exact matching over pattern + separator + text |
| `levenshtein.*` | 4 | Edit distance, bounded distance, `FuzzyMatcher` for typo correction against the vocabulary |
| `ngram_jaccard.*` | 4 | Character and word n-grams, Jaccard similarity, `JaccardIndex` of every chunk's n-gram set |
| `approximate_rerank.*` | 4 | Reranks candidates by weighted word coverage plus Jaccard scaled by the best candidate |
| `context_selection.*` | 5 | Greedy context selection: chunk limit, word budget, Jaccard redundancy filter |
| `json_reader.*`, `vocabulary_loader.*`, `preprocessed_collection_loader.*` | 2 | Load and validate the generated JSON files |
| `python_bindings.cpp` | all | The pybind11 surface of `investment_engine` |
| `*_demo.cpp` | all | One runnable demo per algorithm on the real collection |
| `exact_matching_benchmark.cpp` | 3 | Release benchmark of KMP vs Z function, written to `reports/benchmarks/` |
| `tests/*_tests.cpp` | all | One CTest executable per algorithm, each case run by name |

## Conventions

- C++ treats strings as raw UTF-8 bytes and never normalizes them. Python normalizes queries and chunks with one shared policy, so offsets are byte offsets.
- Ordered containers are used wherever output order matters, and ties are broken by chunk ID, so results and benchmarks are deterministic.
- An empty pattern means no matches and a count of zero, for every matcher.
- Tests that need the real data are only registered if `data/metadata/vocabulary.json` and `data/processed/preprocessed_collection.json` exist when CMake configures. Regenerate the data, then configure again.

## Demos

```bash
./build/trie_demo data/metadata/vocabulary.json
./build/inverted_index_demo data/processed/preprocessed_collection.json
./build/kmp_demo data/processed/preprocessed_collection.json
./build/z_function_demo data/processed/preprocessed_collection.json
./build/levenshtein_demo data/metadata/vocabulary.json
./build/ngram_jaccard_demo data/processed/preprocessed_collection.json
./build/approximate_rerank_demo data/processed/preprocessed_collection.json
./build/context_selection_demo
```
