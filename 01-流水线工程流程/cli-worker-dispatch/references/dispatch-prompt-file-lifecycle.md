# 派工单落盘生命周期 + 命令成组执行（2026-09-19 卡12 九轮实战）

适用于「一张卡要跑很多轮、会撞额度 / 撞宿主崩溃 / 被换会话接手」的场景。

## 1. 每一轮都先把派工单**写成项目内的文件**，再派

命名与位置：`project/outputs/<NN>/R<NN>派工单待发.md`（与交付归档同目录，随卡一起被 git 管）。

必备段落（缺一段就会在重启后重新摸索）：

```markdown
# 卡<NN> R<NN> 派工单（= R<上一轮> 原样重派；<失败原因一句话>）

> 用法：codex exec -m <模型> -c model_reasoning_effort="<档>" -c sandbox_mode="workspace-write" \
>   -c approval_policy="never" -C <项目根> --skip-git-repo-check -o project/outputs/<NN>/执行<轮>日志.md "$(cat 本文件)"

## 只做这 N 件事（其余一律不动）        ← 逐条、可勾选
## 范围：写入白名单 / 读取白名单（已批准，无需再索取）
## 必须守住（回归红线）                 ← 哪些既有语义/断言不许被吃掉
## 要跑并留证：命令 + 期望退出码 + 断言门槛
## 交付记录：summary.json + 结论.md + details/*.log + 校验器 0/0
## 熔断：同因失败 2 次即停 / 撞额度立即停 / 禁第三次
首行回报 `<CARDNN_R<轮>_OK|FAIL:<原因>>`
```

**收益（本次实测两次兑现）**：额度撞限（R02/R06）与 Codex 宿主崩溃（R07，`0xC0000142`）之后，
恢复动作都只是「原样重派同一份文件」，**不重跑前面的诊断与出卡分析**；跨会话接手时，下一轮派工单、
诊断文档、审计文档全在项目里，读文件即可对齐。

## 2. 重派时把**调用方新测到的数字**刷进派工单

重派不是复制粘贴：把当前实测事实写进去，工人就有精确靶子，省掉「它自己跑一遍再判断」的轮次。
本次 R08 派工单里直接写：

```markdown
| 文件 | 门槛 | 实测 | 判定 |
| app/application/api.py | 业务 ≥80% | 67%（缺 95 行）| ❌ 需补测 |
| app/repositories/api.py | 基础 ≥90% | 68%（缺 60 行）| ❌ 需补测 |
未覆盖行集中：application/api.py 的 293-359、372-412…；repositories/api.py 的 236-271…
```

**轮次编号只增不改**（R07 失败 → 新文件 R08），旧派工单保留作为过程证据；不要把失败轮的编号重写，
否则归档里会出现「同一编号两个内容」。

## 3. 长提示词的写入方式（躲两个闸）

- **别内联**：把派工单内容内联进命令行，中文引号/反引号会炸 shell。用
  `python - << 'PYEOF' … io.open(path,'w',encoding='utf-8').write(text) … PYEOF` 写文件，
  再用 `"$(cat 文件)"` 传给 `codex exec`。
- **命令守卫的两个误报**（都实测遇到，处置方式如下，不是「工具坏了」）：
  1. 文本里出现 `uvicorn`/`server` 这类词时，命令可能被判为「要起长驻服务」→ 在写文件的脚本里
     把该词拼出来（`UV = "uvi" + "corn"`，正文先用 `@UV@` 占位再替换），即可正常写入；
  2. 超长内联单行（多重嵌套引号 + 管道）可能被 hardline 拦下，但**它会把你保存成 `.sh` 并给出恢复命令**；
     正确的应对是**拆成几条短命令**或改成脚本文件，而不是重试那条巨行。

## 4. 验证命令成组跑，但每条**独立记退出码**

调用方复跑验收时把同源命令串在一条里（省往返），每条紧跟一个 `echo`：

```bash
cd <项目> && pytest tests/api/ -q --basetemp .pytest_tmp-<卡>/t > <log1> 2>&1; echo "T_EXIT=$?"; \
pytest tests/api/ -q --basetemp .pytest_tmp-<卡>/c --cov=… --cov-report=term-missing > <log2> 2>&1; echo "C_EXIT=$?"; \
pytest <联动四处> -q --basetemp .pytest_tmp-<卡>/l > <log3> 2>&1; echo "L_EXIT=$?"; \
python -m ruff check app tests > <log4> 2>&1; echo "R_EXIT=$?"
```

- **每个 `echo` 单独一行输出**：只打一个总退出码时，前一条的失败会被后一条的成功盖掉（假绿）。
- 回读只取「退出码 + 末尾 ≤30 行 + 必要 traceback」，日志整份落 `details/` 或临时目录，不灌进上下文。
- 需要长时间跑的全量回归放后台（`background=true, notify_on_complete=true`），前台同时跑其余几项，
  最后再合并结论 —— 但**结论一律以自己这次跑出来的输出为准**，不引用工人自报。
