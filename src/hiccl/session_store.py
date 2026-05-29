"""Hiccl SessionStore — session storage abstraction with concurrency-safe memory backend."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from hiccl.session import Session


class SessionStore(ABC):
    """Abstract base class for Session storage backends."""

    @abstractmethod
    async def get(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID. Returns None if not found or expired."""
        pass

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Save/update a session in the store."""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Destroy and dispose a session by ID."""
        pass

    @abstractmethod
    async def list_sessions(self) -> list[Session]:
        """Return a list of all active sessions in the store."""
        pass

    @abstractmethod
    async def sweep_expired(self, max_age: float) -> list[str]:
        """Scan and evict inactive sessions that exceeded max_age.

        Returns a list of evicted session IDs.
        """
        pass


class MemorySessionStore(SessionStore):
    """Thread/Coroutine-safe in-memory session store."""

    def __init__(self) -> None:
        from hiccl.session import _sessions

        self._sessions = _sessions
        self._lock = asyncio.Lock()

    async def get(self, session_id: str) -> Optional[Session]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
            return session

    async def save(self, session: Session) -> None:
        async with self._lock:
            self._sessions[session.session_id] = session

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.dispose()

    async def list_sessions(self) -> list[Session]:
        async with self._lock:
            return list(self._sessions.values())

    async def sweep_expired(self, max_age: float) -> list[str]:
        import time

        evicted = []
        async with self._lock:
            now = time.time()
            for sid, session in list(self._sessions.items()):
                # If transport is active, touch session to keep it alive
                if session.transport.is_connected():
                    session.touch()
                    continue
                if now - session.last_accessed > max_age:
                    evicted.append(sid)

            for sid in evicted:
                session = self._sessions.pop(sid, None)
                if session:
                    session.dispose()
        return evicted


