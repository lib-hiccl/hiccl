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

    async def test_tick_handles_exception_and_logs(self, caplog):
        import logging
        from hiccl.scheduler import RenderScheduler

        scheduler = RenderScheduler()

        async def render_fn(dirty_ids):
            raise ValueError("Simulated render crash")

        async def push_fn(patches):
            pass

        loop = asyncio.get_event_loop()
        with caplog.at_level(logging.ERROR, logger="hiccl.scheduler"):
            scheduler.start(loop, render_fn, push_fn)
            scheduler.mark_dirty("comp-1")
            await asyncio.sleep(0.05)
            await scheduler.stop()

        # Check that the exception was caught and logged
        assert any("Error during scheduler tick" in record.message for record in caplog.records)
        assert any(record.levelname == "ERROR" for record in caplog.records)

    async def test_scheduler_coalescing(self):
        from hiccl.scheduler import RenderScheduler

        # 100ms coalescence
        scheduler = RenderScheduler(coalesce_ms=100.0)
        rendered_ids = []

        async def render_fn(dirty_ids):
            rendered_ids.append(frozenset(dirty_ids))
            return []

        async def push_fn(patches):
            pass

        loop = asyncio.get_event_loop()
        scheduler.start(loop, render_fn, push_fn)

        scheduler.mark_dirty("comp-a")
        # sleep 30ms (less than coalesce_ms)
        await asyncio.sleep(0.03)
        scheduler.mark_dirty("comp-b")

        # At this point, render should NOT have run yet because 100ms has not passed
        assert len(rendered_ids) == 0

        # sleep 90ms more (total > 100ms)
        await asyncio.sleep(0.09)

        # Render should have run now, and both comp-a and comp-b should be batched
        assert len(rendered_ids) >= 1
        assert frozenset({"comp-a", "comp-b"}) in rendered_ids

        await scheduler.stop()
