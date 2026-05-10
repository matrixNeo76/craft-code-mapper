# craft-code-mapper

AST-based code analyzer for Craft Memory — extracts code structure and stores it as a knowledge graph.

## Features

- **Zero dependencies for Python** — uses stdlib `ast` module
- **JavaScript/TypeScript support** — via tree-sitter
- **MCP server** — integrates with Craft Agents OSS as a source
- **Knowledge graph** — saves classes, functions, methods, imports, and call graph to craft-memory
- **CLI tools** — scan directories, analyze files, serve MCP server

## Installation

```bash
pip install craft-code-mapper
```

Or for development:

```bash
git clone https://github.com/matrixNeo76/craft-code-mapper.git
cd craft-code-mapper
pip install -e .
```

### Dependencies

- Python 3.10+
- `mcp[fastmcp]` — MCP server framework
- `httpx` — HTTP client for craft-memory
- `tree-sitter` + `tree-sitter-javascript` + `tree-sitter-typescript` — for JS/TS analysis

## Usage

### CLI

```bash
# Check craft-memory connection
craft-code-mapper check

# Scan a directory (saves to craft-memory)
craft-code-mapper scan /path/to/project

# Dry run (show what would be done without saving)
craft-code-mapper scan /path/to/project --dry-run

# Analyze a single file
craft-code-mapper analyze /path/to/file.py

# Start MCP server (stdio)
craft-code-mapper serve
```

### Python API

```python
from craft_code_mapper.analyzers import python_ast, javascript

# Analyze a Python file
result = python_ast.extract_file("/path/to/file.py")
print(f"Classes: {result['nodes']}")
print(f"Imports: {result['imports']}")
print(f"Calls: {result['calls']}")

# Analyze a JS/TS file
result = javascript.extract_file("/path/to/file.js")
print(f"Nodes: {result['nodes']}")
```

### MCP Server (Craft Agents OSS)

Register as a source in your workspace:

```json
{
  "slug": "code-mapper",
  "type": "mcp",
  "mcp": {
    "transport": "stdio",
    "command": "craft-code-mapper",
    "args": ["serve"]
  }
}
```

Then use the `scan_code` and `analyze_file` MCP tools.

## Supported Languages

| Language | Extensions | Analyzer |
|----------|-----------|----------|
| Python | `.py`, `.pyw`, `.pyi` | stdlib `ast` |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` | tree-sitter |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts` | tree-sitter |

## Extracted Information

- **Classes** — name, line, docstring, base classes
- **Functions/Methods** — name, line, params, decorators, async flag
- **Imports** — module, alias, line
- **Call graph** — caller → callee relationships

## Project Structure

```
src/craft_code_mapper/
├── __init__.py
├── cli.py           # CLI entry point
├── server.py        # MCP server (FastMCP)
├── scanner.py       # Directory scanner + memory save
├── memory_client.py # HTTP client for craft-memory
└── analyzers/
    ├── __init__.py  # BaseAnalyzer interface
    ├── python_ast.py
    └── javascript.py
```

## License

MIT

## Links

- GitHub: https://github.com/matrixNeo76/craft-code-mapper
- craft-memory: https://github.com/matrixNeo76/craft-memory