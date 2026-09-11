#!/usr/bin/env python3
r"""
pick_lab.py — **매일 상위 N개를 뽑으면 성적이 얼마인가 (브리핑 그대로)** (2026-09-02 · 44차)

⚠️⚠️ **사용자 요구.**
   *"그래도 매일 아침마다 갱신되는 브리핑인데, 1주일에 3개 이상은 추천 종목이 나오는 게 좋지!"*

## 빈도와 성적은 맞바꾸는 관계다 (42차에서 이미 보인다)
```
                    연간     주당     코스피대비   승률    연도별
갭 −5%↓ · 소형        40건   0.8개   **+10.14%**  74%   11/14 ⭐
갭 −5~−2% · 소형    **439건** **8.4개**   +2.41%   56%   13/16 ⭐
갭 −5~−2% · 대형      63건   1.2개    +0.77%   54%   11/13 ⭐
```
⇒ **주 3개는 충분히 나온다.** 문제는 **그때 성적이 얼마인가**다.

## 그래서 **브리핑 구조 그대로** 잰다
```
매일 아침, 어제 볼린저 하단을 이탈한 종목들에 **점수**를 매기고 **상위 N개**만 뽑는다
N = 1 · 2 · 3 · 5 · 10  (하루)
⇒ 「주 3개」는 **하루 0.6개**다. 즉 상위 1개를 뽑되 문턱을 걸면 된다
```

## 점수를 무엇으로 매길까 — 다섯 가지를 견준다
```
① 갭 (낮을수록 높은 점수)     42차에서 가장 강했던 축
② 얼마나 빠졌나 (볼린저 위치)
③ RSI (낮을수록)
④ 거래대금 (클수록 — 살 수 있는 종목)
⑤ 갭 + RSI 합산
```
⚠️ 판정은 **코스피 뺀 값 + 승률 + 연도별 승수**. 왕복비용 0.26% · D+20 · 다음날 시가 매수.
⚠️ **연도별을 반드시 본다** — 오늘 두 번 그 함정에 빠졌다.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_보유 = 20
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def _주가():
    원 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                if 종 <= 0:
                    continue
                시 = float(v.get("시가") or 0) or 종
            except (TypeError, ValueError, KeyError):
                continue
            등 = v.get("등락률")
            try:
                등 = float(등) if 등 not in (None, "") else None
            except (TypeError, ValueError):
                등 = None
            if 등 is not None and abs(등) > 31.0:
                등 = None
            try:
                시총 = float(v.get("시총") or 0)
                대금 = float(v.get("거래대금") or 0)
            except (TypeError, ValueError):
                시총 = 대금 = 0.0
            하루[c] = (종, 시, 등, 시총, 대금)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 등, 시총, 대금) in 원[d].items():
            p, s = 앞원.get(c), 앞수.get(c)
            if p is None or s is None:
                수 = 종
            elif 등 is not None:
                수 = s * (1 + 등 / 100.0)
            else:
                r = 종 / p - 1 if p > 0 else 0.0
                수 = s * (1 + (0.0 if abs(r) > 0.32 else r))
            if 수 <= 0:
                수 = s if s and s > 0 else 종
            배 = 수 / 종 if 종 else 1.0
            앞원[c], 앞수[c] = 종, 수
            하루[c] = (수, 시 * 배, 시총, 대금)
        out[d] = 하루
    return out


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    ixv, 앞x = [], None
    for d in 날:
        x = (지수.get(d) or {}).get("KOSPI") or 앞x
        if x:
            앞x = x
        ixv.append(x)
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    # 후보: 볼린저 하단 이탈 첫날 → 다음날 시가 매수 · D+20
    후보 = {}      # i(신호일) -> [(갭, 볼위치, rsi, 대금, 크기, code, 수익, 초과)]
    앞상태 = {}
    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + _보유 >= len(날):
            앞상태 = {}
            continue
        오늘, 묶 = {}, []
        for code, v in 주가[d1].items():
            c1, _시, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            오늘[code] = 볼 <= -1.0
            앞 = 앞상태.get(code)
            if 앞 is None or not (볼 <= -1.0 and not 앞):
                continue
            나 = 주가[날[i + 1]].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝 or 나[1] <= 0 or c1 <= 0:
                continue
            갭 = (나[1] / c1 - 1) * 100
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            r = (끝[0] / 나[1] - 1) * 100 - _비용
            초 = r - ((ixv[i + 1 + _보유] / ixv[i + 1] - 1) * 100
                      if (ixv[i + 1] and ixv[i + 1 + _보유]) else 0)
            묶.append((갭, 볼, rsi, 나[3], _크기(시총), code, r, 초))
        앞상태 = 오늘
        if 묶:
            후보[i] = 묶
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일", flush=True)
    전체 = sum(len(v) for v in 후보.values())
    년수 = len(날) / 245
    print(f"  후보 {전체:,}건 · 신호 있는 날 {len(후보):,}일 "
          f"· 하루 평균 {전체/max(1,len(후보)):.1f}건 · **연 {전체/년수:.0f}건**", flush=True)

    점수법 = [
        ("① 갭 낮은 순", lambda x: -x[0]),
        ("② 많이 빠진 순", lambda x: -x[1]),
        ("③ RSI 낮은 순", lambda x: -x[2]),
        ("④ 거래대금 큰 순", lambda x: x[3]),
        ("⑤ 갭+RSI 합산", lambda x: -x[0] - (x[2] - 30) / 10),
    ]
    N들 = (1, 2, 3, 5, 10)

    print(f"\n  ══ 매일 상위 N개만 뽑으면 (전 종목) ══")
    print("     ⚠️ 「주 3개」 = 하루 0.6개다. N=1이면 주 5개가 나온다")
    print(f"    {'점수 방법':<16}" + "".join(f"{'N='+str(n):>20}" for n in N들))
    for 이름, 키 in 점수법:
        줄 = []
        for n in N들:
            a, 초 = [], []
            for i, 묶 in 후보.items():
                for x in sorted(묶, key=키, reverse=True)[:n]:
                    a.append(x[6])
                    초.append(x[7])
            if len(a) < 500:
                줄.append("-")
                continue
            승 = sum(1 for x in a if x > 0) / len(a) * 100
            줄.append(f"{st.mean(초):+.2f}({승:.0f}%) {len(a)/년수:.0f}/년")
        print(f"    {이름:<16}" + "".join(f"{x:>20}" for x in 줄))

    print(f"\n  ══ 소형만 · 매일 상위 N개 ══")
    후보소 = {i: [x for x in v if x[4] == "소형"] for i, v in 후보.items()}
    후보소 = {i: v for i, v in 후보소.items() if v}
    print(f"    {'점수 방법':<16}" + "".join(f"{'N='+str(n):>20}" for n in N들))
    for 이름, 키 in 점수법:
        줄 = []
        for n in N들:
            a, 초 = [], []
            for i, 묶 in 후보소.items():
                for x in sorted(묶, key=키, reverse=True)[:n]:
                    a.append(x[6])
                    초.append(x[7])
            if len(a) < 500:
                줄.append("-")
                continue
            승 = sum(1 for x in a if x > 0) / len(a) * 100
            줄.append(f"{st.mean(초):+.2f}({승:.0f}%) {len(a)/년수:.0f}/년")
        print(f"    {이름:<16}" + "".join(f"{x:>20}" for x in 줄))

    # 가장 좋은 조합의 연도별
    print(f"\n  ══ ⭐ 연도별 — 오늘 두 번 당한 함정이다 ══")
    print("     ⚠️ 문턱: 17해 중 **3분의 2** 이상 +")
    해들 = sorted({d[:4] for d in 날[250:]})
    for 이름, 키 in 점수법[:3]:
        for n in (1, 3):
            해별 = {}
            for i, 묶 in 후보소.items():
                y = 날[i][:4]
                for x in sorted(묶, key=키, reverse=True)[:n]:
                    해별.setdefault(y, []).append(x[7])
            칸, 플, 전 = [], 0, 0
            for y in 해들:
                a = 해별.get(y) or []
                if len(a) < 15:
                    칸.append((y, None))
                    continue
                m = st.mean(a)
                칸.append((y, m))
                전 += 1
                플 += 1 if m > 0 else 0
            if 전 < 10:
                continue
            전부 = [x for a in 해별.values() for x in a]
            print(f"\n  ── 소형 · {이름} · 상위 {n}개 "
                  f"(전체 {st.mean(전부):+.2f}% · 연 {len(전부)/년수:.0f}건) ──")
            print(f"    {'해':<6}" + "".join(f"{y[2:]:>7}" for y, _ in 칸))
            print(f"    {'초과':<6}" + "".join(
                (f"{m:>+7.1f}" if m is not None else f"{'-':>7}") for _, m in 칸))
            판 = "⭐ 문턱 통과" if 플 / 전 >= 2 / 3 else "❌ 문턱 미달"
            print(f"    ⇒ **{전}해 중 {플}해 + ({플/전*100:.0f}%)**  {판}")

    print("\n  읽는 법")
    print("    - 표의 값은 **코스피 대비 초과(승률%) 연간건수**다")
    print("    - N이 커질수록 건수는 늘고 성적은 떨어진다. **주 3개 = 하루 0.6개**")
    print("    - 점수 방법끼리 견줘 **무엇으로 줄 세울지**를 정한다")
    print("    - ⚠️ 연도별 문턱을 못 넘으면 성적이 좋아도 채택 못 한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
