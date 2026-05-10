"""Tests per craft_code_mapper.scanner."""

import os
import tempfile
import shutil
from craft_code_mapper import scanner


def test_scan_python_files():
    """Test scansione directory con file Python."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Crea alcuni file Python
        os.makedirs(os.path.join(tmpdir, 'subdir'))
        
        with open(os.path.join(tmpdir, 'module1.py'), 'w') as f:
            f.write('def func1():\n    pass\n')
        
        with open(os.path.join(tmpdir, 'subdir', 'module2.py'), 'w') as f:
            f.write('class MyClass:\n    def method(self):\n        pass\n')
        
        stats = scanner.scan_directory(
            tmpdir,
            memory_url='http://127.0.0.1:8392/mcp',
            dry_run=True,  # Non salva in memory per test
        )
        
        assert stats['files_found'] >= 2
        assert stats['files_analyzed'] >= 2


def test_ignore_dirs():
    """Test che directory ignorate non vengano scannerizzate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # File in directory normale
        with open(os.path.join(tmpdir, 'normal.py'), 'w') as f:
            f.write('x = 1\n')
        
        # File in node_modules (dovrebbe essere ignorato)
        node_modules = os.path.join(tmpdir, 'node_modules')
        os.makedirs(node_modules)
        with open(os.path.join(node_modules, 'fake.py'), 'w') as f:
            f.write('export default 1\n')
        
        stats = scanner.scan_directory(
            tmpdir,
            memory_url='http://127.0.0.1:8392/mcp',
            dry_run=True,
        )
        
        # Solo normal.py dovrebbe essere trovato
        assert stats['files_found'] == 1


def test_progress_callback():
    """Test che progress callback venga chiamato."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, 'test.py'), 'w') as f:
            f.write('def test():\n    pass\n')
        
        calls = []
        def progress(current, total, errors):
            calls.append((current, total, errors))
        
        stats = scanner.scan_directory(
            tmpdir,
            memory_url='http://127.0.0.1:8392/mcp',
            dry_run=True,
            progress_cb=progress,
        )
        
        assert len(calls) > 0
        assert calls[-1][0] == stats['files_analyzed']


def test_unsupported_files():
    """Test che file non supportati vengano ignorati."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, 'script.py'), 'w') as f:
            f.write('x = 1\n')
        
        with open(os.path.join(tmpdir, 'data.txt'), 'w') as f:
            f.write('some text\n')
        
        with open(os.path.join(tmpdir, 'script.java'), 'w') as f:
            f.write('public class Foo {}\n')
        
        stats = scanner.scan_directory(
            tmpdir,
            memory_url='http://127.0.0.1:8392/mcp',
            dry_run=True,
        )
        
        # Solo .py dovrebbe essere analizzato
        assert stats['files_found'] == 1
        assert stats['files_found'] <= 3


def test_analyzers_mapping():
    """Test che gli analizzatori siano correttamente registrati."""
    # Verifica che Python sia sempre disponibile
    assert '.py' in scanner._ANALYZERS
    assert '.pyw' in scanner._ANALYZERS
    assert '.pyi' in scanner._ANALYZERS
    
    # Verifica che almeno .js/.ts siano registrati (o None se tree-sitter non disponibile)
    exts = set(scanner._ANALYZERS.keys())
    assert '.js' in exts or '.ts' in exts


def test_format_node():
    """Test formattazione nodo come memoria."""
    node = {
        'type': 'class',
        'name': 'MyClass',
        'line': 10,
        'params': ['self', 'x'],
        'docstring': 'A sample class',
    }
    
    formatted = scanner._format_node(node, '/path/to/file.py')
    
    assert '[class] MyClass' in formatted
    assert 'line 10' in formatted
    assert 'A sample class' in formatted


def test_node_importance():
    """Test calcolo importanza nodi."""
    assert scanner._node_importance({'type': 'class'}) == 7
    assert scanner._node_importance({'type': 'function'}) == 6
    assert scanner._node_importance({'type': 'method'}) == 5
    assert scanner._node_importance({'type': 'variable'}) == 3
    assert scanner._node_importance({'type': 'unknown'}) == 5  # default


def test_error_handling():
    """Test gestione errori su file non analizzabile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, 'syntax_error.py'), 'w') as f:
            f.write('def broken(\n')  # Syntax error
        
        stats = scanner.scan_directory(
            tmpdir,
            memory_url='http://127.0.0.1:8392/mcp',
            dry_run=True,
        )
        
        assert stats['files_errored'] >= 1
        assert len(stats['errors']) >= 1


def test_empty_directory():
    """Test scansione directory vuota."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stats = scanner.scan_directory(
            tmpdir,
            memory_url='http://127.0.0.1:8392/mcp',
            dry_run=True,
        )
        
        assert stats['files_found'] == 0
        assert stats['files_analyzed'] == 0
        assert stats['nodes_found'] == 0