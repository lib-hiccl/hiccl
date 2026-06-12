"""CSP Crypto Trader — A real-world concurrent trading simulator.

Demonstrates:
  - Asynchronous background tasks using `@go`.
  - Non-blocking CSP `Channel` with backpressure and buffer capacity visualization.
  - Multi-channel multiplexing and timeout detection via `alts_` + `timeout(ms)`.
  - Reactive sub-component state isolation to prevent high-frequency re-rendering of input elements (preventing focus reset).
  - Seamless integration of `LoadingTransducer` to automatically inject loading indicator CSS classes to interactive buttons.
  - `SanitizingTransducer` to mask sensitive API tokens or security hashes from rendering in logs.
"""

import asyncio
import random
from datetime import datetime

from hiccl import (
    Channel,
    Component,
    ComponentRegistry,
    HicclConfig,
    LoadingTransducer,
    SanitizingTransducer,
    alts_,
    create_hiccl_app,
    go,
    menu,
    server,
    signal,
    timeout,
)
from hiccl.hiccup import button, div, form, h1, h3, input_, li, p, raw, span, ul


# ---------------------------------------------------------------------------
# 1. 独立反应式子组件 (Isolated Sub-components to prevent thrashed focus)
# ---------------------------------------------------------------------------


class BtcPriceDisplay(Component):
    """Isolates high-frequency BTC price updates so the parent form doesn't re-render."""

    def __init__(self, **kwargs):
        self.btc_price = kwargs.pop("btc_price")
        super().__init__(**kwargs)

    def render(self) -> list:
        price = self.btc_price.get()
        return span(
            {"class": "text-2xl font-black text-accent font-mono"}, f"${price:,.2f}"
        )


class PortfolioDisplay(Component):
    """Isolates portfolio balance and dynamic market evaluation display."""

    def __init__(self, **kwargs):
        self.btc_balance = kwargs.pop("btc_balance")
        self.btc_price = kwargs.pop("btc_price")
        super().__init__(**kwargs)

    def render(self) -> list:
        btc = self.btc_balance.get()
        price = self.btc_price.get()
        return div(
            None,
            span({"class": "text-xl font-bold text-white font-mono"}, f"{btc} BTC"),
            div(
                {"class": "text-[10px] opacity-40 font-mono mt-1"},
                f"估值: ${(btc * price):,.2f}",
            ),
        )


class CashBalanceDisplay(Component):
    """Isolates cash balance and aggregate portfolio valuation display."""

    def __init__(self, **kwargs):
        self.cash_balance = kwargs.pop("cash_balance")
        self.btc_balance = kwargs.pop("btc_balance")
        self.btc_price = kwargs.pop("btc_price")
        super().__init__(**kwargs)

    def render(self) -> list:
        cash = self.cash_balance.get()
        btc = self.btc_balance.get()
        price = self.btc_price.get()
        return div(
            None,
            span(
                {"class": "text-xl font-bold text-primary font-mono"}, f"${cash:,.2f}"
            ),
            div(
                {"class": "text-[10px] opacity-40 font-mono mt-1"},
                f"总资产: ${(cash + btc * price):,.2f}",
            ),
        )


# ---------------------------------------------------------------------------
# 2. 交易模拟终端主组件 (Main Simulator Component)
# ---------------------------------------------------------------------------


