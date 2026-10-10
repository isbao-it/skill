# DSH（DeepSeek Harness）当无头工人：命令、权限、取证与坑

> 实证时间 2026-09-20，DSH 版本 **0.1.0-rc.6**（桌面版 "DSH Desktop" 只是它的 Electron 壳，
> 内核同一套 `@deepseek-ai/dsh` 插件树）。以下结论全部来自本机实跑，不是文档推断。

## 1. 命令模板

```bash
# 在【项目目录】里启动 —— cwd 就是工作区根，也是沙箱白名单
cd "C:/work/dev/projects/<项目>"
K=$(python -c "import yaml;c=yaml.safe_load(open(r'C:/Users/<user>/AppData/Local/hermes/config.yaml',encoding='utf-8'));print([p for p in c['custom_providers'] if p['name']=='deepseek'][0]['api_key'])")
DSH_HOME="C:/Users/<user>/.dsh-worker" DEEPSEEK_API_KEY="$K" \
  node "C:/Users/<user>/.dsh/profiles/node_modules/@deepseek-ai/dsh/lib/bin.js" \
    --profile headless "<任务正文>"
```

- `--profile headless "任务"` = **一次性**：跑完打印最终 assistant 文本并退出；`turn/end` 完成 → exit 0，
  否则 exit 1 且错误进 stderr。**不开监听端口**，适合后台派工。
- 后台派工用 `terminal(background=true, notify_on_complete=true)`；前台有 600s 上限。
- 额外配置层可用 `--patch <file.yml>` 叠加，也可写 `$DSH_HOME/cordis.patch.yml`（home 级，最后叠加）。
- `--dump-config` 打印合成后的插件树（查实际生效的插件配置，**不含** settings.yaml 的用户选择层）。

## 2. 为什么用独立 `DSH_HOME`（不要用 `~/.dsh`）

桌面 App 写的 `~/.dsh/.credentials.yaml` 是 `version: 1` + `records:` 包装格式，而 rc.6 的
`dsh-credentials-local` 契约是**纯 mapping**（`KEY: value`，无包装层、无 version 字段）→ 直接 boot 会挂：

```
Error: dsh: plugin tree failed to load: ... credentials-local: the value for "version"
in C:\Users\<user>\.dsh\.credentials.yaml must be a string
```

所以给工人开独立家（等价于 Hermes 的 profile 隔离）：`C:\Users\<user>\.dsh-worker`。
凭据走**进程环境变量** `DEEPSEEK_API_KEY`（优先级：启动环境 > `$DSH_HOME/.credentials.yaml` > `$DSH_HOME/.env` > ...），
不往磁盘上多写一份密钥。

## 3. 模型与权限（都实测过）

- 模型在 `$DSH_HOME/settings.yaml`：
  ```yaml
  agent-default-model:
    provider: deepseek-official
    model: deepseek-v4-flash     # 用户 2026-09-20 定：工人一律 flash，禁 pro
    reasoningEffort: high
  ```
  核实办法（别信配置、信日志）：解会话日志看 `request/header` → `{provider, model, reasoningEffort, maxTokens}`。
  DSH 自带默认是 `deepseek-v4-flash`；上下文窗口 1,000,000，maxTokens 256,000。
- **权限三件事在会话里被固化**（可审计）：`permission/preset`、`sandbox/mode`、`approval/policy`。
  headless 默认 = preset `workspace-write`（= sandbox `workspace-write` + approval `ask`）。
- approval `ask` 在无应答者时 **fail-closed**，所以工人不可能靠"求批准"越权。
- **沙箱是真实拦截，不是自觉**：让工人写工作区外的 `%LOCALAPPDATA%\Temp\dsh-escape\escape.txt`
  → 返回 `error: Access to the path 'dsh-escape' is denied.`，事后核实文件**确实没被创建**。
  这治的正是我们反复踩的坑（工人顺手改文档/删文件）。

## 4. 工具通道：bash 不通，用 pwsh

