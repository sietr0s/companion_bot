"""Run analyzers, publish actionable reports, and reject new/worsened quality debt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/quality"


@dataclass(frozen=True)
class Finding:
    tool: str
    path: str
    rule: str
    message: str
    score: float = 1

    def key(self) -> str:
        return json.dumps([self.tool, self.path, self.rule, self.message], ensure_ascii=False)


def relative_path(value: str) -> str:
    path = Path(value)
    return (
        path.relative_to(ROOT).as_posix()
        if path.is_absolute()
        else path.as_posix().removeprefix("./")
    )


def run_tool(name: str, command: list[str], expected_codes: tuple[int, ...]) -> str:
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, timeout=300, check=False
    )
    (REPORTS / f"{name}.stdout").write_text(result.stdout, encoding="utf-8")
    (REPORTS / f"{name}.stderr").write_text(result.stderr, encoding="utf-8")
    if result.returncode not in expected_codes:
        raise RuntimeError(
            f"{name} failed ({result.returncode}); inspect reports/quality/{name}.stderr"
        )
    if result.returncode and not result.stdout.strip():
        raise RuntimeError(f"{name} returned no findings; inspect reports/quality/{name}.stderr")
    return result.stdout


def type_findings() -> list[Finding]:
    output = run_tool("mypy", [sys.executable, "-m", "mypy", "src", "--output", "json"], (0, 1))
    rows = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
    return [
        Finding("mypy", relative_path(row["file"]), row["code"], row["message"])
        for row in rows
        if row["severity"] == "error"
    ]


def security_findings() -> list[Finding]:
    output = run_tool(
        "bandit", [sys.executable, "-m", "bandit", "-r", "src", "-f", "json", "-q"], (0, 1)
    )
    report = json.loads(output)
    if report["errors"]:
        raise RuntimeError("Bandit could not scan all files")
    return [
        Finding(
            "bandit",
            relative_path(row["filename"]),
            row["test_id"],
            f"{row['issue_severity']}: {row['issue_text']}",
        )
        for row in report["results"]
    ]


def dead_code_findings(policy: dict[str, Any]) -> list[Finding]:
    output = run_tool(
        "vulture",
        [
            sys.executable,
            "-m",
            "vulture",
            "src",
            "--min-confidence",
            str(policy["vulture_minimum_confidence"]),
        ],
        (0, 3),
    )
    findings = []
    for line in output.splitlines():
        match = re.fullmatch(r"(.+?):\d+: (.+)", line)
        if not match:
            raise RuntimeError(f"Unexpected Vulture output: {line}")
        findings.append(Finding("vulture", relative_path(match[1]), "unused", match[2]))
    return findings


def complexity_blocks(blocks: list[dict[str, Any]], parent: str = "") -> dict[str, float]:
    values = {}
    for block in blocks:
        name = ".".join(filter(None, [parent or block.get("classname", ""), block["name"]]))
        if block["type"] in {"function", "method"}:
            values[name] = block["complexity"]
        values.update(complexity_blocks(block.get("methods", []), name))
        values.update(complexity_blocks(block.get("closures", []), name))
    return values


def complexity_findings(policy: dict[str, Any]) -> list[Finding]:
    output = run_tool("complexity", [sys.executable, "-m", "radon", "cc", "src", "-j"], (0,))
    findings = []
    for path, blocks in json.loads(output).items():
        if not isinstance(blocks, list):
            raise RuntimeError(f"Radon could not scan {path}")
        for name, score in complexity_blocks(blocks).items():
            if score > policy["maximum_function_complexity"]:
                findings.append(
                    Finding("complexity", relative_path(path), "cyclomatic", name, score)
                )
    return findings


def maintainability_findings(policy: dict[str, Any]) -> list[Finding]:
    output = run_tool("maintainability", [sys.executable, "-m", "radon", "mi", "src", "-j"], (0,))
    findings = []
    for path, row in json.loads(output).items():
        if "mi" not in row:
            raise RuntimeError(f"Radon could not scan {path}")
        if row["mi"] < policy["minimum_maintainability_index"]:
            findings.append(
                Finding(
                    "maintainability",
                    relative_path(path),
                    "low-mi",
                    "Maintainability index",
                    100 - row["mi"],
                )
            )
    return findings


def duplicate_findings(binary: str) -> list[Finding]:
    run_tool("jscpd", [binary, "--config", ".jscpd.json"], (0,))
    data = json.loads((REPORTS / "duplicates/jscpd-report.json").read_text())
    findings = []
    for clone in data["duplicates"]:
        paths = sorted(relative_path(clone[name]["name"]) for name in ["firstFile", "secondFile"])
        fragment = re.sub(r"\s+", " ", clone["fragment"]).strip()
        digest = hashlib.sha256(fragment.encode()).hexdigest()[:16]
        findings.append(
            Finding(
                "duplication",
                " <-> ".join(paths),
                digest,
                f"Duplicate {clone['format']} block",
                clone["lines"],
            )
        )
    return findings


def snapshot(findings: list[Finding]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for finding in findings:
        key = finding.key()
        if key not in records:
            records[key] = {**asdict(finding), "count": 0}
        records[key]["count"] += 1
        records[key]["score"] = max(records[key]["score"], finding.score)
    return records


def regressions(
    current: dict[str, dict[str, Any]], baseline: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        record
        for key, record in current.items()
        if key not in baseline
        or record["count"] > baseline[key]["count"]
        or record["score"] > baseline[key]["score"] + 0.000001
    ]


def markdown(
    current: dict[str, dict[str, Any]], failures: list[dict[str, Any]], errors: list[str]
) -> str:
    counts = Counter()
    for record in current.values():
        counts[record["tool"]] += record["count"]
    lines = ["## Code quality", "", "| Analyzer | Current findings |", "| --- | ---: |"]
    lines.extend(
        f"| {tool} | {counts[tool]} |"
        for tool in ["mypy", "bandit", "vulture", "complexity", "maintainability", "duplication"]
    )
    lines += [
        "",
        f"New/worsened findings: **{len(failures)}**. Analyzer failures: **{len(errors)}**.",
        "",
        "Existing findings remain visible in findings.json and raw reports; a passing ratchet does not mean zero debt.",
        "",
        "### New or worsened findings",
        "",
    ]
    lines.extend(
        f"- `{row['tool']}` `{row['path']}`: {row['message']} (score {row['score']}, count {row['count']})"
        for row in failures
    )
    lines.extend(f"- ERROR: {error}" for error in errors)
    lines += [
        "",
        "### Most complex functions",
        "",
        "| File | Function | Complexity |",
        "| --- | --- | ---: |",
    ]
    complex_rows = sorted(
        (r for r in current.values() if r["tool"] == "complexity"),
        key=lambda r: r["score"],
        reverse=True,
    )
    lines.extend(
        f"| `{row['path']}` | `{row['message']}` | {row['score']} |" for row in complex_rows[:15]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Explicitly replace reviewed quality debt; never run automatically in CI",
    )
    parser.add_argument("--jscpd", default=str(ROOT / "frontend/node_modules/.bin/jscpd"))
    args = parser.parse_args()
    if args.update_baseline and os.environ.get("CI"):
        parser.error("CI must not rewrite the baseline")
    REPORTS.mkdir(parents=True, exist_ok=True)
    policy = json.loads((ROOT / "quality-policy.json").read_text())
    findings: list[Finding] = []
    errors = []
    collectors = [
        type_findings,
        security_findings,
        lambda: dead_code_findings(policy),
        lambda: complexity_findings(policy),
        lambda: maintainability_findings(policy),
        lambda: duplicate_findings(args.jscpd),
    ]
    for collect in collectors:
        try:
            findings.extend(collect())
        except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
            errors.append(str(error))
    current = snapshot(findings)
    baseline_path = ROOT / "quality-baseline.json"
    if args.update_baseline and not errors:
        baseline_path.write_text(
            json.dumps(
                {"schema_version": 1, "findings": list(current.values())},
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    baseline = snapshot([])
    if baseline_path.exists():
        records = json.loads(baseline_path.read_text())["findings"]
        baseline = {
            Finding(
                **{key: record[key] for key in ["tool", "path", "rule", "message", "score"]}
            ).key(): record
            for record in records
        }
    else:
        errors.append(
            "Missing quality-baseline.json; initialize it explicitly after reviewing findings"
        )
    failures = regressions(current, baseline)
    (REPORTS / "findings.json").write_text(
        json.dumps(
            {"findings": list(current.values()), "regressions": failures, "errors": errors},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    report = markdown(current, failures, errors)
    (REPORTS / "summary.md").write_text(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as handle:
            handle.write(report)
    print(report)
    return int(bool(failures or errors))


if __name__ == "__main__":
    raise SystemExit(main())
