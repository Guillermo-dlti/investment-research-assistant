cmake_minimum_required(VERSION 3.16)

project(investment_research_assistant_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Python 3.11 COMPONENTS Interpreter Development.Module REQUIRED)
execute_process(
    COMMAND "${Python_EXECUTABLE}" -m pybind11 --cmakedir
    OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE PYBIND11_CMAKE_RESULT
)
if(NOT PYBIND11_CMAKE_RESULT EQUAL 0)
    message(FATAL_ERROR
        "pybind11 is unavailable for ${Python_EXECUTABLE}; install requirements.txt in .venv"
    )
endif()
find_package(pybind11 CONFIG REQUIRED PATHS "${PYBIND11_CMAKE_DIR}" NO_DEFAULT_PATH)

add_library(json_support src/cpp/json_reader.cpp)
target_include_directories(json_support PUBLIC src/cpp)

add_library(trie_core src/cpp/trie.cpp src/cpp/vocabulary_loader.cpp)
target_include_directories(trie_core PUBLIC src/cpp)
target_link_libraries(trie_core PUBLIC json_support)

add_library(inverted_index_core
    src/cpp/inverted_index.cpp
    src/cpp/preprocessed_collection_loader.cpp
)
target_include_directories(inverted_index_core PUBLIC src/cpp)
target_link_libraries(inverted_index_core PUBLIC json_support)

add_library(kmp_core src/cpp/kmp.cpp)
target_include_directories(kmp_core PUBLIC src/cpp)

if(CMAKE_CXX_COMPILER_ID MATCHES "AppleClang|Clang|GNU")
    target_compile_options(json_support PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(trie_core PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(inverted_index_core PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(kmp_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(trie_demo src/cpp/trie_demo.cpp)
target_link_libraries(trie_demo PRIVATE trie_core)

add_executable(inverted_index_demo src/cpp/inverted_index_demo.cpp)
target_link_libraries(inverted_index_demo PRIVATE inverted_index_core)

add_executable(kmp_demo src/cpp/kmp_demo.cpp)
target_link_libraries(kmp_demo PRIVATE kmp_core inverted_index_core)

pybind11_add_module(investment_engine MODULE src/cpp/python_bindings.cpp)
target_link_libraries(investment_engine PRIVATE trie_core inverted_index_core)
set_target_properties(
    investment_engine
    PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python"
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python"
)

enable_testing()
add_executable(trie_tests src/cpp/tests/trie_tests.cpp)
target_link_libraries(trie_tests PRIVATE trie_core)

add_executable(inverted_index_tests src/cpp/tests/inverted_index_tests.cpp)
target_link_libraries(inverted_index_tests PRIVATE inverted_index_core)

add_executable(kmp_tests src/cpp/tests/kmp_tests.cpp)
target_link_libraries(kmp_tests PRIVATE kmp_core)

set(SYNTHETIC_TRIE_TESTS
    insert_and_search
    missing_words
    prefix_search
    shared_prefixes
    duplicate_insertions
    empty_strings
    autocomplete_limits
    autocomplete_order
    financial_tokens
    utf8_tokens
)

foreach(TEST_NAME IN LISTS SYNTHETIC_TRIE_TESTS)
    add_test(NAME "trie_${TEST_NAME}" COMMAND trie_tests "${TEST_NAME}")
    set_tests_properties("trie_${TEST_NAME}" PROPERTIES LABELS "portable")
endforeach()

set(TRIE_VOCABULARY_PATH
    "${CMAKE_SOURCE_DIR}/data/metadata/vocabulary.json"
    CACHE FILEPATH
    "Path to the generated Step 9 vocabulary for local integration tests"
)

if(EXISTS "${TRIE_VOCABULARY_PATH}")
    add_test(
        NAME trie_load_actual_vocabulary
        COMMAND trie_tests load_actual_vocabulary "${TRIE_VOCABULARY_PATH}"
    )
    add_test(
        NAME trie_full_vocabulary_size
        COMMAND trie_tests full_vocabulary_size "${TRIE_VOCABULARY_PATH}"
    )
    set_tests_properties(
        trie_load_actual_vocabulary
        trie_full_vocabulary_size
        PROPERTIES LABELS "local_vocabulary"
    )
else()
    message(STATUS
        "Generated vocabulary not found; local-vocabulary CTests will not be registered"
    )
endif()

set(KMP_TESTS
    basic
    no_match
    multiple
    overlapping
    beginning
    end
    full_text
    longer_pattern
    empty_pattern
    empty_text
    repeated_prefix
    punctuation
    utf8
    lps_correctness
    byte_offsets
)

foreach(TEST_NAME IN LISTS KMP_TESTS)
    add_test(NAME "kmp_${TEST_NAME}" COMMAND kmp_tests "${TEST_NAME}")
    set_tests_properties("kmp_${TEST_NAME}" PROPERTIES LABELS "portable;kmp")
endforeach()

set(SYNTHETIC_INVERTED_INDEX_TESTS
    single_token_lookup
    missing_tokens
    repeated_tokens
    duplicate_chunk_ids
    and_intersection
    or_union
    repeated_query_terms
    empty_queries
    deterministic_ordering
    ranking_and_tie_breaking
    chunk_and_vocabulary_counts
)

foreach(TEST_NAME IN LISTS SYNTHETIC_INVERTED_INDEX_TESTS)
    add_test(
        NAME "inverted_index_${TEST_NAME}"
        COMMAND inverted_index_tests "${TEST_NAME}"
    )
    set_tests_properties(
        "inverted_index_${TEST_NAME}"
        PROPERTIES LABELS "portable"
    )
endforeach()

set(PREPROCESSED_COLLECTION_PATH
    "${CMAKE_SOURCE_DIR}/data/processed/preprocessed_collection.json"
    CACHE FILEPATH
    "Path to the generated Step 9 collection for local integration tests"
)

if(EXISTS "${PREPROCESSED_COLLECTION_PATH}")
    add_test(
        NAME inverted_index_real_collection_loading
        COMMAND inverted_index_tests
            real_collection_loading
            "${PREPROCESSED_COLLECTION_PATH}"
    )
    set_tests_properties(
        inverted_index_real_collection_loading
        PROPERTIES LABELS "local_collection"
    )
else()
    message(STATUS
        "Preprocessed collection not found; local collection CTest will not be registered"
    )
endif()
