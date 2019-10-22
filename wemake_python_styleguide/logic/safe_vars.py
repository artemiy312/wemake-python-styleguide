import ast
from collections import OrderedDict
from functools import reduce
from operator import and_, or_
import typing

from typing_extensions import final

from wemake_python_styleguide.logic.functions import get_all_arguments
from wemake_python_styleguide.logic.naming.name_nodes import (
    flat_variable_names, get_variables_from_node
)
from wemake_python_styleguide.logic.nodes import get_parent


class Scopes:

    TargetBodyOrElse = ast.For, ast.AsyncFor
    BodyOrElse = ast.If, ast.While, *TargetBodyOrElse
    Fn = ast.FunctionDef, ast.AsyncFunctionDef
    Def = ast.ClassDef, *Fn
    Body = ast.Module, ast.ExceptHandler, *Def
    Import = ast.Import, ast.ImportFrom
    WithItem = ast.With, ast.AsyncWith

    def __init__(self, node: ast.AST, scopes: typing.List[str]) -> None:
        self.node = node
        self.vars_: typing.Dict[str, typing.Set[str]] = {
            scope: set() for scope in scopes
        }

    def add_to_scope(self, scope: str, vars_: typing.Set[str]) -> None:
        self.vars_[scope].update(vars_)

    def scope_names(self) -> typing.List[str]:
        return list(self.vars_)

    def scope_vars(self, scope: str) -> typing.Set[str]:
        return self.vars_[scope]

    def safe_vars(self) -> typing.Set[str]:
        if not self.vars_:
            return set()
        return reduce(and_, self.vars_.values())

    def __iter__(self) -> typing.Iterator[typing.Tuple[str, ast.AST]]:
        for scope in self.scope_names():
            for stmt in getattr(self.node, scope):
                yield scope, stmt


@final
class NestedScopes(Scopes):

    def __init__(self, node, hierarchy: OrderedDict) -> None:
        self.hierarchy = hierarchy
        super().__init__(node, list(hierarchy.keys()))

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
        return reduce(and_, vars_)


def get_scopes(node: ast.AST) -> typing.Optional[Scopes]:
    if isinstance(node, Scopes.BodyOrElse):
        scopes = Scopes(node, ['body', 'orelse'])
    elif isinstance(node, Scopes.Body):
        scopes = Scopes(node, ['body'])
    elif isinstance(node, Scopes.Import):
        scopes = Scopes(node, ['names'])
    elif isinstance(node, Scopes.WithItem):
        scopes = NestedScopes(node, OrderedDict([
            ('items', ['body']),
            ('body', []),
        ]))
    elif isinstance(node, ast.Try):
        scopes = NestedScopes(node, OrderedDict([
            ('body', []),
            ('handlers', []),
            ('orelse', ['body']),
            ('finalbody', ['handlers', 'orelse']),
        ]))
    else:
        scopes = None

    return scopes


@final
class SafeVars:

    SharedScope = (
        ast.Try,
        ast.ExceptHandler,
        *Scopes.BodyOrElse,
        *Scopes.TargetBodyOrElse,
        *Scopes.Import,
        *Scopes.WithItem,
    )

    ScopeNodes = (
        ast.Module,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.If,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.ExceptHandler
    )

    def __init__(self) -> None:
        # child to parent
        self.children_hierarchy: typing.Dict[ast.AST, ast.AST] = {}
        # stmt scopes
        self.scopes_of_stmt: typing.Dict[ast.AST, Scopes] = {}
        self.scope_name_of_stmt: typing.Dict[ast.AST, str] = {}
        self.until_vars: typing.Dict[ast.AST, typing.Set[str]] = {}

        self.until_reached = False

    def _get_scope_level_node(self, node: ast.AST) -> ast.AST:
        scope_node = node
        scope = get_parent(node)

        while not (isinstance(scope, self.ScopeNodes) or scope is None):
            scope_node = scope
            scope = get_parent(scope)

        for parent_scope in get_scopes(scope).scope_names():
            if scope_node in getattr(scope, parent_scope):
                return scope_node

        return scope

    def find(
        self,
        node: ast.AST,
        until: typing.Optional[ast.AST]=None,
        ignored: typing.Optional[typing.Set[str]]=None
    ) -> None:
        """Returns True if meet `until` node otherwise False."""
        find_ignored: typing.Set[str] = ignored or set()

        find_until: typing.Optional[ast.AST]
        if until:
            find_until = self._get_scope_level_node(until)
        else:
            find_until = None

        scopes = get_scopes(node)
        if scopes is None:
            return

        self.scopes_of_stmt[node] = scopes

        if isinstance(node, Scopes.Fn):
            vars_ = {arg.arg for arg in get_all_arguments(node)}
            scopes.add_to_scope('body', vars_)

        elif isinstance(node, Scopes.TargetBodyOrElse):
            scopes.add_to_scope('body', get_variables_from_node(node.target))

        elif isinstance(node, ast.ExceptHandler) and node.name:
            scopes.add_to_scope('body', node.name)

        for scope, stmt in scopes:
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                vars_ = {
                    name
                    for name in flat_variable_names([stmt])
                    if name not in find_ignored
                }
                scopes.add_to_scope(scope, vars_)

            elif isinstance(stmt, Scopes.Def):
                scopes.add_to_scope(scope, {stmt.name})

            elif isinstance(stmt, ast.alias):
                name = stmt.asname or stmt.name
                scopes.add_to_scope(scope, {name})

            elif isinstance(stmt, ast.withitem) and stmt.optional_vars:
                scopes.add_to_scope(
                    scope,
                    set(get_variables_from_node(stmt.optional_vars))
                )

            elif isinstance(stmt, self.SharedScope):
                vars_ = scopes.scope_vars(scope)

                self.scope_name_of_stmt[stmt] = scope
                self.children_hierarchy[stmt] = node
                if isinstance(stmt, ast.ExceptHandler):
                    new_shadow = find_ignored
                else:
                    new_shadow = vars_ | find_ignored
                self.find(stmt, find_until, ignored=new_shadow)

            if stmt == find_until or self.until_reached:
                self.until_reached = True
                self.until_vars[node] = scope
                break

    def fold(self) -> typing.Set[str]:
        if len(self.scopes_of_stmt) < 1:
            return set()

        descendants = set(self.children_hierarchy)
        roots = set(self.scopes_of_stmt) - descendants

        # expand vars to outer scopes
        while len(self.children_hierarchy) != 0:
            children = set(self.children_hierarchy) - set(self.children_hierarchy.values())
            for child in children:
                parent = self.children_hierarchy.pop(child)
                self.scopes_of_stmt[child].safe_vars()

                self.scopes_of_stmt[parent].add_to_scope(
                    self.scope_name_of_stmt[child],
                    self.scopes_of_stmt[child].safe_vars(),
                )

        until_vars = set()
        for stmt, scopes in self.scopes_of_stmt.items():
            if stmt in self.until_vars:
                until_vars.update(scopes.scope_vars(self.until_vars[stmt]))

        # roots
        safe_vars = [
            self.scopes_of_stmt[root].safe_vars()
            for root in roots
        ]

        return reduce(or_, safe_vars, until_vars)


def get_safe_vars(
    node: ast.AST,
    until: typing.Optional[ast.AST]=None,
    ignored: typing.Optional[typing.Set[str]]=None
) -> typing.Set[str]:
    vars_ = SafeVars()
    vars_.find(node, until, ignored)
    return vars_.fold()
