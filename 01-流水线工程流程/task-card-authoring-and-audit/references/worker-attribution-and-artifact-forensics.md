# 工人行为的归因与取证（验收侧）

> 用途：白名单外文件被改、工人自报可疑、CLI 工人挂死时，**先取证再记账**。
> 工人生死簿上的每条结论都要能指到证据；误判的代价是暂停一条健康的执行路线或白烧一轮额度。

## 1. 先归因，再定罪（针对「越界」）

`git status` 出现白名单外文件被改时，**不要直接记越界**。三步：

1. 比对该文件 **mtime** 与工人会话的起止时间（会话起止可从 rollout 文件名/首末时间戳取）。
2. 解析**该工人会话的工具调用**（§2），确认有没有指向它的写入。
3. 两者都不指向工人 → 记「未归因」，不要写进越界清单。

**纯空白/表格对齐类 diff（只改格式、零内容变化）尤其可疑**：它更像用户自己的编辑器或预览窗在保存时格式化，
而不是工人改文档。实测形态：两份文档被判越界，审计后工人 8 次工具调用无一碰它们。
按 L0「越界即暂停该执行路线」误停，损失的是整条路线；而真正越界的证据（写入调用 + mtime 落在会话内）不难拿。

**第三类制造者：验收方自己。`git status` 里上游片的夹具/生成物显示 M，先排除「我自己跑出来的」。**
测试的 `beforeAll`/setup 常会**重新生成夹具**（写 xlsx/csv 等二进制或文本，行尾、时间戳随之变化），
验收方一跑回归，这些文件就变成 M —— 与工人无关。判据：diff 只有行尾/时间戳差异 + mtime 落在**验收方自己的复跑时间窗**内
→ 记「验收方复跑产物」，并在验收记录里写明一句；不写，下一位读者会按越界处置，或以为产物被动过。

## 2. 解析 codex rollout 取真实工具调用

`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` 里**字段名要对**：

- 工具调用在 `payload.type == "custom_tool_call"`，其 `input` 是 JS 片段（形如 `tools.exec_command({cmd:...})`）。
- 命令实体在 `event_msg` / `item_completed` 的 `CommandExecution` item 里（含 `command` 数组）。
- `payload.type == "function_call"` **只有极少数条目**（如纯等待）。按它统计会把「工人做了 8 件事」误判成「只做了 1 件」，
  据此宣布它「没干活」或给它定罪都是错的。

```python
import json, glob, os
f = max(glob.glob(os.path.expanduser('~/.codex/sessions/2026/10/07/rollout-*.jsonl')))
for line in open(f, encoding='utf-8'):
    o = json.loads(line); p = o.get('payload') or {}
    if p.get('type') == 'custom_tool_call':
        print(o.get('timestamp'), p.get('name'), str(p.get('input'))[:300].replace('\n', ' | '))
    if p.get('type') == 'item_completed' and (p.get('item') or {}).get('type') == 'CommandExecution':
        print('  [CMD]', str((p['item']).get('command'))[:200])
```

同法可读「工人读了哪些文件」——判断它是否偷偷读了白名单外的文件（读本身不算越界，但会解释它为什么会猜到接口形状）。

**判「写 vs 读」必须按命令原文分类，不能用「文件名 + 写动词」正则**：`Get-Content <文件>` / `Select-String … <文件>` /
行数统计命令**都含文件名**，而 `>>` 这类「写动词」又会命中日志重定向、here-string 乃至引号内的文本
→ 粗糙正则会得出「某文件被写过」的错误结论，逼着你去质问一桩**根本没发生**的越界。
精确分类用动词白名单（`Set-Content|WriteAllText|Out-File|Add-Content|New-Item|Remove-Item|Move-Item`）；拿不准就把命令原文打出来看，别用更宽的正则去猜。

**分阶段卡要证「只读阶段没有越界」时，净 diff 不够用**：阶段 1 改过又改回、或改动与后一阶段重叠，`git diff` 里没有指纹。
按时间顺序找**第一个写操作**，判它是否就是该阶段唯一被允许的产物。验收侧配方（含对「已修条目」的回退验证与覆盖率报表口径）见
`delegated-output-verification` 的 `references/session-rollout-forensics.md`。

## 3. 零输出挂死 ≠ 网络问题

CLI 工人跑几分钟到超时、stdout 全空时，**先开日志开关取证**再判定：

- `opencode run --print-logs --log-level INFO`；codex 读 rollout 尾部。
- 实测两种常见机制：① 上游**限流**（`AI_APICallError: Rate limit exceeded`）——客户端会**无限重试**，
  对外表现就是挂死；② provider 对某模型名报错后重试。二者都**不是**网络不可达。
- 因此：判到限流 → 换工人或等窗口，**禁**当网络问题反复重跑整场（一次重跑 = 一小时额度）。
- **派工前先探活**：用单 token 提示（`"Respond with exactly: OK"`）确认模型真的可用；探活失败只报告，不派工。

## 4. 工人产出文件的编码（Windows）

- **BOM**：PowerShell `Set-Content -Encoding utf8`（Windows PowerShell 5.1 行为）会写 **UTF-8 BOM**，
  污染源码/注释/frontmatter 解析。验收时逐文件查，命中就重写为无 BOM；派工单里直接写「写文件不要带 BOM」。
  ```bash
  python -c "print(open(p,'rb').read()[:3]==b'\xef\xbb\xbf')"
  ```
- **UTF-16 日志**：PowerShell 重定向（`*>` / `>`）写的 `details/*.log` 常是 UTF-16，读前先
  `iconv -f UTF-16LE -t UTF-8`，否则满屏 null 会被误判成「日志是空的」。
