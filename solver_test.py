import os
from threading import Event, Thread
from solver import Solver
from time import perf_counter
from utils import SATSolverResult
from collections import defaultdict
import json


class Tests:
    def __init__(self, TIME_LIMIT: float):
        self.results = defaultdict(lambda: SATSolverResult.UNKNOWN)
        self.RANK = 0.0
        self.TIME_LIMIT = TIME_LIMIT
        self.tests_dir = os.path.join(os.getcwd(), "tests")

    def worker(self, path, event):
        self.results[path] = Solver(path, event).solve()

    def runner(self, path):
        event = Event()
        thread = Thread(target=self.worker, args=(path, event))
        t1 = perf_counter()
        thread.start()
        thread.join(self.TIME_LIMIT)
        event.set()
        thread.join()
        delta_t = perf_counter() - t1
        return delta_t

    def test_folder(self, folder: str, gold_result: SATSolverResult):
        for entry in os.scandir(os.path.join(self.tests_dir, folder)):
            # print("Solving", entry.path)
            delta_t = self.runner(entry.path)
            result = self.results[entry.path]
            if delta_t <= self.TIME_LIMIT and result != SATSolverResult.UNKNOWN:
                if result == gold_result:
                    self.RANK += delta_t
                else:
                    self.RANK += self.TIME_LIMIT * 4
            else:
                self.RANK += self.TIME_LIMIT

    def rank_solver(self, tests):
        for folder, gold_result in tests:
            self.test_folder(folder, gold_result)

    def test_dpll(self):
        self.rank_solver([("sat-dpll", SATSolverResult.SAT), ("unsat-dpll", SATSolverResult.UNSAT)])
        MAX_SCORE = 10
        FULL_SCORE_RANK = 30.0
        SOFTNESS = 40.0

        task_score = min(MAX_SCORE, round(MAX_SCORE * (FULL_SCORE_RANK + SOFTNESS)
                                          / (self.RANK + SOFTNESS)))

        print(f"Your solver RANK: {self.RANK:.10f}")
        print(f"Your score for this homework: {task_score} points")

        passed_test = {
            "name": "Score",
            "status": "pass",
            "message": None,
            "line_no": None,
            "execution_time": "0ms",
            "score": 1,
        }

        failed_test = {
            "name": "Score",
            "status": "fail",
            "message": None,
            "line_no": None,
            "execution_time": "0ms",
            "score": 0,
        }

        scored_points = ([passed_test] * task_score) + ([failed_test] * (MAX_SCORE - task_score))

        results = {
            "version": 1,
            "status": "pass",
            "tests": scored_points,
            "max_score": MAX_SCORE,
        }

        with open('results.json', 'w') as f:
            json.dump(results, f)

        self.RANK = 0


if __name__ == "__main__":
    Tests(TIME_LIMIT=10.0).test_dpll()
