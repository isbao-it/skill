#!/usr/bin/env python
"""契约产物校验器：把工人产出与「权威清单」机器比对，替掉人眼抽查。

典型场景：工人按任务卡实现了若干表/约束/用例，卡面又声称引用了权威设计文档里的
命名清单。本脚本一次跑完下列检查，任何一项失败 exit 1：

  1. 卡面映射行数、唯一性、字符合法性（小写 ASCII、物理名 ≤63）
  2. 长名截断规则：物理名 == 规范名前 46 字符去尾下划线 + "_" + sha256(规范全名)[:16]
  3. 与权威清单的双向差分（多出/缺失分别列出）
  4. 按类型（PK/UQ/IX/CK/FK）计数
  5. 测试用例名是否全部出现在断言映射段（默认 §2.1 → §4 的 Markdown 表格约定）
  6. 陈旧措辞扫描（旧状态、旧口径是否已清除）

用法：
  python verify_contract_artifacts.py \
    --exec-card  project/cards/02b/任务卡_x.md \
    --test-card  project/cards/02b/测试卡_x.md \
    --authority  project/架构方案.md --authority-start '#### 9.8.2' --authority-end '#### 9.8.3' \
    --expect-count 87

注意（踩过的坑）：--authority-start/--authority-end 必须切到**只含本次契约**的那一节。
窗口取大了会把后续补充节里的名字算进来，产生"冲突"假阳性（本机真实发生过一次）。
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import sys

MAP_ROW = re.compile(r'^\|\s*(PK|UQ|IX|CK|FK)\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`', re.M)
NAME = re.compile(r'\b(?:pk|uq|ix|fk|ck)_[a-z0-9_]+')
CASE_ROW = re.compile(r'^\|\s*(?:GWT-\d+)\s*\|\s*`[^`]+`\s*\|\s*`(test_[a-z0-9_]+)`', re.M)
DEFAULT_STALE = ['执行前先报告等批准', '待批准', '尚未批准', 'P1–P4 待']


def read(path: str) -> str:
    """读 UTF-8 文本；读不到直接抛错，不静默吞。"""
    return pathlib.Path(path).read_text(encoding='utf-8')


def mapping_rows(text: str) -> list[tuple[str, str, str]]:
    """抓「| 类型 | 规范全名 | 物理字面名 |」映射行；从第一个 #### `表` 标题起扫，避开前面规则说明表。"""
    start = text.find('#### `')
    return MAP_ROW.findall(text[start:] if start >= 0 else text)


def check(label: str, ok: bool, detail: str = '') -> bool:
    """打印带 ✅/❌ 的单条检查结果并返回布尔值。"""
    print(f'{"✅" if ok else "❌"} {label}{("  → " + detail) if detail else ""}')
    return ok


def main() -> int:  # noqa: C901 - 线性检查清单，拆函数反而更难核对
    ap = argparse.ArgumentParser()
    ap.add_argument('--exec-card', required=True)
    ap.add_argument('--test-card', required=True)
    ap.add_argument('--authority', help='权威清单所在文件')
    ap.add_argument('--authority-start', help='权威节起始锚点')
    ap.add_argument('--authority-end', help='权威节结束锚点')
    ap.add_argument('--expect-count', type=int, help='预期映射条数')
    ap.add_argument('--stale', nargs='*', default=DEFAULT_STALE)
    args = ap.parse_args()

    exec_txt, test_txt = read(args.exec_card), read(args.test_card)
    rows, test_rows = mapping_rows(exec_txt), mapping_rows(test_txt)
    phys = [r[2] for r in rows]
    ok = True

    ok &= check(f'执行卡映射行数 = {len(rows)}'
                + (f'（预期 {args.expect_count}）' if args.expect_count else ''),
                args.expect_count is None or len(rows) == args.expect_count)
    ok &= check('物理名唯一', len(set(phys)) == len(phys), f'{len(phys)} 行 / {len(set(phys))} 唯一')
    bad = [p for p in set(phys) if not re.fullmatch(r'[a-z0-9_]+', p) or len(p) > 63]
    ok &= check('命名合法（小写 ASCII、≤63）', not bad, str(bad))
    ok &= check('两卡映射集合一致', set(phys) == {r[2] for r in test_rows})

    trunc = [(c, p) for _, c, p in rows if c != p]
    mis = [(c, p) for c, p in trunc
           if p != c[:46].rstrip('_') + '_' + hashlib.sha256(c.encode()).hexdigest()[:16]]
    ok &= check(f'截断名 {len(trunc)} 条，哈希重算一致', not mis, str(mis))

    kinds: dict[str, int] = {}
    for k, _, _ in rows:
        kinds[k] = kinds.get(k, 0) + 1
    print(f'   类型计数: {kinds}')

    if args.authority:
        auth = read(args.authority)
        if args.authority_start and args.authority_end:
            auth = auth[auth.index(args.authority_start):auth.index(args.authority_end)]
        names = set(NAME.findall(auth))
        extra, missing = sorted(set(phys) - names), sorted(names - set(phys))
        print(f'   权威清单 {len(names)} 名；卡面多出 {len(extra)}、缺失 {len(missing)}')
        if extra:
            print('   多出:', extra)
        if missing:
            print('   缺失:', missing)

    cases = CASE_ROW.findall(test_txt)
    seg4 = test_txt[test_txt.find('## 4.'):test_txt.find('## 5.')]
    mapped = set(re.findall(r'(test_[a-z0-9_]+)', seg4))
    unmapped = [c for c in cases if c not in mapped]
    ok &= check(f'用例映射完整（§2.1 {len(cases)} 条 → §4）', not unmapped, str(unmapped))

    for word in args.stale:
        hit = exec_txt.count(word) + test_txt.count(word)
        ok &= check(f'陈旧措辞「{word}」已清除', hit == 0, f'命中 {hit}')

    print('\n结论:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
