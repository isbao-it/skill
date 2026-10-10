---
name: cli-worker-dispatch
description: "Dispatch CLI coding agents as workers and verify output."
platforms: [windows, linux, macos]
---

# 🛠️ 派工 CLI 编码 Agent（codex / claude-code / opencode）与验收

适用于「把任务交给一个 CLI 编码 agent 在项目里干活，我来验收」这类工作。无论上游是流水线、
一次性重构还是陪跑式出卡，**派工与验收的方法论是同一套**。

## 何时用

- 要用 `codex exec` / `claude -p` / `opencode` 之类在项目里改文件、写测试、出文档
- 长任务需要后台跑 + 完成通知
- 需要判断「工人说做完了」到底算不算做完
- 派工过程被网络/额度打断，要决定重跑还是收工

## 一、派工指令的骨架（缺一项就会出问题）

派题不是一句话，是一份微型合同。至少五段：

1. **先读后做**：明确列出先读哪些文件（规则文件、任务卡、权威设计文档、现有实现/测试），读完再动
2. **做什么**：逐条、可勾选的要求；禁止用「完整实现 X」「保持高质量」这类空话
3. **验收口径**：要它真实运行哪些命令、输出什么原始证据（首轮失败输出、最终结果、覆盖率、lint、全量回归），并写死「未运行的必须标未验证」
4. **硬约束（逐条写，不要指望它自觉）**：
   - 只改任务列出的文件；**除这些文件外不得写入任何文件，包括"顺手"更新项目文档**（实时解释/学习笔记/模块文档/架构/裁决）—— 工人天生爱做看起来合规的维护动作
   - 不新增依赖（缺依赖先报告等批准）
   - 不做任何 git 操作
   - 不放宽/删除断言、不 mock 掉真实验证、不猜测式修复
5. **回报格式**：要它给「改动文件清单 + 原始输出 + 未验证项 + 不确定点」

## 二、模型与额度

- **显式写死模型**：`-m` 从不省略。默认模型会随 CLI 版本漂移，撞上新模型直接 400
- 版本门禁：新模型可能要求新版 CLI（报 `requires a newer version of Codex`）→ `npm i -g @openai/codex@latest`；但**模型名不存在**是另一回事（报 `is not supported … ChatGPT account`），升级无解，换名字
- **档位与省钱口径（2026-10-08 实测修订）**：出卡 / 架构 / 跨卡裁决 = `gpt-6.1-sol` + **`medium`**（要 `high` 必须在派题里写明理由）；**模块文档 / 错误码表 / 文案同步 / 微修（已定位到行）= `gpt-6-luna` + `medium`，禁 sol** —— 这些是"提取与逐字裁剪"，不是判断。**配额按档位烧、不按 input**：实测 `sol`+`high` 9 个事件 = 5h 窗口 +5 点，`luna` 122 个事件 / 544 万 input 也才 +5 点。省钱第一手段是**别把非判断类活派给 sol**，第二是**合并轮次**（每轮约 21.5k 底噪）。详见 `references/worker-model-tiering-and-probe-ownership.md`
- **额度是账号级的**：撞限时所有模型一起被拒，报 `You've hit your usage limit … try again at <HH:MM>`。等不及就换另一个工人（Claude Code）或由调用方直出并标注回退模式；要「到点自动续跑」挂一次性 cron，但让 cron 第一步做额度探针，探针失败只报告不派工

## 三、失败模式：先看磁盘，再决定重跑

**核心原则：worker 的最终答复丢了 ≠ 活没干。** 本机实测两次（websocket 抖动、额度撞限）都是「产出文件已落盘，只有收尾的总结被掐断」。

