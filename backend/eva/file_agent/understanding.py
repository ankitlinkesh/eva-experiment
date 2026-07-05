from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


SECRET_VALUE_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]{12,}|ghp_[a-z0-9_]{12,}|bearer\s+[a-z0-9._-]{8,}|api[_-]?key\s*[:=]\s*['\"]?[^'\"\s]+|password\s*[:=]\s*['\"]?[^'\"\s]+)"
)


@dataclass(frozen=True)
class FileUnderstanding:
    path: str
    ok: bool
    purpose: str
    summary: str
    file_kind: str = "text"
    headings: list[str] = field(default_factory=list)
    imports_or_dependencies: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    config_type: str | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "ok": self.ok,
            "purpose": self.purpose,
            "summary": self.summary,
            "file_kind": self.file_kind,
            "headings": list(self.headings),
            "imports_or_dependencies": list(self.imports_or_dependencies),
            "symbols": list(self.symbols),
            "todos": list(self.todos),
            "config_type": self.config_type,
            "warnings": list(self.warnings),
        }

    def __str__(self) -> str:
        return format_file_understanding(self)


def summarize_text_content(text: str, filename: str | None = None, max_lines: int = 8) -> dict[str, object]:
    clean = _sanitize_text(text)
    lines = [line.strip() for line in clean.splitlines() if line.strip()]
    interesting = [line for line in lines if not _is_noise_line(line)]
    selected = interesting[: max(1, min(12, int(max_lines or 8)))]
    if not selected:
        selected = ["No substantial readable text was found in the preview limits."]
    return {
        "filename": _display_name(filename),
        "summary": _sentence_from_lines(selected),
        "line_count": len(lines),
        "headings": extract_headings(clean),
        "todos": extract_todos(clean),
        "warnings": _quality_warnings(clean),
    }


def summarize_code_file(text: str, filename: str | None = None) -> dict[str, object]:
    clean = _sanitize_text(text)
    suffix = Path(filename or "").suffix.lower()
    symbols = _extract_python_symbols(clean) if suffix == ".py" else _extract_code_symbols(clean)
    imports = extract_imports_or_dependencies(clean, filename=filename)
    summary_bits = []
    if imports:
        summary_bits.append("uses " + ", ".join(imports[:5]))
    if symbols:
        summary_bits.append("defines " + ", ".join(symbols[:6]))
    if not summary_bits:
        summary_bits.append("contains code-like text inside the preview limits")
    return {
        "filename": _display_name(filename),
        "summary": "This code file " + "; ".join(summary_bits) + ".",
        "imports_or_dependencies": imports,
        "symbols": symbols,
        "todos": extract_todos(clean),
        "warnings": _quality_warnings(clean),
    }


def summarize_markdown_file(text: str, filename: str | None = None) -> dict[str, object]:
    clean = _sanitize_text(text)
    headings = extract_headings(clean)
    bullets = [line.strip("-* ").strip() for line in clean.splitlines() if line.strip().startswith(("-", "*"))]
    themes = bullets[:8]
    if headings:
        summary = "This markdown file is organized around: " + ", ".join(headings[:6]) + "."
    elif themes:
        summary = "This markdown file mainly lists: " + ", ".join(themes[:6]) + "."
    else:
        summary = str(summarize_text_content(clean, filename=filename).get("summary"))
    return {
        "filename": _display_name(filename),
        "summary": summary,
        "headings": headings,
        "bullet_themes": themes,
        "todos": extract_todos(clean),
        "warnings": _quality_warnings(clean),
    }


def detect_file_purpose(path: str, text: str | None = None) -> str:
    name = Path(path or "").name.lower()
    suffix = Path(path or "").suffix.lower()
    lowered = (text or "").lower()[:4000]
    if name == "readme.md":
        return "Project overview documentation."
    if name in {"license", "license.md"}:
        return "Project license document."
    if name == ".gitignore":
        return "Git ignore rules."
    if name == ".env.example":
        return "Example environment configuration without private values."
    if name.startswith("requirements") or name == "pyproject.toml":
        return "Python dependency or project configuration."
    if name == "package.json":
        return "Node package metadata and scripts."
    if "fastapi" in lowered:
        return "Python web/API application code."
    if suffix == ".md":
        return "Markdown documentation."
    if suffix == ".py":
        return "Python source code."
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return "JavaScript or TypeScript source code."
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "Configuration or structured data file."
    if suffix in {".html", ".css"}:
        return "Frontend UI asset."
    return "Safe text file."


