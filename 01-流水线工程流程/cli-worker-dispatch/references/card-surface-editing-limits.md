# 改卡面/交付文档的两个硬约束：字符上限、别用超长内联命令（2026-09-19 实测）

## 一、字符上限会咬人：**先算清能加多少字再落笔**

卡面体量是硬门槛：执行卡 ≤8,000 / 测试卡 ≤6,000 / 合计 ≤14,000 字符。

实测翻车过程（卡12c 初审修正）：往测试卡里补了两段"预授权修正"文字后，字符数从 5,918 涨到 **6,647**，
之后**分三轮**各砍 15~240 字符才刚好压到 6,000（`6,647 → 6,239 → 6,147 → 6,015 → 6,002 → 6,000`）——
每一轮都要重写文件、重跑校验，纯粹是浪费。

**省事做法**：
1. 动手前先 `len(卡面)` 量一遍，算清"还剩多少字符额度"，再把补充文字压缩到额度内；
2. 压缩优先级：**细节留任务卡/裁决，测试卡只留结论**。
   例：DTO 字段清单在测试卡只写「`ManagedUser`、`UserListQuery`、`ManagedUserPage`、`AdminBootstrapResult`（字段逐字见任务卡§2）」，
   比逐个列出字段省 ~170 字符；
3. 同一句话在不同小节重复出现时，删掉重复的那处（预授权语最容易在 §2/§4/§6 各写一遍）；
4. 改完立刻在脚本里打印字符数对账，别等下一轮才发现超限。

## 二、改卡面**别用超长 heredoc**：写临时脚本、**按行号改写**

同一件事我当天被运行时拦了三次：

```
BLOCKED (hardline): command parser limit or malformed executable payload
...
Your command was saved to .../cache/blocked-scripts/blocked-*.sh
```

触发条件不是"操作危险"，而是**内联 payload 过长 / 引号嵌套无法解析**（超长 heredoc、多层引号的一行命令）。
它给的恢复路径是 `bash <blocked-scripts/*.sh>`，但那只是"把刚才那条照跑一遍"——**别把它当常规做法**。

**稳的路子**：用 `write_file` 写一个临时脚本（如 `.tmp-hermes/patch_x.py`），然后 `python -B` 跑它：

```python
lines = path.read_bytes().decode("utf-8").split("\n")
lines[lineno - 1] = 新文本          # 按行号改写，不做锚点替换
path.write_bytes("\n".join(lines).encode("utf-8"))
print(len(path.read_bytes().decode("utf-8")))   # 顺手打印字符数对账
```

好处三合一：① 免疫引号/转义；② 免疫"锚点零命中只改一半"（`references/initial-review-gates-and-scripted-doc-edits.md` 二节讲的坑）；
③ 能一次改多处并在同一脚本里核对字符数。跑完 `rm -rf .tmp-hermes`。

**要保命的一条**：临时脚本里凡是 `str.replace`，都写 `assert old in text`；
凡是要写进 Markdown 的**反引号包着 git hash** 的文字，**不要在 bash 双引号里拼**——
实测 `"...（70f0137，..."` 被 shell 当命令替换执行，hash 变成空字符串写进了文件，只能再补一版修。
