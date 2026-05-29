# Hiccl 核心发展路线图与可行性分析报告 🧪🥒
## —— 注入 Clojure 基因，打造 AI Agent 协同的现代化 Python 全栈反应式框架

> [!NOTE]
> **统一愿景（Vision）与 AI 时代开发范式**
> Hiccl 旨在成为 **"Python 中的 Clojure 哲学全栈框架"**——将 Clojure 优雅的单向数据流、细粒度反应式原子、CSP 并发编排、不可变时间旅行状态与运行时契约 Spec 注入 Python 生态。
>
> 🚀 **开发体验优先（DX-First）战略**：本路线图基于务实的工程判断，将**对开发者体验影响最大且无前置依赖的特性（HMR 热重载、hREPL 交互式开发）置于最高优先级**，让框架尽快产出可演示、可感知的成果。Spec 契约系统作为后续的"安全加固层"在框架核心稳定后引入，确保所有模块、高阶特性都能被契约约束与 AI Agent 自愈闭环所覆盖。

---

## 一、 版本号与阶段映射

> [!IMPORTANT]
> 每个 Phase 绑定明确的语义化版本号（SemVer），提供可衡量的交付里程碑。Phase 之间标注了真实的依赖关系——无依赖的阶段可以并行推进。

| 版本号 | 阶段 | 核心交付物 | 前置依赖 | 预估周期 |
|:---|:---|:---|:---|:---|
| **v0.1.0** | Phase 0（当前已完成） | Signal + Component + Transport + Renderer + DiffEngine | — | ✅ 已完成 |
| **v0.2.0** | Phase 1 | HMR Live Reload + hREPL 交互式开发 | Phase 0 | 4–6 周 |
| **v0.3.0** | Phase 2 | `hiccl.spec` DSL + `@server` 契约验证 + Redis SessionStore | Phase 0 | 4–6 周 |
| **v0.4.0** | Phase 3 核心 | Reagent 纯函数组件 + re-frame 订阅系统 + `hiccl.testing` 单元测试工具 | Phase 1 |  4–6 周 |
| **v0.4.1** | Phase 3 增强 | Spec × Hypothesis 生成式测试 + 契约加固层 | Phase 2, Phase 3 核心 | 2–3 周 |
| **v0.5.0** | Phase 4 | CSP Channel + Transducers 中间件 | Phase 0 | 4–6 周 |
| **v0.6.0** | Phase 5a | `Signal.with_history()` 状态快照与时间旅行 | Phase 0 | 3–4 周 |
| **v0.7.0** | Phase 5b（可选） | Datalog-lite 声明式查询引擎 | Phase 5a | 独立子项目 |
| **v1.0.0** | 生产就绪 | 全量文档 + API Reference + 性能基准 + 安全审计 | 全部 | — |

> [!TIP]
> **Phase 1 和 Phase 2 无相互依赖**，可以并行推进。
> **Phase 3 核心 (函数组件 + re-frame) 不再硬依赖 Phase 2 的 Spec 契约**，只需依赖 Phase 1 以便支持纯函数热重载。Spec 契约结合生成式测试作为 v0.4.1 的增强补丁引入。
> Phase 4 和 Phase 5a 也独立于 Spec系统。
> Phase 5b（Datalog-lite）定位为**可选的独立子项目**，不作为主框架 v1.0 的硬性前提。

### ⚠️ 版本兼容策略 (Breaking Change Policy)

为保障早期采用者的开发信心，Hiccl 制定了严谨的版本稳定性承诺：
- **`0.x` 阶段**：Minor 版本（例如从 `0.1` 升级至 `0.2`）可能包含破坏性 API 变更，但每次变更**必须配套完整的升级迁移指南**（包含在新版本发布日志中）。
- **`1.0` 阶段及以后**：严格遵循语义化版本控制（SemVer）。只有在 Major 版本升级时才允许引入破坏性变更。
- **废弃标记 (Deprecation Policy)**：被标记为 `@deprecated` 的 API 至少会在接下来的**一个完整 Minor 版本**中继续保留并可用，同时输出友好的废弃警告。

---

## 二、 Clojure 基因映射与可行性深度评估

将 Clojure 的核心特性引入以 Python (FastAPI/asyncio) + HTML (HTMX/Alpine.js) 为核心的 Hiccl 中，不仅在工程上完全可行，而且能与 Python 现有的现代基础设施（如 `asyncio`、`Pydantic`、`Hypothesis`）完美融合。以下是各项能力的技术映射与可行性论证：

| Clojure 基因 | Hiccl 映射架构 | 技术实现可行性分析 | AI 自动编程价值 |
| :--- | :--- | :--- | :--- |
| **clojure.spec** | 契约式运行时数据规范 DSL | **高可行性 (95%)**<br>利用 Python 动态修饰器与数据描述符，在 `@server` 边界实现声明式验证。可结合 `Pydantic` 作为底层解析引擎，并提供 Spec 专有的 `explain()` 结构化报错。 | AI 协作的最高级"安全带"。为 AI Agent 生成组件和事件代码提供强力的契约约束，杜绝接口幻觉。 |
| **REPL-driven Dev** | hREPL 交互式内省与远程求值 | **高可行性 (95%)**<br>通过 `asyncio` 开启网络 Socket 监听，接收编辑端发来的代码块并进行远程执行（Remote Eval）。与已有的 HMR 形成强力互补。 | AI Agent 的"远程手术刀"。AI 可以直接连接 hREPL 端口，动态求值、微调状态、完成超高速调试。 |
| **Persistent Data** | 信号系统的不可变状态快照 | **高可行性 (95%)**<br>利用 `pyrsistent` 库或内置的 `tuple`/`frozenset` 可以实现超高效 of O(1) 状态比较。 | AI 可以通过 Spec 验证状态快照的合法性，安全地生成**时间旅行**、**撤销/重做**等逻辑。 |
| **EDN / Transit** | 数据传输与富类型序列化 | **高可行性 (90%)**<br>采用类似 **Transit-JSON** 的有标记 JSON 格式，在传输中保留元数据类型。 | 彻底打破 JSON 只能传输基础类型的限制，让全栈数据传递完全保留 Python 的富类型语意。 |
| **core.async / CSP** | `Channel` 通道与协程编排 | **极高可行性 (98%)**<br>基于 `asyncio.Queue` 和任务管道，包装出 CSP 核心的 `Channel` 结构，使用 `asyncio.wait` 原生实现 `alts!` 操作。 | 摆脱杂乱的 Callback。AI 能够按照明确的通道边界，自动编写极其复杂的**异步 Actor 通信与流程编排**逻辑。 |
| **Transducers** | Hiccup 渲染管线中间件 | **极高可行性 (100%)**<br>Hiccup 语法树在 Python 中表现为嵌套的 `list` 和 `dict`。我们只需提供一个递归的树遍历，即可实现流水线式转换。 | **模块解耦**。AI 可以独立编写各种 Transducer 中间件，无需侵入核心渲染器。 |
| **Protocols** | 抽象多后端系统 | **极高可行性 (100%)**<br>使用 Python 3.8+ 的 `typing.Protocol` 或 `abc.ABC` 制定严密的传输、渲染与存储协议。 | AI 可以根据 Protocol 接口规范，自动编写符合契约的第三方 Storage 或 Transport。 |
| **Datomic** | 全局不可变 App 数据库 | **中等可行性 (70%)**<br>将 Session 中的所有 Signals 归纳为统一的事实数据库。可基于 Python 生成器表达式构建轻量级查询。**注意：完整 Datalog 引擎需要统一索引结构（EAVT），复杂度远超"几百行 Python"，建议作为独立子项目评估。** | AI 能够以声明式查询提取任何层级的状态。 |
| **test.check** | 属性/生成式测试夹具 | **极高可行性 (95%)**<br>利用 Python 生态最强的属性测试框架 **Hypothesis**，将 Hiccl Specs 直接映射为 Hypothesis Strategies。 | AI 自动运行数十万次交互组合，通过生成式测试彻底排查组件状态机的所有死锁和隐蔽 Bug。 |
| **Reagent / re-frame** | 纯函数组件与单向数据流 | **高可行性 (95%)**<br>通过 `ContextVar` 实现渲染时的依赖收集。利用已有的 `ComputedSignal` 实现 re-frame 的 `reg_sub` 与 `reg_event`。 | **Python 唯一的响应式纯函数组件**。结构简单干净，AI Agent 生成此类组件的成功率接近 100%。 |