受限令牌下 **Git bash 起不来**（报 `CreateFileMapping 拒绝`），WSL 无发行版；
`pwsh` 通道正常（实测 `python --version` → `Python 3.11.15`，exit 0）。
本机未装 PowerShell 7 时 DSH 自动兜底 **Windows PowerShell 5.1**（它已强制 UTF-8 输出，中文安全）。
→ 派工命令写成 PowerShell 也能跑的形态（`.venv/Scripts/python.exe -m pytest ...` 两壳通用）。

## 5. 取证与成本：会话日志

- 位置：`$DSH_HOME/sessions/<cwd 转义>/session-*/session.jsonl.zstd`（cwd 里的非 ASCII 会转义成 `~xxxx~`）。
- 文件是**多帧拼接 zstd**（每批事件一帧，实测一次会话 198 帧）。整文件解压只拿到第一帧
  （会误以为"日志只有 185 字节"）。用 `scripts/decode_dsh_session.js` 逐帧解。
- 有用的事件：`user/message`、`assistant/message`（**自带用量** `inputTokens/outputTokens/cacheReadTokens/reasoningTokens`）、
  `tool/call`（工具名+参数 → 查"它到底跑了什么命令"）、`tool/result`、`request/header`（模型/推理强度/上限）、
  `permission/preset`、`sandbox/mode`、`approval/policy`、`session/title`。
- 成本口径照旧：**看 input**，自报 tokens 一律低估。

## 6. skill 机制（"培养"工人的正规入口）

- 格式：`<name>/SKILL.md`（只认一层）或 `<name>.md`；frontmatter 必填 `name`（kebab-case）+ `description`，
  可选 `whenToUse`/`metadata`/`disable-model-invocation`/`user-invocable`。
  **键名拼错或值不是布尔 → 整个 skill 被静默跳过**（fail-closed），不报错，极易白配。
- 扫描根（rank 小者优先）：`<项目根>/.dsh/skills`(100) → `<项目根>/.agents/skills`(200) → 自定义(300)
  → **`<DSH_HOME>/skills`(400)** → `~/.agents/skills`(500)。项目根 = 最近的含 `.git` 祖先目录。
- 成本特性：模型常驻只看到**目录**（描述截断 500 字符），要用时 `skill(name)` 才加载正文 → 常驻成本极低。
  所以 description 要写清"何时用"，正文可以有干货但不该灌水。
- 工人专属 skill 放 `<DSH_HOME>/skills`（只对工人可见，不污染 Hermes 与项目仓库）。

## 7. 约束机制：hook 不是配置，是插件

- 本机已装 `@deepseek-ai/*` 里**没有任何 hook 插件**；官方 repo 的 `packages/hooks/hook-protocol` 是协议库，
  `hook-bridges` 设计笔记已 archived（做过又收了）。
- 现成可用的约束面：
  1. **沙箱**（Windows ACL 受限令牌；`enforcement: partial`，Everyone 边界是官方承认的弱点）；
  2. **permission preset + approval policy**（会话内固化、可审计）；
  3. **`tools/execute` 环绕插件**（参考实现 `@deepseek-ai/dsh-tool-call-timeout-policy`）——要写"卡面白名单守卫"就写这个；
  4. `dsh-repeat-tool-reminder`（重复调用提醒，仅建议型）；
  5. 声明式挂载：`$DSH_HOME/cordis.patch.yml` 或 `--patch <file>`（id 定向覆盖/禁用/insert）。
- 纪律建议：**先用 AGENTS.md 规则 + 沙箱跑 1~2 张卡，按真实缺口再写插件**，别先造没人用的机制。

## 8. 坑清单（都踩过）

- **MSYS 路径不能喂给 node**：`node ~/.dsh/.../bin.js` 会变成 `C:\c\Users\...` 找不到模块。
  一律用 `cygpath -m` 转 `C:/Users/...` 再传。
- `dsh --profile headless --help` 只支持 `-h`；其他 flag 会被当成任务文本拼进去。
- 项目里没 `.git` 时"项目根"退化成启动目录 → skill 扫描根跟着变（本项目有 git，别在子目录里启动）。
- 任务文本是位置参数；含引号时在 bash 里用单引号包住整段。
- 首次在某目录跑会在工作区留下痕迹 → 派工前把相关路径加进 `.gitignore`，验收时排除。

