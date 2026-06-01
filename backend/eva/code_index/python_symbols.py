from __future__ import annotations

import ast
import re

from .models import CodeSymbol


def extract_python_symbols(text: str) -> tuple[list[CodeSymbol], list[str], list[str]]:
    symbols: list[CodeSymbol] = []
    imports: list[str] = []
    routes: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _regex_python_symbols(text), _regex_imports(text), _regex_routes(text)

    parents: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            symbols.append(CodeSymbol(name=node.name, kind="class", line=int(node.lineno), parent=parents[-1] if parents else None))
            parents.append(node.name)
            self.generic_visit(node)
            parents.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            symbols.append(CodeSymbol(name=node.name, kind="function", line=int(node.lineno), parent=parents[-1] if parents else None))
            parents.append(node.name)
            self.generic_visit(node)
            parents.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            symbols.append(CodeSymbol(name=node.name, kind="async_function", line=int(node.lineno), parent=parents[-1] if parents else None))
            parents.append(node.name)
            self.generic_visit(node)
            parents.pop()

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                if alias.name != "__future__":
                    imports.append(alias.name)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            module = "." * int(node.level or 0) + str(node.module or "")
            if module.strip(".") != "__future__":
                imports.append(module.strip())

    Visitor().visit(tree)
    routes = _regex_routes(text)
    return symbols[:200], sorted(set(imports))[:80], routes[:80]


def extract_text_symbols(text: str, extension: str) -> tuple[list[CodeSymbol], list[str], list[str], list[str]]:
    if extension == ".py":
        symbols, imports, routes = extract_python_symbols(text)
        return symbols, imports, routes, _tool_names(text)
    symbols: list[CodeSymbol] = []
    imports: list[str] = []
    routes: list[str] = []
    tool_names: list[str] = []
    for pattern, kind in (
        (r"\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", "function"),
        (r"\bclass\s+([A-Za-z_$][\w$]*)", "class"),
        (r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", "variable"),
    ):
        for match in re.finditer(pattern, text):
            symbols.append(CodeSymbol(name=match.group(1), kind=kind, line=text.count("\n", 0, match.start()) + 1))
    imports = re.findall(r"^\s*(?:import\s+.+?from\s+['\"][^'\"]+['\"]|import\s+['\"][^'\"]+['\"]|from\s+['\"][^'\"]+['\"])", text, flags=re.MULTILINE)[:80]
    routes = re.findall(r"['\"](/[^'\"\s]{1,160})['\"]", text)[:80]
    tool_names = _tool_names(text)
    return symbols[:200], imports, routes, tool_names


def _regex_python_symbols(text: str) -> list[CodeSymbol]:
    symbols: list[CodeSymbol] = []
    for kind, pattern in (
        ("class", r"^class\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("function", r"^def\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("async_function", r"^async\s+def\s+([A-Za-z_][A-Za-z0-9_]*)"),
    ):
        for match in re.finditer(pattern, text, flags=re.MULTILINE):
            symbols.append(CodeSymbol(name=match.group(1), kind=kind, line=text.count("\n", 0, match.start()) + 1))
    return symbols[:200]


def _regex_imports(text: str) -> list[str]:
    imports: list[str] = []
    for match in re.finditer(r"^\s*(?:from\s+([A-Za-z0-9_.$]+)|import\s+([A-Za-z0-9_.$]+))", text, flags=re.MULTILINE):
        module = (match.group(1) or match.group(2) or "").strip()
        if module and module.strip(".") != "__future__":
            imports.append(module)
    return imports[:80]


def _regex_routes(text: str) -> list[str]:
    routes: list[str] = []
    for pattern in (r"@\w+\.(?:get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", r"['\"](/api/[^'\"]+)['\"]"):
        routes.extend(re.findall(pattern, text))
    return sorted(set(routes))[:80]


def _tool_names(text: str) -> list[str]:
    names = re.findall(r"name\s*=\s*['\"]([A-Za-z0-9_.:-]{2,80})['\"]", text)
    names.extend(re.findall(r"['\"]tool_name['\"]\s*:\s*['\"]([A-Za-z0-9_.:-]{2,80})['\"]", text))
    return sorted(set(names))[:80]
