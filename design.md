# Volt — Python Reactive Multi-Tier Web Framework

> 基于 Hiccup 风格 DSL + FastAPI 的轻量级反应式 Web 框架

**定位：** 一个**独立的 Python 库**，开发者可通过 `uv add volt` 直接引入依赖。受 Hyperfiddle Electric 启发，Volt 将服务端反应式信号图与 htmx 结合，实现高效的增量 DOM 更新——在不依赖编译器或宏系统的情况下达成"单一程序、分割执行"范式。

**核心价值：** 用纯 Python 的 Hiccup 风格 DSL 编写 UI 组件，自动追踪数据变更、增量推送 HTML diff，无需编写任何客户端 JavaScript。

**技术栈：** Python 3.10+, FastAPI (ASGI), Hiccup DSL（纯 Python 数据结构，零额外依赖）, htmx + hyperscript（客户端）, WebSocket/SSE（via FastAPI/Starlette）。

---

## Part 1：设计文档

### 1.1 动机与背景

**什么是 Electric Clojure？**

Electric Clojure（hyperfiddle/electric）是一种消除传统前后端边界的 Web 反应式编程语言：

- 在单个 `.cljc` 文件中编写**一个程序**
- **编译器**静态分析数据流，通过 `e/client` / `e/server` 将代码拆分为客户端/服务端两部分
- 运行时通过 **WebSocket** 使用自定义的**差分数据流协议**通信——只发送变更（diff），而非完整快照
- **增量序列引擎**（incseq）计算集合的 diff，实现高效 DOM 修补
- **DOM 集成**直接修补真实 DOM（无虚拟 DOM），通过 incseq diff 翻译为最小化的增/删/替换操作

**为什么需要 Python 版本？**

Electric 的核心洞见—*写一个程序，让系统处理网络边界*—强大但严重依赖 Clojure 的宏系统和 JVM/CLJS 生态。Python 开发者需要一个更易到达的路径实现相同目标：

- **统一的思维模型**：服务端 + 客户端逻辑在一个代码库中
- **反应式数据流**：自动传播变更，无需手动更新 UI
- **增量更新**：最小化网络流量和 DOM 抖动
- **无需构建步骤**：htmx 替代了客户端编译链
- **零 JS 编写**：所有交互逻辑通过 Python + htmx 属性声明式表达

### 1.2 关键设计决策

| 决策 | Electric 的方式 | Volt 的方式 | 理由 |
|---|---|---|---|
| 代码拆分 | 编译器宏（`e/client`, `e/server`） | 装饰器注解 + Python 函数作用域 | Python 无宏；装饰器是 Pythonic 的选择 |
| 客户端运行时 | ClojureScript + 自定义 DOM 协议 | htmx + hyperscript | 无构建步骤、经过验证、体积小 |
| 数据同步 | 基于 WebSocket 的自定义二进制协议 | 基于 WebSocket/SSE 的 JSON diff + htmx OOB swap | 更简单、可调试，htmx 原生处理 DOM 修补 |
| 反应式基础 | Missionary（连续流） | 自定义信号图（Observer 模式 + async 调度） | Python 原生，async/await，无外部反应式库 |
| 增量计算 | incseq（增量序列，全排列代数） | Diff 引擎（基于 key 的 LIS 集合 diff） | 更简单——keyed diff 覆盖常见 UI 场景 |
| DOM 更新 | 通过 incseq 直接 DOM 修补 | htmx HTML swap + OOB | htmx 免费提供 swap 策略、过渡动画、历史记录 |
| **模板系统** | **程序化 DOM 构建（Clojure 数据结构）** | **Hiccup 风格 DSL（Python 数据结构 + 标签函数）** | **与 Electric 同构；无模板语言；类型安全；信号天然集成** |
| **ASGI 框架** | — | **FastAPI** | **基于 Starlette，开箱即用 WebSocket/Pydantic/DI/CORS/OpenAPI** |

### 1.3 架构总览

```
┌──────────────────────────────────────────────────────────┐
│                    Volt Application                        │
│                                                            │
│  @component("counter")                                     │
│  class Counter:                                            │
│      count = signal(0)                                     │
│                                                            │
│      @server                                               │
│      def increment(self): ...                              │
│                                                            │
│      def render(self):        # ← Hiccup DSL, 纯 Python   │
│          count = self.count.get()                          │
│          return div({"id": cid},                           │
│              h2(f"Count: {count}"),                        │
│              button({"hx-post": action_url("inc")}, "+1")) │
├──────────────────────────────────────────────────────────┤
│                    Volt 框架                                │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Signal Graph │  │  Diff Engine │  │  Renderer      │  │
│  │  (reactive    │──│  (LIS keyed  │──│  (Hiccup →     │  │
│  │   deps track) │  │   collection │  │   HTML 序列化) │  │
│  │              │  │   diffing)    │  │                │  │
│  └──────────────┘  └──────────────┘  └────────────────┘  │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Render      │  │  Transport   │  │  Component     │  │
│  │  Scheduler   │──│  (WS/SSE/    │  │  Registry      │  │
│  │  (async      │  │   HTTP)      │  │  + Session     │  │
│  │   batcher)   │  │              │  │  (per-conn     │  │
│  │              │  │              │  │   state)       │  │
│  └──────────────┘  └──────────────┘  └────────────────┘  │
├──────────────────────────────────────────────────────────┤
│              FastAPI (基于 Starlette)                     │
└──────────────────────────────────────────────────────────┘

          │ WebSocket / SSE / HTTP
          ▼
┌──────────────────────────────────────────────────────────┐
│                   浏览器（客户端）                          │
│                                                            │
│  htmx ─────── 处理 AJAX、DOM swap、OOB、历史记录          │
│  hyperscript ── 处理客户端交互                             │
│  volt.js ───── 薄 WebSocket 客户端，用于实时同步           │
└──────────────────────────────────────────────────────────┘
```

### 1.4 核心抽象

#### 1.4.1 Signal — 反应式值容器

Volt 反应式的根基。`Signal[T]` 持有类型为 `T` 的值，并在变化时通知依赖方。

```
Signal[T]
├── value: T                         (当前值)
├── dependents: list[Effect]         (订阅者)
├── version: int                     (变更计数器，用于 diff 跟踪)
│
├── .get() -> T                      (读值，记录依赖)
├── .set(value: T)                   (写值，触发传播)
├── .subscribe(effect: Effect)       (添加订阅者)

ComputedSignal[T](Signal[T])         (派生值)
├── compute_fn: () -> T
├── dirty: bool
├── sources: list[Signal]            (已跟踪的依赖)
│
├── .get() -> T                      (若 dirty 则重新计算)

Effect                               (副作用执行器)
├── effect_fn: () -> None
├── deps: list[Signal]
│
├── .execute()                       (执行 effect，跟踪依赖)
├── .dispose()                       (清理订阅)
```

