#include "trie.h"
#include "vocabulary_loader.h"

#include <filesystem>
#include <functional>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void expect(const bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void expectEqual(
    const std::vector<std::string>& actual,
    const std::vector<std::string>& expected,
    const std::string& message
) {
    expect(actual == expected, message);
}

void insertAndSearch() {
    Trie trie;
    trie.insert("nvidia");
    expect(trie.search("nvidia"), "inserted word should be found");
    expect(trie.size() == 1, "size should count the inserted word");
}

void missingWords() {
    Trie trie;
    trie.insert("nvidia");
    expect(!trie.search("nvda"), "missing word should not be found");
    expect(!trie.search("nvid"), "a prefix is not a complete word");
}

void prefixSearch() {
    Trie trie;
    trie.insert("microsoft");
    expect(trie.startsWith("micro"), "existing prefix should be found");
    expect(!trie.startsWith("macro"), "missing prefix should not be found");
}

void sharedPrefixes() {
    Trie trie;
    trie.insert("app");
    trie.insert("apple");
    trie.insert("application");
    expect(trie.search("app"), "prefix can also be a complete word");
    expect(trie.search("apple"), "shared-prefix word should be found");
    expect(trie.search("application"), "long shared-prefix word should be found");
}

void duplicateInsertions() {
    Trie trie;
    trie.insert("amd");
    trie.insert("amd");
    expect(trie.size() == 1, "duplicates must not increase unique size");
    expectEqual(trie.autocomplete("a", 10), {"amd"}, "duplicates must not appear");
}

void emptyStrings() {
    Trie trie;
    expect(trie.startsWith(""), "empty prefix should match the root");
    expect(!trie.search(""), "empty string is absent until inserted");
    trie.insert("");
    trie.insert("a");
    expect(trie.search(""), "inserted empty string should be searchable");
    expectEqual(trie.autocomplete("", 2), {"", "a"}, "empty-prefix order is wrong");
}

void autocompleteLimits() {
    Trie trie;
    for (const std::string& token : {"app", "apple", "apply", "apt"}) {
        trie.insert(token);
    }
    expect(trie.autocomplete("ap", 0).empty(), "k=0 must return no results");
    expect(trie.autocomplete("ap", 2).size() == 2, "result limit was not applied");
    expect(trie.autocomplete("missing", 4).empty(), "missing prefix must be empty");
}

void autocompleteOrder() {
    Trie trie;
    for (const std::string& token : {"apply", "apt", "application", "apple", "app"}) {
        trie.insert(token);
    }
    expectEqual(
        trie.autocomplete("ap", 10),
        {"app", "apple", "application", "apply", "apt"},
        "autocomplete should use deterministic bytewise lexicographic order"
    );
}

void financialTokens() {
    Trie trie;
    for (const std::string& token :
         {"s&p", "$97,858", "12.5%", "ai-powered", "nvidia's"}) {
        trie.insert(token);
        expect(trie.search(token), "financial token should be found: " + token);
    }
    expect(trie.startsWith("$97"), "punctuation prefix should be supported");
}

void utf8Tokens() {
    Trie trie;
    for (const std::string& token : {"chávez", "€1.5", "東京"}) {
        trie.insert(token);
        expect(trie.search(token), "UTF-8 token should be found: " + token);
    }
    expect(trie.startsWith("chá"), "UTF-8 prefix should be found");
}

VocabularyData loadActual(const std::filesystem::path& path) {
    const VocabularyData vocabulary = loadVocabulary(path);
    expect(!vocabulary.entries.empty(), "actual vocabulary should not be empty");
    expect(
        vocabulary.entries.size() == vocabulary.declared_unique_tokens,
        "declared and loaded vocabulary sizes differ"
    );
    return vocabulary;
}

void loadActualVocabulary(const std::filesystem::path& path) {
    const VocabularyData vocabulary = loadActual(path);
    Trie trie;
    for (const VocabularyEntry& entry : vocabulary.entries) {
        trie.insert(entry.token);
    }
    expect(trie.search("nvidia"), "actual vocabulary should contain nvidia");
    expect(trie.search("s&p"), "actual vocabulary should contain s&p");
    expect(trie.search("chávez"), "actual vocabulary should contain UTF-8 token chávez");
}

void fullVocabularySize(const std::filesystem::path& path) {
    const VocabularyData vocabulary = loadActual(path);
    expect(
        vocabulary.declared_unique_tokens == 14180,
        "actual Step 9 vocabulary should declare 14,180 unique tokens"
    );
    Trie trie;
    for (const VocabularyEntry& entry : vocabulary.entries) {
        trie.insert(entry.token);
    }
    expect(trie.size() == 14180, "Trie should contain all 14,180 unique tokens");
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::map<std::string, std::function<void()>> portable_tests = {
        {"insert_and_search", insertAndSearch},
        {"missing_words", missingWords},
        {"prefix_search", prefixSearch},
        {"shared_prefixes", sharedPrefixes},
        {"duplicate_insertions", duplicateInsertions},
        {"empty_strings", emptyStrings},
        {"autocomplete_limits", autocompleteLimits},
        {"autocomplete_order", autocompleteOrder},
        {"financial_tokens", financialTokens},
        {"utf8_tokens", utf8Tokens},
    };

    if (argc < 2) {
        std::cerr << "Usage: trie_tests TEST_NAME [VOCABULARY_PATH]\n";
        return 2;
    }

    try {
        const std::string test_name = argv[1];
        const auto portable = portable_tests.find(test_name);
        if (portable != portable_tests.end()) {
            portable->second();
        } else if (test_name == "load_actual_vocabulary" && argc == 3) {
            loadActualVocabulary(argv[2]);
        } else if (test_name == "full_vocabulary_size" && argc == 3) {
            fullVocabularySize(argv[2]);
        } else {
            std::cerr << "Unknown test or missing vocabulary path: " << test_name << '\n';
            return 2;
        }
        std::cout << "PASS: " << test_name << '\n';
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << argv[1] << ": " << error.what() << '\n';
        return 1;
    }
    return 0;
}
