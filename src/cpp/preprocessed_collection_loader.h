#ifndef INVESTMENT_RESEARCH_ASSISTANT_PREPROCESSED_COLLECTION_LOADER_H
#define INVESTMENT_RESEARCH_ASSISTANT_PREPROCESSED_COLLECTION_LOADER_H

#include <cstddef>
#include <filesystem>
#include <string>
#include <vector>

struct PreprocessedChunk {
    std::string chunk_id;
    std::string document_id;
    std::string ticker;
    int fiscal_year;
    std::string normalized_text;
    std::vector<std::string> tokens;
};

struct PreprocessedCollection {
    std::size_t declared_total_chunks;
    std::vector<PreprocessedChunk> chunks;
};

[[nodiscard]] PreprocessedCollection loadPreprocessedCollection(
    const std::filesystem::path& path
);

#endif