---

## 三、 重新编排的全景路线图

```
+-------------------------------------------------------+
|  Phase 0 (v0.1.0): 已完成的框架核心 ✅                  |
|  - Signal / ComputedSignal / Effect / batch            |
|  - Hiccup DSL + Renderer + DiffEngine                  |
|  - Component / @server / ActionRef / BoundAction        |
|  - Transport (HTTP, SSE, WebSocket)                    |
|  - Session / SessionStore / EventBus / Router          |
|  - FormValidator (基础版)                               |
+---------------------------+---------------------------+
                            |
              +-------------+-------------+
              |                           |  [可并行推进]
              v                           v
+-----------------------------+  +-----------------------------+
|  Phase 1 (v0.2.0):          |  |  Phase 2 (v0.3.0):          |
|  HMR + hREPL 开发体验       |  |  hiccl.spec 契约系统        |
|  - DOM 级热重载引擎          |  |  - 声明式 Spec DSL          |
|  - hREPL 网络 REPL 服务器    |  |  - @server 边界验证          |
|  - hREPL 安全分层机制        |  |  - Redis SessionStore       |
|  - 性能基准测试              |  |  - EventBus 通配符主题       |
+-------------+---------------+  +-------------+---------------+
              |                                |
              v                                |
+-----------------------------+                |
|  Phase 3 核心 (v0.4.0):      |                |
|  纯函数组件 + re-frame        |                |
|  - use_signal (FP 组件)     |                |
|  - re-frame (reg_sub/event) |                |
|  - hiccl.testing 测试工具    |                |
+-------------+---------------+                |
              |                                |
              +---------------+----------------+
                              |
                              v
+-------------------------------------------------------+
|  Phase 3 增强 (v0.4.1): Spec 契约结合                 |
|  - Spec × Hypothesis 生成式测试                        |
|  - 契约式自愈与错误边界                                |
+---------------------------+---------------------------+
                            |
              +-------------+-------------+
              |                           |  [可并行推进]
              v                           v
+-----------------------------+  +-----------------------------+
|  Phase 4 (v0.5.0):          |  |  Phase 5a (v0.6.0):         |
|  CSP Channel + Transducers  |  |  Signal.with_history()      |
|  - put/get/close/alts_      |  |  - 不可变状态快照            |
|  - Transducer 渲染中间件     |  |  - 撤销/重做/时间旅行       |
|  - 背压控制与高阶流程 DSL    |  |  - Chrome DevTools 面板     |
+-----------------------------+  +-------------+---------------+
                                              |
                                              v  [可选独立子项目]
                                 +-----------------------------+
                                 |  Phase 5b (v0.7.0):         |
                                 |  Datalog-lite 查询引擎       |
                                 |  - EAVT 索引结构             |
                                 |  - 声明式查询 DSL            |
                                 |  - 可作为永久的独立 repo      |
                                 +-----------------------------+
```

---

## 四、 组件模型设计：纯函数组件与类组件的共存策略

> [!IMPORTANT]
> **在 Phase 3 开始前必须明确的架构决策**
> 当前框架的 `Component` 是一个 OOP 基类，深度绑定了 `@server`、`ActionRef`、`BoundAction`、`component_id`、生命周期 (`mount`/`unmount`) 等机制。Phase 3 计划引入 Reagent 风格的纯函数组件。两者的共存规则如下：

### 设计原则：展示层 FP + 状态层 OOP

| 维度 | 纯函数组件 (`@component`) | 类组件 (`class X(Component)`) |
|:---|:---|:---|
| **定位** | 展示 + 事件转发（View Layer） | 有状态 + `@server` 方法的业务容器 |
| **状态管理** | `use_signal()` 闭包捕获（仅限本地 UI 状态） | `self.signal_name`（拥有完整生命周期管理） |
| **服务端方法** | ❌ 不支持 `@server`（通过 `dispatch()` 走 re-frame 事件流） | ✅ 支持 `@server` 方法 |
| **生命周期** | 无 `mount`/`unmount`（由渲染上下文自动管理） | 完整的 `mount` → `render` → `unmount` |
| **适用场景** | 纯 UI 展示、列表项、卡片、表单控件 | 需要 `@server` 交互的业务组件（聊天室、编辑器） |
| **Signal 清理** | 由框架的渲染上下文 (`ContextVar`) 在组件卸载时自动清理，**防止闭包泄漏** | 由 `unmount()` 显式清理 |

### 纯函数组件的声明方式

```python
from hiccl import component, use_signal, dispatch
from hiccl.hiccup import div, button, span

@component
def Counter(initial_count: int = 0):
    """纯展示组件：只负责渲染和转发事件"""
    count = use_signal(initial_count)

    return div({"class": "flex gap-2 items-center"},
        button({"on_click": lambda: count.set(count.get() - 1)}, "-"),
        span(count.get()),
        button({"on_click": lambda: count.set(count.get() + 1)}, "+"),
        # 需要服务端交互时，通过 dispatch 走 re-frame 事件流
        button({"on_click": lambda: dispatch("save-count", count.get())}, "保存")
    )
```

### 类组件的保留用法

