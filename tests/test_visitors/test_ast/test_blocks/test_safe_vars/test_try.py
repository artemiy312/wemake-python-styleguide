# -*- coding: utf-8 -*-

import pytest

from wemake_python_styleguide.violations.consistency import (
    NonExhaustiveVariableViolation,
)
from wemake_python_styleguide.visitors.ast.blocks import SafeVariableVisitor

try_scopes = ['body', 'except_handler', 'orelse', 'final_body']
try_except_else_finally = """
try:
    {body}
except {except_name}:
    {except_handler}
else:
    {orelse}
finally:
    {final_body}
"""
except_items = [
    'Exception as {0}',
    '(Exception, ValueError)  as {0}',
]


@pytest.mark.parametrize('scopes_var', [
    {},
    {'body': 'x'},
    {'except_handler': 'x'},
    {'orelse': 'x'},
    {'body': 'x', 'except_handler': 'y'},
    {'except_handler': 'y', 'orelse': 'x'},
    {'body': 'x', 'except_handler': 'y', 'orelse': 'x'},
])
def test_unsafe_vars_after_statement(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    default_formatter,
    scopes_var,
):
    """A non-exhaustively assigned variable isn't safe after the statement."""
    variable_name = 'x'
    statement = default_formatter.format(
        try_except_else_finally,
        **{
            scope: assign_statement.format(scope_var)
            for scope, scope_var in scopes_var.items()
        },
    )

    tree = parse_ast_tree(mode(format_context_body([statement, variable_name])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [NonExhaustiveVariableViolation])
    assert_error_text(visitor, variable_name)


@pytest.mark.parametrize('scopes_with_var', [
    ['final_body'],
    ['body', 'except_handler'],
    ['except_handler', 'orelse'],
])
def test_safe_vars_after_statement(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    default_formatter,
    scopes_with_var,
):
    """An exhaustively assigned variable is safe after the statement."""
    variable_name = 'x'
    statement = default_formatter.format(
        try_except_else_finally,
        **{
            scope: assign_statement.format(variable_name)
            for scope in scopes_with_var
        },
    )

    tree = parse_ast_tree(mode(format_context_body([statement, variable_name])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('statement_scope', try_scopes)
def test_unsafe_vars_inside_scope(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    format_context_body,
    default_formatter,
    statement_scope,
):
    """An unassigned variable inside a scope isn't safe."""
    variable_name = 'unsafe'
    statement = default_formatter.format(
        try_except_else_finally,
        **{statement_scope: variable_name},
    )

    tree = parse_ast_tree(mode(format_context_body([statement])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [NonExhaustiveVariableViolation])
    assert_error_text(visitor, variable_name)


@pytest.mark.parametrize('statement_scope', try_scopes)
def test_safe_vars_inside_scope(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    default_formatter,
    statement_scope,
):
    """An assigned variable inside a scope is safe."""
    variable_name = 'x'
    scope_body = """
    {0}
    {1}
    """.format(assign_statement.format(variable_name), variable_name)
    statement = default_formatter.format(
        try_except_else_finally,
        **{statement_scope: scope_body},
    )

    tree = parse_ast_tree(mode(format_context_body([statement])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('except_item', except_items)
def test_safe_vars_inside_except_item(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    default_formatter,
    except_item,
):
    """An except item is the safe variable inside the scope."""
    variable_name = 'x'
    statement = default_formatter.format(
        try_except_else_finally,
        except_name=except_item.format(variable_name),
        except_handler=variable_name,
    )

    tree = parse_ast_tree(mode(format_context_body([statement])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])
