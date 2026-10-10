# 派工机制两个可复现陷阱：长内容被截断、默认测试套件红（2026-09-17 实测）

都发生在「派工」这一侧，都不需要网络/额度就能触发，都会让产出悄悄跑偏。
与另外几篇的关系：`codex-exec-dispatch-pitfalls.md`（`-o` 撞名、内联引号、basename 冲突）、
`acceptance-gate-and-error-code-triangulation.md`（校验器 0/0、错误码三角定位）。

## 一、长派工单会被静默截断 → 分块写 + `wc -c` 验字节数

**现象（两种，都实测过）**

| 写法 | 结果 |
|---|---|
| 单次 `write_file` 写 ~1.8k 字符的返工单 | 只落了 **599 字节**，工具报告成功、无报错 |
| `cat >> 文件 << 'EOF'` 追加 | 内容断在句子中间，报 `warning: here-document at line N delimited by end-of-file (wanted 'EOF')` |
| `python -c "…长内容…"` 内联 | 命令出现断口 / `SyntaxError` |

**后果**：工人拿到**半截提示词**，按缺失的约束干活 → 白烧几万 token 换一个跑偏产出。

**铁律**

1. 派工单**分块写**，每块 ≤ ~1.2k 字符：第一段 `write_file`，后续段 `cat >> 文件 << 'EOF'`。
2. **每段写完立刻核对**：`wc -c 文件`（字节数必须递增且与预期量级相符）。
3. 派工前 `tail -2 文件` 确认最后一行是完整句子、文件以换行结尾。
4. 长 Python 逻辑同理：heredoc 到临时脚本再执行，不用 `python -c` 内联。
5. 若某次读回的内容没到达（只回字数/行数、无正文），换终端 Python 打印该文件片段再看一次；
   **不要**据此判定文件不存在或内容为空。

## 二、`addopts` 漏掉真实模型 marker 的默认排除 → 裸跑必红

**现象**：工人自报「6 passed, 1 deselected」完全自洽（它跑定向时手动加了 `-m "not asr_real"`），
但你**裸跑 `pytest` 得到 1 failed** —— 真模型用例被收集执行，而环境里没有模型/GPU。

```toml
# ❌ 裸跑会跑真模型用例
addopts = "-ra --basetemp=.pytest_tmp --import-mode=importlib"
# ✅
addopts = "-ra --basetemp=.pytest_tmp --import-mode=importlib -m \"not asr_real\""
```

**铁律**

- 注册 `@pytest.mark.<real>` 的**同时**，必须把 `-m "not <real>"` 写进 `pyproject.toml` 的 `addopts`；
  派工单里明写这一条（只说「注册 marker」工人就会只注册）。
- 验收清单固定加一条：**`python -m pytest -q`（不带任何 `-m`）必须全绿**，且真模型用例显示 `deselected`；
  另外确认 `-m <real>` 能人工单独跑通（这是「自动测不可达」项，需要时再请用户出手）。

## 三、这两条为什么必须写进流程

它们都属于「工人没撒谎、日志也自洽，但整体是错的」这一类缺陷：
前者的证据在**派工单文件本身**（字节数），后者的证据在**不带参数的默认命令**里。
只看工人交回的定向日志永远发现不了 —— 所以验收必须有一条「照默认口径重跑一遍」的固定动作。
