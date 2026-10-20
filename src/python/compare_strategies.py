"""Stage 6: compare exact and approximate retrieval on one question set.

Every question runs through both search modes and the same context selection
and model. Retrieval is timed separately over several repeats, chunk
usefulness is checked against hand written evidence patterns, and a second
benchmark times both searches on smaller and larger copies of the collection.
Results go to reports/stage6_results.{json,md} and reports/stage6_*.png.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from src.python.research_assistant import (
    DEFAULT_MODEL,
    DEFAULT_SOURCE_COLLECTION,
    MODES,
    NO_CONTEXT_ANSWER,
    NOT_FOUND_ANSWER,
    HuggingFaceGenerator,
    ResearchAssistant,
)
from src.python.run_questions import QUESTIONS as STAGE5_QUESTIONS
from src.python.search_engine import DEFAULT_COLLECTION, DEFAULT_VOCABULARY, SearchEngine


# Extra questions with typos or word variations, where the modes should differ.
EXTRA_QUESTIONS = [
    ("aple iphone net sales", "typo in the company name"),
    ("nvidia reserch and developmnet expenses", "two typos in the topic words"),
    ("alphabet youtube advertisng revenue", "typo in a topic word"),
]
QUESTIONS = STAGE5_QUESTIONS + EXTRA_QUESTIONS

# A chunk is useful for a question when it belongs to the right filing and its
# original text matches every pattern (case insensitive). Questions that the
# collection cannot answer have no entry.
EVIDENCE = {
    "What was NVIDIA data center revenue in fiscal 2025?": ("NVDA", None, [r"115,186"]),
    "How much did NVIDIA spend on research and development in fiscal 2024?": (
        "NVDA", 2024, [r"research and development", r"8,675"]),
    "Who does NVIDIA consider its main competitors?": ("NVDA", None, [r"competitors", r"\bAMD\b|Intel|Broadcom"]),
    "nvidea gaming revenue": ("NVDA", None, [r"gaming revenue"]),
    "What risks does AMD describe about export restrictions to China?": ("AMD", None, [r"export", r"china"]),
    "How does AMD describe its data center segment?": ("AMD", None, [r"data center segment"]),
    "What does AMD say about the acquisition of ZT Systems?": ("AMD", None, [r"zt systems"]),
    "How much did Microsoft Azure and other cloud services revenue grow in fiscal 2025?": (
        "MSFT", 2025, [r"azure and other cloud services revenue"]),
    "What does Microsoft say about its investments in artificial intelligence?": (
        "MSFT", None, [r"artificial intelligence|\bAI\b", r"invest"]),
    "microsft cloud revenue": ("MSFT", None, [r"microsoft cloud revenue"]),
    "What does Apple say about iPhone net sales in fiscal 2025?": ("AAPL", 2025, [r"iphone net sales"]),
    "How does Apple describe its services revenue?": ("AAPL", None, [r"services net sales"]),
    "How many employees does Apple have?": ("AAPL", None, [r"full-time equivalent employees"]),
    "What risks does Apple describe about manufacturing in China?": (
        "AAPL", None, [r"china", r"manufactur|outsourcing partner"]),
    "What are Alphabet's main sources of revenue?": ("GOOGL", None, [r"google advertising", r"google cloud"]),
    "What does Google say about YouTube advertising revenue?": ("GOOGL", None, [r"youtube ads"]),
    "What legal or antitrust matters does Alphabet describe?": ("GOOGL", None, [r"antitrust|competition law"]),
    "Which companies depend on TSMC to manufacture their chips?": (None, None, [r"tsmc|taiwan semiconductor"]),
    "How did share repurchases change in fiscal 2025?": (None, 2025, [r"repurchase"]),
    "aple iphone net sales": ("AAPL", None, [r"iphone net sales"]),
    "nvidia reserch and developmnet expenses": (
        "NVDA", None, [r"research and development", r"8,675|12,914"]),
    "alphabet youtube advertisng revenue": ("GOOGL", None, [r"youtube ads"]),
}
# Facts a correct answer states. Checked as a regex on the model's answer.
EXPECTED_ANSWERS = {
    "What was NVIDIA data center revenue in fiscal 2025?": r"115,186|115\.2 billion",
    "How much did NVIDIA spend on research and development in fiscal 2024?": r"8,675|8\.7 billion",
    "How much did Microsoft Azure and other cloud services revenue grow in fiscal 2025?": r"34%",
    "How many employees does Apple have?": r"16[46],000",  # FY2024 and FY2025
    "nvidia reserch and developmnet expenses": r"8,675|12,914",
}
# Out of corpus: the right behavior is to refuse.
EXPECTED_REFUSALS = {"What is Tesla revenue from electric vehicles?"}

SCALE_FACTORS = (0.125, 0.25, 0.5, 1.0, 2.0, 4.0)
DEFAULT_REPEATS = 7
DEFAULT_JSON = Path("reports/stage6_results.json")
DEFAULT_MARKDOWN = Path("reports/stage6_results.md")
DEFAULT_FIGURES = Path("reports")
PLOT_ORDER = ("exact", "approximate")
COLORS = {"exact": "#2a78d6", "approximate": "#eb6834"}
INK = {"primary": "#1f1f1e", "secondary": "#5f5e57", "grid": "#e4e3de", "surface": "#fcfcfb"}


def evidence_chunks(sources: dict[str, dict[str, Any]], question: str) -> set[str] | None:
    """Chunk IDs that hold the evidence for a question, or None when nothing does."""
    if question not in EVIDENCE:
        return None
    ticker, year, patterns = EVIDENCE[question]
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    return {
        chunk_id
        for chunk_id, source in sources.items()
        if (ticker is None or source["ticker"] == ticker)
        and (year is None or int(source["fiscal_year"]) == year)
        and all(pattern.search(source["text"]) for pattern in compiled)
    }


def usefulness(chunk_ids: list[str], evidence: set[str] | None) -> dict[str, Any]:
    """Hit, precision and first useful rank (1 based) of a ranked chunk list."""
    if evidence is None:
        return {"hit": None, "precision": None, "first_rank": None, "useful": []}
    useful = [chunk_id for chunk_id in chunk_ids if chunk_id in evidence]
    ranks = [rank for rank, chunk_id in enumerate(chunk_ids, 1) if chunk_id in evidence]
    return {
        "hit": bool(useful),
        "precision": len(useful) / len(chunk_ids) if chunk_ids else 0.0,
        "first_rank": ranks[0] if ranks else None,
        "useful": useful,
    }


def judge_answer(question: str, answer: str) -> str:
    """Label the model's answer: refused, correct, missed fact, or answered (unchecked)."""
    refused = NOT_FOUND_ANSWER in answer or answer == NO_CONTEXT_ANSWER
    if question in EXPECTED_REFUSALS:
        return "correct refusal" if refused else "should refuse"
    if refused:
        return "refused"
    expected = EXPECTED_ANSWERS.get(question)
    if expected is None:
        return "answered"
    return "correct" if re.search(expected, answer) else "missed fact"


