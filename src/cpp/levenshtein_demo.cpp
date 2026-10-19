#include "levenshtein.h"
#include "vocabulary_loader.h"

#include <chrono>
#include <exception>
#include <iostream>
#include <string>
#include <vector>

namespace {

void printDistance(const std::string& first, const std::string& second) {
    std::cout << "  " << first << " -> " << second << ": "
              << levenshteinDistance(first, second) << '\n';
}

}  // namespace

int main(int argc, char* argv[]) {
    std::cout << "Levenshtein distance\n";
    printDistance("kitten", "sitting");
    printDistance("nvidea", "nvidia");
    printDistance("revenu", "revenue");
    printDistance("microsfot", "microsoft");

    if (argc != 2) {
        std::cout << "\nPass data/metadata/vocabulary.json to run fuzzy vocabulary matching.\n";
        return 0;
    }

    try {
        const VocabularyData vocabulary = loadVocabulary(argv[1]);
        FuzzyMatcher matcher;
        for (const VocabularyEntry& entry : vocabulary.entries) {
            matcher.addWord(entry.token, entry.frequency);
        }
        std::cout << "\nFuzzy vocabulary matching over " << matcher.size() << " words\n";

        const std::vector<std::string> queries = {
            "nvidea", "revenu", "microsfot", "semiconducter", "artifical", "goverment", "nvidia",
        };
        for (const std::string& query : queries) {
            const auto start = std::chrono::steady_clock::now();
            const auto matches = matcher.match(query, 5);
            const auto elapsed = std::chrono::duration<double, std::micro>(
                std::chrono::steady_clock::now() - start
            ).count();
            std::cout << "  " << query << " (max " << defaultMaxDistance(query)
                      << ", " << elapsed << " us):";
            if (matches.empty()) std::cout << " no match";
            for (const FuzzyMatch& match : matches) {
                std::cout << ' ' << match.word << "[d=" << match.distance
                          << ", f=" << match.frequency << ']';
            }
            std::cout << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "Levenshtein demo failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
