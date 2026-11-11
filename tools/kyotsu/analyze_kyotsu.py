"""共通テストの英語（リーディング・リスニング）のPDFから、頻出単語を数える。

使い方: python3 tools/kyotsu/analyze_kyotsu.py PDFのフォルダ
  PDFは大学入試センターのサイト（https://www.dnc.ac.jp/kyotsu/kakomondai/）から取得する。
  ファイル名の先頭4桁を年度として扱う（例: 2026_ol_10_reading.pdf）。
  結果は data/kyotsu_counts.csv に書き出す（回数だけで、英文は含まない）。
"""
import csv
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import spacy
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parent.parent.parent
POS_JA = {"NOUN": "名詞", "VERB": "動詞", "ADJ": "形容詞", "ADV": "副詞"}


def cefr_levels():
    path = ROOT / "tools" / "predict" / "cefrj-vocabulary-profile-1.5.csv"
    if not path.exists():
        subprocess.run(["curl", "-sL", "-o", str(path),
                        "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/master/cefrj-vocabulary-profile-1.5.csv"])
    lv = {"A1": 1, "A2": 2, "B1": 3, "B2": 4}
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        l = lv.get(r["CEFR"].strip())
        for w in r["headword"].split("/"):
            w = w.strip().lower()
            if l and (w not in out or l < out[w]):
                out[w] = l
    return out


def level(word, cefr):
    """アプリと同じ4段階（1 基礎・2 標準・3 難関・4 最難関）。"""
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


def main(pdf_dir):
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 2_000_000
    cefr = cefr_levels()
    cnt, years, forms = Counter(), defaultdict(set), defaultdict(Counter)
    for pdf in sorted(Path(pdf_dir).glob("*.pdf")):
        year = pdf.name[:4]
        text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        text = re.sub(r"-\n(?=[a-z])", "", text)  # 行末で切れた単語をつなぐ
        for t in nlp(text):
            lem = t.lemma_.lower()
            if t.pos_ in POS_JA and re.fullmatch(r"[a-z]{3,}", lem) and zipf_frequency(lem, "en") >= 1.5:
                k = (lem, POS_JA[t.pos_])
                cnt[k] += 1
                years[k].add(year)
                forms[k][t.text.lower()] += 1
    out = ROOT / "data" / "kyotsu_counts.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["単語", "品詞", "レベル", "合計回数", "出た年数", "まとめた形"])
        for (lem, pos), n in sorted(cnt.items(), key=lambda kv: (-len(years[kv[0]]), -kv[1], kv[0][0])):
            w.writerow([lem, pos, level(lem, cefr), n, len(years[(lem, pos)]),
                        " ".join(f"{a}({b})" for a, b in forms[(lem, pos)].most_common(4))])
    print(len(cnt), "words ->", out)


if __name__ == "__main__":
    main(sys.argv[1])
