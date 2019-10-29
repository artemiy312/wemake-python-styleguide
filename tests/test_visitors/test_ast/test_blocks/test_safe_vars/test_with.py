# -*- coding: utf-8 -*-

import pytest

from wemake_python_styleguide.violations.consistency import (
    NonExhaustiveVariableViolation,
)
from wemake_python_styleguide.visitors.ast.blocks import SafeVariableVisitor

with_ = "with {items}: {body}"
with_items = [
    '... as {0}',
    '... as ({0}, variable)',
    '... as (variable, *{0})',
    '... as {0}, ... as variable',
    '... as variable, ... as {0}',
]


@pytest.mark.parametrize('with_items', with_items)
def test_unsafe_vars_inside_with(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    mode,
    default_options,
    format_context_body,
    with_items,
):
    """An unassigned variable isn't safe inside the scope."""
    variable_name = 'unsafe'
    code = mode(format_context_body([
        with_.format(
            items=with_items.format('safe'),
            body=variable_name,
        ),
    ]))

    tree = parse_ast_tree(code)

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [NonExhaustiveVariableViolation])
    assert_error_text(visitor, variable_name)


def test_safe_vars_inside_with_body(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
):
    """A variable assigned inside the scope is safe."""
    variable_name = 'safe'
    with_body = f"""
    {assign_statement.format(variable_name)}
    {variable_name}"""

    code = mode(format_context_body([
        with_.format(
            items='...',
            body=with_body,
        ),
    ]))

    tree = parse_ast_tree(code)

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('with_items', with_items)
def test_safe_vars_inside_with_items(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    format_context_body,
    with_items,
):
    """A with item is safe inside the scope."""
    variable_name = 'safe'
    code = mode(format_context_body([
        with_.format(
            items=with_items.format(variable_name),
            body=variable_name,
        ),
    ]))

    tree = parse_ast_tree(code)

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])
