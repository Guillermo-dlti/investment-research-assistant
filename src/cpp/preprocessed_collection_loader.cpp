#include "preprocessed_collection_loader.h"

#include "json_reader.h"

#include <limits>
#include <unordered_set>
#include <utility>

namespace {

std::vector<std::string> parseTokens(JsonReader& reader) {
    std::vector<std::string> tokens;
    reader.expect('[');
    while (!reader.consume(']')) {
        tokens.push_back(reader.parseString());
        if (!reader.consume(',')) {
            reader.expect(']');
            break;
        }
    }
    return tokens;
}

PreprocessedChunk parseChunk(JsonReader& reader) {
    PreprocessedChunk chunk{};
    bool found_chunk_id = false;
    bool found_document_id = false;
    bool found_ticker = false;
    bool found_fiscal_year = false;
    bool found_normalized_text = false;
    bool found_tokens = false;
    bool found_token_count = false;
    std::size_t token_count = 0;

    reader.expect('{');
    while (!reader.consume('}')) {
        const std::string key = reader.parseString();
        reader.expect(':');
        if (key == "chunk_id") {
            chunk.chunk_id = reader.parseString();
            found_chunk_id = true;
        } else if (key == "document_id") {
            chunk.document_id = reader.parseString();
            found_document_id = true;
        } else if (key == "ticker") {
            chunk.ticker = reader.parseString();
            found_ticker = true;
        } else if (key == "fiscal_year") {
            const std::size_t year = reader.parseUnsigned();
            if (year > static_cast<std::size_t>(std::numeric_limits<int>::max())) {
                reader.fail("fiscal_year is too large");
            }
            chunk.fiscal_year = static_cast<int>(year);
            found_fiscal_year = true;
        } else if (key == "normalized_text") {
            chunk.normalized_text = reader.parseString();
            found_normalized_text = true;
        } else if (key == "tokens") {
            chunk.tokens = parseTokens(reader);
            found_tokens = true;
        } else if (key == "token_count") {
            token_count = reader.parseUnsigned();
            found_token_count = true;
        } else {
            reader.skipValue();
        }
        if (!reader.consume(',')) {
            reader.expect('}');
            break;
        }
    }

    if (!found_chunk_id || !found_document_id || !found_ticker ||
        !found_fiscal_year || !found_normalized_text || !found_tokens) {
        reader.fail("chunk is missing required index metadata");
    }
    if (chunk.chunk_id.empty() || chunk.document_id.empty() ||
        chunk.ticker.empty() || chunk.normalized_text.empty()) {
        reader.fail("chunk contains empty required metadata");
    }
    if (found_token_count && token_count != chunk.tokens.size()) {
        reader.fail("chunk token_count does not match tokens length");
    }
    return chunk;
}

std::vector<PreprocessedChunk> parseChunks(JsonReader& reader) {
    std::vector<PreprocessedChunk> chunks;
    reader.expect('[');
    while (!reader.consume(']')) {
        chunks.push_back(parseChunk(reader));
        if (!reader.consume(',')) {
            reader.expect(']');
            break;
        }
    }
    return chunks;
}

}  // namespace

PreprocessedCollection loadPreprocessedCollection(
    const std::filesystem::path& path
) {
    JsonReader reader(readJsonFile(path));
    PreprocessedCollection collection{};
    bool found_total_chunks = false;
    bool found_chunks = false;

    reader.expect('{');
    while (!reader.consume('}')) {
        const std::string key = reader.parseString();
        reader.expect(':');
        if (key == "total_chunks") {
            collection.declared_total_chunks = reader.parseUnsigned();
            found_total_chunks = true;
        } else if (key == "chunks") {
            collection.chunks = parseChunks(reader);
            found_chunks = true;
        } else {
            reader.skipValue();
        }
        if (!reader.consume(',')) {
            reader.expect('}');
            break;
        }
    }
    reader.finish();

    if (!found_total_chunks || !found_chunks || collection.chunks.empty()) {
        reader.fail("missing or empty total_chunks/chunks collection data");
    }
    if (collection.declared_total_chunks != collection.chunks.size()) {
        reader.fail("total_chunks does not match chunks length");
    }
    std::unordered_set<std::string> seen;
    for (const PreprocessedChunk& chunk : collection.chunks) {
        if (!seen.insert(chunk.chunk_id).second) {
            reader.fail("duplicate chunk_id in collection: " + chunk.chunk_id);
        }
    }
    return collection;
}
