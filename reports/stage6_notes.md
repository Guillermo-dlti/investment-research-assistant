# Stage 6 Notes: Comparison of Exact and Approximate Retrieval

## Scope

Stage 6 compares the two retrieval strategies built earlier, on the same questions and with everything else held fixed:

- **Exact search (Stage 3).** Ranked AND search over the inverted index, falling back to ranked OR when no chunk contains every word of the question. The score is the summed count of the question's words in the chunk. Stopwords are kept and nothing is corrected.
- **Approximate search (Stage 4).** Stopwords are dropped, each word is corrected with Levenshtein distance, every chunk that contains at least one corrected word becomes a candidate, and candidates are reranked by a mix of weighted word coverage and word n gram Jaccard similarity.

Both strategies feed the same top 10 chunks into the same context selection (at most 4 chunks, 1,100 words, near duplicates dropped at Jaccard 0.5 or more) and the same model, `Qwen/Qwen2.5-3B-Instruct` with greedy decoding. The company and fiscal year filters inferred from the question are applied to both. The only thing that changes is the search algorithm.

The question set is the 21 questions from Stage 5 plus 3 new ones with typos in the topic words ("aple iphone net sales", "nvidia reserch and developmnet expenses", "alphabet youtube advertisng revenue"), 24 in total. The full side by side output is in `reports/stage6_results.md`, the raw data in `reports/stage6_results.json`, and the charts in `reports/stage6_time_per_question.png`, `reports/stage6_context_usefulness.png` and `reports/stage6_time_vs_collection_size.png`. Times were measured on an Apple M4 Pro with a Release build.

## How usefulness was measured

"Useful" needs a definition that does not depend on which search found the chunk. For 22 of the 24 questions an evidence rule was written by hand: the chunk must come from the right company (and year, when the question names one) and its original text must contain specific phrases. For example, for NVIDIA's fiscal 2025 data center revenue the chunk must contain "115,186", which is the figure in the revenue by end market table. Only one chunk in the collection matches that rule. For AMD's export restrictions it must mention both "export" and "China" (16 chunks match). Each rule was checked against the whole collection before the comparison was run. The other two questions (Tesla, which is not in the collection, and the vague "What is the outlook?") have no evidence by design.

Each strategy is then scored on three things: whether a useful chunk appears in the top 10, whether one survives into the 4 chunk context, and the precision of the context (useful chunks divided by selected chunks).

Answers were labeled by checking them against the expected facts for the questions that have a single number as their answer (NVIDIA data center revenue, NVIDIA R&D twice, Azure growth, Apple employees), against a refusal for Tesla, and by reading the rest. An answer that is fluent but leaves out or misstates the expected fact is labeled "missed fact".

## Results

| Measure | Exact | Approximate |
|---|---|---|
| Mean retrieval time | 2.92 ms | 1.94 ms |
| Median retrieval time | 3.43 ms | 1.77 ms |
| Slowest question | 4.78 ms | 3.48 ms |
| Mean candidate chunks examined | 681 | 357 |
| Chunks retrieved / selected per question | 10 / 4 | 10 / 4 |
| Questions with a useful chunk in the top 10 (of 22) | 16 | 18 |
| Questions with a useful chunk in the context (of 22) | 13 | 17 |
| Mean precision of the context | 0.30 | 0.43 |
| Checked answers correct (of 6) | 2 | 3 |
| Refusals on answerable questions | 6 | 2 |
| Mean model generation time | 3.1 s | 3.2 s |

The two strategies rarely agree on which chunks matter. Their top 10 lists share on average 15% of their chunks (Jaccard of the two ID sets), their contexts share 14%, and no question got exactly the same context from both.

## Cases where both methods give similar results

- **Azure growth in fiscal 2025 (question 8).** This question has the highest overlap (0.54 in the top 10). Both contexts hold two of the three evidence chunks, and both answers state the correct 34% growth.
- **iPhone net sales in fiscal 2025 (11), and its typo version "aple iphone net sales" (22).** Both strategies select the single evidence chunk, and the answers are almost word for word the same: sales increased because of higher sales of Pro models. For the typo version, exact search still works because "iphone net sales" is enough to find the right passages even though "aple" matches nothing.
- **Share repurchases in fiscal 2025 (21).** All 4 selected chunks are useful in both modes. Both answers report Microsoft's repurchases, and approximate gives the cleaner figure ($12.0 billion to $13.0 billion).
- **Tesla (19), out of the collection.** Both strategies retrieve unrelated NVIDIA and Microsoft chunks, and in both cases the model correctly refuses.
- **Apple manufacturing in China (14).** Both miss the 7 evidence chunks and both answers are refusals.

These questions share a pattern. When the question uses the same distinctive words as the filing ("Azure and other cloud services", "iPhone net sales", "repurchase"), both methods land on the same passages, and the model's answer does not depend on the search algorithm.

## Cases with an important difference

