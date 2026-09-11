#!/usr/bin/env python3
r"""
cut_lab.py — **「조건 N개 미만은 안 산다」가 진짜인가** (2026-09-04 · 107차)

## 105차가 낸 1차 결과
```
조건    표본    도달률    평균     −10%아래
1개    50건   46.0%   +4.76%   **16.0%**   ← 나쁘다
2개   158건   74.1%  +14.52%     3.8%
3개   148건   77.7%  +16.04%     2.0%
4개   120건   91.7%  +18.10%     0.8%
⇒ 「2개 미만은 안 산다」가 맞아 보인다
```
⚠️ **그런데 살 기회를 줄이는 조건은 지금까지 일곱 번 다 졌다.**
   (88b·88c·89·91·97d·104·106)  도달률이 좋아져도 자본 시뮬에서 무너졌다.
   ⇒ **여기서도 자본 시뮬로 확인한다**

## 재는 것
```
A ⭐⭐ 자본 시뮬 — N개 미만 제외 (N=1·2·3·4)
B 앞뒤 분할 네 곳
C 2025·26 제외
D 낙폭·최악의 해
E ⚠️ **조건 개수가 몇 개인 날이 얼마나 되나** (실전에서 몇 번이나 걸리나)
```
⚠️ 조건 5갈래는 96차 것 (겹치지 않게 하나씩)
   신호 깊이(20일 -20%↓) · 금리 국면(인하기) · 한국 금리(하락 중) ·
   시장 상황(20일 -3%↓) · 크기(시총 1,000억↓)
"""
import bisect
import collections
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_시드 = 5_000_000.0
_목표 = 20.0
_최대보유 = 40
확정 = {"갭": -3.5, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "비중": 0.20, "종목수": 4}
_FR = os.path.join(O._DATA, "fred")
_ETF = os.path.join(O._DATA, "etf-krx")


