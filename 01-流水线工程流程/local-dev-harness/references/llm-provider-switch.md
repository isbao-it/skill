# 切换 / 接入真实 LLM Provider（OpenAI 兼容端点）

适用：项目已有「厂商中立」的 OpenAI 兼容适配器（base_url + 密钥来源 + 模型槽位都在配置里），
现在要换厂商、加一把新密钥、或排查「配好了却调用失败」。配套脚本：`scripts/probe_openai_compatible.py`。

## 1. 切换清单（少改一项就 401 或算错账）

| 配置项 | 说明 |
| --- | --- |
| base_url | 厂商的 OpenAI 兼容地址，含地域；远端只走 HTTPS |
| 密钥来源 + 密钥 | 中性的 `LLM_API_KEY`(source=generic) 或厂商专有变量(source=openai/deepseek/glm/…) |
| 每个模型槽位 | 常有 batch / creative 两槽，模型名是配置值不是代码常量，**逐字**抄厂商模型 id |
| 结构化输出档 | prompt_json（兼容面最大）或 json_schema（端点侧约束输出） |
| 费率 ×2 + 费率来源 | 来源字符串要写清**币种与档位** |
| 超时 | 思考模式默认开启的模型要给足，30s 常不够 |

切回旧厂商时，把旧值以注释块留在同一处，并在文件头注释里写清切换步骤（改哪几项）。

## 2. 重复键是「加了一把密钥」最常见的翻车点

用户在 `.env` 里「加了一个新厂商的密钥」时，往往是把值贴进某个已有变量名下（或新增同名行）。
载荷（dotenv / pydantic-settings）取**最后一次出现**：旧厂商的密钥被新密钥顶掉，而 base_url 还指向旧厂商
→ 每次真实调用都 401，且从错误信息看不出是密钥串了厂商。

排查：只列**键名与值长度**，不打印值（工具输出会脱敏，但常漏出前 4 个字符，别依赖它）。

```
python probe_openai_compatible.py --env-file .env --list
```

修法：把值搬到中性槽位（`LLM_API_KEY` + `source=generic`），**不要**覆盖厂商专有变量，也不要删旧值。

## 3. 先验密钥与地域配对，再改配置

同一厂商的密钥按地域隔离（百炼北京 / 新加坡 / 弗吉尼亚各有各的 key），拿错地域的 key 打错域名只会得到 401。
对候选举措各打一次 `GET <base>/models`：200 = 配对成功，并能从返回清单里**逐字**取到模型 id。

百炼（DashScope）OpenAI 兼容地址：

| 地域 | base_url |
| --- | --- |
| 北京 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 新加坡（国际） | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| 弗吉尼亚 | `https://dashscope-us.aliyuncs.com/compatible-mode/v1` |

百炼控制台还推 `{WorkspaceId}.<region>.maas.aliyuncs.com` 专属域名；旧共享域名仍可用。

## 4. 思维链默认开启 × 严格 JSON 契约（最容易漏的兼容性坑）

qwen3.5 / 3.6 / 3.7 系列**默认开启思考模式**（部分厂商用 `enable_thinking` 顶层参数控制，
百炼兼容端点接受该参数）。实测同一请求连发 10 次：

| 档位 | 干净 JSON | Markdown 围栏 | 中位耗时 | 中位输出 tokens |
| --- | --- | --- | --- | --- |
| prompt_json，思考默认开 | 5/10 | 5/10 | ~27s | ~1738 |
| prompt_json，`enable_thinking=false` | 10/10 | 0/10 | ~2.4s | ~176 |
| json_schema，思考开 | 5/5 | 0/5 | ~14.5s | — |
| json_schema，思考关 | 5/5 | 0/5 | ~2.4s | — |

严格 `json.loads`（不剥围栏）的适配器在第一种档位下**一半概率失败**，且失败重试也走同一条路。

- **纯配置的修法**：结构化输出档改 `json_schema`，围栏归零（切回不支持 `response_format` 的厂商要改回 prompt_json）。
- **更彻底**：请求带 `enable_thinking=false`；适配器没有传额外参数的位置时属于**代码改动 → 开卡**，
  不要为了跑通顺手改冻结区的常量或函数签名。

## 5. 费率与档位悬崖

- 费率字段常是无货币的浮点：把**币种 + 档位**写进费率来源字符串，否则换厂商时 USD 值写进 CNY 槽位，账目口径静默变了。
- 按输入长度**整单重算**的计价（百炼 32K / 256K 两档）不是「超出部分加价」：输入跨过 32K，整单涨 3 倍；跨 256K 涨 6 倍。
  在注释里写明阈值与后果，并提醒用户量一下真实 prompt 大小。
- 缓存命中单价能差一两个数量级（同厂商内也不同），提示词重复度高的负载要把这一列算进去。

## 6. 验证顺序（别用 curl 代替）

1. 抽样实测（脚本 `--sample 10`）：干净率、中位耗时、输出 tokens —— 拿数字下结论。
2. 走**项目自己的适配器**跑真实调用：批处理链路 + 创意链路各一条，断言结构化输出与 usage 都被解析。
3. 跑定向测试（适配器 + Provider 相关 API 测试）确认无回归；再声明哪些项仍未验证（质量、边界 prompt）。

诊断时复用适配器自己的请求体构造函数（如 `_wire_messages` / `_body`）拼出与生产**完全一致**的请求，
再自己发出去打印 `finish_reason`、content 开头、usage —— 这样拿到的才是生产真实形态，
而不是你手拼的、可能漏了 system 提示与 schema 注入的简化版。

## 7. 不许回显密钥

任何输出、摘要、报告里只出现「已设置 / 长度 / 变量名」。改配置前备份成 `.env.bak-<原因>`，
并确认它落在 gitignore 覆盖范围内（常见 `.env.*`）。改完必须重启后端才会生效。
