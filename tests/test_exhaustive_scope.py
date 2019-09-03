# -*- coding: utf-8 -*-

import ast

from wemake_python_styleguide.logic.exhaustive_scope import ExhaustiveScope

import pytest

if_x = """
if some:
    x = 1
else:
    x = 2
"""

for_x = """
for _ in range():
    x = 1
else:
    x = 2
"""

async_for_x = """
async for _ in range():
    x = 1
else:
    x = 2
"""

while_x = """
while _:
    x = 1
else:
    x = 2
"""

xyz = """
if some:
    x = 1
    y = 2
    if other:
        x = 1
        z = 1
    else:
        while _:
            z = 1
        else:
            z = 3
else:
    y = 3
    for _ in range(1):
        x = 1
    else:
        x = 1
    async for _ in range(1):
        z = 2
    else:
        z = 3
"""

yz = """
if some:
    y = 2
    if other:
        x = 1
        z = 1
    else:
        while _:
            z = 1
        else:
            z = 3
else:
    y = 3
    for _ in range(1):
        x = 1
    else:
        x = 1
    async for _ in range(1):
        z = 2
    else:
        z = 3
"""

xz = """
if some:
    x = 1
    if other:
        x = 1
        z = 1
    else:
        while _:
            z = 1
        else:
            z = 3
else:
    y = 3
    for _ in range(1):
        x = 1
    else:
        x = 1
    async for _ in range(1):
        z = 2
    else:
        z = 3
"""

xy = """
if some:
    x = 1
    y = 2
    if other:
        x = 1
        z = 1
    else:
        while _:
            z = 1
else:
    y = 3
    for _ in range(1):
        x = 1
    else:
        x = 1
    async for _ in range(1):
        z = 2
    else:
        z = 3
"""

scope_isolation_x = """
x = 1

def f():
    v = 1

async def f():
    v = 3

class F:
    v = 3
"""

scope_owners_x = """
def x():
    if _:
        x = 1
    else:
        x = 2

async def x():
    while _:
        x = 1
    else:
        x = 2

class A:
    for _ in _:
        x = 1
    else:
        x = 2
"""

scope_owners_isolation_x = """
def x():
    def z():
        y = 3
    async def z():
        y = 3
    class Z:
        y = 3

    if _:
        x = 1
    else:
        x = 2

async def x():
    def z():
        y = 3
    async def z():
        y = 3
    class Z:
        y = 3

    x = 1

class A:
    def z():
        y = 3
    async def z():
        y = 3
    class Z:
        y = 3

    x = 2
"""


@pytest.mark.parametrize(('code', 'exhaustive_scope'), [
    (scope_isolation_x, {'x'}),
    (if_x, {'x'}),
    (while_x, {'x'}),
    (for_x, {'x'}),
    (async_for_x, {'x'}),
    (xyz, {'x', 'y', 'z'}),
    (yz, {'y', 'z'}),
    (xy, {'x', 'y'}),
    (xz, {'x', 'z'}),
])
def test_exhaustive_scope(code, exhaustive_scope):
    assert ExhaustiveScope().exhaustive(ast.parse(code)) == exhaustive_scope


@pytest.mark.parametrize(('code', 'exhaustive_scope'), [
    (scope_owners_x, {'x'}),
    (scope_owners_isolation_x, {'x'}),
])
def test_scope_owners(code, exhaustive_scope):
    for owner_node in ast.parse(code).body:
        assert ExhaustiveScope().exhaustive(owner_node) == exhaustive_scope


@pytest.mark.parametrize(('module_code', 'scopped_code', 'exhaustive_scope'), [
    (yz, scope_owners_x, {'x', 'y', 'z'}),
    (xz, scope_owners_x, {'x', 'z'}),
    (xy, scope_owners_x, {'x', 'y'}),
    (xyz, scope_owners_x, {'x', 'y', 'z'}),
])
def test_traverse_multiple_scopes(module_code, scopped_code, exhaustive_scope):
    module_node = ast.parse(module_code)
    for owner_node in ast.parse(scopped_code).body:
        scope = ExhaustiveScope()
        scope.traverse(owner_node)
        scope.traverse(module_node)
        assert scope.fold() == exhaustive_scope
