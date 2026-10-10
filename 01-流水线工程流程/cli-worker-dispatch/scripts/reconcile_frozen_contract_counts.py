#!/usr/bin/env python
"""冻结契约测试的"期望字典 vs 真实对象"逐项核对（只读，不改任何项目文件）。

用途：拿"契约测试红了"这种不确定状态快速分流成两类——
  A. **只是总数常数没同步**（字典本身正确）→ 一行常数改动即可；
  B. **字典与真实对象真的不一致**（漏了字段/多写了字段）→ 需要判断是实现漏字段还是期望写错。

背景：这类测试常写成
    expected = {"SomeDTO": {"a", "b"}, ...}
    assert sum(len(v) for v in expected.values()) == N
    for name, fields in expected.items():
        assert set(getattr(entities, name).model_fields) == fields
总数断言在前，逐项断言在后 → 总数一红，逐项断言根本没跑到，
于是"到底只是常数陈旧，还是字段集也错了"肉眼看不出来。这个脚本补上这一步。

用法：
    python reconcile_frozen_contract_counts.py <测试文件或源码文件> <模块名> <变量名> [--member=model_fields]

  <模块名>      提供真实对象的 Python 模块（如 app.domain.entities）
  <变量名>      测试文件里那个期望字典的变量名（如 expected_new_fields）
  --member      取对象上的哪个属性做比对，默认 model_fields（Pydantic）；也可传 __annotations__ 等

退出码：0 = 全部一致（只差常数时也返回 0，并在输出里给出正确总数）；1 = 存在不一致。

实测（2026-09-18 卡11）：
    期望 DTO 数: 24 字段总数: 185
    不一致的 DTO 数: 0
    ⇒ 结论 185 才是正确常数，测试里的 165 是陈旧值，改常数即可，不必回退实现。
"""

from __future__ import annotations

import argparse
import ast
import importlib
import sys
from pathlib import Path


def extract_literal(source: str, name: str) -> object:
    """从源码里抽出 ``name = {...}`` 的字面量并求值（不做整体 exec）。"""
    needle = f"{name} = "
    idx = source.index(needle)
    start = idx + len(needle)
    # 用 AST 找到该赋值语句，避免手写括号配对
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise SystemExit(f"未找到赋值语句：{needle}（起点 {start}）")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("test_file")
    parser.add_argument("module")
    parser.add_argument("var_name")
    parser.add_argument("--member", default="model_fields")
    args = parser.parse_args()

    source = Path(args.test_file).read_text(encoding="utf-8")
    expected = extract_literal(source, args.var_name)
    module = importlib.import_module(args.module)

    total = sum(len(v) for v in expected.values())
    print(f"期望条目数: {len(expected)}  字段/成员总数: {total}")

    mismatches: list[tuple[str, str]] = []
    for key, wanted in expected.items():
        obj = getattr(module, key, None)
        if obj is None:
            mismatches.append((key, "目标模块里没有这个对象"))
            continue
        real = set(getattr(obj, args.member))
        missing, extra = sorted(real - set(wanted)), sorted(set(wanted) - real)
        if missing or extra:
            mismatches.append((key, f"少 {missing} 多 {extra}"))

    print(f"不一致条目数: {len(mismatches)}")
    for key, detail in mismatches:
        print(f"  - {key}: {detail}")
    if not mismatches:
        print(f"结论：字典本身正确，测试里的期望总数应为 {total}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
