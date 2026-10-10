# 重依赖 / 真实模型适配器的测试隔离范式（2026-09-17 卡07b 实测）

适用：工人要在项目里接一个**又大又要下载又要 GPU**的依赖（语音识别 faster-whisper、本地 LLM、
图像模型……），而 CI 与日常 `pytest` 必须是秒级、零网络、零模型的。配套 `SKILL.md` §一（派工合同）
与 §四（验收）。

## 1. 契约四条（写进派工单，缺一条就会炸）

1. **默认套件永不需要真依赖**：定向测试一律插**假后端**（零模型 / 零网络 / 零密钥 / 确定性输出）
2. **真实路径不进默认套件**：真实模型用例带 marker（如 `@pytest.mark.asr_real`），**默认排除**
3. **实现必须延迟导入 + 稳定错误码**：适配器**构造期零副作用**（不 import 重依赖、不建模型、不探 GPU、
   不下载），只有首次合法调用才走工厂；依赖/模型/设备缺失时返回**稳定错误码**（如 `asr_unavailable`），
   禁止裸异常穿透
4. **设备回退可观察**：GPU 失败 → CPU 回退必须是**只读属性**（如 `runtime_attempts` / `active_runtime`
   四值：初值 / CUDA 成功 / CPU 回退成功 / 两者失败），**不许靠日志反观察**、禁止静默失败

理由（要能对用户讲清）：`medium` 级模型约 1.5GB 且可能要 CUDA —— 若默认套件跑真模型，CI 从 2 分钟
变十几分钟，还会在无网/无卡机器上红。

## 2. 最大的坑：marker 注册了 ≠ 默认被排除（实测默认套件 1 failed）

工人按契约注册了 marker、也给真实用例打上了标记，**但 `addopts` 里没有排除它**：

```toml
# pyproject.toml —— 现状（坏）
[tool.pytest.ini_options]
markers = ["asr_real: 真实模型用例（人工运行）"]
addopts = "-ra --basetemp=.pytest_tmp --import-mode=importlib"
```

后果：**任何人裸跑 `pytest` 都会 1 failed**（无模型 → 正确抛 `asr_unavailable`，但用例期待成功）。
而工人自己跑定向时**手动加了** `-m "not asr_real"`，所以它的证据日志全是绿的、`结论.md` 也如实 ——
**它没撒谎，是这个缺口只有调用方跑裸 `pytest` 才会暴露**。

修法（收尾单，一行）：

```toml
addopts = "-ra --basetemp=.pytest_tmp --import-mode=importlib -m \"not asr_real\""
```

验收判据（缺一不可）：
- **裸跑** `python -m pytest -q` 必须全绿且打印 `N passed, 1 deselected`（证明排除生效）
- 人工命令仍可跑真模型：`python -m pytest tests/adapters/test_asr.py -q -m asr_real`
- 覆盖率仍达标（本例 92% vs 门槛 80%）

## 3. 依赖安装：venv 里没有 pip 是常态

实测 `.venv` 里 `pip` 不存在（`No module named pip`），工人装依赖直接失败、日志是 `NativeCommandError`。
处置（二选一，都写进收尾单）：

```bash
python -m ensurepip                              # 给 venv 补 pip
uv pip install <pkg>==<ver> --python .venv/Scripts/python.exe   # 有 uv 更快
```

注意：**装包 ≠ 要跑模型**。装完之后默认套件仍不该下载模型（靠 marker 排除），这是两件事。

## 4. 合成 fixture 的期望值要钉死在卡里

真实模型路径的期望输出（转写文本）必须**固定为卡面钉死的合成语句**（本例「你好，这是语音识别测试。」），
否则"转写质量"没法做确定性断言，人工跑的时候也没有可对照的答案。

## 5. 调用方复验清单（本例一次跑全绿）

```bash
grep -a "EXEC07B_EXIT" project/outputs/07b/卡07b执行运行.log   # 退出码（注意 UTF-16 日志要 -a）
.venv/Scripts/python.exe -c "import importlib.util as u; print(u.find_spec('faster_whisper') is not None)"  # 装上了吗
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider          # 裸跑：必须全绿 + N deselected
.venv/Scripts/python.exe -B -m pytest tests/adapters/test_asr.py -q --cov=app.adapters.asr --cov-report=term-missing
.venv/Scripts/python.exe -m ruff check app tests && .venv/Scripts/python.exe -m ruff format --check app tests
.venv/Scripts/python.exe project/templates/validate_summary.py <summary.json>   # 0 ERROR 0 WARN
```
