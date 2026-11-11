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
