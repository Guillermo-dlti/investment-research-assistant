#include "approximate_rerank.h"

#include <algorithm>
#include <stdexcept>
#include <unordered_set>

namespace {

void validate(
    const InvertedIndex& index,
    const std::vector<std::string>& candidate_ids,
    const std::vector<WeightedTerm>& terms,
    const double alpha
) {
    // Written so NaN fails both comparisons and is rejected.
    if (!(alpha >= 0.0 && alpha <= 1.0)) {
        throw std::invalid_argument("alpha must be in [0, 1]");
    }
    for (const WeightedTerm& term : terms) {
        if (!(term.weight > 0.0 && term.weight <= 1.0)) {
            throw std::invalid_argument("term weight must be in (0, 1]: " + term.term);
        }
    }
    std::unordered_set<std::string> seen;
    for (const std::string& chunk_id : candidate_ids) {
        if (index.metadata(chunk_id) == nullptr) {
            throw std::invalid_argument("unknown chunk ID: " + chunk_id);
        }
        if (!seen.insert(chunk_id).second) {
            throw std::invalid_argument("duplicate chunk ID: " + chunk_id);
        }
    }
}

}  // namespace

std::vector<ApproximateResult> rerankCandidates(
    const InvertedIndex& index,
    const JaccardIndex& jaccard_index,
    const std::vector<std::string>& candidate_ids,
    const std::vector<WeightedTerm>& terms,
    const std::vector<std::string>& ngram_tokens,
    const double alpha,
    const std::optional<std::size_t> top_k
) {
    validate(index, candidate_ids, terms, alpha);
    if (candidate_ids.empty() || top_k == std::optional<std::size_t>(0)) {
        return {};
    }

    const std::vector<JaccardResult> jaccard =
        jaccard_index.scoreChunks(candidate_ids, ngram_tokens);
    double jaccard_max = 0.0;
    for (const JaccardResult& result : jaccard) {
        jaccard_max = std::max(jaccard_max, result.score);
    }

    std::vector<ApproximateResult> results;
    results.reserve(candidate_ids.size());
    for (std::size_t position = 0; position < candidate_ids.size(); ++position) {
        const std::string& chunk_id = candidate_ids[position];
        double weight_sum = 0.0;
        std::size_t matched = 0;
        for (const WeightedTerm& term : terms) {
            if (index.termFrequency(term.term, chunk_id) > 0) {
                weight_sum += term.weight;
                ++matched;
            }
        }
        const double coverage = terms.empty()
            ? 0.0
            : std::min(1.0, weight_sum / static_cast<double>(terms.size()));
        const double raw = jaccard[position].score;
        const double scaled = jaccard_max > 0.0 ? raw / jaccard_max : 0.0;
        const double score = alpha * coverage + (1.0 - alpha) * scaled;
        results.push_back({
            chunk_id,
            std::clamp(score, 0.0, 1.0),
            coverage,
            raw,
            scaled,
            matched,
        });
    }

    std::sort(
        results.begin(), results.end(),
        [](const ApproximateResult& left, const ApproximateResult& right) {
            if (left.score != right.score) return left.score > right.score;
            return left.chunk_id < right.chunk_id;
        }
    );
    if (top_k && results.size() > *top_k) {
        results.resize(*top_k);
    }
    return results;
}
