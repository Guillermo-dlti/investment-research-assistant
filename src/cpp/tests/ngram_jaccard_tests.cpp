#include "ngram_jaccard.h"

#include <cmath>
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

JaccardIndex sampleIndex() {
    JaccardIndex index;
    index.addChunk("C1", {"nvidia", "revenue", "grew"});
    index.addChunk("C2", {"amd", "revenue"});
    index.addChunk("C3", {"cloud"});
    return index;
}

std::vector<std::string> ids(const std::vector<JaccardResult>& results) {
    std::vector<std::string> result;
    for (const JaccardResult& item : results) result.push_back(item.chunk_id);
    return result;
}

void characterGrams() {
    expect(characterNgrams("banana", 3) == NgramSet({"ana", "ban", "nan"}), "banana trigrams");
    expect(characterNgrams("abc", 1) == NgramSet({"a", "b", "c"}), "unigrams");
}
void characterShortAndEmpty() {
    expect(characterNgrams("ab", 3) == NgramSet({"ab"}), "short text yields itself");
    expect(characterNgrams("", 3).empty(), "empty text yields nothing");
    expect(throwsInvalidArgument([] { (void)characterNgrams("abc", 0); }), "n = 0 is rejected");
}
void characterUtf8Bytes() {
    // é is two bytes, so "é" has one 2-gram made of both bytes.
    expect(characterNgrams("é", 2) == NgramSet({"é"}), "UTF-8 is handled as bytes");
}
void wordGrams() {
    expect(
        wordNgrams({"ai", "chip", "ai", "chip"}, 1, 2) ==
            NgramSet({"ai", "ai chip", "chip", "chip ai"}),
        "word 1 and 2 grams are sorted and deduplicated"
    );
    expect(wordNgrams({"cloud"}, 2, 2).empty(), "too few tokens yields nothing");
    expect(wordNgrams({}, 1, 2).empty(), "no tokens yields nothing");
}
void wordRangeValidation() {
    expect(throwsInvalidArgument([] { (void)wordNgrams({"a"}, 0, 1); }), "min_n = 0 rejected");
    expect(throwsInvalidArgument([] { (void)wordNgrams({"a"}, 3, 2); }), "min_n > max_n rejected");
    expect(throwsInvalidArgument([] { JaccardIndex bad(2, 1); }), "index range validated");
}
void jaccardValues() {
    expect(near(jaccardSimilarity({"a", "b"}, {"a", "b"}), 1.0), "identical sets score 1");
    expect(near(jaccardSimilarity({"a"}, {"b"}), 0.0), "disjoint sets score 0");
    expect(near(jaccardSimilarity({"a", "b", "c"}, {"b", "c", "d"}), 0.5), "2 shared of 4 is 0.5");
    expect(near(jaccardSimilarity({}, {}), 0.0), "two empty sets score 0");
    expect(near(jaccardSimilarity({}, {"a"}), 0.0), "one empty set scores 0");
}
void jaccardSymmetry() {
    const NgramSet first = characterNgrams("revenue", 3);
    const NgramSet second = characterNgrams("revenues", 3);
    expect(near(jaccardSimilarity(first, second), jaccardSimilarity(second, first)), "symmetric");
    expect(near(jaccardSimilarity(first, second), 5.0 / 6.0), "revenue vs revenues trigrams");
}
void indexRanking() {
    const auto results = sampleIndex().rank({"nvidia", "revenue"});
    expect(ids(results) == std::vector<std::string>({"C1", "C2"}), "ranked by score, zero omitted");
    expect(results[0].shared_ngrams == 3 && results[0].union_size == 5, "C1 shares 3 of 5");
    expect(near(results[0].score, 0.6), "C1 scores 0.6");
    expect(near(results[1].score, 0.2), "C2 scores 0.2");
}
void indexTieBreak() {
    JaccardIndex index;
    index.addChunk("B", {"revenue", "growth"});
    index.addChunk("A", {"revenue", "growth"});
    expect(ids(index.rank({"revenue"})) == std::vector<std::string>({"A", "B"}), "ties by chunk_id");
}
void indexLimits() {
    const JaccardIndex index = sampleIndex();
    expect(index.rank({"nvidia", "revenue"}, 1).size() == 1, "top_k caps results");
    expect(index.rank({"nvidia", "revenue"}, 0).empty(), "top_k zero returns nothing");
    expect(index.rank({}).empty(), "empty query returns nothing");
    expect(index.rank({"missing"}).empty(), "no overlap returns nothing");
}
void indexValidation() {
    JaccardIndex index;
    index.addChunk("C1", {"a"});
    expect(index.chunkCount() == 1, "chunk count");
    expect(index.minN() == 1 && index.maxN() == 2, "default word 1 and 2 grams");
    expect(throwsInvalidArgument([&index] { index.addChunk("C1", {"b"}); }), "duplicate ID rejected");
}

