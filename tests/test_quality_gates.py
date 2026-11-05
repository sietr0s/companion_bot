"""Quality gates must reject regressions and tool failures, not just emit reports."""

from subprocess import CompletedProcess

import pytest

from scripts.coverage_gate import coverage_values, violations
from scripts.quality_report import Finding, complexity_blocks, regressions, run_tool, snapshot


def test_ratchet_detects_new_issues_duplicate_occurrences_and_worsened_complexity():
    original = Finding("mypy", "src/example.py", "type-arg", "Missing type arguments")
    complexity = Finding("complexity", "src/example.py", "cyclomatic", "process", 12)
    baseline = snapshot([original, complexity])
    assert not regressions(snapshot([original, complexity]), baseline)
    assert not regressions(snapshot([original]), baseline)
    new = Finding("mypy", "src/example.py", "arg-type", "Wrong argument type")
    worse = Finding("complexity", "src/example.py", "cyclomatic", "process", 13)
    problems = regressions(snapshot([original, original, new, worse]), baseline)
    assert len(problems) == 3
    assert not regressions(
        snapshot([original, Finding("complexity", "src/example.py", "cyclomatic", "process", 11)]),
        baseline,
    )


def test_missing_analyzer_is_not_interpreted_as_a_clean_report(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.quality_report.REPORTS", tmp_path)
    monkeypatch.setattr(
        "scripts.quality_report.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(
            args=[], returncode=1, stdout="", stderr="No module named mypy"
        ),
    )
    with pytest.raises(RuntimeError, match="no findings"):
        run_tool("mypy", ["python", "-m", "mypy"], (0, 1))


def test_analyzer_crash_is_not_accepted_as_existing_quality_debt(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.quality_report.REPORTS", tmp_path)
    monkeypatch.setattr(
        "scripts.quality_report.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(
            args=[], returncode=2, stdout="partial report", stderr="crashed"
        ),
    )
    with pytest.raises(RuntimeError, match="failed"):
        run_tool("mypy", ["python", "-m", "mypy"], (0, 1))


def test_complexity_includes_nested_callbacks():
    blocks = [
        {
            "type": "method",
            "classname": "Service",
            "name": "register",
            "complexity": 1,
            "closures": [{"type": "function", "name": "handler", "complexity": 15}],
        }
    ]
    assert complexity_blocks(blocks) == {"Service.register": 1, "Service.register.handler": 15}


def test_backend_line_and_branch_metrics_have_independent_gates():
    values = coverage_values(
        {
            "totals": {
                "percent_covered": 80,
                "percent_statements_covered": 90,
                "percent_branches_covered": 50,
            }
        },
        "backend",
    )
    failures = violations(
        values, "backend", {"backend_minimum_coverage": 79, "backend_minimum_branch_coverage": 60}
    )
    assert failures == ["branches: 50.00% < 60%"]


def test_frontend_reports_all_source_coverage_instead_of_only_imported_utilities():
    values = coverage_values({"total": {"lines": {"pct": 12}, "branches": {"pct": 20}}}, "frontend")
    assert (
        len(
            violations(
                values,
                "frontend",
                {"frontend_minimum_line_coverage": 13, "frontend_minimum_branch_coverage": 21},
            )
        )
        == 2
    )
