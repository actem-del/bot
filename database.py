import json
from pathlib import Path
from threading import Lock
from typing import Any


class JsonStore:
    def __init__(self, path: str | Path, default: dict[str, Any] | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.path.exists():
            self.write(default or {})

    def read(self) -> dict[str, Any]:
        with self._lock:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}

    def write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

    def mutate(self, callback):
        with self._lock:
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {}
            else:
                data = {}

            callback(data)

            with self.path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
