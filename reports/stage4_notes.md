# Stage 4 Notes: Approximate Retrieval and Reranking

## Scope

Stage 4 adds a second way to search the 2,458 chunks, next to the exact search from Stages 2 and 3. Exact search only finds chunks that contain the words of the question as typed. Approximate search also tolerates typos and word variations, and it computes relevance again with two approximate techniques: Levenshtein edit distance and Jaccard similarity over word n grams. The design is recorded in spec 0003. Both techniques and the reranker are written from scratch in C++17 and called from Python through pybind11. Exact search and every Stage 1 to 3 interface are unchanged.

## Algorithms

**Levenshtein edit distance (typo correction).** The edit distance between two words is the smallest number of single character insertions, deletions or substitutions that turns one into the other. It is computed with dynamic programming over a table with one row per letter of the first word and one column per letter of the second, keeping only two rows at a time. A bounded version stops early once every value in a row is above the cutoff. Each word of the question is compared with the 14,180 word vocabulary, and the closest word is kept (ties go to the more frequent word, then to alphabetical order). The cutoff is 1 edit for words up to 4 letters and 2 edits for longer words. Words that contain a digit are never corrected, because a number that is one digit away is a different fact, not a typo.

**Word n grams and Jaccard similarity (phrasing similarity).** Each chunk is stored as the set of its single words and its pairs of consecutive words (word 1 grams and 2 grams), sorted and without duplicates. The question gets the same kind of set. The Jaccard similarity of two sets is the size of their intersection divided by the size of their union. Because both sets are sorted, the intersection is counted in one linear merge pass.

**Inverted index (candidate lookup).** The inverted index from Stage 2 returns every chunk that contains at least one of the corrected question words (an OR query).

## How a question is processed

1. The question is normalized and split into words with the same rules used for the chunks.
2. Common filler words (stopwords such as "what", "the", "was") are dropped. If the question is made only of stopwords, all its words are kept instead and the result is flagged as a stopword fallback. Exact search never drops stopwords.
3. Each remaining word is corrected with Levenshtein. An exact vocabulary word has weight 1. A corrected word has weight 1 / (1 + distance), so a word one edit away counts 0.5. A word with no close vocabulary word is kept as typed with weight 1. If a correction turns a word into a stopword, it is dropped.
4. The candidates are every chunk that contains at least one remaining word, after the optional company and fiscal year filters.
5. Every candidate is scored again in C++ and the list is sorted by score, highest first, with ties broken by chunk ID so the order is always the same.

## Similarity formula

For each candidate chunk:

score = alpha × coverage + (1 − alpha) × (J / J_max)

- **coverage** is the sum of the weights of the question words that appear in the chunk, divided by the number of distinct question words. A chunk that contains every word, all spelled correctly, has coverage 1. A typo word that was corrected counts only half when it is one edit away.
- **J** is the Jaccard similarity between the chunk's word n gram set and the question's.
- **J_max** is the highest J among all candidates (after filters, before keeping the top results). Raw Jaccard values here are tiny, around 0.01 to 0.02, because a chunk holds about 250 words and their pairs while a question holds a handful. Dividing by J_max puts Jaccard on the same 0 to 1 range as coverage, so it really changes the order instead of only breaking ties.
- **alpha** is 0.6 by default, so containing the asked words matters a bit more than matching their phrasing.

Every score lies between 0 and 1. Scores are relative to one question's candidates and should not be compared across questions or filters.

**Worked example (checked by a C++ test).** Three tiny chunks: C1 "nvidia revenue grew", C2 "amd revenue", C3 "nvidia cloud chips". The question words are nvidia (weight 1) and revenue (weight 0.5, as if it had been a correction). C1 contains both words, coverage (1 + 0.5) / 2 = 0.75, and shares 3 of 5 n grams, J = 0.6, which is J_max. Its score is 0.6 × 0.75 + 0.4 × 1 = 0.85. C3 contains only nvidia, coverage 0.5, J = 1/7, scaled 0.238, score 0.395. C2 contains only revenue, coverage 0.25, J = 0.2, scaled 0.333, score 0.283. The order is C1, C3, C2.

