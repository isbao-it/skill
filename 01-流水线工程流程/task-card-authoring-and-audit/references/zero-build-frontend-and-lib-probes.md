# 零构建「双击可用」前端 + 第三方库可行性探针

适用：需求写「单文件网页 / 双击 index.html 即用 / 无构建 / 无后端 / 离线」的本地页面项目。
平台探针是**出卡前的取证动作**，不是实现细节——约束与技术栈的冲突在这里花一分钟就能否掉，
拖到卡里就是整卡返工；§6/§7 反过来是**交付前的真跑面**（契约与驱动配方），判据都要能断言、不靠肉眼。

## 1. 「双击可用」= `file://` 协议：先探三条

| 探什么 | 实测结论 | 后果 |
|---|---|---|
| `<script type="module">` | **被拦**（origin 为 null，CORS）→ 模块不执行，页面静默无功能 | 与 ESM 组织方式**互斥**：改用经典 `<script src>` 顺序加载 |
| 经典 `<script src="x.js">` | 正常加载 | 逻辑/界面分文件仍成立 |
| `fetch` / `XHR` 读本地文件 | 被拦 | 文件输入一律走 `<input type="file">` + `FileReader` / `arrayBuffer()` |

**探针配方（两文件一分钟，禁凭记忆断言）**：写 `mod.js`（只有一句 `export const v=1; window.__mod_ok=true;`）
与 `classic.js`（`window.__classic_ok=true;`），两个 html 各引一种，脚本里把 `document.title` 设成
`MODULE_OK` / `MODULE_BLOCKED` 与 `CLASSIC_OK` / `CLASSIC_BLOCKED`，浏览器打开读 title。

## 2. 三合一写法：双击可用 + 逻辑分离 + 可单测

- 逻辑文件（纯函数）用**双导出**：浏览器侧 `window.XxxCore = { ... }`；node 侧
  `if (typeof module !== 'undefined' && module.exports) module.exports = { ... };`
- 界面文件（`app.js`）是**唯一**碰 DOM 的层；测试只 import 逻辑文件（CJS 互操作 vitest 直接吃）。
- 逻辑文件**禁** `document` / `window` / `localStorage` / `Date.now()` / `Math.random()`：
  随机一律由外部传入（种子或 PRNG 实例），文件内容以 `ArrayBuffer` / 字符串作参数。

## 3. 第三方库落盘

- 库必须是**经典脚本 / UMD 构建**：ESM-only 的包在 `file://` 下引不进来。
- 落 `vendor/` 随仓库版本化，**禁 CDN 引用**——CDN 需要联网，断网双击即废，而「断网可用」常是这类项目唯一的验收卖点。
- **记来源与版本**：npm 包与官网版本会长期漂移（SheetJS 官网上有 npm 未发布的更新版本）→
  卡面/文档写明取了哪个版本、从哪取的、多少字节。

## 4. 库可行性四问（出卡前在目标环境实测）

1. **加载**：node `require` 与浏览器经典 script 都能加载吗？
2. **关键 API 的真实返回形状**：空值 / 空单元格 / 缺列用什么表示（`''`、`null`、缺键）——
   夹具与断言按实测值写；解析类 API 多用 `{ header: 1, defval: '' }` 这类开关，实测确认形态。
3. **畸形输入的行为**：喂一个坏文件（改扩展名的纯文本 / 截断的二进制）——**抛错还是静默返回空**？
   实测 SheetJS 对非 zip 文本**不抛错**、返回一张空表（`SheetNames=['Sheet1']`）→
   「非法文件」不能用 `try/catch` 判，必须另立判据（校验 zip 魔数 `PK\x03\x04` 或统一按「解析后名单为空」处理），
   并把取舍结论写进架构/卡面；同理，错误码与用户提示要诚实归因（哪条路径给哪个码）。
4. **环境差异**：同一份构建在 node 与浏览器可能走不同路径，需要显式注入宿主能力
   （SheetJS 标准版在 node 侧必须 `XLSX.set_fs(require('fs'))`，否则 `writeFile` 报 `cannot save file`）。

## 5. 探针执行纪律（一次能省几万字符上下文）

- 探针**写成文件跑**（`node project/probes/<topic>.js`），**不要** `node -e '...'`：
  git-bash 下引号转义极易炸；更要命的是报错时 node 会把**整段被 minify 的 vendor 源码那一行**打进 stderr，
  直接灌满上下文（一个 `| head -12` 就够灌几万字符）。
- 固定跑法：`node probe.js > probe.log 2>&1; echo exit=$?; head -6 probe.log`；
  日志里打印异常用 `e.message.slice(0, 80)`，**禁打印 `e.stack`**。
