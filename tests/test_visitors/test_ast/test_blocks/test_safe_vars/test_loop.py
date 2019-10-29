import pytest

from wemake_python_styleguide.violations.consistency import (
    NonExhaustiveVariableViolation,
)
from wemake_python_styleguide.visitors.ast.blocks import SafeVariableVisitor

for_loop1 = 'for {0} in some():'
for_loop2 = 'for {0}, second in some():'
for_loop3 = 'for first, *{0} in some():'
