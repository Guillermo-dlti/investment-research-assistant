#include "inverted_index.h"
#include "preprocessed_collection_loader.h"

#include <filesystem>
#include <functional>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void expect(const bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void expectIds(
    const std::vector<std::string>& actual,
    const std::vector<std::string>& expected,
    const std::string& message
) {
    expect(actual == expected, message);
}

InvertedIndex makeIndex() {
    InvertedIndex index;
    index.addChunk(
        "CHUNK_A",
        {"revenue", "revenue", "artificial", "intelligence"},
        {"DOC_1", "AAA", 2024}
    );
    index.addChunk(
        "CHUNK_B",
        {"revenue", "intelligence", "growth"},
        {"DOC_1", "AAA", 2024}
    );
    index.addChunk(
        "CHUNK_C",
        {"artificial", "growth"},
        {"DOC_2", "BBB", 2025}
    );
    return index;
}

void singleTokenLookup() {
    const InvertedIndex index = makeIndex();
    expectIds(
        index.getChunkIds("revenue"),
        {"CHUNK_A", "CHUNK_B"},
        "single-token postings are incorrect"
    );
    expect(index.documentFrequency("revenue") == 2, "document frequency is wrong");
}

void missingTokens() {
    const InvertedIndex index = makeIndex();
    expect(index.getChunkIds("missing").empty(), "missing token should have no postings");
    expect(index.documentFrequency("missing") == 0, "missing token frequency should be zero");
    expect(index.termFrequency("missing", "CHUNK_A") == 0, "missing term TF should be zero");
    expect(index.termFrequency("revenue", "MISSING") == 0, "missing chunk TF should be zero");
}

void repeatedTokens() {
    const InvertedIndex index = makeIndex();
    expect(index.termFrequency("revenue", "CHUNK_A") == 2, "repeated TF should be two");
    expect(index.documentFrequency("revenue") == 2, "postings must not duplicate chunk IDs");
}

