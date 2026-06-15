"""LandingPage component for hiccl.dev — the official Hiccl website.

Single-page scroll design with bilingual (zh/en) support via Alpine.js.
All sections are rendered in a single render() method.
"""

from __future__ import annotations

from hiccl import Component
from hiccl.hiccup import (
    a,
    br_,
    button,
    code,
    div,
    footer,
    h1,
    h2,
    h3,
    header,
    main,
    nav,
    p,
    pre,
    raw,
    section,
    span,
)

from .i18n import COUNTER_CODE, EN, EXAMPLES, ZH


def _nav_link(href: str, zh: str, en: str) -> list:
    """Render a navigation link with bilingual text."""
    return a(
        {
            "href": href,
            "class": "text-base-content/70 hover:text-primary transition-colors duration-200 text-sm font-medium",
            "@click": f"smoothScroll('{href}')",
        },
        span({"x-show": "lang === 'zh'", "x-cloak": ""}, zh),
        span({"x-show": "lang === 'en'", "x-cloak": ""}, en),
    )


class LandingPage(Component):
    """Main landing page component for hiccl.dev."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Lang is managed client-side by Alpine; server-side default
        self._lang = "en"

    def render(self):
        return self._build_page()

    # ── Page scaffold ────────────────────────────────────────────────

    def _build_page(self) -> list:
        """Build the complete landing page.

        The entire page is wrapped in an Alpine x-data for language state.
        x-init detects browser language and applies it on load.
        """
        return div(
            {
                "x-data": """{
                        lang: 'en',
                        mobileMenuOpen: false,
                        init() {
                            const stored = localStorage.getItem('hiccl-lang');
                            if (stored) { this.lang = stored; return; }
                            const nav = navigator.language || '';
                            this.lang = nav.startsWith('zh') ? 'zh' : 'en';
                        },
                        switchLang(l) {
                            this.lang = l;
                            localStorage.setItem('hiccl-lang', l);
                        },
                        smoothScroll(hash) {
                            const el = document.querySelector(hash);
                            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    }""",
                "class": "min-h-screen bg-gradient-to-b from-base-100 via-base-200 to-base-300",
            },
            self._navbar(),
            main(
                {"class": "relative"},
                self._hero_section(),
                self._features_section(),
                self._stack_section(),
                self._examples_section(),
                self._quickstart_section(),
                self._install_section(),
                self._footer(),
            ),
        )

    # ── Navbar ───────────────────────────────────────────────────────

    def _navbar(self) -> list:
        """Fixed top navigation bar with language switcher."""
        return header(
            {
                "class": "sticky top-0 z-50 backdrop-blur-xl bg-base-100/70 border-b border-base-200/50",
            },
            div(
                {
                    "class": "max-w-6xl mx-auto px-4 sm:px-6 lg:px-8",
                },
                div(
                    {
                        "class": "flex items-center justify-between h-16",
                    },
                    # Logo
                    div(
                        {"class": "flex items-center gap-3"},
                        span(
                            {
                                "class": "text-2xl",
                            },
                            "🧪",
                        ),
                        span(
                            {
                                "class": "text-xl font-black bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent",
                            },
                            "Hiccl",
                        ),
                        span(
                            {
                                "class": "hidden sm:inline text-xs px-2 py-0.5 rounded-full bg-emerald-400/10 text-emerald-400 border border-emerald-400/20 font-mono",
                            },
                            "v0.7.0",
                        ),
                    ),
                    # Desktop nav links
                    nav(
                        {
                            "class": "hidden md:flex items-center gap-6",
                        },
                        _nav_link("#features", "特性", "Features"),
                        _nav_link("#stack", "技术栈", "Stack"),
                        _nav_link("#examples", "示例", "Examples"),
                        _nav_link("#quickstart", "快速上手", "QuickStart"),
                        _nav_link("#install", "安装", "Install"),
                        a(
                            {
                                "href": "https://github.com/lib-hiccl/hiccl",
                                "target": "_blank",
                                "rel": "noopener",
                                "class": "text-base-content/70 hover:text-primary transition-colors duration-200 text-sm font-medium inline-flex items-center gap-1",
                            },
                            span(
                                {
                                    "x-show": "lang === 'zh'",
                                    "x-cloak": "",
                                },
                                "GitHub",
                            ),
                            span(
                                {
                                    "x-show": "lang === 'en'",
                                    "x-cloak": "",
                                },
                                "GitHub",
                            ),
                            span({"class": "text-xs"}, "↗"),
                        ),
                    ),
                    # Language switcher + mobile menu button
                    div(
                        {"class": "flex items-center gap-2"},
                        # Lang switcher
                        div(
                            {
                                "class": "join join-horizontal",
                            },
                            button(
                                {
                                    "class": "join-item btn btn-xs",
                                    ":class": "lang === 'zh' ? 'btn-primary' : 'btn-ghost'",
                                    "@click": "switchLang('zh')",
                                },
                                "中",
                            ),
                            button(
                                {
                                    "class": "join-item btn btn-xs",
                                    ":class": "lang === 'en' ? 'btn-primary' : 'btn-ghost'",
                                    "@click": "switchLang('en')",
                                },
                                "EN",
                            ),
                        ),
                        # Mobile hamburger
                        button(
                            {
                                "class": "md:hidden btn btn-ghost btn-sm btn-square",
                                "@click": "mobileMenuOpen = !mobileMenuOpen",
                            },
                            raw(svg_icon_menu()),
                        ),
                    ),
                ),
                # Mobile menu
                div(
                    {
                        "x-show": "mobileMenuOpen",
                        "x-cloak": "",
                        "@click.outside": "mobileMenuOpen = false",
                        "class": "md:hidden pb-4 flex flex-col gap-2",
                    },
                    _nav_link("#features", "特性", "Features"),
                    _nav_link("#stack", "技术栈", "Stack"),
                    _nav_link("#examples", "示例", "Examples"),
                    _nav_link("#quickstart", "快速上手", "QuickStart"),
                    _nav_link("#install", "安装", "Install"),
                    a(
                        {
                            "href": "https://github.com/lib-hiccl/hiccl",
                            "target": "_blank",
                            "rel": "noopener",
                            "class": "text-base-content/70 hover:text-primary transition-colors duration-200 text-sm font-medium",
                        },
                        "GitHub ↗",
                    ),
                ),
            ),
        )

    # ── Hero ─────────────────────────────────────────────────────────

    def _hero_section(self) -> list:
        """Hero section with title, subtitle, and CTAs."""
        return section(
            {
                "class": "relative overflow-hidden",
            },
            # Background decoration
            div(
                {
                    "class": "absolute inset-0 overflow-hidden pointer-events-none",
                },
                div(
                    {
                        "class": "absolute -top-40 -right-40 w-80 h-80 bg-emerald-400/10 rounded-full blur-3xl",
                    },
                ),
                div(
                    {
                        "class": "absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-400/10 rounded-full blur-3xl",
                    },
                ),
            ),
            div(
                {
                    "class": "relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16 sm:pt-28 sm:pb-20 text-center",
                },
                # Badge
                div(
                    {
                        "class": "inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-400/10 border border-emerald-400/20 text-emerald-400 text-xs sm:text-sm font-medium mb-6",
                    },
                    span(
                        {
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "🧪 v0.7.0 — 全栈反应式 Web 框架",
                    ),
                    span(
                        {
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "🧪 v0.7.0 — Full-Stack Reactive Web Framework",
                    ),
                ),
                # Headline
                h1(
                    {
                        "class": "text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight mb-6",
                    },
                    span(
                        {
                            "class": "bg-gradient-to-r from-emerald-400 via-cyan-400 to-violet-400 bg-clip-text text-transparent",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "融合 Clojure 声明式基因",
                    ),
                    span(
                        {
                            "class": "bg-gradient-to-r from-emerald-400 via-cyan-400 to-violet-400 bg-clip-text text-transparent",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "Clojure's Declarative Gene",
                    ),
                    br_(),
                    span(
                        {
                            "class": "text-base-content",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "与 Pythonic 全栈反应式",
                    ),
                    span(
                        {
                            "class": "text-base-content",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "Meets Pythonic Full-Stack Reactivity",
                    ),
                ),
                # Subtitle
                p(
                    {
                        "class": "text-base-content/60 text-base sm:text-lg max-w-2xl mx-auto mb-8 leading-relaxed",
                        "x-show": "lang === 'zh'",
                        "x-cloak": "",
                    },
                    "纯 Python 编写全栈应用。零构建、零 API 胶水、天生离线就绪。"
                    "用嵌套列表表达 UI，框架自动完成 WebSocket 双向同步与最小化 DOM 补丁推送。",
                ),
                p(
                    {
                        "class": "text-base-content/60 text-base sm:text-lg max-w-2xl mx-auto mb-8 leading-relaxed",
                        "x-show": "lang === 'en'",
                        "x-cloak": "",
                    },
                    "Build full-stack apps in pure Python. Zero build, zero API glue, air-gapped ready. "
                    "Express UI with nested lists — the framework handles WebSocket bidirectional sync "
                    "and minimal DOM patch pushes automatically.",
                ),
                # CTA buttons
                div(
                    {
                        "class": "flex flex-col sm:flex-row items-center justify-center gap-4 mb-6",
                    },
                    a(
                        {
                            "href": "#quickstart",
                            "class": "btn btn-emerald btn-lg px-8 w-full sm:w-auto",
                            "@click": "smoothScroll('#quickstart')",
                        },
                        span({"x-show": "lang === 'zh'", "x-cloak": ""}, "🚀 快速上手"),
                        span(
                            {"x-show": "lang === 'en'", "x-cloak": ""}, "🚀 Quick Start"
                        ),
                    ),
                    a(
                        {
                            "href": "https://github.com/lib-hiccl/hiccl",
                            "target": "_blank",
                            "rel": "noopener",
                            "class": "btn btn-outline btn-lg px-8 w-full sm:w-auto",
                        },
                        "⭐ GitHub",
                    ),
                ),
                # Version info
                p(
                    {
                        "class": "text-base-content/40 text-xs",
                        "x-show": "lang === 'zh'",
                        "x-cloak": "",
                    },
                    "最新版本 v0.7.0 · MIT 开源 · Python ≥ 3.11",
                ),
                p(
                    {
                        "class": "text-base-content/40 text-xs",
                        "x-show": "lang === 'en'",
                        "x-cloak": "",
                    },
                    "Latest v0.7.0 · MIT Open Source · Python ≥ 3.11",
                ),
            ),
            # Bottom gradient fade
            div(
                {
                    "class": "h-16 bg-gradient-to-b from-transparent to-base-200",
                },
            ),
        )

    # ── Features ─────────────────────────────────────────────────────

    def _features_section(self) -> list:
        """Feature grid section."""
        return section(
            {
                "id": "features",
                "class": "bg-base-200 py-16 sm:py-20",
            },
            div(
                {"class": "max-w-6xl mx-auto px-4 sm:px-6 lg:px-8"},
                # Section header
                div(
                    {"class": "text-center mb-12"},
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "⚡️ 核心特性",
                    ),
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "⚡️ Key Features",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "Hiccl 继承了 Clojure 的优雅哲学，在 Python 生态中打造现代化全栈开发体验。",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "Hiccl inherits Clojure's elegant philosophy, crafting a modern full-stack "
                        "development experience within the Python ecosystem.",
                    ),
                ),
                # Feature grid
                div(
                    {
                        "class": "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4",
                    },
                    *[
                        self._feature_card(i, item)
                        for i, item in enumerate(ZH["features"]["items"])
                    ],
                ),
            ),
        )

    def _feature_card(self, index: int, item: dict) -> list:
        """Render a single feature card (bilingual)."""
        en_item = EN["features"]["items"][index]
        return div(
            {
                "class": (
                    "card bg-base-100 border border-base-300 hover:border-emerald-400/30 "
                    "hover:shadow-lg hover:shadow-emerald-400/5 transition-all duration-300 group"
                ),
            },
            div(
                {"class": "card-body p-5"},
                div(
                    {"class": "flex items-start gap-3"},
                    span({"class": "text-2xl flex-shrink-0"}, item["emoji"]),
                    div(
                        {},
                        h3(
                            {
                                "class": "card-title text-base mb-1 group-hover:text-emerald-400 transition-colors",
                                "x-show": "lang === 'zh'",
                                "x-cloak": "",
                            },
                            item["title"],
                        ),
                        h3(
                            {
                                "class": "card-title text-base mb-1 group-hover:text-emerald-400 transition-colors",
                                "x-show": "lang === 'en'",
                                "x-cloak": "",
                            },
                            en_item["title"],
                        ),
                        p(
                            {
                                "class": "text-sm text-base-content/60 leading-relaxed",
                                "x-show": "lang === 'zh'",
                                "x-cloak": "",
                            },
                            item["desc"],
                        ),
                        p(
                            {
                                "class": "text-sm text-base-content/60 leading-relaxed",
                                "x-show": "lang === 'en'",
                                "x-cloak": "",
                            },
                            en_item["desc"],
                        ),
                    ),
                ),
            ),
        )

    # ── Tech Stack ───────────────────────────────────────────────────

    def _stack_section(self) -> list:
        """Tech stack layers section."""
        return section(
            {
                "id": "stack",
                "class": "bg-base-100 py-16 sm:py-20",
            },
            div(
                {"class": "max-w-4xl mx-auto px-4 sm:px-6 lg:px-8"},
                div(
                    {"class": "text-center mb-12"},
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "🛠 技术栈",
                    ),
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "🛠 Tech Stack",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "Hiccl 的全栈架构由五个精心编排的层次构成，每一层都聚焦于特定的职责。",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "Hiccl's full-stack architecture is composed of five carefully orchestrated layers, "
                        "each focused on a specific responsibility.",
                    ),
                ),
                # Stack layers
                div(
                    {"class": "flex flex-col gap-3"},
                    *[
                        self._stack_layer(i, layer)
                        for i, layer in enumerate(ZH["stack"]["layers"])
                    ],
                ),
            ),
        )

    def _stack_layer(self, index: int, layer: dict) -> list:
        """Render a single tech stack layer."""
        en_layer = EN["stack"]["layers"][index]
        return div(
            {
                "class": (
                    f"card bg-base-200 border-l-4 {layer['color']} "
                    "hover:shadow-md transition-all duration-300"
                ),
            },
            div(
                {"class": "card-body p-5"},
                div(
                    {
                        "class": "flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4"
                    },
                    div(
                        {"class": "flex-shrink-0"},
                        h3(
                            {
                                "class": "font-bold text-base",
                                "x-show": "lang === 'zh'",
                                "x-cloak": "",
                            },
                            layer["name"],
                        ),
                        h3(
                            {
                                "class": "font-bold text-base",
                                "x-show": "lang === 'en'",
                                "x-cloak": "",
                            },
                            en_layer["name"],
                        ),
                    ),
                    div(
                        {"class": "flex-1"},
                        p(
                            {
                                "class": "text-sm text-base-content/60",
                                "x-show": "lang === 'zh'",
                                "x-cloak": "",
                            },
                            layer["desc"],
                        ),
                        p(
                            {
                                "class": "text-sm text-base-content/60",
                                "x-show": "lang === 'en'",
                                "x-cloak": "",
                            },
                            en_layer["desc"],
                        ),
                    ),
                ),
            ),
        )

    # ── Examples ────────────────────────────────────────────────────

    def _examples_section(self) -> list:
        """Examples showcase section with code snippets."""
        return section(
            {"id": "examples", "class": "bg-base-200 py-16 sm:py-20"},
            div(
                {"class": "max-w-6xl mx-auto px-4 sm:px-6 lg:px-8"},
                # Section header
                div(
                    {"class": "text-center mb-12"},
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "🎮 演示示例",
                    ),
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "🎮 Live Examples",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "从极简计数器到全维度特性大秀，探索 Hiccl 的每一种核心能力。每个示例都是可直接运行的完整应用。",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "From a minimal counter to a full-featured showcase, explore every core capability of Hiccl. Each example is a complete, runnable application.",
                    ),
                ),
                # Example cards grid
                div(
                    {"class": "grid grid-cols-1 lg:grid-cols-2 gap-6"},
                    *[self._example_card(ex) for ex in EXAMPLES],
                ),
            ),
        )

    def _example_card(self, ex: dict) -> list:
        """Render a single example card with bilingual text and code snippet."""
        return div(
            {
                "class": (
                    "card bg-base-100 border border-base-300 "
                    "hover:border-emerald-400/30 hover:shadow-lg hover:shadow-emerald-400/5 "
                    "transition-all duration-300 group overflow-hidden"
                ),
            },
            div(
                {"class": "card-body p-5 flex flex-col gap-3"},
                # Header: icon + title + file info
                div(
                    {"class": "flex items-start gap-3"},
                    span({"class": "text-2xl flex-shrink-0"}, ex["icon"]),
                    div(
                        {"class": "flex-1 min-w-0"},
                        h3(
                            {
                                "class": "card-title text-base font-bold group-hover:text-emerald-400 transition-colors",
                                "x-show": "lang === 'zh'",
                                "x-cloak": "",
                            },
                            ex["title_zh"],
                        ),
                        h3(
                            {
                                "class": "card-title text-base font-bold group-hover:text-emerald-400 transition-colors",
                                "x-show": "lang === 'en'",
                                "x-cloak": "",
                            },
                            ex["title_en"],
                        ),
                        span(
                            {"class": "text-xs text-base-content/40 font-mono"},
                            f"examples/{ex['file']} · {ex['lines']} lines",
                        ),
                    ),
                ),
                # Description
                p(
                    {
                        "class": "text-sm text-base-content/60 leading-relaxed",
                        "x-show": "lang === 'zh'",
                        "x-cloak": "",
                    },
                    ex["desc_zh"],
                ),
                p(
                    {
                        "class": "text-sm text-base-content/60 leading-relaxed",
                        "x-show": "lang === 'en'",
                        "x-cloak": "",
                    },
                    ex["desc_en"],
                ),
                # Tags
                div(
                    {"class": "flex flex-wrap gap-1.5"},
                    *[
                        span(
                            {
                                "class": "badge badge-xs badge-outline badge-primary/30 text-primary",
                            },
                            tag,
                        )
                        for tag in ex["tags"]
                    ],
                ),
                # Try Live button
                a(
                    {
                        "href": ex["route"],
                        "class": "btn btn-sm btn-primary btn-outline gap-1 w-full",
                    },
                    span(
                        {"x-show": "lang === 'zh'", "x-cloak": ""},
                        "▶ 在线体验",
                    ),
                    span(
                        {"x-show": "lang === 'en'", "x-cloak": ""},
                        "▶ Try Live",
                    ),
                ),
                # Code block
                div(
                    {
                        "class": "bg-base-300 border border-base-300 rounded-xl overflow-hidden",
                    },
                    # Code header with dots
                    div(
                        {
                            "class": "flex items-center justify-between px-4 py-2 bg-base-200/50 border-b border-base-300",
                        },
                        div(
                            {"class": "flex items-center gap-1.5"},
                            span({"class": "w-2.5 h-2.5 rounded-full bg-red-400"}),
                            span({"class": "w-2.5 h-2.5 rounded-full bg-yellow-400"}),
                            span({"class": "w-2.5 h-2.5 rounded-full bg-green-400"}),
                        ),
                        span(
                            {"class": "text-xs text-base-content/40 font-mono"},
                            ex["file"],
                        ),
                        span({"class": "w-10"}),
                    ),
                    # Code content
                    pre(
                        {
                            "class": "p-4 overflow-x-auto text-xs leading-relaxed",
                        },
                        code(
                            {
                                "class": "font-mono text-base-content/70",
                                "style": "white-space: pre;",
                            },
                            ex["code"],
                        ),
                    ),
                ),
                # Run command
                div(
                    {"class": "mockup-code bg-base-300/50 text-xs"},
                    pre(
                        {"class": "px-4 py-2"},
                        code(
                            {"class": "text-emerald-400"},
                            f"$ uv run python examples/{ex['file']}",
                        ),
                    ),
                ),
            ),
        )

    # ── QuickStart ───────────────────────────────────────────────────

    def _quickstart_section(self) -> list:
        """QuickStart section with code example."""
        return section(
            {
                "id": "quickstart",
                "class": "bg-base-200 py-16 sm:py-20",
            },
            div(
                {"class": "max-w-4xl mx-auto px-4 sm:px-6 lg:px-8"},
                div(
                    {"class": "text-center mb-12"},
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "🚀 快速上手",
                    ),
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "🚀 Quick Start",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "30 行代码，从零到运行一个全栈响应式计数器。",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "30 lines of code, from zero to a running full-stack reactive counter.",
                    ),
                ),
                # Steps
                div(
                    {
                        "class": "grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10",
                    },
                    # Step 1
                    div(
                        {
                            "class": "card bg-base-100 border border-base-300",
                        },
                        div(
                            {"class": "card-body p-5 text-center"},
                            div(
                                {
                                    "class": "w-10 h-10 rounded-full bg-emerald-400/10 text-emerald-400 flex items-center justify-center font-bold mx-auto mb-3",
                                },
                                "1",
                            ),
                            h3(
                                {
                                    "class": "font-bold mb-1",
                                    "x-show": "lang === 'zh'",
                                    "x-cloak": "",
                                },
                                "安装 Hiccl",
                            ),
                            h3(
                                {
                                    "class": "font-bold mb-1",
                                    "x-show": "lang === 'en'",
                                    "x-cloak": "",
                                },
                                "Install Hiccl",
                            ),
                            p(
                                {
                                    "class": "text-sm text-base-content/60",
                                    "x-show": "lang === 'zh'",
                                    "x-cloak": "",
                                },
                                "使用 pip 或 uv 安装框架本体。",
                            ),
                            p(
                                {
                                    "class": "text-sm text-base-content/60",
                                    "x-show": "lang === 'en'",
                                    "x-cloak": "",
                                },
                                "Install the framework via pip or uv.",
                            ),
                        ),
                    ),
                    # Step 2
                    div(
                        {
                            "class": "card bg-base-100 border border-base-300",
                        },
                        div(
                            {"class": "card-body p-5 text-center"},
                            div(
                                {
                                    "class": "w-10 h-10 rounded-full bg-cyan-400/10 text-cyan-400 flex items-center justify-center font-bold mx-auto mb-3",
                                },
                                "2",
                            ),
                            h3(
                                {
                                    "class": "font-bold mb-1",
                                    "x-show": "lang === 'zh'",
                                    "x-cloak": "",
                                },
                                "编写组件",
                            ),
                            h3(
                                {
                                    "class": "font-bold mb-1",
                                    "x-show": "lang === 'en'",
                                    "x-cloak": "",
                                },
                                "Write Component",
                            ),
                            p(
                                {
                                    "class": "text-sm text-base-content/60",
                                    "x-show": "lang === 'zh'",
                                    "x-cloak": "",
                                },
                                "用 Hiccup DSL 声明 UI，用 @server 声明事件。",
                            ),
                            p(
                                {
                                    "class": "text-sm text-base-content/60",
                                    "x-show": "lang === 'en'",
                                    "x-cloak": "",
                                },
                                "Declare UI with Hiccup DSL, declare events with @server.",
                            ),
                        ),
                    ),
                    # Step 3
                    div(
                        {
                            "class": "card bg-base-100 border border-base-300",
                        },
                        div(
                            {"class": "card-body p-5 text-center"},
                            div(
                                {
                                    "class": "w-10 h-10 rounded-full bg-violet-400/10 text-violet-400 flex items-center justify-center font-bold mx-auto mb-3",
                                },
                                "3",
                            ),
                            h3(
                                {
                                    "class": "font-bold mb-1",
                                    "x-show": "lang === 'zh'",
                                    "x-cloak": "",
                                },
                                "启动服务",
                            ),
                            h3(
                                {
                                    "class": "font-bold mb-1",
                                    "x-show": "lang === 'en'",
                                    "x-cloak": "",
                                },
                                "Launch Server",
                            ),
                            p(
                                {
                                    "class": "text-sm text-base-content/60",
                                    "x-show": "lang === 'zh'",
                                    "x-cloak": "",
                                },
                                "一行命令启动，浏览器即刻看到响应式界面。",
                            ),
                            p(
                                {
                                    "class": "text-sm text-base-content/60",
                                    "x-show": "lang === 'en'",
                                    "x-cloak": "",
                                },
                                "One command to start the dev server. See your reactive UI instantly.",
                            ),
                        ),
                    ),
                ),
                # Code block
                div(
                    {
                        "class": "card bg-base-300 border border-base-300 overflow-hidden"
                    },
                    div(
                        {
                            "class": "card-body p-0",
                        },
                        # Code header
                        div(
                            {
                                "class": "flex items-center justify-between px-5 py-3 bg-base-200/50 border-b border-base-300",
                            },
                            div(
                                {"class": "flex items-center gap-2"},
                                span(
                                    {
                                        "class": "w-3 h-3 rounded-full bg-red-400",
                                    },
                                ),
                                span(
                                    {
                                        "class": "w-3 h-3 rounded-full bg-yellow-400",
                                    },
                                ),
                                span(
                                    {
                                        "class": "w-3 h-3 rounded-full bg-green-400",
                                    },
                                ),
                            ),
                            span(
                                {
                                    "class": "text-xs text-base-content/40 font-mono",
                                },
                                "counter_app.py",
                            ),
                            # Copy button placeholder
                            span({"class": "w-14"}),
                        ),
                        # Code content
                        pre(
                            {
                                "class": "p-5 overflow-x-auto text-sm leading-relaxed",
                            },
                            code(
                                {
                                    "class": "font-mono text-base-content/80",
                                    "style": "white-space: pre;",
                                },
                                COUNTER_CODE.strip(),
                            ),
                        ),
                    ),
                ),
            ),
        )

    # ── Install / GitHub ─────────────────────────────────────────────

    def _install_section(self) -> list:
        """Install commands and GitHub repo section."""
        return section(
            {
                "id": "install",
                "class": "bg-base-100 py-16 sm:py-20",
            },
            div(
                {"class": "max-w-4xl mx-auto px-4 sm:px-6 lg:px-8"},
                div(
                    {"class": "text-center mb-12"},
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "📦 安装 Hiccl",
                    ),
                    h2(
                        {
                            "class": "text-3xl sm:text-4xl font-extrabold mb-4",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "📦 Install Hiccl",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'zh'",
                            "x-cloak": "",
                        },
                        "一行命令即可将 Hiccl 添加到你的 Python 项目中。",
                    ),
                    p(
                        {
                            "class": "text-base-content/60 max-w-2xl mx-auto",
                            "x-show": "lang === 'en'",
                            "x-cloak": "",
                        },
                        "Add Hiccl to your Python project with a single command.",
                    ),
                ),
                # Install commands
                div(
                    {
                        "class": "grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10",
                    },
                    # pip
                    div(
                        {
                            "class": "card bg-base-200 border border-base-300",
                        },
                        div(
                            {"class": "card-body p-5"},
                            div(
                                {
                                    "class": "flex items-center gap-2 mb-3",
                                },
                                span(
                                    {
                                        "class": "text-lg",
                                    },
                                    "📦",
                                ),
                                span(
                                    {
                                        "class": "font-bold text-sm",
                                        "x-show": "lang === 'zh'",
                                        "x-cloak": "",
                                    },
                                    "使用 pip",
                                ),
                                span(
                                    {
                                        "class": "font-bold text-sm",
                                        "x-show": "lang === 'en'",
                                        "x-cloak": "",
                                    },
                                    "Using pip",
                                ),
                            ),
                            div(
                                {
                                    "class": "mockup-code bg-base-300/50",
                                },
                                pre(
                                    {
                                        "class": "px-4 py-3",
                                    },
                                    code(
                                        {
                                            "class": "text-sm text-emerald-400",
                                        },
                                        "$ pip install hiccl",
                                    ),
                                ),
                            ),
                        ),
                    ),
                    # uv
                    div(
                        {
                            "class": "card bg-base-200 border border-base-300",
                        },
                        div(
                            {"class": "card-body p-5"},
                            div(
                                {
                                    "class": "flex items-center gap-2 mb-3",
                                },
                                span(
                                    {
                                        "class": "text-lg",
                                    },
                                    "⚡",
                                ),
                                span(
                                    {
                                        "class": "font-bold text-sm",
                                        "x-show": "lang === 'zh'",
                                        "x-cloak": "",
                                    },
                                    "使用 uv（推荐）",
                                ),
                                span(
                                    {
                                        "class": "font-bold text-sm",
                                        "x-show": "lang === 'en'",
                                        "x-cloak": "",
                                    },
                                    "Using uv (recommended)",
                                ),
                                span(
                                    {
                                        "class": "text-[10px] px-1.5 py-0.5 rounded bg-emerald-400/10 text-emerald-400",
                                    },
                                    "推荐",
                                ),
                            ),
                            div(
                                {
                                    "class": "mockup-code bg-base-300/50",
                                },
                                pre(
                                    {
                                        "class": "px-4 py-3",
                                    },
                                    code(
                                        {
                                            "class": "text-sm text-emerald-400",
                                        },
                                        "$ uv add hiccl",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                # GitHub repo card
                a(
                    {
                        "href": "https://github.com/lib-hiccl/hiccl",
                        "target": "_blank",
                        "rel": "noopener",
                        "class": "block",
                    },
                    div(
                        {
                            "class": "card bg-base-200 border border-base-300 hover:border-emerald-400/30 hover:shadow-lg transition-all duration-300",
                        },
                        div(
                            {"class": "card-body p-6"},
                            div(
                                {
                                    "class": "flex flex-col sm:flex-row items-start sm:items-center gap-4",
                                },
                                # GitHub icon
                                div(
                                    {
                                        "class": "w-12 h-12 rounded-xl bg-base-300 flex items-center justify-center flex-shrink-0",
                                    },
                                    raw(svg_github_icon()),
                                ),
                                div(
                                    {"class": "flex-1"},
                                    h3(
                                        {
                                            "class": "font-bold text-lg mb-1",
                                            "x-show": "lang === 'zh'",
                                            "x-cloak": "",
                                        },
                                        "GitHub 开源仓库",
                                    ),
                                    h3(
                                        {
                                            "class": "font-bold text-lg mb-1",
                                            "x-show": "lang === 'en'",
                                            "x-cloak": "",
                                        },
                                        "GitHub Repository",
                                    ),
                                    p(
                                        {
                                            "class": "text-sm text-base-content/60",
                                            "x-show": "lang === 'zh'",
                                            "x-cloak": "",
                                        },
                                        "欢迎 ⭐ Star、🐛 Issue、🤝 PR！完整源码、210+ 单元测试、路线图尽在 GitHub。",
                                    ),
                                    p(
                                        {
                                            "class": "text-sm text-base-content/60",
                                            "x-show": "lang === 'en'",
                                            "x-cloak": "",
                                        },
                                        "Welcome ⭐ Star, 🐛 Issue, 🤝 PR! "
                                        "Full source code, 210+ unit tests, and roadmap all on GitHub.",
                                    ),
                                ),
                                div(
                                    {"class": "flex items-center gap-3 flex-shrink-0"},
                                    # Placeholder star count
                                    div(
                                        {
                                            "class": "flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-base-300",
                                        },
                                        span({"class": "text-yellow-400"}, "⭐"),
                                        span(
                                            {
                                                "class": "text-sm font-mono font-bold",
                                            },
                                            "Star",
                                        ),
                                    ),
                                    span(
                                        {
                                            "class": "text-base-content/30",
                                        },
                                        "↗",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

    # ── Footer ───────────────────────────────────────────────────────

    def _footer(self) -> list:
        """Page footer."""
        return footer(
            {
                "class": "bg-base-200 border-t border-base-300 py-10",
            },
            div(
                {
                    "class": "max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center",
                },
                div(
                    {"class": "flex items-center justify-center gap-3 mb-4"},
                    span({"class": "text-2xl"}, "🧪"),
                    span(
                        {
                            "class": "text-lg font-black bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent",
                        },
                        "Hiccl",
                    ),
                ),
                p(
                    {
                        "class": "text-sm text-base-content/50 mb-2",
                        "x-show": "lang === 'zh'",
                        "x-cloak": "",
                    },
                    "由 Hiccl 自举构建 · 本网站使用 Hiccl 框架自身编写",
                ),
                p(
                    {
                        "class": "text-sm text-base-content/50 mb-2",
                        "x-show": "lang === 'en'",
                        "x-cloak": "",
                    },
                    "Built with Hiccl itself · This website is written using the Hiccl framework",
                ),
                p(
                    {
                        "class": "text-xs text-base-content/30",
                    },
                    "© 2025 Hiccl Contributors. MIT License. Python ≥ 3.11",
                ),
            ),
        )


# ── Inline SVG helpers ──────────────────────────────────────────────


def svg_icon_menu() -> str:
    """Hamburger menu SVG icon."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" '
        'viewBox="0 0 24 24" stroke="currentColor">'
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M4 6h16M4 12h16M4 18h16" /></svg>'
    )


def svg_github_icon() -> str:
    """GitHub SVG icon."""
    return (
        '<svg class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">'
        '<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 '
        "0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695"
        "-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99"
        ".105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225"
        "-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c"
        "2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605"
        "-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225"
        '.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>'
    )