**Typos: approximate search wins clearly.**
- *"nvidea gaming revenue" (4).* Exact search does not know "nvidea", falls back to OR, and fills the context with AMD and Microsoft chunks that repeat "gaming" and "revenue". The model refuses. Approximate search corrects nvidea to nvidia and selects three NVIDIA chunks with gaming revenue, and the model answers correctly ($10.4 billion, up 15%).
- *"nvidia reserch and developmnet expenses" (23).* Exact search finds NVIDIA chunks that do not discuss R&D, and the model says R&D expenses are "not directly disclosed". Approximate search corrects both words and selects the two chunks with the income statement, and the model gives the exact figure of $8,675 million.
- *"alphabet youtube advertisng revenue" (24).* Exact search refuses. Approximate search corrects "advertisng" and answers "YouTube ads revenues increased $4.2 billion from 2024 to 2025", which is in its selected evidence chunk.

**Stopwords: approximate search wins on long questions.** Exact search keeps "what", "was", "the" and "in", so AND search almost never succeeds on a full question and the OR fallback ranks chunks by how often they repeat common words. For "What was NVIDIA data center revenue in fiscal 2025?" (1), the exact context contains none of the evidence, and the model answers with a true but different fact ("up 142%") instead of the amount. The approximate context contains the end market table, and the model answers "$115,186 million". The same effect is behind questions 6, 7, 9 and 12, where approximate search selects one or two more useful chunks than exact search.

**Exact search wins when frequency matters more than phrasing.**
- *"How many employees does Apple have?" (13).* This is the clearest reversal. Apple's filing says "the Company had approximately 164,000 full time equivalent employees" and never says "Apple" in that paragraph. Approximate search gives "apple" a full share of the coverage score and ranks chunks that mention Apple by name higher, so the employee paragraph is lost, and the model refuses. Exact search scores by raw word counts, and the human capital paragraph repeats "employees" often enough to reach the top 10. The model answers correctly with 164,000 (the fiscal 2024 figure).
- *YouTube advertising revenue (16).* Exact search selects three evidence chunks against approximate's one, and gives the better answer ("YouTube ads revenues increased $4.6 billion"). Approximate search spreads its coverage over "google", "youtube", "advertising" and "revenue", and rewards general advertising passages that mention all four.

