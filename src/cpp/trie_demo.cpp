#include "trie.h"
#include "vocabulary_loader.h"

#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

namespace {

void showSearch(const Trie& trie, const std::string& token) {
    std::cout << "search(\"" << token << "\"): "
              << std::boolalpha << trie.search(token) << '\n';
}

void showPrefix(const Trie& trie, const std::string& prefix) {
    std::cout << "startsWith(\"" << prefix << "\"): "
              << std::boolalpha << trie.startsWith(prefix) << '\n';
}

void showAutocomplete(const Trie& trie, const std::string& prefix, std::size_t k) {
    const std::vector<std::string> matches = trie.autocomplete(prefix, k);
    std::cout << "autocomplete(\"" << prefix << "\", " << k << "):";
    for (const std::string& match : matches) {
        std::cout << ' ' << match;
    }
    if (matches.empty()) {
        std::cout << " <no matches>";
    }
    std::cout << '\n';
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::filesystem::path vocabulary_path =
        argc > 1 ? argv[1] : "data/metadata/vocabulary.json";

    try {
        const VocabularyData vocabulary = loadVocabulary(vocabulary_path);
        Trie trie;
        for (const VocabularyEntry& entry : vocabulary.entries) {
            trie.insert(entry.token);
        }

        std::cout << "Vocabulary: " << vocabulary_path << '\n';
        std::cout << "Declared unique tokens: "
                  << vocabulary.declared_unique_tokens << '\n';
        std::cout << "Unique tokens inserted: " << trie.size() << "\n\n";

        showSearch(trie, "nvidia");
        showSearch(trie, "nvda");
        showSearch(trie, "s&p");
        showSearch(trie, "not-in-vocabulary");
        showSearch(trie, "NVIDIA");
        std::cout << '\n';

        showPrefix(trie, "nv");
        showPrefix(trie, "ai-");
        showPrefix(trie, "definitely-missing-prefix");
        std::cout << '\n';

        showAutocomplete(trie, "nv", 10);
        showAutocomplete(trie, "year-over-", 10);
        showAutocomplete(trie, "", 5);
        showAutocomplete(trie, "nv", 0);
    } catch (const std::exception& error) {
        std::cerr << "Trie demonstration failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
