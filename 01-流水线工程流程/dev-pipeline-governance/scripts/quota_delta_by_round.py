#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按「会话/轮次」统计 Codex 额度成本（rate_limits 百分点口径）。

用法:
    python quota_delta_by_round.py [YYYY-MM-DD ...]      # 缺省=今天

输出:
    每会话一行: 开始时刻 / 模型 / 用量事件数 / primary 起止百分点 / Δ

为什么不用 input token 数:
    订阅额度按「模型档位 + reasoning effort」扣, 与 input 大小不成比例。
    实测同一账号: sol+high 9 个用量事件 = 5h 窗口 +5 点;
                  luna 122 个事件 / 544 万 input 也才 +5 点。
    两个口径不可互换 —— 别拿 token 数换算额度节省。

注意:
    百分点是**窗口快照**, 同一窗口内多路并发会互相抬高读数;
    跨窗口(5h)的会话其 Δ 会低估(int 窗口滚动会抵消一部分), 判读按「同一时间段的会话横比」, 不要纵向相加。
"""
import datetime
import glob
import os
import re
import sys

MODEL_RE = re.compile(r'"model":"([^"]+)"')
TS_RE = re.compile(r'"timestamp":"([^"]+)"')
PRIMARY_RE = re.compile(r'"primary":\{[^}]*?"used_percent":([0-9.]+)')


def scan(path):
    model = None
    started = None
    events = 0
    pcts = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if model is None:
                m = MODEL_RE.search(line)
                if m:
                    model = m.group(1)
            if started is None and '"timestamp"' in line:
                m = TS_RE.search(line)
                if m:
                    started = m.group(1)
            if '"rate_limits"' in line:
                events += 1
                m = PRIMARY_RE.search(line)
                if m:
                    pcts.append(float(m.group(1)))
    return model, started, events, pcts


def main():
    days = sys.argv[1:] or [datetime.date.today().isoformat()]
    root = os.path.expanduser('~/.codex/sessions')
    for day in days:
        pattern = os.path.join(root, *day.split('-'), '*.jsonl')
        files = sorted(glob.glob(pattern))
        print(f'== {day}  会话 {len(files)} 个  ({pattern})')
        if not files:
            continue
        print(f'{"started":21} {"model":12} {"ev":>3} {"primary":>13} {"delta":>6}')
        for path in files:
            model, started, events, pcts = scan(path)
            if not pcts:
                print(f'{(started or "?"):21} {(model or "?"):12} {events:>3} '
                      f'{"(无 rate_limits: 请求未发出/探针失败)":>13}')
                continue
            delta = pcts[-1] - pcts[0]
            span = f'{pcts[0]:.0f}->{pcts[-1]:.0f}'
            print(f'{(started or "?"):21} {(model or "?"):12} {events:>3} {span:>13} {delta:>+6.0f}')


if __name__ == '__main__':
    main()