void duplicateChunkIds() {
    InvertedIndex index = makeIndex();
    bool rejected = false;
    try {
        index.addChunk("CHUNK_A", {"new"});
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    expect(rejected, "duplicate chunk ID should be rejected");
    expect(index.chunkCount() == 3, "duplicate insertion changed chunk count");
    expect(index.termFrequency("revenue", "CHUNK_A") == 2, "duplicate changed postings");
}

void andIntersection() {
    const InvertedIndex index = makeIndex();
    expectIds(
        index.andQuery({"artificial", "intelligence"}),
        {"CHUNK_A"},
        "AND intersection is incorrect"
    );
    expect(index.andQuery({"revenue", "missing"}).empty(), "absent AND term must empty result");
}

void orUnion() {
    const InvertedIndex index = makeIndex();
    expectIds(
        index.orQuery({"revenue", "artificial"}),
        {"CHUNK_A", "CHUNK_B", "CHUNK_C"},
        "OR union is incorrect"
    );
    expectIds(index.orQuery({"missing", "growth"}), {"CHUNK_B", "CHUNK_C"}, "OR missing-term behavior is wrong");
}

void repeatedQueryTerms() {
    const InvertedIndex index = makeIndex();
    expectIds(
        index.andQuery({"revenue", "revenue"}),
        {"CHUNK_A", "CHUNK_B"},
        "repeated query terms should be deduplicated"
    );
    const auto ranked = index.rankOr({"revenue", "revenue"});
    expect(ranked.size() == 2, "repeated terms changed match count");
    expect(ranked[0].score == 2 && ranked[1].score == 1, "repeated terms changed scores");
}

void emptyQueries() {
    const InvertedIndex index = makeIndex();
    expect(index.andQuery({}).empty(), "empty AND query should be empty");
    expect(index.orQuery({}).empty(), "empty OR query should be empty");
    expect(index.rankAnd({}).empty(), "empty ranked AND query should be empty");
    expect(index.rankOr({}).empty(), "empty ranked OR query should be empty");
}

void deterministicOrdering() {
    InvertedIndex index;
    index.addChunk("CHUNK_Z", {"token"});
    index.addChunk("CHUNK_A", {"token"});
    index.addChunk("CHUNK_M", {"token"});
    expectIds(
        index.getChunkIds("token"),
        {"CHUNK_A", "CHUNK_M", "CHUNK_Z"},
        "postings should be ordered by chunk ID"
    );
    expectIds(
        index.orQuery({"token"}),
        {"CHUNK_A", "CHUNK_M", "CHUNK_Z"},
        "query order should be deterministic"
    );
}

void rankingAndTieBreaking() {
    const InvertedIndex index = makeIndex();
    const auto ranked_or = index.rankOr({"revenue", "growth"});
    expect(ranked_or.size() == 3, "ranked OR should contain three chunks");
    expect(
        ranked_or[0].chunk_id == "CHUNK_A" && ranked_or[0].score == 2,
        "first tied result should use smaller chunk ID"
    );
    expect(
        ranked_or[1].chunk_id == "CHUNK_B" && ranked_or[1].score == 2,
        "second tied result is incorrect"
    );
    expect(
        ranked_or[2].chunk_id == "CHUNK_C" && ranked_or[2].score == 1,
        "lower-scored result is incorrect"
    );
    const auto ranked_and = index.rankAnd({"revenue", "growth"});
    expect(
        ranked_and.size() == 1 && ranked_and[0].chunk_id == "CHUNK_B" &&
        ranked_and[0].score == 2,
        "ranked AND result is incorrect"
    );
}

void chunkAndVocabularyCounts() {
    const InvertedIndex index = makeIndex();
    expect(index.chunkCount() == 3, "chunk count is incorrect");
    expect(index.vocabularySize() == 4, "vocabulary count is incorrect");
    const ChunkMetadata* metadata = index.metadata("CHUNK_C");
    expect(metadata != nullptr, "chunk metadata should be retained");
    expect(metadata->document_id == "DOC_2", "document ID metadata is incorrect");
    expect(metadata->ticker == "BBB", "ticker metadata is incorrect");
    expect(metadata->fiscal_year == 2025, "fiscal year metadata is incorrect");
}

void realCollectionLoading(const std::filesystem::path& path) {
    const PreprocessedCollection collection = loadPreprocessedCollection(path);
    expect(collection.declared_total_chunks == 2458, "real collection should declare 2,458 chunks");
    expect(collection.chunks.size() == 2458, "real collection loader should return 2,458 chunks");

    InvertedIndex index;
    for (const PreprocessedChunk& chunk : collection.chunks) {
        index.addChunk(
            chunk.chunk_id,
            chunk.tokens,
            {chunk.document_id, chunk.ticker, chunk.fiscal_year}
        );
    }
    expect(index.chunkCount() == 2458, "real index should contain 2,458 chunks");
    expect(index.vocabularySize() == 14180, "real index should contain 14,180 tokens");
    expect(!index.getChunkIds("revenue").empty(), "real index should contain revenue");
    expect(index.metadata("NVDA_2024_10K_0001") != nullptr, "real metadata should be available");
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::map<std::string, std::function<void()>> portable_tests = {
        {"single_token_lookup", singleTokenLookup},
        {"missing_tokens", missingTokens},
        {"repeated_tokens", repeatedTokens},
        {"duplicate_chunk_ids", duplicateChunkIds},
        {"and_intersection", andIntersection},
        {"or_union", orUnion},
        {"repeated_query_terms", repeatedQueryTerms},
        {"empty_queries", emptyQueries},
        {"deterministic_ordering", deterministicOrdering},
        {"ranking_and_tie_breaking", rankingAndTieBreaking},
        {"chunk_and_vocabulary_counts", chunkAndVocabularyCounts},
    };

    if (argc < 2) {
        std::cerr << "Usage: inverted_index_tests TEST_NAME [COLLECTION_PATH]\n";
        return 2;
    }
    try {
        const std::string test_name = argv[1];
        const auto portable = portable_tests.find(test_name);
        if (portable != portable_tests.end()) {
            portable->second();
        } else if (test_name == "real_collection_loading" && argc == 3) {
            realCollectionLoading(argv[2]);
        } else {
            std::cerr << "Unknown test or missing collection path: " << test_name << '\n';
            return 2;
        }
        std::cout << "PASS: " << test_name << '\n';
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << argv[1] << ": " << error.what() << '\n';
        return 1;
    }
    return 0;
}