```python
class ChatRoom(Component):
    """有状态业务组件：拥有 @server 方法和完整生命周期"""
    def __init__(self):
        super().__init__()
        self.messages = signal([])

    @server
    def send_message(self, text: str):
        self.messages.set([*self.messages.get(), {"text": text}])

    def render(self):
        return div(...)
```

> [!WARNING]
> **关键约束**：纯函数组件内部的 `use_signal()` 创建的 Signal **不可**被外部直接引用。如果需要跨组件共享状态，必须通过 re-frame 的 `reg_sub` / `reg_event` 或类组件的 `@server` 方法。这条规则防止了 Signal 的生命周期泄漏问题。

### 🔄 向后兼容承诺与平滑迁移路径

#### 1. 兼容承诺 (Compatibility Commitment)
- **类组件的支持生命周期**：`class X(Component)` 风格的类组件是 Hiccl 的核心奠基模型，**在 v1.0.0 之前绝对不会被废弃**。
- **混合使用支持**：在同一个页面或应用中，允许类组件和纯函数组件**无缝混合嵌套**。例如，一个类组件的 `render()` 方法中可以调用纯函数组件，反之亦然。

#### 2. 类组件 → 纯函数组件迁移指南 (Migration Map)

当用户决定将旧有的类组件重构为更轻量、更利于 AI 自动生成的纯函数组件时，可以参考以下对照映射表进行平滑迁移：

| 机制 / 功能 | 类组件实现方式 (`class`) | 纯函数组件实现方式 (`@component`) | 迁移要点与说明 |
|:---|:---|:---|:---|
| **组件声明** | `class Counter(Component):` | `@component def Counter(initial_val=0):` | 类属性/入参变为函数的参数。 |
| **局部 UI 状态** | `self.count = signal(0)` | `count = use_signal(0)` | 局部状态转换为闭包捕获的 `use_signal`。 |
| **局部状态修改** | `self.count.set(self.count.get() + 1)` | `count.set(count.get() + 1)` | 句法基本一致，省去 `self.` 引用。 |
| **服务端行为** | `@server def save(self, data): ...` | ❌ 不直接支持 `@server`<br>✅ 配合 re-frame: `dispatch("save-data", data)` | 将逻辑移动到全局或模块级 `reg_event` 事件处理器中，实现 UI 与副作用解耦。 |
| **数据订阅** | `self.computed = computed(...)` | `computed_val = computed(lambda: count.get() * 2)`<br>或 `sub = subscribe("some-sub")` | 既可以使用局部 `computed`，也可以通过 `subscribe` 订阅 re-frame 的派生状态树。 |
| **生命周期拦截** | 重写 `mount(self)` / `unmount(self)` | 借助 `Effect` 的清理函数：<br>`@effect\ndef _():\n    # mount 逻辑\n    return lambda: print("unmounted")` | 函数组件生命周期与依赖它的 `Effect` 深度绑定，当组件销毁时，`Effect` 返回的清理函数会自动执行。 |

---

## 五、 深度思辨：HMR 与 hREPL 的互补关系

> [!IMPORTANT]
> **💡 HMR（自动热重载）与 hREPL（网络交互式开发）的本质区别**
> - **HMR (Hot Module Replacement)** 解决的是 **"文件到浏览器的被动流动"**。当你在编辑器保存文件时，系统自动重载整个文件，重新渲染 DOM。
> - **hREPL (Hiccl Network REPL)** 解决的是 **"代码到运行中进程的主动交互与内省"**。它是一个网络套接字（Socket）服务，允许外部编辑器或 **AI Agent** 建立持久连接，直接在"活"的服务器进程中动态执行代码片段。

### 1. 为什么 HMR 无法取代 REPL？

在 Python 传统的 Web 开发中，调试 WebSocket 或异步协程程序非常痛苦。如果使用普通的断点（`breakpoint()`），会**直接冻结整个 `asyncio` 事件循环**，导致 WebSocket 瞬间断连。而 **hREPL** 运行在独立的非阻塞网络协程中：

*   **真正的"热手术刀"式求值**：不需要保存整个文件，只需在编辑器中选中一个方法，按下快捷键，hREPL 会**单点重新编译并覆盖内存中该类的方法**，不影响已连接用户的 WebSocket 会话。
*   **状态的运行时探索 (Introspection)**：可以在 REPL 中直接检索当前活动连接的 `Session` 实例，实时读取甚至修改某个在线用户的 Signal 状态。
*   **AI Agent 的完美"指令通道"**：AI 可以直接通过 hREPL 动态发送一小段诊断 Python 脚本，读取 Signals 依赖链路，或在内存中重定义方法并运行测试。

### 2. hREPL 的安全分层设计

> [!CAUTION]
> **安全风险**：hREPL 允许外部通过 Socket 连接在服务器进程中**任意执行 Python 代码**。如果不加以限制，生产环境中的 hREPL 端口被暴露将导致服务器完全沦陷。

hREPL 必须在设计阶段就内置安全分层机制：

| 安全层 | 措施 | 说明 |
|:---|:---|:---|
| **硬开关** | `HREPL_ENABLED=true` 环境变量 | 默认 `false`，**生产环境必须完全禁用** |
| **网络隔离** | 默认仅监听 `127.0.0.1` | 绝不默认绑定 `0.0.0.0`，本地开发限定 localhost |
| **认证** | 可选的 shared secret / token | 启动时随机生成 token 并打印到 stdout，客户端连接时必须提供 |
| **沙箱（可选）** | 限制可访问 of `globals` 范围 | 高安全场景下，排除 `os`、`subprocess` 等危险模块 |
| **审计日志** | 所有 eval 请求记录到日志文件 | 便于事后追溯，发现异常行为 |

#### 服务端核心代码草案：

```python
# hiccl/repl/server.py 内部设计
import asyncio
import json
import os
import secrets
import traceback

class HReplServer:
    def __init__(self, host="127.0.0.1", port=8998, app_state=None):
        self.host = host
        self.port = port
        self.token = os.environ.get("HREPL_TOKEN") or secrets.token_urlsafe(32)
        # 共享活动应用的全局上下文
        self.globals = {"app_state": app_state, "hiccl": __import__("hiccl")}

    async def start(self):
        if not os.environ.get("HREPL_ENABLED", "").lower() in ("true", "1"):
            return  # 硬开关：未显式启用则完全不启动
        self.server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        print(f"[hREPL] Server started on {self.host}:{self.port}")
        print(f"[hREPL] Auth token: {self.token}")

    async def _handle_client(self, reader, writer):
        # 认证握手
        auth_data = await reader.readline()
        auth_req = json.loads(auth_data.decode("utf-8"))
        if auth_req.get("token") != self.token:
            writer.write(json.dumps({"status": "error", "error": "Unauthorized"}).encode() + b"\n")
            await writer.drain()
            writer.close()
            return

        writer.write(json.dumps({"status": "ok", "message": "Authenticated"}).encode() + b"\n")
        await writer.drain()

        while True:
            try:
                data = await reader.readline()
                if not data:
                    break

                req = json.loads(data.decode("utf-8"))
                code_to_eval = req.get("code")

                # 审计日志
                self._audit_log(code_to_eval)

                result = await self._eval_async(code_to_eval)

                writer.write(json.dumps({"status": "ok", "value": repr(result)}).encode() + b"\n")
                await writer.drain()
            except Exception as e:
                err = traceback.format_exc()
                writer.write(json.dumps({"status": "error", "error": err}).encode() + b"\n")
                await writer.drain()

    def _audit_log(self, code):
        # TODO: 记录到结构化日志文件
        pass

    async def _eval_async(self, code):
        # 内部使用定制的异步编译执行
        pass
```

