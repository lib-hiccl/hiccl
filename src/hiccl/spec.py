"""Hiccl Spec — 契约式运行时数据规范与校验系统。

类似于 Clojure Spec 哲学，提供声明式的轻量级数据校验 DSL，
支持结构化错误说明 (explain-data) 以及自动报错自愈辅助。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any


class SpecValidationError(ValueError):
    """Spec 契约校验失败时抛出的异常。

    包含结构化的错误详情 explain_data。
    """

    def __init__(self, explain_data: list[dict[str, Any]]) -> None:
        self.explain_data = explain_data
        super().__init__(self._format_errors())

    def _format_errors(self) -> str:
        lines = ["Spec 契约验证失败:"]
        for err in self.explain_data:
            path_str = " -> ".join(map(str, err.get("path", []))) or "root"
            lines.append(f"  - 路径: {path_str}")
            lines.append(f"    违规值: {err.get('val')!r}")
            lines.append(f"    未满足谓词: {err.get('pred')}")
            if "via" in err:
                lines.append(f"    关联 Spec: {err.get('via')}")
        return "\n".join(lines)


class Spec:
    """Spec 规范基类。所有具体校验器均需继承此类。"""

    def valid(self, val: Any) -> bool:
        """检查值是否满足契约。满足返回 True，否则返回 False。"""
        return self.explain_data(val) is None

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        """验证值并返回结构化的错误数据列表。如果校验通过则返回 None。

        错误字典字段：
        - "path": 失败字段在嵌套结构中的路径 (list)
        - "val": 导致失败的值
        - "pred": 失败谓词的描述信息
        - "via": 可选，关联的 Spec 标识或名称
        """
        raise NotImplementedError

    def explain(self, val: Any) -> str:
        """以人类可读的中文格式输出失败详情。"""
        data = self.explain_data(val)
        if not data:
            return "验证成功"
        lines = []
        for err in data:
            path_str = " -> ".join(map(str, err.get("path", []))) or "root"
            lines.append(
                f"在路径 {path_str} 中: 值 {err.get('val')!r} 未满足谓词条件 '{err.get('pred')}'"
            )
        return "\n".join(lines)

    def validate(self, val: Any) -> Any:
        """强校验值。如果失败，则抛出 SpecValidationError；如果成功，返回原值本身。"""
        errors = self.explain_data(val)
        if errors:
            raise SpecValidationError(errors)
        return val


# ---------------------------------------------------------------------------
# 具体的 Spec 校验器实现
# ---------------------------------------------------------------------------


class NilSpec(Spec):
    """只匹配 None 值的契约。"""

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        if val is not None:
            return [{"path": path or [], "val": val, "pred": "is_nil"}]
        return None


class AnySpec(Spec):
    """匹配任何值的契约 (永远通过)。"""

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        return None


class NumberSpec(Spec):
    """数值型契约 (支持大小边界限制，以及整型/浮点型区分)。"""

    def __init__(
        self,
        gt: float | None = None,
        gte: float | None = None,
        lt: float | None = None,
        lte: float | None = None,
        is_int: bool = False,
    ) -> None:
        self.gt = gt
        self.gte = gte
        self.lt = lt
        self.lte = lte
        self.is_int = is_int

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        p = path or []
        # Python 中 bool 是 int 的子类，需显式拦截
        if self.is_int:
            if not isinstance(val, int) or isinstance(val, bool):
                return [{"path": p, "val": val, "pred": "is_int"}]
        else:
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                return [{"path": p, "val": val, "pred": "is_number"}]

        errors = []
        if self.gt is not None and not (val > self.gt):
            errors.append({"path": p, "val": val, "pred": f"> {self.gt}"})
        if self.gte is not None and not (val >= self.gte):
            errors.append({"path": p, "val": val, "pred": f">= {self.gte}"})
        if self.lt is not None and not (val < self.lt):
            errors.append({"path": p, "val": val, "pred": f"< {self.lt}"})
        if self.lte is not None and not (val <= self.lte):
            errors.append({"path": p, "val": val, "pred": f"<= {self.lte}"})

        return errors if errors else None


class StringSpec(Spec):
    """字符串契约 (支持长度限制及正则表达式匹配)。"""

    def __init__(
        self,
        min_len: int | None = None,
        max_len: int | None = None,
        pattern: str | re.Pattern | None = None,
    ) -> None:
        self.min_len = min_len
        self.max_len = max_len
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        p = path or []
        if not isinstance(val, str):
            return [{"path": p, "val": val, "pred": "is_str"}]

        errors = []
        if self.min_len is not None and len(val) < self.min_len:
            errors.append({"path": p, "val": val, "pred": f"len >= {self.min_len}"})
        if self.max_len is not None and len(val) > self.max_len:
            errors.append({"path": p, "val": val, "pred": f"len <= {self.max_len}"})
        if self.pattern is not None and not self.pattern.match(val):
            errors.append(
                {"path": p, "val": val, "pred": f"matches {self.pattern.pattern}"}
            )

        return errors if errors else None


class BooleanSpec(Spec):
    """布尔值契约。"""

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        if not isinstance(val, bool):
            return [{"path": path or [], "val": val, "pred": "is_bool"}]
        return None


class CollOfSpec(Spec):
    """集合契约 (元素必须全部符合 element_spec，且支持长度边界)。"""

    def __init__(
        self, element_spec: Spec, min_len: int | None = None, max_len: int | None = None
    ) -> None:
        self.element_spec = element_spec
        self.min_len = min_len
        self.max_len = max_len

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        p = path or []
        if not isinstance(val, (list, tuple, set)):
            return [{"path": p, "val": val, "pred": "is_collection"}]

        errors = []
        if self.min_len is not None and len(val) < self.min_len:
            errors.append({"path": p, "val": val, "pred": f"len >= {self.min_len}"})
        if self.max_len is not None and len(val) > self.max_len:
            errors.append({"path": p, "val": val, "pred": f"len <= {self.max_len}"})

        # 校验子元素
        for i, elem in enumerate(val):
            elem_errors = self.element_spec.explain_data(elem, p + [i])
            if elem_errors:
                errors.extend(elem_errors)

        return errors if errors else None


class KeysSpec(Spec):
    """字典/哈希映射契约 (区分必需键 req 与可选键 opt 且针对各键分别定义契约)。"""

    def __init__(
        self, req: dict[str, Spec] | None = None, opt: dict[str, Spec] | None = None
    ) -> None:
        self.req = req or {}
        self.opt = opt or {}

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        p = path or []
        if not isinstance(val, dict):
            return [{"path": p, "val": val, "pred": "is_dict"}]

        errors = []
        # 验证必需键的存在性及匹配
        for k, k_spec in self.req.items():
            if k not in val:
                errors.append({"path": p + [k], "val": None, "pred": "missing_key"})
            else:
                field_errors = k_spec.explain_data(val[k], p + [k])
                if field_errors:
                    errors.extend(field_errors)

        # 验证可选键匹配
        for k, k_spec in self.opt.items():
            if k in val:
                field_errors = k_spec.explain_data(val[k], p + [k])
                if field_errors:
                    errors.extend(field_errors)

        return errors if errors else None


class AndSpec(Spec):
    """逻辑与契约 (值必须满足所有给定的 Specs)。"""

    def __init__(self, *specs: Spec) -> None:
        self.specs = specs

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        errors = []
        for k_spec in self.specs:
            spec_errors = k_spec.explain_data(val, path)
            if spec_errors:
                errors.extend(spec_errors)
        return errors if errors else None


class OrSpec(Spec):
    """逻辑或契约 (值只需满足给定的任意一个 Spec 即可)。"""

    def __init__(self, **specs: Spec) -> None:
        self.specs = specs

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        all_errors = {}
        valid_any = False
        for name, k_spec in self.specs.items():
            errors = k_spec.explain_data(val, path)
            if not errors:
                valid_any = True
                break
            all_errors[name] = errors

        if not valid_any:
            merged = []
            for name, errors in all_errors.items():
                for err in errors:
                    err_copy = dict(err)
                    err_copy["pred"] = f"分支 {name} 未通过: {err_copy.get('pred')}"
                    merged.append(err_copy)
            return merged
        return None


class PredicateSpec(Spec):
    """函数式谓词契约 (调用自定义的 Callable 进行断言校验)。"""

    def __init__(
        self, predicate: Callable[[Any], bool], name: str | None = None
    ) -> None:
        self.predicate = predicate
        self.name = name or getattr(predicate, "__name__", "custom_predicate")

    def explain_data(
        self, val: Any, path: list[Any] | None = None
    ) -> list[dict[str, Any]] | None:
        try:
            res = self.predicate(val)
        except Exception as e:
            return [
                {
                    "path": path or [],
                    "val": val,
                    "pred": f"在谓词 {self.name} 中抛出异常: {e}",
                }
            ]
        if not res:
            return [
                {"path": path or [], "val": val, "pred": f"未满足谓词断言 {self.name}"}
            ]
        return None


# ---------------------------------------------------------------------------
# 便捷的 Spec 工厂方法导出
# ---------------------------------------------------------------------------


def nil() -> Spec:
    """返回只能校验为 None 的契约。"""
    return NilSpec()


def any() -> Spec:
    """返回能校验通过任何值的契约。"""
    return AnySpec()


def integer(
    gt: int | None = None,
    gte: int | None = None,
    lt: int | None = None,
    lte: int | None = None,
) -> Spec:
    """返回整型数值校验契约。"""
    return NumberSpec(gt=gt, gte=gte, lt=lt, lte=lte, is_int=True)


def float_(
    gt: float | None = None,
    gte: float | None = None,
    lt: float | None = None,
    lte: float | None = None,
) -> Spec:
    """返回浮点型数值校验契约。"""
    return NumberSpec(gt=gt, gte=gte, lt=lt, lte=lte, is_int=False)


def string(
    min_len: int | None = None,
    max_len: int | None = None,
    pattern: str | re.Pattern | None = None,
) -> Spec:
    """返回字符串校验契约。"""
    return StringSpec(min_len=min_len, max_len=max_len, pattern=pattern)


def regex(pattern: str | re.Pattern) -> Spec:
    """返回正则表达式字符串匹配校验契约。"""
    return StringSpec(pattern=pattern)


def boolean() -> Spec:
    """返回布尔值校验契约。"""
    return BooleanSpec()


def coll_of(
    element_spec: Spec, min_len: int | None = None, max_len: int | None = None
) -> Spec:
    """返回集合及内部元素类型校验契约。"""
    return CollOfSpec(element_spec, min_len=min_len, max_len=max_len)


def keys(
    req: dict[str, Spec] | None = None, opt: dict[str, Spec] | None = None
) -> Spec:
    """返回字典映射键值校验契约。"""
    return KeysSpec(req=req, opt=opt)


def and_(*specs: Spec) -> Spec:
    """返回多重 Spec 逻辑与的复合校验契约。"""
    return AndSpec(*specs)


def or_(**specs: Spec) -> Spec:
    """返回多重 Spec 逻辑或的复合校验契约。"""
    return OrSpec(**specs)


def predicate(pred_callable: Callable[[Any], bool], name: str | None = None) -> Spec:
    """返回根据自定义 Python 函数进行断言的契约。"""
    return PredicateSpec(pred_callable, name)
