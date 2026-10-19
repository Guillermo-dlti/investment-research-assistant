#include "kmp.h"
#include "preprocessed_collection_loader.h"
#include "z_function.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
using SearchFunction = std::vector<std::size_t> (*)(
    const std::string&,
    const std::string&
);

volatile std::size_t benchmark_sink = 0;

struct BenchmarkCase {
    std::string name;
    std::string group;
    std::string description;
    std::vector<std::string> fragments;
    std::string pattern;
    std::size_t repetitions;
};

struct Statistics {
    double median_us;
    double mean_us;
    double min_us;
    double max_us;
};

struct Result {
    std::string algorithm;
    const BenchmarkCase* benchmark;
    std::size_t total_bytes;
    std::size_t match_count;
    Statistics timing;
};

std::string joinNormalizedText(const PreprocessedCollection& collection) {
    std::string text;
    std::size_t bytes = collection.chunks.empty()
        ? 0
        : collection.chunks.size() - 1;
    for (const PreprocessedChunk& chunk : collection.chunks) {
        bytes += chunk.normalized_text.size();
    }
    text.reserve(bytes);
    for (const PreprocessedChunk& chunk : collection.chunks) {
        if (!text.empty()) {
            text.push_back('\n');
        }
        text += chunk.normalized_text;
    }
    return text;
}

std::string utf8Prefix(const std::string& text, const std::size_t target_bytes) {
    std::size_t size = std::min(target_bytes, text.size());
    while (size > 0 && size < text.size() &&
           (static_cast<unsigned char>(text[size]) & 0xC0U) == 0x80U) {
        --size;
    }
    return text.substr(0, size);
}

std::size_t totalBytes(const BenchmarkCase& benchmark) {
    std::size_t total = 0;
    for (const std::string& fragment : benchmark.fragments) {
        total += fragment.size();
    }
    return total;
}

std::size_t verifyEquivalent(const BenchmarkCase& benchmark) {
    std::size_t matches = 0;
    for (const std::string& fragment : benchmark.fragments) {
        const auto kmp_positions = kmpSearch(fragment, benchmark.pattern);
        const auto z_positions = zSearch(fragment, benchmark.pattern);
        if (kmp_positions != z_positions) {
            throw std::runtime_error(
                "KMP/Z mismatch in benchmark case: " + benchmark.name
            );
        }
        matches += kmp_positions.size();
    }
    return matches;
}

double timeSearch(
    const BenchmarkCase& benchmark,
    const SearchFunction search
) {
    std::size_t checksum = 0;
    std::size_t matches = 0;
    const auto start = Clock::now();
    for (const std::string& fragment : benchmark.fragments) {
        const auto positions = search(fragment, benchmark.pattern);
        matches += positions.size();
        if (!positions.empty()) {
            checksum += positions.front() + positions.back();
        }
    }
    const auto finish = Clock::now();
    benchmark_sink = benchmark_sink ^ (checksum + matches);
    return std::chrono::duration<double, std::micro>(finish - start).count();
}

Statistics summarize(std::vector<double> samples) {
    if (samples.empty()) {
        throw std::runtime_error("cannot summarize empty benchmark samples");
    }
    std::sort(samples.begin(), samples.end());
    const std::size_t middle = samples.size() / 2;
    const double median = samples.size() % 2 == 0
        ? (samples[middle - 1] + samples[middle]) / 2.0
        : samples[middle];
    const double mean = std::accumulate(samples.begin(), samples.end(), 0.0) /
        static_cast<double>(samples.size());
    return {median, mean, samples.front(), samples.back()};
}

std::pair<Statistics, Statistics> measure(const BenchmarkCase& benchmark) {
    constexpr std::size_t warmups = 3;
    for (std::size_t index = 0; index < warmups; ++index) {
        if (index % 2 == 0) {
            static_cast<void>(timeSearch(benchmark, &kmpSearch));
            static_cast<void>(timeSearch(benchmark, &zSearch));
        } else {
            static_cast<void>(timeSearch(benchmark, &zSearch));
            static_cast<void>(timeSearch(benchmark, &kmpSearch));
        }
    }

    std::vector<double> kmp_samples;
    std::vector<double> z_samples;
    kmp_samples.reserve(benchmark.repetitions);
    z_samples.reserve(benchmark.repetitions);
    for (std::size_t index = 0; index < benchmark.repetitions; ++index) {
        if (index % 2 == 0) {
            kmp_samples.push_back(timeSearch(benchmark, &kmpSearch));
            z_samples.push_back(timeSearch(benchmark, &zSearch));
        } else {
            z_samples.push_back(timeSearch(benchmark, &zSearch));
            kmp_samples.push_back(timeSearch(benchmark, &kmpSearch));
        }
    }
    return {summarize(std::move(kmp_samples)), summarize(std::move(z_samples))};
}