### 3. hREPL 的交互协议

hREPL 将基于异步 TCP Socket 实现，采用 JSON-RPC 协议通信。

> [!TIP]
> **技术选型说明**：选择 JSON-RPC 而非 nREPL 的 Bencode 协议，原因：(1) JSON 在 Python 生态中有 `orjson` 等高性能实现；(2) AI Agent 和 IDE 插件对 JSON 的支持远优于 Bencode；(3) 降低第三方集成的门槛。如果社区后续有 Bencode 需求，可以作为可选的传输编码层加入。

#### AI Agent 交互示例：

```json
// 1. 认证握手
{"token": "abc123..."}
// → {"status": "ok", "message": "Authenticated"}

// 2. 状态查询
{"code": "list(app_state['session_store']._local._sessions.values())[0]._components['chatroom-abc'].messages.get()"}
// → {"status": "ok", "value": "[{'user': 'Me', 'text': 'Hello'}]"}
```

---

## 六、 基于现成 Diff 引擎的极速 DOM 级热重载（HMR Live Reload）

> [!IMPORTANT]
> **💡 架构突破：用极低成本实现 DOM 级的热重载（HMR）**
> 在 Hiccl 中，我们完全可以**利用现有的 Signal 状态层、WebSocket 实时推送管道以及强大的 Diff 引擎，实现一套纯 Python 的、极速的 DOM 级热重载系统，且绝对能做到"状态不丢失"！**

### 1. 技术实现原理解析

Hiccl 具有天然的 **"状态与 UI 渲染代码分离"** 的优良架构：
- 组件的**运行状态**完全被存储在 `Signal` 实例中（由 `Session` 在服务端内存中持有）。
- 组件的 **UI 表达**完全是一个声明式的纯函数/方法（`render()`），它仅从 `Signal` 中拉取值进行渲染。

当开发者（或 AI 协作）在本地编辑了某组件的 `render()` 代码时：
1. **文件监视器（Watchfiles）** 在后台线程捕捉到 `.py` 源码变更。
2. 动态加载模块（使用 `importlib.reload`），并将重新定义后的类/函数重新注入 `ComponentRegistry`。
3. **关键点（状态保留）**：服务端**不重启进程**，也不重置 `Session`！活动 Session 中的组件实例的 `_signals` 依然保留着当前的内存值。
4. 服务端遍历活动 Session 中对应的组件实例，将其类属性更新为重载后的类（`comp.__class__ = reloaded_class`），并触发一次 `mark_dirty()`。
5. **基于 Diff 引擎计算 DOM 补丁**：
   - 渲染器调用重载后的新 `render()` 方法，结合内存中已有的 Signal 状态值，生成全新的 Hiccup 树，并编译为新的 HTML。
   - 渲染器拉取缓存中的**旧 HTML 字符串**与**新 HTML 字符串**。
   - 将两者传入 `DiffEngine`，生成最小增量补丁（Patch）。
   - 将最小补丁通过现成的 WebSocket 推送到前端。
6. 前端 `hiccl.js` 接收补丁，通过 HTMX 的 swap 机制将变动部分进行**就地更新**。
7. **最终效果**：浏览器页面完全不刷新，WebSocket 连接不中断，组件的运行状态完好无损，但 UI 已经秒级变成了最新的代码设计！

> [!TIP]
> **技术选型说明 — `watchfiles`**：选择 `watchfiles`（基于 Rust 的 `notify`）而非 `watchdog`，原因：(1) 跨平台一致性更好（macOS FSEvents / Linux inotify / Windows ReadDirectoryChanges 统一抽象）；(2) Rust 实现的性能远优于纯 Python；(3) API 更简洁，与 asyncio 集成更自然。

```python
# live_reload/watcher.py 内部机制演示
from importlib import reload
import sys

def on_source_changed(file_path):
    # 1. 重新导入修改过的 Python 模块
    module_name = get_module_name(file_path)
    reloaded_module = reload(sys.modules[module_name])

    # 2. 从重载模块提取最新组件定义并更新注册表
    new_comp_cls = getattr(reloaded_module, "MyCounter")
    registry.update("my-counter", new_comp_cls)

    # 3. 遍历活动 session 并应用热重载 (保留 Signal 状态)
    for session in active_sessions:
        for comp in session.list_components_by_type("my-counter"):
            # 动态替换类指针，保留内部 _signals 数据
            comp.__class__ = new_comp_cls

            # 4. 触发局部脏组件重绘并推送到 DiffEngine 进行 Patch 提取
            session.schedule_render(comp)
```

---

## 七、 详细阶段分解与核心实现设计

### 📅 Phase 0 —— 已完成的框架核心 (v0.1.0) ✅

**当前已交付物清单**：

| 模块 | 文件 | 状态 |
|:---|:---|:---|
| Signal 响应式系统 | `signal.py` | ✅ Signal, ComputedSignal, Effect, batch |
| Hiccup DSL | `hiccup.py` | ✅ 声明式 HTML 构建 |
| Renderer | `renderer.py` | ✅ Hiccup → HTML 编译 |
| DiffEngine | `diff.py` | ✅ 增量 DOM 补丁生成 |
| Component 系统 | `component.py` | ✅ OOP 基类, @server, ActionRef, BoundAction |
| Transport 层 | `transport/` | ✅ HTTP, SSE, WebSocket |
| Session 管理 | `session.py`, `session_store.py` | ✅ 基本实现 (内存存储) |
| EventBus | `eventbus.py` | ✅ 基础发布/订阅 |
| FormValidator | `validator.py` | ✅ 基础验证 (非 Spec DSL) |
| Router | `router.py` | ✅ 客户端路由 |
| Registry | `registry.py` | ✅ 组件注册表 |
| App 入口 | `app.py` | ✅ FastAPI 集成 |

---

### 📅 Phase 1 —— HMR Live Reload + hREPL 交互式开发 (v0.2.0)

*   **核心目标**：让开发者（和 AI Agent）获得**即时反馈**的极致开发体验。这是对外演示和吸引早期用户最关键的特性。
*   **前置依赖**：仅依赖 Phase 0 已有的 DiffEngine、WebSocket Transport 和 Session 系统。**不依赖 Spec**。

