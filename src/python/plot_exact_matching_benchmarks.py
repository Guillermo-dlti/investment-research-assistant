"""Generate Stage 3 exact-matching plots from benchmark CSV output."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


DEFAULT_INPUT = Path("reports/benchmarks/exact_matching_results.csv")
DEFAULT_OUTPUT_DIRECTORY = Path("reports/benchmarks")


def load_results(path: Path) -> list[dict[str, Any]]:
    """Load and type-check benchmark rows needed by the plots."""
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError("benchmark CSV contains no results")
    required = {
        "algorithm",
        "scenario_group",
        "scenario",
        "text_bytes",
        "pattern",
        "pattern_bytes",
        "match_count",
        "median_us",
        "timing_unit",
    }
    if not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0]))
        raise ValueError(f"benchmark CSV is missing columns: {', '.join(missing)}")
    converted: list[dict[str, Any]] = []
    for row in rows:
        if row["timing_unit"] != "microseconds":
            raise ValueError("plots require benchmark timings in microseconds")
        converted.append(
            {
                **row,
                "text_bytes": int(row["text_bytes"]),
                "pattern_bytes": int(row["pattern_bytes"]),
                "match_count": int(row["match_count"]),
                "median_us": float(row["median_us"]),
            }
        )
    return converted


def rows_for(
    rows: list[dict[str, Any]],
    group: str,
) -> list[dict[str, Any]]:
    selected = [row for row in rows if row["scenario_group"] == group]
    if not selected:
        raise ValueError(f"benchmark CSV has no {group} rows")
    return selected


def plot_text_sizes(rows: list[dict[str, Any]], output: Path) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows_for(rows, "text_size"):
        grouped[row["algorithm"]].append(row)
    figure, axis = plt.subplots(figsize=(8, 5))
    for algorithm, values in sorted(grouped.items()):
        values.sort(key=lambda row: row["text_bytes"])
        axis.plot(
            [row["text_bytes"] / 1024 for row in values],
            [row["median_us"] for row in values],
            marker="o",
            label=algorithm,
        )
    axis.set_title("Exact Matching Time by Financial Text Size")
    axis.set_xlabel("Text size (KiB)")
    axis.set_ylabel("Median execution time (microseconds)")
    axis.grid(alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def plot_pattern_lengths(rows: list[dict[str, Any]], output: Path) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows_for(rows, "pattern_length"):
        grouped[row["algorithm"]].append(row)
    figure, axis = plt.subplots(figsize=(8, 5))
    for algorithm, values in sorted(grouped.items()):
        values.sort(key=lambda row: row["pattern_bytes"])
        axis.plot(
            [row["pattern_bytes"] for row in values],
            [row["median_us"] for row in values],
            marker="o",
            label=algorithm,
        )
    axis.set_title("Exact Matching Time by Pattern Length")
    axis.set_xlabel("Pattern length (bytes)")
    axis.set_ylabel("Median execution time (microseconds)")
    axis.grid(alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def plot_real_collection(rows: list[dict[str, Any]], output: Path) -> None:
    selected = rows_for(rows, "real_collection")
    patterns = list(dict.fromkeys(row["pattern"] for row in selected))
    algorithms = sorted({row["algorithm"] for row in selected})
    lookup = {(row["pattern"], row["algorithm"]): row for row in selected}
    positions = list(range(len(patterns)))
    width = 0.36
    figure, axis = plt.subplots(figsize=(10, 5.5))
    for algorithm_index, algorithm in enumerate(algorithms):
        offset = (algorithm_index - (len(algorithms) - 1) / 2) * width
        axis.bar(
            [position + offset for position in positions],
            [lookup[(pattern, algorithm)]["median_us"] / 1000 for pattern in patterns],
            width=width,
            label=algorithm,
        )
    labels = [
        f"{pattern}\n({lookup[(pattern, algorithms[0])]['match_count']} matches)"
        for pattern in patterns
    ]
    axis.set_title("Full Financial Collection Exact-Matching Time")
    axis.set_xlabel("Pattern")
    axis.set_ylabel("Median execution time (milliseconds)")
    axis.set_xticks(positions, labels, rotation=12, ha="right")
    axis.grid(axis="y", alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rows = load_results(args.input)
        args.output_directory.mkdir(parents=True, exist_ok=True)
        outputs = [
            args.output_directory / "exact_matching_by_text_size.png",
            args.output_directory / "exact_matching_by_pattern_length.png",
            args.output_directory / "exact_matching_real_collection.png",
        ]
        plot_text_sizes(rows, outputs[0])
        plot_pattern_lengths(rows, outputs[1])
        plot_real_collection(rows, outputs[2])
    except (OSError, ValueError) as error:
        print(f"Could not generate benchmark plots: {error}")
        return 1
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
