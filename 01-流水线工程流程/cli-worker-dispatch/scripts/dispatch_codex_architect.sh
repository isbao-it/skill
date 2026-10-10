#!/usr/bin/env bash
# 用 Codex 跑「出卡/架构」类任务（与 dispatch_dsh_worker.sh 对称）。
#
# 为什么要写成脚本再后台启动（而不是把超长 prompt 内联进 terminal 调用）：
#   实测内联方式会让调用方工具在 420s 处超时且**不登记后台会话** —— 调用方看不到进度，
#   也拿不到 session id，容易误判成"没跑起来"。脚本化后后台启动即可正常登记、可 tail。
#
# 用法：bash dispatch_codex_architect.sh <项目根> <派题文件> <日志输出>
#   例：bash dispatch_codex_architect.sh "C:/work/.../bao-kuan-xin-fa" "project/outputs/13d_brief_v2.txt" "project/outputs/13d_出卡日志.md"
set -uo pipefail

PROJ="${1:?用法: dispatch_codex_architect.sh <项目根> <派题文件> <日志输出>}"
BRIEF="${2:?缺少派题文件}"
LOG="${3:?缺少日志输出路径}"

cd "$PROJ" || { echo "[codex] 无法进入项目目录: $PROJ"; exit 2; }
if [ ! -f "$BRIEF" ]; then echo "[codex] 派题文件不存在: $BRIEF"; exit 2; fi

echo "[codex] 项目=$PROJ  派题=$BRIEF（$(wc -c < "$BRIEF") 字节）  开始=$(date '+%F %T')"

codex exec \
  -m gpt-6-sol \
  -c model_reasoning_effort="high" \
  -c sandbox_mode="workspace-write" \
  -c approval_policy="never" \
  -C "$PROJ" \
  --skip-git-repo-check \
  -o "$LOG" \
  "$(cat "$BRIEF")"

echo "[codex] 结束=$(date '+%F %T') EXIT=$?"
