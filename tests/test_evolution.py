"""Offline tests for the Breeding Tank evolution loop."""

import tempfile
import unittest
from pathlib import Path

from workforce.evolution import Evolver, VARIANT_LIBRARY


class TestEvolution(unittest.TestCase):
    def test_mutation_changes_prompt(self):
        evo = Evolver()
        a = evo._seed(0)
        b = evo._seed(1)
        self.assertIsInstance(a.system_prompt, str)
        self.assertTrue(len(a.system_prompt) > 0)

    def test_fitness_never_decreases(self):
        result = Evolver(population=6, generations=3).run(out_dir=tempfile.mkdtemp())
        curve = result.curve
        self.assertEqual(len(curve), 3)
        self.assertGreaterEqual(curve[-1][1], curve[0][1])

    def test_report_written(self):
        with tempfile.TemporaryDirectory() as d:
            result = Evolver(population=4, generations=2).run(out_dir=d)
            text = Path(result.report_path).read_text()
            self.assertIn("# Breeding Tank", text)
            self.assertIn(result.best.name, text)


if __name__ == "__main__":
    unittest.main()
