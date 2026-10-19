#include "levenshtein.h"

#include <algorithm>
#include <stdexcept>

namespace {

std::size_t absoluteDifference(const std::size_t first, const std::size_t second) {
    return first > second ? first - second : second - first;
}

// Fills the classic DP table two rows at a time. When bounded, stops once
// every cell in the current row exceeds the bound, because later rows can
// only grow from there.
std::size_t editDistance(
    const std::string& first,
    const std::string& second,
    const std::optional<std::size_t> bound
) {
    // Keep the shorter string along the row so memory is O(min(n, m)).
    const std::string& rows = first.size() >= second.size() ? first : second;
    const std::string& columns = first.size() >= second.size() ? second : first;

    if (bound && rows.size() - columns.size() > *bound) {
        return *bound + 1;
    }

    std::vector<std::size_t> previous(columns.size() + 1);
    std::vector<std::size_t> current(columns.size() + 1);
    for (std::size_t column = 0; column <= columns.size(); ++column) {
        previous[column] = column;
    }

    for (std::size_t row = 1; row <= rows.size(); ++row) {
        current[0] = row;
        std::size_t row_minimum = current[0];
        for (std::size_t column = 1; column <= columns.size(); ++column) {
            const std::size_t substitution =
                previous[column - 1] + (rows[row - 1] == columns[column - 1] ? 0 : 1);
            const std::size_t deletion = previous[column] + 1;
            const std::size_t insertion = current[column - 1] + 1;
            current[column] = std::min({substitution, deletion, insertion});
            row_minimum = std::min(row_minimum, current[column]);
        }
        if (bound && row_minimum > *bound) {
            return *bound + 1;
        }
        std::swap(previous, current);
    }

    const std::size_t distance = previous[columns.size()];
    if (bound && distance > *bound) {
        return *bound + 1;
    }
    return distance;
}

}  // namespace

std::size_t levenshteinDistance(const std::string& first, const std::string& second) {
    return editDistance(first, second, std::nullopt);
}

std::size_t boundedLevenshtein(
    const std::string& first,
    const std::string& second,
    const std::size_t max_distance
) {
    return editDistance(first, second, max_distance);
}

std::size_t defaultMaxDistance(const std::string& word) {
    return word.size() <= 4 ? 1 : 2;
}

void FuzzyMatcher::addWord(const std::string& word, const std::size_t frequency) {
    if (word.empty()) {
        throw std::invalid_argument("fuzzy matcher words must be nonempty");
    }
    if (!frequencies_.emplace(word, frequency).second) {
        throw std::invalid_argument("duplicate fuzzy matcher word: " + word);
    }
    words_by_length_[word.size()].push_back(word);
}

std::vector<FuzzyMatch> FuzzyMatcher::match(
    const std::string& query,
    const std::size_t limit,
    const std::optional<std::size_t> max_distance
) const {
    if (query.empty() || limit == 0) {
        return {};
    }

    const auto exact = frequencies_.find(query);
    if (exact != frequencies_.end()) {
        return {{exact->first, 0, exact->second}};
    }

    const std::size_t bound = max_distance.value_or(defaultMaxDistance(query));
    const std::size_t shortest = query.size() > bound ? query.size() - bound : 0;
    const std::size_t longest = query.size() + bound;

    std::vector<FuzzyMatch> matches;
    for (auto bucket = words_by_length_.lower_bound(shortest);
         bucket != words_by_length_.end() && bucket->first <= longest;
         ++bucket) {
        if (absoluteDifference(bucket->first, query.size()) > bound) {
            continue;
        }
        for (const std::string& word : bucket->second) {
            const std::size_t distance = boundedLevenshtein(query, word, bound);
            if (distance <= bound) {
                matches.push_back({word, distance, frequencies_.at(word)});
            }
        }
    }

    std::sort(matches.begin(), matches.end(), [](const FuzzyMatch& left, const FuzzyMatch& right) {
        if (left.distance != right.distance) return left.distance < right.distance;
        if (left.frequency != right.frequency) return left.frequency > right.frequency;
        return left.word < right.word;
    });
    if (matches.size() > limit) {
        matches.resize(limit);
    }
    return matches;
}

std::size_t FuzzyMatcher::size() const {
    return frequencies_.size();
}
