"""In-process pub/sub message bus.

Agents and infrastructure (tracer, memory, CLI) publish and subscribe to typed
events. Subscribers run on a small thread pool so slow consumers do not block
the orchestration pipeline.
"""

from __future__ import annotations

import dataclasses
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

Handler = Callable[["Event"], None]


@dataclasses.dataclass
class Event:
    type: str
    payload: dict[str, Any] = dataclasses.field(default_factory=dict)
    source: str = "system"

    def __getitem__(self, key: str) -> Any:
        return self.payload[key]


class Bus:
    def __init__(self, workers: int = 4) -> None:
        self._subs: dict[str, list[Handler]] = {}
        self._any: list[Handler] = []
        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bus")

    def subscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            self._subs.setdefault(topic, []).append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        with self._lock:
            self._any.append(handler)

    def publish(self, event: Event) -> None:
        with self._lock:
            handlers = [*self._any, *self._subs.get(event.type, [])]
        for handler in handlers:
            self._pool.submit(self._safe, handler, event)

    @staticmethod
    def _safe(handler: Handler, event: Event) -> None:
        try:
            handler(event)
        except Exception:
            import logging

            logging.getLogger("workforce.bus").exception("handler failed for %s", event.type)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True)
