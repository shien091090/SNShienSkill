"""Sound moments for the review page: one tab per moment, a few alternatives each.

"0" = the default PLAN layers of the moment's cues; "x" = silent. Every other option maps cue id -> layers and
replaces every cue of the moment. Cue ids are those of cues.base.json (tools/sfxcues.mjs).
Sources (see CREDITS.md): game/ = 接力吉尼 itself (CC0, Juhani Junkala 512 retro sounds), imp/ rpg/ = Kenney (CC0),
lab/ = 効果音ラボ, mk/ = Mixkit (id).
Game events (jump/land/death/clear) sit where the game itself played them while recording capture/l1 (events.json).
Layer options: align="peak" puts the loudest point on the cue (whooshes), len = max seconds kept, semi = pitch.
"""


def L(name, lufs, off=0.0, **o):
    return (name, lufs, off, o)


def each(name, lufs, cues, **o):
    return {c: [L(name, lufs, 0, **o)] for c in cues}


def up(name, lufs, cues, step=2, **o):
    return {c: [L(name, lufs + i * 0.4, 0, semi=step * i, **o)] for i, c in enumerate(cues)}


G = lambda n: f"game/sfx_{n}.wav"

# 開場與跳不上去: 角色的跳躍與落地 (遊戲當下真的發出的事件)
JUMP12 = ["jump@38", "jump@86", "jump@134", "jump@182", "jump@230"]
LAND12 = ["land@82", "land@130", "land@178", "land@226"]
# 切入正題: 第 3 代的跳躍、落地, 兩次踩頭, 碰旗
JUMP4 = ["jump@457", "jump@497", "jump@558"]
LAND4 = ["land@523", "land@584"]
STOMP = ["stomp1@492", "stomp2@553"]
CUTS = ["cut@852", "cut@927", "cut@1002", "cut@1077"]   # 合作解謎: 開門 / 升降台 / 鉤爪 / 翹翹板
CAPS = ["cap@282", "cap@861", "cap@1170"]               # 「去死一死」「合作解謎」「一起戰鬥?」字幕出現
TYPE_N, TYPE_DT = 7, 0.07                                # 「平台跳躍+解謎」7 個字, 每字 0.07 秒


def typed(name, lufs, **o):
    return {"type@21": [L(name, lufs - 0.0, i * TYPE_DT - 0.05, **o) for i in range(TYPE_N)]}


def jumps(j, jl, l, ll, js=JUMP12, ls=LAND12, **o):
    out = each(j, jl, js, **o)
    if l:
        out.update(each(l, ll, ls))
    return out


SLAM = 0.27  # 字幕砸下來、大震動的那一刻 (film.js K4: 0.05 + 0.22)

