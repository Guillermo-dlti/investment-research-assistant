#include "kmp.h"
#include "preprocessed_collection_loader.h"
#include "z_function.h"

#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

namespace {

void printValues(const std::vector<std::size_t>& values) {
    for (const std::size_t value : values) {
        std::cout << ' ' << value;
    }
    if (values.empty()) {
        std::cout << " <none>";
    }
}

void showMatch(
    const std::string& label,
    const std::string& text,
    const std::string& pattern
) {
    const auto z_positions = zSearch(text, pattern);
    const auto kmp_positions = kmpSearch(text, pattern);
    std::cout << label << "\n  pattern: " << pattern << "\n  Z positions:";
    printValues(z_positions);
    std::cout << "\n  count: " << zCount(text, pattern)
              << "\n  agrees with KMP: " << std::boolalpha
              << (z_positions == kmp_positions) << '\n';
}

std::string joinTokens(const std::vector<std::string>& tokens) {
    std::string text;
    for (const std::string& token : tokens) {
        if (!text.empty()) {
            text.push_back(' ');
        }
        text += token;
    }
    return text;
}

}  // namespace

int main(int argc, char* argv[]) {
    std::cout << "Z-array for abacaba:";
    printValues(computeZ("abacaba"));
    std::cout << '\n';
    showMatch("Basic exact search", "investment research assistant", "research");
    showMatch("Multiple occurrences", "revenue and revenue growth", "revenue");
    showMatch("Overlapping matches", "aaaaa", "aaa");
    showMatch("Financial punctuation", "revenue increased 12.5% to $97,858", "$97,858");
    showMatch("UTF-8", "café café", "é");

    const std::filesystem::path path = argc > 1
        ? argv[1]
        : "data/processed/preprocessed_collection.json";
    try {
        const auto collection = loadPreprocessedCollection(path);
        const std::string pattern = "artificial intelligence";
        for (const auto& chunk : collection.chunks) {
            const std::string text = joinTokens(chunk.tokens);
            const auto positions = zSearch(text, pattern);
            if (!positions.empty()) {
                const auto kmp_positions = kmpSearch(text, pattern);
                std::cout << "Real normalized chunk\n  chunk_id: " << chunk.chunk_id
                          << "\n  pattern: " << pattern << "\n  Z positions:";
                printValues(positions);
                std::cout << "\n  agrees with KMP: " << std::boolalpha
                          << (positions == kmp_positions) << '\n';
                return 0;
            }
        }
        std::cout << "Real normalized chunk\n  pattern not found\n";
    } catch (const std::exception& error) {
        std::cerr << "Z-function demonstration failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
