"""hREPL Server — non-blocking TCP server for runtime exploration."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import TYPE_CHECKING, Any

from hiccl.repl.protocol import parse_message, serialize_response
from hiccl.repl.security import generate_token, log_audit

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger("hiccl.repl")


async def _eval_async(code: str, global_vars: dict[str, Any]) -> tuple[Any, str, str]:
    """Execute Python code in an asynchronous execution sandbox, capturing outputs."""
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    local_vars: dict[str, Any] = {}

    with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
        lines = code.splitlines()
        is_multiline = (
            len(lines) > 1
            or ";" in code
            or "import " in code
            or "def " in code
            or "class " in code
            or "=" in code
        )

        if is_multiline or "await " in code:
            if lines:
                last_line = lines[-1].strip()
                # A simple heuristic to see if the last line is an expression
                # (not a statement/import/assignment/def/class/etc.)
                is_statement = (
                    last_line.startswith("import ")
                    or last_line.startswith("from ")
                    or last_line.startswith("class ")
                    or last_line.startswith("def ")
                    or last_line.startswith("if ")
                    or last_line.startswith("for ")
                    or last_line.startswith("while ")
                    or last_line.startswith("try ")
                    or last_line.startswith("except ")
                    or last_line.startswith("with ")
                    or last_line.startswith("return ")
                    or last_line.startswith("print(")
                    or "=" in last_line
                )
                if not is_statement:
                    # Let's prefix the last line with 'return '
                    lines[-1] = f"return {lines[-1]}"

            indented_lines = "\n".join(f"    {line}" for line in lines)

            if "await " in code:
                wrapper_code = f"async def _hrepl_async_fn():\n{indented_lines}"
                exec(wrapper_code, global_vars, local_vars)
                result = await local_vars["_hrepl_async_fn"]()
            else:
                wrapper_code = f"def _hrepl_fn():\n{indented_lines}"
                exec(wrapper_code, global_vars, local_vars)
                result = local_vars["_hrepl_fn"]()
        else:
            try:
                # Try compiling as a single expression
                compiled = compile(code, "<hrepl>", "eval")
                result = eval(compiled, global_vars, local_vars)
                if asyncio.iscoroutine(result):
                    result = await result
            except SyntaxError:
                # Try compiling as statements block
                compiled = compile(code, "<hrepl>", "exec")
                exec(compiled, global_vars, local_vars)
                result = None

    return result, stdout_buf.getvalue(), stderr_buf.getvalue()


class HReplServer:
    """Non-blocking TCP server exposing an interactive Hiccl REPL."""

    def __init__(
        self, host: str = "127.0.0.1", port: int = 8998, app: FastAPI | None = None
    ) -> None:
        self.host = host
        self.port = port
        self.app = app
        self.token = os.environ.get("HREPL_TOKEN") or generate_token()
        self._server: asyncio.AbstractServer | None = None

        # Expose context variables to the REPL session
        import hiccl

        self.globals: dict[str, Any] = {
            "app": self.app,
            "hiccl": hiccl,
            "sys": sys,
            "os": os,
        }

    async def start(self) -> None:
        """Start listening on the configured TCP port if enabled."""
        hrepl_enabled = os.environ.get("HREPL_ENABLED", "").lower() in (
            "true",
            "1",
        )
        if not hrepl_enabled:
            logger.info(
                "hREPL is disabled (HREPL_ENABLED environment variable is not true)."
            )
            return

        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )

        banner = (
            f"\n"
            f"============================================================\n"
            f"🔓 Hiccl hREPL server started on {self.host}:{self.port}\n"
            f"🔑 Authentication Token: {self.token}\n"
            f"============================================================\n"
        )
        print(banner, flush=True)
        logger.info(f"hREPL listening on {self.host}:{self.port}")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peername = writer.get_extra_info("peername")
        client_info = str(peername)
        logger.info(f"hREPL: Client connected from {client_info}")

        try:
            # 1. Authentication Handshake
            auth_line = await reader.readline()
            if not auth_line:
                writer.close()
                return

            try:
                auth_req = parse_message(auth_line)
            except Exception:
                writer.write(
                    serialize_response("error", error="Invalid handshake format")
                )
                await writer.drain()
                writer.close()
                return

            if auth_req.get("token") != self.token:
                writer.write(serialize_response("error", error="Unauthorized"))
                await writer.drain()
                writer.close()
                logger.warning(
                    f"hREPL: Unauthorized connection attempt from {client_info}"
                )
                return

            writer.write(
                serialize_response("ok", message="Authenticated to Hiccl hREPL")
            )
            await writer.drain()

            # 2. Main REPL loop
            while True:
                line = await reader.readline()
                if not line:
                    break

                try:
                    req = parse_message(line)
                except Exception as e:
                    writer.write(
                        serialize_response(
                            "error", error=f"Invalid message format: {e}"
                        )
                    )
                    await writer.drain()
                    continue

                code = req.get("code")
                if not code:
                    writer.write(
                        serialize_response(
                            "error", error="Missing 'code' key in request"
                        )
                    )
                    await writer.drain()
                    continue

                try:
                    result, stdout, stderr = await _eval_async(code, self.globals)
                    log_audit(code, success=True, client_info=client_info)
                    writer.write(
                        serialize_response(
                            "ok",
                            value=repr(result),
                            stdout=stdout,
                            stderr=stderr,
                        )
                    )
                except Exception:
                    err_str = traceback.format_exc()
                    log_audit(code, success=False, client_info=client_info)
                    writer.write(serialize_response("error", error=err_str))

                await writer.drain()

        except Exception as e:
            logger.error(f"hREPL: Exception handling client {client_info}: {e}")
        finally:
            try:
                writer.close()
            except Exception:
                pass
            logger.info(f"hREPL: Client disconnected: {client_info}")

    async def stop(self) -> None:
        """Stop TCP server and close all connections."""
        if self._server is not None:
            self._server.close()
            self._server = None
            logger.info("hREPL server stopped")
