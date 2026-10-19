#include "vocabulary_loader.h"

#include "json_reader.h"

#include <unordered_set>
#include <utility>

namespace {

std::vector<VocabularyEntry> parseEntries(JsonReader& reader) {
    std::vector<VocabularyEntry> entries;
    reader.expect('[');
    while (!reader.consume(']')) {
        VocabularyEntry entry{};
        bool found_token = false;
        bool found_frequency = false;
        reader.expect('{');
        while (!reader.consume('}')) {
            const std::string key = reader.parseString();
            reader.expect(':');
            if (key == "token") {
                entry.token = reader.parseString();
                found_token = true;
            } else if (key == "frequency") {
                entry.frequency = reader.parseUnsigned();
                found_frequency = true;
            } else {
                reader.skipValue();
            }
            if (!reader.consume(',')) {
                reader.expect('}');
                break;
            }
        }
        if (!found_token || !found_frequency || entry.frequency == 0) {
            reader.fail("invalid token-frequency entry");
        }
        entries.push_back(std::move(entry));
        if (!reader.consume(',')) {
            reader.expect(']');
            break;
        }
    }
    return entries;
}

}  // namespace

VocabularyData loadVocabulary(const std::filesystem::path& path) {
    JsonReader reader(readJsonFile(path));
    VocabularyData vocabulary{};
    bool found_unique_tokens = false;
    bool found_entries = false;

    reader.expect('{');
    while (!reader.consume('}')) {
        const std::string key = reader.parseString();
        reader.expect(':');
        if (key == "unique_tokens") {
            vocabulary.declared_unique_tokens = reader.parseUnsigned();
            found_unique_tokens = true;
        } else if (key == "token_frequencies") {
            vocabulary.entries = parseEntries(reader);
            found_entries = true;
        } else {
            reader.skipValue();
        }
        if (!reader.consume(',')) {
            reader.expect('}');
            break;
        }
    }
    reader.finish();

    if (!found_unique_tokens || !found_entries) {
        reader.fail("missing unique_tokens or token_frequencies");
    }
    if (vocabulary.declared_unique_tokens != vocabulary.entries.size()) {
        reader.fail("unique_tokens does not match token_frequencies length");
    }
    std::unordered_set<std::string> seen;
    for (const VocabularyEntry& entry : vocabulary.entries) {
        if (!seen.insert(entry.token).second) {
            reader.fail("duplicate token in token_frequencies: " + entry.token);
        }
    }
    return vocabulary;
}
