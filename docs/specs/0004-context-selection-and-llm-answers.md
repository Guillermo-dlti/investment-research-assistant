# 0004. Context selection in C++ and local Hugging Face answers

**Date**: 2026-10-19
**Status**: In Progress

## Summary

Stage 5 turns ranked chunks into an answer. Retrieval (approximate by default, exact on request) returns the top 10 chunks. A new C++ greedy selector walks them in score order and keeps a chunk only if it fits a word budget, is not a near duplicate of a chunk already kept (word n gram Jaccard, reusing spec 0002), and the chunk limit is not reached. The kept chunks, with their original text and filing metadata, become numbered sources in a prompt for `Qwen/Qwen2.5-3B-Instruct`, run locally with `transformers` and greedy decoding. The model answers only from those sources and cites them as `[n]`. A script runs 20 fixed questions and saves everything the brief asks for under `reports/`.

## Context

The brief (Stage 5) asks for a pretrained Hugging Face model, no training, that answers from the question plus a limited selection of the retrieved chunks. It suggests top k, a word or token limit, dropping redundant chunks, and favoring chunks with many query terms. The required flow is question → search → retrieval → context selection → model → answer, and at least 20 questions must be shown, each with the selected chunks, the answer and the retrieval time. The report must say whether answers are backed by the chunks and what happens when retrieval is weak.

The data matters here. FY2024 and FY2025 10-Ks of the same company repeat whole paragraphs (risk factors, business descriptions), so the top 10 often holds two near copies of the same text. Chunks are about 250 words with 40 words of overlap. The approximate score (spec 0003) already rewards query term coverage, so "favor chunks with several query terms" is covered by using its order. Project rules put every algorithm in C++ and keep Python to orchestration. The machine is an Apple M4 Pro with 24 GB and MPS.

## Requirements

**Acceptance criteria**:
- **AC-1**: `select_context` (C++) returns, for the given candidates, a decision per candidate (`selected`, `redundant`, `over_budget` or `limit`) and the selected IDs. Selected chunks never exceed `max_chunks`, their summed `word_count` never exceeds `word_budget`, and no two selected chunks have Jaccard similarity at or above `redundancy_threshold`.
- **AC-2**: Selection is greedy in score descending, then `chunk_id` ascending order, and deterministic. An over budget chunk is skipped, not a stop, so a later shorter chunk can still fit. Unknown or duplicate IDs, `redundancy_threshold` outside (0, 1], or `max_chunks` of 0 raise `ValueError`.
- **AC-3**: `ResearchAssistant.ask(question)` runs search → selection → prompt → model and returns the question, mode, filters, retrieval time and candidate count, every selection decision, the selected chunks with original text and citation metadata (`chunk_id`, company, ticker, fiscal year, filing date, source URL), the answer, the generation time, and the source numbers the answer cites.
- **AC-4**: The prompt numbers each selected chunk `[1]..[n]` with its company, ticker and fiscal year (the `chunk_id` stays in the returned metadata; in the prompt the model copied it into answers), and tells the model to answer only from them, cite `[n]`, and say it cannot find the answer when the sources do not contain it. When nothing is retrieved the model is not called and a fixed "no relevant passages" answer is returned.
- **AC-5**: The model is a pretrained Hugging Face model loaded lazily (only on the first answer) with greedy decoding, so the same question gives the same answer on the same machine. The model name is a parameter; the default is `Qwen/Qwen2.5-3B-Instruct`.
- **AC-6**: Company names in the question (NVIDIA, AMD, Microsoft, Apple, Alphabet or Google) set the `ticker` filter when exactly one company is named, and `fiscal 2024`, `fiscal year 2025` or `FY2025` sets `fiscal_year`. Explicit arguments win, and inference can be turned off.
- **AC-7**: `python -m src.python.run_questions` runs at least 20 questions (including a typo, an out of corpus and a vague question) and writes `reports/stage5_results.json` and `reports/stage5_results.md` with, per question, the selected chunks, the answer and the retrieval time.
- **AC-8**: The new C++ code follows the area convention (library target, named CTests, demo, binding, Python tests). Python tests use a fake generator, so they never download a model. All existing tests still pass.

## Options considered

### Option 1: Greedy budgeted selection with Jaccard redundancy in C++ (chosen)
Walk candidates by score; keep a chunk if under the chunk limit, under the word budget, and below the redundancy threshold against every kept chunk.
- Pros: reuses `JaccardIndex` n gram sets; explainable per chunk; O(c · k · g) with c ≤ 10, k ≤ 4.
- Cons: greedy is not the optimal knapsack, which does not matter at this size.

### Option 2: Plain top k in Python
- Pros: trivial.
- Cons: sends near duplicate FY2024/FY2025 paragraphs twice, has no budget, and puts selection logic in Python against the project rule.

### Option 3: Maximal marginal relevance (score minus λ · similarity)
- Pros: a smooth trade off between relevance and novelty.
- Cons: one more weight to justify, and scores from spec 0003 are relative to the candidate set, so mixing them with Jaccard is hard to explain.

