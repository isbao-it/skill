# 初审的两件硬活：核「精确期望值」、砍「超范围守卫」（2026-09-19 卡12c 实测）

补充（不替代）`references/initial-review-gates-and-scripted-doc-edits.md`（联动预授权要钉在卡面）、
`references/linkage-gates-and-diagnose-before-dispatch.md`（联动门清单）、
`references/reconcile_frozen_contract_counts.py`（数字对账脚本）。

## 一、出卡端的「精确期望值」表，数字和**口径**都可能不成立

出卡产物回来做初审时，固定把卡面里每一个「X→Y 总数」回仓库求证，而不是照抄进派工单：

| 要核的 | 怎么核 | 卡12c 实测 |
|---|---|---|
| 端口方法数 | 数 protocol 里的 `def`（`grep -c '    def '` 单块）| `IdentityRepositoryPort` 现值 **6** ✓ |
| 仓储实现方法总数 | 读那条 `assert sum(len(methods) …) == N` 所在行 | `== 60` ✓ |
| 路由/状态码 golden | 读 `tests/api/test_12_01_factory_dto.py` 的 golden 表 | 35 条路由、恰 4 个 202 ✓ |
| 授权矩阵 | 读 `test_12_03_authorization.py` 的 `parametrize` 维度 | 6 资源 × 3 角色 ✓ |

**但核数字不够，还要核「这个文件是不是本卡该动的」**。卡12c 抓到的两处口径错误：

- 卡面要求 `tests/unit/test_domain_ports.py`「48→58」——但该白名单字典**刻意只含 8 个仓储协议、不含 `IdentityRepositoryPort`**；
  凑 58 等于给无关文件**新增一个协议条目**（测试结构变更 + 跨卡耦合），本卡并不需要。
- 卡面要求 `tests/integration/sessions_diff/test_contracts.py`「13＋10＝23」——该文件只断言**卡05** 的
  `ScriptRepositoryPort`(13) + DTO/枚举/分层，本卡完全不触达。

**处置（改卡面，不是改实现）**：把这两处从"必同步"降为「**只回归运行、不得修改**；
若它们因本卡变红＝越界，**停下报告**」。原则：**只预授权本卡真正触达的守卫**；
"顺带加强无关守卫"看着负责，实际是白增返工面 + 跨卡耦合，初审就该删。

## 二、新增端点/路由时，先问「哪几条守卫会红」

除了端口/DTO 总数门，还有两条容易漏的：

- **API 路由 golden**（实测 `tests/api/test_12_01_factory_dto.py`：\"35 条路由 + 恰 4 个 202\"）→ 新增 2 条路由必红；
- **授权矩阵**（`test_12_03_authorization.py`：资源 × 角色）→ 新增 ADMIN-only 资源要补格。

两条都要写进卡面并给出**新期望值**（如 35→37、202 仍 4、资源 6→8 / 24 格），否则工人只跑定向、永远看不见。

## 三、DTO 字段总数口径不许含糊

新卡常会新增若干 DTO。卡面必须写清：**若新 DTO 属于 `expected_new_fields` 清单的覆盖范围，
就按真实字段追加并写明「哪几个 DTO / 各几字段 / 总数 185→N 的精确值」；
若判定某个新 DTO 不属于该清单，逐个列出并说明理由**。"同步 DTO" 这种含糊话会让工人自由裁量，
下一轮才发现数目对不上。
