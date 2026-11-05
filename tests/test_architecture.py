"""Executable module boundaries and lost-file checks."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_imports_resolve_to_source_files():
    missing = []
    for path in (ROOT / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("src."):
                target = ROOT.joinpath(*node.module.split("."))
                if not target.with_suffix(".py").exists() and not (target / "__init__.py").exists():
                    missing.append(f"{path.relative_to(ROOT)}:{node.lineno}: {node.module}")
    assert not missing, "Missing source modules:\n" + "\n".join(missing)


def test_modules_do_not_import_other_module_implementations():
    violations = []
    for path in (ROOT / "src/modules").rglob("*.py"):
        owner = path.relative_to(ROOT / "src/modules").parts[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            for name in names:
                if name.startswith("src.modules.") and name.split(".")[2] != owner:
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")
    assert not violations, "Use domain ports and composition wiring:\n" + "\n".join(violations)


def test_memory_use_cases_do_not_execute_sql():
    for path in (ROOT / "src/modules/memory/services").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                receiver = node.func.value
                if isinstance(receiver, ast.Name) and receiver.id == "session":
                    assert node.func.attr not in {"execute", "add", "add_all", "commit", "flush"}, (
                        f"Persistence belongs in a repository: {path.name}:{node.lineno}"
                    )
