#!/usr/bin/env python3
r"""
tune2_lab.py — **94b차. 94차가 찾은 개선 세 가지가 진짜인가** (2026-09-03)

## 94차가 찾은 것 (2025·26 제외 · 돈은 늘고 낙폭은 안 나빠진 것)
```
지금 (시총 3천억↓ · 목표 +20% · 하루 2종목)   5,238만원  낙폭 -7.6%
-> 시총 **2천억↓**                        5,837만원  낙폭 -7.6%  **+11.4%**
-> 하루 **4종목**                         5,646만원  낙폭 -7.6%   +7.8%
-> 목표 **+25%**                         5,348만원  낙폭 **-7.0%**  +2.1%
```

## ⚠️ 94차의 걷기검증이 훨씬 낮았다 — **이게 더 정직한 숫자다**
```
8해 연평균 **+11.14%** · 흑자 7/8해 (2022년 -9.95%)
「연 +30%」는 **전 기간을 다 보고 문턱을 고른** 성적이다
```

## 여기서 재는 것
```
A 세 개선을 **하나씩·둘씩·셋 다** 조합 (전체 · 2025·26 제외)
B ⭐ **해마다 따로** — 어느 해에 좋고 어느 해에 나쁜가
C ⭐⭐ **걷기검증** — 고정값 vs 매년 다시 고르기
D ⚠️ **자산 규모별** (소액에서도 4종목이 되나 — 87차에서 1주 문제가 있었다)
E ⚠️ **무작위 문턱**과 견주기 — 개선이 우연 범위 안인가
```
"""
import glob
import io
import json
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
지금 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 3e11,
        "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 2}
_느 = {"갭": -2.0, "볼": -0.8, "낙": -5.0, "시총": 5e11}
_목표들 = (15.0, 20.0, 25.0, 30.0)
_보유들 = (20, 40, 60)


def 모으기():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종, 원시 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

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

    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= _느["시총"]:
                continue
            g = 하루갭.get(code)
            if g is None:
                continue
            상갭 = g - 시갭
            if 상갭 > _느["갭"]:
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > _느["볼"] or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > _느["낙"]:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결 = {}
            for 목 in _목표들:
                닿 = None
                for h in range(0, max(_보유들) + 1):
                    j = i + 1 + h
                    if j >= len(날):
                        break
                    vv = 주가[날[j]].get(code)
                    bb2 = (비.get(날[j]) or {}).get(code)
                    if not vv or not bb2:
                        break
                    if vv[0] * bb2[1] >= 매수 * (1 + 목 / 100):
                        닿 = (h, j)
                        break
                for 보 in _보유들:
                    if 닿 and 닿[0] <= 보:
                        결[(목, 보)] = (목 - _비용, 닿[1])
                    else:
                        j = i + 1 + 보
                        if j >= len(날):
                            continue
                        끝 = 주가[날[j]].get(code)
                        if not 끝:
                            continue
                        결[(목, 보)] = ((끝[0] / 매수 - 1) * 100 - _비용, j)
            if not 결:
                continue
            사건.append({"인": i + 1, "날": 다음, "갭": 상갭, "볼": 볼,
                         "낙": 낙, "시총": 시총, "원시": o0, "대금": b0[2],
                         "결": 결})
    return 사건, 날