class CryptoTrader(Component):
    """A real-time Cryptocurrency Trading Simulator powered by CSP channels."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Financial portfolio state
        # NOTE: Using leading underscore self._btc_price so that Component auto-discovery
        # ignores it on the parent component. This prevents the parent from auto-registering
        # a watch effect on it, preventing high-frequency parent re-renders.
        self._btc_price = signal(65000.0)
        self.btc_balance = signal(1.5)
        self.cash_balance = signal(100000.0)

        # Reactive system indicators
        self.trade_logs = signal([])
        self.system_status = signal("🟢 数据订阅连接正常")
        self.backpressure_warning = signal("")
        self.buffer_size = signal(0)

        # Controller flags
        self.feed_active = signal(True)

        # CSP Channels
        self.trade_queue = Channel(maxsize=3)  # Max 3 pending orders
        self.price_queue = Channel(maxsize=5)

        # Asynchronous tasks
        self.price_gen_task = None
        self.orchestrator_task = None
        self.trade_executor_task = None

        # Child sub-components
        self.price_display = None
        self.portfolio_display = None
        self.cash_display = None

    def mount(self) -> None:
        # 挂载子组件隔离频繁更新，防止文本输入框失去焦点
        # Pass self._btc_price to children where it gets bound as a public watched signal
        self.price_display = self._session.mount_component(
            "btc-price-display",
            cid=f"{self.component_id}-price-display",
            btc_price=self._btc_price,
        )
        self.portfolio_display = self._session.mount_component(
            "portfolio-display",
            cid=f"{self.component_id}-portfolio-display",
            btc_balance=self.btc_balance,
            btc_price=self._btc_price,
        )
        self.cash_display = self._session.mount_component(
            "cash-balance-display",
            cid=f"{self.component_id}-cash-display",
            cash_balance=self.cash_balance,
            btc_balance=self.btc_balance,
            btc_price=self._btc_price,
        )

        # 1. 启动价格数据源生成器 (Price Generator Loop)
        @go
        async def price_generator():
            while not self.price_queue.closed:
                if self.feed_active.get():
                    change_pct = random.uniform(-0.015, 0.015)
                    new_price = round(self._btc_price.get() * (1 + change_pct), 2)
                    try:
                        await self.price_queue.put(new_price)
                    except RuntimeError:
                        break
                await asyncio.sleep(0.5)

        self.price_gen_task = price_generator()

        # 2. 启动数据流调度中心 (alts_ Loop with timeout multi-channel multiplexing)
        @go
        async def stream_orchestrator():
            while not self.price_queue.closed:
                selected, val = await alts_([self.price_queue, timeout(1500)])
                if selected is self.price_queue:
                    if val is None:
                        break
                    self._btc_price.set(val)
                    self.system_status.set("🟢 数据订阅连接正常")
                else:
                    self.system_status.set("⚠️ 数据馈送延迟 (超时 1.5 秒无数据)")

        self.orchestrator_task = stream_orchestrator()

        # 3. 启动交易执行协程 (Trade Executor Consumer with simulated lag)
        @go
        async def trade_executor():
            while not self.trade_queue.closed:
                order = await self.trade_queue.get()
                if order is None:
                    break

                await asyncio.sleep(1.2)

                action, amount, price = order
                total_cost = amount * price

                if action == "BUY":
                    if self.cash_balance.get() >= total_cost:
                        self.cash_balance.set(
                            round(self.cash_balance.get() - total_cost, 2)
                        )
                        self.btc_balance.set(round(self.btc_balance.get() + amount, 4))
                        self._add_log(
                            f"✅ 买入成功: {amount} BTC @ ${price} (TX-SECURE-HASH: {random.randint(100000, 999999)})"
                        )
                    else:
                        self._add_log("❌ 买入失败: 现金余额不足")
                elif action == "SELL":
                    if self.btc_balance.get() >= amount:
                        self.btc_balance.set(round(self.btc_balance.get() - amount, 4))
                        self.cash_balance.set(
                            round(self.cash_balance.get() + total_cost, 2)
                        )
                        self._add_log(
                            f"✅ 卖出成功: {amount} BTC @ ${price} (TX-SECURE-HASH: {random.randint(100000, 999999)})"
                        )
                    else:
                        self._add_log("❌ 卖出失败: BTC 持仓不足")

                self.buffer_size.set(len(self.trade_queue._buf))

        self.trade_executor_task = trade_executor()

    def unmount(self) -> None:
        self.trade_queue.close()
        self.price_queue.close()
        if self.price_gen_task:
            self.price_gen_task.cancel()
        if self.orchestrator_task:
            self.orchestrator_task.cancel()
        if self.trade_executor_task:
            self.trade_executor_task.cancel()

    def _add_log(self, msg: str) -> None:
        t_str = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{t_str}] {msg} (API-KEY-SECRET: SECURE_129X0A)"
        self.trade_logs.set([full_msg] + self.trade_logs.get()[:4])

    def submit_trade(self, action: str, amount_str: str) -> None:
        """从客户端手动发起订单提交，挂载生产者 @go 任务进行背压控制。"""
        try:
            amount = float(amount_str)
        except ValueError:
            self._add_log("❌ 交易失败: 无效的交易数量")
            return

        if amount <= 0:
            self._add_log("❌ 交易失败: 数量必须大于 0")
            return

        # 🌟 方案 A：熔断丢弃/负载卸载 (Load Shedding)。若缓冲队列已满 (3/3)，直接拦截并熔断，抛弃交易以防后端协程堆积
        if len(self.trade_queue._buf) >= self.trade_queue.maxsize:
            self._add_log(
                f"❌ 提交拒绝: 交易缓冲队列已满 ({len(self.trade_queue._buf)}/3)，系统自动触发保护性熔断抛弃！"
            )
            return

        price = self._btc_price.get()
        self._add_log(
            f"📤 订单已提交: {action} {amount} BTC @ ${price}，等待区块确认..."
        )

        @go
        async def putter():
            if len(self.trade_queue._buf) >= self.trade_queue.maxsize:
                self.backpressure_warning.set(
                    "⚠️ 交易队列已满，背压启动！当前订单正在排队等待执行..."
                )

            try:
                await self.trade_queue.put((action, amount, price))
                self.backpressure_warning.set("")
                self.buffer_size.set(len(self.trade_queue._buf))
            except RuntimeError:
                self.backpressure_warning.set("")
                self._add_log("❌ 订单拦截: 交易系统已关闭")

        putter()

    # -- @server actions bound cleanly to htmx events ------------------------

    @server
    def buy_btc(self, amount: str) -> None:
        """Receive input field values from browser form POST body."""
        self.submit_trade("BUY", amount)

    @server
    def sell_btc(self, amount: str) -> None:
        """Receive input field values from browser form POST body."""
        self.submit_trade("SELL", amount)

    @server
    def toggle_feed(self) -> None:
        """Pause or restart price generation source to test alts_ timeout."""
        active = not self.feed_active.get()
        self.feed_active.set(active)
        if active:
            self._add_log("📡 行情数据订阅已重启")
        else:
            self._add_log("⏸ 行情数据订阅已暂停 (数据源将断连)")

    def render(self) -> list:
        status = self.system_status.get()
        warning = self.backpressure_warning.get()
        buf = self.buffer_size.get()
        logs = self.trade_logs.get()
        feed = self.feed_active.get()

        # Render sub-components with isolated price reactive scopes
        price_html = self._session.renderer.render_component(self.price_display)
        portfolio_html = self._session.renderer.render_component(self.portfolio_display)
        cash_html = self._session.renderer.render_component(self.cash_display)

        return div(
            {"class": "flex flex-col gap-6 w-full max-w-4xl mx-auto px-4"},
            # 顶部美化横幅
            div(
                {
                    "class": "bg-gradient-to-r from-info/20 via-primary/10 to-accent/20 p-6 rounded-3xl border border-base-300 shadow-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
                },
                div(
                    None,
                    h1(
                        {
                            "class": "text-2xl font-extrabold text-white tracking-tight flex items-center gap-2"
                        },
                        "⚡ CSP 并发加密交易模拟终端",
                    ),
                    p(
                        {"class": "text-xs text-base-content/60 mt-1"},
                        "展示 Python 中的 Clojure 优雅高并发模型：背压控制、alts_ 多路复用和 Transducers 过滤切面。",
                    ),
                ),
                div(
                    {
                        "class": "badge p-3 text-xs font-mono "
                        + ("badge-success" if "正常" in status else "badge-warning")
                    },
                    status,
                ),
            ),
            # 中间网格：行情、持仓、控制
            div(
                {"class": "grid grid-cols-1 md:grid-cols-3 gap-4"},
                # 价格统计卡 (包含隔离的价格子组件)
                div(
                    {
                        "class": "card bg-base-200 border border-base-300 shadow-xl p-4 flex flex-col justify-between"
                    },
                    div(
                        None,
                        p(
                            {"class": "text-xs font-bold opacity-50 mb-1"},
                            "📈 BTC 实时行情",
                        ),
                        raw(price_html),
                    ),
                    div(
                        {"class": "card-actions justify-end mt-4"},
                        button(
                            {
                                "class": f"btn btn-xs {'btn-warning' if feed else 'btn-success'}",
                                "hx-post": self.toggle_feed,
                            },
                            "🔌 暂停订阅数据" if feed else "📡 重启行情订阅",
                        ),
                    ),
                ),
                # 持仓统计卡 (包含隔离的持仓子组件)
                div(
                    {
                        "class": "card bg-base-200 border border-base-300 shadow-xl p-4 flex flex-col justify-between"
                    },
                    div(
                        None,
                        p(
                            {"class": "text-xs font-bold opacity-50 mb-1"},
                            "💼 资产持有 (Portfolio)",
                        ),
                        raw(portfolio_html),
                    ),
                    None,
                ),
                # 资金余额统计卡 (包含隔离的余额子组件)
                div(
                    {
                        "class": "card bg-base-200 border border-base-300 shadow-xl p-4 flex flex-col justify-between"
                    },
                    div(
                        None,
                        p(
                            {"class": "text-xs font-bold opacity-50 mb-1"},
                            "💵 现金余额 (USD)",
                        ),
                        raw(cash_html),
                    ),
                    None,
                ),
            ),
            # 背压与队列看板
            div(
                {
                    "class": "card bg-base-200 border border-base-300 shadow-xl p-4 flex flex-col gap-2"
                },
                div(
                    {"class": "flex justify-between items-center"},
                    span(
                        {"class": "text-xs font-bold opacity-60"},
                        "📦 CSP 交易执行缓冲队列 (Trade Queue Buffer):",
                    ),
                    span(
                        {"class": "text-xs font-mono text-info font-bold"},
                        f"{buf} / 3 订单暂存",
                    ),
                ),
                div(
                    {"class": "w-full bg-base-300 rounded-full h-2"},
                    div(
                        {
                            "class": "bg-info h-2 rounded-full transition-all duration-300",
                            "style": f"width: {(buf / 3.0 * 100):.0f}%",
                        }
                    ),
                ),
                raw(
                    f'<div class="alert alert-warning text-xs p-2.5 rounded-lg border border-warning/30 bg-warning/10 text-warning font-semibold">{warning}</div>'
                )
                if warning
                else "",
            ),
            # 交易下单操作面板 (在此输入不会因为行情更新而闪烁，100% 保持焦点)
            div(
                {
                    "class": "card bg-base-200 border border-base-300 shadow-xl p-6 flex flex-col gap-4"
                },
                h3(
                    {"class": "text-sm font-bold text-white"},
                    "🛒 高并发交易委托 (Instant Buy/Sell Order)",
                ),
                div(
                    {"class": "grid grid-cols-1 md:grid-cols-2 gap-4"},
                    # 买入操作 form
                    form(
                        {
                            "class": "flex flex-col gap-2",
                            "on_submit": self.buy_btc,
                        },
                        div(
                            {"class": "join w-full"},
                            input_(
                                {
                                    "type": "number",
                                    "step": "0.01",
                                    "name": "amount",
                                    "value": "0.10",
                                    "class": "input input-bordered input-sm join-item flex-1 font-mono text-center",
                                }
                            ),
                            # 注册了 LoadingTransducer 的按钮在执行 submit 时将自动变为 loading 态
                            button(
                                {
                                    "type": "submit",
                                    "class": "btn btn-sm btn-success join-item",
                                },
                                "🟢 限价买入 BTC",
                            ),
                        ),
                    ),
                    # 卖出操作 form
                    form(
                        {
                            "class": "flex flex-col gap-2",
                            "on_submit": self.sell_btc,
                        },
                        div(
                            {"class": "join w-full"},
                            input_(
                                {
                                    "type": "number",
                                    "step": "0.01",
                                    "name": "amount",
                                    "value": "0.10",
                                    "class": "input input-bordered input-sm join-item flex-1 font-mono text-center",
                                }
                            ),
                            button(
                                {
                                    "type": "submit",
                                    "class": "btn btn-sm btn-error join-item",
                                },
                                "🔴 限价卖出 BTC",
                            ),
                        ),
                    ),
                ),
            ),
            # 数据总线与哈希安全审计
            div(
                {
                    "class": "card bg-base-200 border border-base-300 shadow-xl p-6 flex flex-col gap-3 min-h-48"
                },
                div(
                    {"class": "flex justify-between items-center"},
                    span(
                        {"class": "text-xs font-bold text-white"},
                        "📋 交易终端实时日志 (含 Transducers 敏感词安全过滤)",
                    ),
                    span(
                        {"class": "badge badge-xs badge-outline badge-accent"},
                        "Transducers 强护盾已启用",
                    ),
                ),
                p(
                    {"class": "text-[10px] text-base-content/50"},
                    "注意：本控制台在渲染时由 `SanitizingTransducer` 对所有的 `API-KEY-SECRET` 以及 `TX-SECURE-HASH` 进行正则掩盖和遮罩阻断，防止敏感凭据泄露到前端渲染：",
                ),
                ul(
                    {"class": "text-[10px] font-mono opacity-80 flex flex-col gap-1.5"},
                    *[li(None, log) for log in logs],
                )
                if logs
                else p(
                    {"class": "text-[10px] opacity-40 italic mt-6 text-center"},
                    "暂无交易成交日志",
                ),
            ),
        )


# ---------------------------------------------------------------------------
# App initialization & Middleware configuration
# ---------------------------------------------------------------------------

registry = ComponentRegistry()
registry.register("btc-price-display", BtcPriceDisplay)
registry.register("portfolio-display", PortfolioDisplay)
registry.register("cash-balance-display", CashBalanceDisplay)
registry.register("crypto-trader", CryptoTrader)

app = create_hiccl_app(
    HicclConfig(
        component_registry=registry,
        transport_modes={"http", "ws", "sse"},
        pages=menu(CryptoTrader),
        brand_name="Hiccl CSP Simulator",
        title="Hiccl CSP Crypto Simulator — Concurrency 大秀",
        theme="night",
        show_navbar=False,
    )
)

# 核心步骤：向全局渲染引擎动态插装 Phase 4 Transducers 变换中间件
renderer = app.state.hiccl["renderer"]

# 1. 挂接自动 Loading 属性注入中间件 (使下单按钮在点击等待时自动追加 DaisyUI 菊花加载态)
renderer.transducers.append(LoadingTransducer(loading_class="btn-loading"))

# 2. 挂接安全审计遮罩中间件 (使日志中可能遗留的 API 密钥及上链哈希自动被模糊处理，防止审计泄露)
renderer.transducers.append(
    SanitizingTransducer(
        blacklist=["SECURE_129X0A", "TX-SECURE-HASH"],
        replacement="[CONFIDENTIAL-MASKED]",
    )
)


if __name__ == "__main__":
    import uvicorn

    print("======================================================================")
    print("🚀 Hiccl CSP 加密交易模拟终端启动中...")
    print("👉 请在浏览器中打开: http://127.0.0.1:8000")
    print("======================================================================")

    # 启用 HMR 实时更新以便同步开发反馈
    import os

    os.environ["HICCL_LIVE_RELOAD"] = "1"

    uvicorn.run(app, host="127.0.0.1", port=8000)
