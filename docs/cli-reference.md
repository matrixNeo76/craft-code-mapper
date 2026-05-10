# CLI Quick Reference — craft-code-mapper

## Installation
```bash
pip install craft-code-mapper
```

## First Steps
```bash
# 1. Ensure craft-memory is running
craft-memory ensure

# 2. Check connection
craft-code-mapper check

# 3. Scan your project
craft-code-mapper scan /path/to/project
```

---

## Commands

### `check`
Verify craft-memory connection.
```bash
craft-code-mapper check
# Output: OK: craft-memory reachable at http://127.0.0.1:8392/mcp (57 tools)
```

### `scan <directory>`
Analyze directory and save to craft-memory.
```bash
# Basic
craft-code-mapper scan ./myproject

# Dry run (don't save)
craft-code-mapper scan ./myproject --dry-run

# Force re-analyze unchanged files
craft-code-mapper scan ./myproject --force

# Skip connection check
craft-code-mapper scan ./myproject --no-check

# Custom memory URL
craft-code-mapper scan ./myproject --memory-url http://localhost:8392/mcp
```

### `analyze <filepath>`
Analyze single file.
```bash
# Analyze and save
craft-code-mapper analyze ./src/module.py

# Analyze without saving
craft-code-mapper analyze ./src/module.py --no-save

# Custom memory URL
craft-code-mapper analyze ./src/module.py --memory-url http://localhost:8392/mcp
```

### `serve`
Start MCP server (stdio mode). Used by Craft Agents OSS.
```bash
craft-code-mapper serve
# Runs indefinitely, listening for MCP commands
```

---

## MCP Tools (when using `serve`)

### `scan_code(directory, memory_url?, dry_run?, force?)`
```json
{
  "directory": "/path/to/project",
  "memory_url": "http://127.0.0.1:8392/mcp",
  "dry_run": false,
  "force": false
}
```

### `analyze_file(filepath, memory_url?, dry_run?)`
```json
{
  "filepath": "/path/to/file.py",
  "memory_url": "http://127.0.0.1:8392/mcp",
  "dry_run": false
}
```

---

## Common Workflows

### Scan entire project
```bash
craft-code-mapper scan . --force
```

### Scan with progress
```bash
craft-code-mapper scan ./myproject
# Shows: Progress: 42/100 files (42%) errors=0
```

### Analyze a single file (debug)
```bash
craft-code-mapper analyze ./src/module.py --no-save
```

---

## Exit Codes
- `0` — Success
- `1` — Error (e.g., files errored during scan)

---

## Examples

### Full project analysis
```bash
$ craft-code-mapper scan ./src
Scanning: C:\Users\...\src
  Memory URL: http://127.0.0.1:8392/mcp
  Dry run: False

Results:
  Files found:     156
  Files analyzed:  152
  Files skipped:   4
  Files errored:   0
  Nodes extracted: 423
  Memories saved:  423
  Relations:       198
  Imports:         892
  Duration:        12.45s
```

### Analyze single file
```bash
$ craft-code-mapper analyze ./src/utils.py
Analysis of: C:\Users\...\src\utils.py
  Language: python
  Hash: a1b2c3d4e5f67890...
  Nodes: 8
  Imports: 3
  Calls: 12

Nodes:
  [class] ConfigManager (line 15)
  [function] load_config (line 45)
  [function] save_config (line 62)
  [method] ConfigManager.get (line 22)

Saved: 8 memories in craft-memory
```

---

## Help
```bash
craft-code-mapper --help
craft-code-mapper scan --help
craft-code-mapper analyze --help
```