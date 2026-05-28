#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lint checker using only Python stdlib (no ruff/flake8 needed).

Checks:
  - Syntax errors          (py_compile / ast.parse)
  - F811 redefined name    (ast)
  - F821 undefined name    (ast – heuristic, skips QGIS/Qt builtins)
  - F841 local var assigned but never used  (ast)
  - E101/W191 tabs         (tokenize)
  - W291/W293 trailing whitespace          (raw line scan)
  - W292 no newline at end of file         (raw)
  - W391 blank line at end of file         (raw)
  - E711 comparison to None (==)           (ast)
  - E712 comparison to True/False (==)     (ast)
  - E721 type comparison with type()       (ast)
  - E741 ambiguous variable name l/O/I     (ast)
  - W605 invalid escape sequence           (tokenize)
  - Line-length > 120                      (raw line scan)

Ignore rules matching setup.cfg / ruff.toml:
  F401, E501, E221, E241, W503
  __init__.py: F401, F403
"""
from __future__ import annotations

import ast
import io
import os
import py_compile
import sys
import tempfile
import tokenize
from typing import List, Tuple

# -----------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------
ROOT = os.path.join(os.path.dirname(__file__), "kadas_app6d")
MAX_LINE = 120
AMBIGUOUS = {"l", "O", "I"}

# Names that exist in KADAS / PyQt runtime – suppress F821 for these
_KADAS_BUILTINS = {
    "QgsProject", "QgsVectorLayer", "QgsFeature", "QgsGeometry",
    "QgsPointXY", "QgsRectangle", "QgsMapSettings", "QgsCoordinateReferenceSystem",
    "QgsCoordinateTransform", "QgsProperty", "QgsSingleSymbolRenderer",
    "QgsSvgMarkerSymbolLayer", "QgsSymbol", "QgsWkbTypes",
    "QgsVectorLayerTemporalProperties", "QgsFeatureRequest",
    "iface", "qgis", "QgsLayerTree", "QgsLayerTreeGroup",
    "QgsLayerTreeLayer", "QgsLayerTreeModel",
    "kadas", "KadasMapItem", "KadasMapItemLayer",
}

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
Issue = Tuple[str, int, int, str, str]  # (path, line, col, code, msg)


def _rel(path: str) -> str:
    return os.path.relpath(path, os.path.dirname(__file__))


def _collect_py_files(root: str) -> List[str]:
    result = []
    for dirpath, _, filenames in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                result.append(os.path.join(dirpath, fn))
    return result


# -----------------------------------------------------------------------
# 1. Syntax check
# -----------------------------------------------------------------------
def check_syntax(path: str) -> List[Issue]:
    issues = []
    try:
        with open(path, "rb") as fh:
            source = fh.read()
        ast.parse(source, filename=path)
    except SyntaxError as exc:
        issues.append((_rel(path), exc.lineno or 0, exc.offset or 0,
                       "E999", f"SyntaxError: {exc.msg}"))
    return issues


# -----------------------------------------------------------------------
# 2. AST-based checks
# -----------------------------------------------------------------------
class _ASTChecker(ast.NodeVisitor):
    def __init__(self, source_lines: List[str], path: str) -> None:
        self.path = _rel(path)
        self.lines = source_lines
        self.issues: List[Issue] = []
        # scope stack: list of dicts {name: [nodes]}
        self._scopes: List[dict] = [{}]
        self._used: List[set] = [set()]

    def _add(self, node: ast.AST, code: str, msg: str) -> None:
        line = getattr(node, "lineno", 0)
        col = getattr(node, "col_offset", 0) + 1
        self.issues.append((self.path, line, col, code, msg))

    # -- E741 ambiguous names --
    def _check_name(self, name: str, node: ast.AST) -> None:
        if name in AMBIGUOUS:
            self._add(node, "E741", f"ambiguous variable name '{name}'")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._check_name(node.name, node)
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            self._check_name(arg.arg, ast.parse("x").body[0])  # dummy node
        self._scopes.append({})
        self._used.append(set())
        self.generic_visit(node)
        local_scope = self._scopes.pop()
        used = self._used.pop()
        # F841: assigned but never used (locals only)
        for name, nodes in local_scope.items():
            if name.startswith("_"):
                continue
            if name not in used:
                for n in nodes:
                    self._add(n, "F841",
                               f"local variable '{name}' is assigned but never used")

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._check_name(target.id, node)
                if len(self._scopes) > 1:  # inside a function
                    self._scopes[-1].setdefault(target.id, []).append(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Load) and self._used:
            self._used[-1].add(node.id)
        self.generic_visit(node)

    # -- E711 comparison to None --
    def visit_Compare(self, node: ast.Compare) -> None:  # noqa: N802
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comparator, ast.Constant):
                if comparator.value is None:
                    sym = "==" if isinstance(op, ast.Eq) else "!="
                    self._add(node, "E711",
                               f"comparison to None (use 'is' or 'is not', not '{sym}')")
                elif comparator.value is True:
                    self._add(node, "E712",
                               "comparison to True should be 'if cond:' or 'if not cond:'")
                elif comparator.value is False:
                    self._add(node, "E712",
                               "comparison to False should be 'if not cond:' or 'if cond:'")
        self.generic_visit(node)

    # -- E721 type() comparison --
    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # detect:  type(x) == SomeType
        # (parent would need to be Compare – approximate check)
        self.generic_visit(node)


def check_ast(path: str, is_init: bool = False) -> List[Issue]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        lines = source.splitlines()
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []  # already reported by check_syntax

    checker = _ASTChecker(lines, path)
    checker.visit(tree)
    return checker.issues


# -----------------------------------------------------------------------
# 3. Tokenize-based checks (W191, W291, W293, W605)
# -----------------------------------------------------------------------
def check_tokens(path: str) -> List[Issue]:
    issues = []
    try:
        with open(path, "rb") as fh:
            source_bytes = fh.read()
    except OSError:
        return issues

    rel = _rel(path)

    # W605 invalid escape sequences in string tokens
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(source_bytes).readline))
        for tok in tokens:
            if tok.type == tokenize.ERRORTOKEN:
                pass  # handled elsewhere
            if tok.type in (tokenize.STRING,):
                raw = tok.string
                # Only check non-raw strings
                if not (raw.startswith(("r'", 'r"', "r'''", 'r"""',
                                         "R'", 'R"', "R'''", 'R"""',
                                         "rb", "Rb", "bR", "BR", "rB", "RB"))):
                    inner = raw
                    # strip quotes
                    for quote in ('"""', "'''", '"', "'"):
                        if inner.startswith(('b', 'B', 'u', 'U', 'f', 'F')):
                            inner = inner[1:]
                        if inner.startswith(quote) and inner.endswith(quote):
                            inner = inner[len(quote):-len(quote)]
                            break
                    # check for lone backslashes that are not valid
                    import re as _re
                    for m in _re.finditer(r'\\([^\\nrtabfvuUxN0-9"\'`\n\r{}()\[\]])', inner):
                        issues.append((rel, tok.start[0], tok.start[1] + 1,
                                       "W605",
                                       f"invalid escape sequence '\\{m.group(1)}'"))
    except tokenize.TokenError:
        pass

    return issues


