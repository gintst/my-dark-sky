from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class JsonCache:
    def __init__(self, path: Path, ttl_seconds: int = 300) -> None:
        self.path = path
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Any | None:
        data = self._read()
        cached = data.get(key)
        if not cached:
            return None
        if time.time() - cached["stored_at"] > self.ttl_seconds:
            data.pop(key, None)
            self._write(data)
            return None
        return cached["payload"]

    def set(self, key: str, payload: Any) -> None:
        data = self._read()
        data[key] = {
            "stored_at": time.time(),
            "payload": payload,
        }
        self._write(data)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
