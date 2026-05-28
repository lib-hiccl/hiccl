"""Tests for hiccl.session_store — RedisSessionStore with Rehydration workflow."""

import pytest
import asyncio
from hiccl.component import Component
from hiccl.signal import Signal
from hiccl.registry import ComponentRegistry
from hiccl.renderer import HiccupRenderer
from hiccl.session import Session
from hiccl.session_store import RedisSessionStore, DummyRedisClient


class SimpleCounter(Component):
    _hiccl_component_name = "simple-counter"

    def __init__(self):
        super().__init__()
        self.count = Signal(0)

    def render(self):
        return ["div", None, f"Count: {self.count.get()}"]


@pytest.mark.asyncio
async def test_redis_session_store_rehydration():
    # 1. Setup registry and components
    registry = ComponentRegistry()
    registry.register("simple-counter", SimpleCounter)
    renderer = HiccupRenderer()

    # 2. Setup RedisSessionStore with Dummy client
    dummy_redis = DummyRedisClient()
    store = RedisSessionStore(redis_client=dummy_redis)
    store.registry = registry
    store.renderer = renderer

    # 3. Create active session and mutate state
    session_id = "test-rehydrate-session-id"
    session = Session(session_id, registry, renderer)
    
    comp = session.mount_component("simple-counter", cid="counter-xyz")
    assert comp.count.get() == 0
    
    # Mutate state (increment counter to 12)
    comp.count.set(12)
    assert comp.count.get() == 12

    # 4. Save session to store (persists meta & signals to DummyRedisClient)
    await store.save(session)
    
    # Verify metadata & signals were exported in dummy store
    meta_key = f"hiccl:session:{session_id}:meta"
    signals_key = f"hiccl:session:{session_id}:signals"
    assert dummy_redis.exists(meta_key)
    assert dummy_redis.exists(signals_key)

    # 5. Evict from local memory store to force a Rehydrate trigger on next get()
    await store._local.delete(session_id)
    assert await store._local.get(session_id) is None

    # 6. Retrieve session from store (triggers Redis Rehydration)
    restored = await store.get(session_id)
    assert restored is not None
    assert restored.session_id == session_id

    # 7. Assert that component was remounted and hydrated with correct signal snapshot
    restored_comp = restored.get_component("counter-xyz")
    assert restored_comp is not None
    assert isinstance(restored_comp, SimpleCounter)
    # CORE ASSERTION: check if the signal value survived the memory wipe!
    assert restored_comp.count.get() == 12
    assert "Count: 12" in renderer.render_component(restored_comp)
