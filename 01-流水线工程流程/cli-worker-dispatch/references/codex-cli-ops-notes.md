# Codex CLI 运维细节（2026-09-14 实测，codex-cli 0.154.0 / Windows + git-bash）

SKILL.md 各节的细节支撑。带「实测」字样的均为本机验证过的行为，不是文档推测。

## 1. 模型与版本门禁

| 模型名 | 状态 |
|---|---|
| `gpt-6-sol` | **高/中两档默认**（出卡/架构/裁决/写码/机械修复）：2026-09-25 实测可用（CLI 0.157.0）；高档配 `high`、中档配 `medium` |
| `gpt-6-luna` | **低档默认**（文档同步、格式、探活，配 `low`）：2026-09-25 实测可用。**不要用它顶中档**——用户定的中档是 `gpt-6-sol`+`medium` |
| `gpt-6-terra` | **不可用**：400 `is not supported when using Codex with a ChatGPT account`（6 代无 terra） |
| `gpt-6-astra` | 可用但**禁用**（消耗太快），除非用户当次点名 |
| `gpt-5.6-sol` / `gpt-5.6-luna` / `gpt-5.6-terra` | 仍可用（5.6 家族）；**已不是默认**——2026-09-25 用户纠正：派卡未跟上 CLI 升级，默认应走 6 代 |
| `gpt-5.6-astra` | **不存在**：400 `is not supported when using Codex with a ChatGPT account` |

- 清单速查：`grep -o '"gpt-[^"]*"' ~/.codex/models_cache.json | sort -u`（缓存滞后于服务端）
- `warning: Model metadata for <name> not found. Defaulting to fallback metadata` 仍可能跑通，不必据此换模型
- 两类模型报错要分清：`requires a newer version of Codex`（升 CLI）vs `is not supported … ChatGPT account`（这个模型名在该账号通道不存在，升级无解）

## 2. 命令形态

```bash
# 一次性执行（非交互，不需要 pty）
codex exec -m gpt-6-sol -c model_reasoning_effort="high" \
  -c sandbox_mode="workspace-write" -c approval_policy="never" \
  -C <项目根> --skip-git-repo-check -o <项目内路径>/log.md "<派工指令>"

# 续同一场会话（保上下文）；resume 只认 -c，不认 -m / -s / -C：
codex exec resume <session-id> -c model="gpt-6-sol" -c model_reasoning_effort="high" \
  -c sandbox_mode="workspace-write" -c approval_policy="never" "<追问>"
codex exec resume --last "<追问>"        # 不记得 id 时
```

- 长任务用 `terminal(background=true, notify_on_complete=true)`；前台 timeout 上限 600s
- `-o` 便于调用方读回验收，但**不能替代让工人自己写产出文件**
- session id 从输出头部 `session id:` 抓取并落盘（调用方上下文会被压缩，别只记在脑子里）
- **`resume` 的三条硬约束**（0.157.0 实测，犯任一条会直接 exit 2 且不跑）：
  1. **不认 `-C`**（报 `unexpected argument '-C' found`）→ 想在哪跑就**先 `cd` 到那**；`resume` 按 **cwd 过滤会话**（`--all` 才禁过滤），跨目录续会话必须 cd 到原目录，否则找不到会话。
  2. 不认 `-m` / `-s`，模型与沙箱一律走 `-c model="..."`、`-c sandbox_mode="workspace-write"`。
  3. 端口与执行纪律：**工人一律新会话**，`resume` 只用于抢救被掐断的同一轮；跨片/跨轮的收口轮用**新会话 + 自带背景的窄派工单**（更可预测，也免踩上述坑）。
- 会话档案（取证 / 捞被掐断的最终答复）：`~/.codex/sessions/YYYY/MM/DD/rollout-<iso>-<session-id>.jsonl`

## 2.1 派工与合并的三个实测坑（0.157.0，2026-09-26）

