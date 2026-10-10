# 交付前运行时冒烟（pre-handoff runtime smoke）

> 用在：卡/功能的自动测试已全绿，接下来要请**用户**手测界面或端到端链路之前。
> 测试跑在夹具里（mock 传输、pytest 临时目录、临时数据库），用户点的是**真实进程**；两者之间的缺口
> （配置闸门、初始化数据、服务未换新配置、响应字段与前端假设不一致）只有跑一次真实链路才会暴露。

## 1. 配置闸门：先读源码，再写 .env

- 多闸门设计（如「环境 + provider + 确认短语 + 固定数据目录」）的**字段名与取值字面值以 `config.py` 为准**，
  不要照文档/裁决里的示例键名猜：猜错表现为一个稳定的配置错误码，看起来像"配置写错了"，实则是键名或字面值不符。
- 改动 `.env` 前先备份；**只打印键名，绝不回显值**；用户原有的密钥要原样保留（合并而非重写）。
- 用一段一次性脚本做"读—改—写"，输出仅 `键名列表` + `原有密钥是否保留=True/False`，避免密钥进入对话。

## 2. 初始化数据：读 CLI 源码确认守卫

- 跑项目自己的 seed/初始化 CLI，写到**独立开发目录**，不碰正式数据。
- CLI 报稳定错误码时，**先读源码定位守卫条件**（`grep -n "<错误码>" -B12 <file>`），再改命令或环境：
  典型守卫是 fail-closed 的 `--reset`——它拒绝没有标记文件（如 `DEV_STUB_ONLY`）的目录，防误删正式库；
  **首次建库必须不带 `--reset`**，由无参调用创建目录与标记，`--reset` 只在重建时用。
  不要靠反复调整 env 来试错。

## 3. 隔离核对（跑完必须核）

- 正式数据与 `.env` 的 mtime/size 与"工人开工前"一致（种子只应落在独立目录）。
- 依赖清单零变化：`git diff --stat -- pyproject.toml frontend/package.json`（空 = 未改）。
- 新增数据目录里应能看到标记文件与库文件。

## 4. 重启服务：改了 .env 就得重启

- `--reload` 只盯 `.py`，**不会重读 `.env`**；不重启就仍是旧配置，报错会和你的配置对不上（常见误判："改造没生效"）。
- 停旧进程**只按 PID 点杀**（禁按名字批量）；若那是用户用 VSCode 任务启的，**明确告知他**，他的终端会显示进程已停止。
- 起新服务用托管背景进程（`background=true` + 就绪通知，或用启动完成串作为 watch pattern），起完用探针确认
  （文档端点 200 / 一个无副作用接口 2xx）。

## 5. 真实 HTTP 冒烟：按前端真实顺序走完整条链

用标准库脚本即可（`urllib` + `http.cookiejar`），要点：

- 状态变更请求带 `Origin`（后端白名单里的那个）+ `X-CSRF-Token`（从 `csrf_token` cookie 读）；cookie 全用同一个 jar。
- **顺序照前端真实交互**：引导/登入 → 建资源 → **取详情** → 业务前置步骤 → 主操作 → 决策类操作。
- **创建接口的响应常不含子资源**（例如新建会话返回 `script: null`）：拿不到字段时**去看前端怎么取的**
  （多半是 `GET /<res>/{id}` 取详情），不要自行推断或改后端。
- **故意用一个陈旧版本号**调一次决策类接口，确认乐观并发冲突（409）真实存在 —— 这同时也是用户手测清单里的一项。
- 只打印**状态码 + 关键字段长度/计数**（内容不进对话）；失败时打印响应体前 200~300 字符即可定位。
- 脚本放临时目录，不进仓库。

```python
import http.cookiejar, json, urllib.request
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def csrf():
    return next((c.value for c in jar if c.name == "csrf_token"), "")
def call(method, path, body=None, need_csrf=False):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Origin", ORIGIN); req.add_header("Referer", ORIGIN + "/")
    if data: req.add_header("Content-Type", "application/json")
    if need_csrf: req.add_header("X-CSRF-Token", csrf())
    try:
        with opener.open(req) as r:
            raw = r.read().decode(); return r.status, (json.loads(raw) if raw[:1] in "{[" else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw[:200]
```

## 6. 交付清单（只留用户要做的）

给三样：**能点的 URL**、**点什么**、**哪些是刻意标记的假数据**（如统一前缀）；并明确列出
「自动测试覆盖不到、只能你手测」的那几项。起服务、初始化、配环境全部由调用方做完 —— 用户只负责点。

> 若链路里仍有外部依赖没接（真实模型、第三方 API），优先派生一张**开发桩**卡把本地链路打通，
> 而不是让用户等着没法测（见 SKILL.md §五）。
