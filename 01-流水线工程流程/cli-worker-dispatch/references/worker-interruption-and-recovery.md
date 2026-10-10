# 工人中断与恢复速查（2026-09-16 实测）

配套 `SKILL.md` §三「失败模式：先看磁盘，再决定重跑」。本文件只收**实测过的命令与判读**。

## 1. 先探针，再决定（不要凭感觉等或重跑）

任何「通道疑似坏了 / 额度撞限 / 403」之后，都先用最小请求探通道：

```bash
codex exec -m <模型> -c sandbox_mode="read-only" -c approval_policy="never" \
  --skip-git-repo-check -o "$LOCALAPPDATA/Temp/probe.md" "只回两个字：可用"
```

- 回「可用」→ 通道好，直接重派（或按下面的半成品协议补缺口）
- 回 `You've hit your usage limit … try again at <时间>` → 账号级额度，等或换工人
- 回 `403 Forbidden` / `tls handshake eof` → 瞬时拦截，等几十秒再探一次

## 2. Cloudflare 403（本次新踩到的失败模式）

症状：`ERROR: unexpected status 403 Forbidden: <html>…` 且带 `cf-ray: …`；同一时刻 MCP 通道也报
`http/request failed … /ps/mcp`。

关键判读：
- **token 照烧，产出零落盘**（实测 1,353,996 token、磁盘上没有任何新文件）。所以「烧了很多 token」
  不代表「干了很多活」——必须核磁盘。
- 拦截图里出现的 HTML 是 Cloudflare 的挑战页，不是项目报错，别去改代码。
- 恢复后重派时**优先新开会话**：`codex exec -m <模型> …`（新），而不是
  `codex exec resume <被打断的 session>` —— resume 会把坏掉的流状态带回来，且上次那种会话
  可能已经在重试循环里烧掉一轮额度。

## 3. 半成品协议（进程被掐断，但活其实干完了）

实测两次（websocket 抖动、额度撞限）：**实现、迁移、测试都已写完且能跑通，只差执行结论**。

处置顺序：

1. **核磁盘**：`git status --short` + `ls` 目标目录 → 列出新增/修改文件
2. **独立复验**（不看它的自报）：跑定向用例、覆盖率、以及反射级契约核对
3. **按复验结果分岔**：
   - 全绿 → **不重做**。重派时把任务收窄成缺口清单：
     > 「继续上一场。上次在写执行结论前被中断，实现与测试已在工作区（未提交、未清理），
     > **不要重做已有实现**，只补：①… ②… ③…」
   - 发现真缺口（例：ORM 声明落后于迁移、某断言缺失）→ 只补缺口，其余原样保留
4. **别急着丢弃**：半成品通常已消耗大量额度，重做等于再烧一遍

## 4. 中断现场保护（不动工作区、不漏未跟踪文件）

`git stash create` 只收**已跟踪**文件 —— 新写的仓储/迁移/测试会漏掉。要连未跟踪文件一起保住，
且不碰工作区和真实索引，用**临时索引快照**：

```bash
cd <项目根>
TMPIDX="$LOCALAPPDATA/Temp/wip.index"; rm -f "$TMPIDX"
GIT_INDEX_FILE="$TMPIDX" git add -A                     # 只写临时索引
tree=$(GIT_INDEX_FILE="$TMPIDX" git write-tree)
commit=$(git commit-tree "$tree" -p HEAD -m "wip(<卡号>): 未验收现场快照")
git update-ref refs/wip/<name> "$commit"                # 挂引用，防 GC
rm -f "$TMPIDX"
git show --stat --oneline refs/wip/<name>               # 核对清单
```

核对点：`git status --short | wc -l` 前后**不变**（证明工作区没被改动）。

同时写一份中断交接文档（`<项目>/project/outputs/<NN>/<卡号>_中断交接.md`）：
中断原因 / 现场文件清单 / 已完成项的独立证据 / 待补项 / **会话 id** / 恢复命令。会话 id 从
`ls -t ~/.codex/sessions/YYYY/MM/DD/*.jsonl | head` 里按提示词特征串（`grep -l "执行【<卡号> 批】"`）
精确定位，不要靠时间猜。

## 5. 文件被误删/覆盖：从会话日志反解

`python scripts/recover_codex_agent_files.py <输出目录> <文件名1> [<文件名2> …]`

三个坑（脚本注释里也写了）：
1. 日志里中文是 `\uXXXX` 转义 → 预筛只能用 ASCII 片段
2. 补丁载荷里的换行常是**字面 `\r\n`** 两字符 → 必须先反转义再按行切块
3. 同一文件可能先 `Add` 再被若干 `Update` 改过 → 要**按顺序应用 hunk**，只取最大块会得到旧版本

恢复后**人工比对关键行**再放回原位；恢复件不等于原件（实测 3/3 恢复成功，其中 2 份差 6 字节＝尾行归一）。

## 6. 复派前的固定检查（省一次白跑）

- 输出目录先建好：`mkdir -p <项目>/project/outputs/<NN>/`（否则 `-o` 报 `os error 3`）
- `resume` 只认 `-c`：换模型写 `-c model="<name>"`，没有 `-m`
- 派题里那句「除上述文件外不得写入、删除或移动任何文件」必须逐字保留
