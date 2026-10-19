#include "kmp.h"

#include <utility>

std::vector<std::size_t> computeLps(const std::string& pattern) {
    std::vector<std::size_t> lps(pattern.size(), 0);
    std::size_t prefix_length = 0;
    std::size_t index = 1;

    while (index < pattern.size()) {
        if (pattern[index] == pattern[prefix_length]) {
            lps[index] = ++prefix_length;
            ++index;
        } else if (prefix_length != 0) {
            prefix_length = lps[prefix_length - 1];
        } else {
            lps[index] = 0;
            ++index;
        }
    }
    return lps;
}

namespace {

template <typename OnMatch>
void scanMatches(
    const std::string& text,
    const std::string& pattern,
    OnMatch&& on_match
) {
    if (pattern.empty() || pattern.size() > text.size()) {
        return;
    }

    const std::vector<std::size_t> lps = computeLps(pattern);
    std::size_t text_index = 0;
    std::size_t pattern_index = 0;
    while (text_index < text.size()) {
        if (text[text_index] == pattern[pattern_index]) {
            ++text_index;
            ++pattern_index;
            if (pattern_index == pattern.size()) {
                on_match(text_index - pattern.size());
                pattern_index = lps[pattern_index - 1];
            }
        } else if (pattern_index != 0) {
            pattern_index = lps[pattern_index - 1];
        } else {
            ++text_index;
        }
    }
}

}  // namespace

std::vector<std::size_t> kmpSearch(
    const std::string& text,
    const std::string& pattern
) {
    std::vector<std::size_t> positions;
    scanMatches(text, pattern, [&positions](const std::size_t position) {
        positions.push_back(position);
    });
    return positions;
}

std::size_t kmpCount(const std::string& text, const std::string& pattern) {
    std::size_t count = 0;
    scanMatches(text, pattern, [&count](const std::size_t) { ++count; });
    return count;
}