**关键行为：**

- **依赖跟踪**：当 Effect 或 ComputedSignal 调用 `.get()` 时，自动记录依赖关系
- **批量处理**：`batch()` 上下文管理器内多次 `.set()` 合并为一次，依赖方仅在批处理结束时收到通知
- **无毛刺（Glitch-free）**：拓扑排序确保传播顺序正确，无中间不一致状态
- **类型安全**：`Signal[T]` 使用 `Generic[T]`（Python 3.10+），`.get()` 返回 `T`，`.set(value: T)` 接收 `T`，`mypy` 可完全检查
- **实例级作用域**：信号值绑定到组件实例，而非类级别，天然支持多会话隔离

#### 1.4.2 Component — UI 构建块

Component 是封装反应式状态、服务端逻辑和 Hiccup 渲染方法的类。

```
Component (abstract)
├── signals: dict[str, Signal]        (反应式状态)
├── component_id: str                 (唯一 DOM id)
├── key: str | None                   (用于 diffing 的稳定标识)
│
├── @server methods                   (通过 htmx/WS 触发的服务端方法)
├── def render(self) -> HiccupNode    (返回 Hiccup 树，纯 Python)
├── .mount()                          (初始化状态，启动 effects)
├── .unmount()                        (清理 effects)
├── .action_url(method: str) -> str   (生成 htmx action URL)

ComponentRegistry
├── _components: dict[str, Type[Component]]
├── register(name, cls)
├── resolve(name) -> Type[Component]
├── create(name, **props) -> Component
```

**渲染契约：**

- 每个组件的 `render()` 返回一棵 **Hiccup 树**（Python 标签函数嵌套调用）
- 标签函数（`div`、`h2`、`button` 等）只是创建标准数据结构的工厂函数
- Renderer 将 Hiccup 树序列化为 HTML 字符串，包裹在 `id="{component_id}"` 的容器中
- htmx 属性（`hx-post`、`hx-target` 等）通过 `@server` 装饰器元数据和 `action_url()` 方法在 Hiccup 树中**直接生成**
- 信号变化时，Effect 包装的渲染函数自动标记组件为 dirty，RenderScheduler 批量触发重渲染

#### 1.4.3 Diff 引擎 — 增量集合 Diffing

对标 Electric 的 incseq，但使用简化的 LIS（最长递增子序列）算法。

```
Diff
├── added: list[item]
├── removed: list[item]
├── moved: dict[int, int]           (old_pos -> new_pos)
├── updated: list[(int, item)]      (position, new_item)

DiffEngine
├── .diff_by(old: list, new: list, key_fn) -> Diff
├── .apply_diff(base: list, diff: Diff) -> list
```

**与 Electric 的差异：**

- Electric 的 incseq 使用全排列代数（循环分解、split-swap 算法）处理集合重排序，diff 是幺半群可组合的
- Volt 使用 **LIS（最长递增子序列）** 算法计算最小移动步数，覆盖 95% 的 UI 场景（列表拖拽重排、排序切换）
- Diff 记录为普通 dict，不追求幺半群可组合性——以数学简洁性换取实现简单性
- HTML 级 diff 不在 Diff 引擎中处理，由 Renderer + 传输层通过旧 HTML 快照对比来做

#### 1.4.4 传输层

三种传输模式，按组件或交互场景选择：

| 模式 | 方向 | 用途 | 机制 |
|---|---|---|---|
| **HTTP（htmx AJAX）** | 客户端 → 服务端 → 客户端 | 表单提交、按钮点击、导航 | 标准 htmx `hx-post`/`hx-get`，服务端返回 HTML 片段 |
| **SSE** | 服务端 → 客户端 | 实时推送、进度更新、通知 | 服务端通过 SSE 事件推送 HTML 片段，htmx `hx-ext="sse"` 处理 |
| **WebSocket** | 双向 | 实时协作、计数器、仪表盘 | 自定义 `volt.js` 客户端收发 JSON 消息，服务端推送组件 HTML diff |

**WebSocket 模式协议：**

```json
// 服务端 → 客户端：patch
{
  "type": "patch",
  "component_id": "counter-1",
  "html": "<div id=\"counter-1\">...</div>",
  "swap": "outerHTML",
  "oob": [
    {"component_id": "status-bar", "html": "<span>...</span>", "swap": "innerHTML"}
  ]
}

// 客户端 → 服务端：action
{
  "type": "action",
  "component_id": "counter-1",
  "method": "increment",
  "args": {}
}

// 服务端 → 客户端：error
{
  "type": "error",
  "component_id": "counter-1",
  "message": "Failed to increment",
  "status": 500
}

// 服务端 → 客户端：批量 patch（合并多个组件更新）
{
  "type": "batch",
  "patches": [
    {"type": "patch", "component_id": "counter-1", "html": "...", "swap": "outerHTML"},
    {"type": "patch", "component_id": "status-bar", "html": "...", "swap": "innerHTML"}
  ]
}
```

**会话生命周期：**

1. 客户端通过 WebSocket 连接（或首次 HTTP 请求创建会话）
2. 服务端创建 `Session` 对象，持有组件树和信号订阅
3. 信号变化时，服务端通过 RenderScheduler 收集脏组件
4. 批量渲染后，diff 序列化为 JSON 推送给客户端
5. 断开连接时，effects 被清理，会话资源释放
6. 重连时通过 session ID 恢复状态

**会话与 FastAPI 依赖注入集成：**

```python
from fastapi import Depends, Request

async def get_session(request: Request) -> Session:
    """FastAPI 依赖：从 cookie / header 获取或创建会话。"""
    sid = request.cookies.get("volt_sid")
    if not sid:
        sid = str(uuid4())
    session = request.app.state.volt["sessions"].get(sid)
    if session is None:
        session = Session(sid)
        request.app.state.volt["sessions"][sid] = session
    return session
```

#### 1.4.5 模板系统 — Hiccup 风格 DSL

**Hiccup** 是 Clojure 生态中将 HTML 表示为嵌套数据结构的惯用方式。Volt 在 Python 中实现同样的理念：

```python
from volt.hiccup import div, h2, button, ul, li, span, input_, p, h1

# 样式 A：标签函数（更 Pythonic，推荐 API）
div(
    {"id": "counter-1", "class": "counter"},
    h2("Count: ", count),
    button({"hx-post": "/inc", "hx-target": "#counter-1"}, "+1"),
)

# 样式 B：纯数据结构（与 Hiccup 原版一致）
["div", {"id": "counter-1", "class": "counter"},
    ["h2", "Count: ", count],
    ["button", {"hx-post": "/inc", "hx-target": "#counter-1"}, "+1"]]
```

