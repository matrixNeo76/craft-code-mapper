"""
Analizzatore per JavaScript e TypeScript via tree-sitter.

Dipende da: tree-sitter, tree-sitter-javascript, tree-sitter-typescript.
"""

import hashlib
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_HAS_JS = False
_HAS_TS = False
_JS_LANG = None
_TS_LANG = None
_PY_LANG = None

try:
    from tree_sitter import Language, Parser

    try:
        import tree_sitter_javascript
        _JS_LANG = Language(tree_sitter_javascript.language())
        _HAS_JS = True
    except Exception as e:
        logger.warning(f"tree-sitter-javascript not available: {e}. JS analysis disabled.")

    try:
        import tree_sitter_typescript
        _TS_LANG = Language(tree_sitter_typescript.language_typescript())
        _HAS_TS = True
    except Exception as e:
        logger.warning(f"tree-sitter-typescript not available: {e}. TS analysis disabled.")

except ImportError:
    pass


def extract_file(filepath: str) -> dict[str, Any]:
    """Estrae nodi AST da un file JS/TS via tree-sitter.

    Returns: dict con filepath, language, hash, nodes[], imports[], calls[], errors[]
    """
    result: dict[str, Any] = {
        "filepath": filepath,
        "language": "unknown",
        "hash": "",
        "nodes": [],
        "imports": [],
        "calls": [],
        "errors": [],
    }

    if not os.path.isfile(filepath):
        result["errors"].append(f"File not found: {filepath}")
        return result

    ext = os.path.splitext(filepath)[1].lower()

    # Seleziona linguaggio
    if ext in (".js", ".jsx", ".mjs", ".cjs"):
        if not _HAS_JS:
            result["errors"].append("tree-sitter-javascript not installed")
            return result
        lang = _JS_LANG
        result["language"] = "javascript"
    elif ext in (".ts", ".tsx", ".mts", ".cts"):
        if not _HAS_TS:
            result["errors"].append("tree-sitter-typescript not installed")
            return result
        lang = _TS_LANG
        result["language"] = "typescript"
    else:
        result["errors"].append(f"Unsupported extension: {ext}")
        return result

    try:
        with open(filepath, "r", encoding="utf-8", errors="surrogateescape") as f:
            source = f.read()
    except OSError as e:
        result["errors"].append(f"Read error: {e}")
        return result

    result["hash"] = hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]

    try:
        parser = Parser(lang)
        tree = parser.parse(bytes(source, "utf-8"))
    except Exception as e:
        result["errors"].append(f"Parse error: {e}")
        return result

    _extract_nodes(tree.root_node, source, filepath, result)

    return result


def _node_text(node, source: str) -> str:
    """Estrae il testo pulito da un nodo tree-sitter."""
    try:
        text = source[node.start_byte:node.end_byte]
        return text.strip()
    except Exception:
        return ""


def _extract_name_from_line(line: str, node_type: str) -> str:
    """Estrae il nome di classe/funzione dalla riga sorgente usando regex."""
    if node_type == "class_declaration":
        m = re.search(r"class\s+(\w+)", line)
        return m.group(1) if m else "anonymous"

    if node_type in ("function_declaration", "method_definition", "arrow_function"):
        # function name(...
        m = re.search(r"(?:async\s+)?function\s+(\w+)", line)
        if m:
            return m.group(1)
        # name(...  (method definition)
        m = re.search(r"(?:async\s+)?(\w+)\s*(?:<[^>]*>)?\s*\(|(?<=\.)(\w+)\s*\(", line)
        if m:
            return m.group(1) or m.group(2) or "anonymous"
        # constructor
        if "constructor" in line:
            return "constructor"
        # get/set
        m = re.search(r"(?:get|set)\s+(\w+)", line)
        if m:
            return m.group(1)

    return "anonymous"


def _extract_nodes(node, source: str, filepath: str, result: dict) -> None:
    """Estrae ricorsivamente nodi significativi dall'albero tree-sitter."""
    node_type = node.type
    lines = source.split("\n")

    try:
        if node_type == "class_declaration":
            line = lines[node.start_point[0]] if node.start_point[0] < len(lines) else ""
            name = _extract_name_from_line(line, "class_declaration")

            # Basi (extends)
            bases = []
            m = re.search(r"extends\s+(\w+)", line)
            if m:
                bases.append(m.group(1))

            result["nodes"].append({
                "type": "class",
                "name": name,
                "line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "bases": bases,
                "docstring": "",
                "filepath": filepath,
            })

        elif node_type in ("function_declaration", "method_definition", "arrow_function"):
            line = lines[node.start_point[0]] if node.start_point[0] < len(lines) else ""
            name = _extract_name_from_line(line, node_type)

            # Param: trova tra parentesi
            params = []
            m = re.search(r"\(([^)]*)\)", line)
            if m:
                raw_params = m.group(1).split(",")
                for rp in raw_params:
                    rp = rp.strip()
                    # Prendi solo il nome (prima di : o =)
                    pname = re.split(r"[=:]", rp)[0].strip()
                    if pname and not pname.startswith(("{", "[", "...")):
                        params.append(pname)

            result["nodes"].append({
                "type": "function",
                "name": name,
                "line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "params": params,
                "filepath": filepath,
            })

        elif node_type in ("import_statement", "import_declaration"):
            for child in node.children:
                if child.type == "string":
                    module = _node_text(child, source).strip("\"'")
                    result["imports"].append({
                        "module": module,
                        "line": node.start_point[0] + 1,
                    })

        elif node_type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node:
                callee = _node_text(func_node, source)
                if callee and len(callee) < 80:
                    result["calls"].append({
                        "caller": "(global)",
                        "callee": callee,
                        "line": node.start_point[0] + 1,
                        "type": "calls",
                    })

    except Exception as e:
        logger.debug(f"Error extracting node {node_type}: {e}")

    # Ricorsione sui figli
    for child in node.children:
        _extract_nodes(child, source, filepath, result)
