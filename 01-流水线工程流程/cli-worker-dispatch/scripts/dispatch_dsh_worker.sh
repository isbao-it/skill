#!/usr/bin/env bash
# 用 DSH（DeepSeek Harness）headless 工人跑一张卡。
#
# 为什么这么写：
#  - 必须 cd 到项目目录再启动 —— dsh 把「启动目录」当作工作区根，也是沙箱白名单；
#  - 必须给独立的 DSH_HOME —— 桌面 App 的 ~/.dsh/.credentials.yaml 格式与 CLI 契约冲突（会 boot 失败）；
#  - 密钥走进程环境变量，不落盘、不进日志；
#  - 任务正文从文件读，避免命令行引号地狱。
#
# 用法：dispatch_dsh_worker.sh <项目目录> <任务正文文件> <日志文件> [worker_home]
# 后台派工：交给 Hermes 的 terminal(background=true, notify_on_complete=true) 调本脚本。
set -uo pipefail

PROJ="${1:?用法: dispatch_dsh_worker.sh <项目目录> <任务正文文件> <日志文件> [worker_home]}"
TASK_FILE="${2:?缺任务正文文件}"
LOG="${3:?缺日志文件}"
DSH_HOME_DIR="${4:-C:/Users/<user>/.dsh-worker}"
DSH_BIN="C:/Users/<user>/.dsh/profiles/node_modules/@deepseek-ai/dsh/lib/bin.js"
CONFIG="C:/Users/<user>/AppData/Local/hermes/config.yaml"

if [ ! -f "$TASK_FILE" ]; then echo "任务正文文件不存在: $TASK_FILE"; exit 2; fi
if [ ! -f "$DSH_BIN" ]; then echo "找不到 dsh CLI: $DSH_BIN"; exit 2; fi
mkdir -p "$(dirname "$LOG")"

# 沙箱模式：默认放开为 danger-full-access（2026-09-20 用户拍板 A 方案）。
# 原因：默认 workspace-write 下 pytest 用 mkdir(mode=0o700) 建的 basetemp 与每个测试 tmp 目录，
# DSH 沙箱视为「仅属主可访问」，连沙箱内的工人自己也枚举/写入不了 —— 定向用例必挂 8 个 tmp_path 用例。
# 三次对照实测见 references/dsh-headless-worker.md §9（danger-full-access 下 22 passed）。
# 代价：沙箱保护失效；补偿控制 = 家规 AGENTS.md + 禁 git/联网 + 卡面白名单
#       + 事后范围审计 scripts/audit_worker_scope.py + 调用方独立重跑验收。
# 允许外部覆盖（便于做对照实验）：把环境变量 DSH_PERMISSION_MODE 设为 workspace-write 即可。
export DSH_PERMISSION_MODE="${DSH_PERMISSION_MODE:-danger-full-access}"

# 密钥取值顺序：环境变量 > 工人家凭据文件 > Hermes config（兜底）；只经进程环境传递，不写日志。
KEY="${DEEPSEEK_API_KEY:-}"
KEY_SOURCE="环境变量"
if [ -z "${KEY:-}" ]; then
  CRED_FILE="$DSH_HOME_DIR/.credentials.yaml"
  if [ -f "$CRED_FILE" ]; then
    KEY=$(python -c "import yaml,sys;d=yaml.safe_load(open(sys.argv[1],encoding='utf-8')) or {};print(d.get('DEEPSEEK_API_KEY',''))" "$CRED_FILE" 2>/dev/null)
    KEY_SOURCE="工人家凭据文件"
  fi
fi
if [ -z "${KEY:-}" ]; then
  KEY=$(python -c "import yaml;c=yaml.safe_load(open(r'$CONFIG',encoding='utf-8'));print([p for p in c['custom_providers'] if p['name']=='deepseek'][0]['api_key'])" 2>/dev/null)
  KEY_SOURCE="Hermes config 兜底"
fi
if [ -z "${KEY:-}" ]; then
  echo "取不到 DeepSeek 密钥：检查 ${DSH_HOME_DIR}/.credentials.yaml"
  exit 2
fi

cd "$PROJ" || exit 2

# 日志里的路径统一成 Windows 形式（MSYS 会把 Windows TEMP 显示成 /tmp，直接打印会误导读者）
PROJ_SHOWN=$(cygpath -m "$PROJ" 2>/dev/null || echo "$PROJ")
{
  echo "[dispatch] 模式=$DSH_PERMISSION_MODE 密钥来源=$KEY_SOURCE（值不打印）"
  echo "[dispatch] 项目=$PROJ_SHOWN home=$DSH_HOME_DIR 任务=$(wc -c < "$TASK_FILE" | tr -d ' ')字节 开始=$(date '+%F %T')"
} | tee "$LOG"

DSH_HOME="$DSH_HOME_DIR" DEEPSEEK_API_KEY="$KEY" \
  node "$DSH_BIN" --profile headless "$(cat "$TASK_FILE")" >> "$LOG" 2>&1
CODE=$?
echo "[dispatch] 结束=$(date '+%F %T') EXIT=$CODE" | tee -a "$LOG"
exit $CODE