def main():
    기준금리 = {}
    p = os.path.join(_FR, "AV_FEDFUNDS.json")
    if os.path.exists(p):
        기준금리 = json.load(io.open(p, encoding="utf-8-sig")).get("값") or {}
    k기 = sorted(기준금리)
    채권 = {}
    for f in sorted(glob.glob(os.path.join(_ETF, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        v = (d.get("종목") or {}).get("114460")
        if v:
            try:
                c2 = float(v.get("종가") or 0)
            except (TypeError, ValueError):
                continue
            if c2 > 0:
                채권[d.get("기준일") or os.path.basename(f)[:8]] = c2
    k채 = sorted(채권)
    if not 기준금리 or not 채권:
        print("  ⚠️⚠️ 국면 자료가 없다 (기준금리 또는 국고채 ETF). 멈춘다")
        return 2

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
            pv = 앞종.get(c)
            앞종[c] = 종c
            if pv and pv > 0:
                g = (시 / pv - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
    시장, 앞2 = {}, {}
    for d in 날:
        벌 = []
        for c, v in 주가[d].items():
            pv = 앞2.get(c)
            앞2[c] = v[0]
            if pv and pv > 0:
                벌.append((v[0] / pv - 1) * 100)
        if len(벌) >= 100:
            시장[d] = st.median(벌)
    누, 시누 = 100.0, {}
    for d in 날:
        누 *= (1 + 시장.get(d, 0) / 100)
        시누[d] = 누

    def 앞값(표, ks, d):
        j = bisect.bisect_left(ks, d)
        return 표[ks[j - 1]] if j > 0 else None

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
        r1 = 앞값(기준금리, k기, 다음)
        r0 = 앞값(기준금리, k기, 날[max(0, i - 62)])
        국면 = "모름"
        if r1 is not None and r0 is not None:
            차 = r1 - r0
            국면 = "인상" if 차 >= 0.20 else ("인하" if 차 <= -0.20 else "동결")
        b1 = 앞값(채권, k채, 다음)
        b0 = 앞값(채권, k채, 날[max(0, i - 20)])
        한금 = ((b1 / b0 - 1) * 100) if (b1 and b0 and b0 > 0) else None
        시20 = None
        if i >= 21 and 시누.get(날[i - 20]):
            시20 = (시누[d1] / 시누[날[i - 20]] - 1) * 100
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 확정["시총"]:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > 확정["갭"]:
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
            if (c1 - s20) / (2 * sd) > 확정["볼"] or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > 확정["낙"]:
                continue
            b02 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b02 or not v0 or not o0:
                continue
            매수 = v0[0] * b02[0]
            if 매수 <= 0:
                continue
            결과, 청산 = None, None
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 청산 = _목표 - _비용, j
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            점 = sum([낙 < -20, 국면 == "인하",
                      (한금 is not None and 한금 > 0.3),
                      (시20 is not None and 시20 < -3), 시총 < 1e11])
            사건.append({"인": i + 1, "날": 다음, "결과": 결과, "청산": 청산,
                         "원시": o0, "대금": b02[2], "상갭": g - 시갭, "점": 점})
    n = len(사건)
    print(f"  사건 {n:,}건\n")
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)

    def 시뮬(최소점, 시작년=None, 끝년=None):
        현금, 보유, 곡, 산 = _시드, [], [], 0
        시작i = 시i
        if 시작년:
            c2 = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = c2[0] if c2 else 시i
        for i in range(시작i, len(날)):
            if 끝년 and 날[i][:4] > 끝년:
                break
            남 = []
            for q in 보유:
                if q["청산"] <= i:
                    현금 += q["주수"] * q["원시"] * (1 + q["결과"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
            골 = [x for x in 묶.get(i, []) if x["점"] >= 최소점]
            for x in sorted(골, key=lambda z: z["상갭"])[:확정["종목수"]]:
                쓸 = min(평 * 확정["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({**x, "주수": 주수})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        c = ((끝 / _시드) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        해 = {}
        for j in range(len(곡)):
            해.setdefault(날[시작i + j][:4], []).append(곡[j])
        수 = {y: (a[-1] / a[0] - 1) * 100
              for y, a in 해.items() if len(a) > 60}
        return {"끝": 끝, "연": c, "낙": 낙, "산": 산, "해": 수}

    def 표(r, 라, 폭=26):
        print(f"    {라:<{폭}}{r['끝']:>15,.0f}원{r['연']:>+9.2f}%"
              f"{r['낙']:>8.1f}%{r['산']:>7}건")

    머 = f"    {'전략':<26}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}"

    print("  ══ A ⭐⭐ **자본 시뮬 — N개 미만은 안 산다** ══")
    print(머)
    기준 = 시뮬(0)
    표(기준, "전부 산다 (지금 규칙)")
    결 = {}
    for N in (1, 2, 3, 4):
        r = 시뮬(N)
        결[N] = r
        표(r, f"조건 {N}개 이상만")

    print(f"\n  ══ B **앞뒤 분할 네 곳** (뒤 기간 연평균) ══")
    print(f"    {'분할':<10}{'전부':>10}{'1개↑':>10}{'2개↑':>10}"
          f"{'3개↑':>10}{'4개↑':>10}")
    뒤 = collections.defaultdict(list)
    for 컷 in ("2019", "2020", "2021", "2022"):
        줄 = [시뮬(0, 시작년=str(int(컷) + 1))["연"]]
        for N in (1, 2, 3, 4):
            줄.append(시뮬(N, 시작년=str(int(컷) + 1))["연"])
        for k2, v2 in zip(["0"] + [str(x) for x in (1, 2, 3, 4)], 줄):
            뒤[k2].append(v2)
        print(f"    {컷}이후{'':<3}" + "".join(f"{x:>+9.1f}%" for x in 줄))
    print(f"    {'평균':<10}" + "".join(
        f"{st.mean(뒤[k2]):>+9.1f}%" for k2 in ["0", "1", "2", "3", "4"]))

    print(f"\n  ══ C ⚠️ **2025·26 제외** ══")
    print(머)
    표(시뮬(0, 끝년="2024"), "전부 산다")
    for N in (1, 2, 3, 4):
        표(시뮬(N, 끝년="2024"), f"조건 {N}개 이상만")

    print(f"\n  ══ D **최악의 해** ══")
    print(f"    {'전략':<20}{'가장 나쁜 해':>28}")
    for N, r in [(0, 기준)] + list(결.items()):
        나 = sorted(r["해"].items(), key=lambda z: z[1])[:3]
        라 = "전부" if N == 0 else f"{N}개 이상"
        print(f"    {라:<20}" + " · ".join(f"{y} {v:+.1f}%" for y, v in 나))

    print(f"\n  ══ E **실전에서 몇 번이나 걸리나** ══")
    c2 = collections.Counter(x["점"] for x in 사건)
    print(f"    {'조건 개수':<12}{'건수':>8}{'비율':>8}{'누적(그 이상)':>14}")
    누 = n
    for s in range(0, 6):
        print(f"    {s}개{'':<9}{c2.get(s,0):>7}건{c2.get(s,0)/n*100:>7.1f}%"
              f"{누:>12}건")
        누 -= c2.get(s, 0)

    print("\n  읽는 법")
    print("    - A·C에서 **끝 자산이 「전부 산다」보다 커야** 조건을 건다")
    print("    - 살 기회를 줄이는 조건은 지금까지 **일곱 번 다 졌다**")
    print("    - E에서 남는 건수가 너무 적으면 실전에서 쓸 수 없다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
