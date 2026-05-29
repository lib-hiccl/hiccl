"""Hiccl Performance Benchmark Suite — evaluates latency of signals, renders, and diffs."""

from __future__ import annotations

import timeit
from hiccl import (
    Signal,
    ComputedSignal,
    Effect,
    Component,
    signal,
    div,
    h2,
    button,
    DiffEngine,
    HiccupRenderer,
)


class BenchmarkCounter(Component):
    """Component used for rendering benchmarks."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = signal(0)

    def render(self):
        return div(
            {"class": "card w-96 bg-base-200 shadow-xl border border-base-300 mx-auto"},
            div(
                {"class": "card-body items-center text-center"},
                h2(
                    {"class": "card-title text-3xl font-extrabold mb-4"},
                    f"Count: {self.count.get()}",
                ),
                div(
                    {"class": "card-actions justify-center gap-2"},
                    button({"class": "btn btn-error"}, "-1"),
                    button({"class": "btn btn-success"}, "+1"),
                ),
            ),
        )


def benchmark_signals() -> float:
    """Benchmark reactive Signal propagation and Computed/Effect latencies."""
    s = Signal(10)
    c1 = ComputedSignal(lambda: s.get() * 2)
    c2 = ComputedSignal(lambda: c1.get() + 5)

    triggered = 0

    def watch():
        nonlocal triggered
        c2.get()
        triggered += 1

    eff = Effect(watch)

    # Measure set-get cycle
    def run():
        s.set(s.get() + 1)
        c2.get()

    number = 10000
    total_time = timeit.timeit(run, number=number)
    eff.dispose()

    avg_ms = (total_time / number) * 1000.0
    return avg_ms


def benchmark_diff_and_render() -> tuple[float, float]:
    """Benchmark HTML serialization and DiffEngine calculation speed."""
    renderer = HiccupRenderer()
    comp = BenchmarkCounter()
    comp._discovered_signals()

    # 1. Benchmark Component Rendering
    def run_render():
        renderer.render_component(comp)

    render_number = 1000
    render_time = timeit.timeit(run_render, number=render_number)
    avg_render_ms = (render_time / render_number) * 1000.0

    # 2. Benchmark collection Diff calculations
    old_list = [{"id": f"id_{i}", "val": i} for i in range(100)]
    new_list = [{"id": f"id_{i}", "val": i} for i in range(100)]
    # Introduce updates, removals, additions, and moves to be highly realistic
    new_list[10]["val"] = 999
    new_list[20]["val"] = 888
    new_list.pop(30)
    new_list.insert(50, {"id": "added_1", "val": 1000})
    moved_item = new_list.pop(60)
    new_list.insert(10, moved_item)

    def run_diff():
        DiffEngine.diff_by(old_list, new_list, lambda x: x["id"])

    diff_number = 1000
    diff_time = timeit.timeit(run_diff, number=diff_number)
    avg_diff_ms = (diff_time / diff_number) * 1000.0

    return avg_render_ms, avg_diff_ms


def main() -> None:
    print("\n⚡ HICCL PERFORMANCE BENCHMARK SUITE ⚡")
    print("=" * 50)

    # 1. Signals
    sig_latency = benchmark_signals()
    status_sig = "🟢" if sig_latency < 0.1 else "🔴"
    print(
        f"{status_sig} Signal Propagation Latency: {sig_latency:.4f} ms (Target: <0.1 ms)"
    )

    # 2. Renders & Diffs
    render_latency, diff_latency = benchmark_diff_and_render()
    status_render = "🟢"
    status_diff = "🟢" if diff_latency < 1.0 else "🔴"

    print(f"{status_render} Component Render Latency   : {render_latency:.4f} ms")
    print(
        f"{status_diff} DOM Diff Latency          : {diff_latency:.4f} ms (Target: <1.0 ms)"
    )
    print("-" * 50)

    if sig_latency < 0.1 and diff_latency < 1.0:
        print("🚀 All latency performance targets are successfully met!\n")
    else:
        print("⚠️ Some performance targets exceeded threshold constraints.\n")


if __name__ == "__main__":
    main()
