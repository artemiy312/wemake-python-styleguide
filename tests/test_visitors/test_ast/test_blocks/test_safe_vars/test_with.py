# -*- coding: utf-8 -*-

import pytest

from wemake_python_styleguide.violations.consistency import (
    NonExhaustiveVariableViolation,
)
from wemake_python_styleguide.visitors.ast.blocks import SafeVariableVisitor

with_ = 'with {items}: {body}'
with_items = [
    '... as {0}',
    '... as ({0}, variable)',
    '... as (variable, *{0})',
    '... as {0}, ... as variable',
    '... as variable, ... as {0}',
]


@pytest.mark.parametrize('with_item', with_items)
def test_unsafe_vars_inside_scope(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    mode,
    default_options,
    format_context_body,
    with_item,
):
    """An unassigned variable inside a scope isn't safe."""
    variable_name = 'unsafe'
    code = mode(format_context_body([
        with_.format(
            items=with_item.format('safe'),
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
    default_formatter,
    format_context_body,
):
    """A variable assigned inside the scope is safe."""
    variable_name = 'safe'
    scope_body = """
    {0}
    {1}
    """.format(assign_statement.format(variable_name), variable_name)

    code = mode(format_context_body([
        default_formatter.format(with_, body=scope_body),
    ]))

    tree = parse_ast_tree(code)

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('with_item', with_items)
def test_safe_vars_from_with_items(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    format_context_body,
    with_item,
):
    """A statement item is safe inside the scope."""
    variable_name = 'safe'
    code = mode(format_context_body([
        with_.format(
            items=with_item.format(variable_name),
            body=variable_name,
        ),
    ]))

    tree = parse_ast_tree(code)

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])