def overlap(first: list[str], second: list[str]) -> float:
    """Jaccard similarity of two chunk ID lists, as sets (1.0 when both are empty)."""
    a, b = set(first), set(second)
    return len(a & b) / len(a | b) if a | b else 1.0


def median_retrieval_ms(
    assistant: ResearchAssistant, question: str, mode: str, filters: dict[str, Any], repeats: int
) -> float:
    """Median search time over ``repeats`` runs after one warm up run."""
    assistant.retrieve(question, mode=mode, **filters)
    return statistics.median(
        assistant.retrieve(question, mode=mode, **filters)["time_ms"] for _ in range(repeats)
    )


def compare_question(
    assistant: ResearchAssistant, question: str, note: str, repeats: int
) -> dict[str, Any]:
    """Answer one question in both modes and measure retrieval and answers."""
    evidence = evidence_chunks(assistant.sources, question)
    entry: dict[str, Any] = {
        "question": question,
        "note": note,
        "evidence_count": None if evidence is None else len(evidence),
    }
    for mode in MODES:
        result = assistant.ask(question, mode=mode)
        retrieved = [item["chunk_id"] for item in result["retrieval"]["results"]]
        selected = [source["chunk_id"] for source in result["context"]["selected"]]
        entry["filters"] = result["filters"]
        entry[mode] = {
            "retrieval_ms": median_retrieval_ms(
                assistant, question, mode, result["filters"], repeats
            ),
            "candidate_count": result["retrieval"]["candidate_count"],
            "retrieved": retrieved,
            "selected": selected,
            "selected_words": result["context"]["total_words"],
            "retrieved_usefulness": usefulness(retrieved, evidence),
            "selected_usefulness": usefulness(selected, evidence),
            "answer": result["answer"],
            "verdict": judge_answer(question, result["answer"]),
            "cited_sources": result["cited_sources"],
            "generation_ms": result["generation_ms"],
        }
    entry["retrieved_overlap"] = overlap(entry["exact"]["retrieved"], entry["approximate"]["retrieved"])
    entry["selected_overlap"] = overlap(entry["exact"]["selected"], entry["approximate"]["selected"])
    entry["same_context"] = entry["exact"]["selected"] == entry["approximate"]["selected"]
    return entry


