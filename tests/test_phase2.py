"""Hiccl Phase 2 Integration and Unit Tests — Spec contract, @server specs, Redis Session Store, and Wildcard EventBus."""

import asyncio
import pytest
from hiccl import spec, server
from hiccl.component import Component
from hiccl.spec import SpecValidationError
from hiccl.session_store import RedisSessionStore, DummyRedisClient
from hiccl.eventbus import EventBus


# ---------------------------------------------------------------------------
# 1. hiccl.spec DSL Unit Tests
# ---------------------------------------------------------------------------


def test_spec_dsl_primitives():
    # Integer spec
    int_spec = spec.integer(gt=0, lte=10)
    assert int_spec.valid(5)
    assert not int_spec.valid(0)
    assert not int_spec.valid(11)
    assert not int_spec.valid("5")
    assert not int_spec.valid(
        True
    )  # True is an instance of int, but we must block bools

    # Float spec
    flt_spec = spec.float_(gt=1.5, lt=5.0)
    assert flt_spec.valid(2.0)
    assert not flt_spec.valid(1.0)
    assert not flt_spec.valid(5.0)

    # String & Regex spec
    str_spec = spec.string(min_len=3, max_len=10)
    assert str_spec.valid("hello")
    assert not str_spec.valid("hi")
    assert not str_spec.valid("hello world indeed")

    email_spec = spec.regex(r"^[^@]+@[^@]+\.[^@]+$")
    assert email_spec.valid("alice@hiccl.dev")
    assert not email_spec.valid("alice_hiccl.dev")

    # Boolean spec
    bool_spec = spec.boolean()
    assert bool_spec.valid(True)
    assert bool_spec.valid(False)
    assert not bool_spec.valid(1)


def test_spec_dsl_complex():
    # Collection spec
    coll_spec = spec.coll_of(spec.integer(gt=0), min_len=2)
    assert coll_spec.valid([1, 2, 3])
    assert not coll_spec.valid([0, 1, 2])
    assert not coll_spec.valid([1])

    # Keys spec
    user_spec = spec.keys(
        req={
            "id": spec.integer(gt=0),
            "username": spec.string(min_len=3),
        },
        opt={
            "email": spec.regex(r"^[^@]+@[^@]+\.[^@]+$"),
        },
    )
    assert user_spec.valid({"id": 1, "username": "bob"})
    assert user_spec.valid({"id": 1, "username": "bob", "email": "bob@hiccl.dev"})
    assert not user_spec.valid({"id": 0, "username": "bob"})  # id invalid
    assert not user_spec.valid({"id": 1})  # username missing
    assert not user_spec.valid({"id": 1, "username": "bob", "email": "invalid-email"})

    # Logic specs (And/Or)
    and_spec = spec.and_(spec.integer(gt=5), spec.integer(lt=10))
    assert and_spec.valid(7)
    assert not and_spec.valid(4)

    or_spec = spec.or_(
        is_three=spec.integer(gt=2, lt=4), is_ten=spec.integer(gt=9, lt=11)
    )
    assert or_spec.valid(3)
    assert or_spec.valid(10)
    assert not or_spec.valid(5)

    # Custom Predicate spec
    pred_spec = spec.predicate(lambda x: x % 2 == 0, name="is_even")
    assert pred_spec.valid(4)
    assert not pred_spec.valid(5)


def test_spec_explain_data():
    user_spec = spec.keys(
        req={
            "id": spec.integer(gt=0),
        }
    )

    # 验证成功的 explain_data 应为 None
    assert user_spec.explain_data({"id": 5}) is None

    # 验证失败的 explain_data 应包含正确的字段和属性路径
    errors = user_spec.explain_data({"id": -1})
    assert errors is not None
    assert len(errors) == 1
    err = errors[0]
    assert err["path"] == ["id"]
    assert err["val"] == -1
    assert "gt" in err["pred"] or ">" in err["pred"]

    # 验证异常说明文本
    explain_txt = user_spec.explain({"id": -1})
    assert "id" in explain_txt
    assert "-1" in explain_txt


# ---------------------------------------------------------------------------
# 2. @server spec Verification Tests
# ---------------------------------------------------------------------------


class SpecRestrictedComponent(Component):
    _hiccl_component_name = "spec-restricted-comp"

    def __init__(self):
        super().__init__()

    # 无参 @server，保留向后兼容性
    @server
    def basic_action(self, val):
        return val * 2

    # 带参 @server(spec=...)，启用契约式输入和输出校验
    @server(
        spec={
            "args": {
                "step": spec.integer(gt=0),
                "name": spec.string(min_len=2),
            },
            "return": spec.boolean(),
        }
    )
    def guarded_action(self, step: int, name: str) -> bool:
        if step > 100:
            return "not-a-bool"  # 返回不合规的返回值，验证返回值 Spec 校验
        return True


