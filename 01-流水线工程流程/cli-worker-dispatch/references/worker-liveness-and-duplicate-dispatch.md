# 派工存活判定与「同题重复工人」事故（2026-09-20 实测）

> **事故**：13d R01 派工后调用方工具在 420s 超时报错，据此误判"没跑起来"→ 重派一次 →
> **两个提示词逐字相同的工人并发**跑同一 run_id，产出目录/命令/日志文件名完全重合、证据互相覆盖。
> 第二个工人（B）发现后**主动停止一切写入**并如实报告；第一个（A）已完成交付（22 用例过、校验器 0/0）。
> 结论：**工具超时 ≠ 进程已死**；重派前必须核实。

## 1. 判定"工人在跑"的三证据（缺一不可）

| # | 证据 | 命令（Windows/git-bash） |
|---|---|---|
| ① 进程 | **命令行**里能看到本题 | `Get-CimInstance Win32_Process -Filter "name='node.exe' or name='codex.exe'" \| Select ProcessId,CreationDate,CommandLine` |
| ② 派工日志 | 有 `[dispatch] 开始=` 且**尚无** `[dispatch] 结束=` | `tail -3 <卡>_执行R<n>日志.md` |
| ③ worker 会话文件 | mtime 在**持续变新** | DSH：`$DSH_HOME/sessions/**/session.jsonl.zstd`；Codex：`~/.codex/sessions/**/rollout-*.jsonl` |

只用其中一条会误判：只看工具返回 → 会把"超时"当"没跑"；只看 `-o` 日志 → codex 的 `-o` 摘要**只在正常退出时落盘**，没文件不代表没跑。

## 1.5 派工命令**禁止与前置命令用 `&&` 串联**（2026-09-21 实测踩坑）

把 `git commit … && bash dispatch_xxx.sh …` 写成一条时，**前置失败会静默短路派工**：
git 撞上瞬时 `index.lock` 返回 128 → 派工**根本没启动**，而调用方只看到"Background process started"，
极易误判"已在跑"。

铁律：
- **提交 / 归档 / 写文件** 与 **派工启动** 分两次调用；
- 派工启动后**立即用三证据确认真的在跑**（日志出现 `开始=` 且无 `结束=`、worker 进程存在）；
- 事后发现 exit≠0 时，**先确认是否有工人真的在跑**（防重复），再决定重派。



## 2. 启动方式（**首选原生托管**，用户 2026-09-21 拍板）

**首选**：`terminal(background=true, notify_on_complete=true)` 直接跑**派工脚本**（命令行保持短）：
```
bash dispatch_dsh_worker.sh <项目根> <派题文件> <日志>
bash dispatch_codex_architect.sh <项目根> <派题文件> <日志>
```
→ 进程**托管在 Hermes**：面板可见 + 结束自动回调（实测可用，这就是"旧方法"）。

**为什么会超时**：把**超长命令内联**进调用（`codex exec … "$(cat 长派题)" …` 前面还挂一串 `git commit`）
会让调用在 420s 超时、拿不到 session_id，甚至**杀掉整棵进程树**（13d 首派即如此）。脚本化后命令行很短，不再触发。

**兜底**（脚本方式也异常时）**立即返回式启动** —— 代价是**失去面板可见性与完成回调**，须自行轮询或另起看门进程：

```bash
cd <项目根> && (nohup bash <派工脚本> "<项目根>" "<派题文件>" "<日志>" >/dev/null 2>&1 &) ; echo LAUNCHED
```

调用方 1 秒内返回 → 不会超时 → 不会杀；随后用 §1 的三证据确认。

## 3. 重派前的强制检查

```bash
# 有任何一行匹配到本题（卡号/run_id），就不要重派
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'CARD13d R01' } |
  Select-Object ProcessId, CreationDate
```

若确需重派：**换新 run_id**（如 R02），不要复用被占用中的 run_id。

## 4. 交付目录被并发写入后的处置

1. 以**先启动的那个会话**的交付为准（其证据链完整），另一个会话的写入视为污染；
2. 要求后续会话**只读复核**、不得覆盖；
3. 在 `details/` 留一份 `_concurrency-note.md` 说明谁写了什么（本例 B 已自动做到）；
4. 调用方复验时**不采信"日志文件内容"**，而是**自己重跑**定向与覆盖率（新结果无法被覆盖）。
