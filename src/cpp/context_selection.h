#ifndef INVESTMENT_RESEARCH_ASSISTANT_CONTEXT_SELECTION_H
#define INVESTMENT_RESEARCH_ASSISTANT_CONTEXT_SELECTION_H

#include "ngram_jaccard.h"

#include <cstddef>
#include <string>
#include <vector>

// A retrieved chunk offered to the language model context.
struct ContextCandidate {
    std::string chunk_id;
    double score;
    std::size_t word_count;
};

// What happened to one candidate. status is "selected", "redundant" (too
// similar to an already selected chunk, named in redundant_with),
// "over_budget" (would exceed the word budget) or "limit" (max_chunks reached).
// max_similarity is the highest Jaccard against the chunks selected before it.
struct ContextDecision {
    std::string chunk_id;
    std::size_t rank;
    double score;
    std::size_t word_count;
    std::string status;
    std::string redundant_with;
    double max_similarity;
};

struct ContextSelection {
    std::vector<ContextDecision> decisions;
    std::vector<std::string> selected_ids;
    std::size_t total_words;
};

// Greedy selection in score descending, then chunk_id ascending order. A
// candidate is kept when fewer than max_chunks are kept, its Jaccard with
// every kept chunk is below redundancy_threshold, and it fits in the word
// budget. An over budget candidate is skipped, so a later shorter one can
// still fit. Decisions are returned in that walk order (rank starts at 1).
// Throws std::invalid_argument for an unknown or duplicate chunk ID,
// max_chunks of 0, or redundancy_threshold outside (0, 1].
[[nodiscard]] ContextSelection selectContext(
    const JaccardIndex& jaccard_index,
    const std::vector<ContextCandidate>& candidates,
    std::size_t max_chunks,
    std::size_t word_budget,
    double redundancy_threshold
);

#endif
