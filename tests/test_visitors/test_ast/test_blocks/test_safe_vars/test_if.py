# -*- coding: utf-8 -*-

import pytest

from wemake_python_styleguide.violations.consistency import (
    NonExhaustiveVariableViolation,
)
from wemake_python_styleguide.visitors.ast.blocks import SafeVariableVisitor

if_scopes = ['body', 'orelse']
if_else = """
if ...:
    {body}
else:
    {orelse}
"""


@pytest.mark.parametrize('scopes_var', [
    {},
    {'body': 'x'},
    {'orelse': 'x'},
    {'body': 'y', 'orelse': 'z'},
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
        if_else,
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


@pytest.mark.parametrize('scopes_with_var', [if_scopes])
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
        if_else,
        **{
            scope: assign_statement.format(variable_name)
            for scope in scopes_with_var
        },
    )

    tree = parse_ast_tree(mode(format_context_body([statement, variable_name])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('statement_scope', if_scopes)
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
        if_else,
        **{statement_scope: variable_name},
    )

    tree = parse_ast_tree(mode(format_context_body([statement])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [NonExhaustiveVariableViolation])
    assert_error_text(visitor, variable_name)


@pytest.mark.parametrize('statement_scope', if_scopes)
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
        if_else,
        **{statement_scope: scope_body},
    )

    tree = parse_ast_tree(mode(format_context_body([statement])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])
