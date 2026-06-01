"""Hiccl Phase 5a — 状态快照与时间旅行尊享版演示沙盒 🧪🕰️

本示例展示了：
1. 底层 HistorySignal 不可变快照管理（计数器与调色盘）。
2. 全局 re-frame DB 自动升级为 HistorySignal 后的全局时间旅行（Todo 任务列表）。
3. 内建的半透明磨砂玻璃（Glassmorphism）时间旅行悬浮调试面板的交互体验。

运行方式:
    uv run python examples/time_travel_demo.py
"""

from __future__ import annotations

import os
from hiccl import (
    Component,
    ComponentRegistry,
    set_registry,
    HicclConfig,
    create_hiccl_app,
    signal_with_history,
    component,
    server,
    reg_state,
    reg_sub,
    reg_event,
    subscribe,
    dispatch,
)

# Initialize global registry so that @component decorators register automatically
registry = ComponentRegistry()
set_registry(registry)
from hiccl.hiccup import (
    div,
    h1,
    h3,
    p,
    span,
    button,
    input_,
    form,
    li,
    ul,
    raw,
)

# ---------------------------------------------------------------------------
# 1. 全局 re-frame DB 状态与事件设计 (全局 DB 自动升级为 HistorySignal)
# ---------------------------------------------------------------------------

reg_state(
    {
        "tasks": [
            {"id": 1, "text": "点击右下角时钟打开调试面板", "done": False},
            {"id": 2, "text": "体验局部 HistorySignal 撤销重做", "done": False},
            {"id": 3, "text": "拖动滑块体验极速时间穿梭", "done": False},
        ]
    }
)


@reg_sub("tasks-list")
def sub_tasks_list(db):
    return db.get("tasks", [])


@reg_sub("tasks-progress")
def sub_tasks_progress(db):
    tasks = db.get("tasks", [])
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("done"))
    return total, done


@reg_event("add-task")
def event_add_task(db, text: str):
    if not text.strip():
        return db
    tasks = db.get("tasks", [])
    new_id = max((t["id"] for t in tasks), default=0) + 1
    new_task = {"id": new_id, "text": text, "done": False}
    return {**db, "tasks": tasks + [new_task]}


@reg_event("toggle-task")
def event_toggle_task(db, task_id: int):
    tasks = db.get("tasks", [])
    new_tasks = []
    for t in tasks:
        if t["id"] == task_id:
            new_tasks.append({**t, "done": not t["done"]})
        else:
            new_tasks.append(t)
    return {**db, "tasks": new_tasks}


# ---------------------------------------------------------------------------
# 2. 局部 HistorySignal 模块：高级计数器 (Counter Component)
# ---------------------------------------------------------------------------