**两种样式等价**——标签函数内部直接生成 `["tagname", attrs, ...children]` 结构，Renderer 统一消费。用户代码可以使用样式 A（推荐），框架内部使用样式 B 处理。

**标签函数实现原理：**

```python
# 类型定义
type HiccupNode = str | list  # 字符串叶节点 或 ["tag", dict|None, *children]

def _tag(name: str):
    """工厂：生成对应 HTML 标签的标签函数。"""
    def tag(*args) -> list:
        # 第一个参数如果是 dict，作为属性
        if args and isinstance(args[0], dict):
            return [name, args[0], *[normalize_child(c) for c in args[1:]]]
        # 否则无属性
        return [name, None, *[normalize_child(c) for c in args]]
    return tag

# 批量生成所有 HTML5 标签
div   = _tag("div")
h1    = _tag("h1")
h2    = _tag("h2")
h3    = _tag("h3")
p     = _tag("p")
span  = _tag("span")
button = _tag("button")
input_ = _tag("input")
ul    = _tag("ul")
ol    = _tag("ol")
li    = _tag("li")
a     = _tag("a")
form  = _tag("form")
label = _tag("label")
select = _tag("select")
option = _tag("option")
textarea = _tag("textarea")
img   = _tag("img")
br_   = _tag("br")
hr_   = _tag("hr")
table = _tag("table")
tr    = _tag("tr")
td    = _tag("td")
th    = _tag("th")
thead = _tag("thead")
tbody = _tag("tbody")
section = _tag("section")
header = _tag("header")
footer = _tag("footer")
nav   = _tag("nav")
main  = _tag("main")

def raw(html_string: str) -> list:
    """标记为原始 HTML，渲染时不做转义。"""
    return ["__raw__", None, html_string]

def fragment(*children) -> list:
    """无包裹容器的片段。"""
    return ["__fragment__", None, *children]

def normalize_child(child) -> str | list:
    """确保叶节点统一为字符串。"""
    return str(child) if not isinstance(child, (str, list)) else child
```

**Renderer（Hiccup 树 → HTML）：**

```python
import html

class HiccupRenderer:
    def render(self, node: HiccupNode) -> str:
        match node:
            case str():
                return html.escape(node, quote=False)
            case ["__raw__", _, content]:
                return content
            case ["__fragment__", _, *children]:
                return "".join(self.render(c) for c in children)
            case [tag, attrs, *children]:
                attrs_html = self._render_attrs(attrs) if attrs else ""
                children_html = "".join(self.render(c) for c in children)
                if tag in ("br", "hr", "input", "img", "meta", "link"):
                    return f"<{tag}{attrs_html}>" if attrs else f"<{tag}>"
                return f"<{tag}{attrs_html}>{children_html}</{tag}>"
            case _:
                return html.escape(str(node), quote=False)

    def _render_attrs(self, attrs: dict) -> str:
        parts = []
        for k, v in sorted(attrs.items()):
            if v is True:
                parts.append(f' {k}')
            elif v is False or v is None:
                continue
            elif isinstance(v, (list, tuple)):
                parts.append(f' {k}="{" ".join(v)}"')
            else:
                parts.append(f' {k}="{html.escape(str(v), quote=True)}"')
        return "".join(parts)

    def render_component(self, component: Component) -> str:
        """渲染组件：执行 render() 方法 → 转 HTML → 包裹容器。"""
        hiccup = component.render()
        html_str = self.render(hiccup)
        return f'<div id="{component.component_id}">{html_str}</div>'
```

**信号集成——自动依赖跟踪：**

```python
class Counter(Component):
    def __init__(self):
        self.count = signal(0)

    @server
    def increment(self):
        self.count.set(self.count.get() + 1)

    def render(self) -> HiccupNode:
        # 关键：.get() 触发依赖跟踪
        # Effect 包装了 render() 调用，自动记录对 count 的依赖
        count = self.count.get()

        return div(
            {"id": self.component_id, "class": "counter"},
            h2(f"Count: {count}"),
            button(
                {
                    "hx-post": self.action_url("increment"),
                    "hx-target": f"#{self.component_id}",
                    "hx-swap": "outerHTML",
                },
                "+1",
            ),
        )
```

当 `render()` 调用 `self.count.get()` 时，依赖跟踪上下文自动将 `count` 信号记录为当前 Effect 的依赖。`count.set()` 被调用后，依赖图通知 Effect，通过 RenderScheduler 将组件标记为 dirty 并触发重渲染。

**条件与循环——纯 Python，无需模板语法：**

```python
def render(self):
    count = self.count.get()
    items = self.items.get()
    user = self.user.get()

    return div({"class": "todo-app"},
        h1("待办事项"),

        # 条件 — 纯 Python if/else
        p({"class": "error"}) if count < 0 else None,

        # 三元表达式
        span(f"用户: {user.name}" if user else "未登录"),

        # 循环 — 纯 Python 列表推导式
        ul(
            [li({"key": item.id, "class": "done" if item.done else ""},
                item.text)
             for item in items]
        ),

        # 条件渲染多个元素 — 用 fragment 包裹
        *([
            p("这是管理员面板"),
            button({"hx-post": "/admin/action"}, "执行"),
        ] if user.is_admin else [
            p("普通用户视图"),
        ]),

        input_({"type": "text", "name": "new-item",
                "hx-post": self.action_url("add_item")}),
    )
```

**为什么 Hiccup 优于 Jinja2：**

| 维度 | Jinja2 | Hiccup DSL |
|---|---|---|
| 类型安全 | 无（运行时字符串拼接） | 有（mypy/pyright 可检查标签调用、属性类型） |
| 依赖 | 需要第三方模板引擎（~500KB） | 纯 Python 数据结构，零额外依赖 |
| 信号集成 | 需要自定义 Jinja2 扩展和模板解析钩子 | `.get()` 天然支持，零开销 |
| 组合性 | 模板宏/继承（受限，参数类型不安全） | `map`、列表推导式、高阶函数、partial |
| 条件/循环 | Jinja2 语法（`{% if %}`, `{% for %}`） | Python 原生（`if`、`for`、列表推导式） |
| IDE 支持 | 模板中无检查，无自动补全 | 全 IDE 支持：跳转定义、自动补全、重构 |
| 测试 | 需要额外的模板测试框架 | 直接对 Python 函数做单元测试 |
| 性能 | 编译模板 → 缓存 → 渲染 | 递归遍历 Python 列表，无编译步骤 |

### 1.5 数据流

**请求-响应周期（HTTP/htmx）：**