def summarize(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Averages per mode over the question set."""
    summary: dict[str, dict[str, Any]] = {}
    judged = [entry for entry in entries if entry["evidence_count"] is not None]
    for mode in MODES:
        sides = [entry[mode] for entry in entries]
        verdicts = [side["verdict"] for side in sides]
        summary[mode] = {
            "mean_retrieval_ms": statistics.mean(side["retrieval_ms"] for side in sides),
            "median_retrieval_ms": statistics.median(side["retrieval_ms"] for side in sides),
            "max_retrieval_ms": max(side["retrieval_ms"] for side in sides),
            "mean_candidates": statistics.mean(side["candidate_count"] for side in sides),
            "mean_retrieved": statistics.mean(len(side["retrieved"]) for side in sides),
            "mean_selected": statistics.mean(len(side["selected"]) for side in sides),
            "judged_questions": len(judged),
            "retrieved_hits": sum(entry[mode]["retrieved_usefulness"]["hit"] for entry in judged),
            "selected_hits": sum(entry[mode]["selected_usefulness"]["hit"] for entry in judged),
            "mean_selected_precision": statistics.mean(
                entry[mode]["selected_usefulness"]["precision"] for entry in judged
            ) if judged else 0.0,
            "verdicts": {verdict: verdicts.count(verdict) for verdict in sorted(set(verdicts))},
            "mean_generation_ms": statistics.mean(side["generation_ms"] for side in sides),
        }
    summary["agreement"] = {
        "mean_retrieved_overlap": statistics.mean(entry["retrieved_overlap"] for entry in entries),
        "mean_selected_overlap": statistics.mean(entry["selected_overlap"] for entry in entries),
        "same_context": sum(entry["same_context"] for entry in entries),
        "questions": len(entries),
    }
    return summary


def scaled_collection(payload: dict[str, Any], factor: float) -> dict[str, Any]:
    """A smaller (every n-th chunk) or larger (renamed copies) collection."""
    chunks = payload["chunks"]
    if factor <= 1:
        step = round(1 / factor)
        scaled = chunks[::step]
    else:
        scaled = []
        for copy in range(round(factor)):
            suffix = "" if copy == 0 else f"_COPY{copy}"
            scaled += [{**chunk, "chunk_id": chunk["chunk_id"] + suffix} for chunk in chunks]
    return {**payload, "total_chunks": len(scaled), "chunks": scaled}


def scaling_benchmark(
    vocabulary: Path,
    collection: Path,
    questions: list[str],
    factors: tuple[float, ...] = SCALE_FACTORS,
    repeats: int = 3,
) -> list[dict[str, Any]]:
    """Time both searches, without filters, on scaled copies of the collection."""
    payload = json.loads(collection.read_text(encoding="utf-8"))
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        for factor in factors:
            path = Path(directory) / f"collection_{factor}.json"
            scaled = scaled_collection(payload, factor)
            path.write_text(json.dumps(scaled), encoding="utf-8")
            engine = SearchEngine(vocabulary, path)
            row: dict[str, Any] = {"factor": factor, "chunks": scaled["total_chunks"]}
            for mode in MODES:
                times, candidates = [], []
                for question in questions:
                    search = _search_function(engine, mode)
                    search(question)
                    runs = []
                    for _ in range(repeats):
                        elapsed, count = search(question)
                        runs.append(elapsed)
                    times.append(statistics.median(runs))
                    candidates.append(count)
                row[mode] = {
                    "mean_ms": statistics.mean(times),
                    "mean_candidates": statistics.mean(candidates),
                }
            rows.append(row)
            print(
                f"x{factor:<5} {row['chunks']:>6} chunks: exact {row['exact']['mean_ms']:.2f} ms, "
                f"approximate {row['approximate']['mean_ms']:.2f} ms"
            )
    return rows


def _search_function(engine: SearchEngine, mode: str):
    def run(question: str) -> tuple[float, int]:
        start = time.perf_counter()
        if mode == "exact":
            _, _, count = engine.exact_ranked_search(question, top_k=10)
        else:
            count = len(engine.approximate_search(question, top_k=None))
        return (time.perf_counter() - start) * 1000, count

    return run


def plot_figures(
    entries: list[dict[str, Any]], scaling: list[dict[str, Any]], directory: Path
) -> list[Path]:
    """Write the three Stage 6 charts and return their paths."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": INK["surface"], "axes.facecolor": INK["surface"],
        "axes.edgecolor": INK["grid"], "axes.labelcolor": INK["secondary"],
        "xtick.color": INK["secondary"], "ytick.color": INK["secondary"],
        "text.color": INK["primary"], "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 10,
    })
    directory.mkdir(parents=True, exist_ok=True)
    paths = []

    # 1. Retrieval time per question, both modes (dot plot, one row per question).
    figure, axis = plt.subplots(figsize=(8, 0.32 * len(entries) + 1.2))
    labels = [f"{number}. {_short(entry['question'])}" for number, entry in enumerate(entries, 1)]
    rows = range(len(entries))[::-1]
    for mode, offset in (("exact", 0.12), ("approximate", -0.12)):
        axis.scatter(
            [entry[mode]["retrieval_ms"] for entry in entries], [row + offset for row in rows],
            s=36, color=COLORS[mode], label=mode, zorder=3, edgecolors=INK["surface"], linewidths=1.5,
        )
    axis.set_yticks(list(rows), labels, fontsize=8)
    axis.set_xlabel("Median retrieval time (ms)")
    axis.grid(axis="x", color=INK["grid"], linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="lower right")
    axis.set_title("Retrieval time per question", loc="left", fontsize=11)
    paths.append(_save(figure, directory / "stage6_time_per_question.png"))

    # 2. Time against collection size.
    figure, axis = plt.subplots(figsize=(7, 4))
    sizes = [row["chunks"] for row in scaling]
    for mode in PLOT_ORDER:
        values = [row[mode]["mean_ms"] for row in scaling]
        axis.plot(sizes, values, color=COLORS[mode], linewidth=2, marker="o", markersize=7,
                  markeredgecolor=INK["surface"], markeredgewidth=1.5, label=mode)
        axis.annotate(f"{mode} {values[-1]:.1f} ms", (sizes[-1], values[-1]),
                      textcoords="offset points", xytext=(-6, 8), ha="right",
                      color=INK["primary"], fontsize=9)
    axis.set_xlabel("Chunks in the collection")
    axis.set_ylabel("Mean retrieval time (ms)")
    axis.set_ylim(bottom=0)
    axis.grid(color=INK["grid"], linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="upper left")
    axis.set_title("Retrieval time against collection size", loc="left", fontsize=11)
    paths.append(_save(figure, directory / "stage6_time_vs_collection_size.png"))

    # 3. Useful chunks among the selected context, per judged question.
    judged = [(number, entry) for number, entry in enumerate(entries, 1) if entry["evidence_count"] is not None]
    figure, axis = plt.subplots(figsize=(9, 3.8))
    width = 0.38
    for index, mode in enumerate(PLOT_ORDER):
        positions = [position + (index - 0.5) * width for position in range(len(judged))]
        values = [len(entry[mode]["selected_usefulness"]["useful"]) for _, entry in judged]
        axis.bar(positions, values, width=width - 0.04, color=COLORS[mode], label=mode, zorder=3)
    axis.set_xticks(range(len(judged)), [str(number) for number, _ in judged])
    axis.set_xlabel("Question number")
    axis.set_ylabel("Useful chunks in context (of 4)")
    axis.set_ylim(0, 4.3)
    axis.grid(axis="y", color=INK["grid"], linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="upper right", ncols=2)
    axis.set_title("Context usefulness: chunks that hold the evidence", loc="left", fontsize=11)
    paths.append(_save(figure, directory / "stage6_context_usefulness.png"))
    return paths


