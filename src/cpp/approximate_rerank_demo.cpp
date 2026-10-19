#include "approximate_rerank.h"
#include "preprocessed_collection_loader.h"

#include <chrono>
#include <exception>
#include <iostream>
#include <string>
#include <vector>

namespace {

void printResults(const std::vector<ApproximateResult>& results) {
    for (const ApproximateResult& result : results) {
        std::cout << "    " << result.chunk_id << " score=" << result.score
                  << " coverage=" << result.coverage << " jaccard=" << result.jaccard
                  << " scaled=" << result.jaccard_scaled
                  << " matched=" << result.matched_terms << '\n';
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    std::cout << "Approximate reranking: alpha * coverage + (1 - alpha) * J / J_max\n";
    InvertedIndex index;
    JaccardIndex jaccard;
    const std::vector<std::pair<std::string, std::vector<std::string>>> sample = {
        {"C1", {"nvidia", "revenue", "grew"}},
        {"C2", {"amd", "revenue"}},
        {"C3", {"nvidia", "cloud", "chips"}},
    };
    for (const auto& [chunk_id, tokens] : sample) {
        index.addChunk(chunk_id, tokens);
        jaccard.addChunk(chunk_id, tokens);
    }
    std::cout << "  query: nvidia revenue (revenue weighted 0.5 as a correction)\n";
    printResults(rerankCandidates(
        index, jaccard, {"C1", "C2", "C3"}, {{"nvidia", 1.0}, {"revenue", 0.5}},
        {"nvidia", "revenue"}, 0.6
    ));

    if (argc != 2) {
        std::cout << "\nPass data/processed/preprocessed_collection.json to rerank real chunks.\n";
        return 0;
    }

    try {
        const PreprocessedCollection collection = loadPreprocessedCollection(argv[1]);
        InvertedIndex real_index;
        JaccardIndex real_jaccard;
        for (const PreprocessedChunk& chunk : collection.chunks) {
            real_index.addChunk(
                chunk.chunk_id, chunk.tokens,
                {chunk.document_id, chunk.ticker, chunk.fiscal_year}
            );
            real_jaccard.addChunk(chunk.chunk_id, chunk.tokens);
        }
        std::cout << "\nOR candidates reranked over " << real_index.chunkCount() << " chunks\n";

        const std::vector<std::vector<std::string>> queries = {
            {"data", "center", "revenue"},
            {"export", "restrictions", "risks"},
            {"iphone", "net", "sales"},
        };
        for (const auto& query : queries) {
            const auto start = std::chrono::steady_clock::now();
            const std::vector<std::string> candidates = real_index.orQuery(query);
            std::vector<WeightedTerm> terms;
            for (const std::string& token : query) terms.push_back({token, 1.0});
            const auto results =
                rerankCandidates(real_index, real_jaccard, candidates, terms, query, 0.6, 3);
            const auto elapsed = std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - start
            ).count();
            std::cout << "  query:";
            for (const std::string& token : query) std::cout << ' ' << token;
            std::cout << " (" << candidates.size() << " candidates, " << elapsed << " ms)\n";
            printResults(results);
        }
    } catch (const std::exception& error) {
        std::cerr << "Approximate rerank demo failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