## Results on three questions

Settings: top 5 results, alpha 0.6, all companies and years. Exact search is the Stage 2 ranked AND search, falling back to ranked OR when no chunk contains every word; its score is the summed count of the question words in the chunk. Times are the median of 5 runs after one warm up run, measured in Python around each search, on an Apple Silicon laptop with a Release build.

### 1. "nvidea data center revenue" (typo)

Corrections: nvidea becomes nvidia at distance 1 (weight 0.5); data, center and revenue are exact.

| Rank | Exact (OR fallback, 985 candidates) | Score | Approximate (1,106 candidates) | Score |
|---|---|---|---|---|
| 1 | AMD_2024_10K_0156 | 19 | NVDA_2024_10K_0146 | 0.925 |
| 2 | AMD_2024_10K_0015 | 18 | NVDA_2024_10K_0147 | 0.911 |
| 3 | AMD_2024_10K_0170 | 17 | NVDA_2024_10K_0156 | 0.889 |
| 4 | AMD_2025_10K_0178 | 17 | NVDA_2024_10K_0145 | 0.870 |
| 5 | NVDA_2024_10K_0146 | 17 | NVDA_2024_10K_0140 | 0.835 |

Time: exact 0.93 ms; approximate 2.88 ms (correction 0.54, candidates 0.50, rerank 1.79).

Exact search does not know the word "nvidea", so no chunk contains all four words and it falls back to OR. Its top results are AMD chunks that repeat "data center" many times. Approximate search recovers the company: all five results are NVIDIA fiscal 2024 chunks. The first three discuss revenue by market and data center demand; the last two are risk factor passages that mention NVIDIA, data center and revenue only in passing, which shows that coverage cannot tell a central mention from a passing one. Those chunks have coverage 0.875 (three exact words plus the half weight correction), which beats AMD chunks at 0.75. Only one chunk appears in both top 5 lists.

### 2. "data center revenue" (expected to agree)

No corrections; no stopwords.

| Rank | Exact (AND, 72 candidates) | Score | Approximate (985 candidates) | Score |
|---|---|---|---|---|
| 1 | AMD_2024_10K_0156 | 19 | AMD_2024_10K_0170 | 1.000 |
| 2 | AMD_2024_10K_0170 | 17 | AMD_2025_10K_0178 | 1.000 |
| 3 | AMD_2025_10K_0178 | 17 | NVDA_2024_10K_0073 | 0.983 |
| 4 | NVDA_2024_10K_0146 | 17 | NVDA_2025_10K_0154 | 0.983 |
| 5 | AMD_2024_10K_0169 | 16 | NVDA_2024_10K_0142 | 0.978 |

Time: exact 0.09 ms; approximate 1.93 ms (correction 0.01, candidates 0.38, rerank 1.50).

The two modes agree only partly: two chunks are in both top 5 lists (AMD_2024_10K_0170 and AMD_2025_10K_0178, both segment results with "data center net revenue"). When every word is spelled correctly, every chunk that contains all three words has coverage 1, so Jaccard alone decides the order among them. Jaccard rewards chunks that contain the exact phrase "data center" and "center revenue" in a shorter n gram set, while exact search rewards chunks that repeat the words most often. Approximate search also examines 985 OR candidates instead of the 72 AND matches, which is why it is slower here.

### 3. "what risks come from export restrictions" (expected to differ)

Stopwords dropped: what, from. Content words: risks, come, export, restrictions, all exact.

