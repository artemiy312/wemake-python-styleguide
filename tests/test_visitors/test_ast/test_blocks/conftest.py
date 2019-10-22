# -*- coding: utf-8 -*-

from functools import partial
from typing import List

import pytest

# Assigns:

simple_assign = '{0} = 1'
multiple_assign = '{0} = unmatched_assign = 1'
annotated_assign1 = '{0}: type = 1'
annotated_assign2 = '{0}: type'
unpacking_assign1 = '{0}, unmatched_assign = (1, 2)'
unpacking_assign2 = 'unmatched_assign, *{0} = (1, 2)'

# Context bodies:
function_context = """
def function():
    {0}
"""

method_context = """
class Class:
    def method(self):
        {0}
"""


@pytest.fixture(params=[
    simple_assign,
    multiple_assign,
    annotated_assign1,
    annotated_assign2,
    unpacking_assign1,
    unpacking_assign2,
])
def assign_statement(request):
    """Parametrized fixture that contains all possible assign templates."""
    return request.param


@pytest.fixture(params=[
    (function_context, 4),
    (method_context, 8),
])
def format_context_body(request):
    """Get context body template."""
    def format_with_scpaces(template: str, spaces: int, subs: List[str]) -> str:
        """Format a context template with given spaces number as indentation."""
        delimeter = '\n' + ' ' * spaces
        return template.format(delimeter.join(sub.replace('\n', delimeter) for sub in subs))

    return partial(format_with_scpaces, *request.param)