void indexScoreChunks() {
    const JaccardIndex index = sampleIndex();
    const auto results = index.scoreChunks({"C3", "C1", "C2"}, {"nvidia", "revenue"});
    expect(ids(results) == std::vector<std::string>({"C3", "C1", "C2"}), "input order kept");
    expect(near(results[0].score, 0.0) && results[0].shared_ngrams == 0, "no overlap kept at 0");
    expect(results[1].shared_ngrams == 3 && results[1].union_size == 5, "C1 shares 3 of 5");
    expect(near(results[2].score, 0.2), "C2 scores 0.2, as in rank");
    expect(index.scoreChunks({}, {"nvidia"}).empty(), "no IDs gives nothing");
    expect(near(index.scoreChunks({"C1"}, {})[0].score, 0.0), "empty query scores 0");
}
void indexScoreChunksUnknown() {
    const JaccardIndex index = sampleIndex();
    expect(throwsInvalidArgument([&index] { (void)index.scoreChunks({"C9"}, {"a"}); }), "unknown ID rejected");
}

void indexChunkSimilarity() {
    JaccardIndex index = sampleIndex();
    index.addChunk("C4", {"nvidia", "revenue", "grew"});
    // C1 = {nvidia, revenue, grew, nvidia revenue, revenue grew};
    // C2 = {amd, revenue, amd revenue}; they share only "revenue": 1 / 7.
    expect(std::fabs(index.chunkSimilarity("C1", "C2") - 1.0 / 7.0) < 1e-12, "partial overlap");
    expect(index.chunkSimilarity("C1", "C4") == 1.0, "identical text");
    expect(index.chunkSimilarity("C1", "C3") == 0.0, "disjoint");
    expect(index.chunkSimilarity("C2", "C1") == index.chunkSimilarity("C1", "C2"), "symmetric");
    expect(index.hasChunk("C1") && !index.hasChunk("C9"), "has chunk");
    expect(throwsInvalidArgument([&index] { (void)index.chunkSimilarity("C1", "C9"); }), "unknown ID rejected");
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::map<std::string, std::function<void()>> tests = {
        {"character_grams", characterGrams}, {"character_short_and_empty", characterShortAndEmpty},
        {"character_utf8_bytes", characterUtf8Bytes}, {"word_grams", wordGrams},
        {"word_range_validation", wordRangeValidation}, {"jaccard_values", jaccardValues},
        {"jaccard_symmetry", jaccardSymmetry}, {"index_ranking", indexRanking},
        {"index_tie_break", indexTieBreak}, {"index_limits", indexLimits},
        {"index_validation", indexValidation}, {"index_score_chunks", indexScoreChunks},
        {"index_score_chunks_unknown", indexScoreChunksUnknown},
        {"index_chunk_similarity", indexChunkSimilarity},
    };
    if (argc != 2 || tests.find(argv[1]) == tests.end()) {
        std::cerr << "Usage: ngram_jaccard_tests TEST_NAME\n";
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
