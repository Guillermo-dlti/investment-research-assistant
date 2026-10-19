cmake_minimum_required(VERSION 3.16)

project(investment_research_assistant_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(trie_core
    src/cpp/trie.cpp
    src/cpp/vocabulary_loader.cpp
)
target_include_directories(trie_core PUBLIC src/cpp)

if(CMAKE_CXX_COMPILER_ID MATCHES "AppleClang|Clang|GNU")
    target_compile_options(trie_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(trie_demo src/cpp/trie_demo.cpp)
target_link_libraries(trie_demo PRIVATE trie_core)

enable_testing()
add_executable(trie_tests src/cpp/tests/trie_tests.cpp)
target_link_libraries(trie_tests PRIVATE trie_core)

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
