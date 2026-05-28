from fastapi.testclient import TestClient
from hiccl.app import create_hiccl_app, HicclConfig
from hiccl.registry import ComponentRegistry


def test_cascade_static_fallback(tmp_path):
    # 1. 创建临时的“用户自定义静态文件目录”，并写入一个自定义静态文件
    user_static_dir = tmp_path / "custom_static"
    user_static_dir.mkdir()

    custom_js_file = user_static_dir / "custom.js"
    custom_js_file.write_text("console.log('custom');", encoding="utf-8")

    # 2. 构造 Hiccl 应用程序配置，将 static_dir 指向该临时目录
    registry = ComponentRegistry()
    config = HicclConfig(
        component_registry=registry,
        transport_modes={"http"},
        static_dir=str(user_static_dir),
    )

    # 3. 创建 FastAPI 实例并建立 TestClient
    app = create_hiccl_app(config)
    client = TestClient(app)

    # 4. 验证级联静态服务行为

    # 场景 A: 请求用户自定义的静态文件 (应该成功返回)
    response = client.get("/static/custom.js")
    assert response.status_code == 200
    assert response.text == "console.log('custom');"

    # 场景 B: 请求内置的静态文件 (应该 Fallback 到包内 static 目录并成功返回)
    response = client.get("/static/hiccl.js")
    assert response.status_code == 200
    assert (
        "hiccl-session" in response.text
        or "htmx" in response.text
        or "addEventListener" in response.text
    )

    # 场景 C: 请求一个两边都不存在的文件 (应该返回 404)
    response = client.get("/static/nonexistent.js")
    assert response.status_code == 404
