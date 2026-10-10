# 技能来源标注

本文件用于声明各技能的来源与授权状态。**发布前请逐条核对。**

| 分类 | 技能 | 来源判断 | 说明 |
|---|---|---|---|
| 01-流水线工程流程 | `dev-pipeline` | 自研 | 你的软件开发自动化流水线主技能 |
| 01-流水线工程流程 | `dev-pipeline-governance` | 自研 | 流水线治理规则 |
| 01-流水线工程流程 | `development-workflow` | 自研 | 需求→架构→任务卡→测试→审核闭环 |
| 01-流水线工程流程 | `cli-worker-dispatch` | 自研 | 派工/验收/额度口径，含 16 篇 references |
| 01-流水线工程流程 | `task-card-authoring-and-audit` | 自研 | 任务卡与测试卡编写/审计规范 |
| 01-流水线工程流程 | `local-dev-harness` | 自研 | 本地开发栈与 LLM provider 切换 |
| 02-编码规范与质量 | `andrej-karpathy-skill` | 待核实 | 名称指向 Karpathy 相关上游，建议确认来源后署名 |
| 02-编码规范与质量 | `ponytail` | 疑似上游(MIT) | frontmatter 自带 license: MIT，非原创，建议保留版权声明 |
| 02-编码规范与质量 | `ponytail-review` | 疑似上游(MIT) | 同上，属 ponytail 系列 |
| 02-编码规范与质量 | `ponytail-audit` | 疑似上游(MIT) | 同上 |
| 02-编码规范与质量 | `ponytail-debt` | 疑似上游(MIT) | 同上 |
| 02-编码规范与质量 | `ponytail-gain` | 疑似上游(MIT) | 同上 |
| 02-编码规范与质量 | `ponytail-help` | 疑似上游(MIT) | 同上 |
| 02-编码规范与质量 | `dogfood` | 待核实 | 探索性 QA 流程 |
| 03-设计与界面 | `impeccable` | 待核实 | 设计评审/塑造 |
| 03-设计与界面 | `ui-ux-pro-max` | 待核实 | UI/UX 设计知识库，含大量 data/*.csv |
| 03-设计与界面 | `gpt-taste` | 待核实 | 前端动效/视觉实现 |
| 03-设计与界面 | `clone-ui` | 待核实 | 网页 UI 像素级复刻 |
| 04-桌面与系统交互 | `computer-use` | 自研 | 桌面自动化驱动，version 2.0.0 |
| 05-Hermes自身配置 | `hermes-desktop-plugins` | 自研 | Hermes 桌面插件开发 |
| 05-Hermes自身配置 | `hermes-themes` | 自研 | Hermes 主题开发 |
| 05-Hermes自身配置 | `memory` | 自研 | 跨会话持久记忆机制 |
| 06-通信与社交 | `yuanbao` | 自研 | 元宝群聊 @ 与信息查询 |

## 待办

- 「待核实」的 8 条：确认是否为原创。若非原创且上游未授权，公开发布前应移除或补署名。
- 「疑似上游(MIT)」的 7 条 ponytail 系列：MIT 允许转载，但**必须保留原版权声明**；请把上游项目的 LICENSE 原文补进对应目录。
- 判断依据：本机 cc-switch 数据库将它们统一记为 `local:` 本地技能，无远程仓库来源记录，故无法从元数据区分原创与转载。
