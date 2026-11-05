"""Advisories and unrecognized dependencies must not become successful audits."""

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from scripts import audit_python


@pytest.mark.parametrize(
    "installed_issue,upstream_issue,unknown_skip",
    [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (False, False, True),
    ],
)
def test_audit_cannot_hide_advisories_or_unaudited_packages(
    monkeypatch, tmp_path, installed_issue, upstream_issue, unknown_skip
):
    monkeypatch.setattr(audit_python, "REPORTS", tmp_path)
    monkeypatch.setattr(audit_python, "version", lambda name: "2.15.0+cpu")

    def audit(command, **kwargs):
        upstream = "--no-deps" in command
        vulnerable = upstream_issue if upstream else installed_issue
        row = {"name": "torch" if upstream else "package", "version": "2.15.0", "vulns": []}
        if vulnerable:
            row["vulns"] = [{"id": "TEST-ADVISORY"}]
        if unknown_skip and not upstream:
            row["skip_reason"] = "not indexed"
        Path(command[command.index("--output") + 1]).write_text(json.dumps({"dependencies": [row]}))
        return CompletedProcess(command, int(vulnerable))

    monkeypatch.setattr(audit_python.subprocess, "run", audit)
    assert audit_python.main() == int(installed_issue or upstream_issue or unknown_skip)
