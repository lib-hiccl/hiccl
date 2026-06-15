"""Hiccl WebShell — a real per-session PTY terminal in the browser (ttyd/gotty style).

Each browser session gets its own pseudo-terminal (PTY) hosting a real shell
(`bb` if available, otherwise ``$SHELL``). Keystrokes are streamed to the PTY
over a Hiccl binary stream and PTY output is streamed back, rendered by
xterm.js — full ANSI, colors, line editing, cursor control, and window resize.

This exercises the Hiccl stream transport end to end:

    browser xterm.js  ──stream──►  WebShellComponent  ──►  PTY (fork+exec)
                   ◄──stream──                      ◄──

Run:
    uv run python examples/webshell/app.py
    # or, via the CLI (note the .app module path — examples/ has no __init__.py):
    uv run hiccl dev examples.webshell.app:app

Override the launched command with ``HICCL_SHELL_CMD="fish -l"``.
The default is an isolated Docker container (debian:stable-slim) — Docker must be
installed and the server user must be able to ``docker run``.
"""

import asyncio
import fcntl
import json
import os
import pty
import resource
import shlex
import signal
import struct
import subprocess
import termios
import warnings

from hiccl import Component, ComponentRegistry, HicclConfig, create_hiccl_app, menu
from hiccl.hiccup import div, h2, p, raw, span
from hiccl.signal import Signal
from hiccl.transport.stream import StreamClosedError


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# A leading 0xFF byte marks a server-bound control frame. 0xFF is never a valid
# UTF-8 leading byte, so it cannot appear in keystrokes produced by xterm.js
# (which emits UTF-8 text) — a safe in-band sentinel.
_CONTROL_PREFIX = 0xFF

_STREAM_NAME = "terminal"

# xterm.js is bundled alongside this example (examples/webshell/static/) and
# served same-origin from /static/. This avoids any CDN dependency — important
# where jsdelivr/unpkg are slow or unreachable — and keeps the demo fully
# offline-capable, matching Hiccl's offline-first defaults.
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

_XTERM_HEAD = """
  <link rel="stylesheet" href="/static/xterm.css">
  <script src="/static/xterm.min.js"></script>
  <script src="/static/xterm-addon-fit.min.js"></script>
  <script src="/static/xterm-addon-weblinks.min.js"></script>
  <script src="/static/webshell.js"></script>
"""


def detect_command(container_label: str = "default") -> list[str]:
    """Pick the shell command to launch inside the PTY.

    Honors ``HICCL_SHELL_CMD``; otherwise launches an isolated Docker container
    (debian:stable-slim) hardened for public-internet deployment:

    * ``--network none`` — complete network isolation
    * ``--memory 64m`` / ``--cpus 0.5`` — minimal resource footprint
    * ``--read-only`` + tmpfs mounts — no persistent writes to the image
    * ``--cap-drop ALL`` / ``--security-opt no-new-privileges`` — no kernel capabilities
    * ``--pids-limit 50`` / ``--ulimit nproc`` — fork-bomb & thread-bomb protection
    * ``--shm-size 4m`` — closes /dev/shm memory bypass
    * ``--init`` — tini PID 1 for proper signal forwarding & zombie reaping
    * ``--user 65534`` — non-root user inside container
    * ``--rm`` + ``--label`` — container destroyed on exit, with fallback cleanup

    The Docker daemon must be running and the server user must have permission
    to create containers (typically via the ``docker`` group).
    """
    raw = os.environ.get("HICCL_SHELL_CMD")
    if raw and raw.strip():
        return shlex.split(raw)
    return [
        "docker",
        "run",
        "--rm",
        "-it",
        "--network",
        "none",
        "--memory",
        "64m",
        "--memory-swap",
        "64m",
        "--cpus",
        "0.5",
        "--cpu-rt-runtime",
        "0",
        "--pids-limit",
        "50",
        "--shm-size",
        "4m",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--tmpfs",
        "/run:rw,noexec,nosuid,size=8m",
        "--tmpfs",
        "/var/tmp:rw,noexec,nosuid,size=4m",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--init",
        "--stop-timeout",
        "5",
        "--ulimit",
        "nproc=50:50",
        "--ulimit",
        "nofile=64:64",
        "--log-driver",
        "none",
        "--label",
        f"hiccl.session={container_label}",
        "--user",
        "65534:65534",
        "debian:stable-slim",
    ]


