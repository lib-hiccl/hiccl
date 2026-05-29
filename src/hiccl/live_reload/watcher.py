"""Hiccl HMR Watcher — utilizes watchfiles to monitor file changes asynchronously."""

from __future__ import annotations

import asyncio
import logging
import os
from watchfiles import PythonFilter, awatch
from hiccl.live_reload.reloader import reload_file_module

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger("hiccl.live_reload")


async def start_watcher(app: FastAPI, path_to_watch: str | None = None) -> None:
    """Non-blocking async folder watcher utilizing watchfiles."""
    if path_to_watch is None:
        path_to_watch = os.getcwd()

    logger.info(f"HMR: Starting file watcher on directory: {path_to_watch}")

    try:
        async for changes in awatch(path_to_watch, watch_filter=PythonFilter()):
            for _, filepath in changes:
                try:
                    reload_file_module(filepath, app)
                except Exception as e:
                    logger.error(
                        f"HMR: Reloader failed for {filepath}: {e}",
                        exc_info=True,
                    )
    except asyncio.CancelledError:
        logger.info("HMR: File watcher task cancelled")
    except Exception as e:
        logger.error(f"HMR: Error in file watcher: {e}", exc_info=True)
