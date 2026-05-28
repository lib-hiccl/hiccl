# Hiccl — 全栈反应式 Python Web 框架 🧪🥒

<p align="center">
  <strong>基于 Hiccup 声明式 DSL 表达与 Pythonic 状态序列化流动的现代化 Web 框架</strong>
</p>

<p align="center">
  <a href="#-设计理念">设计理念</a> •
  <a href="#-核心特性">核心特性</a> •
  <a href="#-快速上手">快速上手</a> •
  <a href="#-架构设计">架构设计</a> •
  <a href="#-极速离线体验">极速离线体验</a>
</p>

---

## 🎨 命名与设计理念

**Hiccl**（读作 `/ˈhɪk.l̩/`，“Hick-le”）是 **Hiccup** 与 **Pickle** 的灵魂结晶：

*   **Hiccup**：继承了 Clojure 的高贵血统。在 Hiccl 中，你不必编写任何 HTML 样板，全部 DOM 结构都可以用极其优雅的 Python 嵌套列表与数据结构（DSL）声明式表达。
*   **Pickle**：散发着浓郁的 Pythonic 风味。代表着组件状态（State/Signal）的自动追踪与生命周期持久化。组件的状态随连接会话建立而自动管理，并通过极速的网络传输机制实现增量更新（Diff Patch）。

**Hiccl** 让 Clojure 式极简的声明式 UI 设计与 Pythonic 的全栈反应式交互在 FastAPI 上完美绽放！

---

## ⚡️ 核心特性

*   **⚡️ 100% 声明式组件**：仅用嵌套 Python 列表（Hiccup）描述 UI，框架自动将 `on_click` 等事件绑定转化为底层的高能网络动作，没有繁琐的 AJAX/Fetch 胶水代码。
*   **🔌 双向反应式状态**：基于 `Signal` 和 `Effect`，任何状态改变都会在服务端自动生成新的虚拟 DOM 并计算最小 Diff 补丁，通过 WebSockets 或 SSE（服务器发送事件）实时推送至前端。
*   **🎨 内置 DaisyUI & TailwindCSS**：默认集成顶级暗色调毛玻璃组件库（DaisyUI）和原子化样式（TailwindCSS），开箱即用构建极其现代、高级的用户界面。
*   **🌿 Alpine.js 客户端加速**：完全移除传统的 Hyperscript，深度整合 Alpine.js，支持以标准的 HTML 属性在浏览器端运行极速的交互渲染（如每秒 60 帧的高频计时器与毫秒级时差偏差计算）。
*   **📦 100% 离线与内网就绪（Air-gapped Ready）**：所有静态依赖（`tailwind.js`、`daisyui.css`、`alpine.js`、`htmx.js`）完全本地托管于 `static/` 目录下。无需任何互联网连接即可在隔离的物理内网高速运行。
*   **🔀 优雅的组件路由与自动导航菜单**：只需通过 `pages=menu(Counter, TwoClocks, ChatRoom)` 即可全自动生成对应的 kebab-case 格式路由路径与毛玻璃渐变顶栏导航。

---

## 🚀 快速上手

### 1. 简易计数器组件 (`examples/counter/app.py`)

Hiccl 组件非常清爽，毫无杂质：

```python
from hiccl import (
    Component,
    ComponentRegistry,
    HicclConfig,  # 全局配置依然保持极简
    create_hiccl_app,
    menu,
    server,
    signal,
)
from hiccl.hiccup import button, div, h2

registry = ComponentRegistry()


class Counter(Component):
    """极简的响应式计数器。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = signal(0)

    @server
    def increment(self, step: int = 1):
        if isinstance(step, str):
            step = int(step)
        self.count.set(self.count.get() + step)

    @server
    def decrement(self, step: int = 1):
        if isinstance(step, str):
            step = int(step)
        self.count.set(self.count.get() - step)

    @server
    def reset(self):
        self.count.set(0)

    def render(self):
        count = self.count.get()
        return div(
            {"class": "card w-96 bg-base-200 shadow-xl border border-base-300 mx-auto"},
            div(
                {"class": "card-body items-center text-center"},
                h2(
                    {"class": "card-title text-3xl font-extrabold mb-4"},
                    f"Count: {count}",
                ),
                div(
                    {"class": "card-actions justify-center gap-2"},
                    button(
                        {
                            "class": "btn btn-outline btn-error",
                            "on_click": self.decrement(5),
                        },
                        "-5",
                    ),
                    button(
                        {"class": "btn btn-error", "on_click": self.decrement(1)}, "-1"
                    ),
                    button(
                        {"class": "btn btn-neutral", "on_click": self.reset}, "Reset"
                    ),
                    button(
                        {"class": "btn btn-success", "on_click": self.increment(1)},
                        "+1",
                    ),
                    button(
                        {
                            "class": "btn btn-outline btn-success",
                            "on_click": self.increment(5),
                        },
                        "+5",
                    ),
                ),
            ),
        )


# 一键自动生成路由并挂载！
app = create_hiccl_app(HicclConfig(component_registry=registry, pages=menu(Counter)))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
```