#### 1. HMR 极速 DOM 热重载引擎
详见第六章的完整技术设计。核心交付物：
- `hiccl/live_reload/watcher.py` — 基于 `watchfiles` 的 file 监控器
- `hiccl/live_reload/reloader.py` — 模块重载与类指针替换引擎
- 开发模式 CLI 启动参数：`hiccl dev --live-reload`

#### 2. hREPL (Hiccl Network REPL)
详见第五章的完整技术设计与安全分层。核心交付物：
- `hiccl/repl/server.py` — 异步 TCP Socket 服务器
- `hiccl/repl/protocol.py` — JSON-RPC 请求/响应协议
- `hiccl/repl/security.py` — 认证、审计日志、沙箱（可选）
- 开发模式 CLI 启动参数：`HREPL_ENABLED=true hiccl dev`

#### 3. 性能基准测试
- 建立 `benchmarks/` 目录，针对 Signal 更新延迟、Diff 计算耗时、端到端渲染时间进行基准测试。
- 对标 Streamlit / NiceGUI / Gradio 的同等场景。

---

### 📅 Phase 2 —— `hiccl.spec` 契约系统与生产化基石 (v0.3.0)

*   **核心目标**：为框架注入运行时契约验证层，补齐 Redis 会话存储等生产化短板。
*   **前置依赖**：仅依赖 Phase 0。**可与 Phase 1 并行推进**。
*   **定位**：Spec 是对已有框架核心的**安全加固层**，而非地基。这意味着 Spec 的引入不应要求对现有 API 进行破坏性重构，而是以**装饰器增强**的方式渐进式嵌入。

#### 1. 声明式 `hiccl.spec` 契约系统

```python
from hiccl import spec

# 定义一个标准的 UserSpec 契约
UserSpec = spec.keys(
    req={
        "id": spec.integer(gt=0),
        "username": spec.string(min_len=3, max_len=30),
        "email": spec.regex(r"[^@]+@[^@]+\.[^@]+")
    },
    opt={
        "roles": spec.coll_of(spec.string(), min_len=1)
    }
)
```

- **Explain Data 报错自愈机制**：Spec 校验失败时，提供结构化的异常数据（包含报错路径、不合规值、所违背的谓词规则）。这使得 AI Agent 能够精准地解析运行错误，不需要人类介入即可修正代码。

> [!TIP]
> **技术选型说明 — 底层引擎**：`hiccl.spec` 的底层验证引擎可选方案：
> - **方案 A：自研轻量引擎**（推荐）— 完全掌控 `explain-data` 的输出结构，与 Clojure spec 语义一致，约 500–800 行 Python。
> - **方案 B：`Pydantic` 桥接** — 利用 Pydantic 的解析能力，但 `explain-data` 的输出格式需要额外适配层。
> - **选型理由**：推荐方案 A。Pydantic 的错误模型（`ValidationError`）与 Clojure spec 的 `explain-data` 在结构上差异较大，桥接成本不亚于自研。

#### 2. `@server` 方法边界契约验证

将 Spec 无缝融入 `@server` 装饰器中，保证客户端请求进入服务器方法时的安全：

```python
class ProfileEditor(Component):
    def __init__(self):
        super().__init__()
        self.user_info = signal({})

    @server(spec={"args": {"data": UserSpec}, "return": spec.boolean()})
    def update_profile(self, data: dict):
        self.user_info.set(data)
        return True
```

#### 3. Redis SessionStore 与生产级重构

- 引入连接池管理（`ConnectionPool`）与断线重连指数退避。
- **状态压缩序列化**：使用 `orjson` 或 `msgpack` 代替标准 JSON。
- 支持 Session 的**悲观锁/乐观锁机制**，避免高频并发 WebSocket 写入导致状态覆盖。

> [!TIP]
> **技术选型说明 — 序列化格式**：
> - **`orjson`**（推荐用于 HTTP/调试场景）— 输出人类可读的 JSON，性能已极优（比标准库快 10x），便于 hREPL 和日志审查。
> - **`msgpack`**（推荐用于 Redis 存储）— 二进制格式，比 JSON 节省 30-50% 空间，Redis 内存占用更低。
> - **选型理由**：两者并用。Redis 存储用 msgpack 优化空间；HTTP 传输和调试输出用 orjson 保持可读性。

#### 4. EventBus 增强与离线打包
- **通配符主题支持**：允许订阅 `chat.*`，实现事件的层次化分发。
- **静态资源全量离线打包**：发布 `hiccl[full]` 安装选项。将前端依赖统一封装进 Python Package 的 `package_data` 中，支持物理隔离环境部署。

---

### 📅 Phase 3 核心 —— Reagent 纯函数组件 + re-frame 订阅系统 (v0.4.0)

*   **核心目标**：引入函数式编程美学，从 OOP 降维到 FP，让 UI 渲染与数据流彻底解耦，并提供轻量级组件单元测试能力。
*   **前置依赖**：仅依赖 Phase 1（HMR 热重载支持）。**不依赖 Phase 2 (Spec)**。

#### 1. Reagent 风格纯函数组件
利用 `ContextVar` 实现全局渲染跟踪器。纯函数组件不再继承 `Component` 类。共存与生命周期绑定机制详见第四章。

#### 2. re-frame 订阅树层（Unidirectional Data Flow）
在大型复杂应用中，直接维护零散的 `Signal` 会导致数据更新拓扑混乱。引入 `re-frame` 的 `reg_sub` 与 `reg_event`：

```python
import hiccl

# 1. 注册全局初始状态
hiccl.reg_state({"todos": [], "filter": "active"})

# 2. 注册派生数据订阅
@hiccl.reg_sub("filtered-todos")
def sub_filtered_todos(db):
    todos = db.get("todos")
    filter_ = db.get("filter")
    return [t for t in todos if filter_ == "all" or t["status"] == filter_]

# 3. 注册纯函数事件处理函数 (实现强一致的单向数据流动)
@hiccl.reg_event("add-todo")
def event_add_todo(db, text: str):
    new_todo = {"id": len(db["todos"]) + 1, "text": text, "status": "active"}
    return {**db, "todos": db["todos"] + [new_todo]}
```

#### 3. ⚡ Signal 错误传播策略与异常边界 (Signal Error Boundary)
为防止反应式计算链中抛出的异常导致 UI 崩溃或状态死锁，Hiccl 在 Phase 3 核心中引入反应式异常边界设计：

*   **`ComputedSignal` 异常捕获**：
    当 `ComputedSignal` 的派生函数执行抛出异常时，默认行为是**将异常向下游污染/传播**，使下游计算链同步感知失败。
    为防止级联崩溃，支持在定义时传入 `fallback` 默认值或 `on_error` 注册回调：
    ```python
    safe_derived = computed(
        lambda: 10 / base_val.get(), 
        fallback=0.0,
        on_error=lambda err: print(f"计算失败: {err}")
    )
    ```
