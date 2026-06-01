"""Hiccl Built-in Time Travel Panel Component — visualization of HistorySignals."""

from __future__ import annotations

import json
from hiccl.component import Component, server
from hiccl.registry import component
from hiccl.hiccup import div, button, span, input_, p, raw, fragment
from hiccl.signal import HistorySignal, Signal


@component("time-travel-panel")
class TimeTravelPanel(Component):
    """Built-in Glassmorphism Time Travel Panel for local development state tracing."""

    def __init__(self) -> None:
        super().__init__()
        self.expanded = Signal(False)

    @server
    def toggle_expand(self) -> None:
        """Toggle expand/collapse state."""
        self.expanded.set(not self.expanded.get())

    @server
    def undo_signal(self, key: str) -> None:
        """Undo the specified HistorySignal."""
        session = self._session
        if session and key in session._history_signals:
            sig = session._history_signals[key]
            sig.undo()

    @server
    def redo_signal(self, key: str) -> None:
        """Redo the specified HistorySignal."""
        session = self._session
        if session and key in session._history_signals:
            sig = session._history_signals[key]
            sig.redo()

    @server
    def jump_to_index(self, key: str, index: str) -> None:
        """Jump to the specific history snapshot index."""
        session = self._session
        if session and key in session._history_signals:
            sig = session._history_signals[key]
            try:
                sig.jump_to(int(index))
            except (ValueError, IndexError):
                pass

    def render(self) -> list:
        session = self._session
        if not session:
            return div({"class": "hidden"}, "")

        is_expanded = self.expanded.get()

        # Collapsed view — minimal hovering badge
        if not is_expanded:
            return div(
                {
                    "class": "fixed bottom-6 right-6 z-50 hover:scale-110 transition-transform duration-200"
                },
                button(
                    {
                        "class": "btn btn-circle bg-neutral/80 border border-white/20 shadow-2xl backdrop-blur-md hover:bg-neutral text-primary-content relative flex items-center justify-center",
                        "on_click": self.toggle_expand,
                        "title": "打开时间旅行调试器",
                    },
                    span(
                        {"class": "absolute -top-1 -right-1 flex h-3 w-3"},
                        span(
                            {
                                "class": "animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"
                            },
                            "",
                        ),
                        span(
                            {
                                "class": "relative inline-flex rounded-full h-3 w-3 bg-success"
                            },
                            "",
                        ),
                    ),
                    raw(
                        '<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-accent animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>'
                    ),
                ),
            )

        # Expanded view — glassmorphism panel
        signals_html = []
        for key, sig in list(session._history_signals.items()):
            hist_len = len(sig.history)
            curr_idx = sig.history_index
            val_repr = repr(sig.get())
            if len(val_repr) > 40:
                val_repr = val_repr[:37] + "..."

            display_name = "全局 re-frame DB" if key == "@re-frame-db" else key

            signals_html.append(
                div(
                    {
                        "class": "flex flex-col gap-2 p-3 bg-white/5 border border-white/10 rounded-lg shadow-inner"
                    },
                    div(
                        {"class": "flex justify-between items-center"},
                        span(
                            {
                                "class": "font-bold text-sm text-accent tracking-wide"
                            },
                            display_name,
                        ),
                        span(
                            {
                                "class": "text-xs bg-accent/20 text-accent px-2 py-0.5 rounded-full font-mono font-medium"
                            },
                            f"{curr_idx + 1} / {hist_len} 快照",
                        ),
                    ),
                    div(
                        {"class": "flex items-center gap-3 w-full"},
                        # Undo button
                        button(
                            {
                                "class": f"btn btn-xs btn-circle border border-white/10 {'btn-disabled opacity-40' if not sig.can_undo() else 'bg-primary hover:bg-primary-focus text-white'}",
                                "on_click": self.undo_signal(key=key),
                                "title": "撤销一小步",
                            },
                            "⟲",
                        ),
                        # Slider Control for Time Travel
                        input_(
                            {
                                "type": "range",
                                "min": "0",
                                "max": str(max(0, hist_len - 1)),
                                "value": str(curr_idx),
                                "name": "index",
                                "class": "range range-xs range-accent flex-1",
                                "hx-vals": json.dumps({"key": key}),
                                "on_change": self.jump_to_index,
                            }
                        ),
                        # Redo button
                        button(
                            {
                                "class": f"btn btn-xs btn-circle border border-white/10 {'btn-disabled opacity-40' if not sig.can_redo() else 'bg-primary hover:bg-primary-focus text-white'}",
                                "on_click": self.redo_signal(key=key),
                                "title": "重做一小步",
                            },
                            "⟳",
                        ),
                    ),
                    div(
                        {
                            "class": "text-xs text-base-content/70 font-mono truncate bg-black/20 p-1.5 rounded border border-black/10"
                        },
                        f"数据: {val_repr}",
                    ),
                )
            )

        if not signals_html:
            signals_html.append(
                p(
                    {
                        "class": "text-xs text-base-content/50 text-center py-4"
                    },
                    "当前无被追踪的历史信号",
                )
            )

        return div(
            {
                "class": "fixed bottom-6 right-6 z-50 w-96 max-w-sm rounded-2xl border border-white/20 bg-neutral/90 backdrop-blur-xl shadow-2xl p-4 flex flex-col gap-4 text-base-content transition-all duration-300"
            },
            # Header
            div(
                {
                    "class": "flex justify-between items-center border-b border-white/10 pb-2"
                },
                div(
                    {"class": "flex items-center gap-2"},
                    raw(
                        '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>'
                    ),
                    span(
                        {"class": "font-black text-white text-base tracking-tight"},
                        "Hiccl 时间旅行调试器",
                    ),
                ),
                button(
                    {
                        "class": "btn btn-xs btn-ghost text-base-content hover:bg-white/10 hover:text-white flex items-center justify-center font-bold",
                        "on_click": self.toggle_expand,
                        "style": "font-size: 14px; padding: 0; min-height: 24px; height: 24px; width: 24px;",
                    },
                    "✕",
                ),
            ),
            # Signal list
            div(
                {
                    "class": "flex flex-col gap-3 max-h-80 overflow-y-auto pr-1",
                    "x-data": "{}",
                    "x-init": "$el.scrollTop = localStorage.getItem('hiccl_dbg_scroll') || 0",
                    "@scroll": "localStorage.setItem('hiccl_dbg_scroll', $el.scrollTop)",
                },
                *signals_html,
            ),
            # Footer
            div(
                {
                    "class": "text-[10px] text-base-content/40 flex justify-between border-t border-white/5 pt-2 font-mono"
                },
                span("双轨制不可变快照已就绪"),
                span("Hiccl 🧬 Clojure"),
            ),
        )
