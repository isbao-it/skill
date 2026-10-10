# 验收闸门与错误码三角定位（2026-09-17 卡07b 实战）

## 一、裸跑默认套件必须绿（真实模型用例的 marker 契约）

工人自己跑定向时常手动加过滤，但**没写进 `pyproject.toml`**：

```toml
addopts = "-ra --basetemp=.pytest_tmp --import-mode=importlib"                        # ❌ 裸跑会跑真模型用例并红
addopts = "-ra --basetemp=.pytest_tmp --import-mode=importlib -m \"not asr_real\""   # ✅
```

- 症状：工人报「6 passed, 1 deselected」自洽；你裸跑 `pytest` 得到 **1 failed**（真模型用例跑了，但环境缺模型/GPU）。
- 验收清单写死：`python -m pytest -q`（**不带任何 `-m`**）全绿，且真模型用例显示 `1 deselected`；同时 `-m <real_marker>` 能人工单独跑通。
- 派工单要写明：「注册 marker 之外，必须把默认排除写进 `addopts`」。

## 二、交付记录 `summary.json` 的 0/0 闸门

- 判据 = `python <项目>/templates/validate_summary.py <summary.json>` 输出 **0 ERROR 且 0 WARN**（工人自报不算）。
- 常见 WARN：`metrics 既无 model_calls 也无 source`。正确补法 = **补一句真实来源**（`metrics.source = "Hermes 复核补记：定向/覆盖率/Ruff/全量均为本机实测"`），**不是**填假数字；字段缺失按契约填 `null` 而非 `0`。
- 这类对交付记录的**留痕式补记**属记账、不属改代码，但必须在回报里明确说「我补了什么」。
- 同时必做：用 Python 逐个 `os.path.exists` 核对 `结论.md` 引用的每个 `details/*.log`（工人声称生成的日志经常不存在）。

## 三、错误码三角定位：别信收敛后的异常

被验收模块若按设计把底层异常收敛成稳定领域错误码（`asr_unavailable`、`upstream_error` …），
**traceback 只显示收敛点，根因被吞**。看到稳定错误码时：

1. 照依赖链**往下走一层直接调用**，让真异常说话：
   ```python
   import traceback
   try:
       from faster_whisper import WhisperModel
       m = WhisperModel('medium', device='cuda', compute_type='float16')   # 加载成功（4.3s）
       list(m.transcribe(audio)[0])                                        # 真异常在第一次 encode
   except Exception:
       traceback.print_exc()
   ```
   本次由此定位 `RuntimeError: Library cublas64_12.dll is not found or cannot be loaded`，
   而**不是**误判成「下不动模型」（HF 的 unauthenticated 告警只是噪声）。
   Windows GPU 侧完整修复见 `windows-hermes` → `references/windows-gpu-cuda-dlls.md`。
2. **先排除三层假嫌疑**：① 站点首页 HTTP 200 ≠ 大文件能下（测 `resolve/main/... -r 0-1023` 是否 206）；
   ② 缓存目录已有 + `snapshot_download()` 秒回 = 模型完整，说明「下载」不是瓶颈；③ 耗时可当判据（GPU 加载 ~4s/转写 ~2s vs CPU 数十秒）。
3. 定位后区分**实现缺口 vs 环境缺口**：契约要求「A→B 回退可观察」而实现只覆盖「加载失败」、漏了「加载成功但首次计算失败」→ 实现缺口，**派返工**（不改契约、不加错误码）；缺运行库 → 环境缺口，补依赖 + PATH。
4. 返工单里写进「已实测复现的真异常 + 复现命令 + 期望的可观察值」，工人不必重新探索（省额度）。

## 四、返工也守同样的边界

- 返工单照写白名单 + 「不得新增错误码/枚举、不得改端口签名、不得新增文件」。
- 增补用例**先红后绿**，不改既有断言，行为组总数不超上限。
- 返工验收 = 同一套闸门重跑一遍（定向 + 覆盖率 + **裸跑全量** + Ruff + 校验器 0/0 + 范围核对），不因为是「小修」而放宽。
- 收尾类小修（配置一行、装依赖、重跑证据）**同样是派人工的活**：默认派工；只有用户明确点名让调用方自己动手时才自己改，且事后要在回报里说明这次是谁改的。
