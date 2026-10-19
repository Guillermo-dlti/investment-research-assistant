#ifndef INVESTMENT_RESEARCH_ASSISTANT_VOCABULARY_LOADER_H
#define INVESTMENT_RESEARCH_ASSISTANT_VOCABULARY_LOADER_H

#include <cstddef>
#include <filesystem>
#include <string>
#include <vector>

struct VocabularyEntry {
    std::string token;
    std::size_t frequency;
};

struct VocabularyData {
    std::size_t declared_unique_tokens;
    std::vector<VocabularyEntry> entries;
};

VocabularyData loadVocabulary(const std::filesystem::path& path);

#endif
