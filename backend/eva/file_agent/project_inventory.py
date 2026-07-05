from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .inspector import IGNORED_DIRS
from .path_policy import FilePathDecision, evaluate_file_path
from .understanding import detect_config_type, extract_imports_or_dependencies


KEY_NAMES = {
    "README.md",
    "LICENSE",
    ".gitignore",
    ".env.example",
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "tsconfig.json",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
}

KEY_DIRS = {"scripts", "tests", "docs", "backend", "frontend", "src", "app", "samples"}


@dataclass(frozen=True)
class ProjectInventoryItem:
    display_path: str
    kind: str
    suffix: str = ""
    size_bytes: int | None = None

    def __str__(self) -> str:
        return self.display_path


@dataclass(frozen=True)
class ProjectInventory:
    decision: FilePathDecision
    ok: bool
    items: list[ProjectInventoryItem] = field(default_factory=list)
    project_types: list[str] = field(default_factory=list)
    key_files: dict[str, list[str]] = field(default_factory=dict)
    missing_recommended_files: list[str] = field(default_factory=list)
    dependency_files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    docs_files: list[str] = field(default_factory=list)
    runtime_or_generated_dirs: list[str] = field(default_factory=list)
    skipped_count: int = 0
    truncated: bool = False
    total_items: int = 0

    def __str__(self) -> str:
        return format_project_inventory(self)


def build_project_inventory(root: str = ".", repo_root: str | Path | None = None, max_files: int = 300, max_depth: int = 4) -> ProjectInventory:
    decision = evaluate_file_path(root, repo_root=repo_root)
    if not decision.allowed or not decision.exists or not decision.is_dir:
        return ProjectInventory(decision=decision, ok=False)
    repo = Path(repo_root or Path.cwd()).resolve()
    start = Path(decision.normalized_path)
    limit = max(20, min(1000, int(max_files or 300)))
    depth_limit = max(1, min(6, int(max_depth or 4)))
    items: list[ProjectInventoryItem] = []
    runtime_dirs: list[str] = []
    skipped = 0
    truncated = False

    def walk(folder: Path, depth: int) -> None:
        nonlocal skipped, truncated
        if truncated:
            return
        if depth > depth_limit:
            return
        for child in sorted(folder.iterdir(), key=_inventory_sort_key):
            if _skip_inventory_path(child, repo):
                skipped += 1
                rel = _display(child, repo)
                if _looks_runtime_generated(rel):
                    runtime_dirs.append(rel)
                continue
            child_decision = evaluate_file_path(str(child), repo_root=repo)
            if not child_decision.allowed:
                skipped += 1
                continue
            item = ProjectInventoryItem(
                display_path=child_decision.display_path,
                kind="folder" if child.is_dir() else "file",
                suffix=child.suffix.lower() if child.is_file() else "",
                size_bytes=child.stat().st_size if child.is_file() else None,
            )
            items.append(item)
            if len(items) >= limit:
                truncated = True
                return
            if child.is_dir():
                walk(child, depth + 1)
                if truncated:
                    return

    walk(start, 0)
    inventory = ProjectInventory(
        decision=decision,
        ok=True,
        items=items,
        skipped_count=skipped,
        truncated=truncated,
        total_items=len(items),
        runtime_or_generated_dirs=sorted(set(runtime_dirs))[:30],
    )
    key_files = detect_key_files(inventory)
    dependency_files = detect_dependency_files(inventory)
    return ProjectInventory(
        decision=decision,
        ok=True,
        items=items,
        project_types=detect_project_type(inventory),
        key_files=key_files,
        missing_recommended_files=detect_missing_recommended_files(inventory),
        dependency_files=dependency_files,
        dependencies=_read_shallow_dependencies(dependency_files, repo),
        test_files=detect_test_files(inventory),
        docs_files=detect_docs_files(inventory),
        runtime_or_generated_dirs=sorted(set(runtime_dirs))[:30],
        skipped_count=skipped,
        truncated=truncated,
        total_items=len(items),
    )


def detect_project_type(inventory: ProjectInventory) -> list[str]:
    paths = _paths(inventory)
    lowered = "\n".join(paths).lower()
    types: list[str] = []
    if "backend/eva/" in lowered or "eva_file_agent" in lowered or "eva" in lowered:
        types.append("Eva project")
    if any(path.endswith(".py") for path in paths) or "requirements.txt" in lowered or "pyproject.toml" in lowered:
        types.append("Python")
    if "fastapi" in _safe_key_text(inventory).lower() or "backend/eva/main.py" in lowered:
        types.append("FastAPI")
    if "package.json" in lowered or any(path.endswith((".js", ".ts", ".tsx", ".jsx")) for path in paths):
        types.append("Node/React/Next")
    if "pubspec.yaml" in lowered or "android/" in lowered or "ios/" in lowered:
        types.append("Flutter")
    if "docs/" in lowered and len([path for path in paths if path.startswith("docs/")]) >= 3:
        types.append("docs-heavy")
    if "agent" in lowered or "planner" in lowered or "capabilities" in lowered:
        types.append("AI agent project")
    return types or ["unknown/mixed"]


