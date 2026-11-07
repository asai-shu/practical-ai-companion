# 頻出単語の分析（原形・意味別・CEFR-Jレベル）

名古屋大学 2次試験（理系前期）英語 2020〜2024年度の頻出単語を、原形・品詞・意味ごとに数えた結果です。

- `output/nagoya_2020-2024.csv`：分析結果（単語・品詞・レベル・意味・回数・年ごとの回数）
- `analyze.py`：原形化（spaCy）と CEFR-J でのレベル分けを行うスクリプト
- `senses.txt`：3回以上出た内容語の意味判定（出現順の番号で意味を割り当てたもの）

過去問の英文そのもの（`text/`）は著作物なので、このリポジトリには含めていません。

レベルは CEFR-J Wordlist Version 1.5（Compiled by Yukio Tono, Tokyo University of Foreign Studies）を参照しています。
