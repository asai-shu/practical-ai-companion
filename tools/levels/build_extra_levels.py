"""イディオムと語源（語根）のレベル（1 基礎〜4 最難関）を決めて data/extra_levels.json に書く。

単語のレベルと同じ4段階にそろえるための仮の決め方（データが増えたら見直す）。
- イディオム：中の単語のうち、いちばん難しい単語のレベル。
  単語データにある単語はそのレベル、ない単語は英語での使われやすさ（wordfreq）から決める。
  ただし、易しい単語だけでできていても意味が想像しにくい句動詞（give in など）は1段上げる。
- 語根：例の単語の使われやすさの中央値から決める（よく使われる単語が多いほど易しい）。
使い方: python3 tools/levels/build_extra_levels.py
"""
import json
import re
import statistics
from pathlib import Path

from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parent.parent.parent
SKIP = {"a", "an", "the", "to", "of", "in", "on", "at", "for", "with", "by", "from", "as", "and", "or", "be", "is",
        "one's", "oneself", "someone", "something", "a", "b", "it", "do", "not", "that", "than", "so", "into", "up",
        "out", "off", "over", "down", "about", "back", "away"}
PARTICLES = {"up", "out", "off", "over", "down", "in", "on", "away", "back", "into", "through", "across", "along"}


def word_level(w, known):
    if w in known:
        return known[w]
    z = zipf_frequency(w, "en")
    return 1 if z >= 5.0 else 2 if z >= 4.0 else 3 if z >= 3.0 else 4


def idiom_level(en, known):
    words = [x for x in re.findall(r"[a-z']+", en.lower()) if x not in SKIP and len(x) > 1]
    if not words:
        return 2
    lv = max(word_level(w, known) for w in words)
    toks = re.findall(r"[a-z']+", en.lower())
    phrasal = len(toks) >= 2 and toks[-1] in PARTICLES or any(t in PARTICLES for t in toks[1:2])
    if lv == 1 and phrasal:      # 易しい単語だけの句動詞は、意味が想像しにくいので1段上げる
        lv = 2
    return lv


def root_level(examples):
    z = statistics.median(zipf_frequency(w.lower(), "en") for w, _ in examples)
    return 1 if z >= 4.6 else 2 if z >= 4.0 else 3 if z >= 3.4 else 4


def main():
    words = json.load(open(ROOT / "data" / "words_nagoya.json", encoding="utf-8")) + \
        json.load(open(ROOT / "data" / "words_kyotsu.json", encoding="utf-8"))
    known = {}
    for w in words:
        if " " not in w["word"]:
            known[w["word"].lower()] = min(known.get(w["word"].lower(), 9), w["level"])
    idioms = {x["en"] for x in json.load(open(ROOT / "data" / "idioms_nagoya.json", encoding="utf-8"))}
    idioms |= {x["en"] for w in words for x in w["idioms"]}
    roots = json.load(open(ROOT / "data" / "roots.json", encoding="utf-8"))
    out = {
        "idioms": {en: idiom_level(en, known) for en in sorted(idioms)},
        "roots": {r["affix"]: root_level([e for s in r["senses"] for e in s["examples"]]) for r in roots},
    }
    json.dump(out, open(ROOT / "data" / "extra_levels.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in out.items():
        c = [list(v.values()).count(i) for i in (1, 2, 3, 4)]
        print(k, len(v), "件 / 基礎・標準・難関・最難関 =", c)


if __name__ == "__main__":
    main()
