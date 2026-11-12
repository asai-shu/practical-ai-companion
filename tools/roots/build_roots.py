"""語源モード用のデータ data/roots.json を作る。

単語の中心になる部品（語根）ごとに、意味（1つ以上）と例の単語を持たせる。
意味と例の単語は、辞書・単語帳を写さずに書いたもの。
使い方: python3 tools/roots/build_roots.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# (語根の形, [(意味, "単語=意味, 単語=意味, ..."), ...])
R = [
    ("spect / spec", [("見る", "inspect=検査する, prospect=見通し, spectator=観客, perspective=視点, spectacle=壮観")]),
    ("vis / vid", [("見る", "visible=目に見える, vision=視力・展望, evidence=証拠, revise=修正する, supervise=監督する")]),
    ("aud", [("聞く", "audience=聴衆, audible=聞こえる, auditorium=講堂, audition=オーディション")]),
    ("dict", [("言う", "predict=予測する, contradict=矛盾する, dictate=書き取らせる・命令する, verdict=評決, dictionary=辞書")]),
    ("voc / vok", [("声・呼ぶ", "vocal=声の, advocate=主張する・支持者, vocabulary=語彙, evoke=呼び起こす, provoke=怒らせる・引き起こす")]),
    ("scrib / script", [("書く", "describe=描写する, prescribe=処方する, subscribe=定期購読する, manuscript=原稿, inscription=碑文")]),
    ("graph / gram", [("書く・描く", "photograph=写真, paragraph=段落, autograph=サイン, diagram=図, telegram=電報")]),
    ("log", [("言葉・話", "dialogue=対話, apology=謝罪, logic=論理, monologue=独白"),
             ("学問", "biology=生物学, psychology=心理学, geology=地質学, ecology=生態学")]),
    ("lingu", [("言語", "linguistics=言語学, bilingual=2言語を話す, multilingual=多言語の")]),
    ("liter", [("文字", "literature=文学, literate=読み書きができる, literal=文字どおりの, literacy=読み書きの能力")]),
    ("nom / nym", [("名前", "nominate=指名する, anonymous=匿名の, synonym=同義語, nominal=名目上の")]),
    ("port", [("運ぶ", "transport=輸送する, export=輸出する, portable=持ち運びできる, support=支える"),
              ("港・門", "airport=空港, port=港, portal=入り口, passport=パスポート")]),
    ("fer", [("運ぶ", "transfer=移す, refer=言及する, offer=提供する, ferry=フェリー"),
             ("生む・耐える", "suffer=苦しむ, fertile=肥沃な, conifer=針葉樹")]),
    ("lat", [("運ぶ", "translate=翻訳する, relate=関連づける, collate=照合する")]),
    ("mit / miss", [("送る", "transmit=送る, submit=提出する, emit=放出する, mission=使命, dismiss=解散させる・退ける, admit=認める")]),
    ("ject", [("投げる", "reject=拒絶する, inject=注射する, project=計画・投影する, eject=追い出す, object=反対する")]),
    ("tract", [("引く", "attract=引きつける, extract=抽出する, distract=気をそらす, contract=契約・縮む, subtract=引く, tractor=トラクター")]),
    ("duc / duct", [("導く", "conduct=行う・導く, educate=教育する, introduce=導入する, reduce=減らす, induce=誘発する, produce=生産する")]),
    ("pel / puls", [("押す・駆り立てる", "compel=強いる, expel=追放する, propel=推進する, impulse=衝動, repel=追い払う")]),
    ("press", [("押す", "pressure=圧力, compress=圧縮する, depress=落ち込ませる, express=表現する, suppress=抑える, impress=印象づける")]),
    ("pos / pon", [("置く", "position=位置, deposit=預ける, compose=構成する, postpone=延期する, opponent=対戦相手, expose=さらす")]),
    ("struct", [("建てる・積む", "structure=構造, construct=建設する, destruction=破壊, instruct=指示する, infrastructure=社会基盤")]),
    ("fac / fact / fect", [("作る・行う", "factory=工場, manufacture=製造する, effect=効果, affect=影響する, facilitate=容易にする, defect=欠陥")]),
    ("form", [("形", "transform=変形させる, uniform=制服・均一の, reform=改革する, formula=公式, conform=従う")]),
    ("mov / mot / mob", [("動く", "remove=取り除く, motion=動き, promote=促進する, mobile=移動できる, emotion=感情, motive=動機")]),
    ("ced / ceed / cess", [("進む・行く", "proceed=進む, exceed=超える, precede=先行する, access=接近・利用, process=過程, succeed=成功する・継ぐ"),
                           ("譲る", "concede=認める・譲る, concession=譲歩")]),
    ("grad / gress", [("歩む・段階", "gradual=徐々の, graduate=卒業する, progress=進歩, aggressive=攻撃的な, degrade=質を落とす")]),
    ("ven / vent", [("来る", "convene=集まる, prevent=防ぐ, event=出来事, invent=発明する, intervene=介入する, avenue=大通り")]),
    ("cur / curs", [("走る・流れる", "current=現在の・流れ, occur=起こる, recur=再発する, currency=通貨, excursion=遠足")]),
    ("sequ / secu", [("続く", "sequence=連続, consequence=結果, subsequent=その後の, consecutive=連続した, sequel=続編")]),
    ("sta / sist / stit", [("立つ", "stable=安定した, status=地位, assist=助ける, resist=抵抗する, constitute=構成する, institute=設立する・機関")]),
    ("sed / sid / sess", [("座る", "sedentary=座りがちな, reside=住む, president=大統領, session=会期・集まり, subside=おさまる")]),
    ("ten / tain / tin", [("保つ", "maintain=維持する, contain=含む, retain=保持する, tenant=賃借人, continue=続ける, sustain=持続させる")]),
    ("cap / cept / ceive", [("取る・つかむ", "capture=捕らえる, accept=受け入れる, receive=受け取る, perceive=認識する, capable=能力がある, concept=概念")]),
    ("capit", [("頭", "capital=首都・資本, capitalism=資本主義, capitalize=大文字で書く, decapitate=首をはねる")]),
    ("man / manu", [("手", "manual=手の・説明書, manufacture=製造する, manipulate=操作する, manuscript=原稿, manage=管理する")]),
    ("ped / pod", [("足", "pedestrian=歩行者, pedal=ペダル, expedition=遠征, tripod=三脚, impede=妨げる")]),
    ("corp", [("体", "corporate=法人の, corpse=死体, incorporate=組み入れる, corporation=企業")]),
    ("cord / cour", [("心", "courage=勇気, cordial=心からの, accord=一致, encourage=励ます, discord=不一致")]),
    ("anim", [("生命・心", "animal=動物, animate=生気を与える, unanimous=全員一致の, animation=アニメーション・活気")]),
    ("psych", [("心・精神", "psychology=心理学, psychiatry=精神医学, psychic=心霊の")]),
    ("ment", [("心", "mental=精神の, mention=言及する, mentality=考え方, demented=正気でない")]),
    ("sens / sent", [("感じる", "sensitive=敏感な, sensation=感覚, sentiment=感情, consent=同意する, resent=憤る, sensible=分別のある")]),
    ("path", [("感情", "sympathy=同情, empathy=共感, apathy=無関心, antipathy=反感"),
              ("病気・苦しみ", "pathology=病理学, pathogen=病原体, psychopath=精神病質者")]),
    ("phil", [("愛する", "philosophy=哲学, philanthropy=慈善活動, philharmonic=音楽を愛する")]),
    ("cred", [("信じる", "credit=信用, credible=信用できる, incredible=信じられない, credential=資格証明, credulous=信じやすい")]),
    ("fid", [("信頼", "confident=自信のある, confide=打ち明ける, fidelity=忠実")]),
    ("sci", [("知る", "science=科学, conscious=意識している, conscience=良心, unconscious=無意識の")]),
    ("cogn", [("知る", "recognize=認める, cognitive=認知の, incognito=身元を隠して, cognition=認知")]),
    ("memor", [("記憶", "memory=記憶, memorial=記念の, memorize=暗記する, commemorate=記念する, memorable=記憶に残る")]),
    ("doc / doct", [("教える", "doctor=医者・博士, doctrine=教義, document=文書, docile=従順な")]),
    ("gen", [("生む・生まれ", "generate=生み出す, gene=遺伝子, genetic=遺伝の, genesis=起源, generation=世代"),
             ("種類", "gender=性, genre=ジャンル, general=全般の, generic=一般的な")]),
    ("nat", [("生まれる", "native=生まれた土地の, nature=自然・性質, nation=国家, innate=生まれつきの, natal=出生の")]),
    ("viv / vit", [("生きる・命", "survive=生き残る, vivid=鮮やかな, vital=不可欠な, revive=生き返らせる, vitamin=ビタミン")]),
    ("bio", [("生命", "biology=生物学, biography=伝記, antibiotic=抗生物質, symbiosis=共生")]),
    ("mort", [("死", "mortal=死ぬ運命の, immortal=不死の, mortality=死亡率, mortgage=住宅ローン")]),
    ("cid / cis", [("切る", "decide=決める, precise=正確な, concise=簡潔な, scissors=はさみ, incision=切開"),
                   ("殺す", "suicide=自殺, pesticide=殺虫剤, homicide=殺人, genocide=大量虐殺")]),
    ("sect", [("切る", "section=部分, insect=昆虫, intersect=交差する, dissect=解剖する, sector=部門")]),
    ("rupt", [("破る", "interrupt=さえぎる, erupt=噴火する, disrupt=混乱させる, bankrupt=破産した, corrupt=腐敗した, abrupt=突然の")]),
    ("frag / fract", [("壊す", "fragile=壊れやすい, fragment=破片, fraction=一部・分数, fracture=骨折")]),
    ("clud / clus / clos", [("閉じる", "include=含む, exclude=除外する, conclude=結論づける, enclose=囲む, exclusive=独占的な, disclose=明らかにする")]),
    ("solv / solu", [("解く・ゆるめる", "solve=解く, dissolve=溶かす, resolve=解決する, solution=解決策・溶液, absolute=絶対的な")]),
    ("tend / tens / tent", [("伸ばす・向ける", "extend=伸ばす, tension=緊張, attend=出席する・注意を向ける, intend=意図する, tendency=傾向, pretend=ふりをする")]),
    ("flect / flex", [("曲げる", "reflect=反射する・熟考する, flexible=柔軟な, deflect=そらす, reflex=反射作用")]),
    ("tort", [("ねじる", "distort=ゆがめる, torture=拷問, extort=ゆすり取る, contort=ねじ曲げる")]),
    ("vert / vers", [("向きを変える・回る", "convert=変換する, reverse=逆にする, diverse=多様な, version=版, advertise=宣伝する, universe=宇宙")]),
    ("volv / volu", [("回る・巻く", "revolve=回転する, evolve=進化する, involve=巻き込む, volume=巻・量, revolution=革命・回転")]),
    ("flu", [("流れる", "fluid=流体, fluent=流ちょうな, influence=影響, influenza=インフルエンザ, affluent=裕福な, fluctuate=変動する")]),
    ("pend / pens", [("つるす・ぶら下がる", "depend=頼る, suspend=つるす・一時停止する, pendulum=振り子, appendix=付録"),
                     ("重さを量る・支払う", "expense=費用, compensate=補償する, pension=年金, expend=費やす, dispense=分配する")]),
    ("plic / ply / plex", [("折る・重ねる", "complicated=複雑な, apply=当てはめる・申し込む, imply=ほのめかす, complex=複雑な, duplicate=複製する, multiply=増やす")]),
    ("sign", [("しるし", "signal=合図, signature=署名, significant=重要な, designate=指定する, assign=割り当てる, resign=辞職する")]),
    ("test", [("証言する・証明する", "testify=証言する, testimony=証言, protest=抗議する, contest=競争・争う, attest=証明する")]),
    ("prob / prov", [("試す・証明する", "prove=証明する, probe=探る, approve=承認する, probable=ありそうな, probation=試用期間")]),
    ("quir / quest / quis", [("求める・尋ねる", "require=必要とする, inquire=尋ねる, request=頼む, acquire=獲得する, conquest=征服, exquisite=非常に美しい")]),
    ("claim / clam", [("叫ぶ", "exclaim=叫ぶ, proclaim=宣言する, acclaim=称賛する, clamor=騒ぎ, reclaim=取り戻す")]),
    ("nounce / nunci", [("知らせる", "announce=発表する, pronounce=発音する, denounce=非難する, renounce=放棄する, pronunciation=発音")]),
    ("jud / jur / jus", [("法・正しい", "judge=裁判官・判断する, jury=陪審, justice=正義, justify=正当化する, prejudice=偏見, injury=けが・損害")]),
    ("leg", [("法", "legal=法律の, legislate=法律を制定する, legitimate=合法の, illegal=違法の"),
             ("読む・選ぶ", "legible=読みやすい, legend=伝説, elegant=上品な")]),
    ("reg / rect", [("まっすぐ・正しい・支配する", "regular=規則的な, regulate=規制する, correct=正しい, direct=直接の・指導する, region=地域, erect=直立した")]),
    ("norm", [("基準", "normal=普通の, enormous=巨大な, abnormal=異常な, norm=規範")]),
    ("domin", [("支配する", "dominate=支配する, dominant=支配的な, dominion=支配権, predominant=優勢な")]),
    ("popul / publ", [("人々", "population=人口, popular=人気のある, public=公共の, publish=出版する, republic=共和国")]),
    ("dem", [("人々", "democracy=民主主義, epidemic=流行病, demographic=人口統計の, pandemic=世界的流行病")]),
    ("greg", [("群れ・集まり", "congregate=集まる, segregate=隔離する, aggregate=総計, gregarious=社交的な")]),
    ("soci", [("仲間・社会", "society=社会, social=社会の, associate=関連づける・仲間, sociology=社会学")]),
    ("host / hosp", [("客・もてなす", "hospital=病院, hospitality=もてなし, host=主人, hostel=簡易宿泊所")]),
    ("priv", [("個人の", "private=個人の, privacy=プライバシー, privilege=特権"),
              ("奪う", "deprive=奪う, deprivation=欠乏")]),
    ("serv", [("仕える", "serve=仕える, service=奉仕, servant=使用人, deserve=値する"),
              ("保つ・守る", "preserve=保存する, conserve=保護する, reserve=取っておく, observe=観察する・守る")]),
    ("val / vail", [("価値", "value=価値, evaluate=評価する, valid=有効な, equivalent=同等の"),
                    ("力・強い", "prevail=普及する・勝つ, available=利用できる, valor=勇気")]),
    ("fort / forc", [("強い", "effort=努力, comfort=快適さ・慰める, fortify=強化する, enforce=施行する, reinforce=強める, fortress=要塞")]),
    ("vinc / vict", [("勝つ", "victory=勝利, convince=納得させる, victor=勝者, invincible=無敵の, convict=有罪を宣告する")]),
    ("pot / poss", [("力がある・できる", "potential=潜在的な, possible=可能な, possess=所有する, potent=強力な")]),
    ("magn", [("大きい", "magnify=拡大する, magnificent=壮大な, magnitude=大きさ, magnate=有力者")]),
    ("min", [("小さい", "minor=小さいほうの, minute=微小な・分, diminish=減らす, minimum=最小限, minority=少数派")]),
    ("medi", [("中間", "medium=中間の・媒体, mediate=仲介する, intermediate=中級の, medieval=中世の, immediate=即座の, Mediterranean=地中海の")]),
    ("fin", [("終わり・限界", "final=最後の, finish=終える, define=定義する, infinite=無限の, confine=閉じ込める, refine=洗練する")]),
    ("termin", [("終わり・境界", "terminal=終点・末期の, terminate=終わらせる, determine=決定する, exterminate=絶滅させる")]),
    ("prim / prin", [("第一の", "primary=第一の, primitive=原始的な, prime=最も重要な, principle=原理, principal=主要な・校長")]),
    ("nov", [("新しい", "novel=小説・目新しい, innovate=革新する, renovate=改装する, novice=初心者, novelty=目新しさ")]),
    ("chron", [("時", "chronic=慢性の, chronological=年代順の, synchronize=同時に起こる, chronicle=年代記")]),
    ("tempor", [("時", "temporary=一時的な, contemporary=同時代の・現代の, temporal=時間の")]),
    ("ann / enn", [("年", "annual=毎年の, anniversary=記念日, centennial=100周年の, millennium=千年間, perennial=永続する")]),
    ("dur", [("続く・固い", "during=～の間, endure=耐える, durable=長持ちする, duration=持続期間")]),
    ("loc", [("場所", "local=地元の, locate=位置を突き止める, allocate=割り当てる, relocate=移転する")]),
    ("terr", [("土地", "territory=領土, terrain=地形, terrestrial=陸上の・地球の, Mediterranean=地中海の"),
              ("恐れ", "terror=恐怖, terrible=ひどい, terrify=怖がらせる")]),
    ("aqu", [("水", "aquarium=水族館, aquatic=水生の, aqueduct=水道橋")]),
    ("hydr", [("水", "hydrogen=水素, dehydrate=水分を取り除く, hydrant=消火栓, hydroelectric=水力発電の")]),
    ("sol", [("太陽", "solar=太陽の, solstice=夏至・冬至, parasol=日傘"),
             ("1つ・ひとり", "sole=唯一の, solitary=ひとりの, solo=独奏, solitude=孤独")]),
    ("luc / lum", [("光", "illuminate=照らす, lucid=明快な, luminous=光る, translucent=半透明の, elucidate=明らかにする")]),
    ("phon", [("音", "telephone=電話, symphony=交響曲, microphone=マイク, phonetic=音声の")]),
    ("therm", [("熱", "thermometer=温度計, thermal=熱の, geothermal=地熱の, hypothermia=低体温症")]),
    ("urb", [("都市", "urban=都市の, suburb=郊外, urbanize=都市化する")]),
    ("migr", [("移る", "migrate=移住する, immigrant=(他国からの)移民, emigrate=(他国へ)移住する, migratory=移動性の")]),
    ("labor", [("働く", "labor=労働, laboratory=実験室, collaborate=協力する, elaborate=念入りな")]),
    ("techn", [("技術", "technology=科学技術, technique=技法, technical=技術的な")]),
    ("tact / tang", [("触れる", "contact=接触, intact=無傷の, tangible=触れられる・明白な, tactile=触覚の, tangent=接線")]),
    ("vac / van / void", [("空の", "vacant=空いている, vacuum=真空, vanish=消える, evacuate=避難させる, avoid=避ける, vacation=休暇")]),
    ("ple / plen", [("満たす", "complete=完全な, plenty=たくさん, supplement=補足, deplete=使い果たす, implement=実行する")]),
    ("cre / cresc", [("増える・育つ", "increase=増える, decrease=減る, create=創造する, crescent=三日月, recreation=気晴らし")]),
    ("alt", [("高い", "altitude=高度, alto=アルト, exalt=高める"),
             ("他の", "alter=変える, alternative=代わりのもの, alternate=交互の")]),
    ("equ", [("等しい", "equal=等しい, equation=方程式, equator=赤道, adequate=十分な, equity=公平")]),
    ("simil / simul", [("似た・同時", "similar=似ている, simulate=模擬実験する, simultaneous=同時の, assimilate=同化する")]),
    ("var", [("変わる", "vary=変わる, various=さまざまな, variable=変わりやすい, variation=変動, variety=多様性")]),
    ("mut", [("変わる", "mutation=突然変異, mutual=相互の, commute=通勤する, immutable=不変の")]),
    ("liber", [("自由", "liberty=自由, liberal=自由主義の, liberate=解放する")]),
    ("don / dot", [("与える", "donate=寄付する, donor=提供者, pardon=許す, anecdote=逸話, antidote=解毒剤")]),
    ("grat", [("喜び・感謝", "grateful=感謝している, gratitude=感謝, congratulate=祝う, gratify=喜ばせる")]),
    ("spir / pir", [("息をする", "inspire=鼓舞する, respiration=呼吸, expire=期限が切れる, aspire=熱望する, spirit=精神, conspire=共謀する")]),
    ("cur / care", [("注意・世話", "cure=治す, secure=安全な, accurate=正確な, curious=好奇心の強い, curator=学芸員")]),
    ("medic / med", [("治す", "medicine=薬・医学, medical=医学の, medication=薬物治療, remedy=治療法")]),
    ("ject / jac", [("横たわる", "adjacent=隣接した")]),
]


def main():
    out, seen = [], set()
    for root, senses in R:
        if root == "ject / jac":      # 例が少ないので入れない
            continue
        if root == "cur / care":      # 「cur（走る）」と形が同じなので、別の意味として合流させる
            for a in out:
                if a["affix"] == "cur / curs":
                    a["senses"].append({"role": "注意・世話", "pos": None,
                                        "examples": [x.split("=") for x in senses[0][1].split(", ")]})
            continue
        a = {"affix": root, "type": "root", "senses": []}
        for role, ex in senses:
            a["senses"].append({"role": role, "pos": None, "examples": [x.split("=") for x in ex.split(", ")]})
        out.append(a)
    # 検査：例の単語に語根の形が入っていること
    bad = []
    for a in out:
        vs = [v.strip() for v in a["affix"].split("/")]
        for s in a["senses"]:
            for w, ja in s["examples"]:
                if not any(v in w.lower() for v in vs):
                    bad.append((a["affix"], w))
        assert a["affix"] not in seen, a["affix"]
        seen.add(a["affix"])
    assert not bad, bad
    json.dump(out, open(ROOT / "data" / "roots.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(out), "語根;", sum(len(a["senses"]) > 1 for a in out), "個は意味が2つ以上;",
          sum(len(s["examples"]) for a in out for s in a["senses"]), "例")


if __name__ == "__main__":
    main()