def _save(figure: Any, path: Path) -> Path:
    import matplotlib.pyplot as plt

    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path


def _short(question: str, limit: int = 48) -> str:
    return question if len(question) <= limit else question[: limit - 1] + "…"


def to_markdown(
    entries: list[dict[str, Any]],
    summary: dict[str, dict[str, Any]],
    scaling: list[dict[str, Any]],
    settings: dict[str, Any],
) -> str:
    agreement = summary["agreement"]
    lines = [
        "# Stage 6 results: exact vs approximate retrieval",
        "",
        f"{len(entries)} questions, each run through both search modes with the same filters, "
        f"context selection (at most {settings['max_chunks']} chunks, {settings['word_budget']} words, "
        f"redundancy threshold {settings['redundancy_threshold']}) and model `{settings['model']}` "
        f"(greedy decoding). Retrieval time is the median of {settings['repeats']} runs after a warm up, "
        "in milliseconds on an Apple M4 Pro with a Release build. A chunk is *useful* when it is "
        "from the right filing and its text contains the evidence for the question "
        "(patterns listed at the end).",
        "",
        "## Summary",
        "",
        "| Measure | Exact | Approximate |",
        "|---|---|---|",
    ]
    exact, approximate = summary["exact"], summary["approximate"]
    judged = exact["judged_questions"]
    rows = [
        ("Mean retrieval time (ms)", "mean_retrieval_ms", "{:.2f}"),
        ("Median retrieval time (ms)", "median_retrieval_ms", "{:.2f}"),
        ("Slowest question (ms)", "max_retrieval_ms", "{:.2f}"),
        ("Mean candidate chunks examined", "mean_candidates", "{:.0f}"),
        ("Mean chunks retrieved (top 10)", "mean_retrieved", "{:.1f}"),
        ("Mean chunks selected as context", "mean_selected", "{:.1f}"),
        ("Mean precision of context (useful / selected)", "mean_selected_precision", "{:.2f}"),
        ("Mean generation time (ms)", "mean_generation_ms", "{:.0f}"),
    ]
    for label, key, template in rows:
        lines.append(f"| {label} | {template.format(exact[key])} | {template.format(approximate[key])} |")
    lines.append(
        f"| Questions with a useful chunk in the top 10 | {exact['retrieved_hits']} of {judged} "
        f"| {approximate['retrieved_hits']} of {judged} |"
    )
    lines.append(
        f"| Questions with a useful chunk in the context | {exact['selected_hits']} of {judged} "
        f"| {approximate['selected_hits']} of {judged} |"
    )
    for verdict in sorted(set(exact["verdicts"]) | set(approximate["verdicts"])):
        lines.append(
            f"| Answers: {verdict} | {exact['verdicts'].get(verdict, 0)} "
            f"| {approximate['verdicts'].get(verdict, 0)} |"
        )
    lines += [
        "",
        f"Agreement: the two top 10 lists share on average {agreement['mean_retrieved_overlap']:.2f} "
        f"of their chunks (Jaccard of the ID sets), the selected contexts "
        f"{agreement['mean_selected_overlap']:.2f}, and {agreement['same_context']} of "
        f"{agreement['questions']} questions got exactly the same context.",
        "",
        "![Retrieval time per question](stage6_time_per_question.png)",
        "",
        "![Context usefulness](stage6_context_usefulness.png)",
        "",
        "## Per question",
        "",
        "| # | Question | Exact ms | Approx ms | Exact cand. | Approx cand. | Top 10 overlap | "
        "Useful in context (E / A) | Exact answer | Approx answer |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for number, entry in enumerate(entries, 1):
        e, a = entry["exact"], entry["approximate"]
        useful = (
            "n/a" if entry["evidence_count"] is None
            else f"{len(e['selected_usefulness']['useful'])} / {len(a['selected_usefulness']['useful'])}"
        )
        lines.append(
            f"| {number} | {entry['question']} | {e['retrieval_ms']:.2f} | {a['retrieval_ms']:.2f} "
            f"| {e['candidate_count']} | {a['candidate_count']} | {entry['retrieved_overlap']:.2f} "
            f"| {useful} | {e['verdict']} | {a['verdict']} |"
        )
    lines += [
        "",
        "## Collection size",
        "",
        f"Both searches timed without filters on the {len(entries)} questions, on every 8th, 4th and 2nd chunk "
        "of the collection, the full collection, and 2 and 4 renamed copies of it. Times are the "
        "mean over questions of the median of 3 runs.",
        "",
        "| Chunks | Exact ms | Approx ms | Exact candidates | Approx candidates |",
        "|---|---|---|---|---|",
    ]
    for row in scaling:
        lines.append(
            f"| {row['chunks']:,} | {row['exact']['mean_ms']:.2f} | {row['approximate']['mean_ms']:.2f} "
            f"| {row['exact']['mean_candidates']:.0f} | {row['approximate']['mean_candidates']:.0f} |"
        )
    lines += ["", "![Time vs collection size](stage6_time_vs_collection_size.png)", "", "## Answers side by side"]
    for number, entry in enumerate(entries, 1):
        lines += ["", f"### {number}. {entry['question']}", ""]
        if entry["note"]:
            lines += [f"*Why this question:* {entry['note']}.", ""]
        filters = entry["filters"]
        lines.append(
            f"Filters: ticker `{filters['ticker']}`, fiscal year `{filters['fiscal_year']}`. "
            f"Evidence chunks in the collection: {entry['evidence_count'] if entry['evidence_count'] is not None else 'none'}."
        )
        for mode in MODES:
            side = entry[mode]
            useful = set(side["selected_usefulness"]["useful"])
            context = ", ".join(
                f"`{chunk_id}`" + (" (useful)" if chunk_id in useful else "") for chunk_id in side["selected"]
            ) or "none"
            lines += [
                "",
                f"**{mode.capitalize()}** ({side['retrieval_ms']:.2f} ms, {side['candidate_count']} candidates, "
                f"verdict: {side['verdict']}). Context: {context}",
                "",
                "> " + side["answer"].replace("\n", "\n> "),
            ]
    lines += ["", "## Evidence patterns", "", "| Question | Ticker | Year | Patterns (all must match) |", "|---|---|---|---|"]
    for question, (ticker, year, patterns) in EVIDENCE.items():
        shown = " and ".join(f"`{pattern}`" for pattern in patterns).replace("|", "\\|")
        lines.append(f"| {question} | {ticker or 'any'} | {year or 'any'} | {shown} |")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare exact and approximate retrieval (Stage 6).")
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--collection", type=Path, default=DEFAULT_COLLECTION)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCE_COLLECTION)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--figures", type=Path, default=DEFAULT_FIGURES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assistant = ResearchAssistant(
        args.vocabulary, args.collection, args.sources, generator=HuggingFaceGenerator(args.model)
    )
    settings = {
        "model": args.model,
        "repeats": args.repeats,
        "retrieval_top_k": assistant.retrieval_top_k,
        "max_chunks": assistant.max_chunks,
        "word_budget": assistant.word_budget,
        "redundancy_threshold": assistant.redundancy_threshold,
    }
    assistant.generator.load()

    entries = []
    for number, (question, note) in enumerate(QUESTIONS, 1):
        entry = compare_question(assistant, question, note, args.repeats)
        entries.append(entry)
        print(
            f"{number:2}. {question}\n    exact {entry['exact']['retrieval_ms']:.2f} ms "
            f"({entry['exact']['verdict']}), approximate {entry['approximate']['retrieval_ms']:.2f} ms "
            f"({entry['approximate']['verdict']}), top 10 overlap {entry['retrieved_overlap']:.2f}"
        )
    summary = summarize(entries)
    scaling = scaling_benchmark(args.vocabulary, args.collection, [question for question, _ in QUESTIONS])
    figures = plot_figures(entries, scaling, args.figures)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(
            {"settings": settings, "summary": summary, "scaling": scaling, "results": entries},
            indent=2, ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(to_markdown(entries, summary, scaling, settings), encoding="utf-8")
    print(f"Wrote {args.json}, {args.markdown} and {', '.join(map(str, figures))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
