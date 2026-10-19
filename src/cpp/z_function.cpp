#include "z_function.h"

#include <algorithm>

namespace {

std::vector<std::size_t> computeZSequence(const std::vector<unsigned int>& sequence) {
    std::vector<std::size_t> z(sequence.size(), 0);
    std::size_t left = 0;
    std::size_t right = 0;
    for (std::size_t index = 1; index < sequence.size(); ++index) {
        if (index < right) {
            z[index] = std::min(right - index, z[index - left]);
        }
        while (index + z[index] < sequence.size() &&
               sequence[z[index]] == sequence[index + z[index]]) {
            ++z[index];
        }
        if (index + z[index] > right) {
            left = index;
            right = index + z[index];
        }
    }
    return z;
}

std::vector<unsigned int> combinedSequence(
    const std::string& pattern,
    const std::string& text
) {
    // Input bytes occupy 0..255, so this value cannot collide with either
    // string, including embedded nulls and arbitrary UTF-8 byte sequences.
    constexpr unsigned int separator = 256;
    std::vector<unsigned int> combined;
    combined.reserve(pattern.size() + 1 + text.size());
    for (const unsigned char byte : pattern) combined.push_back(byte);
    combined.push_back(separator);
    for (const unsigned char byte : text) combined.push_back(byte);
    return combined;
}

template <typename OnMatch>
void scanMatches(
    const std::string& text,
    const std::string& pattern,
    OnMatch&& on_match
) {
    if (pattern.empty() || pattern.size() > text.size()) {
        return;
    }
    const auto combined = combinedSequence(pattern, text);
    const auto z = computeZSequence(combined);
    const std::size_t text_start = pattern.size() + 1;
    for (std::size_t index = text_start; index < combined.size(); ++index) {
        if (z[index] >= pattern.size()) {
            on_match(index - text_start);
        }
    }
}

}  // namespace

std::vector<std::size_t> computeZ(const std::string& text) {
    std::vector<unsigned int> bytes;
    bytes.reserve(text.size());
    for (const unsigned char byte : text) {
        bytes.push_back(byte);
    }
    return computeZSequence(bytes);
}

std::vector<std::size_t> zSearch(
    const std::string& text,
    const std::string& pattern
) {
    std::vector<std::size_t> positions;
    scanMatches(text, pattern, [&positions](std::size_t position) {
        positions.push_back(position);
    });
    return positions;
}

std::size_t zCount(const std::string& text, const std::string& pattern) {
    std::size_t count = 0;
    scanMatches(text, pattern, [&count](std::size_t) { ++count; });
    return count;
}
