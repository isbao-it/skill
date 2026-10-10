# 技能来源与许可

本仓库收录 23 个技能，**并非全部原创**。下表逐条标明来源；第三方内容已在上游许可要求下保留版权声明。

## 一、来自上游（已附许可原文）

| 分类 | 技能 | 上游仓库 | 许可 | 声明 |
|---|---|---|---|---|
| 02-编码规范与质量 | `andrej-karpathy-skill` | https://github.com/duolahypercho/andrej-karpathy-skills | MIT | [NOTICE.md](02-编码规范与质量/andrej-karpathy-skill/NOTICE.md) |
| 02-编码规范与质量 | `ponytail` | https://github.com/DietrichGebert/ponytail | MIT | [NOTICE.md](02-编码规范与质量/ponytail/NOTICE.md) |
| 02-编码规范与质量 | `ponytail-review` | https://github.com/DietrichGebert/ponytail | MIT | [NOTICE.md](02-编码规范与质量/ponytail-review/NOTICE.md) |
| 02-编码规范与质量 | `ponytail-audit` | https://github.com/DietrichGebert/ponytail | MIT | [NOTICE.md](02-编码规范与质量/ponytail-audit/NOTICE.md) |
| 02-编码规范与质量 | `ponytail-debt` | https://github.com/DietrichGebert/ponytail | MIT | [NOTICE.md](02-编码规范与质量/ponytail-debt/NOTICE.md) |
| 02-编码规范与质量 | `ponytail-gain` | https://github.com/DietrichGebert/ponytail | MIT | [NOTICE.md](02-编码规范与质量/ponytail-gain/NOTICE.md) |
| 02-编码规范与质量 | `ponytail-help` | https://github.com/DietrichGebert/ponytail | MIT | [NOTICE.md](02-编码规范与质量/ponytail-help/NOTICE.md) |
| 03-设计与界面 | `impeccable` | https://github.com/pbakaus/impeccable | Apache-2.0 | [NOTICE.md](03-设计与界面/impeccable/NOTICE.md) |
| 03-设计与界面 | `ui-ux-pro-max` | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill | MIT | [NOTICE.md](03-设计与界面/ui-ux-pro-max/NOTICE.md) |
| 03-设计与界面 | `gpt-taste` | https://github.com/tasteskill/tasteskill | MIT | [NOTICE.md](03-设计与界面/gpt-taste/NOTICE.md) |
| 03-设计与界面 | `clone-ui` | https://github.com/santowilem/skills | MIT（上游 README 标注，仓库无 LICENSE 文件） | [NOTICE.md](03-设计与界面/clone-ui/NOTICE.md) |

许可原文集中存放在 [`THIRD-PARTY-LICENSES/`](THIRD-PARTY-LICENSES/README.md)。

其中 `clone-ui` 例外：上游 README 标 MIT，但仓库根目录无 LICENSE 文件，故未附原文。

## 二、Hermes 生态技能（未找到公开上游仓库）

格式为 Hermes Agent 的技能规范（frontmatter 含 `metadata.hermes` / `platforms` / `version`），
未在公开仓库检索到对应来源。若属于 Hermes 官方分发内容，建议在此注明；若为自建则无需处理。

| 分类 | 技能 | 判断 |
|---|---|---|
| 04-桌面与系统交互 | `computer-use` | 待确认归属 |
| 05-Hermes自身配置 | `hermes-desktop-plugins` | 待确认归属 |
| 05-Hermes自身配置 | `hermes-themes` | 待确认归属 |
| 05-Hermes自身配置 | `memory` | 待确认归属 |
| 06-通信与社交 | `yuanbao` | 待确认归属 |
| 02-编码规范与质量 | `dogfood` | 待确认归属 |

## 三、自研（本机工作流沉淀）

| 分类 | 技能 | 说明 |
|---|---|---|
| 01-流水线工程流程 | `dev-pipeline` | 软件开发自动化流水线主技能 |
| 01-流水线工程流程 | `dev-pipeline-governance` | 流水线治理规则 |
| 01-流水线工程流程 | `development-workflow` | 需求→架构→任务卡→测试→审核闭环 |
| 01-流水线工程流程 | `cli-worker-dispatch` | 派工/验收/额度口径，含 16 篇 references 与脚本 |
| 01-流水线工程流程 | `task-card-authoring-and-audit` | 任务卡与测试卡编写/审计规范 |
| 01-流水线工程流程 | `local-dev-harness` | 本地开发栈启动与 LLM provider 切换 |

## 四、判定方法

1. 本机 cc-switch 数据库把这 23 条统一记为 `local:`（本地技能），**没有**远程仓库来源字段，所以元数据里查不出来源。
2. Hermes 的 `.hub/lock.json` 只记录 6 个从技能中心安装的技能，不包含本仓库的任何一条。
3. 因此来源靠两个手段确认：① 读 `SKILL.md` 里残留的许可与版本信息；② 用技能描述原文去公开仓库检索比对。

## 五、待办

- [ ] `clone-ui`：上游补 LICENSE 后同步过来。
- [ ] 第二节 6 条：确认归属，必要时补署名或移除。
- [ ] 若上游技能有更新，用 `scripts/sync.ps1` 前先确认不会覆盖你对本仓库做的改动。
