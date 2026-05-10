# 🔍 craft-code-mapper

**AST-based code analyzer for Craft Memory** — extracts code structure and stores it as a knowledge graph.

[![PyPI version](https://img.shields.io/pypi/v/craft-code-mapper)](https://pypi.org/project/craft-code-mapper/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ Features

- **Zero dependencies for Python** — uses stdlib `ast` module (works anywhere)
- **JavaScript/TypeScript support** — via tree-sitter
- **MCP server** — integrates with Craft Agents OSS as a source
- **Knowledge graph** — saves classes, functions, methods, imports, and call graph to craft-memory
- **24 passing tests** — fully tested and documented

## 🚀 Quick Start

```bash
# Install
pip install craft-code-mapper

# Check craft-memory connection
craft-code-mapper check

# Scan a directory (saves to craft-memory)
craft-code-mapper scan /path/to/project

# Analyze a single file
craft-code-mapper analyze /path/to/file.py
```

## 🔧 Installation

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

| Package | Required | Purpose |
|---------|----------|---------|
| `mcp[fastmcp]` | ✅ | MCP server framework |
| `httpx` | ✅ | HTTP client for craft-memory |
| `tree-sitter` | ✅ | Core tree-sitter library |
| `tree-sitter-javascript` | Recommended | JavaScript analysis |
| `tree-sitter-typescript` | Recommended | TypeScript analysis |

> **Note:** Python analysis works without tree-sitter packages (uses stdlib `ast`).

## 📖 Usage

### CLI Commands

```bash
# Check craft-memory connection
craft-code-mapper check

# Scan a directory (saves to craft-memory)
craft-code-mapper scan /path/to/project

# Dry run (show what would be done without saving)
craft-code-mapper scan /path/to/project --dry-run

# Force re-analysis of unchanged files
craft-code-mapper scan /path/to/project --force

# Analyze a single file
craft-code-mapper analyze /path/to/file.py

# Analyze without saving
craft-code-mapper analyze /path/to/file.py --no-save

# Start MCP server (stdio) for Craft Agents OSS
craft-code-mapper serve
```

### Python API

```python
from craft_code_mapper.analyzers import python_ast, javascript

# Analyze a Python file
result = python_ast.extract_file("/path/to/file.py")
print(f"Classes: {[n['name'] for n in result['nodes'] if n['type'] == 'class']}")
print(f"Imports: {result['imports']}")
print(f"Call graph: {result['calls']}")

# Analyze a JS/TS file
result = javascript.extract_file("/path/to/file.js")
print(f"Functions: {[n['name'] for n in result['nodes'] if n['type'] == 'function']}")
```

### MCP Server (Craft Agents OSS)

Register as a source in your workspace `config.json`:

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

## 📦 Supported Languages

| Language | Extensions | Analyzer | Notes |
|----------|------------|----------|-------|
| Python | `.py`, `.pyw`, `.pyi` | stdlib `ast` | Zero external deps |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` | tree-sitter | Requires `tree-sitter-javascript` |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts` | tree-sitter | Requires `tree-sitter-typescript` |

## 📊 Extracted Information

For each file analyzed:

| Element | Extracted Fields |
|---------|------------------|
| **Classes** | name, line, docstring, base classes (inheritance), methods |
| **Functions** | name, line, params, decorators, async flag |
| **Imports** | module, alias, line |
| **Call Graph** | caller → callee relationships |

### Memory Tags

Nodes are automatically tagged:
- `code:python` / `code:javascript` / `code:typescript` — language
- `type:class` / `type:function` / `type:method` — node type
- `file:filename.py` — source file
- `extends:BaseClass` — inheritance (if applicable)

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_python_ast.py -v

# Run with coverage
pytest tests/ --cov=craft_code_mapper
```

## 📁 Project Structure

```
craft-code-mapper/
├── pyproject.toml           # Package configuration
├── README.md                # This file
├── LICENSE                  # MIT License
├── assets/
│   └── icon.svg             # Project icon
├── src/craft_code_mapper/
│   ├── __init__.py          # Package init (exports __version__)
│   ├── cli.py               # CLI entry point
│   ├── server.py            # MCP server (FastMCP stdio)
│   ├── scanner.py           # Directory scanner + memory save
│   ├── memory_client.py     # HTTP client for craft-memory
│   └── analyzers/
│       ├── __init__.py      # BaseAnalyzer interface
│       ├── python_ast.py    # Python stdlib ast analyzer
│       └── javascript.py    # tree-sitter JS/TS analyzer
└── tests/
    ├── test_python_ast.py   # Python analyzer tests
    ├── test_javascript.py   # JS/TS analyzer tests
    └── test_scanner.py      # Scanner tests
```

## 🔨 Development

```bash
# Clone and setup
git clone https://github.com/matrixNeo76/craft-code-mapper.git
cd craft-code-mapper
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/

# Format
ruff format src/
```

## 📝 Changelog

### v0.2.0 (2026-05-10)
- ✅ Add tree-sitter dependencies to pyproject.toml
- ✅ Fix hash from 16 to 32 chars (collision resistance)
- ✅ Add .pyi stub file support
- ✅ Add retry with exponential backoff in MemoryClient
- ✅ Add visible logging when JS/TS analyzer fails to load
- ✅ Fix O(n²) in `_find_enclosing_function` with context map
- ✅ Extract Python decorators (`@property`, `@staticmethod`, etc.)
- ✅ Add async flag to Python functions
- ✅ Improve encoding with surrogateescape
- ✅ Remove duplicate import in cli.py
- ✅ Remove compress_level=1 (avoid 422 errors)
- ✅ Add comprehensive test suite (24 tests, all passing)
- ✅ Export `__version__` in `__init__.py`

### v0.1.0 (2026-05-04)
- Initial release
- Python AST extraction (stdlib `ast`)
- JavaScript/TypeScript via tree-sitter
- MCP server (FastMCP)
- CLI tools (scan, analyze, serve, check)
- Memory client for craft-memory integration

## 🤝 Contributing

Contributions welcome! Please read the existing tests and follow the same patterns.

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

## 🔗 Links

- **GitHub:** https://github.com/matrixNeo76/craft-code-mapper
- **PyPI:** https://pypi.org/project/craft-code-mapper/
- **craft-memory:** https://github.com/matrixNeo76/craft-memory
- **Craft Agents OSS:** https://github.com/lukilabs/craft-agents-oss