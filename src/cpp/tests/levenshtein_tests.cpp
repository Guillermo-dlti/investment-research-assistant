#include "levenshtein.h"

#include <functional>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void expect(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

FuzzyMatcher sampleMatcher() {
    FuzzyMatcher matcher;
    matcher.addWord("nvidia", 900);
    matcher.addWord("nvda", 120);
    matcher.addWord("revenue", 5000);
    matcher.addWord("revenues", 800);
    matcher.addWord("reverse", 30);
    matcher.addWord("cloud", 400);
    matcher.addWord("could", 700);
    matcher.addWord("amd", 300);
    return matcher;
}

std::vector<std::string> words(const std::vector<FuzzyMatch>& matches) {
    std::vector<std::string> result;
    for (const FuzzyMatch& match : matches) result.push_back(match.word);
    return result;
}

void classic() {
    expect(levenshteinDistance("kitten", "sitting") == 3, "kitten/sitting should be 3");
    expect(levenshteinDistance("flaw", "lawn") == 2, "flaw/lawn should be 2");
    expect(levenshteinDistance("intention", "execution") == 5, "intention/execution should be 5");
}
void identical() { expect(levenshteinDistance("revenue", "revenue") == 0, "identical words differ"); }
void emptyStrings() {
    expect(levenshteinDistance("", "") == 0, "two empty strings should be 0");
    expect(levenshteinDistance("", "amd") == 3, "empty to amd should be 3");
    expect(levenshteinDistance("nvda", "") == 4, "nvda to empty should be 4");
}
void symmetry() {
    expect(
        levenshteinDistance("nvidea", "nvidia") == levenshteinDistance("nvidia", "nvidea"),
        "distance should be symmetric"
    );
}
void singleEdits() {
    expect(levenshteinDistance("revenu", "revenue") == 1, "one insertion");
    expect(levenshteinDistance("revenuee", "revenue") == 1, "one deletion");
    expect(levenshteinDistance("nvidea", "nvidia") == 1, "one substitution");
}
void utf8Bytes() {
    // é is two UTF-8 bytes, so replacing it with e costs two byte edits.
    expect(levenshteinDistance("café", "cafe") == 2, "UTF-8 is compared bytewise");
}
void boundedAgrees() {
    expect(boundedLevenshtein("kitten", "sitting", 3) == 3, "within bound returns exact distance");
    expect(boundedLevenshtein("kitten", "sitting", 2) == 3, "above bound returns bound + 1");
    expect(boundedLevenshtein("a", "abcdef", 2) == 3, "length gap returns bound + 1");
    expect(boundedLevenshtein("", "", 0) == 0, "empty strings within zero bound");
}
void boundedRandomized() {
    std::mt19937 generator(20261019);
    std::uniform_int_distribution<int> letter('a', 'd');
    std::uniform_int_distribution<int> length(0, 9);
    for (int trial = 0; trial < 2000; ++trial) {
        std::string first(length(generator), 'a');
        std::string second(length(generator), 'a');
        for (char& character : first) character = static_cast<char>(letter(generator));
        for (char& character : second) character = static_cast<char>(letter(generator));
        const std::size_t exact = levenshteinDistance(first, second);
        for (std::size_t bound = 0; bound <= 4; ++bound) {
            const std::size_t expected = exact <= bound ? exact : bound + 1;
            expect(boundedLevenshtein(first, second, bound) == expected, "bounded disagrees with full");
        }
    }
}
void defaultCutoff() {
    expect(defaultMaxDistance("amd") == 1, "short words allow 1 edit");
    expect(defaultMaxDistance("nvda") == 1, "4 byte words allow 1 edit");
    expect(defaultMaxDistance("nvidia") == 2, "longer words allow 2 edits");
}
void matcherTypo() {
    const auto matches = sampleMatcher().match("nvidea", 5);
    expect(!matches.empty() && matches[0].word == "nvidia", "nvidea should match nvidia");
    expect(matches[0].distance == 1, "nvidea is one edit from nvidia");
}
void matcherExact() {
    const auto matches = sampleMatcher().match("revenue", 5);
    expect(matches.size() == 1, "an exact hit returns one word");
    expect(matches[0].word == "revenue" && matches[0].distance == 0, "exact hit has distance 0");
    expect(matches[0].frequency == 5000, "exact hit keeps its frequency");
}
void matcherOrdering() {
    // revenu: revenue (1 edit) then revenues (2 edits); reverse is 3 edits away.
    const auto matches = sampleMatcher().match("revenu", 5);
    expect(words(matches) == std::vector<std::string>({"revenue", "revenues"}), "distance then frequency order");
    // coud is 1 edit from both cloud and could; higher frequency (could) first.
    const auto ties = sampleMatcher().match("coud", 5);
    expect(words(ties) == std::vector<std::string>({"could", "cloud"}), "ties break by frequency");
}
void matcherWordTieBreak() {
    FuzzyMatcher matcher;
    matcher.addWord("bat", 10);
    matcher.addWord("cat", 10);
    expect(words(matcher.match("aat", 5)) == std::vector<std::string>({"bat", "cat"}), "equal ties break by word");
}
void matcherLimits() {
    const FuzzyMatcher matcher = sampleMatcher();
    expect(matcher.match("revenu", 1).size() == 1, "limit caps results");
    expect(matcher.match("revenu", 0).empty(), "limit zero returns nothing");
    expect(matcher.match("", 5).empty(), "empty query returns nothing");
    expect(matcher.match("zzzzzzzz", 5).empty(), "far word returns nothing");
}
void matcherCustomBound() {
    const FuzzyMatcher matcher = sampleMatcher();
    expect(matcher.match("nvidxx", 5, 1).empty(), "bound 1 rejects two edits");
    expect(words(matcher.match("nvidxx", 5, 2)) == std::vector<std::string>({"nvidia"}), "bound 2 accepts two edits");
}
void matcherValidation() {
    FuzzyMatcher matcher;
    matcher.addWord("amd", 1);
    expect(matcher.size() == 1, "size counts words");
    bool duplicate_rejected = false;
    try { matcher.addWord("amd", 2); } catch (const std::invalid_argument&) { duplicate_rejected = true; }
    expect(duplicate_rejected, "duplicate words are rejected");
    bool empty_rejected = false;
    try { matcher.addWord("", 2); } catch (const std::invalid_argument&) { empty_rejected = true; }
    expect(empty_rejected, "empty words are rejected");
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::map<std::string, std::function<void()>> tests = {
        {"classic", classic}, {"identical", identical}, {"empty_strings", emptyStrings},
        {"symmetry", symmetry}, {"single_edits", singleEdits}, {"utf8_bytes", utf8Bytes},
        {"bounded_agrees", boundedAgrees}, {"bounded_randomized", boundedRandomized},
        {"default_cutoff", defaultCutoff}, {"matcher_typo", matcherTypo},
        {"matcher_exact", matcherExact}, {"matcher_ordering", matcherOrdering},
        {"matcher_word_tie_break", matcherWordTieBreak}, {"matcher_limits", matcherLimits},
        {"matcher_custom_bound", matcherCustomBound}, {"matcher_validation", matcherValidation},
    };
    if (argc != 2 || tests.find(argv[1]) == tests.end()) {
        std::cerr << "Usage: levenshtein_tests TEST_NAME\n";
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
