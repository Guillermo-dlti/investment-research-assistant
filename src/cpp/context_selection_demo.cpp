#include "context_selection.h"

#include <iostream>
#include <string>
#include <vector>

int main() {
    std::cout << "Greedy context selection: max 3 chunks, 600 word budget, redundant at Jaccard >= 0.5\n";
    JaccardIndex index;
    index.addChunk("NVDA_2025_0042", {"data", "center", "revenue", "grew", "on", "hopper", "demand"});
    index.addChunk("NVDA_2024_0040", {"data", "center", "revenue", "grew", "on", "hopper", "demand"});
    index.addChunk("NVDA_2025_0043", {"export", "controls", "limit", "sales", "to", "china"});
    index.addChunk("NVDA_2025_0100", {"gaming", "revenue", "declined"});
    index.addChunk("NVDA_2025_0101", {"automotive", "segment", "revenue"});

    const std::vector<ContextCandidate> candidates = {
        {"NVDA_2025_0042", 0.92, 250},
        {"NVDA_2024_0040", 0.90, 250},
        {"NVDA_2025_0043", 0.71, 250},
        {"NVDA_2025_0100", 0.55, 240},
        {"NVDA_2025_0101", 0.40, 80},
    };
    const ContextSelection selection = selectContext(index, candidates, 3, 600, 0.5);
    for (const ContextDecision& decision : selection.decisions) {
        std::cout << "  " << decision.rank << ". " << decision.chunk_id << " score=" << decision.score
                  << " words=" << decision.word_count << " -> " << decision.status;
        if (!decision.redundant_with.empty()) std::cout << " (copy of " << decision.redundant_with << ")";
        std::cout << " max_similarity=" << decision.max_similarity << '\n';
    }
    std::cout << "Selected " << selection.selected_ids.size() << " chunks, " << selection.total_words
              << " words\n";
    return 0;
}