def detect_key_files(inventory: ProjectInventory) -> dict[str, list[str]]:
    docs: list[str] = []
    configs: list[str] = []
    folders: list[str] = []
    for item in inventory.items:
        name = Path(item.display_path).name
        if item.kind == "folder" and name in KEY_DIRS:
            folders.append(item.display_path)
        if item.kind == "file" and (name in KEY_NAMES or name.startswith("vite.config") or name.startswith("next.config")):
            if name.lower().endswith(".md") or name.upper() == "LICENSE":
                docs.append(item.display_path)
            else:
                configs.append(item.display_path)
    return {"docs": docs[:30], "configs": configs[:30], "folders": folders[:30]}


def detect_missing_recommended_files(inventory: ProjectInventory) -> list[str]:
    names = {Path(item.display_path).name.lower() for item in inventory.items if item.kind == "file"}
    missing: list[str] = []
    for wanted in ["README.md", "LICENSE", ".gitignore", ".env.example"]:
        if wanted.lower() not in names:
            missing.append(wanted)
    if not any(path.startswith("docs/") for path in _paths(inventory)):
        missing.append("docs/")
    if not any("test" in path.lower() for path in _paths(inventory)):
        missing.append("tests/ or test files")
    return missing


def detect_dependency_files(inventory: ProjectInventory) -> list[str]:
    names = {"requirements.txt", "pyproject.toml", "package.json", "pubspec.yaml", "Dockerfile", "docker-compose.yml"}
    output = []
    for item in inventory.items:
        name = Path(item.display_path).name
        if item.kind == "file" and (name in names or detect_config_type(name)):
            if name in names or name.startswith(("vite.config", "next.config")) or name in {"tsconfig.json"}:
                output.append(item.display_path)
    return output[:40]


def detect_test_files(inventory: ProjectInventory) -> list[str]:
    return [item.display_path for item in inventory.items if item.kind == "file" and ("test" in item.display_path.lower() or item.display_path.startswith("scripts/verify_"))][:40]


def detect_docs_files(inventory: ProjectInventory) -> list[str]:
    return [item.display_path for item in inventory.items if item.kind == "file" and (item.display_path.startswith("docs/") or item.display_path.lower().endswith(".md"))][:40]


def detect_runtime_or_generated_dirs(inventory: ProjectInventory) -> list[str]:
    return list(inventory.runtime_or_generated_dirs)


def explain_project_inventory(inventory: ProjectInventory) -> str:
    if not inventory.ok:
        return "\n".join(["Project explanation", "", f"Path: {inventory.decision.display_path}", "Status: refused.", f"Reason: {inventory.decision.reason}"])
    lines = [
        "Project explanation",
        "",
        f"Root: {inventory.decision.display_path}",
        "Project type: " + ", ".join(inventory.project_types),
        f"Visible inventory items: {inventory.total_items}.",
        "",
        "What this project appears to be:",
        _project_sentence(inventory),
    ]
    lines.append("")
    lines.append("Key files:")
    for label, items in inventory.key_files.items():
        if items:
            lines.append(f"- {label}: " + ", ".join(items[:10]))
    if inventory.missing_recommended_files:
        lines.append("")
        lines.append("Missing or worth checking: " + ", ".join(inventory.missing_recommended_files[:10]) + ".")
    lines.append("")
    lines.append("Limits: local heuristic inventory only; no cloud, shell, package install, secret read, or file write.")
    return "\n".join(lines)


def format_project_inventory(inventory: ProjectInventory) -> str:
    if not inventory.ok:
        return "\n".join(["Project inventory", "", f"Path: {inventory.decision.display_path}", "Status: refused.", f"Reason: {inventory.decision.reason}"])
    lines = [
        "Project inventory",
        "",
        f"Root: {inventory.decision.display_path}",
        "Project type: " + ", ".join(inventory.project_types),
        f"Items scanned: {inventory.total_items}.",
        f"Skipped sensitive/runtime entries: {inventory.skipped_count}.",
        "",
        "Key files:",
    ]
    any_key = False
    for label, items in inventory.key_files.items():
        if items:
            any_key = True
            lines.append(f"- {label}: " + ", ".join(items[:12]))
    if not any_key:
        lines.append("- No common key files found within limits.")
    if inventory.dependency_files:
        lines.extend(["", "Dependency/config files:"])
        lines.extend(f"- {path}" for path in inventory.dependency_files[:15])
    if inventory.test_files:
        lines.extend(["", "Tests/verifiers:"])
        lines.extend(f"- {path}" for path in inventory.test_files[:10])
    if inventory.docs_files:
        lines.extend(["", "Docs:"])
        lines.extend(f"- {path}" for path in inventory.docs_files[:10])
    if inventory.truncated:
        lines.append("Inventory truncated by FileAgent limits.")
    lines.append("Scope: read-only local inventory; runtime and sensitive folders are skipped.")
    return "\n".join(lines)


