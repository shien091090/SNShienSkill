"""Sound moments for the review page: one tab per moment, a few alternatives each.

"0" = the default PLAN layers of the moment's cues (libmix.PLAN, Kenney/OpenGameArt); "x" = silent.
Every other option maps cue id -> layers and replaces every cue of the moment.
Sources: lab/ = 効果音ラボ, mk/ = Mixkit (id), ov/ = Openverse CC0 (id prefix); see lib/CREDITS.md.
Layer options: align="peak" puts the loudest point on the cue (whooshes), len = max seconds kept.
"""


def L(name, lufs, off=0.0, **o):
    return (name, lufs, off, o)


COINS = ["coin:0@1284", "coin:1@1295", "coin:2@1321"]
TEXTS = ["play:text@254", "vote:text@497", "rounds:text@624", "dev:text@1094", "better:text@1253",
         "complete:text@1339", "story:text@1426", "steam:text@1601", "gift:text@1747"]
SPARK = "sparkle:0@1863"
# the two rounds of vote towers springing up, and the winner's six votes flying into the V
VOTES1 = ["votes@507", "votes@510", "votes@512", "votes@513", "votes@515", "votes@516", "votes@518", "votes@521"]
VOTES2 = ["votes@719", "votes@721", "votes@723", "votes@724", "votes@726", "votes@727", "votes@729", "votes@732"]
CHIPS1 = ["chip-in:0@641", "chip-in:1@646", "chip-in:2@650", "chip-in:3@655", "chip-in:4@660", "chip-in:5@665"]
CHIPS2 = ["chip-in:0@835", "chip-in:1@840", "chip-in:2@845", "chip-in:3@850", "chip-in:4@854", "chip-in:5@859"]
# the eight mini-game tiles popping up in turn (in time order)
TILES = ["tile:3@217", "tile:6@229", "tile:0@240", "tile:5@249", "tile:2@256", "tile:7@262", "tile:4@266", "tile:1@271"]
MAJOR = [0, 2, 4, 5, 7, 9, 11, 12]
PENTA = [0, 2, 4, 7, 9, 12]
SEMI = [0, 1, 2, 3, 4, 5, 6, 7]  # paper sounds go thin fast, so they climb in half steps


def scale(name, lufs, cues, steps, base=0, length=0.8):
    # one note per cue climbing the scale; base lifts the second round
    return {c: [L(name, lufs + i * 0.3, 0, semi=base + steps[i], len=length)] for i, c in enumerate(cues)}


# each round's towers: the first tile appears 0.12 s before its cue, and the last chip of the
# tallest towers starts springing up this long after that (film.js votes(): stagger 0.6/n)
STACK = {VOTES1[0]: 0.79, VOTES2[0]: 0.74}


def stack(name, lufs, climb=7, n=12, length=0.35, **o):
    # n notes spread evenly over the whole build of each round, climbing `climb` semitones; round two starts 2 higher
    out = {}
    for r, (c, span) in enumerate(STACK.items()):
        out[c] = [L(name, lufs + i * 0.2, -0.12 + span * i / (n - 1), semi=o.get("semi", 0) + 2 * r + climb * i / (n - 1), len=length,
                    **{k: v for k, v in o.items() if k != "semi"})
                  for i in range(n)]
    return out


def rise(name, lufs):
    # one rising sound per round, from the first tower appearing (0.12 s before its tick) until the towers top out
    return {c: [L(name, lufs, -0.12, len=1.2)] for c in (VOTES1[0], VOTES2[0])}


def up(name, lufs, cues=COINS, step=2):
    # one sound per cue, a whole step higher each time
    return {c: [L(name, lufs + i * 0.5, 0, semi=step * i)] for i, c in enumerate(cues)}


