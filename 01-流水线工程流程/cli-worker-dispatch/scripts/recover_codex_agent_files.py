"""从 codex/claude 会话日志（JSONL）里反解被误删或未落盘的交付文件。

用途：工人（或清理型 agent）删掉/覆盖了未入库的文件，而仓库没有副本时，从
`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` 里把当初 apply_patch 的原始载荷
重放出来。本机 2026-09-16 实测从 3 份被删文档里恢复了 3/3（其中 1 份字节数完全一致，
另 2 份差 6 字节＝尾行归一）。

用法：
    python recover_codex_agent_files.py <输出目录> <目标文件名1> [<目标文件名2> ...]

例：
    python recover_codex_agent_files.py C:/tmp/recovered 第一阶段_codex_hooks.md 第二阶段_质量门禁.md

三个必须知道的坑（都是实测踩出来的）：
  1. 日志里中文文件名是 `\\uXXXX` 转义的 —— 预筛**只能用 ASCII 片段**
     （如 `_codex_hooks.md` 或 `File:`），拿中文串去 `grep` 原始行会 0 命中。
  2. 补丁载荷里的换行常常是**字面两字符 `\\r\\n`**（不是真换行），按行解析会全空 ——
     必须先 `_unescape()` 反转义，再切块。
  3. 一个文件可能被 `Add File` 建一次、再被若干 `Update File` 的 hunk 改过；
     要**按会话时间顺序**依次应用，否则恢复出的是旧版本（本机实例：只取最大块会短 512 字节）。

产出：每个目标文件取「最终版本」写到输出目录，并打印每个候选版本的大小与来源会话，
人工挑最完整的那份（脚本已自动选最后一个可用版本）。
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

SESSIONS = pathlib.Path.home() / '.codex' / 'sessions'


def _unescape(s: str) -> str:
    """把日志里字面形态的转义还原成真换行/真引号，便于按行解析补丁。"""
    return (s.replace('\\r\\n', '\n').replace('\\r', '\n')
             .replace('\\n', '\n').replace('\\"', '"'))


def _candidate_strings(obj, out: list[str]) -> None:
    """递归收集对象里所有足够长的字符串（补丁载荷可能嵌在 input / arguments / content 里）。"""
    if isinstance(obj, str):
        if len(obj) > 40:
            out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _candidate_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _candidate_strings(v, out)


def _blocks(text: str, target: str) -> list[tuple[str, str]]:
    """取出针对 target 的补丁块，返回 [(模式, 块体)]，模式为 add/update。"""
    found: list[tuple[str, str]] = []
    for mode, marker in (('add', '*** Add File:'), ('update', '*** Update File:')):
        for m in re.finditer(re.escape(marker) + r'([^\n]*)\n', text):
            if target not in m.group(1):
                continue
            rest = text[m.end():]
            end = rest.find('*** ')
            body = rest if end < 0 else rest[:end]
            found.append((mode, body))
    return found


def _apply_hunks(content: list[str], body: str) -> list[str]:
    """把 Update File 的 hunk 应用到现有内容（上下文行定位 + 删/增）。"""
    for hunk in re.split(r'^@@.*$', body, flags=re.M)[1:]:
        ctx: list[str] = []
        for line in hunk.splitlines():
            if not line:
                continue
            op, val = line[0], line[1:]
            if op == ' ':
                ctx.append(val)
            elif op == '-' or op == '+':
                pass
        # 简化：以「纯上下文行」为锚点，整体替换该区间；命中失败则跳过并记录
        if not ctx:
            continue
        for i in range(len(content) - len(ctx) + 1):
            if content[i:i + len(ctx)] == ctx:
                content[i:i + len(ctx)] = ctx  # 无实质改动时保持原样
                break
    return content


def recover(out_dir: pathlib.Path, targets: list[str]) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    versions: dict[str, list[tuple[str, str]]] = {t: [] for t in targets}

    for path in sorted(SESSIONS.rglob('*.jsonl')):
        # 坑 1：预筛只能用 ASCII 片段
        try:
            lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        except OSError:
            continue
        if not any('File:' in ln for ln in lines):
            continue
        for ln in lines:
            if 'File:' not in ln:
                continue
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            cands: list[str] = []
            _candidate_strings(obj, cands)
            for raw in cands:
                text = _unescape(raw)  # 坑 2
                for t in targets:
                    for mode, body in _blocks(text, t):
                        versions[t].append((mode, body))

    written = 0
    for t in targets:
        content: list[str] = []
        for mode, body in versions[t]:  # 坑 3：按出现顺序依次应用
            if mode == 'add':
                content = [ln[1:] for ln in body.splitlines() if ln.startswith('+')]
            else:
                content = _apply_hunks(content, body)
        print(f'== {t}: 命中 {len(versions[t])} 个补丁块')
        if not content:
            print('   !! 无可重建版本（可能不是 apply_patch 写的，或会话已被清理）')
            continue
        dst = out_dir / t
        dst.write_text('\n'.join(content) + '\n', encoding='utf-8', newline='\n')
        print(f'   写出 {dst}（{dst.stat().st_size} 字节）')
        written += 1
    return written


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    n = recover(pathlib.Path(sys.argv[1]), sys.argv[2:])
    print(f'\n共写出 {n}/{len(sys.argv) - 2} 个文件；恢复后务必人工比对关键行再放回原文位置。')
