#include "context_selection.h"

#include <algorithm>
#include <stdexcept>
#include <unordered_set>

namespace {

void validate(
    const JaccardIndex& jaccard_index,
    const std::vector<ContextCandidate>& candidates,
    const std::size_t max_chunks,
    const double redundancy_threshold
) {
    if (max_chunks == 0) {
        throw std::invalid_argument("max_chunks must be positive");
    }
    // Written so NaN fails both comparisons and is rejected.
    if (!(redundancy_threshold > 0.0 && redundancy_threshold <= 1.0)) {
        throw std::invalid_argument("redundancy_threshold must be in (0, 1]");
    }
    std::unordered_set<std::string> seen;
    for (const ContextCandidate& candidate : candidates) {
        if (!jaccard_index.hasChunk(candidate.chunk_id)) {
            throw std::invalid_argument("unknown chunk ID: " + candidate.chunk_id);
        }
        if (!seen.insert(candidate.chunk_id).second) {
            throw std::invalid_argument("duplicate chunk ID: " + candidate.chunk_id);
        }
    }
}

}  // namespace

ContextSelection selectContext(
    const JaccardIndex& jaccard_index,
    const std::vector<ContextCandidate>& candidates,
    const std::size_t max_chunks,
    const std::size_t word_budget,
    const double redundancy_threshold
) {
    validate(jaccard_index, candidates, max_chunks, redundancy_threshold);

    std::vector<ContextCandidate> ordered = candidates;
    std::sort(ordered.begin(), ordered.end(), [](const ContextCandidate& a, const ContextCandidate& b) {
        if (a.score != b.score) return a.score > b.score;
        return a.chunk_id < b.chunk_id;
    });

    ContextSelection selection{{}, {}, 0};
    selection.decisions.reserve(ordered.size());
    for (std::size_t position = 0; position < ordered.size(); ++position) {
        const ContextCandidate& candidate = ordered[position];
        ContextDecision decision{
            candidate.chunk_id, position + 1, candidate.score, candidate.word_count, "", "", 0.0,
        };

        if (selection.selected_ids.size() >= max_chunks) {
            decision.status = "limit";
            selection.decisions.push_back(decision);
            continue;
        }

        for (const std::string& kept : selection.selected_ids) {
            const double similarity = jaccard_index.chunkSimilarity(candidate.chunk_id, kept);
            if (similarity > decision.max_similarity) {
                decision.max_similarity = similarity;
                decision.redundant_with = kept;
            }
        }

        if (decision.max_similarity >= redundancy_threshold) {
            decision.status = "redundant";
        } else if (selection.total_words + candidate.word_count > word_budget) {
            decision.status = "over_budget";
            decision.redundant_with.clear();
        } else {
            decision.status = "selected";
            decision.redundant_with.clear();
            selection.total_words += candidate.word_count;
            selection.selected_ids.push_back(candidate.chunk_id);
        }
        selection.decisions.push_back(decision);
    }
    return selection;
}
