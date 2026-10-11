"""Per-run folder and append-only JSONL log of every action."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from .config import ROOT


class RunLog:
    def __init__(self, site_name: str, command: str):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = ROOT / "runs" / f"{stamp}-{site_name}-{command}"
        self.shots = self.dir / "screenshots"
        self.backup = self.dir / "backup"
        for d in (self.dir, self.shots, self.backup):
            d.mkdir(parents=True, exist_ok=True)
        self._file = (self.dir / "log.jsonl").open("a", encoding="utf-8")

    def event(self, kind: str, **data) -> None:
        record = {"t": round(time.time(), 3), "kind": kind, **data}
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()
        print(f"[{kind}] " + ", ".join(f"{k}={v}" for k, v in data.items()))

    def write_json(self, name: str, data) -> Path:
        path = self.dir / name
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def close(self) -> None:
        self._file.close()
