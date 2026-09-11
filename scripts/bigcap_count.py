#!/usr/bin/env python3
r"""
bigcap_count.py — **대형주 규칙이 성립할 수 있나 (개수부터)** (2026-09-07 신설)

## 왜 이것부터
```
과제③ 대형주 전용 규칙을 만들기 전에 **후보가 몇 개나 나오는지**를 알아야 한다.
지금 규칙은 「후보 40개를 뽑아 그 중앙갭으로 판단」이다.
대형주가 하루 1~2개밖에 안 나오면 **그 방식 자체가 성립하지 않는다**
   (중앙값을 내려면 최소 3개는 있어야 한다)
```

## 재는 것
```
A 규모 구간별 **종목 수**        그날 상장된 것 중 몇 개인가
B 규모 구간별 **후보 수**        08:00 조건(볼린저 -1.0 · 20일 -10%)을 통과한 것
C 후보가 3개 이상인 날의 비율     중앙갭을 낼 수 있는 날
D 재무 조건이 대형주에 맞나       잉여금 30%↑ · 부채 80%↓ · 흑자 를 몇 %가 통과하나
```
⚠️ 여기서는 **성적을 재지 않는다.** 「할 수 있나」만 본다.

쓰는 법:
    python scripts\bigcap_count.py
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_시작 = "20160401"
문턱들 = (
    ("후보", -1.0, -10.0),      # 지금 규칙
    ("완화A", -0.7, -5.0),
    ("완화B", -0.5, -3.0),
    ("완화C", -0.3, 0.0),      # 볼린저만
)
구간 = (
    ("초대형 10조↑", 10e12, 9e15),
    ("대형 1조~10조", 1e12, 10e12),
    ("중형 3천억~1조", 3e11, 1e12),
    ("중소형 2천억~3천억", 2e11, 3e11),
    ("소형 500억~2천억 (지금)", 5e10, 2e11),
)


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    def 재무값(code, d8):
        줄 = 재무.get(code)
        if not 줄:
            return None
        m = None
        for 적용, v in 줄:
            if 적용 <= d8:
                m = v
            else:
                break
        return m

    print("=" * 88)
    print("  대형주 규칙이 성립할 수 있나 — 개수부터")
    print("=" * 88)

    셈 = {라: {"종목": [], "재무통과": [], **{이: [] for 이, _, _ in 문턱들}} for 라, _, _ in 구간}
    본날 = 0
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        if 날[i + 1] < _시작:
            continue
        본날 += 1
        하루 = {라: {"종목": 0, "재무": 0, **{이: 0 for 이, _, _ in 문턱들}} for 라, _, _ in 구간}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 대금 < O._MIN_AMT:
                continue
            라 = None
            for n, 하, 상 in 구간:
                if 하 <= 시총 < 상:
                    라 = n
                    break
            if 라 is None:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            하루[라]["종목"] += 1
            fm = 재무값(code, d1)
            재무OK = bool(fm and fm.get("잉여금비율", -9e9) >= 30
                          and fm.get("부채비율", 9e9) <= 80
                          and fm.get("흑자") == 1.0)
            if 재무OK:
                하루[라]["재무"] += 1
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 재무OK:
                for 이, 볼문, 낙문 in 문턱들:
                    if 볼 <= 볼문 and 낙 <= 낙문:
                        하루[라][이] += 1
        for 라 in 셈:
            셈[라]["종목"].append(하루[라]["종목"])
            셈[라]["재무통과"].append(하루[라]["재무"])
            for 이, _, _ in 문턱들:
                셈[라][이].append(하루[라][이])

    print("")
    print("  본 거래일 " + format(본날, ",") + "일")
    for 이, 볼문, 낙문 in 문턱들:
        꼬 = "지금 규칙" if 이 == "후보" else ""
        print("")
        print("  == " + 이 + "  볼린저 " + str(볼문) + " · 20일 "
              + str(낙문) + "%  " + 꼬 + " ==")
        print("  " + "규모".ljust(22) + "종목수".rjust(8) + "재무통과".rjust(9) + "후보".rjust(8) + "3개↑날".rjust(9) + "10개↑날".rjust(9) + "40개↑날".rjust(9))
        for 라, _, _ in 구간:
            s = 셈[라]
            n = max(len(s[이]), 1)
            셋 = sum(1 for x in s[이] if x >= 3)
            열 = sum(1 for x in s[이] if x >= 10)
            마흔 = sum(1 for x in s[이] if x >= 40)
            print("  " + 라.ljust(22)
                  + format(st.mean(s["종목"]), ".0f").rjust(8)
                  + format(st.mean(s["재무통과"]), ".0f").rjust(9)
                  + format(st.mean(s[이]), ".1f").rjust(8)
                  + (format(셋 / n * 100, ".0f") + "%").rjust(9)
                  + (format(열 / n * 100, ".0f") + "%").rjust(9)
                  + (format(마흔 / n * 100, ".0f") + "%").rjust(9))

    print("\n  ── 읽는 법 ──")
    print("    · **후보 3개 이상인 날이 적으면** 중앙갭 방식이 성립하지 않는다")
    print("      (중앙값을 내려면 최소 3개가 있어야 한다)")
    print("    · **40개를 못 채우면** 「후보 40개」라는 지금 구조를 못 쓴다")
    print("      → 대형주는 후보 수를 줄이거나 다른 방식을 써야 한다")
    print("    · **재무통과**가 종목수보다 훨씬 적으면 재무 조건이")
    print("      그 규모에 안 맞는 것이다 (대형주는 부채비율이 높다)")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    sys.exit(main())