# ---------------------------------------------------------------------------
# PTY process (stdlib only — no third-party deps)
# ---------------------------------------------------------------------------


class PtyProcess:
    """A child process attached to a pseudo-terminal with a controlling tty.

    Mirrors what ttyd/gotty do: ``openpty`` → ``fork`` → child calls
    ``setsid`` + ``TIOCSCTTY`` to acquire the slave as controlling terminal,
    then ``exec`` the shell. The parent holds the non-blocking master fd.
    """

    def __init__(
        self,
        argv: list[str],
        cols: int = 80,
        rows: int = 24,
        env: dict[str, str] | None = None,
        container_label: str = "",
    ) -> None:
        self.argv = list(argv)
        self.cols = cols
        self.rows = rows
        self.env = dict(env) if env else {}
        self.container_label = container_label
        self.master_fd: int | None = None
        self.pid: int | None = None

    @staticmethod
    def _set_winsize(fd: int, rows: int, cols: int) -> None:
        try:
            fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except OSError:
            pass

    @staticmethod
    def _fork() -> int:
        # CPython warns when os.fork() is called in a multi-threaded process
        # (the test client, and some ASGI servers, keep helper threads). The
        # deadlock the warning guards against cannot happen here: our child
        # path runs only raw syscalls (setsid/ioctl/dup2/close/execvpe) on the
        # way to exec — it never re-enters the inherited event loop or its
        # locks. Scope the suppression tightly to this single call.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*use of fork\(\) may lead to deadlocks.*",
                category=DeprecationWarning,
            )
            return os.fork()

    def start(self) -> None:
        if self.master_fd is not None:
            return
        master_fd, slave_fd = pty.openpty()
        self._set_winsize(slave_fd, self.rows, self.cols)
        pid = self._fork()
        if pid == 0:
            # ---------------- child ----------------
            try:
                os.close(master_fd)
                os.setsid()
                try:
                    fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
                except OSError:
                    pass
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                if slave_fd > 2:
                    os.close(slave_fd)
                try:
                    max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
                except Exception:
                    max_fd = 1024
                os.closerange(3, max_fd)
                env = {
                    "TERM": "xterm-256color",
                    "PATH": os.environ.get(
                        "PATH",
                        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    ),
                    "HOME": "/tmp",
                    "LANG": os.environ.get("LANG", "C.UTF-8"),
                }
                env.update(self.env)
                os.execvpe(self.argv[0], self.argv, env)
            except Exception:
                pass
            os._exit(127)
        # ---------------- parent ----------------
        os.close(slave_fd)
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        self.master_fd = master_fd
        self.pid = pid

    def resize(self, rows: int, cols: int) -> None:
        self.rows = rows
        self.cols = cols
        if self.master_fd is not None:
            self._set_winsize(self.master_fd, rows, cols)

    def write(self, data: bytes) -> int:
        if self.master_fd is None:
            return 0
        try:
            return os.write(self.master_fd, data)
        except OSError:
            return 0

    def read(self, n: int = 65536) -> bytes:
        if self.master_fd is None:
            return b""
        try:
            return os.read(self.master_fd, n)
        except OSError:
            return b""

    def kill(self) -> None:
        pid, self.pid = self.pid, None
        if pid is not None:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                pass
            else:
                try:
                    os.waitpid(pid, 0)
                except OSError:
                    pass
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
        if self.container_label:
            self._cleanup_docker_container()

    def _cleanup_docker_container(self) -> None:
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-aq",
                    "--filter",
                    f"label=hiccl.session={self.container_label}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for cid in result.stdout.strip().split("\n"):
                if cid:
                    subprocess.run(
                        ["docker", "rm", "-f", cid],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                    )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Inbound frame parsing — distinguish keystrokes from resize control frames
