# C++ Trie

This directory contains the project's first custom C++17 data structure: a Trie for the normalized financial vocabulary.

## Components

- `trie.h` and `trie.cpp`: insertion, exact search, prefix search, autocomplete, and unique-token count.
- `vocabulary_loader.h` and `vocabulary_loader.cpp`: a standard-library-only reader for the generated `vocabulary.json` schema.
- `trie_demo.cpp`: loads the real vocabulary and demonstrates all public Trie operations.
- `tests/trie_tests.cpp`: portable synthetic tests and local full-vocabulary tests.

No external Trie or JSON library is used. Nodes own their children with `std::unique_ptr`, and each node uses `std::map<unsigned char, ...>` so traversal is deterministic and bytewise lexicographic.

## Build and Run

From the repository root, with the Python virtual environment activated so its CMake executable is available:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/trie_demo data/metadata/vocabulary.json
ctest --test-dir build --output-on-failure
```

The local vocabulary is generated and ignored by Git. If it is absent when CMake is configured, the ten synthetic tests remain available but the two local-vocabulary tests are not registered. Generate the file with `src/python/preprocess_text.py`, then configure CMake again to enable all 12 tests. A different vocabulary can be selected at configuration time with `-DTRIE_VOCABULARY_PATH=/absolute/path/to/vocabulary.json`.

## Token and Ordering Policy

The Trie consumes tokens already normalized by Python. It does not lowercase, case-fold, normalize Unicode, or otherwise modify input. A C++ `std::string` is traversed one unsigned UTF-8 byte at a time. Valid UTF-8 tokens are stored and recovered unchanged, although the Trie does not understand Unicode character boundaries. A malformed or partial byte prefix is therefore still treated as a byte sequence. Autocomplete uses unsigned-byte lexicographic order rather than locale-aware or frequency-based ranking.

The loader reads the actual object schema and validates `unique_tokens` against the `token_frequencies` array. Each array item must contain a token string and a positive integer frequency, and duplicate token strings are rejected. Its schema-aware JSON reader supports UTF-8 and escaped JSON strings without adding a third-party dependency.

## Complexity

Let `L` be the input token or prefix length in bytes, `d_i` the number of children at the node visited for byte `i`, and `B <= 256` the byte alphabet size.

- Insertion, exact search, and prefix search take `O(sum(log d_i))`, bounded by `O(L log B)`. Since `B` is fixed, this is commonly described as `O(L)`.
- Autocomplete takes `O(L log B + S + R)`, where `S` is the number of Trie nodes visited while enumerating at most `k` matches and `R` is the total number of bytes copied into returned strings. It is output-sensitive and is not always `O(L)`.
- Memory is `O(N)` Trie nodes in the worst case, where `N` is the sum of byte lengths of all distinct inserted tokens, plus ordered-map and ownership overhead at each node. Shared prefixes reduce the actual node count.

Current limitations include bytewise rather than Unicode-aware traversal, ordered-map overhead, lexicographic rather than frequency-ranked autocomplete, and an in-memory vocabulary load. The inverted index, matching algorithms, pybind11 bindings, and benchmarks remain future work.
