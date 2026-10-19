#include "inverted_index.h"
#include "preprocessed_collection_loader.h"

#include <algorithm>
#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

namespace {

void showIds(
    const std::string& label,
    const std::vector<std::string>& chunk_ids,
    const std::size_t limit = 5
) {
    std::cout << label << " (" << chunk_ids.size() << " matches):";
    for (std::size_t index = 0; index < std::min(limit, chunk_ids.size()); ++index) {
        std::cout << ' ' << chunk_ids[index];
    }
    if (chunk_ids.size() > limit) {
        std::cout << " ...";
    }
    if (chunk_ids.empty()) {
        std::cout << " <no matches>";
    }
    std::cout << '\n';
}

void showRanking(
    const InvertedIndex& index,
    const std::string& label,
    const std::vector<RankedChunk>& ranked,
    const std::size_t limit = 5
) {
    std::cout << label << " (top " << std::min(limit, ranked.size()) << "):\n";
    for (std::size_t position = 0;
         position < std::min(limit, ranked.size()); ++position) {
        const RankedChunk& result = ranked[position];
        const ChunkMetadata* metadata = index.metadata(result.chunk_id);
        std::cout << "  " << position + 1 << ". " << result.chunk_id
                  << " score=" << result.score;
        if (metadata != nullptr) {
            std::cout << " ticker=" << metadata->ticker
                      << " fiscal_year=" << metadata->fiscal_year
                      << " document_id=" << metadata->document_id;
        }
        std::cout << '\n';
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::filesystem::path collection_path =
        argc > 1 ? argv[1] : "data/processed/preprocessed_collection.json";

    try {
        const PreprocessedCollection collection =
            loadPreprocessedCollection(collection_path);
        InvertedIndex index;
        for (const PreprocessedChunk& chunk : collection.chunks) {
            index.addChunk(
                chunk.chunk_id,
                chunk.tokens,
                {chunk.document_id, chunk.ticker, chunk.fiscal_year}
            );
        }

        std::cout << "Collection: " << collection_path << '\n';
        std::cout << "Indexed chunks: " << index.chunkCount() << '\n';
        std::cout << "Indexed unique tokens: " << index.vocabularySize() << "\n\n";

        showIds("lookup revenue", index.getChunkIds("revenue"));
        std::cout << "document frequency revenue: "
                  << index.documentFrequency("revenue") << "\n\n";

        const std::vector<std::string> and_terms = {"artificial", "intelligence"};
        const std::vector<std::string> or_terms = {"nvidia", "amd"};
        showIds("artificial AND intelligence", index.andQuery(and_terms));
        showIds("nvidia OR amd", index.orQuery(or_terms));
        std::cout << '\n';

        showRanking(
            index,
            "Ranked artificial AND intelligence",
            index.rankAnd(and_terms)
        );
        std::cout << '\n';
        showRanking(index, "Ranked nvidia OR amd", index.rankOr(or_terms));
    } catch (const std::exception& error) {
        std::cerr << "Inverted-index demonstration failed: "
                  << error.what() << '\n';
        return 1;
    }
    return 0;
}
