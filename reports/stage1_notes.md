# Stage 1 Academic Notes

## Scope and Selected Documents

The Stage 1 collection contains the FY2024 and FY2025 Form 10-K filings for five large technology companies:

| Company | Ticker | Fiscal year | Fiscal year end | SEC accession number |
|---|---|---:|---|---|
| NVIDIA Corporation | NVDA | 2024 | 2024-01-28 | 0001045810-24-000029 |
| NVIDIA Corporation | NVDA | 2025 | 2025-01-26 | 0001045810-25-000023 |
| Advanced Micro Devices, Inc. | AMD | 2024 | 2024-12-28 | 0000002488-25-000012 |
| Advanced Micro Devices, Inc. | AMD | 2025 | 2025-12-27 | 0000002488-26-000018 |
| Microsoft Corporation | MSFT | 2024 | 2024-06-30 | 0000950170-24-087843 |
| Microsoft Corporation | MSFT | 2025 | 2025-06-30 | 0000950170-25-100235 |
| Apple Inc. | AAPL | 2024 | 2024-09-28 | 0000320193-24-000123 |
| Apple Inc. | AAPL | 2025 | 2025-09-27 | 0000320193-25-000079 |
| Alphabet Inc. | GOOGL | 2024 | 2024-12-31 | 0001652044-25-000014 |
| Alphabet Inc. | GOOGL | 2025 | 2025-12-31 | 0001652044-26-000018 |

All documents are official HTML filings from the SEC EDGAR archives. Their CIKs, accession numbers, filing dates, fiscal periods, primary documents, and source URLs are recorded in `config/document_manifest.json`.

These companies were selected because they are significant participants in semiconductors, cloud computing, software, consumer hardware, internet services, and artificial intelligence. Two consecutive fiscal years support comparisons over time, while Form 10-K filings provide a consistent source containing audited financial statements, business descriptions, risk factors, and management discussion. Company fiscal years are used rather than assuming that every report follows the calendar year.

## Intended Research Questions

The future assistant should help answer document-grounded questions such as:

- What business segments and products does each company describe?
- Which risk factors appear across multiple companies or fiscal years?
- How did reported revenue, operating income, margins, or major expenses change?
- What does management identify as important competitive, regulatory, or supply-chain risks?
- How do the FY2024 and FY2025 discussions differ for the same company?
- Where in the source filing is a particular financial value or statement reported?

These questions concern information contained in the filings. The project does not claim to predict stock prices or future market movements.

## Extraction Methodology

Each verified SEC HTML filing is retained under `data/raw/`. BeautifulSoup parses the HTML and removes scripts, styles, hidden inline-XBRL metadata, and other non-visible elements. Visible headings, paragraphs, list items, and financial table rows are retained. Whitespace is reduced without intentionally altering dates, currency symbols, percentages, negative values, or punctuation.

Every extracted document is stored separately as readable UTF-8 text and structured JSON under `data/processed/`. The JSON preserves filing metadata and assigns an ordered identifier to each extracted paragraph. Keeping raw HTML separate from processed output makes the transformation auditable and repeatable.

## Chunking Methodology

Documents are divided into chunks containing at most 250 tokens, with 40 tokens of overlap between consecutive chunks. Paragraph and sentence endings are preferred as boundaries when practical. Long uninterrupted passages are split at token boundaries. Financial tokens such as currency amounts, comma-formatted numbers, percentages, and dates are kept intact.

Chunk IDs are deterministic and combine the document ID with a sequential position. Each chunk retains the source document metadata, original text, word count, and starting and ending paragraph identifiers. The consolidated collection is ordered first by the tracked manifest and then by chunk position.

## Actual Collection Statistics

| Company | FY | Extracted words | Characters | Paragraphs | Chunks |
|---|---:|---:|---:|---:|---:|
| NVIDIA | 2024 | 51,773 | 345,553 | 1,872 | 258 |
| NVIDIA | 2025 | 53,126 | 354,552 | 1,917 | 265 |
| AMD | 2024 | 57,174 | 379,376 | 1,828 | 291 |
| AMD | 2025 | 59,969 | 397,079 | 1,860 | 303 |
| Microsoft | 2024 | 53,754 | 362,594 | 2,233 | 265 |
| Microsoft | 2025 | 47,696 | 321,213 | 2,073 | 235 |
| Apple | 2024 | 31,388 | 209,121 | 1,241 | 155 |
| Apple | 2025 | 31,668 | 211,606 | 1,212 | 157 |
| Alphabet | 2024 | 53,966 | 357,636 | 2,145 | 268 |
| Alphabet | 2025 | 52,809 | 351,677 | 2,163 | 261 |
| **Total** |  | **493,323** | **3,290,407** | **18,544** | **2,458** |

The average document contains 245.8 chunks. Chunk sizes range from 44 to 250 tokens, with an average of 234.85 tokens. The raw case-folded vocabulary contains 9,359 unique word or number tokens.

The 493,323-word total comes from the non-overlapping processed documents. The chunk token total is 577,264 because overlap deliberately repeats context; it must not be interpreted as the original collection word count. The extractor and chunker use different counting rules, and the generated statistics file documents both methods.

## Limitations

- SEC filings are historical disclosures and do not provide real-time stock prices.
- HTML layouts vary by company and year, so paragraph and table extraction may retain layout artifacts such as page numbers or repeated headings.
- Sentence boundaries are detected with a lightweight heuristic and may treat some abbreviations imperfectly.
- The 40-token overlap intentionally duplicates context in the consolidated chunk array.
- Section labels are not inferred when the extraction output does not identify them reliably.
- The collection covers only two fiscal years and five technology companies, so conclusions should not be generalized to the entire market.
- The filings contain company statements and historical results; they do not guarantee future performance and cannot reliably predict stock movements.
