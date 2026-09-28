#!/usr/bin/env python3
from enum import Enum


class SATSolverResult(Enum):
    SAT = 1
    UNSAT = 2
    UNKNOWN = 3


def lit_from_dimacs(x: int) -> int:
    """3 -> 6, -3 -> 7."""
    return 2 * x if x > 0 else -2 * x + 1


def lit_to_dimacs(lit: int) -> int:
    """6 -> 3, 7 -> -3."""
    v = lit >> 1
    return -v if lit & 1 else v


def neg(lit: int) -> int:
    return lit ^ 1


def var(lit: int) -> int:
    return lit >> 1


class Formula:
    __slots__ = ("num_vars", "num_lits", "clauses")

    def __init__(self, num_vars, clauses):
        self.num_vars = num_vars
        self.num_lits = 2 * num_vars + 2
        self.clauses = clauses


def load_formula(fname) -> Formula:
    num_vars, raw_clauses = read_DIMACS(fname)
    clauses = [[2 * x if x > 0 else -2 * x + 1 for x in raw] for raw in raw_clauses]
    return Formula(num_vars, clauses)


def read_DIMACS(fname):
    with open(fname) as f:
        lines = f.read().split("\n")

    variables_total = clauses_total = None
    clauses = []
    for line in lines:
        line = line.strip()
        if not line or line[0] == "c":
            continue
        if line[0] == "%":
            break
        if line[0] == "p":
            header = line.split()
            assert header[1] == "cnf", line
            variables_total, clauses_total = int(header[2]), int(header[3])
            continue
        clause = [int(x) for x in line.split()]
        if clause and clause[-1] == 0:
            clause.pop()
        clauses.append(clause)

    if clauses_total != len(clauses):
        print("warning: header says ", clauses_total, " but read ", len(clauses))
    return variables_total, clauses
