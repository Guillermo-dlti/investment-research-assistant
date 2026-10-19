#ifndef INVESTMENT_RESEARCH_ASSISTANT_LEVENSHTEIN_H
#define INVESTMENT_RESEARCH_ASSISTANT_LEVENSHTEIN_H

#include <cstddef>
#include <map>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

// Edit distance with unit-cost insertion, deletion, and substitution over
// UTF-8 bytes. Time O(n * m), memory O(min(n, m)).
[[nodiscard]] std::size_t levenshteinDistance(
    const std::string& first,
    const std::string& second
);

// Same distance, but returns max_distance + 1 as soon as the true distance is
// known to exceed max_distance (length gap or a whole DP row above the bound).
[[nodiscard]] std::size_t boundedLevenshtein(
    const std::string& first,
    const std::string& second,
    std::size_t max_distance
);

// Default cutoff: 1 edit for words of up to 4 bytes, otherwise 2 edits.
[[nodiscard]] std::size_t defaultMaxDistance(const std::string& word);

struct FuzzyMatch {
    std::string word;
    std::size_t distance;
    std::size_t frequency;
};

// Finds vocabulary words within an edit distance of a query word. Words are
// bucketed by byte length so candidates outside the length window are skipped
// without computing a distance.
class FuzzyMatcher {
public:
    void addWord(const std::string& word, std::size_t frequency);

    // Ordered by distance, then descending frequency, then word. An exact hit
    // returns only that word. A limit of zero returns no matches.
    [[nodiscard]] std::vector<FuzzyMatch> match(
        const std::string& query,
        std::size_t limit,
        std::optional<std::size_t> max_distance = std::nullopt
    ) const;

    [[nodiscard]] std::size_t size() const;

private:
    std::unordered_map<std::string, std::size_t> frequencies_;
    std::map<std::size_t, std::vector<std::string>> words_by_length_;
};

#endif
