#include "approximate_rerank.h"

#include <cmath>
#include <functional>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

void expect(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

bool near(double actual, double expected) { return std::fabs(actual - expected) < 1e-12; }

template <typename Callable>
bool throwsInvalidArgument(Callable&& callable) {
    try {
        callable();
    } catch (const std::invalid_argument&) {
        return true;
    }
    return false;
}

// Both indexes over the same three tiny chunks.
struct Fixture {
    InvertedIndex index;
    JaccardIndex jaccard;

    void add(const std::string& chunk_id, const std::vector<std::string>& tokens) {
        index.addChunk(chunk_id, tokens);
        jaccard.addChunk(chunk_id, tokens);
    }
};

Fixture sampleFixture() {
    Fixture fixture;
    fixture.add("C1", {"nvidia", "revenue", "grew"});
    fixture.add("C2", {"amd", "revenue"});
    fixture.add("C3", {"nvidia", "cloud", "chips"});
    return fixture;
}

const std::vector<std::string> kCandidates = {"C1", "C2", "C3"};
const std::vector<std::string> kQuery = {"nvidia", "revenue"};

std::vector<std::string> ids(const std::vector<ApproximateResult>& results) {
    std::vector<std::string> result;
    for (const ApproximateResult& item : results) result.push_back(item.chunk_id);
    return result;
}

const ApproximateResult& find(const std::vector<ApproximateResult>& results, const std::string& id) {
    for (const ApproximateResult& item : results) {
        if (item.chunk_id == id) return item;
    }
    throw std::runtime_error("missing result " + id);
}

void handComputed() {
    // Query n-grams {nvidia, nvidia revenue, revenue}; revenue was a correction at distance 1.
    // C1: J = 3/5, coverage = (1 + 0.5) / 2 = 0.75, score = 0.6*0.75 + 0.4*1 = 0.85
    // C2: J = 1/5, coverage = 0.5 / 2 = 0.25, score = 0.6*0.25 + 0.4*(1/3)
    // C3: J = 1/7, coverage = 1 / 2 = 0.5, score = 0.6*0.5 + 0.4*(5/21)
    const Fixture fixture = sampleFixture();
    const auto results = rerankCandidates(
        fixture.index, fixture.jaccard, kCandidates,
        {{"nvidia", 1.0}, {"revenue", 0.5}}, kQuery, 0.6
    );
    expect(ids(results) == std::vector<std::string>({"C1", "C3", "C2"}), "score order");
    const ApproximateResult& c1 = find(results, "C1");
    const ApproximateResult& c2 = find(results, "C2");
    const ApproximateResult& c3 = find(results, "C3");
    expect(near(c1.coverage, 0.75) && c1.matched_terms == 2, "C1 coverage");
    expect(near(c1.jaccard, 0.6) && near(c1.jaccard_scaled, 1.0), "C1 jaccard is J_max");
    expect(near(c1.score, 0.85), "C1 score");
    expect(near(c2.coverage, 0.25) && c2.matched_terms == 1, "C2 coverage");
    expect(near(c2.jaccard_scaled, 1.0 / 3.0), "C2 scaled jaccard");
    expect(near(c2.score, 0.15 + 0.4 / 3.0), "C2 score");
    expect(near(c3.jaccard_scaled, 5.0 / 21.0), "C3 scaled jaccard");
    expect(near(c3.score, 0.3 + 0.4 * 5.0 / 21.0), "C3 score");
    for (const ApproximateResult& result : results) {
        expect(
            near(result.score, 0.6 * result.coverage + 0.4 * result.jaccard_scaled),
            "score follows the formula"
        );
        expect(result.score >= 0.0 && result.score <= 1.0, "score in [0, 1]");
    }
}
void zeroJaccardMax() {
    const Fixture fixture = sampleFixture();
    const auto results = rerankCandidates(
        fixture.index, fixture.jaccard, {"C2", "C1"}, {{"zzz", 1.0}}, {"zzz"}, 0.6
    );
    expect(ids(results) == std::vector<std::string>({"C1", "C2"}), "all zero ties by chunk_id");
    for (const ApproximateResult& result : results) {
        expect(result.jaccard == 0.0 && result.jaccard_scaled == 0.0, "J_max 0 scales to 0");
        expect(result.score == 0.0 && result.coverage == 0.0, "nothing matched scores 0");
    }
}
void typoWeight() {
    const Fixture fixture = sampleFixture();
    const auto exact = rerankCandidates(
        fixture.index, fixture.jaccard, {"C1"}, {{"nvidia", 1.0}}, {"nvidia"}, 0.6
    );
    const auto corrected = rerankCandidates(
        fixture.index, fixture.jaccard, {"C1"}, {{"nvidia", 0.5}}, {"nvidia"}, 0.6
    );
    expect(near(exact[0].coverage, 1.0), "exact term counts 1");
    expect(near(corrected[0].coverage, 0.5), "corrected term counts its weight");
    expect(corrected[0].score < exact[0].score, "correction scores strictly lower");
}
void alphaBounds() {
    const Fixture fixture = sampleFixture();
    const std::vector<WeightedTerm> terms = {{"nvidia", 1.0}, {"revenue", 0.5}};
    const auto coverageOnly =
        rerankCandidates(fixture.index, fixture.jaccard, kCandidates, terms, kQuery, 1.0);
    expect(near(find(coverageOnly, "C3").score, 0.5), "alpha 1 is coverage only");
    const auto jaccardOnly =
        rerankCandidates(fixture.index, fixture.jaccard, kCandidates, terms, kQuery, 0.0);
    expect(near(find(jaccardOnly, "C2").score, 1.0 / 3.0), "alpha 0 is scaled jaccard only");
}
void tieBreak() {
    Fixture fixture;
    fixture.add("B", {"revenue", "growth"});
    fixture.add("A", {"revenue", "growth"});
    const auto results = rerankCandidates(
        fixture.index, fixture.jaccard, {"B", "A"}, {{"revenue", 1.0}}, {"revenue"}, 0.6
    );
    expect(ids(results) == std::vector<std::string>({"A", "B"}), "equal scores tie by chunk_id");
}
void limits() {
    const Fixture fixture = sampleFixture();
    const std::vector<WeightedTerm> terms = {{"nvidia", 1.0}};
    const auto all = rerankCandidates(fixture.index, fixture.jaccard, kCandidates, terms, kQuery, 0.6);
    const auto one = rerankCandidates(fixture.index, fixture.jaccard, kCandidates, terms, kQuery, 0.6, 1);
    expect(all.size() == 3, "no top_k returns every candidate");
    expect(ids(one) == std::vector<std::string>({all[0].chunk_id}), "top_k keeps the best");
    expect(near(one[0].jaccard_scaled, all[0].jaccard_scaled), "J_max is taken before top_k");
    expect(
        rerankCandidates(fixture.index, fixture.jaccard, kCandidates, terms, kQuery, 0.6, 0).empty(),
        "top_k zero returns nothing"
    );
    expect(
        rerankCandidates(fixture.index, fixture.jaccard, {}, terms, kQuery, 0.6).empty(),
        "no candidates returns nothing"
    );
    const auto noTerms = rerankCandidates(fixture.index, fixture.jaccard, {"C1"}, {}, kQuery, 0.6);
    expect(noTerms.size() == 1 && noTerms[0].coverage == 0.0, "no terms gives coverage 0");
}
void validation() {
    const Fixture fixture = sampleFixture();
    const std::vector<WeightedTerm> terms = {{"nvidia", 1.0}};
    const auto call = [&fixture](
        std::vector<std::string> candidates, std::vector<WeightedTerm> weighted, double alpha
    ) {
        return [&fixture, candidates = std::move(candidates), weighted = std::move(weighted), alpha] {
            (void)rerankCandidates(fixture.index, fixture.jaccard, candidates, weighted, kQuery, alpha, 0);
        };
    };
    expect(throwsInvalidArgument(call(kCandidates, terms, 1.5)), "alpha above 1 rejected");
    expect(throwsInvalidArgument(call(kCandidates, terms, -0.1)), "alpha below 0 rejected");
    expect(throwsInvalidArgument(call(kCandidates, terms, std::nan(""))), "NaN alpha rejected");
    expect(throwsInvalidArgument(call(kCandidates, {{"nvidia", 0.0}}, 0.6)), "weight 0 rejected");
    expect(throwsInvalidArgument(call(kCandidates, {{"nvidia", 1.5}}, 0.6)), "weight above 1 rejected");
    expect(throwsInvalidArgument(call({"C1", "C1"}, terms, 0.6)), "duplicate ID rejected");
    expect(throwsInvalidArgument(call({"C9"}, terms, 0.6)), "unknown ID rejected");
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::map<std::string, std::function<void()>> tests = {
        {"hand_computed", handComputed}, {"zero_jaccard_max", zeroJaccardMax},
        {"typo_weight", typoWeight}, {"alpha_bounds", alphaBounds},
        {"tie_break", tieBreak}, {"limits", limits}, {"validation", validation},
    };
    if (argc != 2 || tests.find(argv[1]) == tests.end()) {
        std::cerr << "Usage: approximate_rerank_tests TEST_NAME\n";
        return 2;
    }
    try {
        tests.at(argv[1])();
        std::cout << "PASS: " << argv[1] << '\n';
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << argv[1] << ": " << error.what() << '\n';
        return 1;
    }
    return 0;
}
