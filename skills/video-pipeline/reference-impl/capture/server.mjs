// node server.mjs — 開錄按鍵版遊戲: 瀏覽器開 http://localhost:8790 直接玩, 操作紀錄自動存到 takes/
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PORT = 8790;
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav', '.woff2': 'font/woff2' };
const saved = new Map();

http.createServer((q, r) => {
  const url = decodeURIComponent(q.url.split('?')[0]);
  if (q.method === 'POST' && url === '/log') {
    let body = '';
    q.on('data', (d) => { body += d; });
    q.on('end', () => {
      try {
        const log = JSON.parse(body);
        if (!/^[0-9-]{8,20}$/.test(log.take)) throw new Error('bad take name');
        fs.writeFileSync(path.join(HERE, 'takes', log.take + '.json'), JSON.stringify(log));
        if (saved.get(log.take) !== log.steps) {
          const t = Math.floor(log.steps / 60);
          if (!saved.has(log.take)) console.log('開始錄製 ' + log.take);
          saved.set(log.take, log.steps);
          process.stdout.write(`\r${log.take}  ${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}  按鍵 ${log.ev.length} 次   `);
        }
        r.writeHead(204); r.end();
      } catch (e) { r.writeHead(400); r.end(); }
    });
    return;
  }
  if (url === '/') { r.writeHead(302, { Location: '/game/index.html?w=1280' }); return r.end(); }
  const f = path.join(HERE, url);
  if (!f.startsWith(HERE) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
  fs.createReadStream(f).pipe(r);
}).listen(PORT, () => console.log(`錄按鍵版: http://localhost:${PORT}  (紀錄存在 takes/, Ctrl+C 結束)`));
