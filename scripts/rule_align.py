#!/usr/bin/env python3
r"""
rule_align.py — **규칙이 한 곳에서만 나오는지** 지킨다 (2026-09-11)

## 어떻게 바뀌었나
```
처음 판 (오전)  다섯 파일의 **소스에서 숫자를 긁어** 서로 같은지 봤다
                -> 정규식이 못 찾으면 `None` 이 되고 **조용히 통과**했다.
                   실제로 「볼린저 문턱」의 시험 칸이 그렇게 비어 있었다

지금 판 (오후)  `rule_def.py` 를 만들어 **숫자를 한 곳으로 모았다.**
                그러자 소스에는 숫자가 **없어졌다** — 긁을 게 없다.
                ⇒ 검사를 두 겹으로 바꾼다
```

## 두 겹
```
① 소스   다섯 파일이 `rule_def` 를 읽는가 · **숫자를 다시 적지 않았는가**
         (숫자가 되살아나는 것이 바로 어긋남의 씨앗이다)
② 산출물 **사용자가 실제로 보는 것**이 `rule_def` 와 같은가
         data/briefing-site.html   화면
         data/rule-cases.json      성적표
```

쓰는 법:
    python scripts\rule_align.py
    python scripts\rule_align.py --json    # selfcheck 가 읽는다
"""
import io
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rule_def as R  # noqa: E402

# 규칙을 읽어 써야 하는 **살아 있는 여섯**
# ⚠️⚠️ 「빈도」가 **빠져 있었다** (2026-09-11 오후에 찾음).
#    검사기에 없는 파일은 **영영 안 걸린다.** 그래서 how_often 만 옛 규칙
#    (섹터·시장 없음 · 시총 하한 500억) 으로 남아 화면에 나가고 있었다
_살아있는 = {
    "실전": "record_pick.py",
    "시험": "gate7_lab.py",
    "성적표": "build_rule_cases.py",
    "매수기록": "bought.py",
    "화면": "build_site.py",
    # ⭐ 퀀트 4장 본체가 2026-09-14 에 여기로 옮겨 갔다 — 규칙 문구는 이 파일이 만든다
    "퀀트화면": "quant_cards.py",
    "빈도": "how_often.py",
    # ⭐ 시험 판 셋 (2026-09-16). 사용자 「나중에 결정되어서 테스트에 반영 안 된 거 없어?」 →
    #    combo4 의 「지금 규칙」이 시총 500 · 후보 40 · 기존 갈래만으로 **얼어 있었다.**
    #    09-11 에 실전 다섯 곳을 넣을 때 시험 판은 빠졌다 [[checker-blind-to-unlisted-files]]
    "재료판": "combo4_lab.py",
    "반등판": "rebound_lab.py",
    "종목판": "percode_lab.py",
}

# ⚠️ 소스에 **다시 나타나면 안 되는** 숫자들. 나타났다는 건 누군가
#    `rule_def` 를 안 보고 손으로 적었다는 뜻이다
_되살아남 = [
    (r"_시총하한\s*=\s*3e10", "시총 하한 300억을 손으로 적었다"),
    (r"_시총상한\s*=\s*2e11", "시총 상한 2,000억을 손으로 적었다"),
    # ⚠️ 2026-09-16 — combo4 D절이 `500 <= x["시총억"] < 2000` 으로 얼어 있었다 (실전은 300)
    (r"500\s*<=\s*x\[\"시총억\"\]", "시총 하한 500억을 손으로 적었다 — `R.시총하한억` 이어야 한다"),
    (r"\(\"볼20\",\s*-1\.0,\s*\"낙20\",\s*-10\)", "지금 규칙(볼20 −1.0 · 낙20 −10)을 손으로 적었다"),
    (r"_볼문턱\s*=\s*-1\.0", "볼린저 −1.0σ를 손으로 적었다"),
    (r"_낙문턱\s*=\s*-10\.0", "20일 낙폭 −10%를 손으로 적었다"),
    (r"\(\(0\.5,\s*15", "나눔 (0.5, 15, …)을 손으로 적었다"),
    (r"\"상대갭\":\s*-3\.5", "상대갭 −3.5를 손으로 적었다"),
    (r"\"하루상한\":\s*4\b", "하루 4종목을 손으로 적었다"),
    # ⚠️ 2026-09-14 저녁 — build_rule_cases 가 `0.5 * 앞r + 0.5 * 뒤r` 로 박혀 있어
    #    몫들을 40:60 으로 바꿔도 성적표가 50:50 그대로였다. 비율은 R.몫들 에서만
    (r"0\.[0-9]+\s*\*\s*앞r\s*\+\s*0\.[0-9]+\s*\*\s*뒤r", "매도 몫 비율을 손으로 적었다"),
    # ⚠️ `omni_lab._MIN_MC` 는 **500억**이다. 실전 하한은 300억 —
    #    살아 있는 파일이 이걸 쓰면 실전이 사는 종목의 10% 가 빠진다
    (r"O\._MIN_MC", "시총 하한을 `O._MIN_MC`(500억)로 쓴다 — "
                     "`R.시총하한억`(300억) 이어야 한다"),
    # ⚠️⚠️ **후보수가 검사기 밖에 있었다** (2026-09-14 밤에 알았다).
    #    09-14 저녁에 40 -> 60 으로 바꿨는데, 옛 lab 여럿(chance·crosscheck·
    #    entry2·exit3·filter2)은 아직 `_후보수 = 40` 을 박아 두고 있다.
    #    살아 있는 파일에서만이라도 못 박는다 [[checker-blind-to-unlisted-files]]
    #    ⚠️ `$` 를 쓰면 안 된다 — `re.search` 를 플래그 없이 부르므로
    #       `$` 가 **파일 끝**에서만 맞는다. 숫자만 보고 가른다
    #       (`_후보수 = R.후보수` · `= int(os.environ…)` 는 안 걸린다)
    (r"_후보수\s*=\s*\d", "후보수를 손으로 적었다 — `R.후보수` 여야 한다"),
]


