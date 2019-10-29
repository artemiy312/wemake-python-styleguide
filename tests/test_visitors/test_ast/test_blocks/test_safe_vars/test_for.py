# -*- coding: utf-8 -*-

import pytest

from wemake_python_styleguide.violations.consistency import (
    NonExhaustiveVariableViolation,
)
from wemake_python_styleguide.visitors.ast.blocks import SafeVariableVisitor

for_targets = ['{0}', '{0}, _', '_, *{0}']
for_scopes = ['body', 'orelse']
for_else = """
for {target} in range():
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
        for_else,
        target='_',
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


@pytest.mark.parametrize('scopes_with_var', [for_scopes])
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
        for_else,
        target='_',
        **{
            scope: assign_statement.format(variable_name)
            for scope in scopes_with_var
        },
    )

    tree = parse_ast_tree(mode(format_context_body([statement, variable_name])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('statement_scope', for_scopes)
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
        for_else,
        target='_',
        **{statement_scope: variable_name},
    )

    tree = parse_ast_tree(mode(format_context_body([statement])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [NonExhaustiveVariableViolation])
    assert_error_text(visitor, variable_name)


@pytest.mark.parametrize('statement_scope', for_scopes)
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
    """.format(
        assign_statement.format(variable_name),
        variable_name,
    )
    for_ = default_formatter.format(
        for_else,
        target='_',
        **{statement_scope: scope_body},
    )

    tree = parse_ast_tree(mode(format_context_body([for_])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('for_target', for_targets)
def test_target_safe_vars(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    default_formatter,
    for_target,
):
    """A statement's target is the safe variable inside the body scope."""
    variable_name = 'x'
    statement = default_formatter.format(
        for_else,
        target=for_target.format(variable_name),
        body=variable_name,
    )

    tree = parse_ast_tree(mode(format_context_body([statement])))
    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])