@component("counter-box")
class CounterBox(Component):
    """有状态局部组件：持有 count 这个 HistorySignal。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # 创建一个支持历史记录的局部信号
        self.count = signal_with_history(10, max_snapshots=20)

    @server
    def step_up(self) -> None:
        self.count.set(self.count.get() + 1)

    @server
    def step_down(self) -> None:
        self.count.set(self.count.get() - 1)

    @server
    def multiply_two(self) -> None:
        self.count.set(self.count.get() * 2)

    def render(self) -> list:
        val = self.count.get()
        return div(
            {
                "class": "card bg-neutral border border-white/10 shadow-2xl p-6 flex flex-col gap-4 text-neutral-content rounded-2xl backdrop-blur-md bg-opacity-40"
            },
            div(
                {"class": "flex justify-between items-center"},
                h3({"class": "text-lg font-bold text-primary"}, "🔢 高级反应式计数器"),
                span(
                    {"class": "badge bg-primary/20 text-primary border-none text-xs"},
                    "局部 HistorySignal",
                ),
            ),
            p(
                {"class": "text-xs text-base-content/70"},
                "此组件的值完全由 HistorySignal 托管。每一次计算操作都会在历史链表中保存一个快照：",
            ),
            div(
                {
                    "class": "flex flex-col items-center justify-center bg-black/35 py-6 rounded-xl border border-white/5"
                },
                span({"class": "text-xs opacity-50 mb-1 font-mono"}, "当前数值 (Count)"),
                span(
                    {"class": "text-5xl font-black text-white font-mono tracking-tight animate-pulse"},
                    str(val),
                ),
            ),
            div(
                {"class": "flex justify-center gap-2 mt-2"},
                button(
                    {
                        "class": "btn btn-outline btn-sm btn-error flex-1 font-bold",
                        "on_click": self.step_down,
                    },
                    "-1 递减",
                ),
                button(
                    {
                        "class": "btn btn-outline btn-sm btn-success flex-1 font-bold",
                        "on_click": self.step_up,
                    },
                    "+1 递增",
                ),
                button(
                    {
                        "class": "btn btn-primary btn-sm flex-1 font-bold shadow-[0_0_10px_rgba(59,130,246,0.3)]",
                        "on_click": self.multiply_two,
                    },
                    "×2 翻倍",
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 3. 局部 HistorySignal 模块：互动调色盘 (Canvas Component)
# ---------------------------------------------------------------------------


@component("color-canvas")
class ColorCanvas(Component):
    """有状态局部组件：持有 color 这个 HistorySignal。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # 默认使用 Indigo 靛蓝色，并支持最多 15 次历史追踪
        self.color = signal_with_history("#6366f1", max_snapshots=15)

    @server
    def change_color(self, hex_val: str) -> None:
        self.color.set(hex_val)

    def render(self) -> list:
        curr_color = self.color.get()

        # 调色盘的可选颜色
        colors = [
            ("#6366f1", "bg-indigo-500", "靛蓝"),
            ("#10b981", "bg-emerald-500", "祖母绿"),
            ("#f43f5e", "bg-rose-500", "玫瑰红"),
            ("#f59e0b", "bg-amber-500", "琥珀黄"),
            ("#8b5cf6", "bg-violet-500", "紫罗兰"),
            ("#ec4899", "bg-pink-500", "樱花粉"),
        ]

        color_balls = []
        for hex_code, bg_class, name in colors:
            is_active = curr_color.lower() == hex_code.lower()
            color_balls.append(
                button(
                    {
                        "class": f"w-8 h-8 rounded-full {bg_class} hover:scale-125 hover:shadow-lg transition-all duration-200 border-2 { 'border-white scale-110 shadow-md shadow-white/30' if is_active else 'border-transparent' }",
                        "on_click": self.change_color(hex_val=hex_code),
                        "title": name,
                    },
                    "",
                )
            )

        return div(
            {
                "class": "card bg-neutral border border-white/10 shadow-2xl p-6 flex flex-col gap-4 text-neutral-content rounded-2xl backdrop-blur-md bg-opacity-40"
            },
            div(
                {"class": "flex justify-between items-center"},
                h3({"class": "text-lg font-bold text-accent"}, "🎨 互动调色盘画布"),
                span(
                    {"class": "badge bg-accent/20 text-accent border-none text-xs"},
                    "局部 HistorySignal",
                ),
            ),
            p(
                {"class": "text-xs text-base-content/70"},
                "点击彩色小圆球更改画布背景色。当使用右下角的时间调试面板回溯时，画布色彩将秒级闪回：",
            ),
            # 颜色画布预览区域
            div(
                {
                    "class": "h-28 rounded-xl flex items-center justify-center font-bold text-sm tracking-widest text-white shadow-inner border border-white/5 transition-all duration-500",
                    "style": f"background-color: {curr_color}; text-shadow: 0 2px 4px rgba(0,0,0,0.5);",
                },
                f"当前色彩: {curr_color.upper()}",
            ),
            # 色彩选择栏
            div(
                {"class": "flex justify-around items-center bg-black/20 py-2.5 px-1 rounded-xl border border-white/5"},
                *color_balls,
            ),
        )


# ---------------------------------------------------------------------------
# 4. 全局 re-frame 模块：时间旅行任务清单 (Todo Component)
# ---------------------------------------------------------------------------


@component("time-travel-todo")
def TimeTravelTodo():
    """纯函数组件：订阅全局 re-frame DB，展示在全局 DB 下的时间穿梭。"""
    tasks = subscribe("tasks-list")
    total, done = subscribe("tasks-progress").get()

    # 处理表单提交的动作
    add_ref = dispatch("add-task")

    return div(
        {
            "class": "card bg-neutral border border-white/10 shadow-2xl p-6 flex flex-col gap-4 text-neutral-content rounded-2xl backdrop-blur-md bg-opacity-40 col-span-1 md:col-span-2"
        },
        div(
            {"class": "flex justify-between items-center border-b border-white/5 pb-2"},
            h3(
                {"class": "text-lg font-bold text-success flex items-center gap-2"},
                "📋 时间旅行任务清单",
            ),
            span(
                {"class": "badge bg-success/20 text-success border-none text-xs"},
                "全局 re-frame DB",
            ),
        ),
        p(
            {"class": "text-xs text-base-content/70"},
            "全局 re-frame DB 已默认升级为 HistorySignal。此处添加或勾选任务后，可在右下角的『全局 re-frame DB』中拖拽穿梭整个状态树：",
        ),
        # 统计进度
        div(
            {
                "class": "flex justify-around text-center py-2.5 bg-black/25 rounded-xl border border-white/5 text-xs font-mono font-bold"
            },
            div(None, span({"class": "opacity-50"}, "总事件数: "), total),
            div(None, span({"class": "opacity-50 text-success"}, "已完成: "), done),
            div(None, span({"class": "opacity-50 text-warning"}, "待完成: "), total - done),
        ),
        # 任务列表渲染
        ul(
            {"class": "flex flex-col gap-2 max-h-60 overflow-y-auto pr-1"},
            *[
                li(
                    {
                        "class": "flex justify-between items-center bg-black/15 hover:bg-black/25 p-3 rounded-lg border border-white/5 text-xs font-medium transition-colors"
                    },
                    span(
                        {
                            "class": f"{'line-through opacity-45 text-success' if t['done'] else 'text-white'}"
                        },
                        t["text"],
                    ),
                    button(
                        {
                            "class": f"btn btn-xs {'btn-success' if t['done'] else 'btn-outline btn-warning'}",
                            "on_click": dispatch("toggle-task", t["id"]),
                        },
                        "✓" if t["done"] else "待办",
                    ),
                )
                for t in tasks.get()
            ],
        ),
        # 添加表单
        form(
            {
                "class": "join w-full mt-2 border border-white/10 rounded-xl overflow-hidden",
                "on_submit": add_ref,
            },
            input_(
                {
                    "type": "text",
                    "name": "text",
                    "class": "input input-bordered input-sm join-item bg-black/10 flex-1 text-xs focus:outline-none",
                    "placeholder": "写个新的调试任务，按 Enter 添加...",
                }
            ),
            button(
                {"type": "submit", "class": "btn btn-success btn-sm join-item font-bold"},
                "添加",
            ),
        ),
    )


