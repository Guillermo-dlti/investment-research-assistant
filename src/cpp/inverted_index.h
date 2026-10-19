#ifndef INVESTMENT_RESEARCH_ASSISTANT_INVERTED_INDEX_H
#define INVESTMENT_RESEARCH_ASSISTANT_INVERTED_INDEX_H

#include <cstddef>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

struct ChunkMetadata {
    std::string document_id;
    std::string ticker;
    int fiscal_year = 0;
};

struct RankedChunk {
    std::string chunk_id;
    std::size_t score;
};

class InvertedIndex {
public:
    void addChunk(
        const std::string& chunk_id,
        const std::vector<std::string>& tokens,
        ChunkMetadata metadata = {}
    );

    [[nodiscard]] std::vector<std::string> getChunkIds(
        const std::string& token
    ) const;
    [[nodiscard]] std::size_t termFrequency(
        const std::string& token,
        const std::string& chunk_id
    ) const;
    [[nodiscard]] std::size_t documentFrequency(const std::string& token) const;
    [[nodiscard]] std::size_t chunkCount() const noexcept;
    [[nodiscard]] std::size_t vocabularySize() const noexcept;
    [[nodiscard]] const ChunkMetadata* metadata(const std::string& chunk_id) const;

    [[nodiscard]] std::vector<std::string> andQuery(
        const std::vector<std::string>& tokens
    ) const;
    [[nodiscard]] std::vector<std::string> orQuery(
        const std::vector<std::string>& tokens
    ) const;
    [[nodiscard]] std::vector<RankedChunk> rankAnd(
        const std::vector<std::string>& tokens
    ) const;
    [[nodiscard]] std::vector<RankedChunk> rankOr(
        const std::vector<std::string>& tokens
    ) const;

private:
    using Postings = std::map<std::string, std::size_t>;

    [[nodiscard]] static std::vector<std::string> uniqueTerms(
        const std::vector<std::string>& tokens
    );
    [[nodiscard]] std::vector<RankedChunk> rank(
        const std::vector<std::string>& query_tokens,
        const std::vector<std::string>& matching_chunks
    ) const;

    std::unordered_map<std::string, Postings> index_;
    std::unordered_map<std::string, ChunkMetadata> chunks_;
};

#endif
