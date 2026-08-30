"""Aider-style repository map (specs/repomap.md).

A compact, automatic overview of the codebase — classes/functions/methods from
an `ast` parse — so the model knows the structure without reading every file
(Aider's Repository Map idea). Cached by content fingerprint.
"""
from __future__ import annotations

import ast
import hashlib
import time
from pathlib import Path

_SKIP = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules",
         ".coding-agent", ".idea", ".vscode", "build", "dist", ".env", "demo"}


def _skip(root: Path, p: Path) -> bool:
    rel = p.relative_to(root)
    return any(part in _SKIP for part in rel.parts)


def _params(node: ast.FunctionDef) -> str:
    a = node.args
    pos = [x.arg for x in a.posonlyargs] + [x.arg for x in a.args]
    kw = [x.arg for x in a.kwonlyargs]
    return ", ".join([*pos, *kw])


def _symbols(fp: Path) -> list[str]:
    try:
        tree = ast.parse(fp.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    lines: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = ",".join(ast.unparse(b) for b in node.bases)
            lines.append(f"class {node.name}({bases or ''})")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lines.append(f"  def {item.name}({_params(item)})")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.append(f"def {node.name}({_params(node)})")
    return lines


def build_repo_map(workdir: Path | str, max_chars: int = 4000) -> str:
    """Return a compact map: <file> -> its classes/functions/methods."""
    root = Path(workdir)
    parts: list[str] = []
    files = sorted(p for p in root.rglob("*.py") if _skip(root, p) is False and p.is_file())
    for fp in files:
        syms = _symbols(fp)
        if syms:
            parts.append(f"## {fp.relative_to(root)}")
            parts.extend(syms)
    text = "\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [map truncated]"
    return text


def _fingerprint(root: Path) -> str:
    h = hashlib.sha1()
    files = sorted(p for p in root.rglob("*.py") if _skip(root, p) is False and p.is_file())
    for fp in files:
        st = fp.stat()
        h.update(f"{fp}:{st.st_mtime_ns}:{st.st_size}".encode())
    return h.hexdigest()


def code_map(workdir: Path | str, max_chars: int = 4000) -> str:
    """Cached repo map keyed by content fingerprint (rebuilt when it changes)."""
    root = Path(workdir)
    fp = _fingerprint(root)
    cache = root / ".coding-agent" / "repomap.txt"
    if cache.exists():
        try:
            lines = cache.read_text(encoding="utf-8").split("\n", 1)
            if len(lines) == 2 and lines[0] == fp:
                return lines[1]
        except Exception:
            pass
    content = build_repo_map(root, max_chars)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(fp + "\n" + content, encoding="utf-8")
    except Exception:
        pass
    return content