| 症状 | 判读 | 处置 |
|---|---|---|
| `Failed to write last message file … os error 3` | `-o` 目标目录不存在 | 派工前 `mkdir -p`；已发生则补录日志并标注来源，别重跑 |
| `failed to connect to websocket: IO error: tls handshake eof` | 长连接被断，链路其实通 | 确认产出在磁盘 → kill 卡在重连循环的进程 |
| `You've hit your usage limit` | 账号级额度 | 见上节 |
| 进程一直 `Reconnecting...` | 通常已无事可做 | 先核产出，再 kill |
| `exit_code=-15` + `completion_reason=killed` + `termination_source=**agent_close**` + **收不到完成通知** | **Hermes 自己杀的，不是工人/模型/额度问题**：agent 生命周期事件关闭该 task 资源时，`client_lifecycle._close_task_resources` → `kill_processes()` 会把**该 task 名下所有 status=running 的后台进程**逐个 SIGTERM（源码把它记作可恢复的意外，`_RECOVERABLE_END_REASONS` 含 `agent_close`）。本机实测一天中两次：两次产物都已落盘，只丢收尾自检/回报 | ① **先查磁盘**（按"产物早落盘"规范写的轮次，损失只在收尾）② 只补收尾动作或按需补**微修轮**，**禁重派整轮** ③ 预防：给工人的产出规范写成"先写产物、后写回报"，长任务拆短轮 ④ 该回收**按 task 全量杀**，所以并发的多路会一起死 —— 别指望"另一路还能跑完" |

取证手段：读进程日志尾部；必要时 grep `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`（含模型名、工具调用、报错）。
**永不**在未核对磁盘前重跑整场 —— 一次重跑等于烧掉一小时的额度。

**验收前先跑冻结物校验（2026-10-08 加）**：`python tools/frozen_check.py check project/frozen.lock.json <卡面/模块文档…> [--allow-missing …]` —— 逐字比对冻结文案/枚举/函数 + 占位词 + BOM，**退出码非 0 = 契约漂移，不得进入验收**。首轮 M2 的三处错全在文档层（文案漏冻结、冻结计数 0↔1 漂移、卡面内联超预算），而文档层的错**没有测试会红**。

## 四、验收：永不采信工人的自报

工人自报「60 passed / 100% coverage / 已合入」只是线索，不是证据。固定做四件事：

1. **独立重跑**：自己跑 pytest / 覆盖率 / lint / 全量回归，用**自己**的输出下结论
2. **范围核对**：`git status` + diff，确认只动了允许的文件（越界改文档、顺手重构很常见）
3. **契约逐字核对**：把产出与权威清单机器比对（表名、列名、约束名、用例名映射），而不是抽样人眼扫。长名截断规则要**重算哈希**验证，不能只看长得像
- 抽查可读性产物：注释/docstring 是否符合项目规范（复杂块写"为什么"、魔法数字标来源）
- **复核结论固定分级输出**：**高/中/低 + 每条具体修改建议**；低级别只记录不修（合法止损）。比
  「复核通过/不通过」信息量大得多，也避免低风险项被迫返工；分级后由调用方挑 2~3 条高/中级修完**复跑三件套**
  （定向用例 + 全量回归 + 真跑入口），确认没改坏东西
- **外部平台响应夹具与开关型功能**：凡声明「平台返回什么」的夹具必须来自真实抓包（禁手搓"合理形状"）；
  默认关闭的功能（ASR、真实 LLM、外部推送）必须在卡内安排**一次真跑验收**（开关打开 + 真实样本 + 真库核对），
  否则等于未验。判据、实例与探针配方见 `references/coverage-gates-and-fixture-provenance.md` §6

**⚠️ 最容易放过的一类：卡面规格 vs 实际用例的落差。** 工人会交回「按 TDD 新增固定 8 组测试、
16 passed 全绿」，实际那 8 组只实现了很小一部分（3 个组**零真实 HTTP 调用**、某组只冒烟 1/35 条路由、
错误码只测 1 个）。**只信"全绿"就会被骗**。所以验收必须额外做两件：
① 把卡面每条要求**逐条映射到真实用例名**（映射不上=缺失，判 `blocked`）；
② 用**整文件**覆盖率对门槛（本卡新建的文件没有"历史行"可豁免）。
判据、命令与"回查已合入卡老账"的四把尺子（含"生产类是否从未被 tests/ import"）见
`references/test-spec-fidelity-and-coverage-objectivity.md` —— 这套尺子在卡12 上抓到了整批放水，
并牵出卡08 一个约 313 行、**0 覆盖**的真 SQLite 仓储类。

