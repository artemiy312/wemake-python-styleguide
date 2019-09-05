# -*- coding: utf-8 -*-

import ast
from itertools import chain, zip_longest

from wemake_python_styleguide.logic.exhaustive_scope import ExhaustiveScope

import pytest

x = 'x=1'
y = 'y=1'
z = 'z=1'
xy = f'{x}; {y}'
xz = f'{x}; {z}'
yz = f'{y}; {z}'
xyz = f'{x}; {y}; {z}'
ellipsis = '...'

if_else = """
if some:
    {body}
else:
    {orelse}
"""
for_else = """
for _ in range():
    {body}
else:
    {orelse}
"""
async_for_else = """
async for _ in range():
    {body}
else:
    {orelse}
"""
while_else = """
while ...:
    {body}
else:
    {orelse}
"""
try_except_else_finally = """
try:
    {body}
except:
    {handler}
else:
    {orelse}
finally:
    {final}
"""


body_orelse = [if_else, for_else, async_for_else, while_else]

non_exhaustive_body_orelse = [
    control.format(body=x, orelse=y)
    for control, (x, y) in chain(
        zip_longest(body_orelse, [], fillvalue=(ellipsis, ellipsis)),
        zip_longest(body_orelse, [], fillvalue=(x, ellipsis)),
        zip_longest(body_orelse, [], fillvalue=(ellipsis, x)),
        zip_longest(body_orelse, [], fillvalue=(x, y)),
    )
]

body_orelse_x = [
    control.format(body=x, orelse=x) for control in body_orelse
]

def try_except_else_finally_format(body='...', handler='...', orelse='...', final='...'):
    return try_except_else_finally.format(body=body, handler=handler, orelse=orelse, final=final)

non_exhaustive_try = [
    try_except_else_finally_format(),
    try_except_else_finally_format(body=x),
    try_except_else_finally_format(handler=y),
    try_except_else_finally_format(orelse=x),
    try_except_else_finally_format(body=x, handler=y),
    try_except_else_finally_format(handler=y, orelse=x),
    try_except_else_finally_format(body=x, handler=y, orelse=x),
]

try_except_else_finally_x = [
    try_except_else_finally_format(body=x, handler=x),
    try_except_else_finally_format(handler=x, orelse=x),
    try_except_else_finally_format(final=x),
]
try_except_else_finally_xy = [
    try_except_else_finally_format(body=xy, handler=xy),
    try_except_else_finally_format(handler=xy, orelse=xy),
    try_except_else_finally_format(body=x, handler=xy, orelse=y),
    try_except_else_finally_format(body=x, handler=y, final=xy),
    try_except_else_finally_format(final=xy),
]
try_except_else_finally_xyz = [
    try_except_else_finally_format(body=x, handler=xyz, orelse=yz),
    try_except_else_finally_format(body=xy, handler=xyz, orelse=z),
    try_except_else_finally_format(body=x, handler=y, orelse=z, final=xyz),
]

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

mix_xyz = """
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

mix_yz = """
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

mix_xz = """
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

mix_xy = """
if some:
    try:
        x = 1
    except:
        x = 2

    y = 2
    if other:
        x = 1
        z = 1
    else:
        while _:
            z = 1
else:
    try:
        y = 1
    finally:
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


@pytest.mark.parametrize('code', [
    *non_exhaustive_body_orelse,
    *non_exhaustive_try,
])
def test_non_exhaustive_scopes(code):
    assert not ExhaustiveScope().exhaustive(ast.parse(code))


@pytest.mark.parametrize(('code', 'exhaustive_scope'), [
    *list(zip_longest(body_orelse_x, [], fillvalue={'x'})),
    *list(zip_longest(try_except_else_finally_x, [], fillvalue={'x'})),
    *list(zip_longest(try_except_else_finally_xy, [], fillvalue={'x', 'y'})),
    *list(zip_longest(try_except_else_finally_xyz, [], fillvalue={'x', 'y', 'z'})),
    (scope_isolation_x, {'x'}),
    (mix_xyz, {'x', 'y', 'z'}),
    (mix_yz, {'y', 'z'}),
    (mix_xy, {'x', 'y'}),
    (mix_xz, {'x', 'z'}),
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
    (mix_xy, scope_owners_x, {'x', 'y'}),
    (mix_xz, scope_owners_x, {'x', 'z'}),
    (mix_xyz, scope_owners_x, {'x', 'y', 'z'}),
    (mix_yz, scope_owners_x, {'x', 'y', 'z'}),
])
def test_traverse_multiple_scopes(module_code, scopped_code, exhaustive_scope):
    module_node = ast.parse(module_code)
    for owner_node in ast.parse(scopped_code).body:
        scope = ExhaustiveScope()
        scope.traverse(owner_node)
        scope.traverse(module_node)
        assert scope.fold() == exhaustive_scope
