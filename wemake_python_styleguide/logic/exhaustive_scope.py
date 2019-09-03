import ast
import enum
from collections import defaultdict, namedtuple
from functools import reduce
from operator import iand, ior
import typing


class StmtChain:

    def __init__(self, branches):
        self.context_store = {branch: set() for branch in branches}
        self.chain_state = ''

    def stmts(self, node):
        for branch in self.context_store:
            self.chain_state = branch
            for stmt in getattr(node, branch):
                yield stmt
        self.chain_state = ''

    def is_symmetric(self):
        contexts = set(
            frozenset(context)
            for context in self.context_store.values()
        )
        return len(contexts) == 1

    def intersection(self):
        return reduce(iand, self.context_store.values())

    def context(self):
        if self.chain_state not in self.context_store:
            raise ValueError(
                'You can\'t get context of control flow outside iteration '
                'over stmts().'
            )
        return self.context_store[self.chain_state]

    def __repr__(self):
        return f'<{type(self).__name__} is_symmetric: {self.is_symmetric()}, context: {self.context_store}>'


class ExhaustiveScope:

    BodyOrElseT = (ast.If, ast.For, ast.AsyncFor, ast.While)

    def __init__(self):
        self.stmt_hierarchy = {}
        self.chain_of_stmt = {}
        self.ctx_of_stmt = {}

        self.null_chain = StmtChain([])

    def exhaustive(self, node):
        for stmt in ast.iter_child_nodes(node):
            if isinstance(stmt, self.BodyOrElseT):
                self.traverse(stmt)
        return self.fold()

    def traverse(self, node, shadow_ctx=None):
        shadow_ctx = shadow_ctx or set()

        chain = StmtChain(['body', 'orelse'])
        self.chain_of_stmt[node] = chain

        for stmt in chain.stmts(node):
            ctx = chain.context()

            if isinstance(stmt, ast.Assign):
                for s in stmt.targets:
                    # skip shadowed assigns
                    if s.id not in shadow_ctx:
                        ctx.add(s.id)

            elif isinstance(stmt, self.BodyOrElseT):
                self.stmt_hierarchy[stmt] = node
                self.ctx_of_stmt[stmt] = ctx
                self.traverse(stmt, ctx | shadow_ctx)

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
                self.ctx_of_stmt[leaf].update(chain.intersection())

        # roots
        safe_vars = [
            self.chain_of_stmt[root].intersection()
            for root in roots
        ]
        return reduce(ior, safe_vars)
