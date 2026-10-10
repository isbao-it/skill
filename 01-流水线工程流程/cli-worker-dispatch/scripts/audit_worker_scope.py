"""审计工人改动范围：只允许白名单内的路径被新增/修改/删除。

为什么需要：DSH 工人跑在 danger-full-access（沙箱已放开，见 references/dsh-headless-worker.md §9），
沙箱不再兜底，"只改白名单"就要靠事后核对。工人越界（顺手改文档 / 清目录 / 动别的卡）是高频违规。

用法：
    python audit_worker_scope.py <项目根> [--allow <前缀> ...] [--json]
说明：
    - 用 `git status --porcelain=v1 -uall` 取真实改动面（含未跟踪文件），不读工人的自报；
    - 每条改动路径需匹配任一 --allow 前缀（前缀按 '/' 归一化后做前向匹配，大小写不敏感）；
    - 有越界即打印明细并退出码 1；全部落在白名单内退出码 0。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _normalize(path: str) -> str:
    """把路径归一成 '/' 分隔、小写、去首尾引号，便于做前缀比较。"""
    text = path.strip().strip('"').replace("\\", "/")
    return text.lower().lstrip("./")


def collect_changes(project: Path) -> list[tuple[str, str]]:
    """返回 [(状态码, 相对路径)]；状态码取 porcelain 的前两列（如 ' M'、'??'）。"""
    result = subprocess.run(
        ["git", "-C", str(project), "-c", "core.quotepath=false", "status", "--porcelain=v1", "-uall"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"git status 失败（{result.returncode}）：{result.stderr.strip()}")
    changes: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:]
        if " -> " in path:  # 重命名：取新路径
            path = path.split(" -> ", 1)[1]
        changes.append((code, path))
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="审计工人改动是否越出白名单")
    parser.add_argument("project", help="项目根目录")
    parser.add_argument("--allow", action="append", default=[], help="允许的前缀（可多次）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args(argv)

    project = Path(args.project)
    if not project.is_dir():
        raise SystemExit(f"项目根不存在：{project}")

    allows = [_normalize(item) for item in args.allow]
    changes = collect_changes(project)

    inside: list[dict[str, str]] = []
    outside: list[dict[str, str]] = []
    for code, path in changes:
        record = {"code": code, "path": path}
        key = _normalize(path)
        (inside if any(key.startswith(prefix) for prefix in allows) else outside).append(record)

    if args.json:
        print(json.dumps({"inside": inside, "outside": outside}, ensure_ascii=False, indent=2))
    else:
        print(f"改动合计 {len(changes)} 项：白名单内 {len(inside)}，越界 {len(outside)}")
        for record in outside:
            print(f"  [越界] {record['code']} {record['path']}")
        if not outside:
            print("  ✓ 全部落在白名单内")
    return 1 if outside else 0


if __name__ == "__main__":
    sys.exit(main())