# ---------------------------------------------------------------------------
# 5. 主页面组件与入口配置 (Main Sandbox Page)
# ---------------------------------------------------------------------------


@component("time-travel-sandbox")
class TimeTravelSandbox(Component):
    """主大厅组件：承载计数器、画布与任务看板，创造震撼的互动沙盒。"""

    def render(self) -> list:
        renderer = self._session.renderer

        counter_comp = self._session.get_component("counter-box-main")
        if counter_comp is None:
            counter_comp = self._session.mount_component("counter-box", cid="counter-box-main")

        color_comp = self._session.get_component("color-canvas-main")
        if color_comp is None:
            color_comp = self._session.mount_component("color-canvas", cid="color-canvas-main")

        todo_comp = self._session.get_component("todo-main")
        if todo_comp is None:
            todo_comp = self._session.mount_component("time-travel-todo", cid="todo-main")

        return div(
            {"class": "flex flex-col gap-6 w-full"},
            # 顶部 Slogan 说明
            div(
                {"class": "text-center flex flex-col gap-2 max-w-xl mx-auto mb-2"},
                raw(
                    '<div class="w-16 h-16 mx-auto bg-gradient-to-tr from-accent via-primary to-secondary rounded-2xl flex items-center justify-center shadow-xl shadow-primary/20 mb-2 animate-pulse"><svg xmlns="http://www.w3.org/2000/svg" class="h-9 w-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg></div>'
                ),
                h1(
                    {
                        "class": "text-3xl font-extrabold tracking-tight bg-gradient-to-r from-accent via-primary to-secondary bg-clip-text text-transparent"
                    },
                    "Hiccl 反应式时间旅行沙盒",
                ),
                p(
                    {"class": "text-xs text-base-content/60 leading-relaxed font-medium"},
                    "Clojure 撤销重做哲学在 Python 全栈反应式生态下的惊艳落地。操作下方任何卡片，随后使用右下角的「时间调试器面板」滑块，即可瞬间在历史状态中穿梭！",
                ),
            ),
            # 三大卡片网格布局
            div(
                {"class": "grid grid-cols-1 md:grid-cols-2 gap-6 w-full items-start"},
                # 模块一：计数器
                raw(renderer.render_component(counter_comp)),
                # 模块二：画布
                raw(renderer.render_component(color_comp)),
                # 模块三：Todo 任务清单 (跨两列显示，在 render_component 里由 DaisyUI 支持)
                div(
                    {"class": "col-span-1 md:col-span-2 w-full"},
                    raw(renderer.render_component(todo_comp)),
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 6. APP 启动引导
# ---------------------------------------------------------------------------

# 配置应用环境，强力开启 live_reload (HMR 与内建时间旅行调试器面板)
config = HicclConfig(
    component_registry=registry,
    title="Hiccl 🧬 时间旅行调试沙盒",
    brand_name="Hiccl TimeTravel Sandbox",
    theme="dark",
    live_reload=True,  # 开启开发热重载，会自动在前端注入并挂载 TimeTravelPanel 组件
    pages={"/": TimeTravelSandbox},
)

app = create_hiccl_app(config)

if __name__ == "__main__":
    import uvicorn

    print("🧬 Hiccl TimeTravel Sandbox is starting...")
    print("⚡ Open http://127.0.0.1:8000 in your browser to experience time travel!")
    uvicorn.run(app, host="127.0.0.1", port=8001)
