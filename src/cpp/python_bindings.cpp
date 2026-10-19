#include "inverted_index.h"
#include "kmp.h"
#include "levenshtein.h"
#include "ngram_jaccard.h"
#include "preprocessed_collection_loader.h"
#include "trie.h"
#include "vocabulary_loader.h"
#include "z_function.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <memory>
#include <string>
#include <utility>

namespace py = pybind11;

namespace {

std::unique_ptr<Trie> loadTrieFromFile(const std::string& path) {
    const VocabularyData vocabulary = loadVocabulary(path);
    auto trie = std::make_unique<Trie>();
    for (const VocabularyEntry& entry : vocabulary.entries) {
        trie->insert(entry.token);
    }
    return trie;
}

FuzzyMatcher loadFuzzyMatcherFromFile(const std::string& path) {
    const VocabularyData vocabulary = loadVocabulary(path);
    FuzzyMatcher matcher;
    for (const VocabularyEntry& entry : vocabulary.entries) {
        matcher.addWord(entry.token, entry.frequency);
    }
    return matcher;
}

JaccardIndex loadJaccardIndexFromFile(const std::string& path) {
    const PreprocessedCollection collection = loadPreprocessedCollection(path);
    JaccardIndex index;
    for (const PreprocessedChunk& chunk : collection.chunks) {
        index.addChunk(chunk.chunk_id, chunk.tokens);
    }
    return index;
}

InvertedIndex loadIndexFromFile(const std::string& path) {
    const PreprocessedCollection collection = loadPreprocessedCollection(path);
    InvertedIndex index;
    for (const PreprocessedChunk& chunk : collection.chunks) {
        index.addChunk(
            chunk.chunk_id,
            chunk.tokens,
            {chunk.document_id, chunk.ticker, chunk.fiscal_year}
        );
    }
    return index;
}

py::object metadataAsPython(
    const InvertedIndex& index,
    const std::string& chunk_id
) {
    const ChunkMetadata* metadata = index.metadata(chunk_id);
    if (metadata == nullptr) {
        return py::none();
    }
    py::dict result;
    result["document_id"] = metadata->document_id;
    result["ticker"] = metadata->ticker;
    result["fiscal_year"] = metadata->fiscal_year;
    return std::move(result);
}

}  // namespace

