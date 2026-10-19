#ifndef INVESTMENT_RESEARCH_ASSISTANT_APPROXIMATE_RERANK_H
#define INVESTMENT_RESEARCH_ASSISTANT_APPROXIMATE_RERANK_H

#include "inverted_index.h"
#include "ngram_jaccard.h"

#include <cstddef>
#include <optional>
#include <string>
#include <vector>

// A normalized query term and how much it counts in coverage: 1 for an exact
// vocabulary word, 1 / (1 + distance) for a Levenshtein correction.
struct WeightedTerm {
    std::string term;
    double weight;
};

struct ApproximateResult {
    std::string chunk_id;
    double score;
    double coverage;
    double jaccard;
    double jaccard_scaled;
    std::size_t matched_terms;
};

// Scores every candidate by
//   alpha * coverage + (1 - alpha) * jaccard / J_max
// where coverage is the summed weight of the terms present in the chunk
// divided by the number of terms, jaccard is the word n-gram Jaccard of
// ngram_tokens with the chunk, and J_max is the best jaccard over all
// candidates (scaled jaccard is 0 everywhere when J_max is 0).
// Order is score descending, then chunk_id ascending; top_k cuts afterwards.
// Throws std::invalid_argument for an unknown or duplicate candidate ID,
// alpha outside [0, 1], or a term weight outside (0, 1].
[[nodiscard]] std::vector<ApproximateResult> rerankCandidates(
    const InvertedIndex& index,
    const JaccardIndex& jaccard_index,
    const std::vector<std::string>& candidate_ids,
    const std::vector<WeightedTerm>& terms,
    const std::vector<std::string>& ngram_tokens,
    double alpha,
    std::optional<std::size_t> top_k = std::nullopt
);

#endif
