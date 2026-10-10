#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Codex CLI 会话额度审计 —— 量化「额度到底烧在哪」。

为什么需要它：用户抱怨「额度不够 / 消耗太快」时，凭感觉优化会优化错地方。
本机实测（2026-09）的真实分布是 input : output = 92 : 1 —— 额度烧在「每轮重放
上下文」，不在「写代码」。本脚本把这个乘法结构量化出来，再谈优化。

原理：~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl 里每条 token_count payload 的
total_token_usage 是**累计值**；相邻两次累计之差 ≈ 该轮重放的上下文长度。
于是：单会话成本 ≈ Σ(每轮上下文) ≈ 轮数 × 平均每轮上下文长度。

用法：
    python codex_quota_audit.py                  # 汇总 + Top 15 会话
    python codex_quota_audit.py --per-turn       # 追加每轮上下文重放统计
    python codex_quota_audit.py --days 7         # 只看最近 7 天
    python codex_quota_audit.py --json out.json  # 同时落机器可读结果

退出码：0 正常；1 找不到会话目录。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import json
import os
import sys


def session_files(base: str, days: int | None = None) -> list[str]:
    """列出会话 jsonl 路径（按 mtime 升序）；days 非空时只保留最近 N 天。"""
    files = glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True)
    if days:
        cutoff = dt.datetime.now().timestamp() - days * 86400
        files = [f for f in files if os.path.getmtime(f) >= cutoff]
    return sorted(files, key=os.path.getmtime)


def scan(path: str) -> dict:
    """扫描单个会话，返回 token 累计、轮数、每轮重放量、首条用户提示等。

    容错：JSON 坏行直接跳过；会话没有 token_count 时 turns=0，由调用方过滤。
    """
    rec = {
        "path": path, "size": os.path.getsize(path), "model": None, "start": None,
        "input": 0, "cached": 0, "output": 0, "total": 0, "turns": 0,
        "replays": [], "prompt": None,
    }
    try:
        fh = open(path, encoding="utf-8", errors="ignore")
    except OSError:
        return rec
    with fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if rec["start"] is None and ev.get("timestamp"):
                rec["start"] = ev["timestamp"]
            payload = ev.get("payload")
            if not isinstance(payload, dict):
                continue
            ptype = payload.get("type")
            if ptype == "token_count":
                usage = (payload.get("info") or {}).get("total_token_usage") or {}
                cur = usage.get("input_tokens", 0) or 0
                if rec["turns"]:                      # 累计值之差 = 本轮重放量
                    rec["replays"].append(max(cur - rec["input"], 0))
                rec["input"] = cur
                rec["cached"] = usage.get("cached_input_tokens", 0) or 0
                rec["output"] = usage.get("output_tokens", 0) or 0
                rec["total"] = usage.get("total_tokens", 0) or 0
                rec["turns"] += 1
            elif ptype == "message" and payload.get("role") == "user" and rec["prompt"] is None:
                content = payload.get("content")
                if isinstance(content, list):
                    text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                else:
                    text = str(content)
                text = " ".join(text.split())
                # 跳过环境上下文/规则文件注入，只留真人下的第一句指令
                if "environment_context" not in text and "AGENTS.md" not in text[:200]:
                    rec["prompt"] = text[:110]
            model = payload.get("model")
            if model and model != "codex-auto-review":
                rec["model"] = model
    return rec


def fmt(n: int | float | None) -> str:
    """千分位格式化，0/None 一律显示 0。"""
    return f"{int(n):,}" if n else "0"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Codex CLI 会话额度审计")
    ap.add_argument("--base", default=os.path.expanduser("~/.codex/sessions"),
                    help="会话目录（默认 ~/.codex/sessions）")
    ap.add_argument("--days", type=int, default=None, help="只看最近 N 天的会话")
    ap.add_argument("--top", type=int, default=15, help="列出的会话条数（默认 15）")
    ap.add_argument("--per-turn", action="store_true", help="追加每轮上下文重放统计")
    ap.add_argument("--json", dest="json_out", default=None, help="结果落 JSON 的路径")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.base):
        print(f"找不到会话目录：{args.base}", file=sys.stderr)
        return 1

    recs = [scan(p) for p in session_files(args.base, args.days)]
    counted = [r for r in recs if r["turns"]]
    if not counted:
        print("没有可统计的会话（没有 token_count 记录）。")
        return 0

    tot_in = sum(r["input"] for r in counted)
    tot_cached = sum(r["cached"] for r in counted)
    tot_out = sum(r["output"] for r in counted)
    tot_turns = sum(r["turns"] for r in counted)

    print(f"会话数 {len(recs)}（含 token 统计 {len(counted)}）  轮数合计 {fmt(tot_turns)}")
    print(f"input {fmt(tot_in)}  cached {fmt(tot_cached)}  output {fmt(tot_out)}")
    if tot_out:
        print(f"input : output = {tot_in / tot_out:.0f} : 1"
              "   ← 远大于 1 = 额度烧在上下文重放，不是产出")
    if tot_in:
        print(f"缓存命中 {tot_cached / tot_in:.0%}（前缀缓存只打折，不免费）")

    print(f"\n{'时间':<17}{'模型':<17}{'input':>12}{'out':>9}{'轮':>5}{'每轮重放':>10}  首条提示")
    for r in sorted(counted, key=lambda x: -x["input"])[:args.top]:
        avg = sum(r["replays"]) / len(r["replays"]) if r["replays"] else 0
        print(f"{str(r['start'])[:16]:<17}{str(r['model']):<17}{fmt(r['input']):>12}"
              f"{fmt(r['output']):>9}{r['turns']:>5}{avg / 1000:>9.0f}k  {(r['prompt'] or '')[:70]}")

    if args.per_turn:
        print("\n每轮上下文重放（按总量 Top 10）：")
        for r in sorted(counted, key=lambda x: -sum(x["replays"]))[:10]:
            reps = r["replays"]
            if not reps:
                continue
            print(f"  {str(r['start'])[:16]}  轮 {r['turns']:>3}  首轮 {reps[0] / 1000:>6.0f}k"
                  f"  末轮重放 {reps[-1] / 1000:>6.0f}k  最大 {max(reps) / 1000:>6.0f}k")

    models = collections.Counter(r["model"] for r in counted)
    print("\n模型分布：" + "、".join(f"{k or '未知'}×{v}" for k, v in models.most_common()))

    if args.json_out:
        payload = {
            "totals": {"sessions": len(recs), "counted": len(counted), "turns": tot_turns,
                       "input_tokens": tot_in, "cached_input_tokens": tot_cached,
                       "output_tokens": tot_out},
            "sessions": counted,
        }
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"已写 {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
