# skill — 我的 AI Agent 技能库

跨三个 AI CLI 通用的技能集合，按用途分类存放。技能遵循同一套约定：一个目录 = 一个技能，内含 `SKILL.md`（YAML frontmatter 的 `name` / `description` + 正文）与可选的 `references/` `scripts/` `templates/`。

**支持的工具**：Hermes Agent · Claude Code · Codex CLI（同一份 `SKILL.md` 三端通用）

## 目录结构

```
skill/
├─ README.md              本文件
├─ _sources.md            各技能来源与授权标注（重要）
├─ LICENSE                MIT
├─ 01-流水线工程流程/
├─ 02-编码规范与质量/
├─ 03-设计与界面/
├─ 04-桌面与系统交互/
├─ 05-Hermes自身配置/
├─ 06-通信与社交/
└─ _audit/                本机三端技能全景盘点（非发布内容，仅供维护参考）
```

## 技能清单

共 **23** 个技能，分 6 类。

### 01-流水线工程流程（6）

软件开发流水线的本体：从需求到合入的全流程规则

| 技能 | 说明 |
|---|---|
| [`dev-pipeline`](01-流水线工程流程/dev-pipeline/SKILL.md) | 软件开发自动化流水线 — Hermes 做架构师/PM，Claude Code 做程序员，你做决策者 |
| [`dev-pipeline-governance`](01-流水线工程流程/dev-pipeline-governance/SKILL.md) | Use when changing or following the user's dev pipeline. |
| [`development-workflow`](01-流水线工程流程/development-workflow/SKILL.md) | 按需求、架构、任务卡、测试和人工审核闭环执行软件开发任务，适用于新功能、重构、Bug 修复和项目初始化。 |
| [`cli-worker-dispatch`](01-流水线工程流程/cli-worker-dispatch/SKILL.md) | Dispatch CLI coding agents as workers and verify output. |
| [`task-card-authoring-and-audit`](01-流水线工程流程/task-card-authoring-and-audit/SKILL.md) | Use when authoring or auditing task/test cards. |
| [`local-dev-harness`](01-流水线工程流程/local-dev-harness/SKILL.md) | Use when launching a local dev stack or switching its LLM provider config. |

### 02-编码规范与质量（8）

写代码时的纪律：最小改动、根因调试、质量审计

| 技能 | 说明 |
|---|---|
| [`andrej-karpathy-skill`](02-编码规范与质量/andrej-karpathy-skill/SKILL.md) | Apply Andrej Karpathy-inspired coding-agent guidelines in Codex. Use when writing, reviewing, debugging, or … |
| [`ponytail`](02-编码规范与质量/ponytail/SKILL.md) | — |
| [`ponytail-review`](02-编码规范与质量/ponytail-review/SKILL.md) | — |
| [`ponytail-audit`](02-编码规范与质量/ponytail-audit/SKILL.md) | — |
| [`ponytail-debt`](02-编码规范与质量/ponytail-debt/SKILL.md) | — |
| [`ponytail-gain`](02-编码规范与质量/ponytail-gain/SKILL.md) | — |
| [`ponytail-help`](02-编码规范与质量/ponytail-help/SKILL.md) | — |
| [`dogfood`](02-编码规范与质量/dogfood/SKILL.md) | Exploratory QA of web apps: find bugs, evidence, reports. |

### 03-设计与界面（4）

UI/UX 设计判断、视觉实现、界面复刻

| 技能 | 说明 |
|---|---|
| [`impeccable`](03-设计与界面/impeccable/SKILL.md) | Use when the user wants to design, redesign, shape, critique, audit, polish, clarify, distill, harden, optim… |
| [`ui-ux-pro-max`](03-设计与界面/ui-ux-pro-max/SKILL.md) | UI/UX design intelligence for web, mobile, and desktop. This skill should be used when designing, building, … |
| [`gpt-taste`](03-设计与界面/gpt-taste/SKILL.md) | Elite UX/UI & GSAP Motion Engineer. For visually important web tasks, it must first generate the design imag… |
| [`clone-ui`](03-设计与界面/clone-ui/SKILL.md) | Pixel-faithful clone of any web UI into the user's existing stack, using whatever sources are available — a … |

### 04-桌面与系统交互（1）

驱动桌面完成 GUI 任务

| 技能 | 说明 |
|---|---|
| [`computer-use`](04-桌面与系统交互/computer-use/SKILL.md) | — |

### 05-Hermes自身配置（3）

给 Hermes Agent 自己扩展能力

| 技能 | 说明 |
|---|---|
| [`hermes-desktop-plugins`](05-Hermes自身配置/hermes-desktop-plugins/SKILL.md) | Write desktop app plugins that add UI panes and commands. |
| [`hermes-themes`](05-Hermes自身配置/hermes-themes/SKILL.md) | Author a Hermes color theme that skins every surface. |
| [`memory`](05-Hermes自身配置/memory/SKILL.md) | — |

### 06-通信与社交（1）

IM 群聊自动化

| 技能 | 说明 |
|---|---|
| [`yuanbao`](06-通信与社交/yuanbao/SKILL.md) | Yuanbao (元宝) groups: @mention users, query info/members. |

## 安装

**Claude Code**：把技能目录放进 `~/.claude/skills/`

**Codex CLI**：把技能目录放进 `~/.codex/skills/`

**Hermes Agent**：把技能目录放进 `~/AppData/Local/hermes/skills/`（Windows）或 `~/.hermes/skills/`

> 若只想让某一端看到某技能，就在该端的 skills 目录里建**软链接**指向本仓库对应目录——改一处三端同步，不会产生副本漂移。

## 关于 _audit/

`_audit/` 是生成这些分类时顺带产出的**本机全量盘点**（126 条技能 × 4 个技能源的分布矩阵与重复副本报告），
用来发现"同一个技能存在两份实体副本、会各自漂移"这类问题。它记录的是我本机的状态快照，
包含第三方技能仓库的技能名（如 anthropics/skills、JimLiu/baoyu-skills），**不包含其内容**。

## 来源与许可

见 [`_sources.md`](_sources.md)。本仓库收录的技能并非全部为原创，其中部分可能来自第三方上游，
发布前请核对——MIT 许可仅覆盖原创部分，第三方内容遵循其各自许可。

