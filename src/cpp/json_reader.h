#ifndef INVESTMENT_RESEARCH_ASSISTANT_JSON_READER_H
#define INVESTMENT_RESEARCH_ASSISTANT_JSON_READER_H

#include <cstddef>
#include <filesystem>
#include <string>
#include <string_view>

class JsonReader {
public:
    explicit JsonReader(std::string text);

    [[nodiscard]] bool consume(char expected);
    void expect(char expected);
    [[nodiscard]] std::string parseString();
    [[nodiscard]] std::size_t parseUnsigned();
    void skipValue();
    void finish();
    [[noreturn]] void fail(const std::string& message) const;

private:
    void appendEscapedCodePoint(std::string& output);
    [[nodiscard]] unsigned int parseHexQuad();
    static void appendUtf8(std::string& output, unsigned int code_point);
    void skipNumber();
    void requireDigit() const;
    void skipWhitespace();
    [[nodiscard]] bool startsWith(std::string_view value) const;

    std::string text_;
    std::size_t position_ = 0;
};

[[nodiscard]] std::string readJsonFile(const std::filesystem::path& path);

#endif
