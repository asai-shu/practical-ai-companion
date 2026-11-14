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
roots = json.load(open(ROOT / "data" / "roots.json", encoding="utf-8"))
extra_lv = json.load(open(ROOT / "data" / "extra_levels.json", encoding="utf-8"))   # tools/levels/build_extra_levels.py で作る
# 出やすさ（likely）：何年にわたって出たか ＋ 英語全体での使われやすさ（wordfreq）×0.6。
# 過去問の4年分で残りの1年を当てる試し（tools/vocab-analysis の年ごとの回数を使用）で、
# 出た回数の合計（的中率38.5%）より当たりやすかった並べ方（43.1%）。過去問の年数が増えたら決め方を見直す。
from wordfreq import zipf_frequency
for _w in words + kyotsu:
    _years = _w.get("exam_years", 0) if _w.get("source", "exam") in ("exam", "kyotsu") else 0
    _w["likely"] = round(_years + 0.6 * zipf_frequency(_w["word"], "en"), 3)
# ほかの意味（演習には出さず、単語一覧・詳しいページで見せる）。data/extra_meanings/*.txt に「単語|品詞|意味;意味」で書く
extra_m = {}
_pos = {}
for _w in words + kyotsu:
    _pos.setdefault(_w["word"], []).append(_w["pos"])
for _f in sorted((ROOT / "data" / "extra_meanings").glob("*.txt")):
    for _l in _f.read_text(encoding="utf-8").splitlines():
        if not _l.strip():
            continue
        _w, _p, _ms = _l.split("|")
        _ms = [m for m in _ms.split(";") if m]
        if _p in _pos.get(_w, []):
            extra_m.setdefault(_w + "|" + _p, []).extend(_ms)
        else:   # 品詞が違う意味は、その単語の欄に品詞を添えて出す
            for _q in dict.fromkeys(_pos.get(_w, [])):
                extra_m.setdefault(_w + "|" + _q, []).extend(m if "(" + _p in m else m + "(" + _p + ")" for m in _ms)
near = json.load(open(ROOT / "data" / "near_words.json", encoding="utf-8"))          # tools/synonyms/build_near.py で作る
near_ja = json.load(open(ROOT / "data" / "near_meanings.json", encoding="utf-8"))
# データは空白なしで詰めて書く。意味の「出ていない（false）」「回数なし（null）」は書かない（アプリでは無いのと同じ扱い）
def _slim(ws):
    for _w in ws:
        _w["meanings"] = [{k: v for k, v in m.items() if v not in (False, None)} for m in _w["meanings"]]
    return ws
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
near = {k: " ".join(v) for k, v in near.items()}   # 近い単語は「単語 単語 …」の文字列にする
page = (page.replace("__DATA__", J(_slim(words)))
        .replace("__IDIOMS__", J(idioms))
        .replace("__KYOTSU__", J(_slim(kyotsu)))
        .replace("__AFFIXES__", J(affixes))
        .replace("__ROOTS__", J(roots))
        .replace("__EXTRALV__", J(extra_lv))
        .replace("__EXTRAMEAN__", J(extra_m))
        .replace("__NEARJA__", J(near_ja))
        .replace("__NEAR__", J(near)))
(ROOT / "app" / "meidai-nine.html").write_text(page, encoding="utf-8")
print(len(words), "words,", len(idioms), "idioms")

# ---- Webサイトとして公開するための一式（site/ フォルダ）を作る ----
# quiz_template.html は Artifact 用で <html> や <head> がないので、ここで補う。
SITE = ROOT / "site"
SITE.mkdir(exist_ok=True)
head, body = page.split("</style>", 1)
DESC = "大学入試に実際に出た英単語を、9つの選択肢から意味をすべて選ぶ演習で覚える単語アプリ。共通テスト版は無料。"
SW_REG = """
// オフラインでも開けるようにする（対応していないブラウザでは何もしない）
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
"""
# ---- セキュリティ：このページで動いてよいものを決める（Content-Security-Policy） ----
# スクリプトは、このページに書いてあるもの（下のハッシュで指定）だけ。外への通信・埋め込み・フォーム送信はしない。
# 文字の形（フォント）だけは Google Fonts から読む。
import base64, hashlib, re as _re
_scripts = _re.findall(r"<script>(.*?)</script>", body, _re.S) + [SW_REG]
_hashes = " ".join("'sha256-" + base64.b64encode(hashlib.sha256(x.encode("utf-8")).digest()).decode() + "'" for x in _scripts)
CSP = ("default-src 'self'; script-src " + _hashes + "; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; manifest-src 'self'; worker-src 'self'; "
       "object-src 'none'; base-uri 'none'; form-action 'none'")
html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{DESC}">
<meta name="theme-color" content="#d2554a">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="no-referrer">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icon.svg">
<style>[hidden]{{display:none!important}}body{{margin:0}}img{{max-width:100%}}</style>
{head}</style>
</head>
<body>
{body}
<script>{SW_REG}</script>
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
  // 正しく取れた応答だけを保存する（エラーのページを保存して、オフラインのときに出してしまわないように）
  e.respondWith(fetch(e.request).then(r => {{ if (r.ok && r.type === "basic") {{ const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }} return r; }}).catch(() => caches.match(e.request, {{ignoreSearch: true}})));
}});
""", encoding="utf-8")
# 公開先（Cloudflare Pages など）で付けてもらうヘッダー。meta では効かない「ほかのサイトの枠に埋め込ませない」などもここで指定する
(SITE / "_headers").write_text("/*\n"
    "  Content-Security-Policy: " + CSP + "; frame-ancestors 'none'\n"
    "  X-Content-Type-Options: nosniff\n"
    "  Referrer-Policy: no-referrer\n"
    "  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()\n"
    "  X-Frame-Options: DENY\n", encoding="utf-8")
print("site/ を作成:", ", ".join(sorted(p.name for p in SITE.iterdir())))
