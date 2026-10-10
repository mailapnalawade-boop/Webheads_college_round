"""Small thread-safe LRU cache for finished audits (an injectable object, not module-level state)."""
import threading
from collections import OrderedDict
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class LRUCache(Generic[T]):
    def __init__(self, max_size: int):
        self._max = max_size
        self._items: "OrderedDict[str, T]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            if key not in self._items:
                return None
            self._items.move_to_end(key)
            return self._items[key]

    def put(self, key: str, value: T) -> None:
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self._max:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
