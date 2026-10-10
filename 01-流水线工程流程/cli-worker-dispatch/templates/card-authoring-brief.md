# 出卡派工单骨架（派 CLI agent 当「首席架构师/出卡端」用）

适用：让 codex 之类产出**裁决 + 成对双卡 + 模块文档**（而非直接改实现代码）的那次派工。
实测有效版本（2026-09-18 卡10/卡11）字符量约 5.6k–8.2k，八段齐全；缺段就会被返工吃掉一轮。

> 写法：先 `write_file` 或 heredoc 写到 `"$LOCALAPPDATA/Temp/cardNN_brief.txt"`，
> 每段后 `wc -c` 核对（防静默截断），派工用 `"$(cat 文件)"`（禁把长中文内联进命令行）。
> 落 `-o` 日志路径**不要与任何交付文件同路径**（如 `project/outputs/NN/出卡NN_日志.md`）。

---

```
你是本项目首席架构师。任务：为「卡NN：<卡名>」产出**裁决 + 成对双卡 + 模块文档**。全新会话。

## 1. 已合入前提（勿重复探索）
<逐条列前序卡已提供的能力与契约，含 hash/章节号/表数/迁移 head；明确「零迁移至今未破」>
<写明本卡应复用哪些既有表，默认不新增表/列；确需新增要单独论证并作为待批准项入裁决>

## 2. 架构已冻结的卡NN 契约（务必遵守，不得改写）
<把架构文档里与本卡有关的**具体行为**抄成条目：状态机、值域、错误码「沿用不新增」、
 唯一约束、幂等口径、端口/DTO 归属、LLM 出口与「禁真实联网」、上游契约不得改写>
<写清「哪些不属于本卡」并指名由哪张卡承接（如 HTTP 路由/202 字面量归卡NN+1）>

## 3. 需要你裁决的设计点（每项 ≥3 方案对比 + 推荐 + 理由）
1. <输入取值与聚合口径/数据来源>
2. <Prompt 构造与注入防护分层（system 固定文案、原文落位、日志脱敏）>
3. <失败语义：各错误码 + 是否落库/是否计次/可否重试>
4. <幂等与并发：谁赢、返回什么、是否 0 写>
5. <用量计量与配额接线点>
6. <本卡与后续卡边界；若需新端口/新仓储方法必须列出并联动冻结测试；
    并主动判定「本卡是否存在自动测不到的项」（默认判「无」）>

## 4. 交付（全部落项目内）
A. `project/outputs/NN/裁决_NN_<短名>.md`：设计点方案对比与推荐；与既有卡的接口；**冻结契约**
   （签名/字段/枚举/值域/错误码沿用不新增/零迁移或显式迁移申请）；**架构补丁正文**（可并入 §9.8.X）
B. `project/cards/NN/任务卡_NN_<短名>.md`（**≤8000 字符**）+ `测试卡_...md`（**≤6000 字符**，
   合计 **≤14000**，行为组 ≤8）：按项目七节结构；实施白名单 ≤6 文件；枚举值/字段名/错误码/
   表物理名/阈值**必须钉进卡**；禁成段复制架构章节与整表
C. `docs/modules/NN_<短名>.md`（职责/不负责什么/上下游/数据接口/错误排查/测试场景，≤150 行）

## 5. 上轮教训（必须写进双卡，否则必返工）
1. **联动冻结测试共 3 处一次全授权**：`tests/unit/repositories/test_repository_contracts.py`
   （文件名集合/实现→端口映射/公开方法总数/DTO 字段集）、`tests/unit/test_domain_ports.py`
   （端口方法白名单）、`tests/integration/repositories/` 既有集成测试。
   双卡 §4 须同时列入并写明「**只增不减**：追加进期望集合与总数，禁删/放宽既有断言；
   该失败是本卡预期产物，不是要回退实现」
2. **覆盖率门槛须可达**：落在既有大文件上的门槛表述为「**本卡新增/变更语句** statement ≥X%」
   或给出可达性论证；分层门槛按项目定（业务层 ≥80%，禁 `--cov-branch`）

## 6. 交付记录契约（逐字遵守）
`project/templates/summary.schema.json`：`files[].change=added|modified|deleted`、
`tests[].phase=red|targeted|regression|coverage|lint|performance`、`tests[].result=pass|fail|not_run|error`、
`cmd` 逐字可复现、覆盖率项须给 `coverage_percent` 与 `coverage_threshold`、`metrics.source` 必填

## 7. 读取清单（够用即可，禁全仓探索）
架构：§<章节>（约第 N 行）、§9.8.<x>（卡XX 契约）…   ← **带行号**，能大幅压掉探索轮数
`docs/modules/<相关模块>.md`、`docs/modules/README.md`（本卡那一行）
既有实现：<与本卡同体例的样板文件>、`app/domain/ports.py`、`app/domain/entities.py`、
`app/services/` 体例、对应 `tests/` 体例；`project/cards/<上一张>/` 双卡（薄卡与自测清单样板）

## 8. 纪律
只写上述交付物；**禁**改实现代码、禁 git、禁动 `project/项目实时解释.md` 与 `project/项目学习笔记.md`；
双卡字符上限硬约束；工具调用 ≤25；撞用量上限立即停并如实报告；
首行回报 `CARDNN_OK` 或 `CARDNN_FAIL:<原因>`
```

---

## 派工命令（Windows / git-bash）

```bash
codex exec -m <模型> -c model_reasoning_effort="high" \
  -c sandbox_mode="workspace-write" -c approval_policy="never" \
  -C "<项目根>" --skip-git-repo-check \
  -o "<项目根>/project/outputs/NN/出卡NN_日志.md" "$(cat "$LOCALAPPDATA/Temp/cardNN_brief.txt")"
```

- 派前先探活 1–2k token（只回「正常」即可）确认额度可用，别拿大活去撞限
- 后台派：`terminal(background=true, notify_on_complete=true)`
- 收到 `CARDNN_FAIL:` 或产出缺失 → 先核对磁盘再决定重派（见 `worker-interruption-and-recovery.md`）
