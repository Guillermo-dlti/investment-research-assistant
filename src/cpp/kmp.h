#ifndef INVESTMENT_RESEARCH_ASSISTANT_KMP_H
#define INVESTMENT_RESEARCH_ASSISTANT_KMP_H

#include <cstddef>
#include <string>
#include <vector>

[[nodiscard]] std::vector<std::size_t> computeLps(const std::string& pattern);
[[nodiscard]] std::vector<std::size_t> kmpSearch(
    const std::string& text,
    const std::string& pattern
);
[[nodiscard]] std::size_t kmpCount(
    const std::string& text,
    const std::string& pattern
);

#endif
