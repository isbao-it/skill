# DSH 工人派工单（任务卡 → headless 工人）

> 用法：把 `<>` 占位替换后，整段作为 `--profile headless` 的位置参数发给工人。
> 纪律常驻层在 `<DSH_HOME>/AGENTS.md`（工人家），**派工单只写本卡特有内容**，
> 不要重复抄常驻纪律（省 token，也避免两处口径打架）。

## 派工命令行

```bash
bash "C:/Users/<user>/AppData/Local/hermes/skills/cli-worker-dispatch/scripts/dispatch_dsh_worker.sh" \
  "C:/work/dev/projects/bao-kuan-xin-fa" \
  "project/outputs/<卡号>_r<轮次>_prompt.txt" \
  "project/outputs/<卡号>_执行R<轮次>日志.md"
```

- 后台派工：用 `terminal(background=true, notify_on_complete=true)` 调上面的脚本；前台有 600s 上限。
- 脚本做的事：cd 到项目目录（= 沙箱工作区根）、注入 `DSH_HOME` 与 `DEEPSEEK_API_KEY`、跑 headless、日志落盘。
- 派工前必须 `mkdir -p` 产出目录，否则工人要在自己的作业里补建（易漏）。

## 派工单骨架（五段，缺一段就会出问题）

```markdown
CARD<卡号> R<轮次>。全新会话，先读以下文件再动手：
- 规则：AGENTS.md（本项目）+ 你的常驻纪律
- 卡面：project/cards/<NN>/{执行卡,测试卡}.md（或本派工单里钉死的验收项）
- 现有实现/测试（白名单，≤6 个）：<路径…>

## 目标
<一句话说清做完后世界变成什么样>

## 要求（逐条可勾选，钉死枚举值/字段名/错误码/表名/阈值）
1. …
2. …

## 验收口径（必须真跑并留证）
- 定向用例：<逐条列出用例名/路径>
- 命令与落盘位置：`details/pytest-targeted.log`、`details/ruff.log`
- 未运行的必须显式标「未验证」

## 硬边界（本卡特有；常驻纪律已在 AGENTS.md，不必重抄）
- 写入白名单：<卡面文件 + project/outputs/待审核/<卡号>/<run_id>/**>
- 不得放宽 <某校验>；不得新增错误码；不得加依赖；不得 git；不得越界写
- 本轮熔断只对「同一非 lint 原因失败 2 次」生效；lint（ruff --fix）不计入熔断

## 回报格式
首行 `CARD<卡号>_R<轮次>_OK` 或 `CARD<卡号>_R<轮次>_FAIL:<原因>`；
其后：改动文件（逐条）· 每条命令与结果 · 未验证项 · 不确定点。
```

## 验收（Hermes 侧，工人自报一律不采信）

1. `git status --short` + diff：只动白名单（越界改文档/清目录是高频违规）。
2. 自己重跑：定向用例、覆盖率（整文件对门槛）、全量回归、Ruff、卡面冻结契约校验器。
3. **卡面逐条 → 用例名映射**：映射不上的判 `blocked`（只信"全绿"会被骗）。
4. 读 DSH 会话日志核对真实动作（`scripts/decode_dsh_session.js`）：跑了哪些命令、动了哪些文件、
   真实模型/权限（`request/header`、`sandbox/mode`、`approval/policy`）。
5. 按卡汇总用量：`assistant/message` 里的 `inputTokens/outputTokens/cacheReadTokens/reasoningTokens`。
