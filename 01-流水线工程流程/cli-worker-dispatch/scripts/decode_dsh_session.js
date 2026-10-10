// 解 DSH（DeepSeek Harness）会话日志：文件是「多帧拼接」的 zstd（每批事件一帧）。
// 为什么需要：整文件 zstdDecompressSync 只解第一帧（一次会话几十上百帧，会误以为日志只有几百字节）。
// 做法：按 zstd 魔数 28 B5 2F FD 切帧，逐帧解压再拼；解不出的候选帧跳过（压缩数据里可能有巧合魔数）。
// 用法：node decode_dsh_session.js <session.jsonl.zstd> [输出.txt]
const fs = require('fs');
const zlib = require('zlib');

const src = process.argv[2];
const dst = process.argv[3] || 'decoded.txt';
if (!src) {
  console.error('用法: node decode_dsh_session.js <session.jsonl.zstd> [输出.txt]');
  process.exit(2);
}
const data = fs.readFileSync(src);
const MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);

const offs = [];
for (let i = 0; ; ) {
  const j = data.indexOf(MAGIC, i);
  if (j < 0) break;
  offs.push(j);
  i = j + 1;
}
offs.push(data.length);

const parts = [];
let ok = 0;
let skipped = 0;
for (let k = 0; k < offs.length - 1; k++) {
  const slice = data.subarray(offs[k], offs[k + 1]);
  try {
    parts.push(zlib.zstdDecompressSync(slice).toString('utf8'));
    ok++;
  } catch (e) {
    skipped++;
  }
}
const txt = parts.join('');
fs.writeFileSync(dst, txt);
console.log(`[decode] 候选帧=${offs.length - 1} 成功=${ok} 跳过=${skipped} 文本字节=${txt.length} → ${dst}`);
