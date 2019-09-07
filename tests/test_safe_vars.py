# -*- coding: utf-8 -*-

import ast
from itertools import chain, zip_longest

from wemake_python_styleguide.logic.safe_vars import SafeVars, get_safe_vars

import pytest


def default_zip(code, vars_):
    return list(zip_longest(code, [], fillvalue=vars_))

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

non_safe_vars_body_orelse = [
    control.format(body=x, orelse=y)
    for control, (x, y) in chain(
        default_zip(body_orelse, (ellipsis, ellipsis)),
        default_zip(body_orelse, (x, ellipsis)),
        default_zip(body_orelse, (ellipsis, x)),
        default_zip(body_orelse, (x, y)),
    )
]

body_orelse_x = [
    control.format(body=x, orelse=x) for control in body_orelse
]

import_x = ['import x', 'import _ as x', 'from _ import x', 'from _ import _ as x']


def try_except_else_finally_format(body='...', handler='...', orelse='...', final='...'):
    return try_except_else_finally.format(body=body, handler=handler, orelse=orelse, final=final)

non_safe_vars_try = [
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

vars_isolation_x = """
x = 1

def f():
    v = 1

async def f():
    v = 3

class F:
    v = 3
"""

var_owners_x = """
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

var_owners_isolation_x = """
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
            with _:
                z = 3
        else:
            z = 3
else:
    with _ as y:
        pass
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
        import x
    except:
        from _ import x

    y = 2
    if other:
        x = 1
        from _ import _ as z
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
        import X as x
    async for _ in range(1):
        z = 2
    else:
        z = 3
"""


@pytest.mark.parametrize('code', [
    *non_safe_vars_body_orelse,
    *non_safe_vars_try,
])
def test_non_safe_vars(code):
    assert not get_safe_vars(ast.parse(code))


@pytest.mark.parametrize(('code', 'safe_vars'), [
    *default_zip(body_orelse_x, {'x'}),
    *default_zip(try_except_else_finally_x, {'x'}),
    *default_zip(try_except_else_finally_xy, {'x', 'y'}),
    *default_zip(try_except_else_finally_xyz, {'x', 'y', 'z'}),
    *default_zip(import_x, {'x'}),
    (vars_isolation_x, {'x'}),
    (mix_xyz, {'x', 'y', 'z'}),
    (mix_yz, {'y', 'z'}),
    (mix_xy, {'x', 'y'}),
    (mix_xz, {'x', 'z'}),
])
def test_safe_vars(code, safe_vars):
    assert get_safe_vars(ast.parse(code)) == safe_vars


@pytest.mark.parametrize(('code', 'safe_vars'), [
    (var_owners_x, {'x'}),
    (var_owners_isolation_x, {'x'}),
])
def test_var_owners(code, safe_vars):
    for owner_node in ast.parse(code).body:
        assert get_safe_vars(owner_node) == safe_vars


@pytest.mark.parametrize(('module_code', 'scopped_code', 'safe_vars'), [
    (mix_xy, var_owners_x, {'x', 'y'}),
    (mix_xz, var_owners_x, {'x', 'z'}),
    (mix_xyz, var_owners_x, {'x', 'y', 'z'}),
    (mix_yz, var_owners_x, {'x', 'y', 'z'}),
])
def test_find_multiple_vars(module_code, scopped_code, safe_vars):
    module_node = ast.parse(module_code)
    for owner_node in ast.parse(scopped_code).body:
        vars = SafeVars()
        vars.find(owner_node)
        vars.find(module_node)
        assert vars.fold() == safe_vars
