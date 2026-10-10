# 认证/安全加固类卡的取证据与新增表现码（2026-09-19 卡12e 实测）

适用：用户问"密码/账号限制那些做了没"这类**安全加固**需求，或要出一张 `auth hardening` 卡时。
本文补充 `security-contract-and-negative-test-verification.md`（负向测试与契约）与
`error-surface-domain-vs-presentation-codes.md`（领域码 vs API 层表现码）。

## 1. 先取证，再答"做了没"（照这张清单 grep，5 分钟内出结论）

```bash
grep -n "password" app/api/schemas.py                                   # 是否裸 str（无 min/max_length）
grep -rn "password" app/services/auth.py | grep -iE "len|min|max|complex|policy"   # 服务层有无策略
grep -rniE "rate_limit|throttl|attempt|lockout|failed_login|too_many" app/ --include=*.py
grep -rn "middleware" app/ --include=*.py                               # 有无中间件（限长/限流）
grep -nE "class User" -A 22 app/db/models.py                            # users 是否已有 role/status/token_version
grep -rn "create_admin|seed_admin" scripts/ tools/ 2>/dev/null          # 有无管理员引导入口
```
实测结论（本项目）：**哈希强度做了、登录侧防枚举做了、JWT/Cookie/CSRF 做了**；**密码长度/复杂度、登录限速锁定、
请求体限长、注册侧枚举防护全没做**。答用户时**逐项给"有/没有 + 文件:行证据"**，不要笼统说"安全性还行"。

⚠️ 最容易误导的一条：某张卡在**脚本入口**加的密码护栏（如"12～1024 code point"）**不覆盖 HTTP 注册/登录**，
汇报时必须点明，否则会让人以为密码策略已做。

## 2. 新增两个 API 层表现码（需用户拍板；已批准的写法见 `error-surface-domain-vs-presentation-codes.md`）

| 场景 | 状态 | 码 | 约定 |
|---|---|---|---|
| 限速触发（登录/注册） | **429** | `too_many_requests` | **必须**带 `Retry-After`（正整数秒 = 剩余锁定秒数向上取整）；413 **不带** |
| 请求体超上限 | **413** | `payload_too_large` | 最外层纯 ASGI 中间件：先验 `Content-Length` 再累计分块，**首次超限即返回且不进路由**（不解析 JSON、不调业务、不触发 Argon2id）|

**硬规矩**：**配额 ≠ 限速** —— `quota_exceeded`(429) 只表示配额，限速用 `too_many_requests`(429)；
两者不得互相复用，配额路径也不得写入限速器计数（"归因诚实"原则在 429 上的落地）。

## 3. 限速设计的边界（写进卡面，否则必被抓漏）

- **存储选型要显式裁决**：进程内内存（零迁移，但**重启清零、多进程不共享**）vs DB 表（**需迁移 `0004`，必须用户点头**）。
  单机 MVP 用内存 + 把边界写进交付；公网多 worker 前升级共享存储 + 可信代理。
- **桶必须有界**：按账号/邮箱建键时，攻击者可用海量随机邮箱撑爆内存 → 写死"**最多 N 个活跃键，容量满对新键直接 429**"（实测 N=10,000）。
- **成功只清对应桶**（账户桶清、IP 桶不清）；**不存在邮箱与错密同计**（否则限速本身成了枚举旁路）。
- **`X-Forwarded-For` 不可信**：MVP 用**直连 IP**、显式声明不解析该头；日志里 IP 只允许掩码/哈希。
- **测试时钟必须可注入**（固定单调时钟 fake），**禁真实 sleep 等 15 分钟**。
- **日志脱敏**：限速路径日志**禁明文邮箱**（可用与桶键相同的 HMAC 摘要或干脆不记），异常链/响应体 0 命中。

## 4. 密码策略的取值取向（可复用给用户看的谈判点）

- NIST SP 800-63B（-4）取向：**长度优先、不强制大小写/数字/符号**，按 **Unicode code point** 计数
  （单因素建议 ≥15）。**上限必须设**（Argon2id 输入无上限 = CPU/内存 DoS 面），且拦截必须发生在**哈希之前**。
- **登录端只限上限、不设下限**：否则没有找回密码通道时会把历史短密码用户锁死。
- **一处策略、多处一致**：脚本护栏、HTTP 注册、未来改密必须共用同一常量。实测踩坑：另一张卡已把脚本护栏写成
  `12～1024`，后出的加固卡定为 `15～128` → 卡面必须写"以后者为准并同步改脚本护栏常量 + 白名单加脚本文件"，
  否则三处三个数。
