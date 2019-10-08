import ast
import enum
from collections import defaultdict, namedtuple
from contextlib import contextmanager
from functools import reduce
from operator import iand, ior
import typing

from typing_extensions import final

from wemake_python_styleguide.logic.functions import get_all_arguments
from wemake_python_styleguide.logic.naming.name_nodes import (
    flat_variable_names, get_variables_from_node
)


class Scopes:

    def __init__(self, scopes: typing.List[str]) -> None:
        self.vars_: typing.Dict[str, typing.Set[str]] = {
            scope: set() for scope in scopes
        }

    def scopes(self) -> typing.List[str]:
        return list(self.vars_)

    def add_to_scope(self, scope: str, vars_: typing.Set[str]) -> None:
        self.vars_[scope].update(vars_)

    def scope_vars(self, scope: str) -> typing.Set[str]:
        return self.vars_.get(scope)

    def safe_vars(self) -> typing.Set[str]:
        if not self.vars_:
            return set()
        return reduce(iand, self.vars_.values())


@final
class NestedScopes(Scopes):

    def __init__(self, hierarchy: typing.Dict[str, typing.List[str]]) -> None:
        self.hierarchy = hierarchy
        super().__init__(list(hierarchy.keys()))

    def add_to_scope(self, scope: str, vars_: typing.Set[str]) -> None:
        super().add_to_scope(scope, vars_)
        for parent_scope in self.hierarchy[scope]:
            self.add_to_scope(parent_scope, vars_)

    def safe_vars(self) -> typing.Set[str]:
        vars_ = [
            self.vars_[scope]
            for scope, descendants in self.hierarchy.items()
            if not descendants
        ]

        if not vars_:
            return set()
        return reduce(iand, vars_)


@final
class ScopesChain:

    def __init__(self, scopes: typing.List[str]) -> None:
        self.scopes = scopes
        self.scope = ''

    def stmts(self, node: ast.AST) -> typing.Iterator[ast.AST]:
        for scope in self.scopes:
            self.scope = scope
            for stmt in getattr(node, scope):
                yield stmt


@final
class SafeVars:

    BodyOrElse = ast.If, ast.For, ast.AsyncFor, ast.While
    Fn = ast.FunctionDef, ast.AsyncFunctionDef
    Def = Fn + (ast.ClassDef,)
    Body = Def + (ast.Module, ast.ExceptHandler)
    Import = ast.Import, ast.ImportFrom

    WithItem = ast.With, ast.AsyncWith
    SharedScope = BodyOrElse + Import + WithItem + (ast.Try, ast.ExceptHandler)

    def __init__(self) -> None:
        self.stmt_hierarchy: typing.Dict[ast.AST, ast.AST] = {}
        self.scopes_of_stmt: typing.Dict[ast.AST, Scopes] = {}
        self.vars_of_stmt: typing.Dict[ast.AST, typing.Set[str]] = {}

        self.null_scopes = Scopes([])

    def _get_scopes(self, node: ast.AST) -> Scopes:
        if node in self.scopes_of_stmt:
            return self.scopes_of_stmt[node]

        if isinstance(node, self.BodyOrElse):
            scopes = Scopes(['body', 'orelse'])
        elif isinstance(node, self.Body):
            scopes = Scopes(['body'])
        elif isinstance(node, self.Import):
            scopes = Scopes(['names'])
        elif isinstance(node, self.WithItem):
            scopes = NestedScopes({
                'body': ['items'],
                'items': [],
            })
        elif isinstance(node, ast.Try):
            scopes = NestedScopes({
                'finalbody': ['handlers', 'orelse'],
                'body': [],
                'handlers': [],
                'orelse': ['body'],
            })
        else:
            scopes = self.null_scopes

        self.scopes_of_stmt[node] = scopes
        return scopes

    def find(self, node, until=None, ignored=None) -> bool:
        """Returns True if meet `until` node otherwise False."""
        ignored: typing.Set[str] = ignored or set()

        scopes = self._get_scopes(node)
        if scopes is self.null_scopes:
            return False

        chain = ScopesChain(scopes.scopes())

        if isinstance(node, self.Fn):
            vars_ = {arg.arg for arg in get_all_arguments(node)}
            scopes.add_to_scope('body', vars_)

        for stmt in chain.stmts(node):
            if stmt == until:
                # put vars from a current scope to all scopes
                # to indetify it as safe for `until` node
                vars_ = scopes.scope_vars(chain.scope)
                for scope in scopes.scopes():
                    scopes.add_to_scope(scope, vars_)
                return True

            if isinstance(stmt, ast.Assign):
                vars_ = {
                    name
                    for name in flat_variable_names([stmt])
                    if name not in ignored
                }
                scopes.add_to_scope(chain.scope, vars_)

            elif isinstance(stmt, self.Def):
                scopes.add_to_scope(chain.scope, {stmt.name})

            elif isinstance(stmt, ast.alias):
                name = stmt.asname or stmt.name
                scopes.add_to_scope(chain.scope, {name})

            elif isinstance(stmt, ast.withitem) and stmt.optional_vars:
                scopes.add_to_scope(
                    chain.scope,
                    set(get_variables_from_node(stmt.optional_vars))
                )

            elif isinstance(stmt, self.SharedScope):
                vars_ = scopes.scope_vars(chain.scope)

                self.stmt_hierarchy[stmt] = node
                self.vars_of_stmt[stmt] = vars_
                if isinstance(stmt, ast.ExceptHandler):
                    new_shadow = ignored
                else:
                    new_shadow = vars_ | ignored
                if self.find(stmt, until, ignored=new_shadow):
                    return True
        return False

    def fold(self) -> typing.Set[str]:
        if len(self.scopes_of_stmt) < 1:
            return set()

        descendants = set(self.stmt_hierarchy)
        roots = set(self.scopes_of_stmt) - descendants

        # expand vars to outer scopes
        while len(self.stmt_hierarchy) != 0:
            leafs = set(self.stmt_hierarchy) - set(self.stmt_hierarchy.values())
            for leaf in leafs:
                del self.stmt_hierarchy[leaf]
                scopes = self.scopes_of_stmt[leaf]
                self.vars_of_stmt[leaf].update(scopes.safe_vars())

        # roots
        safe_vars = [
            self.scopes_of_stmt[root].safe_vars()
            for root in roots
        ]
        return reduce(ior, safe_vars, set())


def get_safe_vars(node, until=None):
    vars_ = SafeVars()
    vars_.find(node, until)
    return vars_.fold()