def main():
    사건, 날 = 모으기()
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  후보 {len(사건):,}건\n", flush=True)

    def 시뮬(p, 끝년=None, 시드=5_000_000.0, 해별=False):
        묶 = {}
        for x in 사건:
            if (x["갭"] > p["갭"] or x["볼"] > p["볼"] or x["낙"] > p["낙"]
                    or x["시총"] >= p["시총"]):
                continue
            if (p["목표"], p["보유"]) not in x["결"]:
                continue
            묶.setdefault(x["인"], []).append(x)
        현금, 보유, 곡, 산 = 시드, [], [], 0
        for i in range(시i, len(날)):
            d = 날[i]
            if 끝년 and d[:4] > 끝년:
                break
            남 = []
            for q in 보유:
                if q["끝"] <= i:
                    현금 += q["주수"] * q["원시"] * (1 + q["r"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
            for x in sorted(묶.get(i, []), key=lambda z: z["갭"])[:p["종목수"]]:
                r, 끝i = x["결"][(p["목표"], p["보유"])]
                쓸 = min(평 * p["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({"주수": 주수, "원시": x["원시"], "r": r, "끝": 끝i})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = len(곡) / 245
        cagr = ((끝 / 시드) ** (1 / max(yr, 0.1)) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        if 해별:
            해 = {}
            for j in range(len(곡)):
                해.setdefault(날[시i + j][:4], []).append(곡[j])
            return 끝, cagr, 낙, 산, {y: (a[-1] / a[0] - 1) * 100
                                     for y, a in 해.items() if len(a) > 60}
        return 끝, cagr, 낙, 산, None

    def 줄(p, 라, 폭=32):
        끝, c, 낙, 산, _ = 시뮬(p)
        끝2, c2, 낙2, 산2, _ = 시뮬(p, 끝년="2024")
        print(f"    {라:<{폭}}{끝:>15,.0f}원{c:>+8.2f}%{낙:>7.1f}%{산:>6}"
              f"   {끝2:>13,.0f}원{c2:>+8.2f}%{낙2:>7.1f}%")
        return 끝2, 낙2

    머 = (f"    {'전략':<32}{'끝 자산':>16}{'연평균':>8}{'낙폭':>7}{'산 것':>6}"
          f"   {'25·26 제외':>13}{'연평균':>8}{'낙폭':>7}")

    print("  ══ A **세 개선을 하나씩·둘씩·셋 다** ══")
    print(머)
    기2, 기낙2 = 줄(지금, "지금 (3천억·+20%·2종목)")
    개 = {"시총": ("시총 2천억↓", {"시총": 2e11}),
          "종목수": ("하루 4종목", {"종목수": 4}),
          "목표": ("목표 +25%", {"목표": 25.0})}
    for k, (라, v) in 개.items():
        줄({**지금, **v}, f"+ {라}")
    import itertools
    for a, b in itertools.combinations(개, 2):
        줄({**지금, **개[a][1], **개[b][1]}, f"+ {개[a][0]} + {개[b][0]}")
    셋 = {**지금, **개["시총"][1], **개["종목수"][1], **개["목표"][1]}
    셋끝2, 셋낙2 = 줄(셋, "⭐ **셋 다**")

    print(f"\n  ══ B ⭐ **해마다 따로** — 어느 해에 좋고 나쁜가 ══")
    _, _, _, _, 해1 = 시뮬(지금, 해별=True)
    _, _, _, _, 해2 = 시뮬(셋, 해별=True)
    print(f"    {'해':<8}{'지금':>10}{'셋 다':>10}{'차이':>10}")
    이 = 0
    for y in sorted(해1):
        a, b = 해1[y], 해2.get(y, 0)
        이 += 1 if b > a else 0
        print(f"    {y:<8}{a:>+9.2f}%{b:>+9.2f}%{b-a:>+9.2f}%p")
    print(f"    ⇒ 셋 다가 이긴 해 **{이}/{len(해1)}**")

    print(f"\n  ══ C ⭐⭐ **걷기검증** — 고정값 vs 매년 다시 고르기 ══")
    해들 = [str(y) for y in range(2019, 2027)]
    for p, 라 in ((지금, "지금 값 고정"), (셋, "셋 다 적용 고정")):
        자, 곡 = 5_000_000.0, []
        for y in 해들:
            전, _, _, _, _ = 시뮬(p, 끝년=str(int(y) - 1))
            올, _, _, _, _ = 시뮬(p, 끝년=y)
            수 = (올 / 전 - 1) * 100 if 전 > 0 else 0
            자 *= (1 + 수 / 100)
            곡.append(수)
        c = ((자 / 5_000_000) ** (1 / len(해들)) - 1) * 100
        print(f"    {라:<20}연평균 {c:>+7.2f}%  흑자 "
              f"{sum(1 for x in 곡 if x>0)}/{len(해들)}해  "
              f"최악 {min(곡):+.2f}% ({해들[곡.index(min(곡))]}년)")
    print("    ⚠️ 94차의 「매년 다시 고르기」는 연평균 +11.14% · 7/8해였다")
    print("       고정값이 그보다 높으면, 그 문턱이 **전 기간을 보고 고른** 덕이다")

    print(f"\n  ══ D ⚠️ **자산 규모별** — 소액에서도 4종목이 되나 ══")
    print("     (87차에서 1주도 못 사는 문제가 있었다)")
    print(f"    {'자산':<14}{'지금':>16}{'셋 다':>16}{'지금 산 것':>10}"
          f"{'셋 다 산 것':>11}")
    for 시드 in (1_000_000, 3_000_000, 5_000_000, 10_000_000, 30_000_000):
        a, _, _, 산a, _ = 시뮬(지금, 시드=시드)
        b, _, _, 산b, _ = 시뮬(셋, 시드=시드)
        print(f"    {시드:>12,}원{a/시드:>15.1f}배{b/시드:>15.1f}배"
              f"{산a:>10}{산b:>11}")

    print(f"\n  ══ E ⚠️ **무작위 문턱과 견주기** ══")
    print("     문턱을 아무렇게나 골라도 이만큼 나오나 (200번)")
    random.seed(20260903)
    분포 = []
    for _ in range(200):
        p = {"갭": random.choice((-2.0, -2.5, -3.0, -4.0)),
             "볼": random.choice((-0.8, -1.0, -1.2)),
             "낙": random.choice((-5.0, -10.0, -15.0)),
             "시총": random.choice((1e11, 2e11, 3e11, 5e11)),
             "목표": random.choice(_목표들), "보유": random.choice(_보유들),
             "비중": random.choice((0.15, 0.20, 0.25)),
             "종목수": random.choice((1, 2, 3, 4))}
        끝2, _, _, _, _ = 시뮬(p, 끝년="2024")
        분포.append(끝2)
    분포.sort()
    def 위치(v):
        return sum(1 for x in 분포 if x < v) / len(분포) * 100
    print(f"     무작위 200가지 (2025·26 제외 끝 자산)")
    print(f"       가장 나쁨 {분포[0]:>13,.0f}원   중앙 {분포[len(분포)//2]:>13,.0f}원"
          f"   가장 좋음 {분포[-1]:>13,.0f}원")
    print(f"     지금 값   {기2:>13,.0f}원  →  상위 {100-위치(기2):.0f}%")
    print(f"     셋 다     {셋끝2:>13,.0f}원  →  상위 {100-위치(셋끝2):.0f}%")

    print("\n  읽는 법")
    print("    - B에서 셋 다가 **절반 넘는 해**에서 이겨야 진짜다")
    print("    - C의 걷기검증이 진짜 기대치다. 고정값 성적은 부풀려져 있다")
    print("    - E에서 상위 10% 안에 못 들면 그 문턱이 특별하지 않다는 뜻이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
