#include "inverted_index.h"

#include <algorithm>
#include <iterator>
#include <set>
#include <stdexcept>
#include <utility>

void InvertedIndex::addChunk(
    const std::string& chunk_id,
    const std::vector<std::string>& tokens,
    ChunkMetadata metadata_value
) {
    if (chunk_id.empty()) {
        throw std::invalid_argument("chunk_id must not be empty");
    }
    if (chunks_.find(chunk_id) != chunks_.end()) {
        throw std::invalid_argument("duplicate chunk_id: " + chunk_id);
    }

    std::unordered_map<std::string, std::size_t> frequencies;
    for (const std::string& token : tokens) {
        ++frequencies[token];
    }

    chunks_.emplace(chunk_id, std::move(metadata_value));
    for (const auto& [token, frequency] : frequencies) {
        index_[token].emplace(chunk_id, frequency);
    }
}

std::vector<std::string> InvertedIndex::getChunkIds(
    const std::string& token
) const {
    std::vector<std::string> chunk_ids;
    const auto term = index_.find(token);
    if (term == index_.end()) {
        return chunk_ids;
    }
    chunk_ids.reserve(term->second.size());
    for (const auto& [chunk_id, frequency] : term->second) {
        static_cast<void>(frequency);
        chunk_ids.push_back(chunk_id);
    }
    return chunk_ids;
}

std::size_t InvertedIndex::termFrequency(
    const std::string& token,
    const std::string& chunk_id
) const {
    const auto term = index_.find(token);
    if (term == index_.end()) {
        return 0;
    }
    const auto posting = term->second.find(chunk_id);
    return posting == term->second.end() ? 0 : posting->second;
}

std::size_t InvertedIndex::documentFrequency(const std::string& token) const {
    const auto term = index_.find(token);
    return term == index_.end() ? 0 : term->second.size();
}

std::size_t InvertedIndex::chunkCount() const noexcept {
    return chunks_.size();
}

std::size_t InvertedIndex::vocabularySize() const noexcept {
    return index_.size();
}

const ChunkMetadata* InvertedIndex::metadata(const std::string& chunk_id) const {
    const auto chunk = chunks_.find(chunk_id);
    return chunk == chunks_.end() ? nullptr : &chunk->second;
}

std::vector<std::string> InvertedIndex::uniqueTerms(
    const std::vector<std::string>& tokens
) {
    const std::set<std::string> unique(tokens.begin(), tokens.end());
    return {unique.begin(), unique.end()};
}

std::vector<std::string> InvertedIndex::andQuery(
    const std::vector<std::string>& tokens
) const {
    const std::vector<std::string> terms = uniqueTerms(tokens);
    if (terms.empty()) {
        return {};
    }

    std::vector<std::vector<std::string>> postings_lists;
    postings_lists.reserve(terms.size());
    for (const std::string& term : terms) {
        postings_lists.push_back(getChunkIds(term));
        if (postings_lists.back().empty()) {
            return {};
        }
    }
    std::sort(
        postings_lists.begin(), postings_lists.end(),
        [](const auto& left, const auto& right) {
            return left.size() < right.size();
        }
    );

    std::vector<std::string> result = std::move(postings_lists.front());
    for (std::size_t index = 1;
         index < postings_lists.size() && !result.empty(); ++index) {
        const std::vector<std::string>& next = postings_lists[index];
        std::vector<std::string> intersection;
        intersection.reserve(std::min(result.size(), next.size()));
        std::set_intersection(
            result.begin(), result.end(), next.begin(), next.end(),
            std::back_inserter(intersection)
        );
        result = std::move(intersection);
    }
    return result;
}

std::vector<std::string> InvertedIndex::orQuery(
    const std::vector<std::string>& tokens
) const {
    const std::vector<std::string> terms = uniqueTerms(tokens);
    std::vector<std::string> result;
    for (const std::string& term : terms) {
        const std::vector<std::string> next = getChunkIds(term);
        std::vector<std::string> combined;
        combined.reserve(result.size() + next.size());
        std::set_union(
            result.begin(), result.end(), next.begin(), next.end(),
            std::back_inserter(combined)
        );
        result = std::move(combined);
    }
    return result;
}

std::vector<RankedChunk> InvertedIndex::rank(
    const std::vector<std::string>& query_tokens,
    const std::vector<std::string>& matching_chunks
) const {
    const std::vector<std::string> terms = uniqueTerms(query_tokens);
    std::vector<RankedChunk> ranked;
    ranked.reserve(matching_chunks.size());
    for (const std::string& chunk_id : matching_chunks) {
        std::size_t score = 0;
        for (const std::string& term : terms) {
            score += termFrequency(term, chunk_id);
        }
        ranked.push_back({chunk_id, score});
    }
    std::sort(
        ranked.begin(), ranked.end(),
        [](const RankedChunk& left, const RankedChunk& right) {
            if (left.score != right.score) {
                return left.score > right.score;
            }
            return left.chunk_id < right.chunk_id;
        }
    );
    return ranked;
}

std::vector<RankedChunk> InvertedIndex::rankAnd(
    const std::vector<std::string>& tokens
) const {
    return rank(tokens, andQuery(tokens));
}

std::vector<RankedChunk> InvertedIndex::rankOr(
    const std::vector<std::string>& tokens
) const {
    return rank(tokens, orQuery(tokens));
}
