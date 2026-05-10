# Architecture — craft-code-mapper

## Overview

**craft-code-mapper** is a standalone code analysis tool that integrates with **craft-memory** to build a knowledge graph of your codebase. It extracts structural information (classes, functions, methods, imports, call graph) from source code and stores it as memories in craft-memory's SQLite database.

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Source Code                        │
│                   (Python, JS, TS files)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 craft-code-mapper                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  CLI Tool   │  │  MCP Server │  │ Python API  │          │
│  │ scan/analyz │  │ (FastMCP)   │  │ extract_file│          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Scanner                              ││
│  │  Walks directories → picks up .py/.js/.ts files         ││
│  │  Extracts AST via analyzers (stdlib ast / tree-sitter) ││
│  │  Formats nodes as memory content                       ││
│  └──────────────────────┬──────────────────────────────────┘│
└─────────────────────────┼───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  craft-memory                              │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  remember()     │  │  link_memories()│                   │
│  │  → Memory #123   │  │  → Calls edge   │                   │
│  └─────────────────┘  └─────────────────┘                   │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Knowledge Graph (SQLite + FTS5)           ││
│  │  312 memories, 1859 edges, 12 communities               ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Craft Agents OSS (or any MCP client)           │
│  Search, query, visualize the code knowledge graph          │
│  "Find all classes that inherit from BaseClass"             │
│  "Show call graph for function X"                           │
└─────────────────────────────────────────────────────────────┘
```

## Why This Architecture?

### Problem
When working with large codebases, you need to understand:
- What classes and functions exist
- What calls what (call graph)
- What modules import what (dependency graph)
- Where things are defined (line numbers, files)

### Solution
craft-code-mapper extracts this information once and stores it in craft-memory, making it queryable, searchable, and linkable.

### Design Decisions

1. **Zero deps for Python** — uses stdlib `ast`. Works anywhere without installing tree-sitter.
2. **Separation of concerns** — `scanner.py` orchestrates, `analyzers/` do extraction, `memory_client.py` handles storage.
3. **MCP integration** — Can be used as a source in Craft Agents OSS or called directly via CLI/Python.
4. **Resumable** — Files are hashed and tracked. Re-scanning skips unchanged files.

## Component Details

### 1. CLI (`cli.py`)
Entry point for command-line usage.
- `scan <dir>` — Analyze entire directory
- `analyze <file>` — Analyze single file
- `serve` — Start MCP server (stdio)
- `check` — Verify craft-memory connection

### 2. MCP Server (`server.py`)
Exposes `scan_code` and `analyze_file` as MCP tools.
- Transport: stdio (ideal for Craft Agents OSS integration)
- Protocol: MCP (Model Context Protocol)

### 3. Scanner (`scanner.py`)
Orchestrates the analysis pipeline:
1. Walk directory, collect supported files
2. For each file: run appropriate analyzer
3. For each node: save as memory via `MemoryClient`
4. For each call: create `calls` relation in knowledge graph
5. Track file hashes to skip unchanged files

### 4. Analyzers

#### Python (`analyzers/python_ast.py`)
Uses `ast` module from stdlib — no external deps.
- Extracts: classes, functions, methods, async functions, decorators, imports
- Call graph: uses `_build_function_context()` for O(n) lookup

#### JavaScript/TypeScript (`analyzers/javascript.py`)
Uses tree-sitter — requires `tree-sitter-javascript` and `tree-sitter-typescript`.
- Extracts: classes (with extends), functions, method definitions, arrow functions, imports
- Recursive tree-sitter node traversal

### 5. Memory Client (`memory_client.py`)
HTTP client for craft-memory's MCP interface.
- `remember(content, category, importance, tags)` → memory ID
- `link_memories(source_id, target_id, relation)` → creates edge
- `upsert_fact(key, value)` → tracks file hashes
- **Retry with exponential backoff** (3 retries, 1s → 2s → 4s)

## Data Flow Example

```
User runs: craft-code-mapper scan /path/to/project

1. CLI parses args, calls scan_directory()

2. scanner.py walks /path/to/project
   - Finds 42 .py files
   - Filters out __pycache__, node_modules, etc.

3. For each file (e.g., module.py):
   - python_ast.extract_file("/path/to/module.py")
   - Returns: { nodes: [...], imports: [...], calls: [...] }

4. For each node (class MyClass, line 10):
   - _format_node() creates memory content
   - MemoryClient.remember() saves to craft-memory
   - Returns memory_id = 123

5. For each call (caller → callee):
   - MemoryClient.link_memories(123, 456, "calls")

6. Stats returned: "156 nodes, 89 relations created"

7. User queries: search_memory(query="class MyClass")
   - Returns all memories containing "class MyClass"
```

## Integration Points

### With Craft Agents OSS

```json
{
  "slug": "code-mapper",
  "type": "mcp",
  "mcp": {
    "command": "craft-code-mapper",
    "args": ["serve"]
  }
}
```

Enable both sources:
```json
{
  "sources": ["memory", "code-mapper"]
}
```

Then ask: "Analyze my project and show me all classes that have no methods."

### With Other MCP Clients

Since it exposes standard MCP tools, any MCP-compatible client can use it.

### Standalone CLI

No MCP needed — just run from terminal:
```bash
craft-code-mapper scan /path/to/project
```

### Python API

```python
from craft_code_mapper.analyzers import python_ast

result = python_ast.extract_file("/path/to/file.py")
# Use result['nodes'], result['imports'], result['calls']
```

## File Structure

```
craft-code-mapper/
├── pyproject.toml           # Package config + deps
├── src/craft_code_mapper/
│   ├── __init__.py          # Package init (__version__)
│   ├── cli.py               # CLI entry point
│   ├── server.py            # MCP server (FastMCP stdio)
│   ├── scanner.py           # Directory orchestrator
│   ├── memory_client.py      # HTTP client for craft-memory
│   └── analyzers/
│       ├── __init__.py      # BaseAnalyzer interface
│       ├── python_ast.py    # Python stdlib ast
│       └── javascript.py    # tree-sitter JS/TS
└── tests/
    ├── test_python_ast.py   # 8 tests
    ├── test_javascript.py  # 7 tests
    └── test_scanner.py      # 9 tests
```

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 0.1.0 | 2026-05-04 | Initial release, Python + JS/TS, MCP server |
| 0.2.0 | 2026-05-10 | Fixes: tree-sitter deps, hash 32 chars, retry, logging, tests, decorators, async flag |

## Related Projects

- **[craft-memory](https://github.com/matrixNeo76/craft-memory)** — The knowledge graph backend where analysis results are stored
- **[Craft Agents OSS](https://github.com/lukilabs/craft-agents-oss)** — The AI agent platform that uses craft-code-mapper as a source