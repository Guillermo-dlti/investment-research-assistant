#include "trie.h"

void Trie::insert(const std::string& word) {
    Node* node = &root_;
    for (const unsigned char byte : word) {
        auto& child = node->children[byte];
        if (!child) {
            child = std::make_unique<Node>();
        }
        node = child.get();
    }

    if (!node->is_word) {
        node->is_word = true;
        ++size_;
    }
}

const Trie::Node* Trie::findNode(const std::string& text) const {
    const Node* node = &root_;
    for (const unsigned char byte : text) {
        const auto child = node->children.find(byte);
        if (child == node->children.end()) {
            return nullptr;
        }
        node = child->second.get();
    }
    return node;
}

bool Trie::search(const std::string& word) const {
    const Node* node = findNode(word);
    return node != nullptr && node->is_word;
}

bool Trie::startsWith(const std::string& prefix) const {
    return findNode(prefix) != nullptr;
}

std::vector<std::string> Trie::autocomplete(
    const std::string& prefix,
    const std::size_t k
) const {
    std::vector<std::string> results;
    if (k == 0) {
        return results;
    }

    const Node* node = findNode(prefix);
    if (node == nullptr) {
        return results;
    }

    std::string current = prefix;
    collect(*node, current, k, results);
    return results;
}

void Trie::collect(
    const Node& node,
    std::string& current,
    const std::size_t k,
    std::vector<std::string>& results
) {
    if (results.size() == k) {
        return;
    }
    if (node.is_word) {
        results.push_back(current);
    }
    for (const auto& [byte, child] : node.children) {
        if (results.size() == k) {
            break;
        }
        current.push_back(static_cast<char>(byte));
        collect(*child, current, k, results);
        current.pop_back();
    }
}

std::size_t Trie::size() const noexcept {
    return size_;
}