MOMENTS = [
    # end-word:0 = the three words coming back at the end (film.js K21), the same sound as the opening title
    ("title", "片名出現", ["title:0@17", "end-word:0@2015"], {
        "0": "輕快彈出",
        "a": ("清爽的標題音", {"title:0@17": [L("lab/anime_title1.mp3", -21)]}),
        "b": ("輕快彈出 + 小咻", {"title:0@17": [L("mk/3005", -21)], "end-word:0@2015": [L("mk/3005", -21)]}),
        "c": ("可愛的文字動畫音", {"title:0@17": [L("lab/anime_logo-animation2.mp3", -21)]}),
        "p": ("上一輪選的:四個字各一聲輕點", {c: [L("ui/drop_001", -26)] for c in ["title:0@17", "title:1@21", "title:2@24", "title:plan@28"]}),
    }),
    ("spread", "展開成三個單字", ["spread@98"], {
        "0": "風聲咻",
        "a": ("快速轉場咻", {"spread@98": [L("mk/1490", -21, 0.1, align="peak")]}),
        "b": ("短促掃過", {"spread@98": [L("mk/166", -22, 0.1, align="peak")]}),
        "c": ("輕柔揮動", {"spread@98": [L("ov/97f54c3e", -22, 0.1, align="peak")]}),
        "p": ("上一輪選的:短促揮動", {"spread@98": [L("oga/swish-7", -22, -0.05)]}),
    }),
    ("ring", "聚焦 Play", ["focus:ring@161", "focus-hit:ring@169"], {
        "0": "滑入 + 金屬盤輕敲",
        "a": ("快速拉近衝擊", {"focus-hit:ring@169": [L("mk/772", -18, 0, align="peak")]}),
        "b": ("「ザッ」文字衝擊音", {"focus-hit:ring@169": [L("lab/anime_text-impact1.mp3", -18)]}),
        "c": ("短掃過 + 清脆介面音", {"focus:ring@161": [L("mk/175", -25, 0, align="peak")], "focus-hit:ring@169": [L("mk/2568", -20)]}),
        "p": ("上一輪選的:柔和確認音", {"focus:ring@161": [L("cas/card-slide-3", -27)], "focus-hit:ring@169": [L("ui/confirmation_004", -19)]}),
    }),
    ("tiles", "小遊戲格出現", TILES, {
        "0": "攤開紙牌",
        "a": ("泡泡「啵」一格比一格高", scale("ov/57fc1a1b", -24, TILES, MAJOR, 0, 0.4)),
        "b": ("柔和「ポン」一格比一格高", scale("lab/button_decision34.mp3", -24, TILES, MAJOR, 0, 0.4)),
        "c": ("可愛「ピコッ」一格比一格高", scale("lab/button_decision22.mp3", -25, TILES, MAJOR, 0, 0.4)),
        "d": ("「ニュッ」冒出一格比一格高", scale("lab/anime_nyu2.mp3", -24, TILES, MAJOR, 0, 0.4)),
        "e": ("木琴一格比一格高", scale("lab/button_decision29.mp3", -24, TILES, MAJOR, 0, 0.4)),
        "p": ("上一輪選的:一串俏皮啵啵", {"tile:3@217": [L("mk/2359", -21)]}),
    }),
    ("wan", "「玩」字跳動", ["play:wan@274"], {
        "0": "輕切換聲",
        "a": ("可愛的「咻嗯」", {"play:wan@274": [L("lab/anime_nyu3.mp3", -22, -0.12)]}),
        "b": ("Q 彈「噗溜」", {"play:wan@274": [L("lab/anime_puyon1.mp3", -22, -0.12)]}),
        "c": ("彈簧「啵嚶」", {"play:wan@274": [L("mk/2894", -22, -0.12)]}),
    }),
    ("texts", "文案出現", TEXTS, {
        "0": "只有「投票」有聲",
        "a": ("每段文案一聲可愛「啪」", {c: [L("lab/anime_pa1.mp3", -25)] for c in TEXTS}),
        "b": ("每段文案一聲小啵", {c: [L("ov/7b1f829e", -25)] for c in TEXTS}),
        "c": ("只有「投票」(猜謎出題「登登」)", {"vote:text@497": [L("lab/anime_question1.mp3", -20)]}),
    }),
    ("check", "Vote 打勾", ["focus:check@386", "focus-hit:check@395"], {
        "0": "滑入 + 清亮確認音",
        "a": ("鐵琴答對音", {"focus-hit:check@395": [L("lab/anime_correct2.mp3", -19)]}),
        "b": ("勾選框「喀」", {"focus-hit:check@395": [L("mk/1120", -19)]}),
        "c": ("清亮答對提示", {"focus-hit:check@395": [L("mk/2870", -19)]}),
    }),
    ("wall", "遊戲牆倒下", ["wall-tilt@446", "wall-down@468"], {
        "0": "木頭落地",
        "a": ("木板骨牌倒下", {"wall-tilt@446": [L("mk/3136", -19, 0.1)]}),
        "b": ("木板悶響", {"wall-down@468": [L("ov/08c76ae3", -18)]}),
        "c": ("「咚沙」倒地", {"wall-down@468": [L("lab/battle_real-down1.mp3", -18)]}),
    }),
    ("votes", "疊選票(兩輪)", VOTES1 + VOTES2, {
        "0": "抓一把籌碼",
        "a": ("紙牌推疊(變輕)", stack("cas/card-shove-2", -32.5, length=0.18, hp=1200, semi=3)),
        "b": ("紙牌輕輕滑過", stack("cas/card-slide-3", -30, length=0.15, hp=1000, semi=3)),
        "c": ("書頁輕翻", stack("mk/1104", -30, length=0.18, hp=1500, semi=2)),
        "d": ("紙片輕晃", stack("mk/2380", -31, length=0.15, hp=1500, semi=2)),
        "e": ("紙張輕掠", stack("mk/2384", -31, length=0.15, hp=1200, semi=3)),
        "p": ("上一輪選的:紙牌推疊起來", stack("cas/card-shove-2", -24, length=0.35)),
    }),
    ("fun", "「有趣」跳起", ["fun:jump@531", "fun:land@547"], {
        "0": "明亮確認音",
        "a": ("輕巧跳躍 + 落地", {"fun:jump@531": [L("lab/anime_jump-anime1.mp3", -20)], "fun:land@547": [L("lab/battle_landing1.mp3", -23)]}),
        "b": ("遊戲旋轉跳", {"fun:jump@531": [L("mk/2648", -20)]}),
        "c": ("彈開「啵嗯」", {"fun:jump@531": [L("lab/anime_boyon1.mp3", -20)]}),
    }),
    ("chips", "選票收進 V(兩輪)", ["chips-fly@634", "r2-in@701"] + CHIPS1 + CHIPS2, {
        "0": "滑動 + 籌碼碰撞 + 疊起",
        "a": ("一串鐵琴「叮」", {**scale("lab/anime_kira1.mp3", -25, CHIPS1, PENTA, 0, 0.5), **scale("lab/anime_kira1.mp3", -25, CHIPS2, PENTA, 2, 0.5)}),
        "b": ("一串玻璃「叮」", {**scale("ov/741bb1d4", -25, CHIPS1, PENTA, 0, 0.4), **scale("ov/741bb1d4", -25, CHIPS2, PENTA, 2, 0.4)}),
        "c": ("一串復古金幣", {**scale("ov/16e4248a", -26, CHIPS1, PENTA, 0, 0.3), **scale("ov/16e4248a", -26, CHIPS2, PENTA, 2, 0.3)}),
        "d": ("一串泡泡「啵」", {**scale("ov/57fc1a1b", -25, CHIPS1, PENTA, 0, 0.3), **scale("ov/57fc1a1b", -25, CHIPS2, PENTA, 2, 0.3)}),
        "e": ("一串木琴「咚」", {**scale("lab/button_decision47.mp3", -25, CHIPS1, PENTA, 0, 0.5), **scale("lab/button_decision47.mp3", -25, CHIPS2, PENTA, 2, 0.5)}),
    }),
    ("zoom", "鏡頭推近", ["hero-zoom@902"], {
        "0": "風聲咻",
        "a": ("吸入式拉近", {"hero-zoom@902": [L("mk/2608", -23, 0.15, align="peak")]}),
        "b": ("快速轉場咻", {"hero-zoom@902": [L("mk/3115", -23, 0.15, align="peak")]}),
        "c": ("高速移動「咻」", {"hero-zoom@902": [L("lab/battle_highspeed-movement1.mp3", -23)]}),
    }),
    ("stamp", "蓋「好玩」章", ["stamp@938"], {
        "0": "重拳 + 紙面拍下",
        "a": ("「啪搭」蓋章", {"stamp@938": [L("lab/anime_peta1.mp3", -14)]}),
        "b": ("真實印章蓋下", {"stamp@938": [L("ov/bb6f404c", -14, 0, align="peak")]}),
        "c": ("低沉「咚」+ 木頭敲擊", {"stamp@938": [L("lab/anime_text-impact3.mp3", -15), L("mk/2182", -18)]}),
    }),
    ("gear", "Develop 齒輪", ["focus:gear@1025", "focus-hit:gear@1033", "gear:0@1040", "gear:1@1047", "gear:2@1055"], {
        "0": "滑入 + 金屬卡榫 + 一下喀",
        "a": ("金屬齒輪鎖上", {"focus-hit:gear@1033": [L("mk/2858", -19)]}),
        "b": ("排檔「喀」一聲", {"focus-hit:gear@1033": [L("ov/a6cac67d", -19)]}),
        "c": ("鎖上 + 齒輪轉三格", {"focus-hit:gear@1033": [L("mk/2856", -20)],
                               **{c: [L("mk/2857", -25)] for c in ["gear:0@1040", "gear:1@1047", "gear:2@1055"]}}),
    }),
    # the shards cue sits 0.45 s into the fall (film.js), so breaking sounds run 0.45 s early to start with it
    ("crack", "畫面裂開", ["screen-in@1104", "crack@1123", "shards@1178"], {
        "0": "滑入 + 玻璃裂 + 碎片",
        "a": ("玻璃「啪」裂 + 碎片落下", {"crack@1123": [L("lab/battle_glass-crack1.mp3", -18)], "shards@1178": [L("lab/battle_glass-break2.mp3", -22, -0.45)]}),
        "b": ("牆壁碎開沙沙落", {"crack@1123": [L("lab/battle_wall-destruction1.mp3", -18)]}),
        "c": ("敲碎玻璃 + 掃落碎片", {"crack@1123": [L("mk/759", -18)], "shards@1178": [L("mk/172", -23, -0.45)]}),
    }),
    ("transform", "角色變身", ["transform@1247"], {
        "0": "玻璃閃光",
        "a": ("「鏘—」帥氣定格", {"transform@1247": [L("lab/anime_shakin1.mp3", -20)]}),
        "b": ("可愛閃亮", {"transform@1247": [L("lab/anime_cute-pose1.mp3", -21)]}),
        "c": ("遊戲升等音", {"transform@1247": [L("mk/2062", -22)]}),
    }),
    ("coins", "跳躍吃金幣", ["hero-jump@1269"] + COINS, {
        "0": "遊戲電子音(一枚比一枚高)",
        "a": ("經典吃金幣(一枚比一枚高)", up("ov/7c84a078", -21)),
        "b": ("遊戲贏得金幣(一枚比一枚高)", up("mk/2069", -21)),
        "c": ("跳躍 + 拿到錢(一枚比一枚高)", {"hero-jump@1269": [L("mk/2043", -24)], **up("lab/anime_item-get1.mp3", -21)}),
    }),
    ("enemy", "敵人落下", ["enemy-fall@1349", "enemy-land@1355"], {
        "0": "軟墊重落",
        "a": ("沉重「咚—」", {"enemy-land@1355": [L("lab/anime_don-1.mp3", -16)]}),
        "b": ("重低音踢擊", {"enemy-land@1355": [L("lab/battle_kick-heavy1.mp3", -16)]}),
        "c": ("巨人踩地", {"enemy-land@1355": [L("mk/3046", -16, 0, align="peak")]}),
    }),
    ("sword", "拔劍", ["sword-draw@1359"], {
        "0": "拔刀(厚)",
        "a": ("拔劍(響亮金屬)", {"sword-draw@1359": [L("lab/battle_sword-drawn1.mp3", -20)]}),
        "b": ("架刀「鏘」", {"sword-draw@1359": [L("lab/battle_katana-hold1.mp3", -20)]}),
        "c": ("快速出鞘", {"sword-draw@1359": [L("ov/18b4e02f", -20, 0, len=1.0)]}),
    }),
    ("slash", "劈砍", ["leap@1380", "slash-hit@1388", "enemy-puff@1399"], {
        "0": "揮動 + 刀切 + 打擊 + 布料散開",
        "a": ("「唰鏘」斬擊", {"slash-hit@1388": [L("lab/battle_sword-slash1.mp3", -13, -0.04)]}),
        "b": ("鋒利刀斬 + 打擊", {"slash-hit@1388": [L("lab/battle_katana-slash5.mp3", -14, -0.04), L("mk/2655", -16)]}),
        "c": ("揮劍 + 金屬斬 + 冒煙", {"leap@1380": [L("mk/2792", -20, 0.1, align="peak")], "slash-hit@1388": [L("mk/2160", -14)],
                               "enemy-puff@1399": [L("lab/anime_smoke1.mp3", -24)]}),
    }),
    ("swing", "3D 轉場", ["3d-swing@1464"], {
        "0": "一段風聲",
        "a": ("電影感隧道風聲", {"3d-swing@1464": [L("mk/1486", -21, -0.1, len=3.0)]}),
        "b": ("魔法光芒掃過", {"3d-swing@1464": [L("mk/2583", -22, -0.1, len=3.0)]}),
        "c": ("低沉長風聲", {"3d-swing@1464": [L("ov/eab8a6e2", -21, -0.2)]}),
    }),
    ("steam", "Steam 視窗", ["steam-win@1607", "steam-seat@1649"], {
        "0": "彈出 + 開關",
        "a": ("軟體開啟 + 選取", {"steam-win@1607": [L("mk/2578", -21)], "steam-seat@1649": [L("mk/2573", -21)]}),
        "b": ("開選單 + 確定鍵", {"steam-win@1607": [L("lab/button_menu1.mp3", -21)], "steam-seat@1649": [L("lab/button_decision1.mp3", -21)]}),
        "c": ("科技選取 + 玻璃滑入", {"steam-win@1607": [L("mk/3124", -21)], "steam-seat@1649": [L("mk/1527", -21)]}),
    }),
    ("box", "禮盒蓋上", ["box-up@1766", "game-in@1807", "lid@1822"], {
        "0": "滑動 + 書本闔上",
        "a": ("紙滑過 + 木板闔上", {"box-up@1766": [L("mk/1530", -24)], "lid@1822": [L("ov/f198cc08", -16)]}),
        "b": ("寶箱蓋子闔上", {"lid@1822": [L("ov/7fb87a27", -16, 0, align="peak", len=1.5)]}),
        "c": ("「啵」掉進去 + 木頭敲", {"game-in@1807": [L("lab/anime_cork-plug1.mp3", -22)], "lid@1822": [L("mk/2182", -16)]}),
    }),
    ("sparkle", "星星閃爍", [SPARK], {
        "0": "一聲玻璃閃光",
        "a": ("閃閃發亮", {SPARK: [L("lab/anime_shine1.mp3", -21)]}),
        "b": ("仙子魔法閃光", {SPARK: [L("mk/871", -21)]}),
        "c": ("一瞬「叮」光", {SPARK: [L("lab/anime_kira2.mp3", -21)]}),
    }),
    ("lockup", "結尾片名", ["lockup@1954"], {
        "0": "鐘響",
        "a": ("「鏘！」登場", {"lockup@1954": [L("lab/anime_jean1.mp3", -17)]}),
        "b": ("成就鈴聲", {"lockup@1954": [L("mk/600", -18)]}),
        "c": ("明亮簡報標題音", {"lockup@1954": [L("lab/anime_presentation-title1.mp3", -18)]}),
    }),
]
