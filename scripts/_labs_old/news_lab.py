#!/usr/bin/env python3
r"""
news_lab.py — **뉴스를 역산해서 시험한다** (2026-09-03 · 73차)

⚠️⚠️ **사용자 질문.** *"우리가 뉴스를 테스트 못 해보고 있잖아. 그래서
   1. 보유 데이터로 뉴스를 추측하거나 역산해서 테스트
   2. Yahoo·벤징가에서 수집
   3. 앞으로 브리핑 때 뉴스와 신호로 종목 추천
   위 셋 중 어떤 게 가능해?"*

## 확인한 것 (2026-09-03 실측)
```
FMP 뉴스 (news/stock · general-latest · press-releases)   **전부 402 유료**
Yahoo Finance                                          ✅ 된다 (한국 종목도 005930.KS)
                                                       ⚠️ 다만 **최근 것만** 준다
⇒ **과거 16.7년 뉴스로 백테스트는 불가능하다.**
⇒ 1번(역산)이 **과거 검증이 되는 유일한 방법**이다. 2번은 「오늘부터 쌓기」로만 쓸 수 있다
```

## 뉴스를 어떻게 역산하나
```
「뉴스가 났다」를 직접 못 재니 **대리 지표**를 만든다:
  거래대금배수   그날 거래대금 / 최근 20일 중앙값   ← 관심이 몇 배로 늘었나
  공시없는급변   |등락| 크고 **공시가 없는** 날      ← 공시로 설명 안 되면 뉴스일 가능성
  거래량+가격    둘이 같이 터진 날
⚠️ 정확히는 「뉴스」가 아니라 **「시장의 관심이 급증한 날」**이다.
   실용적으로는 같은 것을 잡는다. **그 한계를 결과에 명시한다.**
```

## 재는 것
```
A 관심 급증일이 실제로 얼마나 되나 (분포)
B **관심 급증 → 다음 20일 수익**  (그 자체가 신호가 되나)
C 공시 있는 급증 vs **공시 없는 급증** ← 후자가 「뉴스」에 가깝다
D ⭐ **우리 신호에 붙이면** 좋아지나 나빠지나
E 방향 — 급증하며 **오른** 날 vs **빠진** 날
```
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · D+20 · 비용 0.26% · 날짜 단위 · 연도별.
"""
import glob
import io
import json
import os
import re
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_보유 = 20
_시작 = "20160401"