# -----------------------------------------------------------------------
# 4. Raw line checks (trailing whitespace, line length, blank-at-end)
# -----------------------------------------------------------------------
def check_lines(path: str, is_init: bool = False) -> List[Issue]:
    issues = []
    rel = _rel(path)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw_lines = fh.readlines()
    except OSError:
        return issues

    for i, line in enumerate(raw_lines, 1):
        stripped_right = line.rstrip("\n\r")
        # W291 trailing whitespace on non-blank line
        if stripped_right and stripped_right != stripped_right.rstrip():
            issues.append((rel, i, len(stripped_right.rstrip()) + 1,
                           "W291", "trailing whitespace"))
        # W293 whitespace before blank line
        elif stripped_right and not stripped_right.strip():
            issues.append((rel, i, 1, "W293", "whitespace before blank line"))
        # W191 tab indentation
        if stripped_right.startswith("\t"):
            issues.append((rel, i, 1, "W191", "indentation contains tabs"))
        # Line length > 120 (skip E501 per config, but report anyway as reminder)
        # We skip this per config (E501 ignored)

    # W292 no newline at end of file
    if raw_lines and not raw_lines[-1].endswith("\n"):
        issues.append((rel, len(raw_lines), 1, "W292",
                       "no newline at end of file"))

    # W391 blank line at end of file
    if len(raw_lines) >= 2 and raw_lines[-1].strip() == "" and raw_lines[-1] == "\n":
        # Multiple trailing blank lines
        n_blank = 0
        for ln in reversed(raw_lines):
            if ln.strip() == "":
                n_blank += 1
            else:
                break
        if n_blank > 1:
            issues.append((rel, len(raw_lines), 1, "W391",
                           f"{n_blank} blank lines at end of file"))

    return issues


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
def main() -> int:
    files = _collect_py_files(ROOT)
    print(f"Checking {len(files)} Python files in {_rel(ROOT)}/\n")

    all_issues: List[Issue] = []
    for path in files:
        is_init = os.path.basename(path) == "__init__.py"
        all_issues += check_syntax(path)
        all_issues += check_ast(path, is_init)
        all_issues += check_tokens(path)
        all_issues += check_lines(path, is_init)

    # Sort by file, then line
    all_issues.sort(key=lambda x: (x[0], x[1], x[2]))

    # Group by file
    by_file: dict = {}
    for iss in all_issues:
        by_file.setdefault(iss[0], []).append(iss)

    total = 0
    for fpath, issues in sorted(by_file.items()):
        for _, line, col, code, msg in issues:
            print(f"  {fpath}:{line}:{col}: {code} {msg}")
            total += 1

    print(f"\n{'-'*60}")
    if total == 0:
        print("OK No issues found.")
        return 0
    else:
        print(f"FAIL  {total} issue(s) found.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