1. **派工单必须写绝对解释器路径**：只给环境变量（如 `$CARD14_PYTHON`）时，工人**不会**继承（脚本导出的变量在手动派工时不生效），会退回系统 `python` → 缺 `alembic` 等依赖 → **收集阶段 exit 4，看起来像代码失败**。派工单里直接写 `C:/.../.venv/Scripts/python.exe`，并禁裸 `python`。连续坑掉两轮工人才定位到。
2. **带副作用的脚本禁止管道进 `head`/`tail`**：`bash script.sh | head -40` 在脚本输出够 40 行时 `head` 关闭管道 → **SIGPIPE 把脚本掐死**，后续段（复制/提交）静默不执行。要截断就先重定向到日志文件，再读日志。
3. **复制式合并必须核对行尾**：工人产物常是 CRLF/LF **混合**（`file` 会显示 "CRLF, LF line terminators"），直接 `cp` 回主仓库会产出**整文件伪 diff**（`git diff` 上万行）。合并后要 `git diff --numstat` 核增量是否只是预期的小改动；若整文件都变，按主仓库约定统一行尾（本项目 CRLF）再核。

4. **工人自报 FAIL 常是环境假失败，验收方必须自己复跑**：本轮三片 + 两轮收口里，`SLICE_*_FAIL` 有 3 次是环境所致（系统 python 缺 `alembic` → 收集期 exit 4；pytest 清理 `.pytest_tmp` 时 `PermissionError: [WinError 5]`）。**不要照抄工人自报状态**，用项目 venv 复跑定向再判定；工人诚实报告环境错误是好行为，别当失败打回。

5. **`--cov=` 要写点分模块名，不是文件路径**：`--cov=app/repositories/jobs.py` 会被当成包名，coverage 只警告 `Module ... was never imported` 然后**给你一张空表**（还显示 exit 0，极易误判为通过）。正确：`--cov=app.repositories.jobs --cov=app.application.pipelines ...`。

6. **派工单一律从文件读，别内联进命令行**：`codex exec ... "$(cat 'project/outputs/.../派工单.md')"`。把 prompt 直接内联进 bash 双引号串时，里面的括号/反引号/星号极易触发 `bash: syntax error near unexpected token '('`，**工人根本没启动**（exit 2），而表面看像"跑完没产出"——白烧一轮。

## 3. 故障处置

### 3.1 `-o` 目标目录不存在
`Failed to write last message file "<路径>": 系统找不到指定的路径。 (os error 3)`
→ 工人产出已落盘、只有总结丢了。派工前 `mkdir -p`；已发生则由调用方补录日志并标注「依据工人最终答复补录」。

### 3.2 websocket 抖动（尾部被掐断）
`failed to connect to websocket: IO error: tls handshake eof, url: wss://chatgpt.com/backend-api/codex/responses`
→ 重试 5 次 → `Falling back from WebSockets to HTTPS transport`。
判读：链路是通的（同时段 HTTPS 与新建 exec 请求正常；`curl -x <proxy> https://chatgpt.com/backend-api/codex/responses` 返回 405/401 即说明可达），只是长连接被断。
处置：确认产出在磁盘上 → 在则 kill 卡在 `ERROR: Reconnecting... waiting for network` 的进程，不要重跑。

### 3.3 账号级用量上限
```
ERROR: You've hit your usage limit. Upgrade to Pro … or try again at <HH:MM>.
```
所有模型一起被拒（sol/astra 都试过）。等不及：改派 Claude Code，或由调用方直出并标注回退模式。
要「到点自动续跑」：一次性 cron + 第一步额度探针；用户提前说"有额度了"就把该 cron 删掉防重复。

### 3.4 额度/可用性探针（几秒、只读、零副作用）
```bash
cd "$LOCALAPPDATA/Temp" && timeout 120 codex exec -m gpt-6-sol -c sandbox_mode=read-only \
  -c approval_policy=never --skip-git-repo-check -o probe.md "只回两个字：可用"
```

### 3.5 让工人别做多余动作
派题结尾固定加一句：**除任务列出的文件外不得写入任何文件**，并逐一点名禁止顺手更新实时解释/学习笔记/模块文档/架构/裁决。不点名时工人会自行"顺手维护文档"（本机真实发生过）。
