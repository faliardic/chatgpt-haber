from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import time
from pathlib import Path
from typing import Any, Iterator


class BuildTimer:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.started_at = datetime.now(timezone.utc)
        self._start = time.perf_counter()
        self.stages: dict[str, dict[str, Any]] = {}

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.stages[name] = {"seconds": round(time.perf_counter() - start, 3), "skipped": False}

    def skip(self, name: str) -> None:
        self.stages[name] = {"seconds": 0.0, "skipped": True}

    def as_dict(self) -> dict[str, Any]:
        finished_at = datetime.now(timezone.utc)
        return {
            "mode": self.mode,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "total_seconds": round(time.perf_counter() - self._start, 3),
            "stages": self.stages,
        }

    def write(self, path: Path) -> dict[str, Any]:
        from .issue import write_json

        data = self.as_dict()
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, data)
        return data

    def print_summary(self, data: dict[str, Any] | None = None) -> None:
        report = data or self.as_dict()
        for name, stage in report["stages"].items():
            if stage.get("skipped"):
                print(f"[GAZETTE TIMING] {name}: skipped")
            else:
                print(f"[GAZETTE TIMING] {name}: {stage.get('seconds', 0.0):.3f}s")
        print(f"[GAZETTE TIMING] total: {report['total_seconds']:.3f}s")