### Model choice
| Model | Why not / why |
|---|---|
| `google/flan-t5-base` | Fast, but short and often ungrounded answers on long financial context; 512 token input limit. |
| `Qwen/Qwen2.5-0.5B-Instruct` | Very fast, but weaker at quoting numbers and citing sources. |
| `Qwen/Qwen2.5-1.5B-Instruct` | Planned first. Tried on four questions: right on simple numbers, but almost never cited `[n]` and attributed NVIDIA automotive revenue to Tesla. |
| **`Qwen/Qwen2.5-3B-Instruct`** | Chosen after that trial. Cites sources on most questions, refuses when the sources lack the answer, about 6 GB, about 3.7 s per answer on MPS. |
| 7B models | Better answers, but 15 GB of weights and slow on a laptop for 20+ runs. |

## Decision

Option 1, with `max_chunks = 4`, `word_budget = 1100`, `redundancy_threshold = 0.5` and 10 retrieved candidates, and `Qwen/Qwen2.5-3B-Instruct` with greedy decoding and `max_new_tokens = 300`.

## Rationale

Four chunks of about 250 words fill roughly 1,000 words (about 1,400 tokens), which keeps answers fast and focused while leaving room for multi part questions. A Jaccard of 0.5 on word 1 and 2 grams only fires for genuinely repeated text (the year over year copies), not for neighbors that share 40 overlap words. Greedy decoding makes the 20 question run reproducible, which the report needs. The 1.5B model was replaced by the 3B one after a four question trial (see Model choice): grounding and refusals matter more for the report than a second of speed.

## Feature design

**Pipeline** (`src/python/research_assistant.py`):
1. Infer filters from the question unless given or disabled (AC-6).
2. Retrieve: `approximate_search(top_k=10)` or, in exact mode, the ranked AND then OR term frequency search used by `compare_search`. Time it.
3. Build `ContextCandidate(chunk_id, score, word_count)` from the results and the original chunk word counts; call C++ `select_context`. Time it.
4. Build chat messages: a system rule and the numbered sources with original text.
5. Generate with the injected generator (default Hugging Face). Rewrite citation variants (`[N1]`, `[Source [1]]`) as `[1]`, then parse `[n]` citations in range.

**Interfaces**:
| Name | Kind | Input | Output | Errors |
|---|---|---|---|---|
| `JaccardIndex.chunk_similarity` (additive) | C++ + binding | two chunk IDs | Jaccard of their n gram sets | unknown ID |
| `JaccardIndex.has_chunk` (additive) | C++ + binding | chunk ID | bool | none |
| `investment_engine.select_context` | C++ binding | `JaccardIndex`, `list[ContextCandidate]`, `max_chunks`, `word_budget`, `redundancy_threshold` | `ContextSelection {decisions, selected_ids, total_words}` | `ValueError` per AC-2 |
| `SearchEngine.exact_ranked_search` (additive) | method | `query`, `ticker`, `fiscal_year`, `top_k` | `(results, mode, candidate_count)` | same as `compare_search` |
| `ResearchAssistant.ask` | method | `question`, `mode="approximate"`, `ticker`, `fiscal_year`, `auto_filters=True` | dict per AC-3 | `ValueError` for an unknown mode |
| `HuggingFaceGenerator.generate` | method | chat messages | answer text | model load errors |

**Key invariants**: the model never sees text outside the selected chunks; `chunk_id` links every source back to its filing; selection never reorders scores.

**Critical test scenarios**: hand built C++ fixtures for budget skip, redundancy, limit, tie break and validation (AC-1, AC-2); a synthetic collection with a fake generator for the prompt, citations, empty retrieval and filter inference (AC-3, AC-4, AC-6); a real data check that NVDA questions select NVDA chunks under budget (AC-1, AC-3).

## Build plan

1. Add `JaccardIndex::chunkSimilarity` and `hasChunk` with CTests (AC-1, AC-8)
2. Add `src/cpp/context_selection.h/.cpp`, `context_selection_core`, named CTests and `context_selection_demo` (AC-1, AC-2, AC-8)
3. Bind `ContextCandidate`, `ContextDecision`, `ContextSelection`, `select_context` and the new Jaccard methods (AC-8)
4. Add `SearchEngine.exact_ranked_search` and have `compare_search` reuse it (AC-3)
5. Add `src/python/research_assistant.py` with filter inference, prompt, citations and the lazy Hugging Face generator (AC-3 to AC-6)
6. Add `tests/test_context_selection.py` and `tests/test_research_assistant.py` with a fake generator (AC-1 to AC-6, AC-8)
7. Add `src/python/run_questions.py`, run it, and commit `reports/stage5_results.{json,md}` (AC-7)
8. Write `reports/stage5_notes.md`: selection strategy, model choice, grounding analysis, weak retrieval cases; no code

## Consequences

**Positive**: one call goes from question to cited answer, ready for the GUI and the Stage 6 comparison; duplicate year over year text no longer wastes the context.

**Negative / tradeoffs**: a 3B model can still misread tables or mix fiscal years (seen in the run: stock based R&D compensation reported as total R&D); filter inference is keyword based and misses indirect mentions ("the GPU maker"); the first answer pays a model load of a few seconds; `torch` and `transformers` are large dependencies.

## Follow-up

- [ ] The word budget never fired in the run (4 chunks of at most 250 words always fit); revisit if chunk size grows.
- [ ] "many" and "much" are not stopwords, which hurt "How many employees does Apple have?"; consider adding them in a Stage 4 follow up (changes spec 0003 behavior).
- [ ] Stage 6 runs the same questions with `mode="exact"` and `mode="approximate"` and compares answers.