std::string jsonEscape(const std::string& value) {
    std::string escaped;
    for (const unsigned char byte : value) {
        switch (byte) {
            case '"': escaped += "\\\""; break;
            case '\\': escaped += "\\\\"; break;
            case '\n': escaped += "\\n"; break;
            case '\r': escaped += "\\r"; break;
            case '\t': escaped += "\\t"; break;
            default: escaped.push_back(static_cast<char>(byte)); break;
        }
    }
    return escaped;
}

std::string csvEscape(const std::string& value) {
    std::string escaped = "\"";
    for (const char character : value) {
        if (character == '"') {
            escaped += "\"\"";
        } else {
            escaped.push_back(character);
        }
    }
    return escaped + '"';
}

std::string compilerDescription() {
#if defined(__clang__)
    return std::string("Clang ") + __clang_version__;
#elif defined(__GNUC__)
    return std::string("GCC ") + __VERSION__;
#else
    return "unknown compiler";
#endif
}

std::string platformDescription() {
#if defined(__APPLE__)
    return "macOS";
#elif defined(__linux__)
    return "Linux";
#elif defined(_WIN32)
    return "Windows";
#else
    return "unknown platform";
#endif
}

std::string timestampUtc() {
    const std::time_t now = std::time(nullptr);
    std::tm utc{};
#if defined(_WIN32)
    gmtime_s(&utc, &now);
#else
    gmtime_r(&now, &utc);
#endif
    std::ostringstream output;
    output << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
    return output.str();
}

std::vector<BenchmarkCase> makeCases(
    const PreprocessedCollection& collection
) {
    const std::string financial_text = joinNormalizedText(collection);
    std::vector<BenchmarkCase> cases;
    const std::vector<std::pair<std::size_t, std::size_t>> sizes = {
        {1U * 1024U, 301},
        {10U * 1024U, 201},
        {50U * 1024U, 101},
        {100U * 1024U, 61},
        {250U * 1024U, 31},
    };
    for (const auto& [bytes, repetitions] : sizes) {
        cases.push_back({
            "financial_prefix_" + std::to_string(bytes / 1024U) + "kb",
            "text_size",
            "Single normalized financial-text prefix",
            {utf8Prefix(financial_text, bytes)},
            "revenue",
            repetitions,
        });
    }

    const std::string pattern_text = utf8Prefix(financial_text, 250U * 1024U);
    for (const std::string& pattern : {
             std::string("ai"),
             std::string("revenue"),
             std::string("artificial intelligence"),
             std::string("artificial intelligence and machine learning"),
         }) {
        cases.push_back({
            "pattern_length_" + std::to_string(pattern.size()) + "b",
            "pattern_length",
            "Single 250 KiB normalized financial-text prefix",
            {pattern_text},
            pattern,
            31,
        });
    }

    const std::string distribution_text = utf8Prefix(financial_text, 100U * 1024U);
    cases.push_back({
        "distribution_no_match",
        "match_distribution",
        "No-match normalized financial-text scan",
        {distribution_text},
        "benchmark-pattern-not-present-7f3a",
        61,
    });
    std::string one_match = distribution_text;
    const std::string marker = "unique-exact-benchmark-marker";
    one_match.insert(one_match.size() / 2, marker);
    cases.push_back({
        "distribution_one_match",
        "match_distribution",
        "Normalized financial text with one inserted marker",
        {std::move(one_match)},
        marker,
        61,
    });
    cases.push_back({
        "distribution_multiple_matches",
        "match_distribution",
        "Multiple matches in normalized financial text",
        {distribution_text},
        "revenue",
        61,
    });
    cases.push_back({
        "distribution_overlapping",
        "match_distribution",
        "Highly repetitive synthetic text with overlapping matches",
        {std::string(100U * 1024U, 'a')},
        "aaaaa",
        15,
    });

    std::vector<std::string> real_fragments;
    real_fragments.reserve(collection.chunks.size());
    for (const PreprocessedChunk& chunk : collection.chunks) {
        real_fragments.push_back(chunk.normalized_text);
    }
    for (const std::string& pattern : {
             std::string("ai"),
             std::string("revenue"),
             std::string("artificial intelligence"),
             std::string("artificial intelligence and machine learning"),
         }) {
        cases.push_back({
            "real_collection_" + std::to_string(pattern.size()) + "b",
            "real_collection",
            "Full collection scanned as 2,458 separate normalized chunks",
            real_fragments,
            pattern,
            11,
        });
    }
    return cases;
}

void writeCsv(
    const std::filesystem::path& path,
    const std::vector<Result>& results,
    const std::string& timestamp
) {
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error("could not write benchmark CSV: " + path.string());
    }
    output << "timestamp_utc,algorithm,scenario_group,scenario,description,"
              "fragment_count,text_bytes,pattern,pattern_bytes,match_count,"
              "repetitions,median_us,mean_us,min_us,max_us,timing_unit,"
              "compiler,build_type,platform\n";
    output << std::fixed << std::setprecision(3);
    for (const Result& result : results) {
        const BenchmarkCase& benchmark = *result.benchmark;
        output << csvEscape(timestamp) << ','
               << csvEscape(result.algorithm) << ','
               << csvEscape(benchmark.group) << ','
               << csvEscape(benchmark.name) << ','
               << csvEscape(benchmark.description) << ','
               << benchmark.fragments.size() << ','
               << result.total_bytes << ','
               << csvEscape(benchmark.pattern) << ','
               << benchmark.pattern.size() << ','
               << result.match_count << ','
               << benchmark.repetitions << ','
               << result.timing.median_us << ','
               << result.timing.mean_us << ','
               << result.timing.min_us << ','
               << result.timing.max_us << ','
               << csvEscape("microseconds") << ','
               << csvEscape(compilerDescription()) << ','
               << csvEscape(BENCHMARK_BUILD_TYPE) << ','
               << csvEscape(platformDescription()) << '\n';
    }
}