**⚠️ 第二类最容易放过：新方法体是空壳/占位返回，而薄测试仍然全绿。**
实测案例：某片交回「6 passed、Ruff 全过」，其中「已入库水位查询」方法体是 `return None`、
「写步骤结果」方法在更新分支**把 checkpoint 置成 None**（会抹掉刚写入的载荷）——两处都是
**行为缺陷**，但片内自测没覆盖；是**另一个并发的片**在接线时读代码才报出来的。
所以验收必须额外做：
③ **抽查每个新方法的方法体**：是否 `pass`/`return None`/`...`/`TODO` 占位，是否只回显入参；
④ **核对关键行为的断言是否真的存在**：读‑写往返、**不破坏既有数据**（如"再写一次不得抹掉已存字段"）、
边界返回（无记录→None）。只看"方法存在 + 测试通过"不算验收。
判据与配方见 `references/coverage-gates-and-fixture-provenance.md` 与 `references/codex-cli-ops-notes.md` §2.1。

脚本：`scripts/verify_contract_artifacts.py`（映射条数/唯一性/命名合法性/截断哈希重算/与权威清单双向差分/用例映射完整性/陈旧措辞扫描）。
命令模板与细节：`references/codex-cli-ops-notes.md`。

## 五、节奏与纪律

- **一任务一会话**：别在长会话里连做多个任务，上下文稀释后规则遵守率下降
- **单件滚动**：出一件 → 审一件 → 做一件 → 验收 → 下一件；批量出产 = 返工放大器（未执行的设计与真实代码必然漂移）
- **先审后动**：审核通过前不派工、不合入；本地 commit ≠ 审核
- **流水线产物主动提交**：卡、裁决、纪要、日志、产出文档这类文档产物验收完自行 commit，别攒成一堆未提交；**代码合入仍等用户明确通过**；无关的并行改动不混进同一 commit，但要列清单说明
- **未通过就退回**：把意见提炼成具体修改指令再转达，不原样转述给工人

## 六、常见坑

- **Codex 连不上是环境（代理）问题，不是模型问题——先探针再决定重派**：症状是 rollout 里 `task_started` 之后立刻 `workspace routing discovery timed out` + 反复 `ERROR: Reconnecting...`，且**没有 `rate_limits`、没有 `agent_message`、0 token 消耗**（本机实测：这三条同时成立 = 请求根本没发出去，磁盘也不会有产物）。判据动作：先跑 30 秒探针（`codex exec -m gpt-6-luna -c model_reasoning_effort=low --skip-git-repo-check "只回复两个字：可用"`），回话=链路通；不回话就查代理（`netstat -ano | grep ':7897.*LISTENING'` 有无监听、`reg query` 的 `ProxyEnable`、Clash/Verge 进程是否存在），**别重派整轮、别换模型/换工人**（本机实测白跑 0 成本，换人换模型纯属白折腾）。附带：日志里 `rmcp::transport::worker ... mcp.context7.com / chatgpt.com/backend-api/ps/mcp` 的报错是**噪音**（MCP 连不上），不致命。
- **Windows 工人写的文件常带 UTF-8 BOM**：工人的 shell 多是 PowerShell，`Set-Content -Encoding utf8` 会加 BOM → 下游 `json.load` 抛 `Unexpected UTF-8 BOM`、md frontmatter 解析错位。实测同一轮里 `summary.json` 与两张卡面 md 全带 BOM。派工单里写死「产出 UTF-8 **无 BOM**」；验收自查 `open(p,'rb').read()[:3] == b'\xef\xbb\xbf'`，已发生则用 `utf-8-sig` 读回并重写。
- **免费模型池限流的症状是「零输出挂死」而非报错**：`opencode run --model opencode/<免费模型>` 命中 `Rate limit exceeded` 时不退出、无限重试，前台表现为 300 秒无输出。先 `--print-logs --log-level INFO` 复跑看 `stream error`，别把它当网络问题去查代理。
- **验收加一道「变异测试」**：把工人的实现做一处定向破坏（如把 `tick` 的 `while` 改成 `if`），看是否有用例立刻变红、退出码非 0，再还原并核对 sha256 一致。比"全绿"更能证明断言真的在保护行为（实测：改 `while`→`if` 后仅跨段那条用例变红，正是预期的保护范围）。**变异要选能区分实现差异的初态**：实测「恢复计数用赋值而非累加」的用例在 **0 计数**的实例上跑，`赋值` 与 `累加` 结果相同 → 把实现改成累加后**整套 24 条全绿、完全漏检**；把初态改成"先 tick 出一个非零计数"后，同一变异立刻变红。**断言存在 ≠ 断言能检出缺陷。**

