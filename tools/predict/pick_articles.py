"""入試に出そうな英文記事を集めて、アプリに入っていない単語を洗い出す。

使い方: python3 pick_articles.py 出力フォルダ
  出力フォルダに、記事の本文（著作物なのでリポジトリには入れない）、選んだ記事の一覧、新しい単語のリストを書き出す。
必要なもの: pip install trafilatura spacy wordfreq && python3 -m spacy download en_core_web_sm
"""
import csv
import html
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import spacy
import trafilatura
from wordfreq import zipf_frequency

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
POS_JA = {"NOUN": "名詞", "VERB": "動詞", "ADJ": "形容詞", "ADV": "副詞"}
LEVEL_JA = {1: "基礎", 2: "標準", 3: "難関", 4: "最難関"}


def get(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "30", "-A", "Mozilla/5.0", url], capture_output=True)
    return r.stdout.decode("utf-8", "ignore")


def read_feed(name, url):
    """RSS / Atom から (媒体, タイトル, URL, 要約) を取り出す。"""
    s = get(url)
    out = []
    for it in re.findall(r"<(?:item|entry)\b.*?>(.*?)</(?:item|entry)>", s, re.S):
        clean = lambda x: html.unescape(re.sub(r"<!\[CDATA\[|\]\]>|<[^>]+>", "", x or "")).strip()
        t = re.search(r"<title[^>]*>(.*?)</title>", it, re.S)
        l = re.search(r'<link[^>]*href="([^"]+)"', it) or re.search(r"<link>(.*?)</link>", it, re.S)
        d = re.search(r"<(?:description|summary)[^>]*>(.*?)</(?:description|summary)>", it, re.S)
        if t and l:
            out.append((name, clean(t.group(1)), clean(l.group(1)).split("?")[0], clean(d.group(1) if d else "")))
    return out


def score(text, profile):
    low = " " + text.lower() + " "
    if any(x in low for x in profile["exclude"]):
        return 0, []
    total, hits = 0, []
    for theme, conf in profile["themes"].items():
        n = sum(1 for w in conf["words"] if re.search(r"\b" + re.escape(w), low))
        if n:
            total += conf["weight"] * n
            hits.append(theme)
    return total, hits


def cefr_levels():
    lv = {"A1": 1, "A2": 2, "B1": 3, "B2": 4}
    out = {}
    path = ROOT / "tools" / "predict" / "cefrj-vocabulary-profile-1.5.csv"
    if not path.exists():
        subprocess.run(["curl", "-sL", "-o", str(path),
                        "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/master/cefrj-vocabulary-profile-1.5.csv"])
    for r in csv.DictReader(open(path, encoding="utf-8")):
        l = lv.get(r["CEFR"].strip())
        for w in r["headword"].split("/"):
            w = w.strip().lower()
            if l and (w not in out or l < out[w]):
                out[w] = l
    return out


def level(word, cefr):
    """アプリと同じ4段階（基礎・標準・難関・最難関）。"""
    f = zipf_frequency(word, "en")
    c = cefr.get(word) or (cefr.get(word[:-2]) if word.endswith("ly") else None)
    if c and c <= 2:
        return 1
    if c == 3:
        return 1 if f >= 3.5 else 2
    if c == 4:
        return 2 if f >= 3.0 else 3
    if f >= 4.5:
        return 2
    return 3 if f >= 3.0 else 4


def main(out_dir):
    out = Path(out_dir)
    (out / "text").mkdir(parents=True, exist_ok=True)
    profile = json.load(open(HERE / "profile.json", encoding="utf-8"))
    seen = set()
    hist = HERE / "picked_urls.txt"
    if hist.exists():
        seen = set(hist.read_text().split())

    cands = []
    for name, url in profile["feeds"].items():
        for src, title, link, summ in read_feed(name, url):
            if link in seen or "/video" in link or "/podcast" in link:
                continue
            s, hits = score(title + " " + summ, profile)
            if s:
                cands.append((s, src, title, link, hits))
    cands.sort(key=lambda x: -x[0])

    picked = []
    for s, src, title, link, hits in cands:
        if len(picked) >= profile["pick"]:
            break
        text = trafilatura.extract(get(link)) or ""
        n = len(text.split())
        if not (profile["min_words"] <= n <= profile["max_words"]):
            continue
        s2, hits2 = score(text[:3000], profile)
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:60].strip("-")
        (out / "text" / f"{slug}.txt").write_text(text, encoding="utf-8")
        picked.append({"媒体": src, "タイトル": title, "URL": link, "語数": n, "点数": s + s2,
                       "テーマ": "・".join(sorted(set(hits + hits2))), "file": slug})

    # 単語の洗い出し
    nlp = spacy.load("en_core_web_sm")
    cefr = cefr_levels()
    have = {x["word"] for x in json.load(open(ROOT / "data" / "words_nagoya.json", encoding="utf-8"))}
    cnt, arts = Counter(), defaultdict(set)
    for p in picked:
        for t in nlp((out / "text" / f"{p['file']}.txt").read_text(encoding="utf-8")):
            lem = t.lemma_.lower()
            if t.pos_ in POS_JA and re.fullmatch(r"[a-z]{4,}", lem):
                cnt[(lem, POS_JA[t.pos_])] += 1
                arts[(lem, POS_JA[t.pos_])].add(p["file"])
    rows = []
    for (w, pos), n in cnt.items():
        lv = level(w, cefr)
        if lv >= 2 and w not in have and w not in profile.get("ignore_words", []) and zipf_frequency(w, "en") >= 2.5:
            rows.append([w, pos, LEVEL_JA[lv], n, len(arts[(w, pos)])])
    rows.sort(key=lambda r: (-r[4], -r[3], r[0]))

    with open(out / "articles.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["媒体", "タイトル", "URL", "語数", "点数", "テーマ", "file"])
        w.writeheader(); w.writerows(picked)
    with open(out / "new_words.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["単語", "品詞", "レベル", "合計回数", "出てきた記事数"]); w.writerows(rows)
    with open(hist, "a") as f:
        for p in picked:
            f.write(p["URL"] + "\n")
    print(len(picked), "articles;", len(rows), "new words")


if __name__ == "__main__":
    main(sys.argv[1])