```
1. 用户点击按钮（htmx 拦截 click 事件）
2. htmx 发送 POST 到 /volt/action/counter-1/increment
3. FastAPI 路由分发给 Counter.increment()
4. increment() 调用 self.count.set(self.count.get() + 1)
5. 信号传播 → Effect 通过 RenderScheduler.mark_dirty("counter-1") 标记脏组件
6. FastAPI 事件循环下一次 tick → RenderScheduler 收集脏组件
7. 调用 Counter.render() 获取 Hiccup 树（.get() 读取信号值）
8. HiccupRenderer 将 Hiccup 树序列化为 HTML 字符串
9. 服务端返回 HTMLResponse，包含新 HTML 片段
10. htmx swap DOM（outerHTML 替换 #counter-1）
```

**实时推送（WebSocket）：**

```
1. 服务端事件（如数据库变更、消息队列）更新信号
2. 信号传播 → mark_dirty("component-id")
3. RenderScheduler 批量收集脏组件（多个信号变化合并为一个渲染批次）
4. 每个脏组件重新执行 render() → 新的 Hiccup 树
5. HiccupRenderer 序列化为 HTML
6. 可选：DiffEngine 与上次渲染快照对比，只发送变化的集合部分
7. JSON batch patch 消息通过 WebSocket 推送
8. volt.js 客户端接收 batch，遍历 patches，调用 htmx swap API 应用 HTML
```

### 1.6 与 Electric 的对比

| 维度 | Electric (Clojure) | Volt (Python) |
|---|---|---|
| **语言** | Clojure + ClojureScript | Python + JavaScript（极简 volt.js） |
| **代码拆分** | 编译器宏静态分析 | 装饰器注解 + Python 函数作用域（运行时） |
| **反应式原语** | Missionary 流 | Signal 图（同步传播 + async 调度） |
| **Diff 计算** | incseq（排列代数，幺半群可组合） | 基于 key 的 LIS diff（更简单，覆盖 95% UI 场景） |
| **协议** | 基于 WebSocket 的自定义二进制协议 | 基于 WebSocket/SSE/HTTP 的 JSON |
| **DOM 更新** | 自定义直接 DOM 修补 | htmx swap + OOB |
| **模板/视图** | Clojure 数据结构（程序化构建） | **Hiccup DSL（Python 数据结构 + 标签函数）——同构方案** |
| **客户端体积** | ClojureScript 全量（~MB 级） | htmx (~14k) + hyperscript (~40k) + volt.js (~2k) = ~56k |
| **构建步骤** | Shadow-CLJS 必需 | 无 |
| **学习曲线** | 陡峭（Clojure、宏、Missionary、incseq） | 中等（Python async、htmx 声明式） |
| **热重载** | CLJ + CLJS REPL 同步 | FastAPI 开发服务器 auto-reload + WebSocket 自动重连 |

### 1.7 约束与权衡

1. **无编译时代码拆分**—与 Electric 的编译器不同，Volt 无法静态分析 Python 代码进行客户端/服务端拆分。`@server` 装饰器是运行时提示，而非编译器指令。客户端逻辑通过 htmx 属性声明式表达，不能运行任意 Python 代码。

2. **更简化的 diff 模型**—Electric 的 incseq 支持完整的排列代数（组合、逆、旋转），实现幺半群可组合的 diff。Volt 的 diff 引擎仅支持增/删/改/重排——对 UI 够用，但在数学通用性上有所取舍。

3. **HTML-over-the-wire**—发送 HTML 片段而非二进制 diff。带宽略高于 Electric 的二进制协议，但省去了自定义客户端解析器，且 htmx 免费提供 swap 策略、过渡、历史记录。

4. **单进程服务端**—Electric 的会话模型支持多服务器对等节点。Volt 初始版本针对单进程部署（标准 ASGI），未来可扩展。

5. **需要少量客户端 JS**—相比纯 htmx 方案，Volt 需要 `volt.js`（~2KB）处理 WebSocket 实时同步。纯 HTTP/htmx 模式不需要它。

6. **Python 没有真正的客户端执行**—Electric 的 `e/client` 块可以在客户端运行任意 ClojureScript 代码。Volt 的客户端行为完全通过 htmx 属性定义，不能执行任意的客户端交互逻辑。对于需要复杂客户端状态的场景，需要 hyperscript 或 Alpine.js 辅助。

---

## Part 2：项目结构与实施计划

### 2.1 项目结构

```
volt/                              # 项目根目录（由 uv 管理的 Python 包）
├── pyproject.toml                 # 包元数据、依赖声明（uv 构建）
├── mise.toml                      # 环境管理（Python 版本、工具链）
├── README.md
├── LICENSE
│
├── src/
│   └── volt/                      # 库源码（可发布的 Python 包）
│       ├── __init__.py            # 公共 API 导出
│       │
│       ├── signal.py              # Signal[T], ComputedSignal[T], Effect, batch()
│       ├── hiccup.py              # 标签函数工厂 + HiccupNode 类型定义
│       ├── component.py           # Component 基类、@server 装饰器
│       ├── diff.py                # DiffEngine, 基于 key 的 LIS 集合 diff
│       ├── renderer.py            # HiccupRenderer: Hiccup 树 → HTML
│       ├── scheduler.py           # RenderScheduler: 脏组件批量 + async 调度
│       ├── registry.py            # ComponentRegistry
│       ├── session.py             # Session（每连接状态 + FastAPI Depends）
│       │
│       ├── transport/             # 传输层
│       │   ├── __init__.py
│       │   ├── http.py            # FastAPI router for htmx AJAX actions
│       │   ├── websocket.py       # FastAPI WebSocket handler
│       │   ├── sse.py             # SSE stream handler
│       │   └── protocol.py        # 消息类型（Pydantic models）
│       │
│       └── app.py                 # create_volt_app() 工厂函数 + VoltConfig
│
├── static/
│   ├── volt.js                    # 薄 WebSocket 客户端（~200 行）
│   ├── htmx.min.js                # htmx（可选项，加载自 CDN）
│   └── hyperscript.min.js         # hyperscript（可选项，加载自 CDN）
│
├── examples/                      # 示例应用（作为文档和集成测试）
│   ├── counter/
│   │   ├── app.py                 # Counter 示例应用
│   │   └── index.html             # 页面模板
│   └── chat/
│       ├── app.py                 # 实时聊天示例
│       └── index.html
│
└── tests/                         # 测试（与包结构镜像）
    ├── test_signal.py
    ├── test_hiccup.py
    ├── test_component.py
    ├── test_registry.py
    ├── test_renderer.py
    ├── test_scheduler.py
    ├── test_session.py
    │
    ├── transport/
    │   ├── test_protocol.py
    │   ├── test_http.py
    │   ├── test_websocket.py
    │   └── test_sse.py
    │
    └── integration/
        └── test_counter_e2e.py    # 端到端集成测试
```

### 2.2 环境管理（mise）

```toml
# mise.toml
[tools]
python = "3.12"

[env]
VOLT_ENV = "development"
```