void writeSummary(
    const std::filesystem::path& path,
    const std::vector<Result>& results,
    const std::string& timestamp,
    const std::filesystem::path& collection_path
) {
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error("could not write benchmark JSON: " + path.string());
    }
    output << std::fixed << std::setprecision(3);
    output << "{\n"
           << "  \"benchmark_version\": 1,\n"
           << "  \"timestamp_utc\": \"" << jsonEscape(timestamp) << "\",\n"
           << "  \"timer\": \"std::chrono::steady_clock\",\n"
           << "  \"timing_unit\": \"microseconds\",\n"
           << "  \"warmup_repetitions\": 3,\n"
           << "  \"algorithm_order\": \"alternating per repetition\",\n"
           << "  \"collection_path\": \""
           << jsonEscape(collection_path.string()) << "\",\n"
           << "  \"compiler\": \"" << jsonEscape(compilerDescription()) << "\",\n"
           << "  \"build_type\": \"" << jsonEscape(BENCHMARK_BUILD_TYPE) << "\",\n"
           << "  \"platform\": \"" << platformDescription() << "\",\n"
           << "  \"results\": [\n";
    for (std::size_t index = 0; index < results.size(); ++index) {
        const Result& result = results[index];
        const BenchmarkCase& benchmark = *result.benchmark;
        output << "    {\"algorithm\": \"" << result.algorithm
               << "\", \"scenario_group\": \"" << benchmark.group
               << "\", \"scenario\": \"" << benchmark.name
               << "\", \"fragment_count\": " << benchmark.fragments.size()
               << ", \"text_bytes\": " << result.total_bytes
               << ", \"pattern\": \"" << jsonEscape(benchmark.pattern)
               << "\", \"pattern_bytes\": " << benchmark.pattern.size()
               << ", \"match_count\": " << result.match_count
               << ", \"repetitions\": " << benchmark.repetitions
               << ", \"median_us\": " << result.timing.median_us
               << ", \"mean_us\": " << result.timing.mean_us
               << ", \"min_us\": " << result.timing.min_us
               << ", \"max_us\": " << result.timing.max_us << '}';
        output << (index + 1 == results.size() ? "\n" : ",\n");
    }
    output << "  ]\n}\n";
}

}  // namespace

int main(int argc, char* argv[]) {
    const std::filesystem::path collection_path = argc > 1
        ? argv[1]
        : "data/processed/preprocessed_collection.json";
    const std::filesystem::path csv_path = argc > 2
        ? argv[2]
        : "reports/benchmarks/exact_matching_results.csv";
    const std::filesystem::path summary_path = argc > 3
        ? argv[3]
        : "reports/benchmarks/exact_matching_summary.json";
    try {
        const PreprocessedCollection collection =
            loadPreprocessedCollection(collection_path);
        std::vector<BenchmarkCase> cases = makeCases(collection);
        std::vector<Result> results;
        results.reserve(cases.size() * 2);
        std::cout << std::fixed << std::setprecision(3);
        for (const BenchmarkCase& benchmark : cases) {
            const std::size_t match_count = verifyEquivalent(benchmark);
            const auto [kmp_timing, z_timing] = measure(benchmark);
            const std::size_t bytes = totalBytes(benchmark);
            results.push_back({"KMP", &benchmark, bytes, match_count, kmp_timing});
            results.push_back({"Z-function", &benchmark, bytes, match_count, z_timing});
            std::cout << benchmark.name << " bytes=" << bytes
                      << " pattern_bytes=" << benchmark.pattern.size()
                      << " fragments=" << benchmark.fragments.size()
                      << " matches=" << match_count
                      << " repetitions=" << benchmark.repetitions
                      << " kmp_median_us=" << kmp_timing.median_us
                      << " z_median_us=" << z_timing.median_us << '\n';
        }
        std::filesystem::create_directories(csv_path.parent_path());
        std::filesystem::create_directories(summary_path.parent_path());
        const std::string timestamp = timestampUtc();
        writeCsv(csv_path, results, timestamp);
        writeSummary(summary_path, results, timestamp, collection_path);
        std::cout << "equivalence=passed cases=" << cases.size()
                  << " sink=" << benchmark_sink << '\n'
                  << "csv=" << csv_path << '\n'
                  << "summary=" << summary_path << '\n';
    } catch (const std::exception& error) {
        std::cerr << "Exact-matching benchmark failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