def extract_headings(text: str, limit: int = 10) -> list[str]:
    headings: list[str] = []
    for line in _sanitize_text(text).splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading and not _looks_secret_like(heading):
                headings.append(_clip(heading, 120))
        if len(headings) >= limit:
            break
    return headings


def extract_imports_or_dependencies(text: str, filename: str | None = None, limit: int = 20) -> list[str]:
    clean = _sanitize_text(text)
    suffix = Path(filename or "").suffix.lower()
    items: list[str] = []
    if suffix == ".py":
        for line in clean.splitlines():
            stripped = line.strip()
            match = re.match(r"import\s+([a-zA-Z0-9_.,\s]+)", stripped)
            if match:
                for part in match.group(1).split(","):
                    items.append(part.strip().split(" as ")[0])
            match = re.match(r"from\s+([a-zA-Z0-9_.]+)\s+import\s+", stripped)
            if match:
                items.append(match.group(1))
            if len(items) >= limit:
                break
    elif Path(filename or "").name.lower() == "requirements.txt":
        for line in clean.splitlines():
            dep = line.strip()
            if dep and not dep.startswith("#") and not _looks_secret_like(dep):
                items.append(re.split(r"[<>=~!]", dep, maxsplit=1)[0].strip())
            if len(items) >= limit:
                break
    elif suffix == ".json":
        try:
            data = json.loads(clean)
            for key in ("dependencies", "devDependencies", "peerDependencies", "scripts"):
                value = data.get(key) if isinstance(data, dict) else None
                if isinstance(value, dict):
                    items.extend(list(value.keys())[:limit])
        except Exception:
            pass
    elif suffix == ".toml":
        for line in clean.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                items.append(stripped.strip("[]"))
            if len(items) >= limit:
                break
    return _dedupe_safe(items)[:limit]


def extract_todos(text: str, limit: int = 20) -> list[str]:
    todos: list[str] = []
    for line in _sanitize_text(text).splitlines():
        if re.search(r"(?i)\b(todo|fixme|hack|note)\b", line):
            cleaned = _clip(line.strip(" #/-*\t"), 180)
            if cleaned and not _looks_secret_like(cleaned):
                todos.append(cleaned)
        if len(todos) >= limit:
            break
    return todos


def detect_config_type(path: str) -> str | None:
    name = Path(path or "").name.lower()
    suffix = Path(path or "").suffix.lower()
    mapping = {
        "pyproject.toml": "Python project configuration",
        "requirements.txt": "Python dependency list",
        "package.json": "Node package configuration",
        "tsconfig.json": "TypeScript configuration",
        "vite.config.js": "Vite frontend configuration",
        "vite.config.ts": "Vite frontend configuration",
        "next.config.js": "Next.js configuration",
        "next.config.ts": "Next.js configuration",
        "dockerfile": "Docker build configuration",
        "docker-compose.yml": "Docker Compose configuration",
        "makefile": "Make task configuration",
        ".gitignore": "Git ignore configuration",
        ".env.example": "Example environment configuration",
    }
    if name in mapping:
        return mapping[name]
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "Structured configuration or data"
    return None


