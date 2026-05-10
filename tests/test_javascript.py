"""Tests per craft_code_mapper.analyzers.javascript."""

import os
import tempfile
import pytest
import time
from craft_code_mapper.analyzers import javascript

# Skip all tests if tree-sitter not available
skiptest = pytest.mark.skipif(
    not javascript._HAS_JS,
    reason="tree-sitter-javascript not available"
)


def _write_temp(code: str, suffix='.js') -> str:
    """Create temp file and return path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, code.encode('utf-8'))
    os.close(fd)
    return path


def _cleanup(path: str) -> None:
    """Cleanup temp file with retry on Windows."""
    try:
        os.unlink(path)
    except PermissionError:
        time.sleep(0.1)
        try:
            os.unlink(path)
        except Exception:
            pass


@skiptest
def test_extract_class():
    """Test estrazione di classi JS."""
    code = '''
class MyClass extends BaseClass {
    constructor() {
        this.value = 42;
    }

    getValue() {
        return this.value;
    }

    static staticMethod() {
        return "static";
    }
}
'''
    path = _write_temp(code)
    try:
        result = javascript.extract_file(path)

        assert result['language'] == 'javascript'
        assert result['hash'] != ''
        assert len(result['hash']) == 32

        class_nodes = [n for n in result['nodes'] if n['type'] == 'class']
        assert len(class_nodes) == 1
        assert class_nodes[0]['name'] == 'MyClass'
        assert class_nodes[0]['bases'] == ['BaseClass']
    finally:
        _cleanup(path)


@skiptest
def test_extract_functions():
    """Test estrazione di funzioni JS."""
    code = '''
function regularFunc(a, b) {
    return a + b;
}

async function asyncFunc() {
    return await Promise.resolve(1);
}

const arrowFunc = (x) => x * 2;

const arrowMulti = (a, b, c) => {
    return a + b + c;
};
'''
    path = _write_temp(code)
    try:
        result = javascript.extract_file(path)

        func_nodes = [n for n in result['nodes'] if n['type'] == 'function']
        assert len(func_nodes) > 0
    finally:
        _cleanup(path)


@skiptest
def test_extract_imports():
    """Test estrazione import JS."""
    code = '''
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils.js';
'''
    path = _write_temp(code)
    try:
        result = javascript.extract_file(path)

        assert len(result['imports']) > 0

        modules = [i['module'] for i in result['imports']]
        assert 'react' in modules
    finally:
        _cleanup(path)


@skiptest
def test_typescript():
    """Test file TypeScript."""
    code = '''
interface Person {
    name: string;
    age: number;
}

class Student implements Person {
    name: string;
    age: number;

    constructor(name: string, age: number) {
        this.name = name;
        this.age = age;
    }

    greet(): void {
        console.log(`Hello, ${this.name}`);
    }
}
'''
    path = _write_temp(code, suffix='.ts')
    try:
        result = javascript.extract_file(path)

        # Language should be typescript
        assert result['language'] == 'typescript'

        class_nodes = [n for n in result['nodes'] if n['type'] == 'class']
        assert len(class_nodes) >= 1
    finally:
        _cleanup(path)


@skiptest
def test_unsupported_extension():
    """Test errore su estensione non supportata."""
    path = _write_temp('public class Foo {}', suffix='.java')
    try:
        result = javascript.extract_file(path)

        # JS analyzer non supporta .java
        assert len(result['errors']) > 0
        assert 'unsupported' in result['errors'][0].lower()
    finally:
        _cleanup(path)


def test_file_not_found():
    """Test errore su file non esistente."""
    result = javascript.extract_file('/nonexistent/file.js')
    assert len(result['errors']) > 0
    assert 'not found' in result['errors'][0].lower()


@skiptest
def test_method_definition():
    """Test metodi in classi."""
    code = '''
class Counter {
    count = 0;

    increment() {
        this.count++;
    }

    decrement() {
        this.count--;
    }
}
'''
    path = _write_temp(code)
    try:
        result = javascript.extract_file(path)

        # Dovrebbe trovare la classe
        class_nodes = [n for n in result['nodes'] if n['type'] == 'class']
        assert len(class_nodes) >= 1

        # Dovrebbe trovare funzioni/metodi
        assert len(result['nodes']) >= 2
    finally:
        _cleanup(path)