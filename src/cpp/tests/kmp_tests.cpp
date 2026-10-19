#include "kmp.h"

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

void expectPositions(
    const std::string& text,
    const std::string& pattern,
    const std::vector<std::size_t>& expected
) {
    const auto actual = kmpSearch(text, pattern);
    expect(actual == expected, "unexpected match positions");
    expect(kmpCount(text, pattern) == expected.size(), "incorrect match count");
}

void basic() { expectPositions("investment research", "research", {11}); }
void noMatch() { expectPositions("revenue", "profit", {}); }
void multiple() { expectPositions("revenue revenue revenue", "revenue", {0, 8, 16}); }
void overlapping() { expectPositions("aaaaa", "aaa", {0, 1, 2}); }
void beginning() { expectPositions("artificial intelligence", "artificial", {0}); }
void end() { expectPositions("cloud revenue", "revenue", {6}); }
void fullText() { expectPositions("nvidia", "nvidia", {0}); }
void longerPattern() { expectPositions("amd", "competition", {}); }
void emptyPattern() {
    expectPositions("revenue", "", {});
    expect(computeLps("").empty(), "empty pattern LPS should be empty");
}
void emptyText() { expectPositions("", "revenue", {}); }
void repeatedPrefix() { expectPositions("ababababaca", "ababaca", {4}); }
void punctuation() {
    expectPositions("growth was 12.5% and revenue was $97,858", "12.5%", {11});
    expectPositions("growth was 12.5% and revenue was $97,858", "$97,858", {33});
}
void utf8() { expectPositions("café café", "é", {3, 9}); }
void lpsCorrectness() {
    expect(
        computeLps("ABABCABAB") == std::vector<std::size_t>({0, 0, 1, 2, 0, 1, 2, 3, 4}),
        "LPS table is incorrect"
    );
}
void byteOffsets() { expectPositions("éaé", "a", {2}); }

}  // namespace

int main(int argc, char* argv[]) {
    const std::map<std::string, std::function<void()>> tests = {
        {"basic", basic}, {"no_match", noMatch}, {"multiple", multiple},
        {"overlapping", overlapping}, {"beginning", beginning}, {"end", end},
        {"full_text", fullText}, {"longer_pattern", longerPattern},
        {"empty_pattern", emptyPattern}, {"empty_text", emptyText},
        {"repeated_prefix", repeatedPrefix}, {"punctuation", punctuation},
        {"utf8", utf8}, {"lps_correctness", lpsCorrectness},
        {"byte_offsets", byteOffsets},
    };
    if (argc != 2 || tests.find(argv[1]) == tests.end()) {
        std::cerr << "Usage: kmp_tests TEST_NAME\n";
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
