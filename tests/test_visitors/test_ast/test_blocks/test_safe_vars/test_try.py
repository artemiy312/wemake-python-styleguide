# -*- coding: utf-8 -*-

import pytest

from wemake_python_styleguide.violations.consistency import (
    NonExhaustiveVariableViolation,
)
from wemake_python_styleguide.visitors.ast.blocks import SafeVariableVisitor


try_scopes = ['try', 'except', 'else', 'finally']
try_except_else_finally = """
try:
    {try}
except {except_name}:
    {except}
else:
    {else}
finally:
    {finally}
"""
except_items = [
    'Exception as {0}',
    '(Exception, ValueError)  as {0}',
]

def format_try(subs):
    subs_with_defaults = {scope: subs.get(scope, '...') for scope in try_scopes}
    name = 'except_name'
    subs_with_defaults[name] = subs.get(name, '...')
    return try_except_else_finally.format(**subs_with_defaults)


@pytest.mark.parametrize('try_scope_var', [
    {},
    {'try': 'x'},
    {'except': 'x'},
    {'else': 'x'},
    {'try': 'x', 'except': 'y'},
    {'except': 'y', 'else': 'x'},
    {'try': 'x', 'except': 'y', 'else': 'x'},
])
def test_unsafe_vars_after_try(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    try_scope_var,
):
    """Unsafe variables exist after try statement."""
    variable_name = 'x'
    tree = parse_ast_tree(mode(format_context_body([
        format_try({
            scope: assign_statement.format(var)
            for scope, var in try_scope_var.items()
        }),
        variable_name,
    ])))

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [NonExhaustiveVariableViolation])
    assert_error_text(visitor, variable_name)


@pytest.mark.parametrize('try_scope', try_scopes)
def test_unsafe_vars_inside_try(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    format_context_body,
    try_scope,
):
    """Unsafe variables exist inside try statement."""
    variable_name = 'safe'
    tree = parse_ast_tree(mode(format_context_body([
        format_try({try_scope: variable_name}),
    ])))

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [NonExhaustiveVariableViolation])
    assert_error_text(visitor, variable_name)


@pytest.mark.parametrize('scopes_with_var', [
    ['finally'],
    ['try', 'except'],
    ['except', 'else'],
])
def test_safe_vars_after_try(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    scopes_with_var,
):
    """Safe variables exist after try statement."""
    variable_name = 'x'
    tree = parse_ast_tree(mode(format_context_body([
        format_try({
            scope: assign_statement.format(variable_name)
            for scope in scopes_with_var
        }),
        variable_name,
    ])))

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('try_scope', try_scopes)
def test_safe_vars_inside_try(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    try_scope,
):
    """Safe variables exist inside try statement."""
    variable_name = 'x'
    try_scope_body = f"""
    {assign_statement.format(variable_name)}
    {variable_name}
    """
    tree = parse_ast_tree(mode(format_context_body([
        format_try({try_scope: try_scope_body}),
    ])))

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize('except_items', except_items)
def test_safe_vars_inside_except_item(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    mode,
    assign_statement,
    format_context_body,
    except_items,
):
    """Safe variables exist inside try statement."""
    variable_name = 'x'
    tree = parse_ast_tree(mode(format_context_body([
        format_try({
            'except_name': except_items.format(variable_name),
            'except': variable_name,
        }),
    ])))

    visitor = SafeVariableVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])
