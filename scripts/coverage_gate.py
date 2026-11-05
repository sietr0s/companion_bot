"""Display coverage in CI and enforce independently configured line/branch floors."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def coverage_values(report: dict, kind: str) -> dict[str, float]:
    if kind == "backend":
        total = report["totals"]
        return {
            "combined": total["percent_covered"],
            "lines": total["percent_statements_covered"],
            "branches": total["percent_branches_covered"],
        }
    return {key: report["total"][key]["pct"] for key in ["lines", "branches"]}


def violations(values: dict[str, float], kind: str, policy: dict) -> list[str]:
    limits = {
        "backend": {
            "combined": "backend_minimum_coverage",
            "branches": "backend_minimum_branch_coverage",
        },
        "frontend": {
            "lines": "frontend_minimum_line_coverage",
            "branches": "frontend_minimum_branch_coverage",
        },
    }
    return [
        f"{metric}: {values[metric]:.2f}% < {policy[key]}%"
        for metric, key in limits[kind].items()
        if values[metric] < policy[key]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["backend", "frontend"])
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    values = coverage_values(json.loads(args.report.read_text()), args.kind)
    if not all(isinstance(value, int | float) and 0 <= value <= 100 for value in values.values()):
        raise ValueError("Invalid or missing coverage measurements")
    if (
        args.kind == "backend"
        and json.loads(args.report.read_text())["totals"]["num_statements"] == 0
    ):
        raise ValueError("No backend source measured")
    if (
        args.kind == "frontend"
        and json.loads(args.report.read_text())["total"]["lines"]["total"] == 0
    ):
        raise ValueError("No frontend source measured")
    policy = json.loads((ROOT / "quality-policy.json").read_text())
    failures = violations(values, args.kind, policy)
    summary = f"## {args.kind.title()} coverage\n\n" + "\n".join(
        f"- {key}: **{value:.2f}%**" for key, value in values.items()
    )
    summary += (
        "\n\n"
        + ("FAILED: " + "; ".join(failures) if failures else "Coverage floors passed.")
        + "\n"
    )
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as handle:
            handle.write(summary)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
