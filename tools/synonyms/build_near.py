"""意味の近い単語どうしの一覧 data/near_words.json を作る。

クイズで、正解の単語と意味の近い単語（類義語）の意味が、不正解の選択肢に並ばないようにするために使う。
英語の類義語辞書 WordNet（Princeton University）で、同じ意味のグループに入っている単語と、
そのすぐ上・すぐ下の意味のグループに入っている単語を「近い」とみなす。
多めに「近い」と判定しても、選択肢の候補が少し減るだけなので問題ない。

使い方: python3 tools/synonyms/build_near.py <WordNet を置いた nltk_data フォルダ>
  （WordNet のデータ自体はリポジトリに入れない。nltk_data/corpora/wordnet.zip を置いたフォルダを渡す）
"""
import json
import sys
from pathlib import Path

import nltk

ROOT = Path(__file__).resolve().parent.parent.parent
nltk.data.path.insert(0, sys.argv[1])
from nltk.corpus import wordnet as wn  # noqa: E402


def related(word):
    """word と意味の近い英単語（小文字）の集まり"""
    out = set()
    for s in wn.synsets(word.replace(" ", "_")):
        group = [s] + s.hypernyms() + s.hyponyms() + s.similar_tos() + s.also_sees() + s.verb_groups()
        for g in group:
            for lemma in g.lemmas():
                out.add(lemma.name().replace("_", " ").lower())
                for d in lemma.derivationally_related_forms():   # success / succeed / successful など
                    out.add(d.name().replace("_", " ").lower())
    out.discard(word.lower())
    return out


def main():
    words = set()
    for f in ("words_kyotsu.json", "words_nagoya.json"):
        words |= {w["word"] for w in json.load(open(ROOT / "data" / f, encoding="utf-8"))}
    near = {}
    for w in sorted(words):
        hit = sorted(related(w) & {x.lower() for x in words})
        if hit:
            near[w] = hit
    # 片方だけに出ている組は、両方に入れる
    for w, hs in list(near.items()):
        for h in hs:
            near.setdefault(h, [])
            if w.lower() not in near[h]:
                near[h].append(w.lower())
    near = {w: sorted(set(hs)) for w, hs in near.items()}
    json.dump(near, open(ROOT / "data" / "near_words.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    sizes = sorted(len(v) for v in near.values())
    print(len(words), "語のうち", len(near), "語に近い単語あり; 1語あたり 中央値", sizes[len(sizes) // 2], "最大", sizes[-1])
    for w in ("maintain", "consistent", "suppose", "reduce", "huge", "benefit", "make", "thing"):
        print(" ", w, "→", near.get(w))


if __name__ == "__main__":
    main()
