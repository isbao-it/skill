# pytest `--basetemp` 在 Windows 上的正确用法（两条判据）

> **本文更正 `references/worker-sandbox-basetemp-acl.md` 里的一个错误说法。**
> 那份文件写「该父目录不存在，pytest 会自己 `mkdir(parents=True)` 建出来」—— **是错的**（2026-09-19 实测推翻）。
> 其余内容（ACL 收紧导致 `WinError 5`、UTF-16 日志、只读复现）仍然有效，两份合起来看。

## 两条判据（背这一句就够）

**「父目录先建好、子目录名字要新」**

| 报错 | 含义 | 处置 |
|---|---|---|
| `FileNotFoundError: [WinError 3] 系统找不到指定的路径` | **父目录不存在** —— pytest 建 basetemp 用 `mkdir(parents=False)`，**不会补父级** | 派工前 `mkdir -p <父目录>`；卡面写 `<父目录>/<尚未存在的子目录>` |
| `PermissionError: [WinError 5] 拒绝访问`（工人特有）| **父目录 ACL 收紧** —— 复用了早前卡留下的旧目录（ACL 只剩 `SYSTEM/Administrators/OWNER RIGHTS`，无用户 ACE / 无 `Users`） | 换一个**新建**的父目录前缀（继承项目根 ACL，含 `Users`），别复用旧 `.pytest_tmp/` |

实测佐证：`.pytest_tmp-08b/h-cov` 在父目录缺失时 9 个用例全 ERROR（`WinError 3`）；先 `mkdir -p .pytest_tmp-08b`，
同一条命令立即通过。而老 `.pytest_tmp/` 里的子目录对工人永远是 `WinError 5`（Hermes 自己跑却正常 ——
所以"我能跑过、工人跑炸"这类分歧，第一件事是查父目录是否存在、ACL 是否收紧）。

## 派工单照抄句式

```
basetemp 一律用 `<新父目录>/<尚未存在的子目录名>`（如 .pytest_tmp-12c/r03-targeted）；
父目录已由调用方 mkdir -p 建好。若报 WinError 3/5 → 立即停并如实报告，
不许反复重试、不许自行改卡面路径、不许去动文件系统权限。
```

`.gitignore` 补一行 `.pytest_tmp*/`（覆盖所有变体，保留原 `.pytest_tmp/`）。

备选（要动 ACL，非默认）：`icacls .pytest_tmp /grant "*S-1-5-32-545:(OI)(CI)F" /T` 给 `Users` 授权；
或删掉旧 `.pytest_tmp`（可再生临时产物，按删除纪律须先列清单取得授权）。

## 顺带两条

- 工人 `details/*.log` 在 Windows 上常是 **UTF-16**（PowerShell 重定向）→ 读前 `iconv -f UTF-16LE -t UTF-8`，
  否则满屏 `\u0000` 会让人误判"日志是空的"。
- **Hermes 的全量回归别和工人的 pytest 并发跑**：实测同一套 612 用例，独占 **5:47**，与工人并发 **7:00** —— 只有慢，没有别的收益。
