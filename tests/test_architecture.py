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


def imported_targets(path):
    import importlib.util

    package = ".".join(path.relative_to(ROOT).with_suffix("").parts[:-1])
    if path.name == "__init__.py":
        package = ".".join(path.parent.relative_to(ROOT).parts)
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            target = importlib.util.resolve_name(name, package) if node.level else name
            yield target
            for alias in node.names:
                candidate = target + "." + alias.name
                local = ROOT.joinpath(*candidate.split("."))
                if local.exists() or local.with_suffix(".py").exists():
                    yield candidate
        elif isinstance(node, ast.Call) and node.args:
            function = (
                node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            )
            if (
                function in {"import_module", "__import__"}
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                yield node.args[0].value


def test_module_boundaries_also_cover_relative_and_lazy_imports():
    violations = []
    for path in (ROOT / "src/modules").rglob("*.py"):
        owner = path.relative_to(ROOT / "src/modules").parts[0]
        for target in imported_targets(path):
            if target.startswith("src.modules.") and target.split(".")[2] != owner:
                violations.append(f"{path.relative_to(ROOT)} imports {target}")
    assert not violations, "\n".join(violations)


def test_shared_layers_never_depend_on_application_modules_or_composition():
    violations = []
    for folder in ["base", "core", "bus", "domain", "utils"]:
        for path in (ROOT / "src" / folder).rglob("*.py"):
            for target in imported_targets(path):
                if target.startswith(("src.modules", "src.composition", "src.main")):
                    violations.append(f"{path.relative_to(ROOT)} imports {target}")
    assert not violations, "\n".join(violations)


def test_services_and_access_levels_have_one_canonical_layout():
    for module in (ROOT / "src/modules").iterdir():
        if not module.is_dir() or module.name.startswith("_"):
            continue
        assert not ((module / "service.py").exists() and (module / "services").is_dir()), module
        routers = module / "routers"
        if not routers.exists():
            continue
        for path in routers.glob("*.py"):
            assert path.stem in {"__init__", "public", "internal", "manager"}, path
        for level in ["public", "internal", "manager"]:
            assert not ((routers / f"{level}.py").exists() and (routers / level).is_dir()), routers
            if (routers / level).is_dir():
                entities = [p for p in (routers / level).glob("*.py") if p.name != "__init__.py"]
                assert len(entities) > 1, f"One entity should use {level}.py: {routers}"


def test_memory_domain_and_inner_services_do_not_import_orm_or_transport_dtos():
    domain = ROOT / "src/modules/memory/domain.py"
    for target in imported_targets(domain):
        assert not target.startswith(
            (
                "sqlalchemy",
                "fastapi",
                "src.modules.memory.models",
                "src.modules.memory.schemas",
                "src.modules.memory.repository",
            )
        ), target
    for path in (ROOT / "src/modules/memory/services").glob("*.py"):
        for target in imported_targets(path):
            assert target != "src.modules.memory.models", path
            assert not target.startswith("src.modules.memory.schemas.api"), path
            if path.name not in {"pipeline.py", "__init__.py"}:
                assert not target.startswith("src.modules.memory.schemas"), path