PYBIND11_MODULE(investment_engine, module) {
    module.doc() =
        "Python bindings for the C++17 retrieval, exact-matching, and "
        "approximate-matching algorithms.";

    py::class_<Trie>(module, "Trie")
        .def(py::init<>())
        .def("insert", &Trie::insert, py::arg("word"))
        .def("search", &Trie::search, py::arg("word"))
        .def("starts_with", &Trie::startsWith, py::arg("prefix"))
        .def(
            "autocomplete",
            &Trie::autocomplete,
            py::arg("prefix"),
            py::arg("k")
        )
        .def_property_readonly("size", &Trie::size);

    py::class_<RankedChunk>(module, "RankedChunk")
        .def_readonly("chunk_id", &RankedChunk::chunk_id)
        .def_readonly("score", &RankedChunk::score)
        .def("__repr__", [](const RankedChunk& result) {
            return "RankedChunk(chunk_id='" + result.chunk_id +
                   "', score=" + std::to_string(result.score) + ")";
        });

    py::class_<InvertedIndex>(module, "InvertedIndex")
        .def(py::init<>())
        .def(
            "add_chunk",
            [](InvertedIndex& index,
               const std::string& chunk_id,
               const std::vector<std::string>& tokens,
               const std::string& document_id,
               const std::string& ticker,
               const int fiscal_year) {
                index.addChunk(
                    chunk_id,
                    tokens,
                    {document_id, ticker, fiscal_year}
                );
            },
            py::arg("chunk_id"),
            py::arg("tokens"),
            py::arg("document_id") = "",
            py::arg("ticker") = "",
            py::arg("fiscal_year") = 0
        )
        .def("lookup", &InvertedIndex::getChunkIds, py::arg("token"))
        .def("and_query", &InvertedIndex::andQuery, py::arg("tokens"))
        .def("or_query", &InvertedIndex::orQuery, py::arg("tokens"))
        .def(
            "term_frequency",
            &InvertedIndex::termFrequency,
            py::arg("token"),
            py::arg("chunk_id")
        )
        .def(
            "document_frequency",
            &InvertedIndex::documentFrequency,
            py::arg("token")
        )
        .def("ranked_and", &InvertedIndex::rankAnd, py::arg("tokens"))
        .def("ranked_or", &InvertedIndex::rankOr, py::arg("tokens"))
        .def("get_metadata", &metadataAsPython, py::arg("chunk_id"))
        .def_property_readonly("chunk_count", &InvertedIndex::chunkCount)
        .def_property_readonly("vocabulary_size", &InvertedIndex::vocabularySize);

    py::class_<FuzzyMatch>(module, "FuzzyMatch")
        .def_readonly("word", &FuzzyMatch::word)
        .def_readonly("distance", &FuzzyMatch::distance)
        .def_readonly("frequency", &FuzzyMatch::frequency)
        .def("__repr__", [](const FuzzyMatch& match) {
            return "FuzzyMatch(word='" + match.word +
                   "', distance=" + std::to_string(match.distance) +
                   ", frequency=" + std::to_string(match.frequency) + ")";
        });

    py::class_<FuzzyMatcher>(module, "FuzzyMatcher")
        .def(py::init<>())
        .def(
            "add_word",
            &FuzzyMatcher::addWord,
            py::arg("word"),
            py::arg("frequency") = 0
        )
        .def(
            "match",
            &FuzzyMatcher::match,
            py::arg("query"),
            py::arg("limit") = 5,
            py::arg("max_distance") = py::none()
        )
        .def_property_readonly("size", &FuzzyMatcher::size);

    py::class_<JaccardResult>(module, "JaccardResult")
        .def_readonly("chunk_id", &JaccardResult::chunk_id)
        .def_readonly("score", &JaccardResult::score)
        .def_readonly("shared_ngrams", &JaccardResult::shared_ngrams)
        .def_readonly("union_size", &JaccardResult::union_size)
        .def("__repr__", [](const JaccardResult& result) {
            return "JaccardResult(chunk_id='" + result.chunk_id +
                   "', score=" + std::to_string(result.score) +
                   ", shared_ngrams=" + std::to_string(result.shared_ngrams) +
                   ", union_size=" + std::to_string(result.union_size) + ")";
        });

    py::class_<JaccardIndex>(module, "JaccardIndex")
        .def(py::init<std::size_t, std::size_t>(), py::arg("min_n") = 1, py::arg("max_n") = 2)
        .def("add_chunk", &JaccardIndex::addChunk, py::arg("chunk_id"), py::arg("tokens"))
        .def(
            "rank",
            &JaccardIndex::rank,
            py::arg("query_tokens"),
            py::arg("top_k") = py::none()
        )
        .def_property_readonly("chunk_count", &JaccardIndex::chunkCount)
        .def_property_readonly("min_n", &JaccardIndex::minN)
        .def_property_readonly("max_n", &JaccardIndex::maxN);

    module.def(
        "load_trie",
        &loadTrieFromFile,
        py::arg("vocabulary_path"),
        "Load the generated vocabulary and construct the C++ Trie."
    );
    module.def(
        "load_inverted_index",
        &loadIndexFromFile,
        py::arg("collection_path"),
        "Load the preprocessed collection and construct the C++ index."
    );
    module.def(
        "load_fuzzy_matcher",
        &loadFuzzyMatcherFromFile,
        py::arg("vocabulary_path"),
        "Load the generated vocabulary into the C++ Levenshtein fuzzy matcher."
    );
    module.def(
        "levenshtein_distance",
        &levenshteinDistance,
        py::arg("first"),
        py::arg("second"),
        "Unit-cost edit distance between two UTF-8 byte strings."
    );
    module.def(
        "bounded_levenshtein",
        &boundedLevenshtein,
        py::arg("first"),
        py::arg("second"),
        py::arg("max_distance"),
        "Edit distance, or max_distance + 1 once it is known to exceed the bound."
    );
    module.def(
        "default_max_distance",
        &defaultMaxDistance,
        py::arg("word"),
        "Default fuzzy cutoff: 1 edit up to 4 bytes, otherwise 2."
    );
    module.def(
        "load_jaccard_index",
        &loadJaccardIndexFromFile,
        py::arg("collection_path"),
        "Load the preprocessed collection into the C++ word n-gram Jaccard index."
    );
    module.def(
        "character_ngrams",
        &characterNgrams,
        py::arg("text"),
        py::arg("n"),
        "Sorted, unique byte n-grams of text."
    );
    module.def(
        "word_ngrams",
        &wordNgrams,
        py::arg("tokens"),
        py::arg("min_n"),
        py::arg("max_n"),
        "Sorted, unique runs of min_n..max_n tokens joined by spaces."
    );
    module.def(
        "jaccard_similarity",
        &jaccardSimilarity,
        py::arg("first"),
        py::arg("second"),
        "Jaccard similarity of two sorted, unique n-gram sets."
    );
    module.def(
        "compute_lps",
        &computeLps,
        py::arg("pattern"),
        "Build the KMP longest-prefix/suffix table for UTF-8 bytes."
    );
    module.def(
        "kmp_search",
        &kmpSearch,
        py::arg("text"),
        py::arg("pattern"),
        "Return zero-based byte offsets of all KMP matches."
    );
    module.def(
        "kmp_count",
        &kmpCount,
        py::arg("text"),
        py::arg("pattern"),
        "Count all KMP matches without returning their offsets."
    );
    module.def(
        "compute_z",
        &computeZ,
        py::arg("text"),
        "Build the Z-array for UTF-8 bytes with Z[0] equal to zero."
    );
    module.def(
        "z_search",
        &zSearch,
        py::arg("text"),
        py::arg("pattern"),
        "Return zero-based byte offsets of all Z-function matches."
    );
    module.def(
        "z_count",
        &zCount,
        py::arg("text"),
        py::arg("pattern"),
        "Count all Z-function matches without returning their offsets."
    );
}
