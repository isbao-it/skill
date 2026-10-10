# 联动门禁与「先诊断再派工」（2026-09-18 实测，卡09 全链路）

> 本文补充两处既有资料：
> - `dispatch-contract-for-new-repository-modules.md` §1 —— 那里只列了**第 ① 处**联动冻结测试，实测共 **3 处**，见 §1；
> - `resume-vs-fresh-session-and-delivery-record-gates.md` §一/§三 —— 补成本量级与第二个覆盖率坑，见 §2。

## 1. 联动冻结测试共 **6** 处（2026-09-19 更新），初审必须**主动枚举、一次全查**（只查 ① 会多返工一整轮；漏 ④/⑥ 会到全量才炸）

| # | 文件 | 关键断言 | 什么改动必然打挂它 |
|---|---|---|---|
| ① | `tests/unit/repositories/test_repository_contracts.py` | 仓储文件名集合、实现类→端口映射、**公开方法总数**（如 `sum(len(methods))==48`）、DTO 字段数（如 73） | 新增仓储文件 / 仓储方法 / DTO 字段 |
| ② | **`tests/unit/test_domain_ports.py`**（约 137 行） | **端口方法白名单** `repository_ports == {...}`（另有 `app/domain/*.py` 文件集合检查） | **新增任何端口方法** |
| ③ | **`tests/integration/repositories/` 下的既有集成测试** | 旧契约行为（如「候选可带任意 status」） | 本卡**收紧 DTO 校验或状态值域**（如 status 只收 `PENDING\|OBSERVING`） |
| ④ | **`tests/integration/sessions_diff/test_contracts.py`**（卡05 端口/DTO/分层契约门，约 152 行；**2026-09-18 卡11 实测新增**） | `ScriptRepositoryPort` **公开方法集合等于批准清单**（当时 9 个）+ 卡05 DTO 字段元组 + 服务依赖方向 | **给卡05 已有端口加方法**（卡11 加 4 个 → 必红）。它不在 `repositories/` 下，历次清单都漏了它 |

| ⑤ | **`tests/api/test_12_01_factory_dto.py`**（接口层路由 golden；**2026-09-19 卡12c 出卡时抓到**） | **路由条数与每条的成功码/出网 DTO 逐项匹配**（当时 35 条、恰好 4 个 202）、冻结 DTO 字段 | **新增/删除任何 HTTP 路由**或改其成功码 → 必红（`test_12_03_authorization.py` 的授权矩阵同理，6→8 资源/24 格） |
| ⑥ | **`tests/integration/auth/test_contracts.py`**（身份契约门；**2026-09-19 卡12c 全量回归才炸出**） | `IdentityRepositoryPort` **公开方法集合**（当时 6 个）+ **40 表 / 208 物理名 / `0003` head / PRAGMA** + 认证 DTO 字段元组 | **给身份端口加方法**（卡12c 加了 4 个 → 必红）。它不在 `repositories/`、也不在 `sessions_diff/` 下，**是第 3 个只按"卡名"找不到的门** |

**别再靠记忆列门 —— 用枚举命令（出卡/初审必跑，把命中处全部列入预授权）**：

```bash
# 1) 所有"断言某端口方法集"的门
grep -rln "_methods(\|public_protocol_methods\|RepositoryPort\b" tests/ | sort -u
# 2) 所有"表数/物理名/迁移 head"守卫
grep -rln "== 40\|208\|alembic_version\|physical" tests/ | sort -u
# 3) 所有"路由/成功码/DTO 字段"golden
grep -rln "factory_routes\|202\|model_fields" tests/ | sort -u
```

**本项目已知门清单（截至 2026-09-19）**：`tests/unit/repositories/test_repository_contracts.py`（实现→端口映射 + 公开方法总 60 + DTO 字段总 185→…）、
`tests/unit/test_domain_ports.py`（8 协议白名单，**刻意不含身份/接口端口** —— 不要往这里塞，只回归）、
`tests/integration/sessions_diff/test_contracts.py`（卡05：Script 端口 13 + DTO + 枚举 + 分层，**只回归**）、
**`tests/integration/auth/test_contracts.py`（身份端口 6 + 40/208/0003/PRAGMA）**、
`tests/api/test_12_01_factory_dto.py`（路由 golden 35→37、202=4）、`tests/api/test_12_03_authorization.py`（授权矩阵）、
`tests/unit/db/approved_contract.json`（25 表 + 3 跨卡 FK —— **只管表/物理对象，加 DTO/枚举不影响**）。

**派工单写法**：**枚举出的命中处全部同时**列入写入白名单并预授权**最小扩展**（只增不减、更新总数、逐处给出精确期望值），
写明「该失败是本卡预期产物，不是要回退实现」。
③ 的同步**必须保留原验证意图** —— 那条用例原本验的是「批次要求已发布统计集 + 原子性」，
不是因为枚举值本身；改成新契约后仍要验原子性。

**工人永远发现不了它们**：按纪律工人只跑定向、不跑全量，全量归调用方。代价实测 = 白烧一轮（R04 10.6 万 token）。

