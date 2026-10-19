#ifndef INVESTMENT_RESEARCH_ASSISTANT_Z_FUNCTION_H
#define INVESTMENT_RESEARCH_ASSISTANT_Z_FUNCTION_H

#include <cstddef>
#include <string>
#include <vector>

// Returns the bytewise Z-array for text. The first entry is always zero.
// Empty input returns an empty array.
[[nodiscard]] std::vector<std::size_t> computeZ(const std::string& text);

// Returns ascending, zero-based byte offsets for all exact matches, including
// overlaps. Empty patterns, empty text, and patterns longer than text produce
// no matches. Input is not normalized or interpreted as Unicode code points.
[[nodiscard]] std::vector<std::size_t> zSearch(
    const std::string& text,
    const std::string& pattern
);

// Applies the same matching policy as zSearch without storing match offsets.
[[nodiscard]] std::size_t zCount(
    const std::string& text,
    const std::string& pattern
);

#endif