*   **`Effect` 异常边界**：
    `Effect` 处于反应式图的终点，若其中发生异常，将自动被 `Effect` 边界捕获，**不会崩溃阻塞整个 asyncio 事件循环**。
    被捕获的错误会通过 `hiccl.eventbus` 以 `hiccl.error.effect` 为主题进行广播，允许全局挂载统一的错误监控与弹窗提示（类似 React Error Boundary）。

#### 4. 🧪 `hiccl.testing` 组件单元测试工具集
无需启动 FastAPI 网页服务器，支持对组件的渲染结果及业务逻辑进行高速单元测试：

- **DOM 快照测试 (Snapshot Testing)**：
  提供 `render_to_string` 方法，允许直接输入组件和 Signal 数据，返回渲染出的原始 HTML 字符串并进行断言：
  ```python
  from hiccl.testing import render_to_string
  
  html = render_to_string(Counter(initial_count=5))
  assert "5" in html
  ```
- **服务端 Mock 夹具**：
  提供 `@mock_server` 上下文管理器，方便对类组件的 `@server` 方法进行隔离测试，拦截并伪造远程调用的返回值。
- **Signal 状态监控断言**：
  提供 `assert_signal_changes` 辅助函数，在给定的回调函数执行时，自动监控特定 Signal 是否发生了预期内的修改。

---

### 📅 Phase 3 增强 —— Spec 契约结合与生成式测试 (v0.4.1)

*   **核心目标**：将 Phase 2 的 `hiccl.spec` 契约系统深层嵌入到 Phase 3 的数据流中，实现高强度的生成式属性测试与接口自愈。
*   **前置依赖**：依赖 Phase 2（Spec 系统）与 Phase 3 核心。

#### 1. 契约式数据流验证
- 将 Spec 注册应用到 re-frame 的 `reg_event` 参数校验中：
  ```python
  @hiccl.reg_event("add-todo", spec={"args": [spec.string(min_len=1)]})
  def event_add_todo(db, text: str):
      ...
  ```
  如果 dispatch 传入非法数据，立即触发 explain 报错。

#### 2. 基于 Spec + Hypothesis 的生成式测试 (Property-based Testing)
有了 `spec` 对数据契约的严格定义，可以利用 **Hypothesis** 库，将 Spec 直接转换为生成测试数据的 Strategies，全自动运行上万次随机状态交互，发现极端并发或状态边界下的隐蔽 Bug：
```python
from hiccl.testing import given_spec
import hypothesis.strategies as st

@given_spec(TodoSpec)
def test_todo_component_invariance(todo_data):
    # Hypothesis 会自动根据 TodoSpec 生成成百上千组奇异的字典输入
    # 验证渲染与状态机永远不发生死锁或不一致错误
    ...
```

---

### 📅 Phase 4 —— core.async 并发编排与 Transducers 中间件 (v0.5.0)

*   **核心目标**：引入高阶并发哲学，用 CSP 通道控制异步协作，通过 Transducer 解耦 UI 渲染管线。
*   **前置依赖**：仅依赖 Phase 0。**可独立推进**。

#### 1. Python 纯异步 CSP Channel

基于 `asyncio.Queue` 打造功能完整的通道系统，支持多路复用：

```python
from hiccl.csp import Channel, go, alts_
import asyncio

data_chan = Channel(maxsize=1)
timeout_chan = Channel(maxsize=1)

@go
async def render_orchestrator(comp):
    while True:
        # alts_ 对应 core.async/alts!，多路复用监听
        channel, value = await alts_([data_chan, timeout(3000)])

        if channel == data_chan:
            comp.status.set(f"最新数据: {value['time']}")
        else:
            comp.status.set("连接超时，等待重试...")
```

> [!TIP]
> **技术选型说明 — `asyncio.Queue` vs 第三方**：
> 选择基于标准库 `asyncio.Queue` 自研而非 `aiostream` 或 `trio` 的 Channel，原因：(1) 零额外依赖；(2) 与 Hiccl 已有的 asyncio 事件循环无缝集成；(3) `asyncio.wait` 天然支持 `alts!` 语义的多路复用。

#### 2. 🔀 EventBus 与 CSP Channel 的职责划分 (Architectural Boundaries)

为避免开发者在"何时使用 EventBus"与"何时使用 Channel"上产生困惑，框架明确了两者的架构边界与适用场景：

| 特性 / 维度 | EventBus (事件总线) | CSP Channel (通信通道) |
|:---|:---|:---|
| **通信模式** | 广播式 (一对多, Pub/Sub) | 点对点 (一对一管道, Producer/Consumer) |
| **拓扑关系** | 解耦的多方订阅者 | 明确的有向数据管道与流向 |
| **同步/控制** | 无状态触发，不关注订阅者是否接收完毕 | **强同步/异步背压控制 (Backpressure)**，支持暂停与阻塞 |
| **典型场景** | - 广播全局性通知 ("系统即将关机", "用户已登录")<br>- 跨组件解耦通信<br>- 错误日志/全局异常分发 | - 复杂异步流程多路复用编排 (`alts_`) 为单个组件拉取数据<br>- 限流与并发度控制<br>- 管道化数据转换与清洗流水线 |
| **不适用场景** | 点对点精密管道流、高频控制流、背压控制 | 一对多广播通知 |

#### 3. Transducer 渲染中间件管线

允许开发者定义通用的 Hiccup 树变换器（Transducer），用于在输出 HTML 之前，拦截、审查或增强 DOM 节点。

> [!CAUTION]
> **不可变性约束**：Transducer 的 `transform` 方法**必须返回全新节点**，绝对禁止对输入的 node 或其 attrs dict 进行就地修改（In-place mutation），否则会导致多处引用的静态组件模板产生意外的副作用。

##### 示例：
```python
from hiccl.transducers import Transducer
import copy

class AutoloadingTransducer(Transducer):
    def transform(self, node):
        if isinstance(node, list) and len(node) > 0 and node[0] == "button":
            # 1. 深度克隆 attrs 以防不可变性被破坏
            old_attrs = node[1] if (len(node) > 1 and isinstance(node[1], dict)) else {}
            attrs = {
                **old_attrs,
                "class": old_attrs.get("class", "") + " btn-loading-indicator",
                "hx-indicator": "#global-spinner"
            }
            # 2. 返回全新的 list 节点，保持纯函数式语义
            children = node[2:] if isinstance(node[1], dict) else node[1:]
            return ["button", attrs] + children
        return node
```

---

### 📅 Phase 5a —— `Signal.with_history()` 状态快照与时间旅行 (v0.6.0)

*   **核心目标**：为 Signal 系统增加不可变快照回溯能力，实现撤销/重做与时间旅行调试。
*   **前置依赖**：仅依赖 Phase 0。**可独立推进**。
*   **定位**：这是 Datomic 愿景中**最高价值、最低风险**的子集，独立于 Datalog 查询引擎。

