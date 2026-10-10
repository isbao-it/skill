# 工人进程卫生与验收补充（2026-09-17 实测）

配套 `SKILL.md` §三/§四 与 `references/worker-interruption-and-recovery.md`。
本文件只收**本次新踩到、且已被验证有效**的处置。

## 1. 被 kill 的会话留下孤儿进程 → 新会话工具握手失败

症状：新派的 `codex exec` 秒退或几十秒后被 kill，日志里出现

```text
ERROR codex_core::tools::router: error=code-mode host exited during handshake
```

工人会按「同一失败两次即停」自停，**不写任何文件**（连读取都没完成）——对外表现就是「派工没反应」。

判读：**不是额度、不是卡片、不是代码问题**。上一场被 kill 的会话留下了孤儿 node 进程
（`codex.js` + `cua_node` 工具宿主 + `playwright`/`github` 等 MCP），新会话抢工具宿主时互锁。

处置（顺序固定，已实测清完即恢复：同一命令再派 0 次 handshake 报错）：

```bash
# 1) 认人：看命令行 + 创建时间，只认与那场被 kill 的会话时间吻合的
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='node.exe'\" | \
  Select-Object ProcessId,CreationDate,@{n='Cmd';e={\$_.CommandLine.Substring(0,[Math]::Min(120,\$_.CommandLine.Length))}} | Format-List"

# 2) 清孤儿
powershell -NoProfile -Command "Stop-Process -Id <pid> -Force"

# 3) 确认无残留后**单独**重派（同时只跑 1 个主动任务）
```

坑：

- **MSYS 下 `taskkill //F //PID` 报「无效参数」**（`/F` 被当路径吃掉）→ 必须用 PowerShell `Stop-Process`
- **杀 `codex.js` 父进程会连带子进程**（cua_node、MCP），常杀一个就干净
- 保留**不属于**被 kill 会话的常驻 MCP（例如 Hermes 自己起的），别一刀切
- §「探针」只证明**模型通道**通：最小探针（「只回两个字」）不碰工具宿主，所以**探针通过 ≠ 可以派工**。
  复派前要一并确认「无残留进程」，否则又要白跑一场

## 2. 工人日志编码：统一走 git-bash 重定向

- 要求工人在 **git-bash** 里写 `> 文件 2>&1`（纯 ASCII/UTF-8）
- **PowerShell 重定向会写出 UTF-16 + NUL 的乱码日志**（实测 `coverage.log` 每字符间夹 `\x00`，
  人读不了、grep 也命中不了）——发现这类日志应让工人重跑该命令并改重定向方式，别塞进归档
- 派题里写明这条，比事后返工便宜

## 3. 验收补充：两条固定动作

### 3.1 证据存在性核对（工人最容易在这里说谎）

工人 `结论.md` 里写的「见 `details/xxx.log`」**可能根本没生成**。实测一卡一次缺 2 个
（`ruff-format.log`、`summary-validation.log`），还同时声称「校验 0 ERROR 0 WARN」，
而调用方亲自跑出的结果是 **1 WARN**。

固定动作：

1. 用正则把结论里出现的 `details/*.log` 全部提取出来，**逐个 `Path.exists()`**；
2. 亲自跑交付契约校验器（本仓为 `project/templates/validate_summary.py <summary.json>`）——
   它会自动校验 `tests[].evidence_path` 指向的文件是否存在，**判据是 0 ERROR 且 0 WARN**，
   不是工人自报的「0/0」；
3. 派题里写明「每一条声称通过的命令都必须有对应日志文件，禁止编造未运行的结果」。

### 3.2 覆盖率压线时按函数归类

覆盖率刚过门槛（实测 81.17% vs 门槛 80%）**不等于**防护被测到。把未覆盖行按函数归类后，
若集中在**安全/校验函数的拒绝分支**，即使达标也应要求补负向用例：

```python
# 用 ast 取函数行区间，把 coverage 的 Missing 行号按函数归类
funcs = [(n.name, n.lineno, max(getattr(x,'lineno',n.lineno) for x in ast.walk(n)))
         for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
```

实测收益：补测后 81% → **92%**，且负向用例**真抓出一个实现漏洞**
（`_is_public_address` 里 Python 3.11 的 `ipaddress.is_global` 对**多播地址**返回真 →
原实现把多播当成公网放行，属 SSRF 白名单漏洞；修法 `not address.is_multicast`）。

结论：**安全类模块的「压线达标」应视为待返工信号**，要求补拒绝分支的用例，而不是放行。

## 4. 卡面/文档体量压线时的取舍

出卡超上限（实测执行卡正文 8,156 > 8,000）时，**优先移出「派工侧指令」**——
预授权说明、命令模板、交付与证据要求**本来就属于派工单**，不该占卡面；再删重复表述。
**绝不删契约值/常量/错误码/阈值**来凑字数。注意「正文」与 frontmatter 要分开算。