通过 `mise` 管理 Python 版本和项目环境变量，确保所有开发者使用一致的运行时。

### 2.3 包配置（uv）

```toml
# pyproject.toml
[project]
name = "volt"
version = "0.1.0"
description = "Volt Reactive Web Framework — Hiccup DSL + FastAPI"
requires-python = ">=3.10"
license = "MIT"
authors = [
    {name = "Volt Contributors"},
]

dependencies = [
    "fastapi>=0.110.0",
]

[project.urls]
Repository = "https://github.com/your-org/volt"
Documentation = "https://volt.dev"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "uvicorn[standard]>=0.29",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

其他开发者可通过以下方式引入依赖：

```bash
# 作为依赖添加
uv add volt

# 或从源码安装
uv sync
```

### 2.4 依赖图

```
阶段 1a (Signal) ─────────→ 阶段 3 (Component) ──→ 阶段 4 (Renderer) ──→ 阶段 5 (Transport) ──→ 阶段 6 (VoltApp) ──→ 阶段 7 (Examples)
阶段 1b (Scheduler) ─────────────────────────────────────────────────────────→ 阶段 5 (Transport)
阶段 2 (Hiccup DSL) ─────────────────────────────────→ 阶段 4 (Renderer)
阶段 3 (Diff Engine) ───────────────────────────────────────────────────────→ 阶段 5 (Transport)
```

可并行路径：
- **路径 A**：阶段 1a（Signal）→ 阶段 3（Component）→ 阶段 4（Renderer）
- **路径 B**：阶段 1b（Scheduler）→ 阶段 5（Transport）
- **路径 C**：阶段 2（Hiccup DSL）→ 阶段 4（Renderer）
- **路径 D**：阶段 3（Diff Engine）→ 阶段 5（Transport）

阶段 1a、1b、2、3 可并行开发。

### 2.5 实施计划

#### 阶段 1：反应式信号系统（基础）

**目标：** 实现核心反应式原语——Signal、ComputedSignal、Effect、依赖跟踪，以及连接 async 传输层的 RenderScheduler。

**Task 1.1：Signal 与依赖跟踪**

文件：`src/volt/signal.py`，测试：`tests/test_signal.py`

```python
from typing import Generic, TypeVar
from contextvars import ContextVar

T = TypeVar("T")

_current_tracker: ContextVar["_Tracker | None"] = ContextVar("_tracker", default=None)

class Signal(Generic[T]):
    """反应式值容器。调用 .get() 时自动注册到当前 _current_tracker。"""

    def __init__(self, initial: T) -> None:
        self._value: T = initial
        self._version: int = 0
        self._dependents: list[Effect] = []

    def get(self) -> T:
        tracker = _current_tracker.get()
        if tracker is not None:
            tracker.add_dependency(self)
        return self._value

    def set(self, value: T) -> None:
        if self._value == value:
            return
        self._value = value
        self._version += 1
        # 同步通知所有依赖（批量模式下延迟）
        for dep in self._dependents:
            dep.invalidate()
```

**Task 1.2：ComputedSignal**

```python
class ComputedSignal(Signal[T]):
    """派生值：源信号变化时惰性重新计算。"""

    def __init__(self, compute_fn: Callable[[], T]) -> None:
        self._compute_fn = compute_fn
        self._dirty = True
        self._sources: list[Signal] = []
        super().__init__(compute_fn())  # 初始计算

    def get(self) -> T:
        if self._dirty:
            self._recompute()
        return super().get()

    def _recompute(self) -> None:
        self._sources.clear()
        tracker = _Tracker()
        token = _current_tracker.set(tracker)
        try:
            new_value = self._compute_fn()
        finally:
            _current_tracker.reset(token)
        self._sources = tracker.dependencies
        self._dirty = False
        for src in self._sources:
            if self not in src._dependents:
                src._dependents.append(self)

    def invalidate(self) -> None:
        self._dirty = True
        for dep in self._dependents:
            dep.invalidate()
```

**Task 1.3：Effect 系统**

```python
class Effect:
    """副作用执行器：创建时立即执行，依赖变化时自动重新执行。"""

    def __init__(self, effect_fn: Callable[[], None]) -> None:
        self._effect_fn = effect_fn
        self._deps: list[Signal] = []
        self._disposed = False
        self._execute()

    def _execute(self) -> None:
        self._deps.clear()
        tracker = _Tracker()
        token = _current_tracker.set(tracker)
        try:
            self._effect_fn()
        finally:
            _current_tracker.reset(token)
        self._deps = tracker.dependencies
        for dep in self._deps:
            if self not in dep._dependents:
                dep._dependents.append(self)

    def invalidate(self) -> None:
        if not self._disposed:
            if _batch_level.get() > 0:
                _pending_effects.add(self)
            else:
                self._execute()

    def dispose(self) -> None:
        self._disposed = True
        for dep in self._deps:
            if self in dep._dependents:
                dep._dependents.remove(self)
        self._deps.clear()
```

**Task 1.4：批量更新（batch）**

```python
_batch_level: ContextVar[int] = ContextVar("_batch_level", default=0)
_pending_effects: set[Effect] = set()

@contextmanager
def batch() -> Generator[None, None, None]:
    token = _batch_level.set(_batch_level.get() + 1)
    try:
        yield
    finally:
        _batch_level.reset(token)
        if _batch_level.get() == 0:
            effects = _pending_effects.copy()
            _pending_effects.clear()
            for effect in _topological_sort(effects):
                effect._execute()
```

**Task 1.5：RenderScheduler（async 调度器）**

**作用：** 连接同步信号传播和 async 传输层。当 Effect 检测到信号变化时，通过 `mark_dirty` 异步唤醒渲染循环。

文件：`src/volt/scheduler.py`，测试：`tests/test_scheduler.py`

```python
import asyncio
from collections.abc import Callable, Awaitable

class RenderScheduler:
    """将同步信号传播桥接到 async 渲染队列。

    架构：
        同步侧（Signal → Effect）
            │
            ▼
        mark_dirty(component_id)   ← Effect 回调（同步）
            │
            ▼
        asyncio.Event.set()
            │
            ▼
        async tick() 循环           ← FastAPI 事件循环
            │
            ▼
        render_fn(dirty_ids)        ← 批量渲染 Hiccup → HTML
            │
            ▼
        push_fn(patches)            ← WebSocket/SSE 推送
    """

    def __init__(self) -> None:
        self._dirty: set[str] = set()
        self._event = asyncio.Event()
        self._task: asyncio.Task | None = None

    def mark_dirty(self, component_id: str) -> None:
        """由 Effect 回调调用（同步的 Signal 传播线程中）。"""
        self._dirty.add(component_id)
        self._event.set()

    async def tick(
        self,
        render_fn: Callable[[set[str]], Awaitable[list[dict]]],
        push_fn: Callable[[list[dict]], Awaitable[None]],
    ) -> None:
        """在 FastAPI 事件循环中永久运行。"""
        while True:
            await self._event.wait()
            self._event.clear()
            dirty = self._dirty.copy()
            self._dirty.clear()
            if dirty:
                patches = await render_fn(dirty)
                if patches:
                    await push_fn(patches)

    def start(self, loop: asyncio.AbstractEventLoop,
              render_fn, push_fn) -> None:
        self._task = loop.create_task(self.tick(render_fn, push_fn))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
