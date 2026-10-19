#include "kmp.h"
#include "preprocessed_collection_loader.h"

#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

namespace {

void showMatch(
    const std::string& label,
    const std::string& text,
    const std::string& pattern
) {
    const std::vector<std::size_t> positions = kmpSearch(text, pattern);
    std::cout << label << "\n  pattern: " << pattern << "\n  positions:";
    for (const std::size_t position : positions) {
        std::cout << ' ' << position;
    }
    if (positions.empty()) {
        std::cout << " <none>";
    }
    std::cout << "\n  count: " << kmpCount(text, pattern) << '\n';
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
    showMatch("Basic exact search", "investment research assistant", "research");
    showMatch("Multiple occurrences", "revenue and revenue growth", "revenue");
    showMatch("Overlapping matches", "aaaaa", "aaa");
    showMatch(
        "Financial phrase",
        "artificial intelligence supports financial research",
        "artificial intelligence"
    );
    showMatch(
        "Financial punctuation",
        "revenue increased 12.5% to $97,858",
        "$97,858"
    );

    const std::filesystem::path collection_path =
        argc > 1 ? argv[1] : "data/processed/preprocessed_collection.json";
    try {
        const PreprocessedCollection collection =
            loadPreprocessedCollection(collection_path);
        const std::string real_pattern = "artificial intelligence";
        for (const PreprocessedChunk& chunk : collection.chunks) {
            const std::string token_text = joinTokens(chunk.tokens);
            const auto positions = kmpSearch(token_text, real_pattern);
            if (!positions.empty()) {
                std::cout << "Real normalized chunk\n"
                          << "  chunk_id: " << chunk.chunk_id << '\n'
                          << "  pattern: " << real_pattern << '\n'
                          << "  first byte position: " << positions.front() << '\n'
                          << "  count: " << positions.size() << '\n';
                return 0;
            }
        }
        std::cout << "Real normalized chunk\n  pattern not found\n";
    } catch (const std::exception& error) {
        std::cerr << "KMP demonstration failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
