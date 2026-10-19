#ifndef INVESTMENT_RESEARCH_ASSISTANT_NGRAM_JACCARD_H
#define INVESTMENT_RESEARCH_ASSISTANT_NGRAM_JACCARD_H

#include <cstddef>
#include <optional>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

// N-gram sets are sorted and duplicate-free so Jaccard can merge them linearly.
using NgramSet = std::vector<std::string>;

// Byte n-grams of text. A nonempty text shorter than n yields itself.
[[nodiscard]] NgramSet characterNgrams(const std::string& text, std::size_t n);

// Every run of min_n..max_n consecutive tokens, joined by one space.
[[nodiscard]] NgramSet wordNgrams(
    const std::vector<std::string>& tokens,
    std::size_t min_n,
    std::size_t max_n
);

// |A ∩ B| / |A ∪ B| for sorted, duplicate-free sets; 0 when both are empty.
[[nodiscard]] double jaccardSimilarity(const NgramSet& first, const NgramSet& second);

struct JaccardResult {
    std::string chunk_id;
    double score;
    std::size_t shared_ngrams;
    std::size_t union_size;
};

// Stores each chunk's word n-gram set and ranks chunks against a query by
// Jaccard similarity with a full scan.
class JaccardIndex {
public:
    explicit JaccardIndex(std::size_t min_n = 1, std::size_t max_n = 2);

    void addChunk(const std::string& chunk_id, const std::vector<std::string>& tokens);

    // Score descending (exact fraction comparison), then chunk_id ascending.
    // Chunks with no shared n-gram are omitted.
    [[nodiscard]] std::vector<JaccardResult> rank(
        const std::vector<std::string>& query_tokens,
        std::optional<std::size_t> top_k = std::nullopt
    ) const;

    // One result per chunk ID, in input order, including chunks with no
    // shared n-gram (score 0). Throws std::invalid_argument for an unknown ID.
    [[nodiscard]] std::vector<JaccardResult> scoreChunks(
        const std::vector<std::string>& chunk_ids,
        const std::vector<std::string>& query_tokens
    ) const;

    [[nodiscard]] std::size_t chunkCount() const;
    [[nodiscard]] std::size_t minN() const;
    [[nodiscard]] std::size_t maxN() const;

private:
    std::size_t min_n_;
    std::size_t max_n_;
    std::vector<std::pair<std::string, NgramSet>> chunks_;
    std::unordered_map<std::string, std::size_t> positions_;
};

#endif