- 探针脚本 + 日志随项目入库（`project/probes/<topic>.js` / `.log`），结论进派题与卡面事实基线段。
- 探针回答**一个未知量**即可（M3 定位）：结论入库、代码不演变成产品代码。

## 6. 打印 / 剪贴板契约（本地页面的两个「真跑才暴露」面）

- **打印视图用 `@media print` + 一个类名**（如 `body > :not(#print-area) { display: none !important; }`），
  判据写成「打印预览里只剩讲台/标题与当前矩阵，输入区、状态、按钮、页内说明全隐藏」。
  **浏览器自身的页眉页脚不属于 DOM** → 验收只记录打印设置，**禁**宣称 CSS 能关掉它们。
- **矩阵即唯一真相**：复制与打印必须复用**当前那份矩阵**，禁重新排座 —— 打印前再随机会把用户的表换掉。
- **剪贴板要有手动兜底路径**：`navigator.clipboard` 失败时展示只读文本框供手动复制，并**保留已生成状态**；
  只有「生成 Markdown 成功、复制被拒」才拿本次字符串去展示，**禁**拿上一次的旧 Markdown 冒充本次输出。
- **状态机区分「参数错」与「数据错」**：参数错（行列/种子非法）留在就绪态让用户改，数据错（名单/矩阵非法）才清数据。
  两者共用一条迁移，真跑时表现为「改个列数就把名单清了」。

## 7. 真浏览器验收的驱动配方（CDP）

自动测全绿 ≠ 页面能用。以下每条都是**用真浏览器驱动本地页面**的固定动作，判据写成可断言的值，别靠肉眼看截图。

- **上传夹具**：`DOM.setFileInputFiles` 往 `<input type=file>` 塞文件路径（`fill_input` 传不了文件）。
  二进制夹具可在**页内现造**——用已加载的库 API 生成字节 → `new File([buf], 'x.xlsx')`，
  免把 base64 塞进驱动脚本（省上下文，也免编码坑）。
- **驱动脚本的交互陷阱（会伪装成产品缺陷）**：程序化选 `<select>` 必须 `sel.selectedIndex = n`，
  再 `dispatchEvent(new Event('change', {bubbles: true}))`。**设一个不存在的 value 会被浏览器归零**
  （`sel.value = '99'` → `''`），应用于是报「非法选择」——那是**正确行为**，不是缺陷。
  判定「不可复现的异常」前，先把**驱动那一步是否真的生效**打印出来（value/selectedIndex、事件是否派发、状态快照各一次）；
  同理复选框用 `.click()`，不要只改 `.checked`。
- **复制/导出类**：拦截 `navigator.clipboard.writeText` **记录实参、同时调用原函数**（保留真实写入路径），
  判据用「实参 === 独立算出的期望串」判逐字。**禁**用授权后的 `readText()` 回读做逐字比对：
  浏览器/系统会规范化文本（实测回读多出行间空行）→ 假红。`file://` 下剪贴板写入**默认被拒**
  （`NotAllowedError: Write permission denied`）→ 这本身是**降级路径的真跑机会**（应展示只读手动框、不得报「复制成功」）；
  要跑成功路径再用 CDP 授予剪贴板权限。
- **打印**：`Emulation.setEmulatedMedia({media:'print'})` 后读 `getComputedStyle().display`，断言输入区/状态区 `none`、
  打印区 `block`，并断言打印区**子元素只有标题类与矩阵**（无 button/input）。页眉页脚不是 DOM，只能记录设置。
- **离线双击**：`Network.emulateNetworkConditions({offline: true})` + 重载 `file://` 页面 →
  断言仍能走完一次完整流程（这是「离线可用」唯一的真跑判据；静态扫 `fetch(` 只能证明源码里没写）。
- **注入式装配入口的契约**：`document.implementation.createHTMLDocument()` 造**隔离 document**
  （同一页面可再挂一次，互不干扰），传入**记录型端口对象** → 断言 ① 返回值形状
  ② 状态字段是**只读 getter**（`Object.getOwnPropertyDescriptor` 无 setter）③ 每个端口的调用次数与实参
  ④ 状态机各态迁移。**记录器必须真调用原实现**，否则验的是影子路径。
- **竞态用「可控 Promise」造**：端口返回自己 resolve 的 Promise；连续触发两次，**后一次先 resolve、旧的后 resolve**
  → 断言旧 Promise 迟到后界面快照**逐字不变**（且没冒出错误提示）。这是「旧结果不覆盖新结果」唯一能真跑的判据。
- **性能**：页内 `performance.now()` 包住真实链路（解析 + 清洗 + 排座），把门禁值与实测值一起写进验收记录。