| Rank | Exact (OR fallback, 1,487 candidates) | Score | Approximate (541 candidates) | Score |
|---|---|---|---|---|
| 1 | AMD_2024_10K_0107 | 13 | NVDA_2024_10K_0034 | 0.850 |
| 2 | AMD_2025_10K_0113 | 12 | NVDA_2024_10K_0143 | 0.843 |
| 3 | NVDA_2024_10K_0111 | 11 | NVDA_2025_10K_0038 | 0.817 |
| 4 | AMD_2024_10K_0108 | 10 | AMD_2025_10K_0117 | 0.814 |
| 5 | NVDA_2024_10K_0099 | 9 | NVDA_2025_10K_0152 | 0.781 |

Time: exact 1.60 ms; approximate 1.21 ms (correction 0.01, candidates 0.21, rerank 0.97).

The two lists share no chunk. Both are on topic (export controls on AI chips, licensing for China), but they reach it differently. Exact search falls back to OR over all six words, including "what" and "from", which appear almost everywhere, so it ranks 1,487 chunks largely by how often common words repeat. Approximate search drops those two stopwords, so it examines only 541 chunks, and is faster here even though it does more work per chunk. Its top results contain three of the four content words (coverage 0.75); none contains "come", and Jaccard then prefers chunks whose phrasing is closest, such as NVIDIA's description of U.S. licensing rules for China. Part of this difference comes from dropping stopwords, not from fuzzy matching.

## Differences from exact search

- **Typos.** Exact search cannot match a misspelled word. Approximate search corrects it and still finds the right company, while counting the corrected word at half weight so a wrong correction cannot dominate.
- **Candidates examined.** Approximate search always uses OR over content words. It examines more chunks than an exact AND search that succeeds (985 against 72 for question 2), and fewer than an exact OR search full of stopwords (541 against 1,487 for question 3).
- **Order.** Exact search orders by raw word counts, which favors long chunks that repeat a word. Approximate search orders first by how many distinct question words a chunk contains, then by phrasing similarity, which favors chunks that use the question's word pairs.
- **Time.** Both modes finish in a few milliseconds. Most approximate time is the C++ rerank, which grows with the number of candidates (about 1 to 2 ms for 500 to 1,100 candidates). Correcting a word costs about 0.5 ms when it really needs a vocabulary scan, and almost nothing when the word is already in the vocabulary.

## When approximate search helps and when it adds noise

**It helps** when the question has a typo or an unusual spelling (question 1), and when the question is phrased as natural language with many filler words (question 3): dropping stopwords keeps "what" and "from" from flooding the candidates, and coverage rewards chunks that contain the meaningful words.

**It adds noise** in these cases:

- A correction can be wrong. For example "say" is corrected to "may", and "teh" becomes "ten" rather than "the" (swapping two letters costs 2 edits, above the 1 edit cutoff for short words). The half weight limits the damage but does not remove it.
- Content words that are not in the stopword list but carry little meaning ("come", "company", "revenue") still enlarge the candidate set and count fully in coverage, because coverage has no inverse document frequency (no down weighting of common words).
- When all question words are spelled correctly and appear together often, coverage is 1 for many chunks and Jaccard alone decides the order. Jaccard leans toward shorter chunks, which can push down long but relevant chunks (question 2).
- J / J_max makes scores relative. A single candidate always gets the full Jaccard part, and two chunks with identical n gram overlap tie exactly (the first two results of question 2 both score 1.0 and are ordered by chunk ID).
- alpha = 0.6 and the 1 / (1 + distance) weight are reasoned defaults, not tuned on labeled questions. Stage 6 can test other alpha values on the full question set.

## Testing

Seven new C++ tests cover the worked example above, the case where no candidate shares an n gram (J_max = 0), the typo discount, alpha at 0 and 1, tie breaking by chunk ID, top k limits, and rejection of invalid alpha, weights, and unknown or duplicate chunk IDs. Two more C++ tests cover scoring a given list of chunks with Jaccard. Thirteen Python tests cover the same behavior through `SearchEngine`, on a small synthetic collection and on the real collection: the typo question found only by approximate search, stopword handling and fallback, company and year filters applied before scoring, input validation, and the shape of the side by side comparison. All earlier C++ and Python tests still pass unchanged.
