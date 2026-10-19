#include "context_selection.h"

#include <functional>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void expect(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

template <typename Callable>
bool throwsInvalidArgument(Callable&& callable) {
    try {
        callable();
    } catch (const std::invalid_argument&) {
        return true;
    }
    return false;
}

// A and A_COPY repeat the same sentence (as FY2024 and FY2025 filings do);
// B and C are unrelated to A and to each other.
JaccardIndex sampleIndex() {
    JaccardIndex index;
    index.addChunk("A", {"data", "center", "revenue", "grew"});
    index.addChunk("A_COPY", {"data", "center", "revenue", "grew"});
    index.addChunk("B", {"export", "controls", "china"});
    index.addChunk("C", {"iphone", "net", "sales"});
    index.addChunk("D", {"gaming", "segment"});
    return index;
}

std::vector<std::string> statuses(const ContextSelection& selection) {
    std::vector<std::string> result;
    for (const ContextDecision& decision : selection.decisions) result.push_back(decision.status);
    return result;
}

void selectsTopInOrder() {
    const auto selection = selectContext(
        sampleIndex(), {{"C", 0.5, 100}, {"A", 0.9, 100}, {"B", 0.7, 100}}, 4, 1000, 0.5
    );
    expect(selection.selected_ids == std::vector<std::string>({"A", "B", "C"}), "score order");
    expect(selection.total_words == 300, "total words");
    expect(selection.decisions[0].rank == 1 && selection.decisions[2].rank == 3, "ranks");
}

void dropsRedundant() {
    const auto selection = selectContext(
        sampleIndex(), {{"A", 0.9, 100}, {"A_COPY", 0.8, 100}, {"B", 0.7, 100}}, 4, 1000, 0.5
    );
    expect(selection.selected_ids == std::vector<std::string>({"A", "B"}), "copy dropped");
    const ContextDecision& copy = selection.decisions[1];
    expect(copy.status == "redundant", "redundant status");
    expect(copy.redundant_with == "A", "names the kept chunk");
    expect(copy.max_similarity == 1.0, "identical similarity");
    expect(selection.total_words == 200, "redundant words not counted");
}

void skipsOverBudget() {
    // B does not fit after A, but the shorter C still does.
    const auto selection = selectContext(
        sampleIndex(), {{"A", 0.9, 600}, {"B", 0.8, 500}, {"C", 0.7, 300}}, 4, 1000, 0.5
    );
    expect(statuses(selection) == std::vector<std::string>({"selected", "over_budget", "selected"}), "skip, not stop");
    expect(selection.total_words == 900, "budget respected");
}

void respectsLimit() {
    const auto selection = selectContext(
        sampleIndex(), {{"A", 0.9, 10}, {"B", 0.8, 10}, {"C", 0.7, 10}, {"D", 0.6, 10}}, 2, 1000, 0.5
    );
    expect(statuses(selection) == std::vector<std::string>({"selected", "selected", "limit", "limit"}), "limit");
}

void tieBreak() {
    const auto selection = selectContext(sampleIndex(), {{"C", 0.5, 10}, {"B", 0.5, 10}}, 4, 1000, 0.5);
    expect(selection.selected_ids == std::vector<std::string>({"B", "C"}), "equal scores by chunk_id");
}

void thresholdOne() {
    // Only identical n-gram sets are redundant at threshold 1.
    const auto selection = selectContext(
        sampleIndex(), {{"A", 0.9, 10}, {"A_COPY", 0.8, 10}, {"B", 0.7, 10}}, 4, 1000, 1.0
    );
    expect(selection.selected_ids == std::vector<std::string>({"A", "B"}), "identical still dropped");
}

void emptyCandidates() {
    const auto selection = selectContext(sampleIndex(), {}, 4, 1000, 0.5);
    expect(selection.decisions.empty() && selection.selected_ids.empty(), "nothing selected");
    expect(selection.total_words == 0, "zero words");
}

void validation() {
    const JaccardIndex index = sampleIndex();
    const auto call = [&index](std::vector<ContextCandidate> candidates, std::size_t limit, double threshold) {
        return [&index, candidates, limit, threshold] {
            (void)selectContext(index, candidates, limit, 1000, threshold);
        };
    };
    expect(throwsInvalidArgument(call({{"A", 1.0, 1}}, 0, 0.5)), "max_chunks 0 rejected");
    expect(throwsInvalidArgument(call({{"A", 1.0, 1}}, 4, 0.0)), "threshold 0 rejected");
    expect(throwsInvalidArgument(call({{"A", 1.0, 1}}, 4, 1.5)), "threshold above 1 rejected");
    expect(throwsInvalidArgument(call({{"Z", 1.0, 1}}, 4, 0.5)), "unknown ID rejected");
    expect(throwsInvalidArgument(call({{"A", 1.0, 1}, {"A", 0.5, 1}}, 4, 0.5)), "duplicate ID rejected");
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::map<std::string, std::function<void()>> tests = {
        {"selects_top_in_order", selectsTopInOrder}, {"drops_redundant", dropsRedundant},
        {"skips_over_budget", skipsOverBudget}, {"respects_limit", respectsLimit},
        {"tie_break", tieBreak}, {"threshold_one", thresholdOne},
        {"empty_candidates", emptyCandidates}, {"validation", validation},
    };
    if (argc != 2 || tests.find(argv[1]) == tests.end()) {
        std::cerr << "Usage: context_selection_tests TEST_NAME\n";
        return 2;
    }
    try {
        tests.at(argv[1])();
        std::cout << "PASS: " << argv[1] << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << argv[1] << ": " << error.what() << '\n';
        return 1;
    }
}
