#include "ngram_jaccard.h"
#include "preprocessed_collection_loader.h"

#include <chrono>
#include <exception>
#include <iostream>
#include <string>
#include <vector>

namespace {

void printSet(const std::string& label, const NgramSet& grams) {
    std::cout << "  " << label << ":";
    for (const std::string& gram : grams) std::cout << " [" << gram << ']';
    std::cout << '\n';
}

}  // namespace

int main(int argc, char* argv[]) {
    std::cout << "N-grams and Jaccard similarity\n";
    const NgramSet revenue = characterNgrams("revenue", 3);
    const NgramSet revenues = characterNgrams("revenues", 3);
    printSet("revenue trigrams", revenue);
    printSet("revenues trigrams", revenues);
    std::cout << "  Jaccard(revenue, revenues) = " << jaccardSimilarity(revenue, revenues) << '\n';
    printSet("word 1-2 grams of 'data center revenue'", wordNgrams({"data", "center", "revenue"}, 1, 2));

    if (argc != 2) {
        std::cout << "\nPass data/processed/preprocessed_collection.json to rank real chunks.\n";
        return 0;
    }

    try {
        const PreprocessedCollection collection = loadPreprocessedCollection(argv[1]);
        JaccardIndex index;
        for (const PreprocessedChunk& chunk : collection.chunks) {
            index.addChunk(chunk.chunk_id, chunk.tokens);
        }
        std::cout << "\nJaccard ranking over " << index.chunkCount() << " chunks\n";

        const std::vector<std::vector<std::string>> queries = {
            {"data", "center", "revenue"},
            {"artificial", "intelligence", "risks"},
            {"iphone", "net", "sales"},
        };
        for (const auto& query : queries) {
            const auto start = std::chrono::steady_clock::now();
            const auto results = index.rank(query, 3);
            const auto elapsed = std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - start
            ).count();
            std::cout << "  query:";
            for (const std::string& token : query) std::cout << ' ' << token;
            std::cout << " (" << elapsed << " ms)\n";
            for (const JaccardResult& result : results) {
                std::cout << "    " << result.chunk_id << " score=" << result.score
                          << " shared=" << result.shared_ngrams << '/' << result.union_size << '\n';
            }
        }
    } catch (const std::exception& error) {
        std::cerr << "N-gram Jaccard demo failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