# ---------------------------------------------------------------------------


def parse_terminal_frame(data: bytes) -> tuple[str, tuple[int, int] | bytes]:
    """Classify an inbound terminal stream frame.

    Returns ``("resize", (rows, cols))`` for a control frame, otherwise
    ``("data", payload)``. Malformed control frames degrade to empty data so a
    bad resize never corrupts the terminal stream.
    """
    if data and data[0] == _CONTROL_PREFIX:
        try:
            msg = json.loads(data[1:].decode("utf-8"))
            return ("resize", (int(msg["rows"]), int(msg["cols"])))
        except (ValueError, KeyError, TypeError):
            return ("data", b"")
    return ("data", data)


# ---------------------------------------------------------------------------
# WebShell component
# ---------------------------------------------------------------------------


class WebShellComponent(Component):
    """Renders an xterm.js terminal backed by a per-session PTY."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.pty: PtyProcess | None = None
        self.stream = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._read_queue: asyncio.Queue | None = None
        self._tasks: list[asyncio.Task] = []
        self.pty_status = Signal("connecting")

    # -- lifecycle ---------------------------------------------------------

    async def on_stream_open(self, stream) -> None:
        """Spawn the PTY and pump bytes both ways once the client connects."""
        self._teardown()
        self.stream = stream
        self._loop = asyncio.get_running_loop()
        self.pty_status.set("connecting")
        try:
            self.pty = PtyProcess(
                detect_command(container_label=self.component_id),
                container_label=self.component_id,
            )
            self.pty.start()
        except Exception as exc:  # pragma: no cover - environment dependent
            self.pty_status.set("closed")
            try:
                await stream.send(
                    f"\r\n\x1b[31m*** failed to start shell: {exc} ***\x1b[0m\r\n".encode()
                )
            except Exception:
                pass
            return
        self.pty_status.set("live")
        self._read_queue = asyncio.Queue()
        self._loop.add_reader(self.pty.master_fd, self._on_pty_readable)
        self._tasks = [
            asyncio.create_task(self._pump_pty_to_stream()),
            asyncio.create_task(self._pump_stream_to_pty()),
            asyncio.create_task(self._watchdog()),
        ]

    def unmount(self) -> None:
        self._teardown()
        if self.stream is not None and not self.stream.closed:
            self.stream.close_sync()
        self.stream = None
        self._read_queue = None
        super().unmount()

    # -- byte pumps --------------------------------------------------------

    def _on_pty_readable(self) -> None:
        assert self.pty is not None and self._read_queue is not None
        data = self.pty.read()
        if data == b"":
            # EOF — stop watching and signal the pump.
            if self._loop is not None and self.pty.master_fd is not None:
                try:
                    self._loop.remove_reader(self.pty.master_fd)
                except Exception:
                    pass
            self._read_queue.put_nowait(None)
        else:
            self._read_queue.put_nowait(data)

    async def _pump_pty_to_stream(self) -> None:
        try:
            while True:
                assert self._read_queue is not None
                data = await self._read_queue.get()
                if data is None:
                    return  # PTY exited
                if self.stream is not None and not self.stream.closed:
                    await self.stream.send(data)
        except StreamClosedError:
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            return

    async def _pump_stream_to_pty(self) -> None:
        try:
            assert self.stream is not None
            async for data in self.stream:
                if not data:
                    continue
                kind, value = parse_terminal_frame(bytes(data))
                if kind == "resize":
                    if self.pty is not None:
                        self.pty.resize(*value)  # type: ignore[arg-type]
                else:
                    if self.pty is not None:
                        self.pty.write(value)  # type: ignore[arg-type]
        except StreamClosedError:
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    async def _watchdog(self) -> None:
        """Tear everything down as soon as either pump finishes.

        Covers both exit paths: the user typing ``exit`` (PTY EOF → pty pump
        ends) and the client disconnecting / closing the stream (stream pump
        ends). FIRST_COMPLETED so an idle PTY is still reaped on disconnect.
        """
        pumps = self._tasks[:2]
        try:
            await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        except Exception:
            pass
        self._teardown()
        self.pty_status.set("closed")
        if self.stream is not None and not self.stream.closed:
            await self.stream.close()
        self.stream = None
        self._read_queue = None

    def _teardown(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        self._tasks = []
        if self.pty is not None:
            if self._loop is not None and self.pty.master_fd is not None:
                try:
                    self._loop.remove_reader(self.pty.master_fd)
                except Exception:
                    pass
            self.pty.kill()
            self.pty = None

    # -- view --------------------------------------------------------------

    def render(self):
        cid = self.component_id
        status = self.pty_status.get()

        if status == "live":
            badge_status_class = "badge badge-success"
            badge_status_dot = span(
                {"class": "w-2 h-2 rounded-full bg-emerald-300 animate-pulse"}
            )
            badge_status_text = "live"
        elif status == "connecting":
            badge_status_class = "badge badge-warning"
            badge_status_dot = span(
                {"class": "w-2 h-2 rounded-full bg-amber-300 animate-pulse"}
            )
            badge_status_text = "connecting"
        else:
            badge_status_class = "badge badge-ghost"
            badge_status_dot = ""
            badge_status_text = "closed"

        return div(
            {
                "class": "card bg-slate-900/90 border border-slate-700/50 backdrop-blur-xl shadow-2xl mx-auto w-full max-w-5xl"
            },
            div(
                {"class": "card-body p-6"},
                div(
                    {
                        "class": "flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4"
                    },
                    div(
                        {},
                        h2(
                            {
                                "class": "card-title text-2xl font-bold text-slate-100 flex items-center gap-2"
                            },
                            "🐚 Hiccl WebShell",
                        ),
                        p(
                            {"class": "text-xs text-slate-400 mt-1"},
                            "真实伪终端 (PTY) · 每个浏览器会话独立分配 · 基于 Hiccl 流式传输",
                        ),
                    ),
                    div(
                        {
                            "id": f"term-status-{cid}",
                            "class": f"{badge_status_class} gap-1 font-mono text-xs py-3",
                        },
                        badge_status_dot,
                        " " + badge_status_text,
                    ),
                ),
                div(
                    {
                        "class": "rounded-xl overflow-hidden border border-slate-800 shadow-inner bg-black",
                    },
                    div(
                        {
                            "id": f"term-host-{cid}",
                            "class": "hiccl-terminal",
                            "style": "height: 30rem; padding: 0.5rem;",
                        }
                    ),
                ),
                p(
                    {"class": "mt-3 text-xs text-slate-500"},
                    "提示：默认运行于 Docker 沙箱 (debian:stable-slim, 无网络, 64MB 内存限制)。支持 ANSI 颜色、行编辑、光标与窗口尺寸同步。输入 ",
                    span({"class": "font-mono text-slate-400"}, "exit"),
                    " 退出会关闭终端。",
                ),
                raw("<script>WebShellTerminal.init('" + cid + "')</script>"),
            ),
        )


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

registry = ComponentRegistry()
app = create_hiccl_app(
    HicclConfig(
        component_registry=registry,
        transport_modes={"http", "ws"},
        pages=menu(WebShellComponent),
        brand_name="Hiccl WebShell",
        title="Hiccl WebShell",
        description="Per-session PTY terminal in the browser — ttyd/gotty style.",
        theme="dark",
        head_extra=_XTERM_HEAD,
        static_dir=_STATIC_DIR,
    )
)


if __name__ == "__main__":
    import uvicorn

    print("Starting Hiccl WebShell...")
    print("URL: http://127.0.0.1:8000")
    print(f"Shell command: {' '.join(detect_command())}")
    uvicorn.run(app, host="127.0.0.1", port=8000)
