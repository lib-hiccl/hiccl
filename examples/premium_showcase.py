"""Hiccl 尊享版全维度特性大秀 (Premium Showcase) 🧪🛡️

本示例高度整合并展示了 Hiccl 框架在 Phase 0, 1, 2 中交付的所有尖端全栈响应式能力：
1. [Phase 0] 细粒度反应式原子：Signal, ComputedSignal, Effect 以及批量事务 batch。
2. [Phase 0] 声明式富界面 Hiccup 渲染管线与 Alpine.js/DaisyUI 精美融合。
3. [Phase 1] 模块热重载与 hREPL 运行时状态内省调试（在注释中说明）。
4. [Phase 2] 自研 hiccl.spec 契约 DSL 对服务端 `@server` 方法边界的强约束。
5. [Phase 2] explain-data 报错内省可视化：当契约校验失败时，实时捕获并以极具视觉冲击力的红橘色渐变面板渲染结构化报错。
6. [Phase 2] EventBus 层级通配符广播订阅：展示类似 MQTT 规范的单层 '*' 与多层 '#' 通配事件路由。
7. [Phase 2] RedisSessionStore 悲观分布式锁与 Msgpack/Base64 二进制状态持久化。

运行方式:
    uv run python examples/premium_showcase.py
"""

from __future__ import annotations

from datetime import datetime

from hiccl import (
    Component,
    ComponentRegistry,
    HicclConfig,
    batch,
    component,
    computed,
    create_hiccl_app,
    effect,
    server,
    signal,
    spec,
    use_signal,
    reg_state,
    reg_sub,
    reg_event,
    subscribe,
    dispatch,
)
from hiccl.eventbus import event_bus
from hiccl.hiccup import (
    button,
    div,
    form,
    h1,
    h3,
    input_,
    li,
    p,
    raw,
    span,
    ul,
)
from hiccl.session_store import DummyRedisClient, RedisSessionStore
from hiccl.spec import SpecValidationError

# ---------------------------------------------------------------------------
# 1. 契约定义层 (Spec Contracts)
# ---------------------------------------------------------------------------

# 用户个人资料契约：约束 ID, 用户名, 邮箱格式, 年龄边界及角色列表
UserProfileSpec = spec.keys(
    req={
        "id": spec.integer(gt=0),
        "username": spec.string(min_len=3, max_len=20, pattern=r"^[a-zA-Z0-9_]+$"),
        "age": spec.integer(gte=18, lte=120),
    },
    opt={
        "email": spec.regex(r"^[^@]+@[^@]+\.[^@]+$"),
        "roles": spec.coll_of(spec.string(), min_len=1),
    },
)

# ---------------------------------------------------------------------------
# 2. 反应式大沙盒组件 (Reactive Sandbox - Phase 0 & 1 Showcase)
# ---------------------------------------------------------------------------