```

---

#### 阶段 2：Hiccup DSL（核心模板层）

**目标：** 实现 Hiccup 风格的 HTML DSL——标签函数、HiccupNode 类型、HTML 序列化。

**此阶段无依赖，可与阶段 1 并行开发。**

文件：`src/volt/hiccup.py`，测试：`tests/test_hiccup.py`

```python
# 节点类型
type HiccupNode = str | list

def _tag(name: str) -> Callable:
    """创建单个 HTML 标签函数。"""
    def tag(*args):
        if args and isinstance(args[0], dict):
            return [name, args[0],
                    *[str(c) if not isinstance(c, (str, list)) else c
                      for c in args[1:]]]
        return [name, None,
                *[str(c) if not isinstance(c, (str, list)) else c
                  for c in args]]
    return tag

# 批量生成标签
div = _tag("div")
h1 = _tag("h1")
# ... 所有 HTML5 标签

def raw(html: str) -> list:
    return ["__raw__", None, html]

def fragment(*children) -> list:
    return ["__fragment__", None, *children]
```

需要编写以下测试：
- 标签函数生成正确结构
- 嵌套标签渲染
- 布尔属性、class 列表、data-* 属性
- XSS 防护（`html.escape`）
- `raw()` 跳过转义

---

#### 阶段 3：组件系统

**目标：** 定义组件抽象，含生命周期、装饰器、注册表。

文件：`src/volt/component.py`、`src/volt/registry.py`，测试：`tests/test_component.py`、`tests/test_registry.py`

```python
import uuid
from volt.signal import Signal

class Component:
    """UI 组件基类。子类定义信号和 render() 方法。"""

    component_id: str
    key: str | None = None

    def __init__(self, **props: dict) -> None:
        self.component_id = (
            f"{self.__class__.__name__.lower()}-{uuid.uuid4().hex[:8]}"
        )
        self._signals: dict[str, Signal] = {}
        self._discovered_signals()
        for k, v in props.items():
            if k in self._signals:
                self._signals[k].set(v)

    def _discovered_signals(self) -> None:
        for name in dir(self):
            attr = getattr(self, name, None)
            if isinstance(attr, Signal):
                self._signals[name] = attr

    def render(self) -> list:
        raise NotImplementedError

    def mount(self) -> None:
        pass

    def unmount(self) -> None:
        pass

    def action_url(self, method_name: str) -> str:
        return f"/volt/action/{self.component_id}/{method_name}"
```

```python
_SERVER_METHODS_ATTR = "_volt_server_methods"

def server(method: Callable) -> Callable:
    """标记方法为服务端 action（可通过 htmx/WS 触发）。"""
    if not hasattr(method, _SERVER_METHODS_ATTR):
        setattr(method, _SERVER_METHODS_ATTR, True)
    return method
```

```python
class ComponentRegistry:
    def __init__(self) -> None:
        self._components: dict[str, type[Component]] = {}

    def register(self, name: str, cls: type[Component]) -> None:
        self._components[name] = cls

    def resolve(self, name: str) -> type[Component]:
        if name not in self._components:
            raise ValueError(f"Component '{name}' not registered")
        return self._components[name]

    def create(self, name: str, **props) -> Component:
        cls = self.resolve(name)
        return cls(**props)


_registry: ComponentRegistry | None = None

def set_registry(registry: ComponentRegistry) -> None:
    global _registry
    _registry = registry

def component(name: str):
    """装饰器：将类注册为组件。"""
    def wrapper(cls):
        if _registry is not None:
            _registry.register(name, cls)
        return cls
    return wrapper
```

---

#### 阶段 4：Renderer（Hiccup → HTML）

**目标：** 将 Hiccup 树序列化为 HTML 字符串，集成组件渲染和缓存优化。

文件：`src/volt/renderer.py`，测试：`tests/test_renderer.py`

```python
import html
from volt.hiccup import HiccupNode
from volt.component import Component

class HiccupRenderer:
    """将 Hiccup 树序列化为 HTML 字符串。"""

    def render(self, node: HiccupNode) -> str:
        match node:
            case str():
                return html.escape(node, quote=False)
            case ["__raw__", _, content]:
                return content
            case ["__fragment__", _, *children]:
                return "".join(self.render(c) for c in children)
            case [tag, attrs, *children] if tag:
                a = self._render_attrs(attrs) if attrs else ""
                c = "".join(self.render(child) for child in children)
                if tag in _VOID_ELEMENTS:
                    return f"<{tag}{a}>"
                return f"<{tag}{a}>{c}</{tag}>"
            case _:
                return html.escape(str(node), quote=False)

    def _render_attrs(self, attrs: dict) -> str:
        parts = []
        for k, v in attrs.items():
            if v is True:
                parts.append(f' {k}')
            elif v is False or v is None:
                continue
            elif isinstance(v, (list, tuple)):
                parts.append(
                    f' {k}="{html.escape(" ".join(str(x) for x in v), quote=True)}"'
                )
            else:
                parts.append(f' {k}="{html.escape(str(v), quote=True)}"')
        return "".join(parts)

    def render_component(self, component: Component) -> str:
        hiccup = component.render()
        body = self.render(hiccup)
        return f'<div id="{component.component_id}">{body}</div>'

_VOID_ELEMENTS = frozenset({
    "br", "hr", "input", "img", "meta", "link",
    "area", "base", "col", "embed", "source", "track", "wbr",
})
```

**缓存优化版本：**

```python
class HiccupRenderer:
    def __init__(self):
        self._cache: dict[str, tuple[int, str]] = {}

    def render_component_cached(self, component: Component) -> str | None:
        """缓存渲染：信号版本未变时返回 None（表示无变化）。"""
        total_version = sum(s._version for s in component._signals.values())
        cached = self._cache.get(component.component_id)
        if cached and cached[0] == total_version:
            return None
        html = self.render_component(component)
        self._cache[component.component_id] = (total_version, html)
        return html
```

---

#### 阶段 5：传输层（FastAPI）

**目标：** HTTP、WebSocket 和 SSE 传输通道。

**Task 5.1：协议定义（Pydantic Models）**

```python
from pydantic import BaseModel
from typing import Literal

