"""共通テスト版の単語データ data/words_kyotsu.json を作る。

材料:
  data/kyotsu_src/selected.csv  共通テスト版に入れる単語と回数
  data/words_nagoya.json        名大のデータ（かぶる単語は意味・語源などを使い回す）
  data/kyotsu_src/done_*.txt    新しく書いた意味
使い方: python3 tools/kyotsu/build_kyotsu.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "data" / "kyotsu_src"


def parse_done():
    out = {}
    for f in sorted(SRC.glob("done_*.txt")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            w, pos, ms, ids, cf = (line.split("|") + ["", "", ""])[:5]
            out[(w, pos)] = {
                "meanings": [{"ja": m, "in_exam": False, "exam_count": None} for m in ms.split(";") if m],
                "idioms": [{"en": a.split("=")[0], "ja": a.split("=")[1]} for a in ids.split(",") if "=" in a],
                "confusables": [{"en": a.split("=")[0].strip(), "ja": a.split("=")[1].strip()} for a in cf.split(" / ") if "=" in a],
            }
    return out


def main():
    nagoya = {(x["word"], x["pos"]): x for x in json.load(open(ROOT / "data" / "words_nagoya.json", encoding="utf-8"))}
    done = parse_done()
    overrides = json.load(open(ROOT / "data" / "level_overrides.json", encoding="utf-8"))  # 目視の見直しで直したレベル
    words, missing = [], []
    for r in csv.DictReader(open(SRC / "selected.csv", encoding="utf-8")):
        k = (r["単語"], r["品詞"])
        base = nagoya.get(k) or done.get(k)
        if not base:
            missing.append(k)
            continue
        e = {
            "word": r["単語"], "pos": r["品詞"], "level": overrides.get(r["単語"], int(r["レベル"])),
            "exam_count": int(r["合計回数"]), "exam_years": int(r["出た年数"]), "source": "kyotsu",
            # 共通テストでどの意味で使われたかは数えていないので、意味の印（★）は付けない
            "meanings": [{"ja": m["ja"], "in_exam": False, "exam_count": None} for m in base["meanings"]],
            "idioms": base.get("idioms", []), "confusables": base.get("confusables", []),
        }
        if base.get("etymology"):
            e["etymology"] = base["etymology"]
        words.append(e)
    words.sort(key=lambda x: (-x["exam_years"], -x["exam_count"], x["word"]))
    json.dump(words, open(ROOT / "data" / "words_kyotsu.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(words), "words;", len(missing), "skipped (意味が未作成または除外):", missing[:20])


if __name__ == "__main__":
    main()
