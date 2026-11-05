"""Publish complete dependency-audit counts; failures remain owned by the audit commands."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    lines = ["## Dependency security", ""]
    errors = []
    for name in ["python", "npm"]:
        path = ROOT / f"reports/security/{name}-audit.json"
        try:
            report = json.loads(path.read_text())
            if name == "python":
                affected = [row for row in report["dependencies"] if row.get("vulns")]
                skipped = [row for row in report["dependencies"] if row.get("skip_reason")]
                lines.append(
                    f"- Python: **{sum(len(row['vulns']) for row in affected)}** known advisories in {len(affected)} packages."
                )
                for row in affected:
                    ids = ", ".join(issue["id"] for issue in row["vulns"])
                    lines.append(f"  - `{row['name']}=={row['version']}`: {ids}")
                for row in skipped:
                    lines.append(f"  - NOT AUDITED: `{row['name']}` — {row['skip_reason']}")
                upstream_path = ROOT / "reports/security/torch-upstream-audit.json"
                upstream = json.loads(upstream_path.read_text())
                for row in upstream["dependencies"]:
                    ids = ", ".join(issue["id"] for issue in row.get("vulns", []))
                    lines.append(
                        f"  - CPU wheel fallback: public `{row['name']}=={row['version']}`: {ids or 'no known advisories'}."
                    )
                lines.append(
                    "  - The public-release audit does not attest to the CPU binary's supply chain."
                )
            else:
                counts = report["metadata"]["vulnerabilities"]
                lines.append(
                    "- npm: "
                    + ", ".join(
                        f"**{counts[level]} {level}**"
                        for level in ["critical", "high", "moderate", "low"]
                    )
                )
                lines.append(
                    "  - High/critical findings fail CI; all lower-severity findings remain in the artifact."
                )
        except (OSError, ValueError, KeyError) as error:
            errors.append(f"{name} audit unavailable: {error}")
    lines.extend(f"- ERROR: {message}" for message in errors)
    summary = "\n".join(lines) + "\n"
    destination = ROOT / "reports/security/summary.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(summary)
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as handle:
            handle.write(summary)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