class PatchMessage(BaseModel):
    type: Literal["patch"] = "patch"
    component_id: str
    html: str
    swap: str = "outerHTML"
    oob: list["PatchMessage"] | None = None

class ActionMessage(BaseModel):
    type: Literal["action"] = "action"
    component_id: str
    method: str
    args: dict = {}

class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    component_id: str
    message: str
    status: int = 500

class BatchMessage(BaseModel):
    type: Literal["batch"] = "batch"
    patches: list[PatchMessage]

WSMessage = ActionMessage | PatchMessage | ErrorMessage | BatchMessage
```

**Task 5.2：HTTP Action Handler（htmx AJAX）**

```python
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/volt")

@router.post("/action/{component_id}/{method_name}")
async def handle_action(
    component_id: str,
    method_name: str,
    request: Request,
    session: Session = Depends(get_session),
):
    component = session.get_component(component_id)
    if component is None:
        return HTMLResponse("Component not found", status_code=404)

    methods = dict(component.get_server_methods())
    if method_name not in methods:
        return HTMLResponse(f"Method '{method_name}' not found", status_code=404)

    try:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        result = methods[method_name](**(body if body else {}))
        if result is not None and asyncio.iscoroutine(result):
            await result
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)

    html = session.renderer.render_component(component)
    return HTMLResponse(html)
```

**Task 5.3：WebSocket Handler**

```python
@router.websocket("/volt/ws/{session_id}")
async def volt_websocket(
    websocket: WebSocket,
    session_id: str,
    session: Session = Depends(get_session_ws),
):
    await websocket.accept()
    scheduler = RenderScheduler()
    session.on_signal_change = scheduler.mark_dirty

    async def render_fn(dirty_ids: set[str]) -> list[dict]:
        patches = []
        for cid in dirty_ids:
            component = session.get_component(cid)
            if component is None:
                continue
            html = session.renderer.render_component(component)
            patches.append({
                "type": "patch",
                "component_id": cid,
                "html": html,
                "swap": "outerHTML",
            })
        return patches

    async def push_fn(patches: list[dict]) -> None:
        if patches:
            await websocket.send_json({"type": "batch", "patches": patches})

    scheduler.start(asyncio.get_event_loop(), render_fn, push_fn)
    try:
        async for message in websocket.iter_json():
            if message.get("type") == "action":
                component = session.get_component(message["component_id"])
                if component:
                    method = message["method"]
                    args = message.get("args", {})
                    methods = dict(component.get_server_methods())
                    if method in methods:
                        result = methods[method](**args)
                        if asyncio.iscoroutine(result):
                            await result
    except WebSocketDisconnect:
        pass
    finally:
        await scheduler.stop()
        session.dispose()
```

**Task 5.4：SSE Handler**

```python
@router.get("/volt/sse/{session_id}")
async def volt_sse(session_id: str, session: Session = Depends(get_session)):
    async def event_stream():
        scheduler = RenderScheduler()
        session.on_signal_change = scheduler.mark_dirty
        while True:
            await asyncio.sleep(0.05)
            yield f"event: heartbeat\ndata: \n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

**Task 5.5：Session Manager**

文件：`src/volt/session.py`

```python
from fastapi import Request, WebSocket
from volt.registry import ComponentRegistry
from volt.renderer import HiccupRenderer
from volt.component import Component

class Session:
    def __init__(self, session_id: str, registry: ComponentRegistry,
                 renderer: HiccupRenderer) -> None:
        self.session_id = session_id
        self._components: dict[str, Component] = {}
        self._registry = registry
        self.renderer = renderer
        self.on_signal_change: Callable[[str], None] | None = None

    def mount_component(self, name: str, cid: str | None = None,
                        **props) -> Component:
        component = self._registry.create(name, **props)
        if cid:
            component.component_id = cid
        self._components[component.component_id] = component
        component.mount()

        for sig in component._signals.values():
            effect = Effect(lambda cid=component.component_id: (
                self.on_signal_change(cid) if self.on_signal_change else None
            ))
            component._effects.append(effect)

        return component

    def get_component(self, component_id: str) -> Component | None:
        return self._components.get(component_id)

    def dispose(self) -> None:
        for component in self._components.values():
            component.unmount()
        self._components.clear()
```

**Task 5.6：错误处理**

- HTTP 路径：`@server` 方法抛出异常时返回 500 + 错误信息
- WebSocket 路径：捕获异常后推送 `ErrorMessage`，连接不中断

---

#### 阶段 6：VoltApp（集成）

**目标：** 将所有组件集成为 FastAPI 应用工厂，对外提供简洁的 API。

文件：`src/volt/app.py`

```python
from dataclasses import dataclass, field
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from volt.registry import ComponentRegistry
from volt.renderer import HiccupRenderer
from volt.session import _sessions
from volt.transport import http, websocket, sse

@dataclass
class VoltConfig:
    component_registry: ComponentRegistry
    renderer: HiccupRenderer | None = None
    transport_modes: set[str] = field(default_factory=lambda: {"http", "ws"})
    session_cookie_name: str = "volt_sid"
    static_url: str | None = "/static"
    static_dir: str | None = "static"
    cors_origins: list[str] | None = None
    title: str = "Volt"
    version: str = "0.1.0"

def create_volt_app(config: VoltConfig) -> FastAPI:
    """创建并返回配置好的 FastAPI 应用。"""
    app = FastAPI(title=config.title, version=config.version)

    app.state.volt = {
        "registry": config.component_registry,
        "renderer": config.renderer or HiccupRenderer(),
        "sessions": _sessions,
    }

    if "http" in config.transport_modes:
        app.include_router(http.router)
    if "ws" in config.transport_modes:
        app.include_router(websocket.router)
    if "sse" in config.transport_modes:
        app.include_router(sse.router)

    if config.static_url and config.static_dir:
        app.mount(
            config.static_url,
            StaticFiles(directory=config.static_dir),
            name="static",
        )

    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.on_event("shutdown")
    async def cleanup_sessions():
        for session in _sessions.values():
            session.dispose()
        _sessions.clear()

    return app


def run_dev(app: FastAPI, host: str = "127.0.0.1", port: int = 8000) -> None:
    """开发服务器启动。"""
    import uvicorn
    uvicorn.run(app, host=host, port=port, reload=True)
```

**极简占位 API 文档：**

```python
# 开发者使用 Volt 的方式
#
# 1. 安装：
#    uv add volt
#
# 2. 定义组件：
#    @component("counter")
#    class Counter(Component):
#        def __init__(self):
#            self.count = signal(0)
#
#        @server
#        def increment(self):
#            self.count.set(self.count.get() + 1)
#
#        def render(self):
#            return div(h2(f"Count: {self.count.get()}"),
#                       button({"hx-post": self.action_url("increment")}, "+1"))
#
# 3. 创建应用：
#    registry = ComponentRegistry()
#    registry.register("counter", Counter)
#    app = create_volt_app(VoltConfig(component_registry=registry))
#
# 4. 运行：
#    uvicorn app:app --reload
```