MOMENTS = [
    ("type", "開場字幕打字", ["type@21"], {
        "0": ("打字機一字一聲", typed("mk/1125", -24)),
        "a": ("RPG 對白「嗶嗶」一字一聲", typed("lab/button_message-display1.mp3", -27, len=0.12)),
        "b": ("遊戲選單音一字一聲 (遊戲原音)", typed(G("ui_page"), -27, len=0.15)),
        "c": ("鍵盤快打一整串", {"type@21": [L("lab/machine_keyboard-high-speed1.mp3", -24, -0.05, len=0.55)]}),
    }),
    ("jump12", "角色跳躍 (開場、跳不上去)", JUMP12 + LAND12, {
        "0": ("遊戲原音: 跳 + 落地", jumps(G("jump"), -24, G("land"), -27)),
        "a": ("卡通跳躍「咻」+ 著地「スタッ」", jumps("lab/anime_jump-anime1.mp3", -24, "lab/battle_landing1.mp3", -27)),
        "b": ("彈簧「啵嗯」(越跳越高)", up("lab/anime_boyon1.mp3", -25, JUMP12, step=1, len=0.6)),
        "c": ("遊戲原音: 只有跳, 一次比一次高 (越跳越急)", up(G("jump"), -24, JUMP12, step=1)),
    }),
    ("anger", "切特寫 + 生氣符號", ["zoom@120", "anger@141"], {
        "0": ("快速咻 + 怒氣「ゴゴゴ」", {"zoom@120": [L("mk/1464", -26, 0, align="peak")], "anger@141": [L("lab/anime_gogogogo1.mp3", -25, 0, len=1.8)]}),
        "a": ("衝擊一瞬「ジャン」", {"anger@141": [L("lab/anime_shock1.mp3", -22)]}),
        "b": ("鋼琴「ガーン」", {"anger@141": [L("lab/anime_shock2.mp3", -22, 0, len=1.6)]}),
        "c": ("快門 + 可愛「パッ」", {"zoom@120": [L("lab/machine_camera-shutter2.mp3", -24)], "anger@141": [L("lab/anime_pa1.mp3", -23)]}),
    }),
    ("fall", "跳坑", ["fall@384", "death@389"], {
        "0": ("遊戲原音: 死亡音", {"death@389": [L(G("death"), -20)]}),
        "a": ("卡通落下哨音 + 遊戲死亡音", {"fall@384": [L("mk/395", -24, -0.15, len=0.75)], "death@389": [L(G("death"), -21)]}),
        "b": ("「ヒューン」落下 + 「ドーン」", {"fall@384": [L("lab/anime_hyun1.mp3", -24, -0.2, len=0.7)], "death@389": [L("lab/anime_shock5.mp3", -20, 0, len=0.9)]}),
        "c": ("短哨音 + 遊戲失敗音", {"fall@384": [L("mk/406", -24, -0.1, len=0.6)], "death@389": [L(G("level_fail"), -22, 0, len=0.9)]}),
    }),
    ("slam", "「這就對了!」砸下來", ["slam@450"], {
        "0": ("「ザッ!」文字衝擊", {"slam@450": [L("lab/anime_text-impact1.mp3", -16, SLAM, align="peak")]}),
        "a": ("沉重「ドーン」", {"slam@450": [L("lab/anime_don-1.mp3", -16, SLAM, align="peak")]}),
        "b": ("預告片咻 + 重擊", {"slam@450": [L("mk/2918", -16, SLAM, align="peak")]}),
        "c": ("太鼓一齊「ドーン」", {"slam@450": [L("lab/anime_doon1.mp3", -16, SLAM, align="peak")]}),
    }),
    ("stomp", "踩頭往上跳 (切入正題)", JUMP4 + LAND4 + STOMP, {
        "0": ("遊戲原音: 跳 + 踩頭 + 落地", {**jumps(G("jump"), -24, G("land"), -27, JUMP4, LAND4), **each(G("head_stand"), -20, STOMP)}),
        "a": ("遊戲原音 + 踩頭多一聲「キラッ」", {**jumps(G("jump"), -24, G("land"), -27, JUMP4, LAND4),
                                         **{c: [L(G("head_stand"), -21), L("lab/anime_kira2.mp3", -23)] for c in STOMP}}),
        "b": ("遊戲跳躍 + 踩頭「ボヨン」", {**jumps(G("jump"), -24, None, 0, JUMP4), **each("lab/anime_boyon1.mp3", -20, STOMP, len=0.6)}),
        "c": ("街機吃金幣 (一次比一次高)", up("mk/216", -23, JUMP4[:1] + STOMP[:1] + JUMP4[1:2] + STOMP[1:] + JUMP4[2:], step=2, len=0.6)),
    }),
    ("clear", "碰到旗子過關", ["clear@637"], {
        "0": ("遊戲原音: 過關號角", {"clear@637": [L(G("level_clear"), -20, 0, len=1.1)]}),
        "a": ("「叮咚叮咚」答對", {"clear@637": [L("lab/anime_correct1.mp3", -21, 0, len=1.1)]}),
        "b": ("中古號角 (短)", {"clear@637": [L("mk/226", -21, 0, len=1.1)]}),
        "c": ("技能取得「キュイーン」", {"clear@637": [L("lab/button_decision10.mp3", -21, 0, len=1.1)]}),
    }),
    ("hud", "甩鏡到「第 3 代」", ["whip@708", "hud@732"], {
        "0": ("快速咻 + 遊戲翻頁音", {"whip@708": [L("mk/1490", -22, 0.3, align="peak")], "hud@732": [L(G("ui_page"), -22)]}),
        "a": ("短促咻 + 可愛「パッ」", {"whip@708": [L("mk/1464", -22, 0.3, align="peak")], "hud@732": [L("lab/anime_pa1.mp3", -22)]}),
        "b": ("揮拳風切 + 遊戲出生音", {"whip@708": [L("lab/battle_punch-real-swing3.mp3", -22, 0.3, align="peak")], "hud@732": [L(G("spawn"), -23, 0, len=0.8)]}),
        "c": ("輕快「咻啵」一聲", {"whip@708": [L("mk/3005", -21, 0.3, align="peak")]}),
    }),
    ("cuts", "解謎快切", CUTS, {
        "0": ("每段配該關的遊戲原音 (開門 / 升降台 / 鉤爪 / 翹翹板)", {
            CUTS[0]: [L(G("gate_open"), -22, 0.1)], CUTS[1]: [L(G("lift_move"), -24, 0.1)],
            CUTS[2]: [L(G("hook_whoosh"), -22, 0.1), L(G("hook_rise"), -25, 0.2)], CUTS[3]: [L(G("seesaw_launch"), -22, 0.1)]}),
        "a": ("每次切換一聲快門", each("lab/machine_camera-shutter2.mp3", -23, CUTS)),
        "b": ("每次切換一聲咻", each("mk/1464", -24, CUTS, align="peak")),
        "c": ("每次切換一聲遊戲翻頁音 (一次比一次高)", up(G("ui_page"), -23, CUTS, step=2)),
    }),
    ("k7", "連攜攻擊 (未來計畫)", ["dash@1167", "note@1173", "k7hit1@1211", "k7jump@1221", "k7hit2@1263", "combo@1285"], {
        "0": ("8-bit 遊戲音 (衝刺 / 撞擊 / 跳 / 踩扁 / COMBO)", {
            "dash@1167": [L(G("hook_whoosh"), -24)], "k7hit1@1211": [L(G("seesaw"), -21)], "k7jump@1221": [L(G("jump"), -24)],
            "k7hit2@1263": [L(G("death"), -20)], "combo@1285": [L(G("unlock"), -22, 0, len=1.0)]}),
        "a": ("格鬥遊戲 (小拳 → 必殺技命中)", {
            "dash@1167": [L("lab/battle_punch-real-swing1.mp3", -24, 0.2, align="peak")], "k7hit1@1211": [L("lab/battle_punch-middle2.mp3", -20)],
            "k7jump@1221": [L("lab/battle_jump1.mp3", -24)], "k7hit2@1263": [L("lab/battle_punch-high2.mp3", -18)],
            "combo@1285": [L("lab/button_decision10.mp3", -22, 0, len=1.0)]}),
        "b": ("卡通 (咻 / 卡通拳 / 跳 / 玩具槌「ピコッ」/ 閃亮)", {
            "dash@1167": [L("mk/1464", -24, 0.2, align="peak")], "k7hit1@1211": [L("mk/2149", -20)], "k7jump@1221": [L("lab/anime_jump-anime1.mp3", -24)],
            "k7hit2@1263": [L("lab/anime_pico-pico-hammer1.mp3", -19)], "combo@1285": [L("lab/anime_kira1.mp3", -22, 0, len=1.0)]}),
        "c": ("重擊 (打擊 / 重踢 / 文字衝擊)", {
            "k7hit1@1211": [L("lab/battle_blow2.mp3", -20)], "k7hit2@1263": [L("lab/battle_kick-heavy1.mp3", -18)],
            "combo@1285": [L("lab/anime_text-impact1.mp3", -20, 0, align="peak")]}),
    }),
    ("stamp", "兩個大標籤蓋章", ["stamp1@1411", "stamp2@1442", "pulse@1482"], {
        "0": ("「ペタッ」蓋章兩下", each("lab/anime_peta1.mp3", -15, ["stamp1@1411", "stamp2@1442"])),
        "a": ("和太鼓「ドン」「ドドン」", {"stamp1@1411": [L("lab/anime_drum-japanese1.mp3", -15, 0, align="peak", len=1.0)],
                                   "stamp2@1442": [L("lab/anime_drum-japanese2.mp3", -15, 0, align="peak", len=1.5)]}),
        "b": ("重拳 + 書本拍下 (兩下)", {c: [L("imp/impactPunch_heavy_002", -15), L("rpg/bookPlace2", -19)] for c in ["stamp1@1411", "stamp2@1442"]}),
        "c": ("低沉「ズン」兩下 + 最後一聲閃光", {**each("lab/anime_text-impact3.mp3", -16, ["stamp1@1411", "stamp2@1442"], align="peak"),
                                       "pulse@1482": [L("lab/anime_kira2.mp3", -22)]}),
    }),
    ("caps", "其他字幕出現 (去死一死 / 合作解謎 / 一起戰鬥?)", CAPS, {
        "0": ("每句一聲可愛「パッ」", each("lab/anime_pa1.mp3", -26, CAPS)),
        "a": ("每句一聲 RPG 對白音", each("lab/button_message-display3.mp3", -26, CAPS)),
        "b": ("每句一聲遊戲選單音", each(G("menu_move"), -26, CAPS)),
    }),
]

PLAN = {}
for _m in MOMENTS:
    PLAN.update(_m[3]["0"][1])
# libmix reads "0" as a plain label (its layers are PLAN)
for _i, _n, _c, _o in MOMENTS:
    _o["0"] = _o["0"][0]