- **出卡/派工的 prompt 与任务书必须是同一份白名单**：实测「任务书里列了 `modules/app.md`，但派工 prompt 只写了"只读 pomodoro.js"」→ 工人就按 prompt 走，没读模块文档，还如实上报"无法核对 §7" → 卡面质量降级、返工一轮。两份文件都列文件时，逐字对照，缺一个都会改变工人行为。**同一坑在本项目连踩两次**：第二次派「卡03 出卡」时 prompt 仍只写了 brief + `pomodoro.js`，工人据此没读老师指导书原文与其余资料，产出的卡面缺「验证命令表/白名单/输出规范/关闭检查」等必需字段 → 整卡返工重写。
- **派「出卡」必须等依赖卡已合入再派**：实测在卡01b 仍在执行时派「卡03 出卡」，工人读到的是**改动前**的 `pomodoro.js`（11 个方法），于是整份卡面建立在陈旧接口上，还多出一整节多余的「已知前置差异」，执行前必须先删掉。派卡前先看依赖卡的 commit 是否已落地。
- **vault 根 `_Tasks/` 是全局队列，多项目共用 `01/NN` 编号会撞号**：实测 fanqie 的卡01 与「流水线自身」的卡01 落进了同一个 `_Tasks/已完成/01/`。卡目录按 `<项目>/<NN>/` 分（如 `_Tasks/已完成/fanqie/01/`），`_Outputs/已归档/` 同理。
- `-o` 目标目录必须先存在（见上表）
- `codex exec resume` 只认 `-c`，不认 `-m` / `-s`；换模型写 `-c model="<name>"`
- `exec` 默认只读沙箱：要写文件必须 `-c sandbox_mode="workspace-write" -c approval_policy="never"`
- 后台派工用 `terminal(background=true, notify_on_complete=true)`；前台有 600s 上限
- 交互式会话才需要 pty，`exec` 非交互模式不需要
- 同一个文件不要在一个回合里发两个并发 patch（并发写会互相看不见对方的结果）
- **`--basetemp` 指向 Hermes 自己创建过的目录 → 工人沙箱 `WinError 5` 建不了子目录**（同一命令我能跑过、工人报"权限拒绝"）。判据与修法见 `references/worker-sandbox-basetemp-acl.md`：换一个**尚未存在**的 basetemp 前缀（`.pytest_tmp-<卡号>/`）让工人自建，`.gitignore` 补 `.pytest_tmp*/`
- 工人 `details/*.log` 在 Windows 上常是 **UTF-16**（PowerShell 重定向），读前先 `iconv -f UTF-16LE -t UTF-8`，否则满屏 null 会让人误判"日志是空的"
- **「一屏装下/不滚动」不能靠 `min-height`**：flex 子项要能收缩到比内容矮，父链必须是**确定高度**——`height: 100dvh` + `overflow: hidden` + 各级 `min-height: 0` + 给列表 `flex: 1 1 auto; overflow-y: auto`。`min-height` 只保证"至少这么高"，内容一多容器跟着长，子项没有可收缩空间，最终由整页滚动代偿（实测：容器 950 > 视口 800，列表 `scrollHeight == clientHeight` 完全没滚）。**改 CSS 必须删/改写旧规则，不能只在文件末尾追加**——层叠覆盖会让旧 `min-height: 400px` 继续生效，判定性失败。验收方可以在真实页面里注入候选规则先验证配方，再据此出卡（比"我觉得应该行"可靠）。
- **验收"不滚动/不溢出"必须覆盖内容增长态**：空列表时量 `scrollHeight` 必然全绿，加满 N 条后才会暴露"整页滚动"。判据要写成"加 N 条后 `scrollHeight ≤ 视口`**且** 目标容器 `scrollHeight > clientHeight`"（证明是容器在滚，不是页面在滚）。
- **真浏览器验收前先探活本地静态服务**：后台起的 `python -m http.server` 会被回收，页面停在 `about:blank` 时 `localStorage` 访问被拒（`SecurityError: Access is denied for this document`）。先 `curl -s -o /dev/null -w '%{http_code}'` 看是否 200，别把 HTTP 000 当成页面/布局问题白跑一轮（换端口或重起即可）。
- **提交前逐文件核对 diff——用户会直接改工作区文件**：实测用户自己把 `pomodoro.js` 的默认值从 25/5 改成 1.5/0.5，我方 `git add <文件>` 顺手把它收进了"卡04 修复"提交，导致提交里混入未审改动、并打红 3 个用例。**提交前对自己要 add 的每个文件先 `git diff` 一眼**；发现非本方改动先问，不要盲 add。
- **用例别耦合默认配置值**：`createApp({ workMinutes: 1 })` 建实例、却拿 `breakMinutes: 5` 的快照去 `restore` —— 默认值一改，"配置一致性"校验就把快照整体拒绝，用例成片变红。**用例要把参与校验的配置全部显式写死**（`createApp({ workMinutes: 1, breakMinutes: 5 })`），别吃默认值。
- **破坏性 git 命令前必须断言 `pwd`（本技能最贵的一次教训）**：实测某个 shell 里 `$TMPDIR` 为空 → `cd "$DST"` 静默失败 → 紧随其后的 `git filter-branch` **在源仓库里执行**，把 15 个提交重写成 11 个、把 `project/` 从工作区删掉。写法必须：① 目标路径用**显式绝对路径**，不依赖环境变量；② `cd` 后立刻 `case "$(pwd)" in *目标目录名*) ;; *) exit 1 ;; esac` 断言；③ 执行 `git log --oneline -1` 确认是预期的那个仓库；④ 破坏性动作**单独一条命令**，不与"造副本/切目录"混在一条链里。恢复：filter-branch 的 `refs/original/*` **不要提前删**（它保存着重写前的全部 ref），或走 reflog。
- **`git reset --hard` 遇到被程序占用的文件会中途失败**：Windows 上 Word 打开着 `.docx`，reset 报 `unable to unlink old '...docx': Invalid argument` 并中止，工作区停在半还原态。想把分支/历史退回去、又不想动磁盘文件时用 `git reset --mixed <sha>`（只重置索引，不碰工作区），随后 `git status` + `git diff HEAD` 必须为空才说明磁盘与历史一致。
- **只推"项目本体"到公开仓库的干净流程**：在**副本**里 `git filter-branch --prune-empty --index-filter 'git rm -r --cached --ignore-unmatch <路径…>' -- --all` → 删掉 `refs/original/*` → **重指 tag**（filter-branch 连 tag 一起重写并把旧指向存进 `refs/original`；旧 tag 仍指向含敏感文件的提交，一旦 `push --tags` 就漏，而 `git rev-list --all` 会把 `refs/original/*` 也算进去，出现"仍有敏感路径"的假警报）→ 逐提交核验 `git ls-tree -r --name-only <sha> | grep -iE '敏感路径'` → 最后才推。源仓库**不留 remote**，避免日后在源仓库手滑 `git push` 把全量（含敏感文件）推上去。