def format_missing_files(inventory: ProjectInventory) -> str:
    if not inventory.ok:
        return format_project_inventory(inventory)
    lines = ["Project missing-file checklist", "", f"Root: {inventory.decision.display_path}"]
    if not inventory.missing_recommended_files:
        lines.append("No obvious common docs/config checklist gaps found within FileAgent limits.")
    else:
        lines.append("Recommended items to check:")
        lines.extend(f"- {item}" for item in inventory.missing_recommended_files)
    lines.append("Scope: checklist only; no files were created.")
    return "\n".join(lines)


def format_project_dependencies(inventory: ProjectInventory) -> str:
    if not inventory.ok:
        return format_project_inventory(inventory)
    lines = ["Project dependencies/config", "", f"Root: {inventory.decision.display_path}"]
    if inventory.dependency_files:
        lines.append("Detected dependency/config files:")
        lines.extend(f"- {path}" for path in inventory.dependency_files[:20])
    else:
        lines.append("No common dependency/config files found within limits.")
    if inventory.dependencies:
        lines.append("")
        lines.append("Shallow dependency hints:")
        lines.extend(f"- {dep}" for dep in inventory.dependencies[:30])
    lines.append("Scope: shallow local detection only; secret-like values are not printed.")
    return "\n".join(lines)


def format_key_files(inventory: ProjectInventory) -> str:
    if not inventory.ok:
        return format_project_inventory(inventory)
    lines = ["Project key files", "", f"Root: {inventory.decision.display_path}"]
    for label, items in inventory.key_files.items():
        lines.append(f"{label}:")
        lines.extend(f"- {item}" for item in (items or ["none found"])[:30])
    lines.append("Scope: read-only key-file detection.")
    return "\n".join(lines)


def _read_shallow_dependencies(paths: list[str], repo: Path) -> list[str]:
    deps: list[str] = []
    for display in paths[:8]:
        path = repo / display
        if not path.exists() or not path.is_file() or path.stat().st_size > 100_000:
            continue
        decision = evaluate_file_path(str(path), repo_root=repo)
        if not decision.allowed:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:40_000]
        except OSError:
            continue
        if path.name.lower() == "package.json":
            deps.extend(_package_json_deps(text))
        else:
            deps.extend(extract_imports_or_dependencies(text, filename=path.name, limit=15))
    return _dedupe(deps)[:40]


def _package_json_deps(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except Exception:
        return []
    output: list[str] = []
    if isinstance(data, dict):
        for key in ("dependencies", "devDependencies"):
            value = data.get(key)
            if isinstance(value, dict):
                output.extend(value.keys())
    return output


def _safe_key_text(inventory: ProjectInventory) -> str:
    return "\n".join(_paths(inventory)[:300])


def _project_sentence(inventory: ProjectInventory) -> str:
    types = set(inventory.project_types)
    if "Eva project" in types:
        return "This looks like the Eva local AI assistant repo, with backend agent systems, docs, verifiers, and frontend UI files."
    if "Python" in types and "Node/React/Next" in types:
        return "This looks like a mixed Python backend and JavaScript/TypeScript frontend project."
    if "Python" in types:
        return "This looks like a Python project with local scripts, backend code, or verifier tooling."
    return "This is a mixed project; FileAgent can only infer from filenames and small safe key files."


def _paths(inventory: ProjectInventory) -> list[str]:
    return [item.display_path for item in inventory.items]


def _skip_inventory_path(path: Path, repo: Path) -> bool:
    if path.name.lower() in IGNORED_DIRS:
        return True
    rel = _display(path, repo).replace("\\", "/").lower()
    if rel.startswith("backend/eva/data"):
        return True
    return any(part in rel.split("/") for part in {"__pycache__", ".git", ".venv", "node_modules"})


def _inventory_sort_key(path: Path) -> tuple[int, str]:
    name = path.name
    if path.is_file() and (name in KEY_NAMES or name.startswith(("vite.config", "next.config"))):
        return (0, name.lower())
    if path.is_dir() and name in KEY_DIRS:
        return (1, name.lower())
    if path.is_file():
        return (2, name.lower())
    return (3, name.lower())


def _looks_runtime_generated(display: str) -> bool:
    lowered = display.replace("\\", "/").lower()
    return any(marker in lowered for marker in ["backend/eva/data", "/data", "traces", "screenshots", "__pycache__", "node_modules", ".venv"])


def _display(path: Path, repo: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return path.name


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        clean = str(item or "").strip()
        if clean and clean not in output:
            output.append(clean)
    return output