**Task 6.2：Client-side JavaScript（volt.js）**

文件：`static/volt.js`

```javascript
class VoltClient {
    constructor(sessionId, wsUrl) {
        this.sessionId = sessionId;
        this.wsUrl = wsUrl;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(this.wsUrl);
        this.ws.onopen = () => { this.reconnectDelay = 1000; };
        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this._handleMessage(msg);
            } catch (e) {
                console.error("[volt] Parse error", e);
            }
        };
        this.ws.onclose = () => {
            setTimeout(() => this.connect(), this.reconnectDelay);
            this.reconnectDelay = Math.min(
                this.reconnectDelay * 2, this.maxReconnectDelay
            );
        };
    }

    _handleMessage(msg) {
        switch (msg.type) {
            case "batch":
                for (const patch of msg.patches) this._applyPatch(patch);
                break;
            case "patch":
                this._applyPatch(msg);
                break;
            case "error":
                console.error("[volt] Server error:", msg.message);
                break;
        }
    }

    _applyPatch(patch) {
        const target = document.getElementById(patch.component_id);
        if (!target) return;
        if (typeof htmx !== "undefined") {
            htmx.swap(target, patch.html, { swapStyle: patch.swap || "outerHTML" });
        } else {
            target[patch.swap === "outerHTML" ? "outerHTML" : "innerHTML"] = patch.html;
        }
    }

    sendAction(componentId, method, args = {}) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: "action", component_id: componentId, method, args,
            }));
        }
    }

    disconnect() { this.ws?.close(); this.ws = null; }
}

document.addEventListener("DOMContentLoaded", () => {
    const meta = document.querySelector('meta[name="volt-session"]');
    if (meta) {
        const sessionId = meta.getAttribute("content");
        const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
        window.voltClient = new VoltClient(
            sessionId, `${wsProtocol}//${location.host}/volt/ws/${sessionId}`
        );
    }
});
```

---

#### 阶段 7：示例应用 + 集成测试

**目标：** 通过工作示例验证全栈，并建立自动化集成测试。

**示例 1：Counter**

文件：`examples/counter/app.py`

```python
from volt import (
    Component, signal, server, component,
    ComponentRegistry, create_volt_app, VoltConfig,
)
from volt.hiccup import div, h2, button

@component("counter")
class Counter(Component):
    def __init__(self):
        super().__init__()
        self.count = signal(0)

    @server
    def increment(self):
        self.count.set(self.count.get() + 1)

    @server
    def decrement(self):
        self.count.set(self.count.get() - 1)

    @server
    def reset(self):
        self.count.set(0)

    def render(self):
        count = self.count.get()
        return div(
            {"class": "counter"},
            h2(f"Count: {count}"),
            button({"hx-post": self.action_url("decrement")}, "-1"),
            button({"hx-post": self.action_url("reset")}, "Reset"),
            button({"hx-post": self.action_url("increment")}, "+1"),
        )

registry = ComponentRegistry()
registry.register("counter", Counter)

app = create_volt_app(VoltConfig(component_registry=registry))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
```

**集成测试：**

```python
@pytest.mark.asyncio
async def test_counter_http_cycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport) as client:
        resp = await client.get("/")
        assert "Count: 0" in resp.text
        sid = resp.cookies.get("volt_sid")

        resp = await client.post(
            "/volt/action/counter-1/increment",
            cookies={"volt_sid": sid},
        )
        assert "Count: 1" in resp.text

        resp = await client.post(
            "/volt/action/counter-1/reset",
            cookies={"volt_sid": sid},
        )
        assert "Count: 0" in resp.text
```

**示例 2：实时聊天**

文件：`examples/chat/app.py`

```python
@component("chat-room")
class ChatRoom(Component):
    def __init__(self):
        super().__init__()
        self.messages = signal(list(messages))

    @server
    def send_message(self, text: str, user: str = "Anonymous"):
        msg = {"user": user, "text": text, "time": datetime.now().isoformat()}
        messages.append(msg)
        self.messages.set(list(messages))

    def render(self):
        msgs = self.messages.get()
        return div(
            {"class": "chat-room"},
            h2("聊天室"),
            ul([li(
                {"key": m["time"]},
                span({"class": "user"}, m["user"]),
                ": ",
                span({"class": "text"}, m["text"]),
            ) for m in msgs]),
            form({"hx-post": self.action_url("send_message")},
                 input_({"type": "text", "name": "text"}),
                 button({"type": "submit"}, "发送")),
        )
```

---

## 汇总

| 阶段 | 模块 | 文件 | 关键依赖 |
|---|---|---|---|
| 1 | Signal 系统 + Scheduler | `signal.py`, `scheduler.py` | 无（基础） |
| 2 | Hiccup DSL | `hiccup.py` | 无（可与阶段 1 并行） |
| 3 | 组件系统 | `component.py`, `registry.py` | 阶段 1 |
| 4 | Renderer | `renderer.py` | 阶段 1, 2, 3 |
| 5 | 传输层 | `transport/` | 阶段 1, 3, 4 |
| 6 | VoltApp 集成 | `app.py`, `static/volt.js` | 阶段 5 |
| 7 | 示例 + 集成测试 | `examples/`, `tests/integration/` | 阶段 6 |

**核心原则：**

- **独立的 Python 包**：通过 `uv add volt` 直接安装，无 Polylith 约束
- **最小依赖**：仅强制依赖 FastAPI，其余均为可选或开发依赖
- **零 JS 编写**（可选）：WebSocket 模式需要 `volt.js`（2KB），HTTP 模式完全不需要
- **类型安全**：全链路 mypy/pyright 可检查

---

## 附录：迭代路线图

### V0.1 — 最小可行
- Signal + Effect + batch（阶段 1）
- Hiccup DSL + Renderer（阶段 2 + 4）
- Component + `@server` + Registry（阶段 3）
- HTTP transport only（阶段 5.1 + 5.5）
- Counter 示例（阶段 7）
- `uv` 构建配置 + `mise.toml`

### V0.2 — 实时同步
- RenderScheduler（阶段 1.5）
- WebSocket transport + volt.js（阶段 5.3 + 6.2）
- 聊天示例 + 集成测试（阶段 7）
- 错误处理（阶段 5.6）

### V0.3 — 完整功能
- Diff Engine
- SSE transport（阶段 5.4）
- 渲染缓存优化（阶段 4.2）
- Session 重连恢复

### V1.0 — 生产准备
- 配置系统完善
- OpenAPI 文档自动生成（FastAPI 原生）
- 性能基准测试
- CI/CD（GitHub Actions）
- PyPI 发布