def _읽(경로):
    try:
        return io.open(경로, encoding="utf-8-sig").read()
    except Exception:  # noqa: BLE001
        return ""


def _벗김(글):
    r"""**주석을 지운 사본**. 되살아남 검사는 이걸로 본다

    ⚠️ 안 지우면 「고쳤다는 설명」이 「되살아났다」로 걸린다.
       실제로 `how_often.py` 의 주석 두 줄이 그렇게 걸렸다 (2026-09-11).
       가짜 경보가 쌓이면 **진짜 경보를 안 보게 된다**
    """
    벌 = []
    for 줄 in 글.splitlines():
        i = 줄.find("#")
        벌.append(줄 if i < 0 else 줄[:i])
    return "\n".join(벌)


def _수(글, 패턴, 바꿈=None):
    m = re.search(패턴, 글)
    if not m:
        return None
    v = float(m.group(1))
    return 바꿈(v) if 바꿈 else v


def 소스검사():
    """① 다섯 파일이 rule_def 를 읽는가 · 숫자를 되살리지 않았는가"""
    나쁨 = []
    for 라, 이름 in _살아있는.items():
        t = _읽(os.path.join(_BASE, "scripts", 이름))
        if not t:
            나쁨.append(f"{라}({이름}): 파일을 못 읽었다")
            continue
        if not re.search(r"import rule_def", t):
            나쁨.append(f"{라}({이름}): **`rule_def` 를 안 읽는다** — "
                        f"규칙을 손으로 적고 있다는 뜻이다")
        # ⚠️ **주석은 뺀다** — 고쳤다는 설명이 걸리면 안 된다
        _민 = _벗김(t)
        for pat, 말 in _되살아남:
            if re.search(pat, _민):
                나쁨.append(f"{라}({이름}): **{말}** — `rule_def` 에서 읽어라")
    return 나쁨


