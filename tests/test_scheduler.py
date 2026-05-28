"""Tests for hiccl.scheduler — RenderScheduler."""

import asyncio

import pytest


@pytest.mark.asyncio
class TestRenderScheduler:
    async def test_mark_dirty_and_tick(self):
        from hiccl.scheduler import RenderScheduler

        scheduler = RenderScheduler()
        rendered_ids = []
        pushed_patches = []

        async def render_fn(dirty_ids):
            rendered_ids.append(dirty_ids)
            return [
                {"type": "patch", "component_id": cid, "html": f"<p>{cid}</p>"}
                for cid in dirty_ids
            ]

        async def push_fn(patches):
            pushed_patches.extend(patches)

        # Start the scheduler
        loop = asyncio.get_event_loop()
        scheduler.start(loop, render_fn, push_fn)

        # Mark dirty
        scheduler.mark_dirty("comp-1")

        # Give the event loop time to process
        await asyncio.sleep(0.05)

        assert len(rendered_ids) > 0
        assert "comp-1" in rendered_ids[0]
        assert len(pushed_patches) > 0

        await scheduler.stop()

    async def test_batch_multiple_dirty(self):
        from hiccl.scheduler import RenderScheduler

        scheduler = RenderScheduler()
        rendered_ids = []

        async def render_fn(dirty_ids):
            rendered_ids.append(frozenset(dirty_ids))
            return []

        async def push_fn(patches):
            pass

        loop = asyncio.get_event_loop()
        scheduler.start(loop, render_fn, push_fn)

        # Mark multiple dirty before tick processes
        scheduler.mark_dirty("a")
        scheduler.mark_dirty("b")
        scheduler.mark_dirty("c")

        await asyncio.sleep(0.05)

        # Should have batched into one render call
        assert len(rendered_ids) >= 1
        assert frozenset({"a", "b", "c"}) in rendered_ids

        await scheduler.stop()

    async def test_stop_cancels_task(self):
        from hiccl.scheduler import RenderScheduler

        scheduler = RenderScheduler()
        loop = asyncio.get_event_loop()
        scheduler.start(loop, lambda ids: asyncio.sleep(0), lambda p: asyncio.sleep(0))
        assert scheduler._task is not None
        await scheduler.stop()
        assert scheduler._task is None