## 9. **默认 `workspace-write` 下 pytest 跑不起来**（2026-09-20 三次对照实测，必读）

### 现象
DSH 当工人时，定向用例大面积 fixture ERROR：

```
_pytest/tmpdir.py：cleanup_dead_symlinks(basetemp) → root.iterdir()
PermissionError: [WinError 5] 拒绝访问。: '...\.pytest_tmp-dshprobe\run1'
14 passed, 8 errors   （22 条用例里 8 条 tmp_path 相关全挂）
```

### 三组对照（每步只改一个变量，排除法）
| 预检 | 沙箱模式 | basetemp 父目录 | 结果 |
|---|---|---|---|
| #1 | `workspace-write`（默认）| 无（工人自建）| ❌ 14 passed / **8 errors** |
| #2 | `danger-full-access` | 无 → 建父目录后重跑 | ❌ → ✅ **22 passed** |
| #3 | **`workspace-write`** | **调用方预建** | ❌ 仍失败（`basetemp.mkdir(mode=0o700)` 之后枚举被拒）|

### 根因（#3 的权限探针逐条结论）
- 父目录：`Test-Path`=True、`Get-ChildItem 父目录`=**成功**、在父目录下建子目录=**成功**；
- **但枚举 pytest 自己建的 `run1` 目录 → `UnauthorizedAccessException`**；同 `.venv` Python 子进程：`LIST run1`/`MKDIR run1/x` → `WinError 5`、`WRITE run1` → `Errno 13`、`STAT/ACCESS` 正常；
- **分界线是目录创建 mode**：pytest 在 `_pytest/tmpdir.py` 用 `mkdir(mode=0o700)` 建 basetemp 与每个测试的 tmp 目录（139/158/218 行），
  DSH 沙箱把它当成"仅属主可访问"，**连沙箱内的工人自己也枚举/写入不了**。
- 所以：**"父目录预建"只能解决 `basetemp.mkdir` 那一步，解决不了 pytest 自建 0o700 目录**（这是与 codex 的关键差异 ——
  codex 的 `workspace-write` 允许枚举自建目录，本项目 20+ 张卡都在其下跑通）。

### 配置面（`dsh --profile headless --dump-config`）
```yaml
- id: sandbox-policy
  config:
    mode: !!js process.env.DSH_PERMISSION_MODE ?? 'workspace-write'
    workspaceRoot: !!js process.cwd()
- id: permission
  config:
    presets:
      read-only:          { sandbox: read-only,          approval: ask }
      workspace-write:    { sandbox: workspace-write,    approval: ask }
      danger-full-access: { sandbox: danger-full-access, approval: never }
```
**只有三档，没有细粒度放行开关**（无 allow-list / 路径白名单 / ACL 覆盖）。`DSH_PERMISSION_MODE` 是唯一杠杆。

### 处置（**必须让用户拍板**，涉及安全取舍）
- **A（能干活）**：派工脚本里 `export DSH_PERMISSION_MODE=danger-full-access`（`approval: never`，headless 友好）。
  沙箱保护实际仅剩：`AGENTS.md` 纪律 + **无 git + 无网络** + 卡面写入白名单 + 调用方事后 `git status/diff` 范围核对 + 独立重跑验收。
- **B（保安全）**：测试类卡继续用 codex（其 `workspace-write` 下 pytest 正常）；或把"0o700 目录对沙箱自身进程锁死"当 bug 反馈 DSH，修复后再用。
- 预检脚本/任务留档：`project/outputs/dsh_probe{,_2,_3}_task.txt` 与 `project/outputs/待审核/DSH预检/probe{,2,3}/`。

### 顺带的正面样本
同批预检里 DSH 的自证行为质量高：**主动补做对照实验**、给出源码级定位（`_pytest/tmpdir.py:158`）、
**逐条列出未验证项**（"未在 read-only/workspace-write 下重复本实验"）、失败那次的日志也保全不覆盖。
→ 派工单里"未验证即声明""留两次运行的证据"这类条款确实生效。
