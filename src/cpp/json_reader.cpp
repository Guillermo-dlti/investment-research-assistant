#include "json_reader.h"

#include <cctype>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <utility>

JsonReader::JsonReader(std::string text) : text_(std::move(text)) {}

bool JsonReader::consume(const char expected) {
    skipWhitespace();
    if (position_ < text_.size() && text_[position_] == expected) {
        ++position_;
        return true;
    }
    return false;
}

void JsonReader::expect(const char expected) {
    if (!consume(expected)) {
        fail(std::string("expected '") + expected + "'");
    }
}

std::string JsonReader::parseString() {
    skipWhitespace();
    if (position_ >= text_.size() || text_[position_] != '"') {
        fail("expected string");
    }
    ++position_;
    std::string result;
    while (position_ < text_.size()) {
        const unsigned char byte = static_cast<unsigned char>(text_[position_++]);
        if (byte == '"') {
            return result;
        }
        if (byte < 0x20) {
            fail("unescaped control character in string");
        }
        if (byte != '\\') {
            result.push_back(static_cast<char>(byte));
            continue;
        }
        if (position_ >= text_.size()) {
            fail("unfinished string escape");
        }
        const char escaped = text_[position_++];
        switch (escaped) {
            case '"': result.push_back('"'); break;
            case '\\': result.push_back('\\'); break;
            case '/': result.push_back('/'); break;
            case 'b': result.push_back('\b'); break;
            case 'f': result.push_back('\f'); break;
            case 'n': result.push_back('\n'); break;
            case 'r': result.push_back('\r'); break;
            case 't': result.push_back('\t'); break;
            case 'u': appendEscapedCodePoint(result); break;
            default: fail("invalid string escape");
        }
    }
    fail("unterminated string");
}

std::size_t JsonReader::parseUnsigned() {
    skipWhitespace();
    if (position_ >= text_.size() ||
        !std::isdigit(static_cast<unsigned char>(text_[position_]))) {
        fail("expected non-negative integer");
    }
    std::size_t value = 0;
    while (position_ < text_.size() &&
           std::isdigit(static_cast<unsigned char>(text_[position_]))) {
        const std::size_t digit = static_cast<std::size_t>(text_[position_] - '0');
        if (value > (std::numeric_limits<std::size_t>::max() - digit) / 10) {
            fail("integer is too large");
        }
        value = value * 10 + digit;
        ++position_;
    }
    return value;
}

void JsonReader::skipValue() {
    skipWhitespace();
    if (position_ >= text_.size()) {
        fail("expected JSON value");
    }
    if (text_[position_] == '"') {
        static_cast<void>(parseString());
    } else if (text_[position_] == '{') {
        expect('{');
        while (!consume('}')) {
            static_cast<void>(parseString());
            expect(':');
            skipValue();
            if (!consume(',')) {
                expect('}');
                break;
            }
        }
    } else if (text_[position_] == '[') {
        expect('[');
        while (!consume(']')) {
            skipValue();
            if (!consume(',')) {
                expect(']');
                break;
            }
        }
    } else if (startsWith("true")) {
        position_ += 4;
    } else if (startsWith("false")) {
        position_ += 5;
    } else if (startsWith("null")) {
        position_ += 4;
    } else {
        skipNumber();
    }
}

void JsonReader::finish() {
    skipWhitespace();
    if (position_ != text_.size()) {
        fail("unexpected data after root value");
    }
}

void JsonReader::appendEscapedCodePoint(std::string& output) {
    unsigned int code_point = parseHexQuad();
    if (code_point >= 0xD800 && code_point <= 0xDBFF) {
        if (position_ + 2 > text_.size() ||
            text_[position_] != '\\' || text_[position_ + 1] != 'u') {
            fail("high surrogate without low surrogate");
        }
        position_ += 2;
        const unsigned int low = parseHexQuad();
        if (low < 0xDC00 || low > 0xDFFF) {
            fail("invalid low surrogate");
        }
        code_point = 0x10000 + ((code_point - 0xD800) << 10) + (low - 0xDC00);
    } else if (code_point >= 0xDC00 && code_point <= 0xDFFF) {
        fail("unexpected low surrogate");
    }
    appendUtf8(output, code_point);
}

