#!/usr/bin/env python
"""
Craft Code Mapper — CLI.

Comandi:
  scan <directory>              Analizza directory e salva in craft-memory
  analyze <filepath>            Analizza un singolo file
  serve                         Avvia server MCP (stdio)
  check                         Verifica connessione a craft-memory
"""

import argparse
import sys
import os


def check_memory(memory_url: str) -> bool:
    """Verifica che craft-memory sia raggiungibile."""
    try:
        import httpx
        resp = httpx.post(
            memory_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=5,
        )
        if resp.status_code == 200:
            result = resp.json()
            tools = result.get("result", {}).get("tools", [])
            print(f"OK: craft-memory reachable at {memory_url} ({len(tools)} tools)")
            return True
        else:
            print(f"FAIL: craft-memory returned HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"FAIL: Cannot connect to craft-memory at {memory_url}: {e}")
        return False


def cmd_scan(args):
    """Esegue una scansione completa della directory."""
    if not args.no_check:
        if not check_memory(args.memory_url):
            print("ERROR: craft-memory is not reachable. Use --no-check to skip.")
            sys.exit(1)

    # Progress callback
    last_pct = -1
    def progress(current, total, errors):
        nonlocal last_pct
        pct = (current * 100) // total if total else 100
        if pct != last_pct:
            print(f"\r  Progress: {current}/{total} files ({pct}%)  errors={errors}", end="", flush=True)
            last_pct = pct

    from craft_code_mapper.scanner import scan_directory

    print(f"Scanning: {os.path.abspath(args.directory)}")
    print(f"  Memory URL: {args.memory_url}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Force: {args.force}")
    print()

    stats = scan_directory(
        directory=args.directory,
        memory_url=args.memory_url,
        dry_run=args.dry_run,
        force=args.force,
        progress_cb=progress,
    )

    print("\n")
    print(f"Results:")
    print(f"  Files found:     {stats['files_found']}")
    print(f"  Files analyzed:  {stats['files_analyzed']}")
    print(f"  Files skipped:   {stats['files_skipped_hash']}")
    print(f"  Files errored:   {stats['files_errored']}")
    print(f"  Nodes extracted: {stats['nodes_found']}")
    print(f"  Memories saved:  {stats['memories_created']}")
    print(f"  Relations:       {stats['relations_created']}")
    print(f"  Imports:         {stats['imports_found']}")
    print(f"  Duration:        {stats['duration_sec']}s")

    if stats["errors"]:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats["errors"][:10]:
            print(f"  - {err}")

    if stats["files_errored"] > 0:
        sys.exit(1)


def cmd_analyze(args):
    """Analizza un singolo file."""
    from craft_code_mapper.server import analyze_file

    result = analyze_file(
        filepath=args.filepath,
        memory_url=args.memory_url,
        dry_run=args.dry_run or args.no_save,
    )
    print(result)


def cmd_serve(args):
    """Avvia server MCP in modalità stdio."""
    from craft_code_mapper.server import run_server
    run_server()


def cmd_check(args):
    """Verifica connessione a craft-memory."""
    check_memory(args.memory_url)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="craft-code-mapper",
        description="AST-based code analyzer for Craft Memory",
    )
    parser.add_argument("--memory-url", default="http://127.0.0.1:8392/mcp",
                        help="craft-memory MCP URL")

    sub = parser.add_subparsers(dest="command", help="Commands")

    p_scan = sub.add_parser("scan", help="Scan directory and save to craft-memory")
    p_scan.add_argument("directory", help="Directory to scan")
    p_scan.add_argument("--dry-run", action="store_true", help="Don't save to memory")
    p_scan.add_argument("--force", action="store_true", help="Re-analyze unchanged files")
    p_scan.add_argument("--no-check", action="store_true", help="Skip memory connection check")

    p_analyze = sub.add_parser("analyze", help="Analyze a single file")
    p_analyze.add_argument("filepath", help="File to analyze")
    p_analyze.add_argument("--no-save", action="store_true", help="Don't save to memory")

    sub.add_parser("serve", help="Start MCP server (stdio)")

    sub.add_parser("check", help="Check craft-memory connection")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "check":
        cmd_check(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