class DummyRedisClient:
    """Mock Redis client used when actual redis is missing or for testing."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def exists(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def setex(self, key: str, seconds: int, value: str) -> None:
        self._data[key] = value

    def delete(self, *keys: str) -> None:
        for k in keys:
            self._data.pop(k, None)


class RedisSessionStore(SessionStore):
    """Distributed SessionStore with local memory cache + Redis backup.

    Implements Hybrid Sticky Session with Redis backup & Rehydration.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        local_store: MemorySessionStore | None = None,
        redis_client: Any = None,
    ) -> None:
        self._local = local_store or MemorySessionStore()
        self.registry = None
        self.renderer = None

        if redis_client is not None:
            self._redis = redis_client
        else:
            try:
                import redis
                from redis.retry import Retry
                from redis.backoff import ExponentialBackoff

                # 配置原生的指数退避重连机制
                retry = Retry(ExponentialBackoff(), 3)

                # 配置 ConnectionPool
                pool = redis.ConnectionPool.from_url(
                    redis_url,
                    decode_responses=True,
                    retry_on_timeout=True,
                )
                self._redis = redis.Redis(connection_pool=pool, retry=retry)
                self._redis.ping()
            except Exception:
                self._redis = DummyRedisClient()

    def lock(self, session_id: str, timeout: float = 10.0) -> Any:
        """返回针对特定 session_id 的悲观分布式锁上下文管理器。

        适用于在高频 WebSocket 写入时防止状态竞争覆盖。
        """
        if self._redis is not None and not isinstance(self._redis, DummyRedisClient):
            lock_key = f"hiccl:lock:{session_id}"
            return self._redis.lock(lock_key, timeout=timeout)
        else:

            class DummyLock:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            return DummyLock()

    def _pack_data(self, data: Any) -> str:
        """使用 msgpack 压缩并进行 base64 编码，如果 msgpack 不可用，则优雅降级使用 orjson 或内置 json。"""
        try:
            import msgpack
            import base64

            packed = msgpack.packb(data)
            return "msgpack:" + base64.b64encode(packed).decode("ascii")
        except (ImportError, Exception):
            pass

        try:
            import orjson

            return "orjson:" + orjson.dumps(data).decode("utf-8")
        except (ImportError, Exception):
            pass

        import json

        return "json:" + json.dumps(data)

    def _unpack_data(self, data_str: str) -> Any:
        """对打包的数据进行解压和还原，支持优雅的降级兼容。"""
        if not data_str:
            return {}

        if data_str.startswith("msgpack:"):
            import msgpack
            import base64

            raw_b64 = data_str[len("msgpack:") :]
            packed = base64.b64decode(raw_b64.encode("ascii"))
            return msgpack.unpackb(packed)

        if data_str.startswith("orjson:"):
            import orjson

            raw_json = data_str[len("orjson:") :]
            return orjson.loads(raw_json)

        if data_str.startswith("json:"):
            import json

            raw_json = data_str[len("json:") :]
            return json.loads(raw_json)

        # 兼容旧版本不带前缀的裸 JSON 串
        import json

        try:
            return json.loads(data_str)
        except Exception:
            return {}

    async def get(self, session_id: str) -> Optional[Session]:
        # 1. Try local cache
        session = await self._local.get(session_id)
        if session:
            return session

        # 2. Try Redis restore & Rehydrate
        if self._redis is None:
            return None

        meta_key = f"hiccl:session:{session_id}:meta"
        signals_key = f"hiccl:session:{session_id}:signals"

        try:
            if not self._redis.exists(meta_key):
                return None
        except Exception:
            return None

        meta_data_str = self._redis.get(meta_key)
        if not meta_data_str:
            return None

        meta_data = self._unpack_data(meta_data_str)
        if not meta_data:
            return None

        if not self.registry or not self.renderer:
            return None

        from hiccl.session import Session

        # Reconstruct Session instance
        session = Session(session_id, self.registry, self.renderer, store=self)

        # Restore component hierarchy and their signals
        signals_data_str = self._redis.get(signals_key)
        signals_data = {}
        if signals_data_str:
            try:
                signals_data = self._unpack_data(signals_data_str)
            except Exception:
                pass

        components_list = meta_data.get("components", [])
        for comp_info in components_list:
            name = comp_info.get("name")
            cid = comp_info.get("cid")
            props = comp_info.get("props", {})

            # Mount component
            comp = session.mount_component(name, cid=cid, **props)

            # Hydrate signals
            comp_signals = signals_data.get(cid, {})
            for sig_name, val in comp_signals.items():
                if sig_name in comp._signals:
                    comp._signals[sig_name].set(val)

        # Save to local cache
        await self._local.save(session)
        return session

    async def save(self, session: Session) -> None:
        await self._local.save(session)

        if self._redis is None:
            return

        components_list = []
        signals_data = {}

        for cid, comp in session._components.items():
            comp_name = getattr(
                comp, "_hiccl_component_name", comp.__class__.__name__.lower()
            )
            components_list.append({"name": comp_name, "cid": cid, "props": {}})

            comp_signals = {}
            for sig_name, sig in comp._signals.items():
                comp_signals[sig_name] = sig._value
            signals_data[cid] = comp_signals

        meta_data = {
            "session_id": session.session_id,
            "components": components_list,
            "last_accessed": session.last_accessed,
        }

        meta_key = f"hiccl:session:{session.session_id}:meta"
        signals_key = f"hiccl:session:{session.session_id}:signals"

        try:
            self._redis.setex(meta_key, 1800, self._pack_data(meta_data))
            self._redis.setex(signals_key, 1800, self._pack_data(signals_data))
        except Exception:
            pass

    async def delete(self, session_id: str) -> None:
        await self._local.delete(session_id)
        if self._redis is None:
            return

        meta_key = f"hiccl:session:{session_id}:meta"
        signals_key = f"hiccl:session:{session_id}:signals"

        try:
            self._redis.delete(meta_key, signals_key)
        except Exception:
            pass

    async def list_sessions(self) -> list[Session]:
        return await self._local.list_sessions()

    async def sweep_expired(self, max_age: float) -> list[str]:
        # Local eviction handles actual cleanup of active instances
        evicted = await self._local.sweep_expired(max_age)
        if self._redis is not None:
            for sid in evicted:
                meta_key = f"hiccl:session:{sid}:meta"
                signals_key = f"hiccl:session:{sid}:signals"
                try:
                    self._redis.delete(meta_key, signals_key)
                except Exception:
                    pass
        return evicted
