import ast
import enum
from collections import defaultdict, namedtuple
from contextlib import contextmanager
from functools import reduce
from operator import iand, ior
import typing

from wemake_python_styleguide.logic.naming.name_nodes import flat_variable_names, get_variables_from_node


class Scopes:
    """
    Each scope has its own variables.

    DirectStorage(['body', 'orelse'])
    """

    def __init__(self, scopes):
        self.vars_ = {scope: set() for scope in scopes}

    def scopes(self):
        return list(self.vars_)

    def add_to_scope(self, scope, var):
        self.vars_[scope].add(var)

    def scope_vars(self, scope):
        return self.vars_.get(scope)

    def safe_vars(self):
        if not self.vars_:
            return set()
        return reduce(iand, self.vars_.values())


class NestedScopes(Scopes):
    """
    Each scope has its own variables and parent's variables.

    HierarchyStorage({
        'finalbody': ['excepthandlers', 'orelse'],
        'body': [],
        'excepthandlers': [],
        'orelse': ['body'],
    })
    """

    def __init__(self, hierarchy):
        self.hierarchy = hierarchy
        super().__init__(list(hierarchy.keys()))

    def add_to_scope(self, scope, var):
        super().add_to_scope(scope, var)
        for parent_scope in self.hierarchy[scope]:
            self.add_to_scope(parent_scope, var)

    def safe_vars(self):
        vars_ = [
            self.vars_[scope]
            for scope, descendants in self.hierarchy.items()
            if not descendants
        ]
        return reduce(iand, vars_)


class ScopesChain:

    def __init__(self, scopes):
        self.scopes = scopes
        self.scope = ''

    def body(self, node):
        for scope in self.scopes:
            self.scope = scope
            for stmt in getattr(node, scope):
                yield stmt


class SafeVars:

    BodyOrElse = ast.If, ast.For, ast.AsyncFor, ast.While
    Body = ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module, ast.ExceptHandler
    Import = ast.Import, ast.ImportFrom
    WithItem = ast.With, ast.AsyncWith
    SharedScope = BodyOrElse + Import + WithItem + (ast.Try,)

    def __init__(self):
        self.stmt_hierarchy = {}
        self.scopes_of_stmt = {}
        self.vars_of_stmt = {}

        self.null_scopes = Scopes([])

    def _get_scopes(self, node):
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
        return scopes

    def find(self, node, shadow_vars=None):
        shadow_vars = shadow_vars or set()

        scopes = self.scopes_of_stmt[node] = self._get_scopes(node)
        if scopes is self.null_scopes:
            return

        chain = ScopesChain(scopes.scopes())
        for stmt in chain.body(node):
            vars_ = scopes.scope_vars(chain.scope)

            if isinstance(stmt, ast.Assign):
                for name in flat_variable_names([stmt]):
                    # skip shadowed assigns
                    if name not in shadow_vars:
                        scopes.add_to_scope(chain.scope, name)

            elif isinstance(stmt, ast.alias):
                name = stmt.asname or stmt.name
                scopes.add_to_scope(chain.scope, name)

            elif isinstance(stmt, ast.withitem) and stmt.optional_vars:
                for name in get_variables_from_node(stmt.optional_vars):
                    scopes.add_to_scope(chain.scope, name)

            elif isinstance(stmt, ast.ExceptHandler):
                self.stmt_hierarchy[stmt] = node
                self.vars_of_stmt[stmt] = vars_
                self.find(stmt, shadow_vars)

            elif isinstance(stmt, self.SharedScope):
                self.stmt_hierarchy[stmt] = node
                self.vars_of_stmt[stmt] = vars_
                self.find(stmt, vars_ | shadow_vars)

    def fold(self):
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
        return reduce(ior, safe_vars)


def get_safe_vars(node):
    vars_ = SafeVars()
    vars_.find(node)
    return vars_.fold()
