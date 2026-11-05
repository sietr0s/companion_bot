"""Audit installed packages and explicitly audit PyTorch's public CPU release version."""

from __future__ import annotations

import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/security"


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    for name in ["python-audit.json", "torch-upstream-audit.json"]:
        (REPORTS / name).unlink(missing_ok=True)
    installed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--progress-spinner",
            "off",
            "--format",
            "json",
            "--output",
            str(REPORTS / "python-audit.json"),
        ],
        check=False,
    )
    data = json.loads((REPORTS / "python-audit.json").read_text())
    skipped = {row["name"] for row in data["dependencies"] if row.get("skip_reason")}
    if skipped - {"torch"}:
        print(f"ERROR: unaudited packages: {sorted(skipped - {'torch'})}", file=sys.stderr)
        return 1
    # The CPU wheel has a PEP 440 local suffix, which PyPI's advisory catalog does
    # not index. Audit the same public release separately, without installing it.
    public_version = version("torch").split("+", 1)[0]
    requirement = REPORTS / "torch-upstream-requirement.txt"
    requirement.write_text(f"torch=={public_version}\n")
    upstream = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--progress-spinner",
            "off",
            "--disable-pip",
            "--no-deps",
            "-r",
            str(requirement),
            "--format",
            "json",
            "--output",
            str(REPORTS / "torch-upstream-audit.json"),
        ],
        check=False,
    )
    upstream_data = json.loads((REPORTS / "torch-upstream-audit.json").read_text())
    if any(row.get("skip_reason") for row in upstream_data["dependencies"]):
        print("ERROR: the PyTorch public release could not be audited", file=sys.stderr)
        return 1
    return int(bool(installed.returncode or upstream.returncode))


if __name__ == "__main__":
    raise SystemExit(main())
