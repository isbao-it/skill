# Codex exec 派工三大坑（2026-09-17 卡06 实测）

派工 `codex exec` 时反复踩到的三个非额度类坑，每次都可能让产出报废或命令白跑。带「实测」字样的均为本机验证。

## 1. `-o` 路径撞上工人产出文件 → 产出被覆盖

- **现象**：工人自报「已写 299 行裁决」，回来看文件只剩 34 行——那是 Codex 退出时用**最终答复（汇报摘要）**覆盖了工人刚写好的同名文件。
- **根因**：`-o`（最终答复落盘路径）与派题里让工人写的产出文件路径**相同**，Codex 进程结束时把摘要写进同一路径。
- **铁律**：`-o` 永远指向 `<产出名>_日志.md`，绝不与工人产出文件同路径。产出文件由工人写、调用方 Python 读回验证行数/哈希。
- **已被覆盖后的反解**：`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` 里找 `event_msg` 且 `payload.item.type == "FileChange"` 的记录，其 `payload.item.changes[<路径>].content` 是**完整文件内容**（整文件重建，比 `apply_patch` 载荷更全、更可靠）。配合本 skill 的 `scripts/recover_codex_agent_files.py` 使用。

## 2. 长提示词内联进命令 → 引号/反引号炸 shell

- **现象**：`codex exec ... "含 "引号" 的提示词"` 直接报 `bash: unexpected EOF while looking for matching '"'`，exit 2，**Codex 根本没启动**（不是额度/工人问题）。
- **根因**：提示词里的英文双引号/反引号与 bash 的引号配对冲突。
- **铁律**：长提示词一律 write_file 写到临时文件（中文路径可，内容用「」与《》代替 ASCII 引号更保险），再 `codex exec ... "$(< 提示词文件)"` 读入。

## 3. 新测试目录复用既有 basename → 全量收集失败

- **现象**：`tests/integration/auth/test_contracts.py` 与 `tests/integration/sessions_diff/test_contracts.py` 并存，全量跑报 `Interrupted: 2 errors during collection`（import file mismatch）。定向只选一个目录时不暴露。
- **根因**：pytest 默认 `prepend` 导入模式按 basename 做模块名，重名即冲突。
- **根治**：在 `pyproject.toml` 的 `[tool.pytest.ini_options]` 的 `addopts` 加 `--import-mode=importlib`（模块名按完整路径解析），一劳永逸，后续每张卡都能安心复用 `test_contracts.py` / `test_performance.py` 这类名字。
- **连带坑**：新增仓储模块会撞「冻结仓储文件清单」的既有契约测试（`test_repository_contracts.py` 硬编码文件集合 + 方法数），须同步**扩展**该测试（只增条目/计数，不改既有断言；同一类问题已踩 04a、05 两次）。
