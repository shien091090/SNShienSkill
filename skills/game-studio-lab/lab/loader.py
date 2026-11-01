"""網站版遊戲的載入進度條: 把 index.html 裡依序載入的本地 <script src> 換成一段載入程式。

載入程式先用 fetch 逐段下載(依位元組算百分比), 全部到齊後照原順序執行, 畫面上顯示進度條與百分比,
並用 postMessage 通知網站(`pvd:progress` 帶 0~1 的 progress、載完送 `pvd:loaded`)。
file:// 開啟或瀏覽器不支援 fetch 串流時, 退回逐個插入 <script src>(依檔案數算百分比)。

檔案大小在產生時寫死(未壓縮位元組, 和瀏覽器解壓後讀到的位元組數一致); 改了遊戲檔要重跑 add_loader 更新。
"""
import json
import re
from pathlib import Path

MARK = "pvd-loader"
SCRIPT_TAG_RE = re.compile(r"""[ \t]*<script\s+src=["'](?!https?:|//)([^"']+)["']\s*>\s*</script>[ \t]*\r?\n?""", re.I)
BLOCK_RE = re.compile(r"[ \t]*<!-- pvd-loader -->[\s\S]*?<!-- /pvd-loader -->[ \t]*\r?\n?")
FILES_RE = re.compile(r"var FILES = (\[.*?\]);")

TEMPLATE = """<!-- pvd-loader -->
<div id="pvd-load" style="position:fixed;inset:0;z-index:9;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;background:__BG__;color:#e8e8ee;font:600 15px/1.4 system-ui,'Microsoft JhengHei',sans-serif">
<div style="width:min(320px,60vw);height:10px;border-radius:5px;background:#2a2a33;overflow:hidden"><div id="pvd-load-bar" style="width:0;height:100%;border-radius:5px;background:#e8e8ee;transition:width .15s"></div></div>
<div id="pvd-load-text">載入中 0%</div>
</div>
<script>
// 載入進度條(由 game-studio-lab 發布流程產生, 改了遊戲檔要重新產生): FILES = [路徑, 未壓縮位元組]
(function () {
  var FILES = __FILES__;
  var total = 0, got = [], last = -1, i;
  for (i = 0; i < FILES.length; i++) { total += FILES[i][1]; got.push(0); }
  function post(msg) { try { if (window.parent && window.parent !== window) window.parent.postMessage(msg, location.origin); } catch (e) { /* file:// 開啟時略過 */ } }
  function show() {
    var n = 0; for (var k = 0; k < got.length; k++) n += got[k];
    var p = total ? Math.min(1, n / total) : 1, pct = Math.floor(p * 100);
    if (pct === last) return;
    last = pct;
    document.getElementById('pvd-load-bar').style.width = pct + '%';
    document.getElementById('pvd-load-text').textContent = '載入中 ' + pct + '%';
    post({ type: 'pvd:progress', progress: p });
  }
  function done() {
    got = FILES.map(function (f) { return f[1]; }); show();
    var el = document.getElementById('pvd-load'); if (el) el.parentNode.removeChild(el);
    post({ type: 'pvd:loaded' });
  }
  // 退回做法: 逐個插入 <script src>, 一個載完才載下一個(保持執行順序)
  function byTags(from) {
    if (from >= FILES.length) return done();
    var s = document.createElement('script');
    s.src = FILES[from][0];
    s.onload = s.onerror = function () { got[from] = FILES[from][1]; show(); byTags(from + 1); };
    document.body.appendChild(s);
  }
  function fetchOne(f, k) {
    return fetch(f[0]).then(function (r) {
      if (!r.ok) throw new Error(f[0] + ' ' + r.status);
      if (!r.body || !r.body.getReader) return r.text();
      var rd = r.body.getReader(), parts = [], n = 0;
      function pump() {
        return rd.read().then(function (x) {
          if (x.done) return new Blob(parts).text();
          parts.push(x.value); n += x.value.length; got[k] = Math.min(n, f[1]); show();
          return pump();
        });
      }
      return pump();
    });
  }
  show();
  if (location.protocol === 'file:' || !window.fetch || !window.Blob || !Blob.prototype.text) return byTags(0);
  Promise.all(FILES.map(fetchOne)).then(function (codes) {
    for (var k = 0; k < codes.length; k++) {
      var s = document.createElement('script');
      s.text = codes[k] + '\\n//# sourceURL=' + FILES[k][0];
      document.body.appendChild(s);   // 插入即執行, 照 FILES 順序
    }
    done();
  }, function () { got = FILES.map(function () { return 0; }); last = -1; byTags(0); });
})();
</script>
<!-- /pvd-loader -->
"""


def page_background(html: str) -> str:
    """遊戲頁面的底色(index.html 樣式裡 body 的 background), 讓載入畫面和遊戲接得上; 找不到用深灰。"""
    for m in re.finditer(r"(?:^|[},>\s])(?:html\s*,\s*)?body\s*(?:,\s*html\s*)?\{([^}]*)\}", html):
        bg = re.search(r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|[a-zA-Z]+)\s*[;}]?", m.group(1) + ";")
        if bg:
            return bg.group(1)
    return "#111"


def loader_files(html: str) -> list[str]:
    """index.html 依序載入的本地程式路徑(已加過載入程式的, 從載入程式讀回)。"""
    block = BLOCK_RE.search(html)
    if block:
        m = FILES_RE.search(block.group(0))
        return [f[0] for f in json.loads(m.group(1))] if m else []
    return SCRIPT_TAG_RE.findall(html)


def add_loader(game: Path) -> list[str]:
    """在 game/index.html 加上(或更新)載入進度條, 回傳納入進度的程式路徑; 沒有本地程式就不改。"""
    index = Path(game) / "index.html"
    html = index.read_text(encoding="utf-8")
    files = loader_files(html)
    if not files:
        return []
    missing = [f for f in files if not (Path(game) / f).is_file()]
    if missing:
        raise FileNotFoundError(f"index.html 載入的程式不存在: {', '.join(missing)}")
    rest = html[SCRIPT_TAG_RE.search(html).start():] if not BLOCK_RE.search(html) else ""
    if re.search(r"<script(?![^>]*\ssrc\s*=)[^>]*>\s*\S", rest):
        raise ValueError("index.html 在本地程式之後還有內嵌程式, 改成載入程式後執行順序會變, 請手動處理")
    sizes = [[f, (Path(game) / f).stat().st_size] for f in files]
    block = TEMPLATE.replace("__FILES__", json.dumps(sizes, ensure_ascii=False)).replace("__BG__", page_background(html))
    if BLOCK_RE.search(html):
        html = BLOCK_RE.sub(lambda m: block, html, count=1)
    else:
        first = SCRIPT_TAG_RE.search(html)
        html = html[:first.start()] + block + SCRIPT_TAG_RE.sub("", html[first.start():])
    index.write_text(html, encoding="utf-8", newline="")
    return files