#### 1. `Signal.with_history()` 与状态快照

将信号底层的 `_value` 替换为不可变结构（例如 `pyrsistent.pmap`）。每次 `.set()` 不仅改变当前值，还在历史链表中增加一个节点（类似 Git Commit）：

```python
class Counter(Component):
    def __init__(self):
        super().__init__()
        self.count = signal_with_history(0, max_snapshots=50)

    @server
    def undo(self):
        self.count.undo()  # 自动回退到上一状态快照并触发局部刷新
```

> [!TIP]
> **技术选型说明 — `pyrsistent` vs 内置不可变类型**：
> - **`pyrsistent`**（推荐用于复杂嵌套状态）— 提供 `PMap`/`PVector` 等持久化数据结构，支持结构共享（structural sharing），嵌套状态的更新为 O(log n) 而非 O(n) 的深拷贝。
> - **内置 `tuple`/`frozenset`**（适用于扁平状态）— 零依赖，但不支持结构共享，深层嵌套时性能较差。
> - **选型理由**：默认使用内置类型以保持零依赖，提供 `hiccl[persistent]` 可选安装项引入 `pyrsistent`。

#### 2. 状态补丁流与可视化时间旅行
- 服务端自动记录增量 Diff（Patch Log）。
- **Chrome DevTools 插件**：开发专用的 Hiccl 面板，支持拖拽滑块控制时钟，在历史各状态中穿梭。

---

### 📅 Phase 5b —— Datalog-lite 声明式查询引擎 (v0.7.0) [可选]

> [!WARNING]
> **风险评估**：真正的 Datomic 是一个完整的分布式不可变数据库，`pyrsistent.PMap` 只是不可变数据结构的冰山一角。即使是"lite"版的 Datalog 查询引擎也涉及统一的 EAVT 索引结构，复杂度远超几百行 Python。**建议作为独立子项目（独立 repo）推进，不作为主框架 v1.0 的硬性前提。**

*   **核心目标**：将应用的状态树数据库化，支持声明式的多维检索。
*   **前置依赖**：依赖 Phase 5a 的状态快照能力。
*   **定位**：**可选的独立子项目**。对于大多数应用，简单的 `dict`/`list` 遍历配合 re-frame 订阅已经足够。Datalog 查询主要服务于**超大规模状态树的复杂关联查询**场景。

#### Datalog-lite 声明式查询

```python
# 状态即数据库：查询所有在线且未完成任务的 Todo 组件
results = app.db.query("""
    [:find ?todo-text ?assignee
     :where [?todo :type "TodoItem"]
            [?todo :status "active"]
            [?todo :text ?todo-text]
            [?todo :assignee ?assignee]]
""")
```

**替代方案**：如果 Datalog-lite 被判定为投入产出不匹配，可以用以下轻量方案替代：
- re-frame 的 `reg_sub` 链式订阅已覆盖 80% 的查询需求
- 对于剩余 20% 的复杂关联查询，提供基于 Python 生成器表达式的 `app.db.filter()` API

---

## 八、 全景安全机制与插件生态架构

在从“概念验证”走向“生产就绪”的演进中，安全防护与生态扩展能力是 Hiccl 框架必须具备的基石。

### 1. 全景安全防护设计 (Security Landscape)

| 安全维度 | 威胁描述 | 框架级防护机制与策略 |
|:---|:---|:---|
| **XSS 防护 (Cross-Site Scripting)** | 恶意用户输入脚本通过渲染管线注入 DOM 并执行 | - **默认自动转义**：Hiccup → HTML 编译渲染时，对所有字符串节点默认进行 HTML 转义。<br>- **显式逃逸**：仅在显式调用 `hiccl.hiccup.raw(html_str)` 时允许直接注入未转义 HTML，强制开发者意识到注入风险。 |
| **CSRF 防护 (Cross-Site Request Forgery)** | 第三方恶意站点伪造客户端向 `@server` 端发起操作请求 | - **Token 自动注入与验证**：在 HTTP POST / WebSocket 连接握手时自动注入并校验一次性 CSRF Token。<br>- **WebSocket 源校验**：强制限制连接的 `AllowedOrigins`，阻止未经授权的跨域 WebSocket 握手。 |
| **Signal 状态隔离 (Session Isolation)** | 不同用户的浏览器 Session 共享同一块内存状态，导致隐私泄漏 | - **物理 Session 状态隔离**：每个用户 Session 在服务端由独立的 `SessionStore` 分配独立内存/Redis空间，Signal 实例挂载于 Session 上，从物理上杜绝跨会话状态泄漏与污染。 |
| **hREPL 访问控制** | 外部未经授权访问 hREPL 网络套接字导致远程代码执行 (RCE) | - **三层防御体系**：硬开关控制 + localhost 绑定 + 启动时动态生成 32 位 Token 强认证鉴权（详见第五章第 2 节）。 |

### 2. 插件生态与组件化扩展点 (Extensibility & Protocols)

Hiccl 并非紧耦合的黑盒，而是基于 `typing.Protocol` 制定了严密的接口契约，允许第三方开发者和 AI 自动编写定制扩展组件：

*   **自定义 Transport 协议**：
    继承 `hiccl.protocols.Transport`，可实现自定义协议传输层（例如针对 IoT 设备定制的超轻量化 MQTT 传输层）。
*   **自定义 SessionStore 后端**：
    继承 `hiccl.protocols.SessionStore`，可开发多种企业级数据库存储后端（如 MongoDB、PostgreSQL、DynamoDB，默认已规划 Redis 与内存）。
*   **自定义 Transducers 中间件**：
    实现 `hiccl.transducers.Transducer` 接口，可编写各类 DOM 过滤器（例如自动将敏感词过滤的 `ShieldingTransducer`，或自动附加性能检测属性的 `PerfTransducer`）。
*   **自定义 Spec 验证逻辑**：
    支持向 `hiccl.spec` 注册用户自定义的复合类型校验器，以便支持特定行业标准（例如地理信息 GIS 坐标验证）。

---

## 九、 竞品对比与核心商业叙事

> [!NOTE]
> 以下对比表严格区分**已实现**和**计划中**的特性。未实现的特性标注为"计划中"，避免过度承诺。当已实现特性累积足够的 benchmark 数据后，将补充具体的性能数字。

