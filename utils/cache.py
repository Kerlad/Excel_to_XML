import time
import logging
from typing import Dict, Any, Optional, Tuple
from collections import OrderedDict

logger = logging.getLogger(__name__)


class LRUCache:
    """PERFORMANCE: LRU-кэш с ограничением по размеру и TTL."""

    def __init__(self, maxsize: int = 200, ttl_seconds: int = 300):
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        ts, value = self._cache[key]
        if time.time() - ts > self._ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        while len(self._cache) >= self._maxsize:
            self._cache.popitem(last=False)
        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        self._cache.clear()

    def invalidate(self, prefix: str) -> None:
        keys = [k for k in self._cache if k.startswith(prefix)]
        for k in keys:
            del self._cache[k]

    @property
    def size(self) -> int:
        return len(self._cache)


# PERFORMANCE: глобальные кэши API ответов
api_snils_cache = LRUCache(maxsize=500, ttl_seconds=600)
api_setid_cache = LRUCache(maxsize=100, ttl_seconds=600)

# PERFORMANCE: кэш сводки по сотрудникам (инвалидируется при изменении данных)
employee_summary_cache: Dict[str, Any] = {}
_summary_cache_dirty: bool = True


def invalidate_summary_cache() -> None:
    global _summary_cache_dirty
    _summary_cache_dirty = True
    employee_summary_cache.clear()


def is_summary_cache_valid() -> bool:
    return not _summary_cache_dirty and bool(employee_summary_cache)


def set_summary_cache(data: Any) -> None:
    global _summary_cache_dirty
    employee_summary_cache.clear()
    employee_summary_cache['data'] = data
    employee_summary_cache['ts'] = time.time()
    _summary_cache_dirty = False


def get_summary_cache() -> Optional[Any]:
    if _summary_cache_dirty:
        return None
    return employee_summary_cache.get('data')


# PERFORMANCE: Throttling для API запросов
class Throttle:
    def __init__(self, min_interval: float = 0.5):
        self._min_interval = min_interval
        self._last_call: float = 0.0

    def wait(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()

    def reset(self) -> None:
        self._last_call = 0.0


api_throttle = Throttle(min_interval=0.3)
