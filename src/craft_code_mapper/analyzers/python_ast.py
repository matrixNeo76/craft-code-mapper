"""
Analizzatore AST per Python — estrae classi, funzioni, import e call graph.

Usa esclusivamente la libreria standard `ast` (zero dipendenze esterne).
Supporta Python 3.10+.
"""

import ast
import hashlib
import os
from typing import Any


def extract_file(filepath: str) -> dict[str, Any]:
    """Estrae nodi AST da un file Python.

    Args:
        filepath: Percorso assoluto del file .py

    Returns:
        dict con:
          - filepath: percorso del file
          - language: "python"
          - hash: SHA256 del contenuto
          - nodes: lista di dict (tipo, nome, linea, docstring...)
          - imports: lista di import
          - calls: lista di (chiamante, chiamato, linea)
          - errors: lista di errori di parsing (se presenti)
    """
    result: dict[str, Any] = {
        "filepath": filepath,
        "language": "python",
        "hash": "",
        "nodes": [],
        "imports": [],
        "calls": [],
        "errors": [],
    }

    if not os.path.isfile(filepath):
        result["errors"].append(f"File not found: {filepath}")
        return result

    try:
        with open(filepath, "r", encoding="utf-8", errors="surrogateescape") as f:
            source = f.read()
    except OSError as e:
        result["errors"].append(f"Read error: {e}")
        return result

    result["hash"] = hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        result["errors"].append(f"Syntax error: {e}")
        return result

    # Build function context map once: node -> enclosing_function_name
    func_context = _build_function_context(tree)

    _extract_nodes(tree, filepath, result, func_context)
    _extract_calls(tree, result, func_context)

    return result


def _extract_nodes(tree: ast.Module, filepath: str, result: dict, func_context: dict) -> None:
    """Estrae classi, funzioni e import da un albero AST."""
    # Import a livello di modulo
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                result["imports"].append({
                    "module": f"{module}.{alias.name}" if module else alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ClassDef):
            _extract_class(node, filepath, result, func_context)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _extract_function(node, filepath, result, is_method=False, func_context=func_context)


def _extract_class(node: ast.ClassDef, filepath: str, result: dict, func_context: dict) -> None:
    """Estrae una classe e i suoi metodi."""
    docstring = ast.get_docstring(node) or ""
    bases = [
        _node_name(b) for b in node.bases if hasattr(b, "id") or hasattr(b, "attr")
    ]

    class_node = {
        "type": "class",
        "name": node.name,
        "line": node.lineno,
        "end_line": node.end_lineno,
        "docstring": docstring[:200],
        "bases": bases,
        "filepath": filepath,
    }
    result["nodes"].append(class_node)

    # Metodi della classe
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _extract_function(
                child, filepath, result, is_method=True, class_name=node.name, func_context=func_context
            )
            result["calls"].append({
                "caller": f"{node.name}.{child.name}",
                "callee": node.name,
                "line": child.lineno,
                "type": "method_of",
            })


def _extract_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    filepath: str,
    result: dict,
    is_method: bool = False,
    class_name: str | None = None,
    func_context: dict | None = None,
) -> dict:
    """Estrae una funzione/metodo."""
    docstring = ast.get_docstring(node) or ""
    func_name = f"{class_name}.{node.name}" if class_name else node.name

    # Parametri
    params = []
    for arg in node.args.args:
        params.append(arg.arg)

    # Decoratori (T-09)
    decorators = []
    for d in node.decorator_list:
        dec_name = _node_name(d) if hasattr(d, "id") else None
        if dec_name:
            decorators.append(dec_name)
        else:
            try:
                dec_name = ast.unparse(d)
                decorators.append(dec_name)
            except Exception:
                decorators.append("<decorator>")

    func_node = {
        "type": "method" if is_method else "function",
        "name": func_name,
        "line": node.lineno,
        "end_line": node.end_lineno,
        "docstring": docstring[:200],
        "params": params,
        "decorators": decorators,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "filepath": filepath,
    }
    result["nodes"].append(func_node)


def _build_function_context(tree: ast.AST) -> dict[ast.AST, str]:
    """Costruisce una mappa node -> enclosing_function_name in O(n)."""
    func_context: dict[ast.AST, str] = {}

    def walk(node: ast.AST, current_func: str | None) -> None:
        func_context[node] = current_func or ""
        for child in ast.iter_child_nodes(node):
            # Determine if child is a function/method
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                child_func = child.name
            elif isinstance(child, ast.ClassDef):
                child_func = current_func  # class methods handled separately
            else:
                child_func = current_func
            walk(child, child_func if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else current_func)

    walk(tree, None)
    return func_context


def _extract_calls(tree: ast.Module, result: dict, func_context: dict) -> None:
    """Trova chiamate a funzioni (call graph semplice).

    Cerca pattern come `self.x()`, `obj.method()`, `function()`.
    Questo è un'analisi statica — non risolve alias o import dinamici.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            caller_func = func_context.get(node, "") or None
            if caller_func:
                callee = _call_name(node.func)
                if callee:
                    result["calls"].append({
                        "caller": caller_func,
                        "callee": callee,
                        "line": node.lineno,
                        "type": "calls",
                    })


def _call_name(func: ast.AST) -> str | None:
    """Estrae il nome di una chiamata di funzione."""
    if isinstance(func, ast.Name):
        return func.id
    elif isinstance(func, ast.Attribute):
        return func.attr
    elif isinstance(func, ast.Call):
        return _call_name(func.func)
    return None


def _node_name(node: ast.AST) -> str:
    """Estrae il nome da un nodo AST (per basi di classe, ecc.)."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_node_name(node.value)}.{node.attr}"
    return ""