class ReactiveSandbox(Component):
    """反应式沙盒：展示 Signal、Computed 以及 batch() 批量更新与拓扑更新链。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.base_val = signal(5)
        # 派生状态 ComputedSignal
        self.squared = computed(lambda: self.base_val.get() ** 2)
        self.cubed = computed(lambda: self.base_val.get() ** 3)
        # 记录 Effect 执行次数与时间
        self.effect_runs = signal(0)
        self.last_run_time = signal("尚未运行")

    def mount(self) -> None:
        # 注册反应式副作用 Effect，在 base_val 变动时自动触发
        @effect
        def _():
            # 依赖追踪
            _ = self.base_val.get()
            # 更新执行指标
            self.effect_runs.set(self.effect_runs.get() + 1)
            self.last_run_time.set(datetime.now().strftime("%H:%M:%S.%f")[:-3])

    @server
    def step_up(self, step: int = 1) -> None:
        """单步递增。"""
        self.base_val.set(self.base_val.get() + int(step))

    @server
    def step_down(self, step: int = 1) -> None:
        """单步递减。"""
        self.base_val.set(self.base_val.get() - int(step))

    @server
    def run_batch_transaction(self) -> None:
        """展示 batch 事务：在 batch 块中多次修改信号，仅触发一次 Effect 重新计算。"""
        with batch():
            # 进行 3 次无谓的震荡修改
            self.base_val.set(10)
            self.base_val.set(20)
            self.base_val.set(8)  # 最终收敛于 8

    def render(self) -> list:
        return div(
            {
                "class": "card bg-base-200 border border-base-300 shadow-2xl p-6 flex flex-col gap-4"
            },
            div(
                {
                    "class": "flex justify-between items-center border-b border-base-300 pb-3"
                },
                h3(
                    {"class": "text-xl font-bold text-primary flex items-center gap-2"},
                    "⚡ 反应式大沙盒 (Reactive Sandbox)",
                ),
                span({"class": "badge badge-primary"}, "Phase 0 核心"),
            ),
            p(
                {"class": "text-sm text-base-content/70"},
                "在此体验细粒度反应式原子、派生计算链以及 batch 批处理事务：",
            ),
            div(
                {
                    "class": "grid grid-cols-1 md:grid-cols-3 gap-4 bg-base-300 p-4 rounded-2xl border border-base-200"
                },
                div(
                    {"class": "flex flex-col items-center justify-center p-2"},
                    span({"class": "text-xs opacity-50 mb-1"}, "基础信号 Base"),
                    span(
                        {"class": "text-3xl font-black text-white font-mono"},
                        self.base_val.get(),
                    ),
                ),
                div(
                    {
                        "class": "flex flex-col items-center justify-center p-2 border-y md:border-y-0 md:border-x border-base-200"
                    },
                    span({"class": "text-xs opacity-50 mb-1"}, "平方计算 Computed²"),
                    span(
                        {"class": "text-3xl font-black text-accent font-mono"},
                        self.squared.get(),
                    ),
                ),
                div(
                    {"class": "flex flex-col items-center justify-center p-2"},
                    span({"class": "text-xs opacity-50 mb-1"}, "立方计算 Computed³"),
                    span(
                        {"class": "text-3xl font-black text-secondary font-mono"},
                        self.cubed.get(),
                    ),
                ),
            ),
            div(
                {
                    "class": "flex justify-between items-center text-xs bg-base-300 p-3 rounded-xl border border-base-200 font-mono"
                },
                span(
                    {"class": "text-success"},
                    f"✔ Effect 自动监听执行: {self.effect_runs.get()} 次",
                ),
                span({"class": "opacity-50"}, f"最后触发: {self.last_run_time.get()}"),
            ),
            div(
                {"class": "card-actions justify-center gap-2 mt-2"},
                button(
                    {
                        "class": "btn btn-outline btn-sm btn-error",
                        "on_click": self.step_down(1),
                    },
                    "-1 递减",
                ),
                button(
                    {
                        "class": "btn btn-outline btn-sm btn-success",
                        "on_click": self.step_up(1),
                    },
                    "+1 递增",
                ),
                button(
                    {
                        "class": "btn btn-primary btn-sm btn-wide shadow-[0_0_15px_rgba(59,130,246,0.3)]",
                        "on_click": self.run_batch_transaction,
                    },
                    "运行 Batch 批处理事务 (收敛为 8)",
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 3. 带契约校验与报错自愈的可视化个人资料卡 (Profile Editor - Phase 2 Showcase)
# ---------------------------------------------------------------------------


class SpecProfileCard(Component):
    """带 Spec 契约校验的个人资料卡：

    展示 @server 方法边界对 UserProfileSpec 的极致验证，
    以及在界面上实时渲染出 explain-data 自愈报错面板的极致 DX。
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # 当前持久化的合法个人资料
        self.profile = signal(
            {"id": 1, "username": "admin", "age": 28, "email": "admin@hiccl.dev"}
        )
        # 校验错误信号：保存失败时的结构化 explain-data 列表
        self.validation_errors = signal([])
        # 操作状态提示
        self.status_msg = signal("")

    # 声明强类型契约校验约束 args 入参及 return 返回值
    @server(spec={"args": {"data": UserProfileSpec}, "return": spec.boolean()})
    def update_profile(self, data: dict) -> bool:
        """被 Spec 契约高度保卫的服务端方法。"""
        # 注意：此处参数在进入方法前已被 BoundAction 进行 Spec 强校验。
        # 如果不符合 Spec，会在入口处自动抛出 SpecValidationError 阻断执行。
        self.profile.set(data)
        return True

    @server
    def submit_form(self, id: str, username: str, age: str, email: str) -> None:
        """处理表单提交，在局部捕获 SpecValidationError 以进行前端的报错内省展示。"""
        try:
            # 数据类型清洗
            parsed_id = int(id) if id.isdigit() else -1
            parsed_age = int(age) if age.isdigit() else -1

            payload = {
                "id": parsed_id,
                "username": username,
                "age": parsed_age,
            }
            if email.strip():
                payload["email"] = email

            # 调用带 @server 契约强类型校验的方法
            self.update_profile(data=payload)

            # 校验成功：清除历史报错
            self.validation_errors.set([])
            self.status_msg.set(
                f"🎉 个人资料保存成功！更新时间: {datetime.now().strftime('%H:%M:%S')}"
            )
        except SpecValidationError as e:
            # 核心看点：提取高度结构化的 explain-data 报错，并在 UI 实时可视化！
            self.validation_errors.set(e.explain_data)
            self.status_msg.set("")
        except Exception as e:
            self.status_msg.set(f"❌ 系统发生其他错误: {e}")

    def render(self) -> list:
        prof = self.profile.get()
        errors = self.validation_errors.get()
        msg = self.status_msg.get()

        # 报错面板渲染
        error_panel = ""
        if errors:
            error_panel = div(
                {
                    "class": "alert alert-error bg-red-950/40 border border-red-500/30 text-red-200 p-4 rounded-2xl flex flex-col items-start gap-2 shadow-inner"
                },
                span(
                    {
                        "class": "font-extrabold text-sm flex items-center gap-2 text-red-400"
                    },
                    "⚠️ 发现 Spec 契约违规 (Explain-Data 内省):",
                ),
                ul(
                    {
                        "class": "list-disc pl-5 text-xs flex flex-col gap-1.5 font-mono text-red-300/90"
                    },
                    *[
                        li(
                            None,
                            span(
                                {"class": "text-red-400 font-bold"},
                                f"路径: {' -> '.join(map(str, err['path'])) or 'root'}",
                            ),
                            " | 违规输入: ",
                            span(
                                {"class": "bg-red-500/20 px-1 rounded text-white"},
                                repr(err["val"]),
                            ),
                            " | 未满足谓词: ",
                            span(
                                {"class": "badge badge-outline badge-sm badge-error"},
                                err["pred"],
                            ),
                        )
                        for err in errors
                    ],
                ),
            )

        success_panel = ""
        if msg:
            success_panel = div(
                {
                    "class": "alert alert-success bg-green-950/40 border border-green-500/30 text-green-200 p-3 rounded-xl text-xs"
                },
                msg,
            )

        return div(
            {
                "class": "card bg-base-200 border border-base-300 shadow-2xl p-6 flex flex-col gap-4"
            },
            div(
                {
                    "class": "flex justify-between items-center border-b border-base-300 pb-3"
                },
                h3(
                    {"class": "text-xl font-bold text-accent flex items-center gap-2"},
                    "🛡️ 契约安全边界 (Spec & @server)",
                ),
                span({"class": "badge badge-accent"}, "Phase 2 契约"),
            ),
            p(
                {"class": "text-sm text-base-content/70"},
                "本组件由 `UserProfileSpec` 守卫，输入不合规的数据会被契约直接拦截：",
            ),
            # 当前持久化资料面板
            div(
                {
                    "class": "bg-base-300/50 p-4 rounded-xl border border-base-200 text-xs grid grid-cols-2 gap-2 font-mono"
                },
                div(None, span({"class": "opacity-50"}, "ID: "), prof.get("id")),
                div(
                    None,
                    span({"class": "opacity-50"}, "用户姓名: "),
                    prof.get("username"),
                ),
                div(
                    None,
                    span({"class": "opacity-50"}, "年龄: "),
                    f"{prof.get('age')} 岁",
                ),
                div(
                    None,
                    span({"class": "opacity-50"}, "电子邮箱: "),
                    prof.get("email", "未提供"),
                ),
            ),
            # 契约校验提示面板
            error_panel,
            success_panel,
            # 表单提交
            form(
                {"class": "flex flex-col gap-3", "on_submit": self.submit_form},
                div(
                    {"class": "grid grid-cols-2 gap-2"},
                    input_(
                        {
                            "type": "text",
                            "name": "id",
                            "value": str(prof.get("id")),
                            "class": "input input-bordered input-sm",
                            "placeholder": "ID (需 >0)",
                        }
                    ),
                    input_(
                        {
                            "type": "text",
                            "name": "username",
                            "value": prof.get("username"),
                            "class": "input input-bordered input-sm",
                            "placeholder": "姓名 (字母/数字/下划线, >=3)",
                        }
                    ),
                ),
                div(
                    {"class": "grid grid-cols-2 gap-2"},
                    input_(
                        {
                            "type": "text",
                            "name": "age",
                            "value": str(prof.get("age")),
                            "class": "input input-bordered input-sm",
                            "placeholder": "年龄 (需 18~120)",
                        }
                    ),
                    input_(
                        {
                            "type": "text",
                            "name": "email",
                            "value": prof.get("email", ""),
                            "class": "input input-bordered input-sm",
                            "placeholder": "邮箱 (正则格式校验)",
                        }
                    ),
                ),
                button(
                    {
                        "type": "submit",
                        "class": "btn btn-accent btn-sm shadow-[0_0_15px_rgba(16,185,129,0.2)]",
                    },
                    "💾 提交修改 (自动触发 @server 契约校验)",
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 4. 通配符广播中心组件 (Wildcard Event Hub - Phase 2 Showcase)
# ---------------------------------------------------------------------------


class WildcardEventHub(Component):
    """通配符广播中心：展现 EventBus 高性能通配符层级订阅 matching。

    允许用户订阅单层（sport.*）或多层（sport.#）通配，并发布主题以观察匹配情况。
    """

    # 告知当前组件需要订阅的主题 (演示层次通配符)
    topics = ["sport.*", "sport.#", "chat.room1"]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # 分别存储各个队列接收到的消息日志
        self.star_logs = signal([])
        self.hash_logs = signal([])
        self.exact_logs = signal([])

    def on_broadcast(self, topic: str) -> None:
        """EventBus 广播到达时回调。"""
        # 注意：此处由 EventBus 匹配 match_topic 成功后，自动根据组件的 topics 进行广播投递
        t_str = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{t_str}] 主题 '{topic}' 推送成功！"

        # 精准路由到 UI 的不同展示列表
        # 1. 匹配 sport.* (星号通配)
        from hiccl.eventbus import match_topic

        if match_topic("sport.*", topic):
            self.star_logs.set([log_entry] + self.star_logs.get()[:4])

        # 2. 匹配 sport.# (井号多层通配)
        if match_topic("sport.#", topic):
            self.hash_logs.set([log_entry] + self.hash_logs.get()[:4])

        # 3. 匹配精确订阅 chat.room1
        if match_topic("chat.room1", topic):
            self.exact_logs.set([log_entry] + self.exact_logs.get()[:4])

    @server
    def publish_event(self, topic: str) -> None:
        """发布具体主题事件到全局总线。"""
        if not topic.strip():
            return
        # 广播到 EventBus，EventBus 会自动检测匹配所有的通配符订阅者
        event_bus.publish_sync(topic, data=None)

    def render(self) -> list:
        stars = self.star_logs.get()
        hashes = self.hash_logs.get()
        exacts = self.exact_logs.get()

        return div(
            {
                "class": "card bg-base-200 border border-base-300 shadow-2xl p-6 flex flex-col gap-4 col-span-1 md:col-span-2"
            },
            div(
                {
                    "class": "flex justify-between items-center border-b border-base-300 pb-3"
                },
                h3(
                    {
                        "class": "text-xl font-bold text-secondary flex items-center gap-2"
                    },
                    "🔀 层级通配符总线 (Wildcard EventBus)",
                ),
                span({"class": "badge badge-secondary"}, "Phase 2 广播"),
            ),
            p(
                {"class": "text-sm text-base-content/70"},
                "Hiccl EventBus 完美遵循工业级通配层级：可以使用 `.` 做分隔符，`*` 匹配单层，`#` 匹配多层。体验下面的广播匹配路由：",
            ),
            # 发布控制台
            div(
                {
                    "class": "flex flex-col gap-2 bg-base-300 p-4 rounded-xl border border-base-200"
                },
                span(
                    {"class": "text-xs font-bold opacity-60"},
                    "🚀 事件控制台 (发布广播)：",
                ),
                div(
                    {"class": "flex flex-wrap gap-2"},
                    button(
                        {
                            "class": "btn btn-outline btn-xs btn-primary",
                            "on_click": self.publish_event("sport.basketball"),
                        },
                        "发送到 'sport.basketball' (匹配 * 与 #)",
                    ),
                    button(
                        {
                            "class": "btn btn-outline btn-xs btn-primary",
                            "on_click": self.publish_event("sport.football.match1"),
                        },
                        "发送到 'sport.football.match1' (仅匹配 #)",
                    ),
                    button(
                        {
                            "class": "btn btn-outline btn-xs btn-primary",
                            "on_click": self.publish_event("sport"),
                        },
                        "发送到 'sport' (匹配 # 的 0 层匹配)",
                    ),
                    button(
                        {
                            "class": "btn btn-outline btn-xs btn-secondary",
                            "on_click": self.publish_event("chat.room1"),
                        },
                        "发送到 'chat.room1' (精准匹配)",
                    ),
                ),
            ),
            # 三个订阅者展示箱
            div(
                {"class": "grid grid-cols-1 md:grid-cols-3 gap-4 mt-2"},
                # 订阅箱 1：sport.*
                div(
                    {
                        "class": "bg-base-300/60 p-3 rounded-xl border border-base-200 flex flex-col gap-2 min-h-36"
                    },
                    span(
                        {"class": "text-xs font-bold text-primary"},
                        "📡 订阅: 'sport.*' (单层通配)",
                    ),
                    ul(
                        {
                            "class": "text-[10px] opacity-80 font-mono flex flex-col gap-1"
                        },
                        *[li(None, log) for log in stars],
                    )
                    if stars
                    else p(
                        {"class": "text-[10px] opacity-40 italic mt-4 text-center"},
                        "暂无匹配消息",
                    ),
                ),
                # 订阅箱 2：sport.#
                div(
                    {
                        "class": "bg-base-300/60 p-3 rounded-xl border border-base-200 flex flex-col gap-2 min-h-36"
                    },
                    span(
                        {"class": "text-xs font-bold text-accent"},
                        "📡 订阅: 'sport.#' (任意多层通配)",
                    ),
                    ul(
                        {
                            "class": "text-[10px] opacity-80 font-mono flex flex-col gap-1"
                        },
                        *[li(None, log) for log in hashes],
                    )
                    if hashes
                    else p(
                        {"class": "text-[10px] opacity-40 italic mt-4 text-center"},
                        "暂无匹配消息",
                    ),
                ),
                # 订阅箱 3：chat.room1
                div(
                    {
                        "class": "bg-base-300/60 p-3 rounded-xl border border-base-200 flex flex-col gap-2 min-h-36"
                    },
                    span(
                        {"class": "text-xs font-bold text-secondary"},
                        "🎯 订阅: 'chat.room1' (精准接收)",
                    ),
                    ul(
                        {
                            "class": "text-[10px] opacity-80 font-mono flex flex-col gap-1"
                        },
                        *[li(None, log) for log in exacts],
                    )
                    if exacts
                    else p(
                        {"class": "text-[10px] opacity-40 italic mt-4 text-center"},
                        "暂无匹配消息",
                    ),
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 5. Phase 3 纯函数组件与 re-frame 单向数据流演示 (Reagent & re-frame Showcase)
# ---------------------------------------------------------------------------

# 注册 re-frame 初始状态
reg_state(
    {
        "todos": [
            {"id": 1, "text": "体验 Phase 0-2 的极速反应式与契约", "done": True},
            {"id": 2, "text": "体验 Phase 3 纯函数组件与单向数据流", "done": False},
        ]
    }
)


# 注册派生数据订阅
@reg_sub("todo-list")
def sub_todo_list(db):
    return db.get("todos", [])


@reg_sub("todo-count")
def sub_todo_count(db):
    todos = db.get("todos", [])
    total = len(todos)
    done = sum(1 for t in todos if t.get("done"))
    return total, done


# 注册带 Spec 契约的事件处理器！
TodoTextSpec = spec.string(
    min_len=2, max_len=30, pattern=r"^[a-zA-Z0-9_\u4e00-\u9fa5\s\?\!\.,\-\(\)]+$"
)


@reg_event("add-todo-item", spec={"args": [TodoTextSpec]})
def event_add_todo(db, text: str):
    todos = db.get("todos", [])
    new_id = max((t["id"] for t in todos), default=0) + 1
    new_todo = {"id": new_id, "text": text, "done": False}
    return {**db, "todos": todos + [new_todo]}


@reg_event("toggle-todo-item")
def event_toggle_todo(db, todo_id: int):
    if isinstance(todo_id, str):
        todo_id = int(todo_id)
    todos = db.get("todos", [])
    new_todos = []
    for t in todos:
        if t["id"] == todo_id:
            new_todos.append({**t, "done": not t["done"]})
        else:
            new_todos.append(t)
    return {**db, "todos": new_todos}


@component("reframe-todo-demo")
def ReframeTodoDemo():
    """纯函数组件：使用 use_signal、subscribe 和 dispatch 构建优雅的 Todo 卡片。"""
    # 局部 UI 状态
    input_text = use_signal("")
    spec_error = use_signal("")
    prev_total = use_signal(0)

    # 订阅全局状态
    todos = subscribe("todo-list")
    total, done = subscribe("todo-count").get()

    # 自愈捕获与 typed input 状态保留
    from hiccl.component import _current_rendering_component

    comp = _current_rendering_component.get()
    submitted = getattr(comp, "_submitted_values", {})
    if "todo_text" in submitted:
        input_text.set(submitted["todo_text"])
        del submitted["todo_text"]

    err_msg = getattr(comp, "_last_spec_error", None) or ""

    # 任务成功添加或减少后的清理状态机
    if total > prev_total.get():
        input_text.set("")
        spec_error.set("")
        prev_total.set(total)
    elif total < prev_total.get():
        prev_total.set(total)

    # 首次载入初始化 prev_total 避免误触清空逻辑
    if prev_total.get() == 0 and total > 0:
        prev_total.set(total)

    return div(
        {
            "class": "card bg-base-200 border border-base-300 shadow-2xl p-6 flex flex-col gap-4"
        },
        div(
            {
                "class": "flex flex-wrap justify-between items-center gap-2 border-b border-base-300 pb-3"
            },
            h3(
                {
                    "class": "text-lg md:text-xl font-bold text-success flex items-center gap-2"
                },
                "🎯 反应式纯函数式 Todo 大秀",
            ),
            span({"class": "badge badge-success"}, "Phase 3 函数式"),
        ),
        p(
            {"class": "text-sm text-base-content/70"},
            "这是纯函数式反应式大秀。局部状态由 `use_signal()` 闭包捕获，数据源全量由 `subscribe` 驱动，事件由 `dispatch` 强一致单向更新：",
        ),
        # 统计数据条
        div(
            {
                "class": "flex gap-4 bg-base-300 p-3 rounded-xl border border-base-200 justify-around text-center text-xs font-semibold font-mono"
            },
            div(
                None,
                span({"class": "opacity-50"}, "总任务数: "),
                span({"class": "text-primary font-bold"}, total),
            ),
            div(
                None,
                span({"class": "opacity-50"}, "已完成: "),
                span({"class": "text-success font-bold"}, done),
            ),
            div(
                None,
                span({"class": "opacity-50"}, "待处理: "),
                span({"class": "text-warning font-bold"}, total - done),
            ),
        ),
        # 错误提示
        div(
            {
                "class": "alert alert-error bg-red-950/40 border border-red-500/30 text-red-200 text-xs p-2 rounded-lg"
            },
            f"⚠️ 未满足契约: {err_msg}",
        )
        if err_msg
        else "",
        # 列表项
        ul(
            {"class": "flex flex-col gap-2"},
            *[
                li(
                    {
                        "class": "flex justify-between items-center bg-base-300 p-3 rounded-lg border border-base-200 text-sm font-semibold"
                    },
                    span(
                        {
                            "class": f"{'line-through opacity-40 text-success' if item['done'] else 'text-white'}"
                        },
                        item["text"],
                    ),
                    button(
                        {
                            "class": f"btn btn-xs {'btn-success' if item['done'] else 'btn-outline btn-warning'}",
                            # 客户端点击：通过 dispatch 绑定事件，直接触发服务端事件处理器！
                            "on_click": dispatch("toggle-todo-item", item["id"]),
                        },
                        "✓ 已完成" if item["done"] else "标记完成",
                    ),
                )
                for item in todos.get()
            ],
        ),
        # 新增表单
        form(
            {
                "class": "join mt-2 w-full",
                "on_submit": dispatch("add-todo-item"),
            },
            input_(
                {
                    "type": "text",
                    "name": "todo_text",
                    "class": "input input-bordered input-sm join-item flex-1",
                    "placeholder": "新增任务 (需 2~30 字，自动触发 Spec 强检验)",
                    "value": input_text.get(),
                }
            ),
            button(
                {
                    "class": "btn btn-success btn-sm join-item",
                    "type": "submit",
                },
                "➕ 添加",
            ),
        ),
    )


# ---------------------------------------------------------------------------
# 6. 联合大秀主面板 (Main Showcase Frame)
# ---------------------------------------------------------------------------


class PremiumShowcaseFrame(Component):
    """联合大秀的主页面布局。包含 RedisSessionStore 和 hREPL 的状态内省指示器。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.redis_status = signal("检测中...")
        self.lock_status = signal("非活跃")
        self.sandbox_comp = None
        self.profile_comp = None
        self.event_comp = None
        self.reframe_comp = None

    def mount(self) -> None:
        # 在活动 Session 中挂载并装配子组件
        self.sandbox_comp = self._session.mount_component(
            "reactive-sandbox", cid="sandbox-main"
        )
        self.profile_comp = self._session.mount_component(
            "spec-profile-card", cid="profile-main"
        )
        self.event_comp = self._session.mount_component(
            "wildcard-event-hub", cid="event-main"
        )
        self.reframe_comp = self._session.mount_component(
            "reframe-todo-demo", cid="reframe-main"
        )

        # 检测存储引擎状态
        store = self._session._store
        if isinstance(store, RedisSessionStore):
            if isinstance(store._redis, DummyRedisClient):
                self.redis_status.set("已启用 (自动降级至 Memory 引擎)")
            else:
                self.redis_status.set("已连接 (连接池池化 & 原生指数退避重试)")
        else:
            self.redis_status.set("内存默认 MemoryStore")

    def render(self) -> list:
        sb_html = self._session.renderer.render_component(self.sandbox_comp)
        pf_html = self._session.renderer.render_component(self.profile_comp)
        ev_html = self._session.renderer.render_component(self.event_comp)
        rf_html = self._session.renderer.render_component(self.reframe_comp)

        return div(
            {"class": "flex flex-col gap-6 w-full max-w-6xl mx-auto px-4"},
            # 头部玻璃渐变横幅
            div(
                {
                    "class": "bg-gradient-to-r from-primary/20 via-accent/10 to-secondary/20 p-8 rounded-3xl border border-base-200/50 shadow-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
                },
                div(
                    None,
                    h1(
                        {
                            "class": "text-3xl font-extrabold text-white tracking-tight flex items-center gap-3"
                        },
                        "🧪 Hiccl Premium Showcase",
                    ),
                    p(
                        {"class": "text-sm text-base-content/60 mt-1 max-w-xl"},
                        "Python 中的 Clojure 哲学全栈全自愈反应式框架。本示例已深度打通并高亮展现了 Phase 0、1、2、3 所有革命性特性！",
                    ),
                ),
                div(
                    {
                        "class": "flex flex-col gap-2 font-mono text-[10px] bg-base-300/80 p-3 rounded-2xl border border-base-200 min-w-56"
                    },
                    div(
                        None,
                        span({"class": "opacity-50"}, "🗄️ 存储: "),
                        self.redis_status.get(),
                    ),
                    div(
                        None,
                        span({"class": "opacity-50"}, "🔐 悲观锁: "),
                        "Redis Distributed Lock",
                    ),
                    div(
                        None,
                        span({"class": "opacity-50"}, "🔌 hREPL: "),
                        "HREPL_ENABLED=true (Port 8998)",
                    ),
                ),
            ),
            # 中间两列主体组件大秀
            div(
                {"class": "grid grid-cols-1 md:grid-cols-2 gap-6"},
                raw(sb_html),
                raw(pf_html),
            ),
            # 底部 re-frame 大秀与事件总线大秀 (双列宽)
            div(
                {"class": "grid grid-cols-1 md:grid-cols-2 gap-6"},
                raw(rf_html),
                raw(ev_html),
            ),
        )


# ---------------------------------------------------------------------------
# 7. 应用引导配置与启动 (FastAPI Launch)
# ---------------------------------------------------------------------------

# 实例化全局组件注册表
registry = ComponentRegistry()
# 注册所有的演示组件
registry.register("reactive-sandbox", ReactiveSandbox)
registry.register("spec-profile-card", SpecProfileCard)
registry.register("wildcard-event-hub", WildcardEventHub)
registry.register("reframe-todo-demo", ReframeTodoDemo)
registry.register("premium-showcase-frame", PremiumShowcaseFrame)

# 配置 RedisSessionStore (含 Msgpack & 连接池加固)
# 本处为确保零配置开箱即用，会探测本地 Redis，若无则自动优雅降级至 Dummy
redis_store = RedisSessionStore(redis_url="redis://localhost:6379")
redis_store.registry = registry

config = HicclConfig(
    component_registry=registry,
    session_store=redis_store,
    transport_modes={"http", "ws", "sse"},
    pages={"/": PremiumShowcaseFrame},
    brand_name="Hiccl Premium Showcase",
    title="Hiccl Premium Showcase — Phase 0-3 联合大秀",
    theme="night",
    show_navbar=False,  # 隐藏默认导航，使用我们定制的豪华大横幅
)

app = create_hiccl_app(config)

if __name__ == "__main__":
    import uvicorn

    print("======================================================================")
    print("🚀 Hiccl Premium Showcase 正在启动...")
    print("👉 浏览器访问: http://127.0.0.1:8000")
    print("📡 hREPL 交互式内省端口: 8998 (HREPL_ENABLED=true)")
    print("======================================================================")

    # 启用 HMR 及 hREPL 环境变量，以便同步展示 Phase 1 的开发反馈体验
    import os

    os.environ["HICCL_LIVE_RELOAD"] = "1"
    os.environ["HREPL_ENABLED"] = "true"

    uvicorn.run(app, host="127.0.0.1", port=8000)
