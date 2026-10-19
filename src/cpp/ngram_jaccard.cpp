#include "ngram_jaccard.h"

#include <algorithm>
#include <stdexcept>

namespace {

void sortUnique(NgramSet& grams) {
    std::sort(grams.begin(), grams.end());
    grams.erase(std::unique(grams.begin(), grams.end()), grams.end());
}

std::size_t sharedCount(const NgramSet& first, const NgramSet& second) {
    std::size_t shared = 0;
    auto left = first.begin();
    auto right = second.begin();
    while (left != first.end() && right != second.end()) {
        if (*left < *right) {
            ++left;
        } else if (*right < *left) {
            ++right;
        } else {
            ++shared;
            ++left;
            ++right;
        }
    }
    return shared;
}

}  // namespace

NgramSet characterNgrams(const std::string& text, const std::size_t n) {
    if (n == 0) {
        throw std::invalid_argument("n-gram size must be positive");
    }
    if (text.empty()) {
        return {};
    }
    if (text.size() < n) {
        return {text};
    }
    NgramSet grams;
    grams.reserve(text.size() - n + 1);
    for (std::size_t start = 0; start + n <= text.size(); ++start) {
        grams.push_back(text.substr(start, n));
    }
    sortUnique(grams);
    return grams;
}

NgramSet wordNgrams(
    const std::vector<std::string>& tokens,
    const std::size_t min_n,
    const std::size_t max_n
) {
    if (min_n == 0 || min_n > max_n) {
        throw std::invalid_argument("word n-gram range must satisfy 0 < min_n <= max_n");
    }
    NgramSet grams;
    for (std::size_t n = min_n; n <= max_n; ++n) {
        for (std::size_t start = 0; start + n <= tokens.size(); ++start) {
            std::string gram = tokens[start];
            for (std::size_t offset = 1; offset < n; ++offset) {
                gram += ' ';
                gram += tokens[start + offset];
            }
            grams.push_back(std::move(gram));
        }
    }
    sortUnique(grams);
    return grams;
}

double jaccardSimilarity(const NgramSet& first, const NgramSet& second) {
    const std::size_t shared = sharedCount(first, second);
    const std::size_t union_size = first.size() + second.size() - shared;
    if (union_size == 0) {
        return 0.0;
    }
    return static_cast<double>(shared) / static_cast<double>(union_size);
}

JaccardIndex::JaccardIndex(const std::size_t min_n, const std::size_t max_n)
    : min_n_(min_n), max_n_(max_n) {
    if (min_n == 0 || min_n > max_n) {
        throw std::invalid_argument("word n-gram range must satisfy 0 < min_n <= max_n");
    }
}

void JaccardIndex::addChunk(
    const std::string& chunk_id,
    const std::vector<std::string>& tokens
) {
    if (!positions_.emplace(chunk_id, chunks_.size()).second) {
        throw std::invalid_argument("duplicate chunk ID: " + chunk_id);
    }
    chunks_.emplace_back(chunk_id, wordNgrams(tokens, min_n_, max_n_));
}

std::vector<JaccardResult> JaccardIndex::rank(
    const std::vector<std::string>& query_tokens,
    const std::optional<std::size_t> top_k
) const {
    const NgramSet query = wordNgrams(query_tokens, min_n_, max_n_);
    if (query.empty() || top_k == std::optional<std::size_t>(0)) {
        return {};
    }

    std::vector<JaccardResult> results;
    for (const auto& [chunk_id, grams] : chunks_) {
        const std::size_t shared = sharedCount(query, grams);
        if (shared == 0) {
            continue;
        }
        const std::size_t union_size = query.size() + grams.size() - shared;
        results.push_back({
            chunk_id,
            static_cast<double>(shared) / static_cast<double>(union_size),
            shared,
            union_size,
        });
    }

    std::sort(results.begin(), results.end(), [](const JaccardResult& left, const JaccardResult& right) {
        // a/b > c/d  <=>  a*d > c*b, avoiding floating-point ties.
        const std::size_t left_cross = left.shared_ngrams * right.union_size;
        const std::size_t right_cross = right.shared_ngrams * left.union_size;
        if (left_cross != right_cross) return left_cross > right_cross;
        return left.chunk_id < right.chunk_id;
    });
    if (top_k && results.size() > *top_k) {
        results.resize(*top_k);
    }
    return results;
}

std::vector<JaccardResult> JaccardIndex::scoreChunks(
    const std::vector<std::string>& chunk_ids,
    const std::vector<std::string>& query_tokens
) const {
    const NgramSet query = wordNgrams(query_tokens, min_n_, max_n_);
    std::vector<JaccardResult> results;
    results.reserve(chunk_ids.size());
    for (const std::string& chunk_id : chunk_ids) {
        const auto position = positions_.find(chunk_id);
        if (position == positions_.end()) {
            throw std::invalid_argument("unknown chunk ID: " + chunk_id);
        }
        const NgramSet& grams = chunks_[position->second].second;
        const std::size_t shared = sharedCount(query, grams);
        const std::size_t union_size = query.size() + grams.size() - shared;
        results.push_back({
            chunk_id,
            union_size == 0 ? 0.0 : static_cast<double>(shared) / static_cast<double>(union_size),
            shared,
            union_size,
        });
    }
    return results;
}

std::size_t JaccardIndex::chunkCount() const {
    return chunks_.size();
}

std::size_t JaccardIndex::minN() const {
    return min_n_;
}

std::size_t JaccardIndex::maxN() const {
    return max_n_;
}
