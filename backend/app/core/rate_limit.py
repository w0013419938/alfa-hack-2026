"""Простое ограничение попыток входа (в памяти процесса).

Ограничение: при нескольких экземплярах бэкенда у каждого свой счётчик.
В продакшене счётчик нужно хранить в общем хранилище (например, Redis) — см. docs/assumptions.md.
"""

import threading
import time


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        return [moment for moment in self._failures.get(key, []) if now - moment < self.window_seconds]

    def is_blocked(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            self._failures[key] = recent
            return len(recent) >= self.max_attempts

    def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            recent.append(now)
            self._failures[key] = recent

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
