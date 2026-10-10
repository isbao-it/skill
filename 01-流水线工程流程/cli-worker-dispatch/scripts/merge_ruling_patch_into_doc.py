#!/usr/bin/env python
"""把"裁决稿 / 架构补充说明"里的补丁文本并入设计文档（幂等 + 自校验）。

实战背景：编码代理（架构师会话）产出的裁决稿通常带一段
「可直接粘贴进架构文档的 Markdown 补丁文本」，按「插入位置一/二/三…」分块，
另加若干"必须同步替换的旧示例"。手工复制粘贴易漏、易重复；用本模块按锚点插入。

两种形态：
  A. 插入式 —— 补丁源用标题分隔块，每块插到目标文档的一个锚点字符串之前
  B. 替换式 —— 给出 (old, new) 对，直接 replace 一次

硬要求（都是踩过的坑）：
  1. **幂等**：目标文档已含该块的指纹（如新标题、"仓储查询确定性"等短语）→ 跳过，不重复插入
  2. **先找锚点再改**：锚点缺失必须报错并停下，绝不"猜一个位置"写进去
  3. **打印每次动作**：插入了多少字符、行数从多少变到多少
  4. **收尾自校验**：新标记都在 + 关键相对顺序正确（例如 §9.8.7 必须在 §10 之前）

用法（改下方 CONFIG 后直接运行，或 import 后在自己的脚本里调）::

    python merge_ruling_patch_into_doc.py
"""

from __future__ import annotations

import pathlib

# ------------------------------ CONFIG ------------------------------
DOC = pathlib.Path(r"C:/work/dev/projects/<proj>/project/需求分析与架构方案.md")
SOURCE = pathlib.Path(r"C:/work/dev/projects/<proj>/project/outputs/03/架构补充_03八项缺口裁决.md")

# 插入式：(块的起止标题(在 SOURCE 里), 目标锚点(在 DOC 里), 幂等指纹)
INSERTS: list[tuple[str, str, str]] = [
    ("### 插入位置一：§4.1“五步检索”之后", "### 4.2", "仓储查询确定性"),
    ("### 插入位置二：§9.6的`usage_events`表行之后", "### 9.7", "用量幂等作用域修订"),
    ("### 新增位置四：接在§9.8.6之后", "## 10. API 设计", "#### 9.8.7"),
    # 块以 "### 插入位置二…" 这类标题结尾 → 起止用 (起始标题, 下一块标题)
]

# 替换式：旧口径 → 新口径（只替换一次；命中 0 次要报警）
REPLACES: list[tuple[str, str]] = [
    ('"week_start": "2026-08-28T00:00:00+08:00",', '"week_start": "2026-08-31T00:00:00Z",'),
]

# 收尾自校验：(A, B) 要求 A 在 B 之前
ORDER: list[tuple[str, str]] = [("#### 9.8.7", "## 10. API 设计")]
# --------------------------------------------------------------------


def extract(source_text: str, start_marker: str, end_marker: str) -> str:
    """取补丁源里两段标题之间的正文（块的边界）。"""
    i = source_text.index(start_marker) + len(start_marker)
    j = source_text.index(end_marker)
    return source_text[i:j].strip("\n")


def insert_before(doc: str, anchor: str, text: str, fingerprint: str) -> tuple[str, str]:
    """把 text 插到 anchor 之前；已含 fingerprint 则跳过。返回 (新文档, 动作说明)。"""
    if fingerprint in doc:
        return doc, f"跳过（已含「{fingerprint}」）"
    if anchor not in doc:
        raise SystemExit(f"锚点缺失，停止：{anchor!r}")
    idx = doc.index(anchor)
    return doc[:idx] + text + "\n\n" + doc[idx:], f"已插入 {len(text)} 字符"


def main() -> None:
    doc = DOC.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    lines_before = len(doc.splitlines())
    log: list[str] = []

    for start, anchor, fingerprint in INSERTS:
        # 块的结束边界 = 补丁源里下一个 "### " 标题；简单起见取 CONFIG 顺序里的下一项起始标题
        following = [s for s, _, _ in INSERTS if s != start]
        end = next((s for s in following if source.index(s) > source.index(start)), "### ")
        block = extract(source, start, end)
        doc, action = insert_before(doc, anchor, block, fingerprint)
        log.append(f"  {start[:28]}… → {action}")

    for old, new in REPLACES:
        hits = doc.count(old)
        if hits == 1:
            doc = doc.replace(old, new)
            log.append(f"  替换式：命中 1 次，已替换（{old[:32]}…）")
        else:
            log.append(f"  !! 替换式：命中 {hits} 次（应恰为 1），未改动，请人工核对")

    DOC.write_text(doc, encoding="utf-8", newline="\n")
    after = DOC.read_text(encoding="utf-8")

    print("\n".join(log))
    print(f"\n行数: {lines_before} → {len(after.splitlines())}")
    for a, b in ORDER:
        ok = a in after and b in after and after.index(a) < after.index(b)
        print(f"  顺序校验 {a} 在 {b} 之前: {ok}")
    missing = [f for _, _, f in INSERTS if f and f not in after]
    print("  缺失指纹:", missing or "无")


if __name__ == "__main__":
    main()
