# Stage 5 Notes: Context Selection and Language Model Answers

## Scope

Stage 5 closes the loop the brief describes: question → search → retrieved chunks → context selection → language model → answer. Retrieval is the approximate search from Stage 4 (exact search can be chosen instead). The selection algorithm is new and written from scratch in C++17. The language model is a pretrained Hugging Face model used without any training. The full output for 21 questions is in `reports/stage5_results.md`, with the raw data in `reports/stage5_results.json`.

## Context selection

The model cannot read the whole collection, and even the top 10 retrieved chunks (about 2,400 words) are more than a small model handles well. The selector therefore picks a few chunks under three limits.

- **Top k by score.** Candidates are visited from the highest retrieval score to the lowest (ties by chunk ID), so the order from Stage 4, which already favors chunks that contain more of the question's words, decides priority.
- **Chunk limit.** At most 4 chunks are kept.
- **Word budget.** The kept chunks may add up to at most 1,100 words. A chunk that would go over the budget is skipped, not treated as the end, so a shorter chunk further down can still fit.
- **Redundancy removal.** A chunk is dropped when its Jaccard similarity (word 1 grams and 2 grams, the same sets as Stage 4) with any chunk already kept is 0.5 or more. This matters for this collection because each company's FY2024 and FY2025 10-Ks repeat whole paragraphs. Neighboring chunks, which share only their 40 word overlap, stay well below 0.5.

**Design technique.** This is a greedy algorithm: each candidate is accepted or rejected once, based only on the chunks already kept, and decisions are never undone. Greedy selection is not guaranteed to find the best possible set under a word budget (that is a knapsack problem), but with 10 candidates of nearly equal length the difference is negligible and the result is easy to explain chunk by chunk.

**Complexity.** Let c be the number of candidates (10), k the chunk limit (4) and g the size of a chunk's n gram set (about 450). Sorting costs O(c log c). Each candidate is compared with at most k kept chunks, and each Jaccard comparison is one linear merge of two sorted sets, O(g). Selection is therefore O(c log c + c · k · g), about 18,000 basic steps per question, and it uses O(c) extra memory because the n gram sets are already stored by the Stage 4 index. Measured selection time, including the call from Python, had a median of 0.09 ms per question (at most 0.15 ms).

**What it did on the 21 questions.** 84 chunks were selected, 12 were dropped as redundant and 114 were cut by the chunk limit. Redundancy removal fired on 9 of the 21 questions, always between the FY2024 and FY2025 versions of the same paragraph, with similarities between 0.56 and 0.97 (for example the YouTube advertising question, where two pairs of chunks scored 0.97 and 0.92). The highest similarity between two chunks that were both kept was 0.43. The word budget never fired: four chunks of at most 250 words always fit, so in practice the chunk limit and redundancy removal shape the context, and the budget is a safety cap.

## Language model

**Model.** `Qwen/Qwen2.5-3B-Instruct` from Hugging Face, run locally with the `transformers` library on the Apple M4 Pro GPU (MPS) in half precision. It is an instruction tuned chat model with a 32,000 token context, so four chunks (about 1,300 tokens) fit easily.

**Why this model.** The smaller `Qwen/Qwen2.5-1.5B-Instruct` was tried first on four of these questions. It answered the simple numeric question correctly but almost never cited its sources, and for the Tesla question it presented NVIDIA's automotive revenue as Tesla's. The 3B model cited sources on most questions and correctly refused the Tesla question. Larger 7B models would answer better but need about 15 GB of weights and are slow to run 20 or more times on a laptop.

**Prompt.** A system instruction tells the model to use only the numbered sources, cite each fact as [n], keep numbers and fiscal years as written, give exact dollar amounts and percentages when a source states them, read tables (flattened to one line with cells separated by |, values usually in millions), answer in at most five sentences, and reply with a fixed sentence ("The provided filings do not contain this information.") when the sources do not contain the answer. Each selected chunk is given as a numbered source headed by its company, ticker and fiscal year, followed by the original (not normalized) text, so numbers and capitalization are preserved. The question comes last, followed by a reminder to end each sentence with its source number and not to repeat the source headings.

Small models are sensitive to this wording, and several versions were tried on the same questions. Putting the chunk ID in each heading made the model copy the heading into its answer. A concrete example sentence in the instruction ("Revenue grew 10% [2].") was copied into two answers. Headings without square brackets ("Source 1") made it invent source numbers such as [39]. The final version keeps the [n] headings, and a small post processing step rewrites the citation variants the model still produces, such as [N1] or [Source [3]], as [1] and [3]. This changes only the citation format, never the content of the answer.

**Decoding.** Greedy decoding (always the most likely next token) with a limit of 300 new tokens. This makes every run reproducible on the same machine, which the report needs. If nothing is retrieved, the model is not called at all and a fixed "no relevant passages" message is returned.

**Filters from the question.** When a question names exactly one company (NVIDIA, AMD, Microsoft, Apple, Alphabet or Google), retrieval is limited to that company's filings, and "fiscal 2025" or "FY2024" limits it to that year. This is simple keyword matching in the orchestration layer.

