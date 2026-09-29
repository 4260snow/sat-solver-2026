import sys
import random
from threading import Event
from utils import SATSolverResult, load_formula, lit_to_dimacs, neg


class Solver:
    def __init__(self, filename: str, sigkill: Event):
        self.sigkill = sigkill
        self.formula = load_formula(filename)
        self.num_vars = self.formula.num_vars
        num_lits = self.formula.num_lits

        # Присваивание: values[ℓ] = 1 (истинен), -1 (ложен), 0 (не означен).
        # Хранится и для ℓ, и для ¬ℓ: values[ℓ] == -values[ℓ ^ 1].
        self.values = [0] * num_lits

        # Трейл — означенные литералы в порядке присваивания.
        # trail[:propagated] уже распространены, trail[propagated:] — ещё нет.
        self.trail = []
        self.propagated = 0

        # control[i] — позиция в trail решения уровня i + 1;
        # текущий уровень решения = len(control).
        self.control = []

        self.model = None

        self.preprocess()

    def preprocess(self):
        """
        Разбор дизъюнктов формулы:
          clauses          — дизъюнкты длины ≥ 2, без повторов литералов и тавтологий (a ∨ ¬a ∨ ...)
          units            — литералы единичных дизъюнктов
          has_empty_clause — во входе есть пустой дизъюнкт (формула невыполнима)
        """
        self.clauses = []
        self.units = []
        self.has_empty_clause = False
        for clause in self.formula.clauses:
            lits = set(clause)
            if not lits:
                self.has_empty_clause = True
            elif any(lit ^ 1 in lits for lit in lits):
                continue
            elif len(lits) == 1:
                self.units.append(lits.pop())
            else:
                self.clauses.append(list(lits))

    def level(self) -> int:
        return len(self.control)

    def assign(self, lit: int):
        """Сделать ℓ истинным на текущем уровне."""
        self.values[lit] = 1
        self.values[lit ^ 1] = -1
        self.trail.append(lit)

    def decide(self, lit: int):
        """Открыть новый уровень решения и сделать ℓ истинным."""
        self.control.append(len(self.trail))
        self.assign(lit)

    def decision(self, level: int) -> int:
        """Литерал-решение уровня level (1 ≤ level ≤ self.level())."""
        return self.trail[self.control[level - 1]]

    def backtrack(self, level: int):
        """Отменить все присваивания уровней > level."""
        if level >= len(self.control):
            return
        values, trail = self.values, self.trail
        start = self.control[level]
        for i in range(start, len(trail)):
            lit = trail[i]
            values[lit] = 0
            values[lit ^ 1] = 0
        del trail[start:]
        del self.control[level:]
        self.propagated = start

    def save_model(self):
        values = self.values
        self.model = [lit_to_dimacs(2 * v if values[2 * v] > 0 else 2 * v + 1)
                      for v in range(1, self.num_vars + 1)]

    def build_occurrences(self):
        self.occurrences = [[] for _ in range(self.formula.num_lits)]
        for c in self.clauses:
            for lit in c:
                self.occurrences[lit].append(c)

    def build_watches(self):
        num_lits = self.formula.num_lits
        self.binary = [[] for _ in range(num_lits)]
        self.watches = [[] for _ in range(num_lits)]
        for c in self.clauses:
            if len(c) == 2:
                self.binary[c[0]].append(c[1])
                self.binary[c[1]].append(c[0])
            else:
                self.watches[c[0]].append([c[1], c])
                self.watches[c[1]].append([c[0], c])

    def propagate(self) -> bool:
        """
        UnitPropagate: распространить литералы trail[propagated:].
        Возвращает True, если найден конфликт (все литералы дизъюнкта ложны).
        """
        #if self.sigkill.is_set():
        #    return False

        while self.propagated < len(self.trail):
            self.propagated += 1

            for clause in self.clauses:
                satisfied = False
                unassigned = None
                unassigned_count = 0

                for lit in clause:
                    if self.values[lit] == 1:
                        satisfied = True
                        break

                    if self.values[lit] == 0:
                        unassigned = lit
                        unassigned_count += 1

                if satisfied:
                    continue

                if unassigned_count == 0:
                    return True

                if unassigned_count == 1:
                    self.assign(unassigned)

        return False

    def eliminate_pure_literals(self):
        #if self.sigkill.is_set():
        #    return None

        for v in range(1, self.num_vars + 1):
            pos = 2 * v

            if self.values[pos] != 0:
                continue

            if self.occurrences[pos] and not self.occurrences[neg(pos)]:
                return pos

            if self.occurrences[neg(pos)] and not self.occurrences[pos]:
                return neg(pos)

        return None

    def most_freq(self):
        #if self.sigkill.is_set():
        #    return None
    
        best_lit = None
        best_score = -1

        for v in range(1, self.num_vars + 1):
            pos = 2 * v

            if self.values[pos] != 0:
                continue

            pos_score = len(self.occurrences[pos])
            neg_score = len(self.occurrences[neg(pos)])

            if pos_score >= neg_score:
                lit = pos
                score = pos_score
            else:
                lit = neg(pos)
                score = neg_score

            if score > best_score:
                best_score = score
                best_lit = lit

        return best_lit

    def choose_literal(self):
        """
        ChooseLiteral: литерал для следующего решения или None, если все
        переменные означены.
        """
        lit = self.eliminate_pure_literals()

        if lit:
            return lit

        return self.most_freq()

    def solve(self) -> SATSolverResult:
        if self.sigkill.is_set():  # TODO: your code should check this predicate frequently! If it is set, you should return
            return SATSolverResult.UNKNOWN

        if self.has_empty_clause:
            return SATSolverResult.UNSAT

        self.build_occurrences()

        for lit in self.units:
            if self.values[lit] == -1:
                return SATSolverResult.UNSAT

            if self.values[lit] == 0:
                self.assign(lit)

        while True:
            if self.sigkill.is_set():
                return SATSolverResult.UNKNOWN

            if self.propagate():
                level = self.level()

                if level == 0:
                    return SATSolverResult.UNSAT

                decision_lit = self.decision(level)

                self.backtrack(level - 1)
                #self.assign(neg(decision_lit ^ 1))
                self.assign(neg(decision_lit))

                continue

            lit = self.choose_literal()

            if lit is None:
                self.save_model()
                return SATSolverResult.SAT

            self.decide(lit)


if __name__ == "__main__":
    result = Solver(sys.argv[1], Event()).solve()
    if result == SATSolverResult.SAT:
        print("sat")
    elif result == SATSolverResult.UNSAT:
        print("unsat")
    else:
        print("unknown")