**Approximate search can produce confident answers to bad questions.** For "What is the outlook?" (20), approximate search drops "what", "is" and "the", which leaves the single word "outlook" and only 11 candidates. Its context is Microsoft impairment policy text, and the model writes a fluent but useless answer. Exact search, whose context is dominated by stopwords, makes the model refuse, which is the better outcome. In the same way, approximate retrieval answered question 15 (Alphabet's sources of revenue) from cost of revenue passages and labeled traffic acquisition costs as a revenue source, while exact search refused. Fewer refusals (2 against 6) is therefore not purely good. Some of the extra answers come from context that is related but not relevant.

**Neither method finds it.** NVIDIA's fiscal 2024 R&D (2) fails in both modes. Approximate search returns the stock based compensation table, where R&D appears with $2,532 million, and the model reports that number as total R&D spending. Exact search returns human capital text. The typo version of the same question (23) succeeds because its words, "research", "development" and "expenses", match the income statement better than "spend on". This is a reminder that both methods match words, not meaning.

## Which algorithm is faster

It depends on the filters, and the reason is in where each method filters.

**With the company and year filters inferred from the question (the real pipeline), approximate search is faster**: 1.94 ms against 2.92 ms on average, and faster on 19 of the 24 questions. Exact search ranks every chunk that matches, across all 10 filings, before it applies the filters, and its OR fallback over stopwords matches most of the collection (2,418 of 2,458 chunks for the TSMC question). Approximate search removes stopwords, so its candidate list is about half as long (357 against 681 on average), and it filters candidates before the C++ reranking step, so the filters reduce the expensive part of the work.

**Without filters, exact search is faster**: on the full collection, 2.38 ms against 3.07 ms (table below). Exact scoring is one addition per matched word per chunk, while approximate reranking also computes a Jaccard similarity for every candidate, a linear merge of two sorted n gram sets of about 450 entries. Approximate search examines fewer candidates, but it spends more on each one.

The questions where exact search is much faster (4, 10, 22 and 24, about 1 ms against 3 ms) are the short typo questions. There, exact search has only three or four words to look up and no correction step, while approximate search spends about half a millisecond comparing each word against the 14,180 word vocabulary with bounded Levenshtein distance.

Both strategies take a few milliseconds, while the model takes about 3 seconds per answer. End to end, the choice of search algorithm changes the total time by less than 0.1%. Speed is not a reason to prefer either method in this system, but quality is.

## How collection size affects search time

Both searches were timed, without filters, on the 24 questions over six versions of the collection: every 8th, 4th and 2nd chunk, the full collection, and two and four renamed copies of it.

| Chunks | Exact | Approximate | Exact candidates | Approximate candidates |
|---|---|---|---|---|
| 308 | 0.28 ms | 0.48 ms | 232 | 125 |
| 615 | 0.55 ms | 0.82 ms | 463 | 248 |
| 1,229 | 1.15 ms | 1.57 ms | 929 | 496 |
| 2,458 | 2.38 ms | 3.07 ms | 1,854 | 985 |
| 4,916 | 5.02 ms | 6.35 ms | 3,708 | 1,971 |
| 9,832 | 10.97 ms | 13.20 ms | 7,416 | 3,942 |

Both grow linearly. Doubling the collection doubles the number of candidates and roughly doubles the time, about 1.1 µs per chunk for exact search and 1.3 µs for approximate search at the largest size. This matches the analysis of earlier stages. The inverted index avoids scanning chunks that contain none of the words, but common words such as "revenue" appear in a fixed fraction of all chunks, so the candidate list, and every per candidate step (building results, filtering, Jaccard scoring), grows in proportion to the collection. The only cost that does not grow is the Levenshtein correction, which depends on the vocabulary, and the vocabulary grows much more slowly than the collection because new filings mostly reuse the same words. Neither method is close to a practical limit. At 4 times the current collection both stay around 11 to 13 ms, still far below the model's time. A collection thousands of times larger would need the index to return fewer candidates, for example by ranking posting lists and stopping early, rather than a different string algorithm.

## How context selection affects the answer

The model answered every question from the 4 chunks it was given, and its behavior followed the context almost exactly:

- **When an evidence chunk was in the context, the model used it.** In all 5 correct checked answers (3 approximate, 2 exact), the stated figure comes from a selected evidence chunk, and the citation points to it.
- **When no evidence chunk was in the context, the model either refused or answered from the nearest related number.** Refusals happened on 6 answerable questions with exact search and 2 with approximate. Wrong numbers appeared when the context held a table with the right words but the wrong measure: R&D stock compensation instead of R&D expense (question 2), and segment and cloud figures mixed up in question 10, where both methods selected the useful chunks but the model still combined numbers from different years.
- **More useful chunks do not always mean a better answer.** For ZT Systems (7), approximate search selected 4 useful chunks out of 4, including both fiscal years. The model still used only the older statement ("expected to close in the first half of 2025"). Selection decides what the model can see, not which part of it the model trusts.
- **Redundancy removal mattered for both strategies.** Year over year filings repeat whole paragraphs, and without removing near duplicates, several contexts would have spent half their space on the same text. This step made room for a different chunk in many questions, regardless of which search produced the candidates.

## Advantages and limitations of classic string algorithms for retrieval

**Advantages**
- **Speed and predictability.** Both strategies answer in a few milliseconds over about 490,000 words of filings, with linear growth that can be analyzed in advance. Every score is deterministic and can be explained, for example "this chunk contains 3 of the 4 words, one of them corrected at distance 1".
- **Exact facts survive.** String matching does not paraphrase. When the question uses the filing's terms, the passage with the exact number is found, and the model can quote it with a citation that a reader can check.
- **Robustness to typos is cheap.** Bounded Levenshtein distance fixed every typo question in the set at a cost of about half a millisecond.
- **No training and no external service.** The whole retrieval side runs locally from data structures built in C++, which made it possible to measure every step.

**Limitations**
- **They match words, not meaning.** "Apple" and "the Company", "spend on R&D" and "research and development expenses", or "outlook" and "guidance" look unrelated to both methods. Every question where approximate search put no evidence in the context (2, 3, 13, 14 and 15) fails because of a vocabulary mismatch, not because the algorithm is slow or wrong.
- **Frequency is not relevance.** Exact search rewards repetition of common words. Approximate search rewards containing every question word once. Neither can tell a passing mention from the paragraph about the topic, which is why tables with similar labels (stock compensation by function, segment revenue next to total revenue) are a frequent source of wrong numbers.
- **No notion of answerability.** Retrieval always returns 10 chunks, even for Tesla or "What is the outlook?". The decision to refuse is left entirely to the model.
- **The two methods fail differently.** Their top 10 lists share only 15% of their chunks, and each one wins questions the other loses (approximate on typos and long questions, exact on questions 13 and 16). A practical system would combine both, or add a semantic method such as embedding similarity on top of the string based candidates.

## Conclusions

- **Approximate search recovers more useful information**: a useful chunk reaches the context on 17 of 22 questions against 13, with context precision 0.43 against 0.30, and more checked answers are correct. Its biggest gains are on typos and long natural language questions, where stopword removal and Levenshtein correction fix the weaknesses of exact matching.
- **Exact search remains competitive** when the question's own words are the filing's words, and it wins when repetition of a key word matters more than coverage of the question (Apple employees, YouTube ads). It also refuses more often, which is safer on vague questions but loses answers on answerable ones.
- **Speed does not separate the methods in practice.** With filters, approximate search is faster (1.9 ms against 2.9 ms), and without them exact search is (2.4 ms against 3.1 ms). Both scale linearly with the collection and both are about a thousand times faster than the language model.
- **Retrieval determines the answer.** With the model, prompt and selection held fixed, changing only the search algorithm changed the wording of 23 of the 24 answers and the outcome of 8 (refusal against answer, or missed fact against correct figure). The quality of the string algorithms directly controls what the language model can say.
