#!/usr/bin/env python3
r"""
combo2_lab.py — **어떤 조건이 겹칠 때 오르나** (2026-09-02 · 46차)

⚠️⚠️ **사용자가 목표를 다시 못박았다.**
   *"이 테스트를 하는 건 여러 표본을 테스트해서 **어떤 조합 신호가 있을 때 종목이 상승**하고,
   그걸 캐치해서 브리핑에 반영하고, 브리핑 사용자가 그대로 했을 때 수익이 나게 하기 위함"*

## 🔴 오늘의 큰 구멍 — **신호를 거의 다 하나씩만 쟀다**
```
오늘 45개 시험에서 조합을 본 건 14차 한 번뿐이고 그것도 **초과수익 기준**이었다.
가장 복잡한 게 「볼린저 하단 + 갭 −5%↓」 **두 개짜리**다.
「볼하단 + 갭하락 + 수급유입 + 대형」처럼 **넷이 겹치는 것**은 한 번도 안 봤다.
```

## ⚠️ 판정 기준을 목표에 맞게 다시 세웠다
```
① **절대 수익 > 0**      (왕복비용 0.26% 차감)  ← 판정은 이것으로
② 승률                  몇 %가 오르나
③ **연도별 안정성**       특정 해에 몰리지 않았나 (오늘 세 번 당한 함정)
④ 매수는 **다음날 시가**   브리핑 보고 09:00~09:30에 사는 것
⑤ 코스피는 **참고로만** 옆에 표시. **기각 사유로 쓰지 않는다**
   ⚠️ 다만 절대만 보면 시장 상승분에 속으니(39차) 옆에는 둔다
⑥ 자본 시뮬은 **참고 지표로 내렸다** — 전 자산 운용 성적은 다른 문제다
```

## 재는 것 — 조건 여덟을 2·3개씩 겹친다
```
a 볼린저 하단 이탈(≤ −1.0)     b 갭 하락(다음날 시가 −2%↓)
c RSI 과매도(≤35)             d 거래량 3배↑
e 수급 유입(외국인+기관 순매수)   f 20일선 아래
g 최근 20일 −10%↓ (많이 빠짐)  h 신고가 근접(≥ 95%)
```
⚠️ 2개 조합 28개 + 3개 조합 56개 × 크기 3 = **252칸**. 다중검정이 크다
   → **연도별 문턱(3분의 2)**으로 방어한다. 표본 400건 미만은 버린다
"""
import glob
import io
import itertools
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_보유 = 20
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]
축이름 = {"a": "볼하단", "b": "갭−2%↓", "c": "RSI≤35", "d": "거래량3배",
          "e": "수급유입", "f": "20일선아래", "g": "20일−10%↓", "h": "신고가근접"}


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
                량 = float(v.get("거래량") or 0)
            except (TypeError, ValueError):
                시총 = 대금 = 량 = 0.0
            하루[c] = (종, 시, 등, 시총, 대금, 량)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 등, 시총, 대금, 량) in 원[d].items():
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
            하루[c] = (수, 시 * 배, 시총, 대금, 량)
        out[d] = 하루
    return out


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본, 수급 = O._지수(), O._기본(), O._수급()
    종계, 량계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            량계.setdefault(c, []).append(v[4])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    ixv, 앞x = [], None
    for d in 날:
        x = (지수.get(d) or {}).get("KOSPI") or 앞x
        if x:
            앞x = x
        ixv.append(x)
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    # 관측치: (해, 크기, 조건집합, 절대수익, 코스피뺀것)
    관측 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        fl = 수급.get(d1) or {}
        for code, v in 주가[d1].items():
            c1, _시, 시총, 대금, 량 = v
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
            나 = 주가[날[i + 1]].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝 or 나[1] <= 0:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            평량 = st.mean(량계[code][k - 20:k]) or 1
            f = fl.get(code) or {}
            순 = (f.get("외국인") or 0) + (f.get("기관") or 0)
            고 = max(sq[k - 250:k + 1])
            갭 = (나[1] / c1 - 1) * 100
            최근 = (c1 / sq[k - 20] - 1) * 100 if k >= 20 and sq[k - 20] > 0 else 0

            켠 = set()
            if 볼 <= -1.0:
                켠.add("a")
            if 갭 <= -2:
                켠.add("b")
            if rsi <= 35:
                켠.add("c")
            if 량 >= 평량 * 3:
                켠.add("d")
            if 순 > 0:
                켠.add("e")
            if c1 < s20:
                켠.add("f")
            if 최근 <= -10:
                켠.add("g")
            if 고 and c1 >= 고 * 0.95:
                켠.add("h")
            if not 켠:
                continue
            r = (끝[0] / 나[1] - 1) * 100 - _비용
            초 = r - ((ixv[i + 1 + _보유] / ixv[i + 1] - 1) * 100
                      if (ixv[i + 1] and ixv[i + 1 + _보유]) else 0)
            관측.append((d1[:4], _크기(시총), frozenset(켠), r, 초))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 관측 {len(관측):,}", flush=True)
    print(f"  관측 {len(관측):,}건", flush=True)

    축들 = list(축이름)
    년수 = len(날) / 245
    결과 = []
    for 개수 in (1, 2, 3):
        for 조합 in itertools.combinations(축들, 개수):
            s조 = set(조합)
            for g, _, _ in 크기표:
                a = [x for x in 관측 if x[1] == g and s조 <= x[2]]
                if len(a) < 400:
                    continue
                절 = [x[3] for x in a]
                초 = [x[4] for x in a]
                승 = sum(1 for x in 절 if x > 0) / len(절) * 100
                해별 = {}
                for x in a:
                    해별.setdefault(x[0], []).append(x[3])
                전 = 플 = 0
                for y, arr in 해별.items():
                    if len(arr) < 15:
                        continue
                    전 += 1
                    플 += 1 if st.mean(arr) > 0 else 0
                통과 = 전 >= 8 and 플 / 전 >= 2 / 3
                결과.append((st.mean(절), 승, st.mean(초), len(a), len(a) / 년수,
                             전, 플, 통과, "+".join(축이름[c] for c in 조합), g, 개수))

    print(f"\n  ══ 조건 조합 — **절대 수익**으로 판정 (다음날 시가 매수 · D+{_보유}) ══")
    print("     ⚠️ 코스피 대비는 **참고**다. 기각 사유로 쓰지 않는다")
    print(f"     칸 {len(결과)}개를 쟀다 · 연도별 문턱 3분의 2")
    for 개수 in (1, 2, 3):
        묶 = [x for x in 결과 if x[10] == 개수]
        묶.sort(reverse=True)
        print(f"\n  ── 조건 {개수}개 · 절대 수익 상위 12 ──")
        print(f"    {'조합':<34}{'크기':<6}{'절대':>9}{'승률':>7}"
              f"{'코스피대비':>11}{'연간':>8}{'연도별':>9}{'표본':>9}")
        for m, 승, 초, n, 연, 전, 플, 통과, 이름, g, _ in 묶[:12]:
            별 = "⭐" if (m > 0 and 통과 and 승 >= 50) else (
                "○" if (m > 0 and 통과) else ("  " if m > 0 else "❌"))
            print(f"    {이름:<34}{g:<6}{m:>+8.2f}%{승:>6.0f}%{초:>+10.2f}%"
                  f"{연:>7.0f}건{f'{플}/{전}':>9}{n:>9,}{별}")

    print(f"\n\n  ══ ⭐ **절대 수익 + · 승률 50%↑ · 연도별 통과** 를 모두 넘은 것 ══")
    산 = [x for x in 결과 if x[0] > 0 and x[1] >= 50 and x[7]]
    산.sort(reverse=True)
    if not 산:
        print("    ❌ 없다")
    print(f"    {'조합':<34}{'크기':<6}{'절대':>9}{'승률':>7}"
          f"{'코스피대비':>11}{'연간':>8}{'연도별':>9}{'표본':>9}")
    for m, 승, 초, n, 연, 전, 플, _, 이름, g, _c in 산[:25]:
        print(f"    {이름:<34}{g:<6}{m:>+8.2f}%{승:>6.0f}%{초:>+10.2f}%"
              f"{연:>7.0f}건{f'{플}/{전}':>9}{n:>9,}")
    if 산:
        총연 = sum(x[4] for x in 산[:10])
        print(f"\n    ⇒ 상위 10개를 다 쓰면 **연 {총연:.0f}건** (겹치는 종목 있음)")

    print("\n  읽는 법")
    print("    - **판정은 절대 수익**이다. 「그 종목을 사서 돈을 벌었나」")
    print("    - 조건이 겹칠수록 표본이 줄고 성적이 오르면 **조합이 값어치 있다**")
    print("    - 연도별을 못 넘으면 성적이 좋아도 **특정 해에 몰린 것**이다")
    print("    - ⚠️ 칸이 많아 우연히 좋은 게 섞인다. 연도별 문턱이 그걸 거른다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
