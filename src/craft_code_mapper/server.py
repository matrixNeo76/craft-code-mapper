#!/usr/bin/env python
"""
Craft Code Mapper — MCP Server.

Espone tool per l'analisi statica di codice tramite MCP (Model Context Protocol).
Può essere usato come source in Craft Agents OSS o chiamato direttamente.

Trasporto: stdio (default), ideale per integrazione come source MCP.
"""

import sys
import os

# Assicura che src sia nel path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.server.fastmcp import FastMCP

from craft_code_mapper.scanner import scan_directory

mcp = FastMCP(
    "craft-code-mapper",
    instructions="""Craft Code Mapper — Analisi statica di codice.

Analizza file Python, JavaScript e TypeScript estraendo:
- Classi, funzioni, metodi
- Import e dipendenze
- Call graph (chi chiama cosa)
- Relazioni di ereditarietà

I risultati vengono salvati in craft-memory come memorie nel knowledge graph.

Comandi tipici:
  scan_code(directory="/path/to/project") — analisi completa
""",
)


@mcp.tool()
def scan_code(
    directory: str,
    memory_url: str = "http://127.0.0.1:8392/mcp",
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """Analizza una directory di codice e salva i risultati in craft-memory.

    Supporta: .py, .js, .jsx, .ts, .tsx, .mjs, .cjs, .mts, .cts

    Args:
        directory: Directory del progetto da analizzare
        memory_url: URL di craft-memory (default: http://127.0.0.1:8392/mcp)
        dry_run: Se True, mostra cosa farebbe senza salvare
        force: Se True, ri-analizza anche file invariati

    Returns:
        Statistiche dell'analisi
    """
    stats = scan_directory(
        directory=directory,
        memory_url=memory_url,
        dry_run=dry_run,
        force=force,
    )

    lines = [
        f"Code analysis complete: {os.path.abspath(directory)}",
        f"  Files found: {stats['files_found']}",
        f"  Files analyzed: {stats['files_analyzed']}",
        f"  Files skipped (dry): {stats['files_skipped_hash']}",
        f"  Files errored: {stats['files_errored']}",
        f"  Nodes extracted: {stats['nodes_found']}",
        f"  Memories created: {stats['memories_created']}",
        f"  Relations created: {stats['relations_created']}",
        f"  Imports found: {stats['imports_found']}",
        f"  Duration: {stats['duration_sec']}s",
    ]

    if stats["errors"]:
        lines.append(f"\nErrors ({len(stats['errors'])}):")
        for err in stats["errors"][:10]:
            lines.append(f"  - {err}")

    return "\n".join(lines)


@mcp.tool()
def analyze_file(
    filepath: str,
    memory_url: str = "http://127.0.0.1:8392/mcp",
    dry_run: bool = False,
) -> str:
    """Analizza un singolo file e opzionalmente lo salva in craft-memory.

    Args:
        filepath: Percorso del file da analizzare
        memory_url: URL di craft-memory
        dry_run: Se True, mostra solo i risultati senza salvare

    Returns:
        Risultati dell'analisi del file
    """
    import os
    from craft_code_mapper.scanner import _ANALYZERS

    if not os.path.isfile(filepath):
        return f"File not found: {filepath}"

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in _ANALYZERS:
        return f"Unsupported file type: {ext}"

    lang_name, analyzer = _ANALYZERS[ext]
    result = analyzer.extract_file(filepath)

    lines = [
        f"Analysis of: {filepath}",
        f"  Language: {lang_name}",
        f"  Hash: {result.get('hash', 'N/A')}",
        f"  Nodes: {len(result['nodes'])}",
        f"  Imports: {len(result['imports'])}",
        f"  Calls: {len(result.get('calls', []))}",
    ]

    if result.get("errors"):
        lines.append(f"\nErrors:")
        for e in result["errors"]:
            lines.append(f"  - {e}")

    if result["nodes"]:
        lines.append(f"\nNodes:")
        for n in result["nodes"][:20]:
            lines.append(f"  [{n['type']}] {n['name']} (line {n.get('line', '?')})")

    if result["imports"]:
        lines.append(f"\nImports ({len(result['imports'])}):")
        for imp in result["imports"][:15]:
            lines.append(f"  {imp['module']}")

    if not dry_run:
        # Salva in memory
        from craft_code_mapper.scanner import _format_node, _node_importance
        from craft_code_mapper.memory_client import MemoryClient

        client = MemoryClient(memory_url)
        try:
            saved = 0
            for node in result["nodes"]:
                content = _format_node(node, filepath)
                tags = [f"code:{lang_name}", f"type:{node['type']}"]
                mem_id = client.remember(
                    content=content,
                    category="discovery",
                    importance=_node_importance(node),
                    tags=tags,
                )
                if mem_id is not None:
                    saved += 1
            lines.append(f"\nSaved: {saved} memories in craft-memory")
        finally:
            client.close()

    return "\n".join(lines)


def run_server():
    """Avvia il server MCP (trasporto stdio)."""
    mcp.run(transport="stdio")
