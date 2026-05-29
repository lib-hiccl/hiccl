"""Hiccl HMR Reloader — performs hot swapping of modified Python classes."""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from hiccl.component import Component

logger = logging.getLogger("hiccl.live_reload")


def reload_file_module(file_path: str, app: FastAPI) -> None:
    """Reload the module corresponding to the given file path and apply hot swapping.

    1. Finds the imported module matching the absolute file path.
    2. Reloads the module using importlib.reload.
    3. Finds all subclasses of Component in the reloaded module.
    4. Updates the global/app component registries.
    5. Modifies __class__ on all active session component instances to point to the new classes.
    6. Invalidates render caches and marks components dirty.
    """
    abs_path = os.path.abspath(file_path)
    module_name = None

    # Try to find the module by checking absolute file paths of imported modules
    for name, module in list(sys.modules.items()):
        mod_file = getattr(module, "__file__", None)
        if mod_file:
            try:
                if os.path.abspath(mod_file) == abs_path:
                    module_name = name
                    break
            except Exception:
                continue

    if not module_name:
        logger.debug(f"HMR: No imported module found matching {file_path}")
        return

    logger.info(f"HMR: Reloading module '{module_name}' from {file_path}")

    try:
        module = sys.modules[module_name]
        reloaded_module = importlib.reload(module)
    except Exception as e:
        logger.error(f"HMR: Error reloading module {module_name}: {e}", exc_info=True)
        return

    # Exported component base class reference to identify subclasses
    from hiccl.component import Component

    # Registry to update
    hiccl_state = getattr(app.state, "hiccl", {})
    registry = hiccl_state.get("registry") if isinstance(hiccl_state, dict) else None
    session_store = (
        hiccl_state.get("session_store") if isinstance(hiccl_state, dict) else None
    )
    config = hiccl_state.get("config") if isinstance(hiccl_state, dict) else None

    # Discover Component subclasses in the reloaded module
    reloaded_components: dict[str, type[Component]] = {}
    for attr_name in dir(reloaded_module):
        try:
            attr = getattr(reloaded_module, attr_name)
        except Exception:
            continue
        if (
            isinstance(attr, type)
            and issubclass(attr, Component)
            and attr is not Component
        ):
            # Determine its registered name
            comp_name = getattr(attr, "_hiccl_component_name", None)
            if not comp_name:
                comp_name = (
                    re.sub(r"(?<!^)(?=[A-Z])", "-", attr.__name__).strip("-").lower()
                )
                attr._hiccl_component_name = comp_name
            reloaded_components[comp_name] = attr

    if not reloaded_components:
        logger.debug(f"HMR: No components found in reloaded module '{module_name}'")
        return

    # Update Registry
    if registry:
        for comp_name, new_cls in reloaded_components.items():
            registry.register(comp_name, new_cls)
            logger.info(
                f"HMR: Updated component registry for '{comp_name}' -> {new_cls.__name__}"
            )

    # Update app config pages mapping if they point to the old class
    if config and config.pages:
        for path, old_cls in list(config.pages.items()):
            old_name = getattr(
                old_cls, "_hiccl_component_name", old_cls.__name__.lower()
            )
            if old_name in reloaded_components:
                config.pages[path] = reloaded_components[old_name]

    # Swap active instances in all sessions
    if session_store:

        async def swap_instances():
            try:
                sessions = await session_store.list_sessions()
                for session in sessions:
                    for cid, comp in list(session._components.items()):
                        comp_name = getattr(
                            comp,
                            "_hiccl_component_name",
                            comp.__class__.__name__.lower(),
                        )
                        if comp_name in reloaded_components:
                            new_cls = reloaded_components[comp_name]

                            # Swap class pointer
                            comp.__class__ = new_cls

                            # Invalidate renderer caches
                            session.renderer._cache.pop(cid, None)

                            # Mark dirty to trigger websocket push
                            if session.on_signal_change:
                                session.on_signal_change(cid)

                            logger.info(
                                f"HMR: Hot-swapped active component instance '{cid}'"
                            )
            except Exception as e:
                logger.error(f"HMR: Error swapping instances: {e}", exc_info=True)

        # Run the swap task in the active asyncio loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(swap_instances())
        except RuntimeError:
            # In case we are not in an active event loop (e.g. testing)
            asyncio.run(swap_instances())