def 산출물검사():
    """② 사용자가 실제로 보는 것이 rule_def 와 같은가"""
    나쁨, 표 = [], []
    html = _읽(os.path.join(_BASE, "data", "briefing-site.html"))
    # ⭐⭐ **태그를 벗기고 맨글로 맞춘다** (2026-09-14).
    #    퀀트 4장이 quant_cards.py 로 옮겨 가면서 숫자가 `<b style="…">` 로 감싸져
    #    옛 정규식(`<b>(\d+)억`)이 **8개 항목을 조용히 「못 찾았다」** 로 흘렸다.
    #    마크업은 디자인이 바꾸는 것이라, 대조는 **글자만** 본다
    맨 = re.sub(r"<[^>]+>", "", html)
    민 = 맨.replace(",", "")
    # ⚠️ 매도 몫 이름은 50:50 이면 「반은」, 아니면 「30%는」 — 둘 다 받는다 (디자인 답 6)
    몫 = r"(?:반은|\d+%는)"

    def _분(s):
        h, m = s.split(":")
        return float(h) * 60 + float(m)
    잴것 = [
        ("화면 · 시총 하한", R.시총하한억, _수(민, r"시가총액 (\d+)억~")),
        ("화면 · 시총 상한", R.시총상한억, _수(민, r"시가총액 \d+억~(\d+)억")),
        ("화면 · 볼린저", R.볼린저문턱,
         _수(맨, r"볼린저 −([\d.]+)σ\)에 있다", lambda v: -v)),
        ("화면 · 20일 낙폭", R.낙폭20문턱,
         _수(맨, r"20거래일 동안 ([\d.]+)% 넘게", lambda v: -v)),
        ("화면 · 섹터 업종 수", float(len(R.섹터규칙)), _수(맨, r"등 (\d+)개 업종")),
        ("화면 · 지수 20일", R.지수낙20문턱,
         _수(맨, r"\(20일 −([\d.]+)% · 60일", lambda v: -v)),
        ("화면 · 지수 60일", R.지수낙60문턱,
         _수(맨, r"· 60일 −([\d.]+)%\)에는", lambda v: -v)),
        ("화면 · 상대갭", R.상대갭문턱,
         _수(맨, r"([\d.]+)%p 더 빠진 것만", lambda v: -v)),
        ("화면 · 하루 최대", float(R.하루최대종목), _수(맨, r"최대 (\d+)종목 지정가")),
        ("화면 · 앞 몫 목표", R.앞몫목표,
         _수(맨, rf"산 주식의 {몫} \+([\d.]+)%에 팔아")),
        ("화면 · 뒤 몫 목표", R.뒷몫목표,
         _수(맨, rf"나머지 {몫} \+([\d.]+)%까지")),
        ("화면 · 앞 몫 기한", float(R.앞몫기한),
         _수(맨, rf"앞의 {몫} (\d+)거래일")),
        ("화면 · 뒤 몫 기한", float(R.뒷몫기한),
         _수(맨, rf"뒤의 {몫} (\d+)거래일")),
        # ⭐ 판정 시각 — 킥커·리드·각주·3장이 rule_def.판정시각 하나를 쓰는지 (디자인 답 5)
        ("화면 · 판정 시각(분)", _분(R.판정시각),
         (lambda m: _분(m.group(1)) if m else None)(
             re.search(r"(\d\d:\d\d)에 5분, 여기서 살지", 맨))),
    ]
    try:
        rc = json.load(io.open(os.path.join(_BASE, "data", "rule-cases.json"),
                               encoding="utf-8-sig"))
        # 0 = 같다 · 1 = 다르다
        잴것.append(("성적표 · 규칙 문구", 0.0,
                     0.0 if rc.get("규칙") == R.한줄() else 1.0))
    except Exception:  # noqa: BLE001
        나쁨.append("성적표: rule-cases.json 을 못 읽었다")
    # ⭐ 빈도도 같은 규칙으로 세었는가 (2026-09-11 오후)
    try:
        rf = json.load(io.open(os.path.join(_BASE, "data",
                                            "rule-frequency.json"),
                               encoding="utf-8-sig"))
        잴것.append(("빈도 · 규칙 문구", 0.0,
                     0.0 if rf.get("규칙") == R.한줄() else 1.0))
    except Exception:  # noqa: BLE001
        나쁨.append("빈도: rule-frequency.json 을 못 읽었다")
    for 이름, 있어야, 실제 in 잴것:
        ok = 실제 is not None and abs(실제 - 있어야) < 1e-9
        표.append((이름, 있어야, 실제, ok))
        if 실제 is None:
            나쁨.append(f"{이름}: **못 찾았다** — 문구가 바뀌었는데 "
                        f"`rule_align` 이 안 따라왔다. 이대로 두면 "
                        f"그 칸은 **영영 검사되지 않는다**")
        elif not ok:
            나쁨.append(f"{이름}: rule_def 는 {있어야:g} 인데 "
                        f"**{실제:g}** 로 나갔다")
    return 나쁨, 표


def 보기():
    """selfcheck 가 부른다 — (곳, 줄, 어긋남)"""
    나1 = 소스검사()
    나2, 표 = 산출물검사()
    줄 = [(이름, [있어야, 실제], ok) for 이름, 있어야, 실제, ok in 표]
    return ["rule_def", "실제"], 줄, 나1 + 나2


def main():
    나1 = 소스검사()
    나2, 표 = 산출물검사()
    print("=" * 92)
    print("  규칙 대조 — 숫자는 `rule_def.py` 한 곳에만 있어야 한다")
    print("=" * 92)
    print("\n  ① 소스 — 다섯 파일이 rule_def 를 읽는가")
    if 나1:
        for z in 나1:
            print(f"     ❌ {z}")
    else:
        print("     ✅ 다섯 파일 모두 rule_def 를 읽고, "
              "숫자를 손으로 적은 곳이 없다")
    print("\n  ② 산출물 — 사용자가 **실제로 보는 것**이 같은가")
    print(f"     {'칸':<22}{'rule_def':>10}{'실제':>10}")
    for 이름, 있어야, 실제, ok in 표:
        s = f"{실제:>10g}" if 실제 is not None else f"{'못 찾음':>10}"
        print(f"     {'✅' if ok else '❌'} {이름:<20}{있어야:>10g}{s}")
    어 = 나1 + 나2
    print()
    if 어:
        print(f"  ❌ **어긋난 것 {len(어)}개**")
        for z in 어:
            print(f"     · {z}")
        return 1
    print("  ✅ **규칙이 한 곳에서만 나온다**")
    return 0


if __name__ == "__main__":
    if "--json" in sys.argv:
        _, _, _어 = 보기()
        print(json.dumps({"어긋남": _어}, ensure_ascii=False))
        sys.exit(1 if _어 else 0)
    sys.exit(main())
