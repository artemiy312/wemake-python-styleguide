import ast
import enum
from collections import defaultdict, namedtuple
from functools import reduce
from operator import iand, ior
import typing


class Scopes:
    """
    Each scope has its own storage.

    DirectStorage(['body', 'orelse'])
    """

    def __init__(self, scopes):
        self.storage = {scope: set() for scope in scopes}

    def __iter__(self):
        for scope in self.storage:
            yield scope

    def add(self, scope, value):
        self.storage[scope].add(value)

    def get(self, scope):
        return self.storage.get(scope)

    def intersection(self):
        return reduce(iand, self.storage.values())


class NestedScopes(Scopes):
    """
    Each scope has its own storage and parent's storages.

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

    def add(self, scope, value):
        super().add(scope, value)
        for parent_scope in self.hierarchy[scope]:
            self.add(parent_scope, value)

    def intersection(self):
        scope_leafs = [
            self.storage[scope]
            for scope, descendants in self.hierarchy.items()
            if not descendants
        ]
        return reduce(iand, scope_leafs)


class StmtChain:

    def __init__(self, storage: Scopes):
        self.storage = storage
        self.chain_state = ''

    def stmts(self, node):
        for scope in self.storage:
            self.chain_state = scope
            for stmt in getattr(node, scope):
                yield stmt
        self.chain_state = ''

    def _check_state(self):
        if self.chain_state not in self.storage:
            raise ValueError(
                'You can\'t get scope of control flow outside iteration '
                'over stmts().'
            )

    def scope(self):
        self._check_state()
        return self.storage.get(self.chain_state)

    def add_to_scope(self, value):
        self._check_state()
        self.storage.add(self.chain_state, value)


class ExhaustiveScope:

    BodyOrElseT = (ast.If, ast.For, ast.AsyncFor, ast.While)
    BodyT = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module, ast.ExceptHandler)

    def __init__(self):
        self.stmt_hierarchy = {}
        self.chain_of_stmt = {}
        self.scope_of_stmt = {}

        self.null_chain = StmtChain([])

    def exhaustive(self, node):
        self.traverse(node)
        return self.fold()

    def traverse(self, node, shadow_scope=None):
        shadow_scope = shadow_scope or set()

        if isinstance(node, self.BodyOrElseT):
            chain = StmtChain(Scopes(['body', 'orelse']))
        elif isinstance(node, self.BodyT):
            chain = StmtChain(Scopes(['body']))
        elif isinstance(node, ast.Try):
            chain = StmtChain(NestedScopes({
                'finalbody': ['handlers', 'orelse'],
                'body': [],
                'handlers': [],
                'orelse': ['body'],
            }))
        else:
            return

        self.chain_of_stmt[node] = chain

        for stmt in chain.stmts(node):
            scope = chain.scope()

            if isinstance(stmt, ast.Assign):
                for s in stmt.targets:
                    # skip shadowed assigns
                    if s.id not in shadow_scope:
                        chain.add_to_scope(s.id)

            elif isinstance(stmt, ast.ExceptHandler):
                self.stmt_hierarchy[stmt] = node
                self.scope_of_stmt[stmt] = scope
                self.traverse(stmt, shadow_scope)

            elif isinstance(stmt, self.BodyOrElseT + (ast.Try,)):
                self.stmt_hierarchy[stmt] = node
                self.scope_of_stmt[stmt] = scope
                self.traverse(stmt, scope | shadow_scope)

    def fold(self):
        if len(self.chain_of_stmt) < 1:
            return set()

        descendants = set(self.stmt_hierarchy)
        roots = set(self.chain_of_stmt) - descendants

        # expand vars to outer scopes
        while len(self.stmt_hierarchy) != 0:
            leafs = set(self.stmt_hierarchy) - set(self.stmt_hierarchy.values())
            for leaf in leafs:
                del self.stmt_hierarchy[leaf]
                chain = self.chain_of_stmt.get(leaf, self.null_chain)
                self.scope_of_stmt[leaf].update(chain.storage.intersection())

        # roots
        safe_vars = [
            self.chain_of_stmt[root].storage.intersection()
            for root in roots
        ]
        return reduce(ior, safe_vars)
