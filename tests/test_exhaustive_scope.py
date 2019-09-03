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


@pytest.mark.parametrize(('code', 'exhaustive_scope'), [
    (if_x, {'x',}),
    (while_x, {'x',}),
    (for_x, {'x',}),
    (async_for_x, {'x',}),
    (xyz, {'x', 'y', 'z'}),
    (yz, {'y', 'z'}),
    (xy, {'x', 'y'}),
    (xz, {'x', 'z'}),
])
def test_exhaustive_ctx(code, exhaustive_scope):
    assert ExhaustiveScope().exhaustive(ast.parse(code)) == exhaustive_scope
