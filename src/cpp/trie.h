#ifndef INVESTMENT_RESEARCH_ASSISTANT_TRIE_H
#define INVESTMENT_RESEARCH_ASSISTANT_TRIE_H

#include <cstddef>
#include <map>
#include <memory>
#include <string>
#include <vector>

class Trie {
public:
    void insert(const std::string& word);
    [[nodiscard]] bool search(const std::string& word) const;
    [[nodiscard]] bool startsWith(const std::string& prefix) const;
    [[nodiscard]] std::vector<std::string> autocomplete(
        const std::string& prefix,
        std::size_t k
    ) const;
    [[nodiscard]] std::size_t size() const noexcept;

private:
    struct Node {
        bool is_word = false;
        std::map<unsigned char, std::unique_ptr<Node>> children;
    };

    const Node* findNode(const std::string& text) const;
    static void collect(
        const Node& node,
        std::string& current,
        std::size_t k,
        std::vector<std::string>& results
    );

    Node root_;
    std::size_t size_ = 0;
};

#endif