## Timing

Median over the 21 questions: retrieval 2.8 ms (at most 5.8 ms), selection 0.09 ms, and generation 2.9 s (the model is loaded before the first question, so loading time is not counted). Answer generation takes about a thousand times longer than the string algorithms, so retrieval speed does not limit the system end to end. What retrieval does control is which text the model gets to see.

## Are the answers backed by the selected chunks?

Each answer was checked against its selected chunks in `reports/stage5_results.md`.

**Correct and grounded.** Questions 1, 4, 5, 8, 9, 11, 16 and 17 (NVIDIA data center revenue of $115,186 million read from the revenue by end market table, NVIDIA gaming revenue, AMD export restriction risks, Azure growth of 34%, Microsoft AI investment, iPhone net sales, YouTube ads, Alphabet antitrust matters including the €2.4 billion EC fine) are answered with facts stated in the selected chunks and cite the right source numbers. Question 21 had a fiscal year but no company; three of the four selected chunks were Microsoft's and one NVIDIA's, and the answer correctly reports only Microsoft's figures ($13.0 billion vs. $12.0 billion) without mixing the companies.

**Typo questions.** "nvidea gaming revenue" and "microsft cloud revenue" both retrieved the right company through the Levenshtein correction even though no company filter could be inferred from the misspelled name.

**Grounded but wrong.** When retrieval brings a related but different passage, the model tends to use whatever number it sees. Each number below appears in a selected chunk, so a check of "is the number in the context" would pass, yet the answer is wrong.
- *NVIDIA R&D in fiscal 2024 (question 2):* the answer says $2,532 million, which is the stock based compensation charged to R&D, not total R&D spending. The chunk with the total was not retrieved.
- *AMD data center segment (question 6):* the 2025 figure ($16.6 billion, up 32%) is right, but for 2024 the answer gives AMD's total revenue (up 14% to $25.8 billion) as if it were the segment's. The same chunk says the segment had $12.6 billion, up 94%.
- *Microsoft Cloud revenue (question 10):* the answer treats the "Intelligent Cloud" segment ($106,265 million) as if it were "Microsoft Cloud" revenue ($137.4 billion the year before).
- *ZT Systems (question 7):* only the FY2024 filing's statements were used, so the answer says the deal "is expected to close in the first half of 2025", which the FY2025 filing shows already happened. Both filings were in the context, and the model picked the older one.
- *Alphabet's sources of revenue (question 15):* the selected chunks came from the deferred revenue and cost of revenue discussion, so the answer leaves out advertising, Alphabet's largest source of revenue, and describes traffic acquisition costs (a cost) under revenue.

**Grounded but not answering the question.**
- *NVIDIA competitors (question 3):* retrieval found the word "competitors" only in export control risk paragraphs, so the answer describes competitors as "those who sell products not subject to the restrictions" instead of naming them.
- *Companies that depend on TSMC (question 18):* only AMD is named, because the selected chunks came from AMD's filings. NVIDIA and Apple also rely on TSMC, but their chunks ranked lower.
- *Vague question (question 20):* "What is the outlook?" reduces to the single word "outlook", which matched an investment impairment policy in Microsoft's filings. The model gave a fluent answer about impairment assessments that is faithful to the chunks but useless for the question.

**Correct refusals when retrieval was weak.**
- *Tesla revenue (question 19):* there is no Tesla filing in the collection. Retrieval still returned NVIDIA automotive chunks, and the model correctly said the filings do not contain the information (the 1.5B model had instead presented NVIDIA's automotive revenue as Tesla's).
- *Apple employees (question 13):* the 10-K states "approximately 166,000 full-time equivalent employees", but it says "the Company", not "Apple", and the word "many" from the question pulled in unrelated chunks, so the employee paragraph was not retrieved. The model refused rather than invent a number.
- *Apple manufacturing in China (question 14):* the selected chunks were about currency effects and component supply in general, and the model refused.

In questions 13 and 14 the model appended a stray [1] to the refusal sentence. The refusal itself is correct; the citation is meaningless and should be ignored.

## Conclusions for Stage 5

- The answer can only be as good as the selected context. When the right chunk is selected, a 3B model answers precisely and cites it. When it is not, the model either refuses (the safe case) or answers from the nearest related number (the dangerous case, five of the 21 questions).
- Citations make the second case checkable: every wrong number above can be traced to the exact chunk it came from, which is what made this analysis possible.
- Refusing when the sources are insufficient is the most valuable behavior to prompt for, and it worked on the three questions where retrieval clearly missed.
- Redundancy removal is worth having in a collection with year over year repetition: without it, 9 of the 21 contexts would have spent a quarter to half of their space on duplicate text. It does not solve the opposite problem seen in question 7, where two different years of the same topic are both kept and the model has to choose between them.
- The main failures come from retrieval, not generation: a question word missing from the passage (Apple vs. "the Company"), a broad word dominating the score ("many", "outlook"), and similar numbers in neighboring tables. Stage 6 compares how exact and approximate retrieval change these outcomes.
