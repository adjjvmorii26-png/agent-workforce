"""Offline tests: config, memory, bus, sandbox tools, and a full mock run."""

import json
import os
import tempfile
import unittest

from workforce.config import load_config
from workforce.memory import Memory
from workforce.bus import Bus, Event
from workforce.models import extract_json, parse_review, parse_tasks
from workforce.llm import MockProvider
from workforce.orchestrator import Workforce
from workforce.tools import SandboxError, build_default_registry
from workforce.config import WorkforceConfig

class TestTeam(unittest.TestCase):
    def test_all_agents_build(self):
        from workforce.config import WorkforceConfig
        from workforce.agents import build_team, AGENT_LOOKUP
        cfg = WorkforceConfig()
        team = build_team(MockProvider(), build_default_registry(cfg), Memory(""), Bus(workers=1), "x")
        self.assertIn("designer", team)
        self.assertIn("qa", team)
        self.assertIn("docsmith", team)
        self.assertIn("critic", team)
        self.assertIn("devops", team)
        self.assertIn("recruiter", team)
        self.assertIn("architect", team)
        self.assertIn("analyst", team)
        self.assertIn("curator", team)
        self.assertEqual(len(AGENT_LOOKUP), 14)

    def test_routing(self):
        from workforce.agents import resolve_agent_name
        for cap, agent in [("design","designer"),("redteam","critic"),("devops","devops"),("test","qa"),("docs","docsmith"),
                        ("recruit","recruiter"),("architecture","architect"),("analytics","analyst"),("curate","curator")]:
            self.assertEqual(resolve_agent_name(cap), agent)


class TestModels(unittest.TestCase):
    def test_extract_json_from_text(self):
        self.assertEqual(extract_json('x {"a": 1} y')["a"], 1)

    def test_parse_tasks(self):
        tasks = parse_tasks(json.dumps({"tasks": [{"id": "t1", "title": "T", "capability": "code", "depends_on": []}]}))
        self.assertEqual(tasks[0].capability, "code")

    def test_parse_review(self):
        r = parse_review('{"verdict": "pass", "score": 88, "comments": "ok"}')
        self.assertEqual(r.verdict, "pass")
        self.assertEqual(r.score, 88)


class TestMemory(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            m = Memory(os.path.join(d, "t.db"))
            m.remember("k", {"a": 1})
            self.assertEqual(m.recall("k")["a"], 1)
            m.start_run("r1", "goal", "mock", "m")
            m.upsert_task("r1", "t1", "code", "T", status="accepted", output="out", is_final=True)
            self.assertEqual(m.get_tasks("r1")[0]["status"], "accepted")


class TestBus(unittest.TestCase):
    def test_publish(self):
        b = Bus(workers=1)
        seen = []
        b.subscribe("x", lambda e: seen.append(e.payload["n"]))
        b.publish(Event("x", {"n": 1}))
        b.shutdown()
        self.assertEqual(seen, [1])


class TestTools(unittest.TestCase):
    def test_sandbox_escape_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = WorkforceConfig()
            cfg.tools.sandbox = d
            reg = build_default_registry(cfg)
            with self.assertRaises(SandboxError):
                reg.read_file("../outside.txt")
            self.assertIn("Wrote", reg.write_file("a/b.txt", "hi"))
            self.assertIn("a/b.txt", reg.list_files(recursive=True))
            with self.assertRaises(SandboxError):
                reg.write_file(".git/config", "bad")


class TestOrchestratorMock(unittest.TestCase):
    def test_full_run_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = load_config(yaml_path=None, env_path=None)
            cfg.provider = "mock"
            cfg.artifact_dir = os.path.join(d, "runs")
            cfg.memory_db = os.path.join(d, "wf.db")
            cfg.tools.sandbox = os.path.join(d, "ws")
            cfg.workers = 2
            w = Workforce(cfg)
            result = w.run("deliver a demo script", run_id="testrun")
            w.shutdown()
            self.assertEqual(result.status, "completed")
            ids = [t.id for t in result.tasks]
            self.assertIn("t1", ids)
            for t in result.tasks:
                self.assertIn(t.status.value, {"accepted", "failed", "blocked"})
            self.assertTrue(os.path.exists(result.report_path))
            with open(result.report_path, encoding="utf-8") as fh:
                report = fh.read()
            self.assertIn("# Final Report", report)


class TestFactory(unittest.TestCase):
    def test_recruiter_spawns_dynamic_agent(self):
        import os
        import tempfile as _tf
        from workforce.agents import AgentContext
        from workforce.agents.factory import RecruiterAgent, materialize_spec, DynamicAgent
        from workforce.models import Task
        with _tf.TemporaryDirectory() as d:
            cfg = WorkforceConfig()
            cfg.memory_db = os.path.join(d, "m.db")
            reg = build_default_registry(cfg)
            mem = Memory(cfg.memory_db)
            llm = MockProvider()
            bus = Bus(workers=1)
            task = Task(id="r", title="recruit", capability="recruit", description="need a localization agent")
            out = RecruiterAgent(llm, reg, mem, bus, "r1").run(AgentContext(goal="localize dashboard", task=task)).output
            self.assertIn("localizer", out)
            agent = materialize_spec(out, llm, reg, mem, bus, "r1")
            self.assertIsInstance(agent, DynamicAgent)
            self.assertEqual(agent.name, "localizer")
            got = agent.run(AgentContext(goal="x", task=task)).output
            self.assertTrue(got)
            bus.shutdown()


if __name__ == "__main__":
    unittest.main()