def test_server_decorator_compatibility():
    comp = SpecRestrictedComponent()

    # 验证基础的无参 @server action 能正常调用
    assert comp.basic_action(5) == 10


def test_server_spec_args_and_return_validation():
    comp = SpecRestrictedComponent()

    # 1. 传入符合 Spec 契约的合法参数
    assert comp.guarded_action(5, "alice") is True

    # 2. 传入不合规的参数 (step 必须为正数)
    with pytest.raises(SpecValidationError) as exc_info:
        comp.guarded_action(-2, "alice")

    errors = exc_info.value.explain_data
    assert len(errors) == 1
    assert errors[0]["path"] == ["step"]
    assert errors[0]["val"] == -2

    # 3. 传入不合规的参数 (name 长度必须 >= 2)
    with pytest.raises(SpecValidationError) as exc_info:
        comp.guarded_action(5, "a")

    errors = exc_info.value.explain_data
    assert len(errors) == 1
    assert errors[0]["path"] == ["name"]

    # 4. 触发返回值 spec 校验异常
    with pytest.raises(SpecValidationError) as exc_info:
        comp.guarded_action(150, "alice")

    errors = exc_info.value.explain_data
    assert len(errors) == 1
    # 返回值的验证没有参数名路径，应当是 root 路径
    assert errors[0]["path"] == []
    assert errors[0]["val"] == "not-a-bool"


# ---------------------------------------------------------------------------
# 3. RedisSessionStore Enhanced (Msgpack, ConnectionPool, Pessimistic Lock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_session_store_lock_and_msgpack():
    # 模拟 DummyRedisClient 并配置 RedisSessionStore
    dummy_redis = DummyRedisClient()
    store = RedisSessionStore(redis_client=dummy_redis)

    # 1. 验证悲观锁上下文管理器接口在 DummyRedisClient 下的兼容可用性
    async with store.lock("session-xyz", timeout=5.0):
        # 确保在锁块内部代码能正常运行而不报错
        pass

    # 2. 验证数据压缩打包 _pack_data 和还原 _unpack_data 机制
    original_data = {
        "user_id": 42,
        "tags": ["active", "premium"],
        "info": {"nested": "value"},
    }

    packed_str = store._pack_data(original_data)
    # 检测是否默认使用 msgpack
    try:
        import msgpack  # noqa: F401

        assert packed_str.startswith("msgpack:")
    except ImportError:
        try:
            import orjson  # noqa: F401

            assert packed_str.startswith("orjson:")
        except ImportError:
            assert packed_str.startswith("json:")

    # 还原并断言数据原样恢复
    unpacked_data = store._unpack_data(packed_str)
    assert unpacked_data == original_data


# ---------------------------------------------------------------------------
# 4. Wildcard EventBus Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eventbus_wildcard_routing():
    bus = EventBus()

    # 创建订阅队列
    q_exact = asyncio.Queue()
    q_star = asyncio.Queue()
    q_hash = asyncio.Queue()

    # 订阅不同格式的主题
    bus.subscribe("sport.basketball", q_exact)
    bus.subscribe("sport.*", q_star)
    bus.subscribe("sport.#", q_hash)

    # 1. 精确发布到 sport.basketball
    await bus.publish("sport.basketball", "B1")

    # 所有 3 个订阅者都应收到该消息
    assert q_exact.get_nowait()["data"] == "B1"
    assert q_star.get_nowait()["data"] == "B1"
    assert q_hash.get_nowait()["data"] == "B1"

    # 2. 发布到 sport.football (匹配星号与井号，不匹配 exact)
    await bus.publish("sport.football", "F1")

    with pytest.raises(asyncio.QueueEmpty):
        q_exact.get_nowait()
    assert q_star.get_nowait()["data"] == "F1"
    assert q_hash.get_nowait()["data"] == "F1"

    # 3. 发布到 sport.football.match1 (仅匹配井号多层，星号不匹配，exact 不匹配)
    await bus.publish("sport.football.match1", "M1")

    with pytest.raises(asyncio.QueueEmpty):
        q_exact.get_nowait()
    with pytest.raises(asyncio.QueueEmpty):
        q_star.get_nowait()
    assert q_hash.get_nowait()["data"] == "M1"

    # 4. 发布到 sport (对于井号 sport.#，匹配零个子层，应当让 q_hash 收到；星号不匹配)
    await bus.publish("sport", "S1")

    with pytest.raises(asyncio.QueueEmpty):
        q_exact.get_nowait()
    with pytest.raises(asyncio.QueueEmpty):
        q_star.get_nowait()
    assert q_hash.get_nowait()["data"] == "S1"

    # 清理所有队列
    bus.unsubscribe_all(q_exact)
    bus.unsubscribe_all(q_star)
    bus.unsubscribe_all(q_hash)
