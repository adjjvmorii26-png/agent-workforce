"""JSONL run tracing for observability."""

from __future__ import annotations

import json
import pathlib
import time
from typing import Any


class Tracer:
    def __init__(self, run_dir: pathlib.Path) -> None:
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.run_dir / "trace.jsonl"

    def event(self, type_: str, **data: Any) -> None:
        line = {
            "ts": time.time(),
            "type": type_,
            **data,
        }
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, default=str) + "\n")

    @property
    def path(self) -> pathlib.Path:
        return self._path
