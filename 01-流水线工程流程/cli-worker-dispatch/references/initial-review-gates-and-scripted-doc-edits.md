# 初审关口前移 + 脚本批量改文档的两个静默坑（2026-09-18 卡09 实测）

配套（不替代）：`references/dispatch-artifact-and-prompt-integrity.md`（交付记录完整性）、
`references/dispatch-contract-for-new-repository-modules.md`（联动预授权的派工单句式）、
`references/resume-vs-fresh-session-and-delivery-record-gates.md`（覆盖率与额度门禁）。

## 一、联动预授权要钉在**出卡阶段的卡面**上，不是等派工单

既有的两条经验讲的是「派工单」层面；更省事的位置是**更早一步**：出卡产物（裁决 + 双卡）回来做**初审**时，
固定问三句，任何一句答案是「没有」就是漏项：

1. 本卡是否**新增/修改仓储端口方法**？→ 冻结契约测试的**总数断言**必红
   （实测 `sum(len(methods)) == 48`；注意**仓储文件早已存在**、只是给它加方法，照样打断总数断言）。
2. 本卡是否**扩展任何命令 DTO 的字段**？→ `test_repository_command_dtos_cover_required_columns` 必红
   （实测断言 73 字段；卡08 给 `CaseRevisionPatch` 加 6 个字段即触发）。
3. 两种情形下，**卡面「实施白名单」里有没有那个测试文件 + 预授权语 + 一条单文件定向命令**？
   只写在派工单里不够 —— **卡面才是工人当轮真正读的合同**，而工人按纪律只跑定向、永远看不到全量红。

卡09 实测：新增 `WeeklyLexiconRepositoryPort` 六个方法 + 给 `LexiconCandidateCreate` 加 `status` 字段，
卡面白名单却**没有**联动文件 → 初审当场补：

- 白名单追加 `tests/unit/repositories/test_repository_contracts.py`；
- 写明「**只增不减**、更新总数、禁放宽既有断言」「**不算第 7 个实施文件、不算越界**」
  「**该失败是本卡预期产物，不是要回退实现**」；
- 加一条命令让它自己跑绿：`pytest tests/unit/repositories/test_repository_contracts.py -q`（日志入 `details/`）。

**判据**：初审报告里必须出现「联动文件已预授权」。没有就在初审补 —— 等全量回归红了再返工是最贵的位置
（卡08 就是这么白烧一轮的）。

**顺带固定查一条**：覆盖率命令是不是"**合跑 + 一个阈值**"？`--cov-fail-under` 只判**单次运行的总和**，
要求「各模块 ≥80%/≥90%」就必须**每模块一条独立命令**（卡07c 的测试卡就是这么放水的，初审当场改成三条）。

## 二、脚本批量改文档：`$` 锚点必须带 `re.M`，每处替换都要 assert 命中数

主代理常做「归一 / 同步」类批量改文档（改卡面 `status`、改快照行、把裁决补丁并入架构）。用 Python 正则时：

- **不带 `re.M` 时 `$` 只匹配全文末尾** → 行级锚点（`^status:.*$`、`^| 08 …|.*$`）**静默零命中**；
  而同一批里的字面量替换却照常命中，于是「只改了一半」完全看不出来（实测改到第三次才发现）。
- 对策：每次 `re.subn` / `str.replace` 都**断言命中数**（`assert n == 1`）或把命中数打出来；
  改完用 `wc -c` / 行数对账（`ok/miss` 逐条打印最省事）。
- 同类坑：**锚点别用整条命令**。实测 `l.startswith('.venv/Scripts/python.exe -m ruff …')`
  因实际命令多了个 `-B` 而零命中 → **锚点取最短稳定子串**（如 `'ruff check app/domain'`）。