| 维度 | NiceGUI / Gradio | Streamlit | **Hiccl** | 实现状态 |
| :--- | :--- | :--- | :--- | :--- |
| **响应式粒度** | 粗粒度 / 事件回调驱动 | 极粗粒度 / 每次交互全量脚本重算 | **细粒度 Signal + Effect + 局部 DOM 补丁** | ✅ 已实现 |
| **UI 更新方式** | 整体组件重渲染 | 全脚本重算 | **增量 Diff 补丁推送** | ✅ 已实现 |
| **服务端交互模型** | 事件回调 | 无（全脚本顺序执行） | **@server 装饰器 + ActionRef** | ✅ 已实现 |
| **传输协议** | WebSocket | HTTP Long-Polling | **HTTP + SSE + WebSocket 三协议可选** | ✅ 已实现 |
| **热重载 (HMR)** | 重启整个后台服务器进程 | 重启整个 Python 脚本 | **DOM 级 HMR，运行状态 100% 保留** | 🔜 计划中 (v0.2.0) |
| **运行时 REPL** | 无 | 无 | **内置非阻塞 hREPL + 安全分层** | 🔜 计划中 (v0.2.0) |
| **运行时契约验证** | 无 | 无 | **hiccl.spec 契约 DSL + explain-data** | 🔜 计划中 (v0.3.0) |
| **AI 代理协作友好度** | 中等 | 中等 | **Spec 契约 + 结构化报错 + hREPL 直连** | 🔜 计划中 |
| **复杂状态管理** | 弱（手写回调） | 极弱（`session_state` 字典） | **Reagent use_signal + re-frame 单向数据流** | 🔜 计划中 (v0.4.0) |
| **异步/并发编排** | 原生 Task + 简单 EventBus | 难以进行长连接异步交互 | **CSP Channel + alts! 多路复用** | 🔜 计划中 (v0.5.0) |
| **状态回溯与调试** | 不可逆的就地修改 | 每次重算都是全新状态 | **不可变快照 + 时间旅行** | 🔜 计划中 (v0.6.0) |

---

## 十、 路线图推进与验证方案

### 1. 代码质量目标

| 指标 | 目标值 | 说明 |
|:---|:---|:---|
| **代码覆盖率** | ≥ 85% | 核心模块（Signal, Renderer, DiffEngine, Spec）要求 ≥ 95% |
| **Signal 更新延迟** | < 0.1ms | CI 中设置性能回归断言 |
| **Diff 计算耗时** | < 1ms（中等复杂度 DOM） | benchmark 回归测试 |
| **Python 版本支持** | 3.11 / 3.12 / 3.13 | CI 矩阵测试 |

### 2. 自动化质量验证（Automated Tests）

- **hREPL 动态执行与状态捕获测试**：模拟客户端通过 Socket 连入，发送求值代码，动态重定义某个组件的 Action 函数，并在 Session 中验证新方法是否生效。
- **HMR 状态无损回归测试**：模拟加载组件，改变状态信号值，动态热替换其 render 属性，断言状态在 HTML Patch 重组后依旧精确保持原有数值。**增加并发安全测试**：多个文件同时变更时的行为验证。
- **Spec 边界与安全性测试**：每次提交均通过 pytest 执行，保证对于非法输入，Spec 抛出的 `Conformance Report` 保持绝对准确。
- **信号一致性测试**：每当引入不可变状态或 functional components，均需运行 `tests/test_signal.py`，确保性能在 0.1ms 内，依赖关系不发生死锁或内存泄露。
- **并发压力测试**：对于 Phase 4 中的 CSP，运行并发竞争测试，保证在高频并发 put/get/alts 下不丢失任何消息，且背压机制正常生效。
- **性能回归测试**：在 CI 中设置性能断言（Signal 更新 < 0.1ms, Diff 计算 < 1ms），防止重构引入性能退化。

### 3. 真实应用演示（Manual Verification）

在每个大阶段发布时，重构 `examples/combined_app.py`：
- **Phase 1 验证**：现场演示不重启服务器、不重新加载页面、100% 保留数据的 HMR 热重载。通过外部 IDE 向 hREPL 端口发送代码，动态修改组件文案并在浏览器端瞬间反应。
- **Phase 2 验证**：将 `Counter` 和 `ChatRoom` 重构为带有 **Spec 契约约束**的组件，演示非法输入时的结构化错误报告。
- **Phase 3 验证**：使用纯函数组件重写 UI 层，演示 re-frame 事件流的完整生命周期。
- **Phase 4 验证**：在 `TwoClocks` 中增加 `CSP Network Simulator`，通过 Channel 模拟具有延迟、丢包和背压的真实网络。
- **Phase 5a 验证**：在顶栏菜单中注入 **"Time Travel 拖拽滑块"**，用户可以拖动滑块倒流时间，见证所有组件退回历史状态。

---

## 十一、 文档与开发者体验（DX）跟踪

> [!IMPORTANT]
> 文档和开发者体验是框架成功的另一半。以下跟踪项贯穿所有 Phase，确保每个里程碑发布时都有配套的文档。

| 阶段 | 文档交付物 |
|:---|:---|
| **v0.1.0** (Phase 0) | README + 基础安装指南 + examples/ 示例 |
| **v0.2.0** (Phase 1) | HMR 使用教程 + hREPL 连接指南 + IDE 插件配置文档 |
| **v0.3.0** (Phase 2) | Spec DSL API Reference + 契约编写最佳实践 + 迁移指南（给现有组件加 Spec） |
| **v0.4.0** (Phase 3 核心) | 纯函数组件 vs 类组件选择指南 + re-frame 教程 + 组件设计模式 + `hiccl.testing` 使用说明 |
| **v0.4.1** (Phase 3 增强) | Spec 结合 Hypothesis 生成式测试实战 + 异常边界处理最佳实践 |
| **v0.5.0** (Phase 4) | CSP Channel 教程 + Transducer 编写指南 + EventBus 职责对比指南 |
| **v0.6.0** (Phase 5a) | 时间旅行调试教程 + DevTools 安装指南 |
| **v1.0.0** | 完整 API Reference + 架构设计文档 + 贡献指南 + Changelog + 全景安全规范与插件开发手册 |

### 文档基础设施

- 使用 **MkDocs Material** 构建文档站点（选型理由：Python 生态标配，Markdown 原生支持，主题美观）
- 代码示例使用 **doctest** 保持与实际 API 同步
- 每个 PR 必须包含对应的文档更新（CI 检查）

---

> [!IMPORTANT]
> **路线图的执行原则：**
> 1. **DX 最优先**：将对开发者体验影响最大的特性（HMR、hREPL）置于最高优先级，让框架尽快产出可演示、可感知的成果。
> 2. **Spec 加固层**：契约系统作为"安全加固层"在核心稳定后引入，以装饰器增强的方式渐进式嵌入，不要求对现有 API 进行破坏性重构。
> 3. **渐进式演进与复用**：热重载（HMR）与 hREPL 深度复用框架已有的细粒度状态、双向通信通道以及高性能局部 Diff 引擎。
> 4. **诚实评估与风险控制**：对高风险特性（Datalog-lite）设置明确的边界和退出机制，不为了对标 Clojure 生态的每一个概念而过度设计。
> 5. **文档同步交付**：每个里程碑发布时，必须有配套的文档和迁移指南。
