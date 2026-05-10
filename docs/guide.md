# User Guide — craft-code-mapper

## What is craft-code-mapper?

**craft-code-mapper** is a tool that analyzes your source code (Python, JavaScript, TypeScript) and stores the extracted information in **craft-memory** as a knowledge graph.

### What does it extract?

For each file it analyzes, it extracts:
- **Classes** — name, line number, docstring, base classes, methods
- **Functions/Methods** — name, line number, parameters, decorators, async flag
- **Imports** — which modules are imported, with aliases
- **Call Graph** — which function calls which other function

### Why would I use it?

Imagine you have a large codebase and want to:
- Find all classes that inherit from `BaseClass`
- See which functions call a specific function (upstream callers)
- Find unused imports or duplicate function definitions
- Understand the architecture of a new project
- Create documentation automatically from code structure

craft-code-mapper makes all this information searchable and queryable.

---

## Quick Example

### 1. Install craft-code-mapper

```bash
pip install craft-code-mapper
```

### 2. Ensure craft-memory is running

```bash
craft-memory ensure
```

### 3. Scan your project

```bash
craft-code-mapper scan /path/to/your/project
```

Output:
```
Scanning: C:\path\to\your\project
  Memory URL: http://127.0.0.1:8392/mcp
  Dry run: False

Results:
  Files found:     42
  Files analyzed:  38
  Files skipped:   4
  Files errored:   0
  Nodes extracted: 156
  Memories saved:  156
  Relations:       89
  Imports:         234
  Duration:        3.21s
```

### 4. Query the knowledge graph

Now in Craft Agents OSS (or any MCP client):

```
search_memory(query="class MyClass", tags=["code:python"])
```

Returns all classes named `MyClass` found in your project.

---

## Installation Options

### Option 1: pip install (recommended)

```bash
pip install craft-code-mapper
```

### Option 2: Development installation

```bash
git clone https://github.com/matrixNeo76/craft-code-mapper.git
cd craft-code-mapper
pip install -e .
```

### Option 3: As a Craft Agents OSS source

Add to your workspace config:

```json
{
  "slug": "code-mapper",
  "type": "mcp",
  "enabled": true,
  "mcp": {
    "transport": "stdio",
    "command": "craft-code-mapper",
    "args": ["serve"]
  }
}
```

---

## CLI Commands

### `craft-code-mapper check`

Verify that craft-memory is reachable.

```bash
$ craft-code-mapper check
OK: craft-memory reachable at http://127.0.0.1:8392/mcp (57 tools)
```

### `craft-code-mapper scan <directory>`

Analyze a directory and save results to craft-memory.

```bash
# Basic usage
craft-code-mapper scan ./myproject

# Dry run (show what would happen without saving)
craft-code-mapper scan ./myproject --dry-run

# Force re-analysis of unchanged files
craft-code-mapper scan ./myproject --force

# Skip the connection check (if craft-memory is down)
craft-code-mapper scan ./myproject --no-check
```

### `craft-code-mapper analyze <filepath>`

Analyze a single file.

```bash
# Analyze and save to craft-memory
craft-code-mapper analyze ./src/module.py

# Analyze without saving (dry run)
craft-code-mapper analyze ./src/module.py --no-save
```

### `craft-code-mapper serve`

Start the MCP server (stdio mode). Used automatically when integrated with Craft Agents OSS.

```bash
craft-code-mapper serve
# Server runs on stdio, waiting for MCP commands
```

---

## MCP Tools

When running as an MCP server (via `craft-code-mapper serve`), the following tools are available:

### `scan_code(directory, memory_url?, dry_run?, force?)`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `directory` | string | ✅ | - | Directory to scan |
| `memory_url` | string | ❌ | `http://127.0.0.1:8392/mcp` | craft-memory URL |
| `dry_run` | boolean | ❌ | `false` | Don't save to memory |
| `force` | boolean | ❌ | `false` | Re-analyze unchanged files |

**Example:**
```
scan_code(directory="/path/to/project", force=true)
```

**Returns:**
```
Code analysis complete: /path/to/project
  Files found: 42
  Files analyzed: 38
  Nodes extracted: 156
  Memories created: 156
  Relations created: 89
  Duration: 3.21s
```

### `analyze_file(filepath, memory_url?, dry_run?)`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filepath` | string | ✅ | - | File to analyze |
| `memory_url` | string | ❌ | `http://127.0.0.1:8392/mcp` | craft-memory URL |
| `dry_run` | boolean | ❌ | `false` | Don't save to memory |

