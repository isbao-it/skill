"""验收 DSH 工人家 skill 目录：frontmatter 合法性 + 反纪律内容扫描。

为什么需要：DSH 的 skill 是 fail-closed 的——frontmatter 键名拼错（驼峰、非布尔）
会让整个 skill 被**静默跳过**，不报错；而第三方改写的 skill 还可能混进
git commit/push、pip install、跑全量回归这类与工人纪律冲突的指令。
所以装完必须机器校验，不靠肉眼扫。

用法：python validate_dsh_skills.py [skills_dir]
默认 skills_dir = C:/Users/<user>/.dsh-worker/skills
退出码：0 = 全部通过；1 = 有 ERROR。
"""
import os
import re
import sys

DEFAULT_DIR = "C:/Users/<user>/.dsh-worker/skills"
# 禁止内容按【行】判定，并跳过"否定/边界"语境的句子。
# 为什么：技能正文里出现「全量回归由 Hermes 跑」「禁止 pip install」是正确的边界声明，
# 朴素整篇匹配会把这类正话说成违规（第一版就误报了 7 条）。
EXTRA_RULES = [
    # PowerShell 通道（DSH 的 pwsh 工具）不认 MSYS 路径与 bash 的退出码变量——
    # 第一版 6 份 skill 里就混进过 `cd /c/...` 与 `echo "exit=$?"`，必须机器拦住。
    (r"cd\s+/[a-z]/|cd\s+/c/", "ERROR", "MSYS 路径（pwsh 通道认不出，用相对路径或 C:/ 形式）"),
    (r'echo\s+"?\$(\?|LASTEXITCODE)"?', "WARN", "bash 退出码写法（pwsh 里用 $LASTEXITCODE）"),
]
NEGATION = ("由 Hermes", "hermes", "禁止", "不得", "不要", "不是", "不属于", "非工人", "边界", "交给 Hermes")
FORBIDDEN = [
    (r"git\s+(commit|push|merge|checkout|rebase|branch\s+-D)", "git 操作（工人禁 git）"),
    (r"pip\s+install|npm\s+i(nstall)?\s|apt-get\s+install", "安装依赖（须先报告等批准）"),
    (r"跑全量回归|全量回归|pytest\s+tests/?\s*$|pytest\s*$", "全量回归（Hermes 的活）"),
    (r"--cov-branch", "覆盖率分支口径（本项目禁）"),
]
REQUIRED_KEYS = ("name", "description")


def parse_frontmatter(text: str):
    """取出 --- 包裹的 frontmatter；返回 (键值字典, 正文)。缺 frontmatter 返回 (None, text)。"""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.S)
    if not m:
        return None, text
    body = m.group(2)
    kv = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            k, v = line.split(":", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
    return kv, body


def check(path: str) -> list:
    """校验单个 SKILL.md；返回 [(级别, 说明)]。"""
    issues = []
    text = open(path, encoding="utf-8").read()
    kv, body = parse_frontmatter(text)
    if kv is None:
        return [("ERROR", "缺 frontmatter（--- 包裹块）")]
    for key in REQUIRED_KEYS:
        if key not in kv or not kv[key]:
            issues.append(("ERROR", f"frontmatter 缺 {key}"))
    name = kv.get("name", "")
    if name and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        issues.append(("ERROR", f"name 不是 kebab-case: {name}"))
    if name and name != os.path.basename(os.path.dirname(path)):
        issues.append(("WARN", f"name({name}) 与目录名不一致"))
    desc = kv.get("description", "")
    if desc and len(desc) > 500:
        issues.append(("ERROR", f"description {len(desc)} 字符 > 500（目录会被截断）"))
    # 未声明的可选键按 DSH 规则会被忽略或整条跳过，这里提示拼写风险
    for key in kv:
        if key not in ("name", "description", "whenToUse", "metadata",
                       "disable-model-invocation", "user-invocable"):
            issues.append(("WARN", f"疑似拼错的 frontmatter 键: {key}"))
    if not re.search(r"##\s*何时用", body):
        issues.append(("WARN", "正文缺 「## 何时用」小节"))
    for pat, why in FORBIDDEN:
        for lineno, line in enumerate(body.splitlines(), 1):
            low = line.lower()
            if any(neg.lower() in low for neg in NEGATION):
                continue
            hit = re.search(pat, line)
            if hit:
                issues.append(("ERROR", f"第{lineno}行命中禁止内容「{hit.group(0).strip()}」→ {why}: {line.strip()[:70]}"))
                break
    for pat, level, why in EXTRA_RULES:
        for lineno, line in enumerate(body.splitlines(), 1):
            low = line.lower()
            if any(neg.lower() in low for neg in NEGATION):
                continue
            if re.search(pat, line):
                issues.append((level, f"第{lineno}行 {why}: {line.strip()[:70]}"))
                break
    chars = len(text)
    if chars > 4500:
        issues.append(("WARN", f"正文 {chars} 字符偏长（建议 ≤4000，省工人上下文）"))
    return issues


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    if not os.path.isdir(root):
        print(f"目录不存在: {root}")
        return 1
    files = []
    for entry in sorted(os.listdir(root)):
        p = os.path.join(root, entry, "SKILL.md")
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isfile(os.path.join(root, entry)) and entry.endswith(".md"):
            files.append(os.path.join(root, entry))
    if not files:
        print(f"没有找到任何 SKILL.md: {root}")
        return 1
    errors = 0
    for p in files:
        issues = check(p)
        status = "OK" if not issues else ("ERROR" if any(i[0] == "ERROR" for i in issues) else "WARN")
        errors += sum(1 for i in issues if i[0] == "ERROR")
        print(f"[{status}] {os.path.relpath(p, root)}  {os.path.getsize(p)} 字节")
        for level, msg in issues:
            print(f"        {level}: {msg}")
    print(f"\n合计 {len(files)} 个 skill，ERROR {errors} 条")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