unsigned int JsonReader::parseHexQuad() {
    if (position_ + 4 > text_.size()) {
        fail("incomplete Unicode escape");
    }
    unsigned int value = 0;
    for (int index = 0; index < 4; ++index) {
        const char digit = text_[position_++];
        value <<= 4;
        if (digit >= '0' && digit <= '9') {
            value += static_cast<unsigned int>(digit - '0');
        } else if (digit >= 'a' && digit <= 'f') {
            value += static_cast<unsigned int>(digit - 'a' + 10);
        } else if (digit >= 'A' && digit <= 'F') {
            value += static_cast<unsigned int>(digit - 'A' + 10);
        } else {
            fail("invalid Unicode escape");
        }
    }
    return value;
}

void JsonReader::appendUtf8(
    std::string& output,
    const unsigned int code_point
) {
    if (code_point <= 0x7F) {
        output.push_back(static_cast<char>(code_point));
    } else if (code_point <= 0x7FF) {
        output.push_back(static_cast<char>(0xC0 | (code_point >> 6)));
        output.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
    } else if (code_point <= 0xFFFF) {
        output.push_back(static_cast<char>(0xE0 | (code_point >> 12)));
        output.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
        output.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
    } else {
        output.push_back(static_cast<char>(0xF0 | (code_point >> 18)));
        output.push_back(static_cast<char>(0x80 | ((code_point >> 12) & 0x3F)));
        output.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
        output.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
    }
}

void JsonReader::skipNumber() {
    skipWhitespace();
    if (position_ < text_.size() && text_[position_] == '-') {
        ++position_;
    }
    if (position_ >= text_.size() ||
        !std::isdigit(static_cast<unsigned char>(text_[position_]))) {
        fail("invalid JSON value");
    }
    if (text_[position_] == '0') {
        ++position_;
    } else {
        while (position_ < text_.size() &&
               std::isdigit(static_cast<unsigned char>(text_[position_]))) {
            ++position_;
        }
    }
    if (position_ < text_.size() && text_[position_] == '.') {
        ++position_;
        requireDigit();
        while (position_ < text_.size() &&
               std::isdigit(static_cast<unsigned char>(text_[position_]))) {
            ++position_;
        }
    }
    if (position_ < text_.size() &&
        (text_[position_] == 'e' || text_[position_] == 'E')) {
        ++position_;
        if (position_ < text_.size() &&
            (text_[position_] == '+' || text_[position_] == '-')) {
            ++position_;
        }
        requireDigit();
        while (position_ < text_.size() &&
               std::isdigit(static_cast<unsigned char>(text_[position_]))) {
            ++position_;
        }
    }
}

void JsonReader::requireDigit() const {
    if (position_ >= text_.size() ||
        !std::isdigit(static_cast<unsigned char>(text_[position_]))) {
        fail("expected digit");
    }
}

void JsonReader::skipWhitespace() {
    while (position_ < text_.size() &&
           std::isspace(static_cast<unsigned char>(text_[position_]))) {
        ++position_;
    }
}

bool JsonReader::startsWith(const std::string_view value) const {
    return text_.compare(position_, value.size(), value) == 0;
}

void JsonReader::fail(const std::string& message) const {
    throw std::runtime_error(
        "invalid JSON near byte " + std::to_string(position_) + ": " + message
    );
}

std::string readJsonFile(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("could not open JSON file: " + path.string());
    }
    std::ostringstream buffer;
    buffer << input.rdbuf();
    if (!input.good() && !input.eof()) {
        throw std::runtime_error("could not read JSON file: " + path.string());
    }
    return buffer.str();
}
