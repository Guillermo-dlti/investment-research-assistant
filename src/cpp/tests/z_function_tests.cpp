#include "kmp.h"
#include "z_function.h"

#include <functional>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void expect(bool value, const std::string& message) {
    if (!value) {
        throw std::runtime_error(message);
    }
}

void matches(
    const std::string& text,
    const std::string& pattern,
    const std::vector<std::size_t>& expected
) {
    expect(zSearch(text, pattern) == expected, "incorrect positions");
    expect(zCount(text, pattern) == expected.size(), "incorrect count");
}
void basicZ() {
    expect(
        computeZ("abacaba") == std::vector<std::size_t>({0, 0, 1, 0, 3, 0, 1}),
        "basic Z array"
    );
}
void repeatedZ() {
    expect(
        computeZ("aaaaa") == std::vector<std::size_t>({0, 4, 3, 2, 1}),
        "repeated Z array"
    );
}
void emptyZ() { expect(computeZ("").empty(), "empty Z array"); }
void basic() { matches("investment research", "research", {11}); }
void noMatch() { matches("revenue", "profit", {}); }
void multiple() { matches("revenue revenue revenue", "revenue", {0, 8, 16}); }
void overlapping() { matches("aaaaa", "aaa", {0, 1, 2}); }
void boundaries() { matches("revenue and revenue", "revenue", {0, 12}); }
void fullText() { matches("nvidia", "nvidia", {0}); }
void longer() { matches("amd", "competition", {}); }
void emptyInputs() {
    matches("revenue", "", {});
    matches("", "revenue", {});
    matches("", "", {});
}
void punctuation() { matches("growth 12.5% and $97,858", "$97,858", {17}); }
void utf8() { matches("café café", "é", {3, 9}); }
void embeddedNull() {
    const std::string text("a\0b\0a\0b", 7);
    const std::string pattern("a\0b", 3);
    matches(text, pattern, {0, 4});
}
void separatorSafety() {
    std::string text = "#$";
    text.push_back('\0');
    text.push_back(static_cast<char>(255));
    text += "#$";
    std::string pattern;
    pattern.push_back('\0');
    pattern.push_back(static_cast<char>(255));
    matches(text, pattern, {2});
}
void randomized() {
    std::mt19937 generator(20261019);
    std::uniform_int_distribution<int> length(0, 24);
    std::uniform_int_distribution<int> byte(0, 255);
    for (int trial = 0; trial < 500; ++trial) {
        std::string text(length(generator), '\0');
        std::string pattern(length(generator) % 9, '\0');
        for (char& value : text) value = static_cast<char>(byte(generator));
        for (char& value : pattern) value = static_cast<char>(byte(generator));
        expect(
            zSearch(text, pattern) == kmpSearch(text, pattern),
            "randomized KMP disagreement"
        );
        expect(
            zCount(text, pattern) == kmpCount(text, pattern),
            "randomized count disagreement"
        );
    }
}
void deterministic() {
    const auto first = zSearch("abababab", "abab");
    expect(first == zSearch("abababab", "abab"), "output is not deterministic");
}
}

int main(int argc, char* argv[]) {
    const std::map<std::string, std::function<void()>> tests = {
        {"basic_z", basicZ}, {"repeated_z", repeatedZ}, {"empty_z", emptyZ},
        {"basic", basic}, {"no_match", noMatch}, {"multiple", multiple},
        {"overlapping", overlapping}, {"boundaries", boundaries},
        {"full_text", fullText}, {"longer", longer}, {"empty_inputs", emptyInputs},
        {"punctuation", punctuation}, {"utf8", utf8}, {"embedded_null", embeddedNull},
        {"separator_safety", separatorSafety}, {"randomized", randomized},
        {"deterministic", deterministic},
    };
    if (argc != 2 || tests.find(argv[1]) == tests.end()) {
        std::cerr << "Usage: z_function_tests TEST_NAME\n";
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