---

## 🛠 架构设计

Hiccl 在架构上高度分工，每个部分各司其职，保证了全栈反应式通信的极致顺畅：

```mermaid
graph TD
    Client[浏览器/客户端] -->|htmx / WebSockets| Server[FastAPI / Starlette 服务端]
    Server -->|Session 管理| SessionStore[会话状态持久化]
    SessionStore -->|挂载渲染| VDOM[Hiccup 声明式树]
    VDOM -->|Signal 改变| DiffEngine[增量 Diff 引擎]
    DiffEngine -->|最小补丁 HTML| WSChannel[WebSocket 实时推送通道]
    WSChannel -->|自动局部置换 DOM| Client
```

1.  **Hiccup UI 引擎**：负责将 Python 列表转化为标准 HTML。渲染时，带有 `@server` 修饰器的属性（如 `on_click`）会被智能捕捉并转化为底层的网络事件。
2.  **增量 Diff 引擎**：任何服务端的 `Signal` 状态变更触发 Effect。框架仅重新渲染脏组件，计算并提取最小补丁，以最小的数据开销实时更新客户端。
3.  **多路传输层（SSE/WebSockets）**：无缝支持高频实时状态同步。

---

## 🤖 为什么 Hiccl 天生适合 AI 时代？

在 AI Agent（如 Antigravity）与 Copilot 成为核心生产力的今天，**传统的前后端分离（React/Vue + API + Backend）开发范式正在成为 AI 编写代码的沉重枷锁**。Hiccl 从底层架构上彻底消除了这一痛点：

1. **🧩 单一语言与统一心智模型**：
   - 告别在 TypeScript (前端) 与 Python (后端) 之间的频繁上下文切换。
   - 整个应用（UI、响应式状态、事件处理器）100% 采用纯 Python 声明式编写。AI 程序员只需专注在一种语言、一个类中完成全栈功能。

2. **🔌 零 API 胶水代码，杜绝接口对不齐**：
   - 无需编写任何 REST 路由、Pydantic 序列化 Schema、Axios 抓取钩子或前端 Redux 状态管理。
   - AI 只需要调用 `self.count.set(self.count.get() + 1)`，网络传输与状态同步完全由框架自动搞定，从根本上杜绝了接口不一致导致的“AI 幻觉”与联调报错。

3. **🌿 纯数据结构声明 UI (Hiccup)**：
   - Hiccl 使用声明式的 Python 数据结构表达 DOM（Hiccup DSL），规避了 HTML/JSX 标签未闭合或缩进错乱的问题。
   - LLM 极其擅长生成结构化数据（如 Python 列表与函数嵌套）。此外，纯 Python 语法让 `mypy` / `pyright` 可以秒级进行静态类型检查，AI 能够实现高精度的“测试-报错-自愈”闭环。

4. **⚡ 极致飞速的开发与自愈反馈**：
   - 去除了前端繁琐的 Vite/Webpack 打包编译链。
   - Hiccl 组件可以直接在 Python 内存中以毫秒级运行单元测试（**140 个测试仅需 0.3 秒！**）。超高速的反馈环能让 AI Agent 在几秒内完成十几次自主迭代，达到惊人的开发成功率。

---

## 📦 极速离线体验

Hiccl 天生为企业级内网而设计。只需运行以下三合一联合应用即可预览超级炫酷的多组件自动路由与极速切换：

```bash
# 启动离线三合一演示（集成 Counter, TwoClocks, ChatRoom）
python3 examples/combined_app.py
```

### 演示亮点：
1.  **DaisyUI Chat**：进入 `/chat-room` 开启高颜值多人同步聊天。
2.  **DaisyUI Stats**：进入 `/two-clocks` 查看由 Alpine.js 驱动的毫秒级系统偏差统计图表。
3.  **完全断网测试**：你可以彻底拔掉电脑网线，你会发现导航、交互、动态刷新均毫无迟滞地正常工作，所有 JS/CSS 均完全由本地静态服务器提供。

---

## 📝 授权许可

本项目采用 [MIT 许可证](LICENSE) 授权。
