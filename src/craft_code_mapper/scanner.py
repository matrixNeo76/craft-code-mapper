"""
Scanner orchestratore — cammina directory, analizza file, salva in craft-memory.
"""

import hashlib
import logging
import os
import time
from typing import Any

from craft_code_mapper.analyzers import python_ast, javascript
from craft_code_mapper.memory_client import MemoryClient

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(name)s: %(levelname)s: %(message)s",
    )

# Mappatura estensione → analizzatore
_ANALYZERS: dict[str, Any] = {}

# Python AST (stdlib, sempre disponibile)
_ANALYZERS[".py"] = ("python", python_ast)
_ANALYZERS[".pyw"] = ("python", python_ast)
_ANALYZERS[".pyi"] = ("python", python_ast)  # Python stub files

# JavaScript (via tree-sitter, se disponibile)
try:
    javascript.extract_file  # verifica import
    _ANALYZERS[".js"] = ("javascript", javascript)
    _ANALYZERS[".jsx"] = ("javascript", javascript)
    _ANALYZERS[".mjs"] = ("javascript", javascript)
    _ANALYZERS[".cjs"] = ("javascript", javascript)
    _ANALYZERS[".ts"] = ("typescript", javascript)
    _ANALYZERS[".tsx"] = ("typescript", javascript)
    _ANALYZERS[".mts"] = ("typescript", javascript)
    _ANALYZERS[".cts"] = ("typescript", javascript)
except Exception:
    pass

# Directory da ignorare
IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv",
    ".tox", "dist", "build", ".egg-info", "env", ".env",
    "coverage", ".next", ".nuxt", ".cache", "target",
}


def scan_directory(
    directory: str,
    memory_url: str = "http://127.0.0.1:8392/mcp",
    dry_run: bool = False,
    force: bool = False,
    progress_cb: callable = None,
) -> dict[str, Any]:
    """Analizza ricorsivamente una directory e salva i risultati in craft-memory.

    Args:
        directory: Directory da analizzare
        memory_url: URL del server MCP di craft-memory
        dry_run: Se True, non salva nulla
        force: Se True, ri-analizza anche file invariati
        progress_cb: Callback opzionale (file_analyzed, total_files, errors)

    Returns:
        Statistiche dell'analisi
    """
    start_time = time.time()
    stats: dict[str, Any] = {
        "directory": os.path.abspath(directory),
        "files_found": 0,
        "files_analyzed": 0,
        "files_skipped_hash": 0,
        "files_errored": 0,
        "nodes_found": 0,
        "memories_created": 0,
        "relations_created": 0,
        "imports_found": 0,
        "errors": [],
        "duration_sec": 0,
    }

    # Cache dei memory_id: { (filepath, node_name): memory_id }
    memory_cache: dict[tuple[str, str], int] = {}

    client = None if dry_run else MemoryClient(memory_url)

    try:
        # Raccogli file supportati
        all_files = []
        for root, dirs, files in os.walk(directory):
            # Salta directory ignorate
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in _ANALYZERS:
                    all_files.append(os.path.join(root, f))

        stats["files_found"] = len(all_files)

        for idx, filepath in enumerate(all_files):
            ext = os.path.splitext(filepath)[1].lower()
            lang_name, analyzer = _ANALYZERS[ext]

            try:
                result = analyzer.extract_file(filepath)
            except Exception as e:
                logger.error(f"Analyze error {filepath}: {e}")
                stats["files_errored"] += 1
                stats["errors"].append(f"{filepath}: {e}")
                if progress_cb:
                    progress_cb(idx + 1, len(all_files), stats["files_errored"])
                continue

            if result.get("errors"):
                stats["files_errored"] += 1
                stats["errors"].extend(
                    f"{filepath}: {e}" for e in result["errors"]
                )
                if progress_cb:
                    progress_cb(idx + 1, len(all_files), stats["files_errored"])
                continue

            # Verifica hash (skip se non cambiato, a meno che force)
            if not force and not dry_run:
                fact_key = f"filehash:{filepath}"
                # Non possiamo verificare facilmente senza query — skip per ora
                # L'upsert_fact sottostante aggiornerà l'hash

            stats["files_analyzed"] += 1
            stats["nodes_found"] += len(result["nodes"])
            stats["imports_found"] += len(result["imports"])

            if dry_run:
                if progress_cb:
                    progress_cb(idx + 1, len(all_files), stats["files_errored"])
                continue

            # Salva ogni nodo come memoria in craft-memory
            for node in result["nodes"]:
                content = _format_node(node, filepath)
                tags = [f"code:{lang_name}", f"type:{node['type']}", f"file:{os.path.basename(filepath)}"]
                if node.get("bases"):
                    for base in node["bases"]:
                        tags.append(f"extends:{base}")

                importance = _node_importance(node)

                mem_id = client.remember(
                    content=content,
                    category="discovery",
                    importance=importance,
                    tags=tags,
                )

                if mem_id is not None:
                    stats["memories_created"] += 1
                    key = (filepath, node["name"])
                    memory_cache[key] = mem_id

            # Crea relazioni (call graph)
            for call in result.get("calls", []):
                caller_name = call.get("caller", "")
                callee_name = call.get("callee", "")

                caller_id = memory_cache.get((filepath, caller_name))
                callee_id = memory_cache.get((filepath, callee_name))

                # Cerca anche in altri file
                if callee_id is None:
                    for (fp, name), mid in memory_cache.items():
                        if name == callee_name and fp != filepath:
                            callee_id = mid
                            break

                if caller_id is not None and callee_id is not None:
                    relation = "calls" if call.get("type") == "calls" else "extends"
                    if client.link_memories(caller_id, callee_id, relation):
                        stats["relations_created"] += 1

            # Registra hash file per skip futuro
            if result.get("hash"):
                client.upsert_fact(
                    f"filehash:{os.path.abspath(filepath)}",
                    result["hash"],
                )

            if progress_cb:
                progress_cb(idx + 1, len(all_files), stats["files_errored"])

    finally:
        if client:
            client.close()

    stats["duration_sec"] = round(time.time() - start_time, 2)
    return stats


def _format_node(node: dict, filepath: str) -> str:
    """Formatta un nodo AST come memoria testuale."""
    name = node["name"]
    node_type = node["type"]
    line = node.get("line", "?")
    rel_path = os.path.relpath(filepath, start=os.path.dirname(filepath) or ".")

    parts = [f"[{node_type}] {name}"]
    parts.append(f"  Defined in: {rel_path} at line {line}")

    if node.get("params"):
        parts.append(f"  Params: {', '.join(node['params'])}")

    if node.get("bases"):
        parts.append(f"  Extends: {', '.join(node['bases'])}")

    if node.get("docstring"):
        parts.append(f"  Doc: {node['docstring'][:200]}")

    return "\n".join(parts)


def _node_importance(node: dict) -> int:
    """Calcola importanza in base al tipo di nodo."""
    type_map = {
        "class": 7,
        "function": 6,
        "method": 5,
        "variable": 3,
    }
    return type_map.get(node.get("type", ""), 5)
