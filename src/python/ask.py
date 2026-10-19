"""Ask one question from the command line and print the cited answer."""

from __future__ import annotations

import argparse

from src.python.research_assistant import DEFAULT_MODEL, HuggingFaceGenerator, ResearchAssistant


def main() -> int:
    parser = argparse.ArgumentParser(description="Answer a question from the 10-K filings.")
    parser.add_argument("question")
    parser.add_argument("--mode", choices=("approximate", "exact"), default="approximate")
    parser.add_argument("--ticker")
    parser.add_argument("--fiscal-year", type=int)
    parser.add_argument("--no-auto-filters", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    assistant = ResearchAssistant(generator=HuggingFaceGenerator(args.model))
    result = assistant.ask(
        args.question,
        mode=args.mode,
        ticker=args.ticker,
        fiscal_year=args.fiscal_year,
        auto_filters=not args.no_auto_filters,
    )
    print(f"Filters: {result['filters']}")
    print(
        f"Retrieval: {result['retrieval']['time_ms']:.2f} ms, "
        f"{result['retrieval']['candidate_count']} candidates"
    )
    for decision in result["context"]["decisions"]:
        print(f"  {decision['rank']:2}. {decision['chunk_id']} {decision['score']:.3f} {decision['status']}")
    print(f"\n{result['answer']}\n")
    for number, source in enumerate(result["context"]["selected"], 1):
        print(f"[{number}] {source['company']} 10-K FY{source['fiscal_year']} {source['chunk_id']} {source['source_url']}")
    print("\nEducational project output, not financial advice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
