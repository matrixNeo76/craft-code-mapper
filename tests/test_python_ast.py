"""Tests per craft_code_mapper.analyzers.python_ast."""

import os
import tempfile
from craft_code_mapper.analyzers import python_ast


def _write_temp(code: str, suffix='.py') -> str:
    """Create temp file and return path (caller must delete manually on Windows)."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, code.encode('utf-8'))
    os.close(fd)
    return path


def _cleanup(path: str) -> None:
    """Cleanup temp file with retry on Windows."""
    try:
        os.unlink(path)
    except PermissionError:
        import time
        time.sleep(0.1)
        try:
            os.unlink(path)
        except Exception:
            pass


def test_extract_class_and_methods():
    """Test estrazione di classi e metodi."""
    code = '''
class MyClass:
    """A sample class."""

    def method_one(self):
        """First method."""
        pass

    async def method_two(self):
        """Second async method."""
        pass
'''
    path = _write_temp(code)
    try:
        result = python_ast.extract_file(path)

        # Verifica linguaggio
        assert result['language'] == 'python'

        # Verifica classe
        class_nodes = [n for n in result['nodes'] if n['type'] == 'class']
        assert len(class_nodes) == 1
        assert class_nodes[0]['name'] == 'MyClass'
        assert 'A sample class' in class_nodes[0]['docstring']

        # Verifica metodi
        method_nodes = [n for n in result['nodes'] if n['type'] == 'method']
        assert len(method_nodes) == 2
        method_names = [m['name'] for m in method_nodes]
        assert 'MyClass.method_one' in method_names
        assert 'MyClass.method_two' in method_names

        # Verifica async flag
        async_method = next(m for m in method_nodes if 'method_two' in m['name'])
        assert async_method['is_async'] is True
    finally:
        _cleanup(path)


def test_extract_functions():
    """Test estrazione di funzioni top-level."""
    code = '''
def top_level_func(a, b):
    """A top-level function."""
    return a + b

async def async_func():
    """An async function."""
    pass
'''
    path = _write_temp(code)
    try:
        result = python_ast.extract_file(path)

        func_nodes = [n for n in result['nodes'] if n['type'] == 'function']
        assert len(func_nodes) == 2

        # Verifica parametri
        top_func = next(n for n in func_nodes if 'top_level_func' in n['name'])
        assert 'a' in top_func['params']
        assert 'b' in top_func['params']

        # Verifica async
        async_func_node = next(n for n in func_nodes if 'async_func' in n['name'])
        assert async_func_node['is_async'] is True
    finally:
        _cleanup(path)


def test_extract_imports():
    """Test estrazione di import."""
    code = '''
import os
import sys as system
from collections import defaultdict, OrderedDict
from typing import List, Optional
'''
    path = _write_temp(code)
    try:
        result = python_ast.extract_file(path)

        assert len(result['imports']) >= 5

        import_modules = [i['module'] for i in result['imports']]
        assert 'os' in import_modules
        assert 'sys' in import_modules  # alias 'system'
        assert 'collections.defaultdict' in import_modules
    finally:
        _cleanup(path)


def test_extract_decorators():
    """Test estrazione di decoratori."""
    code = '''
class MyClass:
    @property
    def value(self):
        return self._value

    @staticmethod
    def static_method():
        pass

    @classmethod
    def class_method(cls):
        pass

    @abstractmethod
    async def abstract_async(self):
        pass
'''
    path = _write_temp(code)
    try:
        result = python_ast.extract_file(path)

        method_nodes = [n for n in result['nodes'] if n['type'] == 'method']

        prop = next(n for n in method_nodes if 'value' in n['name'])
        assert 'property' in prop['decorators']

        stat = next(n for n in method_nodes if 'static_method' in n['name'])
        assert 'staticmethod' in stat['decorators']

        cls_m = next(n for n in method_nodes if 'class_method' in n['name'])
        assert 'classmethod' in cls_m['decorators']

        abstract = next(n for n in method_nodes if 'abstract_async' in n['name'])
        assert 'abstractmethod' in abstract['decorators']
        assert abstract['is_async'] is True
    finally:
        _cleanup(path)


def test_file_not_found():
    """Test errore su file non esistente."""
    result = python_ast.extract_file('/nonexistent/path/file.py')
    assert len(result['errors']) > 0
    assert 'not found' in result['errors'][0].lower()


def test_syntax_error():
    """Test errore su syntax error."""
    code = 'def broken('  # Syntax error
    path = _write_temp(code)
    try:
        result = python_ast.extract_file(path)
        assert len(result['errors']) > 0
        assert 'syntax' in result['errors'][0].lower()
    finally:
        _cleanup(path)


def test_hash_length():
    """Test che l'hash sia 32 caratteri."""
    code = 'x = 1'
    path = _write_temp(code)
    try:
        result = python_ast.extract_file(path)
        assert len(result['hash']) == 32
    finally:
        _cleanup(path)


def test_call_graph():
    """Test estrazione call graph."""
    code = '''
def caller():
    callee()
    obj.method()
'''
    path = _write_temp(code)
    try:
        result = python_ast.extract_file(path)

        calls = result.get('calls', [])
        assert len(calls) > 0

        caller_calls = [c for c in calls if c.get('caller') == 'caller']
        assert len(caller_calls) >= 1
    finally:
        _cleanup(path)