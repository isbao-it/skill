# 工人沙箱无法在 Hermes 创建的临时目录里建子目录（pytest `--basetemp` WinError 5）

实测日期：2026-09-18（项目 bao-kuan-xin-fa 卡11 R01）。**症状 —— 同一命令，Hermes 跑过、工人跑炸。**

## 症状

工人 `codex exec`（`sandbox_mode="workspace-write"`）跑

```bash
.venv/Scripts/python.exe -B -m pytest ... --basetemp .pytest_tmp/card11-targeted > details/pytest-targeted.log 2>&1
```

报（**日志是 UTF-16**，`tail` 会看到 null 间隔，先 `iconv -f UTF-16LE -t UTF-8` 再读）：

```
E   PermissionError: [WinError 5] 拒绝访问:
    'C:\...\.pytest_tmp\card11-targeted'
    ... pathlib.py:1116  os.mkdir(self, mode)
```

真 SQLite 用例直接 `ERROR`（连断言都没进），纯内存用例照过 → 看起来像"代码问题"，其实是**目录权限**。

## 真因

1. `.pytest_tmp/` 这个目录是 **Hermes 进程早先跑 pytest 时创建的**（本机 `icacls` 显示 ACL 只有
   `NT AUTHORITY\SYSTEM` / `BUILTIN\Administrators` / `OWNER RIGHTS:(OI)(CI)(F)`，
   **没有当前用户 ACE，也没有 `Users`**，属主是自己 + OWNER RIGHTS）。
2. Hermes 以普通令牌运行 → 享有 OWNER RIGHTS → 建子目录**成功**（自己复现 `EXIT=0`）。
3. 工人的 codex 沙箱用**受限/过滤令牌**，`Administrators` 对其是 deny-only、OWNER RIGHTS 不等价 →
   在该目录内 `mkdir` 被拒（`WinError 5`）。它能在项目根新建文件（根目录 ACL 有 `Users` 写权限），
   只在**这个已存在且 ACL 收紧的目录里**失败。

判断口径：**"我能跑过、工人跑就 WinError 5 on mkdir" ⇒ 先查 `icacls`，别怀疑代码。**

## 修法（首选：换一个尚未存在的 basetemp 前缀，不动权限、不删东西）

1. 卡面/派工单里的 `--basetemp .pytest_tmp/<x>` → `--basetemp .pytest_tmp-<卡号>/<x>`；
   该父目录**不存在**，pytest 会自己 `mkdir(parents=True)` 建出来，属主与 ACL 都是工人令牌自己的 → 可写。
2. `.gitignore` 补一行 `.pytest_tmp*/`（覆盖所有变体；`.pytest_tmp/` 保留）。
3. 派工单写明：**照抄更新后的路径**，不得自行改回；若仍 `WinError 5` → **立即停并如实报告**，
   不许反复重试、不许自行改卡面路径、不许去动文件系统权限。
4. 已落盘的实现**不要回退**：新会话在原工作区续做（先 `git status` 核范围，确认只动了白名单文件）。

备选（要动 ACL，非默认）：`icacls .pytest_tmp /grant "*S-1-5-32-545:(OI)(CI)F" /T` 给 `Users` 授权；
或删掉 `.pytest_tmp`（可再生临时产物，但按删除纪律须先列清单取得授权）让工人自建。

## 顺带查出的两条排查习惯

- 工人 `details/*.log` 在 Windows 上常是 **UTF-16**（PowerShell 重定向产物）→ 读之前先转码，
  否则会看到满屏 `\u0000` 甚至误判"日志是空的"。
- 工人 `blocked` 时先做**只读复现**：同一条命令自己跑一遍 + `icacls` + 写探针，
  通常几分钟就能把"环境问题"与"代码问题"分开 —— 这两类的处置完全相反（前者修环境重派，后者派返工）。
