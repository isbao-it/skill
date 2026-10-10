# 接浏览器端（前端）前的前置检查清单（2026-09-19 卡12f 实测，宝宽心法项目）

> 场景：后端已合入、接口都测过（TestClient/集成测试全绿），现在要写**真正的浏览器前端**。
> 这一类「后端早绿、前端一联调就死」的坑**不会**在接口测试里暴露 —— 因为 TestClient **不发 Origin、不检查 CORS、不需要 JS 读 cookie**。
> 教训来源：出 13a 前端卡之前做需求盘点时，才发现**开发态所有写请求都会 403**，若直接出前端卡必返工。

## 1. 出前端卡前，先跑这四个 grep（几分钟，省一整轮返工）

```bash
grep -rn "allowed_origins\|allowed_hosts" app/ tests/ --include=*.py   # 来源白名单在哪、是否硬编码
grep -rn "CORSMiddleware\|allow_origins\|Access-Control" app/ --include=*.py  # 有没有 CORS 中间件
grep -rn "set_cookie" app/api/ --include=*.py | head                    # cookie 名与属性
grep -rn "require_csrf\|X-CSRF-Token\|csrf_token" app/api/ | head       # CSRF 契约
```

然后确认三件事，任一为「否」就必须**先出一张"联调前置"小卡**，再出前端卡：

| 检查 | 为什么致命 |
|---|---|
| **来源白名单可配置**（不是硬编码在组合根） | 开发态前端源（如 `http://localhost:5173`）不在白名单 → 每个写请求 `permission_denied`/403 |
| **有 CORS 中间件**（或前端走同源代理） | 没有 `Access-Control-Allow-Origin` 时，跨源 `fetch` **连响应体都读不到**（错误看起来像网络失败） |
| **CSRF token cookie 是 JS 可读的**（`HttpOnly=False`） | double-submit 方案要求前端把 cookie 值放进请求头；`HttpOnly=True` 就拿不到 → 所有写请求 403，且极难 debug |

## 2. 本项目实测形态（宝宽心法，可作参照）

- `app/main.py`：`allowed_origins` **硬编码**（测试路径 `("https://testserver",)`；默认应用再补 `http://127.0.0.1:8012`）
- `app/api/dependencies.py::require_csrf`：要求 `Origin ∈ runtime.allowed_origins` **且** `X-CSRF-Token` 与 Cookie `csrf_token` 做 `secrets.compare_digest`
- **项目无任何 CORS 中间件** → 跨源直连不可行
- 结论：Vite dev(5173) 不在白名单 → 开发态必 403；且跨源响应无 ACAO 读不到

## 3. 推荐处置（写进"联调前置"卡）

1. **来源做成配置**：`Settings` 字段 + 环境变量（逗号分隔），**严格相等匹配**，**禁 `*` 与 `null` origin**，非法配置启动即失败
2. **前端走 Vite 同源代理**：浏览器视角同源 → **完全不需要 CORS**；但后端仍会看到 dev 源 Origin → 仍须进白名单（不要试图在代理里伪造 Origin）
3. **固化 CSRF 契约**：cookie 名、**非 HttpOnly**、SameSite/Secure（注意 `Secure` 在 `http://localhost` 的浏览器例外）、下发时机（登录/注册/游客 bootstrap 之后，以及刷新页面后如何重新获取）、请求头名、失败语义（403，**不新增错误码**）
4. **中间件顺序要写明**：请求体上限 413、Origin/CSRF 403、路由/DTO 422 的先后（否则"未过 CSRF 是否仍读 body"这种问题会在实现里各写一套）

## 4. 顺带：用户口述的每个 UI 动作，都要映射到后端接口

用户描述前端时用的都是自然语言（「**我的**里可以查看和**更改**一些资料」）。出卡前把每个动作映射到真实接口，**缺失项单独成卡**：

- 「查看资料」→ `GET /auth/me` + `GET /usage/me` ✅ 已有
- 「**更改**资料」→ 后端**完全没有**改邮箱/改密码/改配额接口 → 不能塞进前端卡（前端卡会变成后端改造），要单独出「账户自助」卡
- 「管理员管理用户」→ 若无 `/users` 路由，同样单独成卡（本项目已由卡12c 交付）

映射盘点的产出**一次写进正式需求文档**（本项目：`project/decisions/decision_<卡号>_frontend_flow.md`），前端卡与前置卡都从它取规格。
