"""Offline tests for the IXPANSION recipe engine (X-01)."""

import tempfile
import unittest
from pathlib import Path

from ixpansion.core.engine import Engine
from ixpansion.core.recipe import Recipe, RecipeError
from workforce.llm import MockProvider


class TestRecipe(unittest.TestCase):
    def test_load_named_recipe(self):
        p = Path("ixpansion/content_output/recipes/summary.yaml")
        r = Recipe.load(p)
        self.assertEqual(r.name, "summary")
        self.assertEqual(len(r.steps), 3)

    def test_rejects_empty_steps(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.yaml"
            bad.write_text("name: bad\nsteps: []\n")
            with self.assertRaises(RecipeError):
                Recipe.load(bad)


class TestEngine(unittest.TestCase):
    def test_mock_run_writes_report(self):
        with tempfile.TemporaryDirectory() as d:
            engine = Engine(MockProvider(), output_dir=d)
            result = engine.run(
                Recipe.load("ixpansion/content_output/recipes/summary.yaml"),
                "Launch a rocket to Mars.",
            )
            self.assertEqual(result.status, "ok")
            self.assertEqual(result.steps, 3)
            content = Path(result.report_path).read_text()
            self.assertIn("# summary", content)
            self.assertIn("## Overview", content)
            self.assertIn("## Outcome", content)

    def test_empty_input_rejected(self):
        engine = Engine(MockProvider(), output_dir=tempfile.mkdtemp())
        with self.assertRaises(RecipeError):
            engine.run(
                Recipe.load("ixpansion/content_output/recipes/summary.yaml"),
                "   ",
            )


class TestEvaluate(unittest.TestCase):
    def test_mock_judge_scores(self):
        from ixpansion.core.evaluate import evaluate_report

        ev = evaluate_report("# Report\n\nbody", "goal", mock=True)
        self.assertEqual(ev.relevance, 88)
        self.assertEqual(ev.structure, 85)
        self.assertTrue(0 <= ev.mean <= 100)


if __name__ == "__main__":
    unittest.main()
