#include "inverted_index.h"
#include "preprocessed_collection_loader.h"
#include "trie.h"
#include "vocabulary_loader.h"

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
        "Python bindings for the C++17 Trie and chunk-level inverted index.";

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
}
