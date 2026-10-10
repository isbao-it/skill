# 派工单与交付记录的三条完整性检查（2026-09-17 连踩后补）

补充（不替代）`references/dispatch-contract-for-new-repository-modules.md` 与
`references/worker-interruption-and-recovery.md`。三条都是「漏了就要多烧一轮」的类型。

## 1. 冻结契约测试不只查仓储文件名/方法数，**还查领域 DTO 的字段集合**

`tests/unit/repositories/test_repository_contracts.py` 里还有一条
`test_repository_command_dtos_cover_required_columns`：它断言某个命令 DTO 的**字段集**。
所以**卡面只要要求扩展某个 DTO，这条也会红** —— 不限于「新增仓储文件/端口」。

卡08 实测：卡面要求给 `CaseRevisionPatch` 加
`tags / transcript / description / published_at / views / likes` 六个字段，工人**照卡面做对了**，
但全量回归报：

```
Extra items in the left set: 'views' 'transcript' 'published_at' 'tags' 'likes' 'description'
```

卡面其实已授权「仅新增必需公开方法时，**最小增补**该测试文件，**只增不减**」，工人只是**没跑全量**
（纪律如此，全量归调用方）→ 漏掉联动 → 白搭一轮返工。

**派工单照抄**：白名单追加该测试文件；把新增字段清单**逐字列出**；写「只增不减，不得放宽既有断言」；
写「**该文件是联动文件，不算第 7 个实施文件、不算越界**」；写「**该失败是本卡预期产物，不是要回退实现**」。

## 2. 交付校验器的 WARN，多半死在 `metrics` 没有来源字段

多数 `summary.json` 校验器对「`metrics` 全为 `null`」判 WARN
（`metrics 既无 model_calls 也无 source（来源不明的读数不要写）`），而合入判据是 **0 ERROR 0 WARN**。
卡07b 与卡08 **连踩两次**，每次都多一轮补记往返。

**派工单写死一句**：`summary.json` 的 `metrics` 至少要给一个来源字段（如
`"source": "本机实测（无 LLM 调用）"`），判据 0 ERROR **0 WARN**。

**补记授权**：若只需补这一行元数据，调用方可**只动交付记录、不动代码** —— 但必须在报告里向用户
**明示「这是 Hermes 补记的元数据」**，不要把补记混进工人自报里。

## 3. 长派工单写进文件后，**必须 `wc -c` 核对字节数**

长内容一次性写入可能**静默截断**：实测出现过 599 字节的残单（预期约 1,800 字节，工人只看到一半要求），
以及 heredoc 报 `warning: here-document at line N delimited by end-of-file (wanted 'EOF')`
—— 提示词缺尾、甚至少了收尾的硬约束段。

**对策（成本极低，务必做）**：

```bash
# 第一段用 write_file；后续分段用 heredoc 追加，每段 ≤ 约 600 字符
cat >> "$LOCALAPPDATA/Temp/派工单.txt" << 'EOF'
…第二段…
EOF
wc -c "$LOCALAPPDATA/Temp/派工单.txt"        # ★ 每段后核对，派工前再核一次
```

派工命令仍用 `"$(< 派工单.txt)"`；**字节数明显小于预期就不要派**，先补齐。