def understand_text_file(path: str, text: str) -> FileUnderstanding:
    display = _display_name(path)
    suffix = Path(path or "").suffix.lower()
    purpose = detect_file_purpose(display, text)
    config_type = detect_config_type(display)
    if suffix == ".md" or Path(display).name.lower() == "readme.md":
        summary = summarize_markdown_file(text, filename=display)
        file_kind = "markdown"
    elif suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css"}:
        summary = summarize_code_file(text, filename=display)
        file_kind = "code"
    else:
        summary = summarize_text_content(text, filename=display)
        file_kind = "config" if config_type else "text"
    return FileUnderstanding(
        path=display,
        ok=True,
        purpose=purpose,
        summary=str(summary.get("summary") or "Heuristic summary unavailable."),
        file_kind=file_kind,
        headings=list(summary.get("headings") or []),
        imports_or_dependencies=list(summary.get("imports_or_dependencies") or extract_imports_or_dependencies(text, filename=display)),
        symbols=list(summary.get("symbols") or []),
        todos=list(summary.get("todos") or []),
        config_type=config_type,
        warnings=list(summary.get("warnings") or []),
    )


def format_file_understanding(result: FileUnderstanding | dict[str, object]) -> str:
    data = result.as_dict() if isinstance(result, FileUnderstanding) else dict(result)
    if not data.get("ok", True):
        return "\n".join(["File understanding", "", f"Path: {data.get('path') or 'unknown'}", "Status: refused.", f"Reason: {data.get('summary') or 'FileAgent refused this path safely.'}"])
    lines = [
        "File understanding",
        "",
        f"Path: {data.get('path') or 'unknown'}",
        "Mode: read-only heuristic local summary.",
        f"Purpose: {data.get('purpose') or 'Unknown safe text file.'}",
        f"Summary: {data.get('summary') or 'No summary available within limits.'}",
    ]
    if data.get("config_type"):
        lines.append(f"Config type: {data.get('config_type')}.")
    for label, key in [
        ("Headings", "headings"),
        ("Imports/dependencies", "imports_or_dependencies"),
        ("Symbols", "symbols"),
        ("TODOs/notes", "todos"),
        ("Warnings", "warnings"),
    ]:
        items = [str(item) for item in (data.get(key) or []) if str(item).strip()]
        if items:
            lines.append(f"{label}: " + ", ".join(_clip(item, 100) for item in items[:10]) + ".")
    lines.append("Limits: heuristic only; no cloud, LLM, OCR, PDF/DOCX parsing, or secret reading.")
    return "\n".join(lines)


def _extract_python_symbols(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _extract_code_symbols(text)
    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(f"class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(f"def {node.name}")
    return symbols[:30]


def _extract_code_symbols(text: str) -> list[str]:
    symbols: list[str] = []
    patterns = [
        r"\bfunction\s+([A-Za-z0-9_]+)\s*\(",
        r"\bclass\s+([A-Za-z0-9_]+)",
        r"\b(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=",
        r"\bdef\s+([A-Za-z0-9_]+)\s*\(",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            symbols.append(match.group(1))
            if len(symbols) >= 30:
                return symbols
    return symbols


def _sanitize_text(text: str) -> str:
    return SECRET_VALUE_RE.sub("[REDACTED_SECRET_LIKE_VALUE]", str(text or ""))


def _looks_secret_like(text: str) -> bool:
    return bool(SECRET_VALUE_RE.search(str(text or "")))


def _display_name(path: str | None) -> str:
    if not path:
        return "unknown"
    value = str(path).replace("\\", "/")
    if ":" in value:
        return Path(value).name or "outside repo path"
    return value


def _is_noise_line(line: str) -> bool:
    stripped = line.strip()
    return stripped in {"{", "}", "[", "]"} or len(stripped) <= 1


def _sentence_from_lines(lines: list[str]) -> str:
    clipped = [_clip(line, 140) for line in lines[:8]]
    return " ".join(clipped)


def _quality_warnings(text: str) -> list[str]:
    stripped = text.strip()
    warnings: list[str] = []
    if len(stripped) < 80:
        warnings.append("very short preview")
    if SECRET_VALUE_RE.search(stripped):
        warnings.append("secret-like value was redacted")
    return warnings


def _clip(text: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value if len(value) <= limit else value[: max(0, limit - 3)].rstrip() + "..."


def _dedupe_safe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        clean = _clip(item, 80)
        if clean and clean not in output and not _looks_secret_like(clean):
            output.append(clean)
    return output
