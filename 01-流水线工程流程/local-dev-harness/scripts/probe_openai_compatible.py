"""通用探针：检查配置文件的键、探测 OpenAI 兼容端点与密钥、抽样测结构化输出可靠性。

为什么存在：换厂商/加密钥时先证伪三件事——键名有没有重名、密钥属于哪个地域、模型在严格 JSON
契约下稳不稳。这三件各花一分钟，能省掉一轮“配好了但调用一直失败”。

只读模式（不发请求）：--list / --probe-models
会花钱的模式：--sample N（N 次真实 chat completion，短提示）

用法：
  python probe_openai_compatible.py --env-file .env --list
  python probe_openai_compatible.py --env-file .env --key-var LLM_API_KEY \
      --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 --probe-models
  python probe_openai_compatible.py --env-file .env --key-var LLM_API_KEY \
      --base-url <base> --model <model-id> --sample 10 [--json-schema] [--no-thinking]

绝不打印密钥；只输出状态码、长度、计数与耗时。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"term": {"type": "string"}, "weight": {"type": "number"}},
                "required": ["term", "weight"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}
PROMPT = (
    "把下面这句话里的关键词抽出来，只输出一个JSON对象，不要解释、不要Markdown代码块：\n"
    "「三句话让他主动道歉。」"
)
CONTRACT = "\n必须严格满足此JSON Schema：" + json.dumps(JSON_SCHEMA, ensure_ascii=False)


def parse_env(path: str) -> list[tuple[int, str, str]]:
    """返回 [(行号, 键名, 值)]；保持出现顺序，便于发现重复键。"""
    rows: list[tuple[int, str, str]] = []
    with open(path, encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            rows.append((lineno, name.strip(), value.strip()))
    return rows


def opener(use_env_proxy: bool) -> urllib.request.OpenerDirector:
    """默认忽略环境代理（多数应用用 trust_env=False 直连），可用 --use-env-proxy 打开。"""
    handlers = [] if use_env_proxy else [urllib.request.ProxyHandler({})]
    return urllib.request.build_opener(*handlers)


def post_json(op: urllib.request.OpenerDirector, url: str, key: str, body: dict, timeout: float = 120.0):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
    with op.open(request, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8", "replace"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="OpenAI 兼容 Provider 探针（不打印密钥）")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--key-var", default="LLM_API_KEY", help="从哪个变量取密钥（默认 LLM_API_KEY）")
    parser.add_argument("--base-url", default="", help="OpenAI 兼容 base_url（不带 /chat/completions）")
    parser.add_argument("--model", default="")
    parser.add_argument("--list", action="store_true", help="只列出键名/长度/重复键")
    parser.add_argument("--probe-models", action="store_true", help="GET <base>/models 验密钥与地域配对")
    parser.add_argument("--contains", default="", help="在模型清单里过滤子串")
    parser.add_argument("--sample", type=int, default=0, help="抽样请求次数（会真实计费）")
    parser.add_argument("--json-schema", action="store_true", help="请求带 response_format=json_schema")
    parser.add_argument("--no-thinking", action="store_true", help="请求带 enable_thinking=false")
    parser.add_argument("--use-env-proxy", action="store_true", help="使用环境代理（默认直连）")
    args = parser.parse_args(argv)

    rows = parse_env(args.env_file)
    by_name: dict[str, list[tuple[int, str]]] = {}
    for lineno, name, value in rows:
        by_name.setdefault(name, []).append((lineno, value))

    if args.list or not (args.probe_models or args.sample):
        print(f"{args.env_file}: {len(rows)} 行赋值，{len(by_name)} 个键")
        for name, entries in by_name.items():
            flag = ""
            if len(entries) > 1:
                flag = f"  <== 重复 {len(entries)} 次，实际生效的是第 {entries[-1][0]} 行"
            print(f"  {name}: len={len(entries[-1][1])} empty={not entries[-1][1]}{flag}")
        return 0

    key = by_name.get(args.key_var, [(0, "")])[-1][1]
    if not key:
        print(f"警告：{args.key_var} 为空，将以无密钥方式请求")
    base = args.base_url.rstrip("/")
    if not base:
        print("错误：--probe-models/--sample 需要 --base-url")
        return 2
    op = opener(args.use_env_proxy)

    if args.probe_models:
        try:
            with op.open(urllib.request.Request(f"{base}/models", headers={"Authorization": f"Bearer {key}"})) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
                ids = [item.get("id", "") for item in data.get("data", [])]
                hits = sorted(i for i in ids if args.contains in i) if args.contains else sorted(ids)
                print(f"{base}/models -> HTTP {resp.status}，模型 {len(ids)} 个；过滤结果 {hits[:40]}")
        except urllib.error.HTTPError as exc:
            print(f"{base}/models -> HTTP {exc.code}（401/403 多为密钥与地域不配对）: {exc.read()[:160]!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"{base}/models -> 失败: {type(exc).__name__}: {exc}")

    if args.sample:
        clean = fenced = other = 0
        latencies: list[float] = []
        tokens: list[float] = []
        reasons: set[str] = set()
        for _ in range(args.sample):
            body: dict = {
                "model": args.model,
                "messages": [{"role": "user", "content": PROMPT + CONTRACT}],
                "temperature": 0.0,
                "max_tokens": 2048,
            }
            if args.no_thinking:
                body["enable_thinking"] = False
            if args.json_schema:
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "probe", "schema": JSON_SCHEMA, "strict": True},
                }
            started = time.perf_counter()
            try:
                status, data = post_json(op, f"{base}/chat/completions", key, body)
                latencies.append((time.perf_counter() - started) * 1000)
                if status != 200:
                    other += 1
                    continue
                choice = data["choices"][0]
                reasons.add(str(choice.get("finish_reason")))
                content = choice["message"].get("content") or ""
                usage = data.get("usage") or {}
                if isinstance(usage.get("completion_tokens"), int):
                    tokens.append(usage["completion_tokens"])
                try:
                    json.loads(content)
                    clean += 1
                except Exception:  # noqa: BLE001
                    if "```" in content:
                        fenced += 1
                    else:
                        other += 1
            except urllib.error.HTTPError as exc:
                other += 1
                print(f"HTTP {exc.code}: {exc.read()[:160]!r}")
            except Exception as exc:  # noqa: BLE001
                other += 1
                print(f"请求失败: {type(exc).__name__}: {exc}")
        n = args.sample
        print(
            f"抽样 {n} 次（model={args.model} json_schema={args.json_schema} thinking_off={args.no_thinking}）: "
            f"干净JSON {clean}/{n} | Markdown围栏 {fenced}/{n} | 其他失败 {other}/{n}"
        )
        if latencies:
            print(f"中位耗时 {statistics.median(latencies):.0f}ms | finish_reason 集合 {sorted(reasons)}")
        if tokens:
            print(f"中位输出 tokens {statistics.median(tokens):.0f}")
        print("判读：围栏命中即说明严格 json.loads 的适配器会失败 —— 换 json_schema 档或关思考模式。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