## 2. 覆盖率门槛：第二个坑是「**不可达**」

`--cov-fail-under` 判的是**总和**（第一条坑，见既有资料 §三）；第二条坑是**门槛本身不可达**：

- 实例：卡面要求**既有** `app/repositories/<module>.py`（978 行、本卡只新增其中 6 个方法）statement ≥90%
  → 实测天花板只有 **60%**（缺口一大片在本卡范围外的既有分支）→ 工人怎么修都过不了，白烧一轮。
- **写法**：门槛落在既有大文件上时，一律写成「**本卡新增/变更语句** statement ≥X%」，
  或先给可达性论证（要补哪些真 SQLite 集成测试、覆盖到哪几条分支）。既有文件的全量覆盖率归模块级/项目级回归。
- **正面样本**：新模块 `app/agents/<agent>.py` 94%、既有仓储经"真 SQLite 集成测试"补到 90% —— 按上写法即可达。

**成本量级（供预算与交底）**：一张 7 组 GWT + 新 Agent + 6 个仓储方法的卡全链路 ≈ **854k token**，
≈ **5 倍**于一张 6 文件 / 18 用例的卡（166k）。三次可避免的浪费：① 漏第 ②/③ 处联动文件；
② 失败只写「先定位真因」不给真因（两轮 29.3 万）；③ 覆盖率门槛不可达。

## 3. 能自己复现的失败，**先只读复现，再派工**

工人两轮盲派（合计 29.3 万 token）没解决的同一失败，调用方用**只读复现脚本**几分钟钉死：

```python
# 只读诊断：内存 SQLite + 直接调真实仓储，不碰任何项目文件
engine = create_engine("sqlite:///:memory:")
storage.XRow.metadata.create_all(engine)
repo = storage.XRepository(sessionmaker(bind=engine, expire_on_commit=False))
r1 = repo.start_or_get_run(cmd, key, rules)       # call1 OK
# 再查库里的真实行：发现 week_start 存成字符串 '2026-09-07 00:00:00+00:00'
r2 = repo.start_or_get_run(cmd, key, rules)       # call2 FAIL ← 回查用 date 对象比字符串，永远查不到
```

**结论与纪律**：派工单只写「先定位真因」= 让工人从零摸索；
把 **真因 + 复现证据 + 两条候选修法**（推荐「改用最权威的键回查」，备选「写入与回查共用同一规范化函数」）
写进派工单后，下一轮一次通过。**同一类缺陷要点名要求一并排查**（例：所有"回查已存在行"的路径），
只修可见那一处不算完成。

## 4. 工人如实自报 `failed` 是**正面样本**

**但熔断条款必须排除「可自动修复的 lint」（2026-09-20 卡12f 实测，白烧一轮）**：
派工单写"同因失败 2 次即停"时，工人会把 **`ruff check` 的 `I001 unsorted-imports`** 也当成失败原因，
跑两次 → 熔断停下 → 明明 `[*] 1 fixable`（一条 `ruff check --fix` 就好），却把整个收尾（复跑/覆盖率/交付记录）拖到下一轮。
**写法**：派工单里显式写明 ——
> 「Ruff 先跑 `ruff check <paths> --fix`；**lint 的自动修复与等价的手工格式调整不属于熔断范围**；
> 仅对『同一**非 lint** 原因失败 2 次』熔断。」

同理适用于：格式化（`ruff format`）、可自动补的 import、可自动生成的锁文件等机械性修复。


实测两轮工人在 12–16 万 token 处**如实自报** `status: failed` 并停手（未闷头试错）。
派工单里「同因失败 2–3 次即停、撞限立即停并如实报告」的熔断条款有效，值得照抄；
调用方收到 `failed` 时按 **先诊断 → 带真因重派**，不要无脑加派下一轮。

## 5. 交付记录自检（省掉调用方人工归一）

把 `summary.schema.json` 的枚举**逐字**粘进派工单（`result=pass|fail|not_run|error`、
`phase=red|targeted|regression|coverage|lint|performance`、`files[].change=added|modified|deleted`、
`cmd` 逐字可复现、覆盖率项须给 `coverage_percent`+`coverage_threshold`、`metrics.source` 必填），
并要求工人**自跑** `project/templates/validate_summary.py <summary.json>` 到 **0 ERROR / 0 WARN** 再交回。

两条 2026-09-19 补的硬要求（否则调用方拿到的是"机器可读、人读不了"的交付）：

- **`结论.md` 必须是实质摘要（派工单里写明 ≥10 行）**：判定 + 本轮改了什么 + **每条命令与结果对照** + 未验证项。
  实测工人只写一行 `ready_for_review`（既往同类交付是 27–30 行）——**卡面若只写"结论只写 ready_for_review"，工人就会照字面办**，
  所以卡面必须同时要求"实质摘要 + 最少行数"。
- **字符上限要用「字符」口径核，不是字节**：中文 1 字 = UTF-8 3 字节，用 `len(read_bytes())` 会虚高 3 倍，
  误判"超限"后瞎删内容。正确做法：`len(io.open(path, encoding="utf-8").read())`。