**Example:**
```
analyze_file(filepath="/path/to/file.py", dry_run=true)
```

**Returns:**
```
Analysis of: /path/to/file.py
  Language: python
  Hash: a1b2c3d4e5f6...
  Nodes: 12
  Imports: 5
  Calls: 8

Nodes:
  [class] MyClass (line 10)
  [function] my_function (line 25)
  [method] MyClass.method (line 15)
```

---

## Python API

You can use craft-code-mapper directly in Python scripts:

### `extract_file()`

```python
from craft_code_mapper.analyzers import python_ast, javascript

# Python analysis
result = python_ast.extract_file("/path/to/file.py")
print(f"Classes: {result['nodes']}")
print(f"Imports: {result['imports']}")
print(f"Calls: {result['calls']}")
```

**Returns:**
```python
{
    "filepath": "/path/to/file.py",
    "language": "python",
    "hash": "a1b2c3d4e5f67890...",
    "nodes": [
        {
            "type": "class",
            "name": "MyClass",
            "line": 10,
            "end_line": 20,
            "docstring": "A sample class.",
            "bases": ["BaseClass"],
            "decorators": [],
            "filepath": "/path/to/file.py"
        },
        {
            "type": "function",
            "name": "my_function",
            "line": 25,
            "end_line": 30,
            "docstring": "A sample function.",
            "params": ["a", "b"],
            "decorators": ["staticmethod"],
            "is_async": False,
            "filepath": "/path/to/file.py"
        }
    ],
    "imports": [
        {"module": "os", "alias": None, "line": 1},
        {"module": "sys", "alias": "system", "line": 2}
    ],
    "calls": [
        {"caller": "my_function", "callee": "helper", "line": 28, "type": "calls"}
    ],
    "errors": []
}
```

---

## Use Cases

### 1. Code Review

Before a code review, scan the codebase:
```bash
craft-code-mapper scan /path/to/project
```

Then in Craft Agents OSS, you can:
- Find large classes (> 500 lines)
- Find functions with no docstrings
- Find classes with many children (complex inheritance)

### 2. Onboarding

When joining a new project:
```bash
craft-code-mapper scan /path/to/new-project --dry-run
```

Understand the structure:
- What are the main classes?
- What's the call graph?
- What's the import dependency structure?

### 3. Refactoring Support

Before refactoring:
```bash
craft-code-mapper scan /path/to/project --force
```

Find all callers of a function you want to change:
```
search_memory(query="calls helper_function")
```

### 4. Documentation Generation

Extract all public APIs:
```
search_memory(query="function", tags=["code:python"])
```

---

## Troubleshooting

### "Cannot connect to craft-memory"

craft-memory is not running. Start it:
```bash
craft-memory ensure
```

### "tree-sitter not available"

JavaScript/TypeScript files won't be analyzed. Install tree-sitter packages:
```bash
pip install tree-sitter tree-sitter-javascript tree-sitter-typescript
```

### "Files not being analyzed"

Check if files are in ignored directories:
- `node_modules`
- `.git`
- `__pycache__`
- `venv`
- `dist`
- `build`

### "No memories created"

Check that craft-memory is running and accepting connections:
```bash
craft-code-mapper check
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CRAFT_MEMORY_URL` | `http://127.0.0.1:8392/mcp` | craft-memory MCP URL |

### Ignored Directories

The following directories are automatically skipped:
- `node_modules`, `.git`, `__pycache__`
- `venv`, `.venv`, `env`
- `dist`, `build`, `target`
- `.egg-info`, `coverage`, `.next`

### Supported Extensions

| Language | Extensions | Analyzer |
|----------|------------|----------|
| Python | `.py`, `.pyw`, `.pyi` | stdlib `ast` |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` | tree-sitter |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts` | tree-sitter |

---

## Performance Notes

- **Python analysis**: Very fast (stdlib `ast`), no external deps
- **JS/TS analysis**: Requires tree-sitter parsers, slower but comprehensive
- **Re-scanning**: Uses file hashes to skip unchanged files
- **Memory usage**: O(n) where n = number of lines in analyzed files
- **Call graph**: O(n) lookup via pre-built context map

---

## Getting Help

- **GitHub Issues:** https://github.com/matrixNeo76/craft-code-mapper/issues
- **Documentation:** https://github.com/matrixNeo76/craft-code-mapper#readme
- **craft-memory:** https://github.com/matrixNeo76/craft-memory