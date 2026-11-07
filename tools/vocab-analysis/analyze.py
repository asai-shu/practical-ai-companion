"""名大2次（理系前期）英語の頻出語を、原形・品詞ごとに数えて CEFR-J でレベル分けする。"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import spacy
from wordfreq import zipf_frequency

BASE = Path(__file__).parent
TEXT_DIR = BASE / "text"
CEFRJ = BASE.parent / "cefrj-1.5.csv"

FUNCTION_POS = {"DET", "ADP", "PRON", "AUX", "CCONJ", "SCONJ", "PART", "NUM", "INTJ"}
POS_JA = {
    "NOUN": "名詞", "VERB": "動詞", "ADJ": "形容詞", "ADV": "副詞", "PROPN": "固有名詞",
    "DET": "限定詞", "ADP": "前置詞", "PRON": "代名詞", "AUX": "助動詞", "CCONJ": "接続詞",
    "SCONJ": "接続詞", "PART": "不変化詞", "NUM": "数詞", "INTJ": "間投詞", "X": "その他",
}
LEVEL_OF = {"A1": 1, "A2": 2, "B1": 3, "B2": 4}
LEVEL_JA = {1: "1 中学基本", 2: "2 高校基本", 3: "3 高校発展", 4: "4 入試難関", 5: "5 リスト外（難関・専門）"}

# 意味が大きく変わるので、元の形容詞にまとめない副詞・名詞
NO_DERIVE = {"hardly", "nearly", "lately", "shortly", "fairly", "barely", "highly", "mostly",
             "scarcely", "presently", "business", "witness", "only", "early", "likely",
             "daily", "weekly", "family", "apply", "reply", "supply", "fly", "rely", "ally"}


def load_cefrj():
    levels = {}
    with open(CEFRJ, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lv = LEVEL_OF.get(row["CEFR"].strip())
            if not lv:
                continue
            for w in row["headword"].split("/"):
                w = w.strip().lower()
                if w and (w not in levels or lv < levels[w]):
                    levels[w] = lv
    return levels


def derive_base(lemma, pos, known):
    """推測できる派生語（-ly 副詞、-ness 名詞）を元の形容詞にまとめる。"""
    if lemma in NO_DERIVE:
        return None
    cands = []
    if pos == "ADV" and lemma.endswith("ly"):
        stem = lemma[:-2]
        cands = [stem, stem[:-1] + "y" if stem.endswith("i") else None,
                 stem + "le" if lemma.endswith("bly") or lemma.endswith("ply") else None,
                 stem + "e", lemma[:-1] if lemma.endswith("lly") else None]
        if lemma.endswith("ically"):
            cands.insert(0, lemma[:-4])  # dramatically -> dramatic
    elif pos == "NOUN" and lemma.endswith("ness"):
        stem = lemma[:-4]
        cands = [stem, stem[:-1] + "y" if stem.endswith("i") else None]
    for c in cands:
        if c and len(c) >= 3 and c in known:
            return c
    return None


def fix_lemma(lemma, surface):
    """未知語で起きる原形化のミス（cyberbullye, identifi など）を直す。"""
    if zipf_frequency(lemma, "en") >= 1.5:
        return lemma
    cands = [lemma[:-1] if lemma.endswith("e") else None,
             lemma[:-2] + "y" if lemma.endswith("ie") else None,
             lemma[:-1] + "y" if lemma.endswith("i") else None,
             surface]
    for c in cands:
        if c and zipf_frequency(c, "en") >= 1.5:
            return c
    return lemma


def main():
    nlp = spacy.load("en_core_web_sm")
    cefr = load_cefrj()
    years = sorted(p.stem for p in TEXT_DIR.glob("*.txt"))

    tokens = []  # (year, lemma, pos, surface, sentence)
    for y in years:
        doc = nlp((TEXT_DIR / f"{y}.txt").read_text(encoding="utf-8"))
        for t in doc:
            if not re.fullmatch(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-z]+)*", t.text):
                continue
            pos = t.pos_
            lemma = t.lemma_ if pos == "PROPN" else fix_lemma(t.lemma_.lower(), t.text.lower())
            if len(lemma) == 1 and lemma not in ("a", "i"):
                continue  # 選択肢記号 (A) (B) など
            tokens.append((y, lemma, pos, t.text, t.sent.text.strip()))

    known = set(cefr) | {lem for _, lem, _, _, _ in tokens}
    entries = {}
    for y, lemma, pos, surface, sent in tokens:
        key_pos = "PROPN" if pos == "PROPN" else ("FUNC" if pos in FUNCTION_POS else pos)
        base = None if key_pos in ("PROPN", "FUNC") else derive_base(lemma, pos, known)
        head, head_pos = (base, "ADJ") if base else (lemma, key_pos)
        # 同じ見出し語で品詞が違う場合（例: close 動詞/形容詞）は別項目にする
        k = (head, head_pos)
        e = entries.setdefault(k, {"word": head, "pos": head_pos, "count": 0,
                                   "years": defaultdict(int), "forms": defaultdict(int), "contexts": []})
        e["count"] += 1
        e["years"][y] += 1
        e["forms"][surface.lower() if pos != "PROPN" else surface] += 1
        e["contexts"].append({"year": y, "form": surface, "sentence": sent})

    rows = []
    for e in entries.values():
        w = e["word"].lower()
        if e["pos"] == "PROPN":
            level = "固有名詞"
        elif w in cefr:
            level = LEVEL_JA[cefr[w]]
        elif zipf_frequency(w, "en") < 1.5:
            level = "要確認（読み取りミスの可能性）"
        else:
            level = LEVEL_JA[5]
        pos_ja = "機能語" if e["pos"] == "FUNC" else POS_JA.get(e["pos"], e["pos"])
        rows.append({**e, "level": level, "pos_ja": pos_ja})

    rows.sort(key=lambda r: (-r["count"], -len(r["years"]), r["word"]))
    json.dump(rows, open(BASE / "entries.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0, default=dict)
    print(len(tokens), "tokens,", len(rows), "entries")


if __name__ == "__main__":
    sys.exit(main())
