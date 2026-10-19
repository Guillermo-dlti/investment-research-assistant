# Investment Research Assistant

Investment Research Assistant is an educational project for an Advanced Algorithms university course. The project will explore how advanced string-matching algorithms and data structures can support an AI-powered system that retrieves relevant information from financial documents and uses it to answer research questions.

The initial scope covers five technology companies:

- NVIDIA
- AMD
- Microsoft
- Apple
- Alphabet

## Technology Stack

- **Python:** Document processing, application logic, and AI integration.
- **C++:** Custom implementations of algorithms and data structures.
- **pybind11:** Integration of the C++ implementations with Python.
- **Hugging Face:** Pretrained language model support.
- **Streamlit:** User interface.

## Planned Algorithms and Data Structures

- **Knuth-Morris-Pratt (KMP):** Exact pattern matching within document text.
- **Z-function:** Efficient pattern-search and string-analysis operations.
- **Levenshtein Distance:** Approximate matching based on edit distance.
- **N-grams and Jaccard Similarity:** Similarity measurement between queries and document passages.
- **Trie:** Efficient storage and lookup of terms and prefixes.
- **Inverted Index:** Mapping terms to the document passages in which they occur.

## Planned Workflow

Financial reports will be collected and converted into clean text. The text will then be divided into searchable chunks and enriched with metadata such as company, document type, and reporting period. The custom C++ algorithms and data structures, exposed to Python through pybind11, will help find and rank chunks relevant to a user's question. Selected context will be passed to a pretrained Hugging Face language model, which will generate a response grounded in the retrieved documents. Streamlit will eventually provide the interface for submitting questions and viewing answers and supporting sources.

## Current Status

**Stage 1 — Document Selection and Preparation**

The initial project structure is in place. Document processing, retrieval algorithms, AI integration, and the user interface have not yet been implemented.

## Development Setup

The project requires Python 3.11 or newer. Python 3.11 or 3.12 is recommended for consistent package compatibility. A compiler with C++17 support is also required; Apple Clang, included with the Xcode Command Line Tools, is suitable on macOS.

From the project root, create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install the project dependencies inside the environment:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify Python, the required imports, CMake, and the C++ compiler:

```bash
python --version
python -c "import pymupdf, pybind11, pytest; print('Python dependencies are available')"
cmake --version
clang++ --version
```

If `clang++` is unavailable on macOS, install Apple's command-line developer tools with `xcode-select --install`. The `cmake` command is installed in the virtual environment by `requirements.txt`; if a system-wide CMake installation is needed separately, install it manually with Homebrew using `brew install cmake`.

When finished, leave the virtual environment:

```bash
deactivate
```

## Disclaimer

This application is intended solely for educational and research purposes. It does not provide personalized financial advice, investment recommendations, or a substitute for professional financial guidance.
