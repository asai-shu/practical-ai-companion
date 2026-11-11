"""quiz_template.html に単語データとイディオムを埋め込んで meidai-nine.html を作る。

使い方: python3 app/build.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
words = json.load(open(ROOT / "data" / "words_nagoya.json", encoding="utf-8"))
idioms = json.load(open(ROOT / "data" / "idioms_nagoya.json", encoding="utf-8"))
page = (ROOT / "app" / "quiz_template.html").read_text(encoding="utf-8")
kyotsu = json.load(open(ROOT / "data" / "words_kyotsu.json", encoding="utf-8"))
affixes = json.load(open(ROOT / "data" / "affixes_nagoya.json", encoding="utf-8"))
page = (page.replace("__DATA__", json.dumps(words, ensure_ascii=False))
        .replace("__IDIOMS__", json.dumps(idioms, ensure_ascii=False))
        .replace("__KYOTSU__", json.dumps(kyotsu, ensure_ascii=False))
        .replace("__AFFIXES__", json.dumps(affixes, ensure_ascii=False)))
(ROOT / "app" / "meidai-nine.html").write_text(page, encoding="utf-8")
print(len(words), "words,", len(idioms), "idioms")

# ---- Webサイトとして公開するための一式（site/ フォルダ）を作る ----
# quiz_template.html は Artifact 用で <html> や <head> がないので、ここで補う。
SITE = ROOT / "site"
SITE.mkdir(exist_ok=True)
head, body = page.split("</style>", 1)
DESC = "大学入試に実際に出た英単語を、9つの選択肢から意味をすべて選ぶクイズで覚える単語アプリ。共通テスト版は無料。"
html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{DESC}">
<meta name="theme-color" content="#d2554a">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icon.svg">
<style>[hidden]{{display:none!important}}body{{margin:0}}img{{max-width:100%}}</style>
{head}</style>
</head>
<body>
{body}
<script>
// オフラインでも開けるようにする（対応していないブラウザでは何もしない）
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {{}});
</script>
</body>
</html>
"""
(SITE / "index.html").write_text(html, encoding="utf-8")
(SITE / "manifest.webmanifest").write_text(json.dumps({
    "name": "入試 英単語 ナイン", "short_name": "英単語ナイン", "description": DESC, "lang": "ja",
    "start_url": ".", "display": "standalone", "background_color": "#fbf9f8", "theme_color": "#d2554a",
    "icons": [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
}, ensure_ascii=False, indent=1), encoding="utf-8")
# アイコン：マークシートの9つの丸（2つ塗りつぶし）
cells = "".join(
    f'<ellipse cx="{22 + 28 * c}" cy="{22 + 28 * r}" rx="8" ry="11" fill="{"#d2554a" if (r, c) in ((1, 1), (2, 0)) else "none"}" stroke="#d2554a" stroke-width="4"/>'
    for r in range(3) for c in range(3))
(SITE / "icon.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="18" fill="#ffffff"/>{cells}</svg>', encoding="utf-8")
# サービスワーカー：ページを更新するたびにキャッシュの名前を変える
import hashlib
ver = hashlib.sha1(html.encode("utf-8")).hexdigest()[:10]
(SITE / "sw.js").write_text(f"""const CACHE = "nine-{ver}";
const FILES = ["./", "index.html", "manifest.webmanifest", "icon.svg"];
self.addEventListener("install", e => {{ e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES))); self.skipWaiting(); }});
self.addEventListener("activate", e => {{ e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); }});
// 新しい版があればそれを使い、つながらないときだけ保存してある版を使う
self.addEventListener("fetch", e => {{
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => {{ const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; }}).catch(() => caches.match(e.request, {{ignoreSearch: true}})));
}});
""", encoding="utf-8")
print("site/ を作成:", ", ".join(sorted(p.name for p in SITE.iterdir())))