def 재기(날별, 이름, 년수, 폭=36):
    if len(날별) < 8:
        print(f"    {이름:<{폭}}신호일 {len(날별)}일 — 부족")
        return None
    수 = [st.mean(v) for v in 날별.values()]
    승 = sum(1 for x in 수 if x > 0) / len(수) * 100
    해 = {}
    for d, v in 날별.items():
        해.setdefault(d[:4], []).append(st.mean(v))
    전 = 플 = 0
    for y, arr in 해.items():
        if len(arr) < 3:
            continue
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
    a = sorted(수)
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 8
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    종 = sum(len(v) for v in 날별.values())
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/max(0.1,년수):>7.1f}일{f'{플}/{전}':>8}{종:>8}건{별}")
    return st.mean(수)


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    날인 = {d: i for i, d in enumerate(날)}
    종계, 대계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            대계.setdefault(c, []).append(v[2])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # 공시가 난 (종목, 날) — dart-daily
    공시일 = {}
    공시커버 = set()
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            g = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = g.get("기준일")
        i = 날인.get(d8)
        if i is None:
            continue
        공시커버.add(i)
        for x in (g.get("챙길공시") or []):
            code = x.get("종목코드")
            if code:
                공시일.setdefault(code, set()).add(i)
    print(f"  공시 있는 날 {len(공시커버):,}일 · 공시 난 종목 {len(공시일):,}", flush=True)

    갭표, 시장갭, 앞종 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d["기준일"]] = 하루
        if len(하루) >= 100:
            시장갭[d["기준일"]] = st.median(list(하루.values()))

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

    # ── 후보: 관심 급증 지표를 담는다 ──
    후보 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        공시날인가 = i in 공시커버
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            g = 하루갭.get(code)
            if g is None:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            대열 = 대계[code]
            앞대 = 대열[k - 20:k]
            중앙 = st.median(앞대) if 앞대 else 0
            if 중앙 <= 0:
                continue
            배수 = 대금 / 중앙                     # ⭐ 관심 급증 지표
            sq = 종계[code]
            if sq[k - 1] <= 0:
                continue
            당일 = (c1 / sq[k - 1] - 1) * 100      # 그날 등락
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if sq[k - 20] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            # ⚠️ 「공시 없음」은 **공시를 받은 날에만** 말할 수 있다
            공시있나 = (i in (공시일.get(code) or set())) if 공시날인가 else None
            후보.append((다음, code, (끝[0] / 매수 - 1) * 100 - _비용,
                        배수, 당일, 볼, r20, g - 시갭, 공시있나,
                        재무값(code, d1)))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  후보 {len(후보):,}건 · {년수:.1f}년\n", flush=True)

    # ══ A 분포 ══
    배수들 = sorted(x[3] for x in 후보)
    print("  ══ A **관심 급증(거래대금 배수)** 분포 ══")
    print("     그날 거래대금 ÷ 최근 20일 중앙값")
    for q, 라 in ((50, "중앙"), (75, "상위25%"), (90, "상위10%"),
                  (95, "상위5%"), (99, "상위1%")):
        print(f"    {라:<10}{배수들[len(배수들)*q//100]:>8.2f}배")
    for 문 in (2, 3, 5, 10):
        n = sum(1 for x in 배수들 if x >= 문)
        print(f"    {문}배 이상: {n:,}건 ({n/len(배수들)*100:.2f}%)")

    def 모으기(cond):
        t = {}
        for x in 후보:
            if cond(x):
                t.setdefault(x[0], []).append(x[2])
        return t

    머 = (f"    {'조건':<36}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'건수':>9}")
    print("\n  ══ B **관심 급증 그 자체가 신호가 되나** ══")
    print(머)
    재기(모으기(lambda x: True), "전체 (기준선)", 년수)
    for 문 in (2, 3, 5, 10):
        재기(모으기(lambda x, m=문: x[3] >= m), f"거래대금 **{문}배 이상**", 년수)

    print("\n  ══ E 방향 — 급증하며 **오른** 날 vs **빠진** 날 ══")
    print(머)
    for 문 in (3, 5):
        재기(모으기(lambda x, m=문: x[3] >= m and x[4] >= 5),
             f"{문}배 급증 + 그날 **+5%↑**", 년수)
        재기(모으기(lambda x, m=문: x[3] >= m and x[4] <= -5),
             f"{문}배 급증 + 그날 **−5%↓**", 년수)

    print("\n  ══ C 공시 있는 급증 vs **공시 없는 급증** ══")
    print("     ⚠️ 공시 없이 터진 것이 **「뉴스」에 더 가깝다**")
    print(머)
    for 문 in (3, 5):
        재기(모으기(lambda x, m=문: x[3] >= m and x[8] is True),
             f"{문}배 급증 + **공시 있음**", 년수)
        재기(모으기(lambda x, m=문: x[3] >= m and x[8] is False),
             f"{문}배 급증 + **공시 없음**", 년수)
        재기(모으기(lambda x, m=문: x[3] >= m and x[8] is False and x[4] <= -5),
             f"  └ 공시 없이 **−5%↓**", 년수)
        재기(모으기(lambda x, m=문: x[3] >= m and x[8] is False and x[4] >= 5),
             f"  └ 공시 없이 **+5%↑**", 년수)

    print("\n  ══ D ⭐ **우리 신호에 붙이면** ══")
    print(머)

    def 우리(x):
        fm = x[9]
        return (bool(fm) and fm.get("잉여금비율", -9e9) >= 30
                and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0
                and x[7] <= -3 and x[5] <= -1.0 and x[6] <= -10)

    재기(모으기(우리), "우리 신호 (기준선)", 년수)
    for 문 in (1.5, 2, 3):
        재기(모으기(lambda x, m=문: 우리(x) and x[3] >= m),
             f"+ 거래대금 {m}배 이상" if False else f"+ 거래대금 **{문}배 이상**", 년수)
    재기(모으기(lambda x: 우리(x) and x[3] < 1.5), "+ 거래대금 1.5배 **미만**(조용)", 년수)
    재기(모으기(lambda x: 우리(x) and x[8] is False), "+ **공시 없음**", 년수)
    재기(모으기(lambda x: 우리(x) and x[8] is True), "+ 공시 있음", 년수)

    print("\n  읽는 법")
    print("    - ⚠️⚠️ 이건 **「뉴스」가 아니라 「관심 급증」**이다. 그 한계를 안고 읽는다")
    print("    - C의 **「공시 없는 급증」**이 뉴스에 가장 가깝다")
    print("    - D에서 붙여서 좋아지면 브리핑에 쓸 수 있다. **나빠지면 그것도 발견이다**")
    print("    - ⚠️ 공시는 3,203일뿐이다 — 「공시 없음」은 그 날들에서만 판정했다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
