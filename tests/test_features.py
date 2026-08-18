"""Tests for splice (chimera), hive (consensus), oracle (forecast), pulse."""

import os
import tempfile
import unittest
from pathlib import Path

from workforce.bus import Bus
from workforce.config import WorkforceConfig
from workforce.llm import MockProvider
from workforce.memory import Memory
from workforce.tools import build_default_registry

CFG = WorkforceConfig()


def _infra(tmp: str):
    cfg = WorkforceConfig()
    cfg.memory_db = os.path.join(tmp, "m.db")
    return (
        MockProvider(),
        build_default_registry(cfg),
        Memory(cfg.memory_db),
        Bus(workers=1),
    )


class TestSplice(unittest.TestCase):
    def test_chimera_is_hybrid(self):
        with tempfile.TemporaryDirectory() as d:
            llm, reg, mem, bus = _infra(d)
            from workforce.splice import splice

            chimera = splice("critic", "designer", llm, reg, mem, bus, "t")
            self.assertIn("critic", chimera.system_prompt())
            self.assertIn("designer", chimera.system_prompt())
            self.assertEqual(chimera.name, "criticxdesigner")
            bus.shutdown()


class TestHive(unittest.TestCase):
    def test_consensus_has_views(self):
        with tempfile.TemporaryDirectory() as d:
            llm, reg, mem, bus = _infra(d)
            from workforce.hive import run_hive

            out = run_hive("What is the top risk?", llm, reg, mem, bus, "t")
            self.assertEqual(len(out["views"]), 3)
            self.assertTrue(out["consensus"])
            bus.shutdown()


class TestOracle(unittest.TestCase):
    def test_forecast_from_history(self):
        with tempfile.TemporaryDirectory() as d:
            llm, reg, mem, bus = _infra(d)
            mem.start_run("r1", "goal", "mock", "m")
            mem.upsert_task("r1", "t1", "code", "T", status="accepted", output="o", score=90, is_final=True)
            from workforce.oracle import forecast

            text = forecast(mem)
            self.assertIn("runs observed: 1", text)
            self.assertIn("accept rate 100%", text)
            bus.shutdown()


class TestPulse(unittest.TestCase):
    def test_pulse_records_without_commit(self):
        with tempfile.TemporaryDirectory() as d:
            llm, reg, mem, bus = _infra(d)
            from workforce.pulse import pulse

            text = pulse(evolve_dir=os.path.join(d, "evo"), commit=False)
            self.assertIn("WORKSPACE PULSE", text)
            self.assertIn("fitness", text)
            bus.shutdown()
            Path("WORKSPACE_PULSE.md").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
