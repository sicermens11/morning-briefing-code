#!/usr/bin/env python3
r"""
brief_lab.py — **브리핑에 어떤 숫자를 보여줄 것인가** (2026-09-04 · 105차)

## ⚠️ 왜 재나 — 사용자 질문
```
*"과거도달율은 과거 사례를 봤을때 상승확율이야?"*

**아니다.** 「+20%에 닿아서 **목표가로 팔린** 비율」이다.
나머지는 40거래일 뒤 종가에 파는데 그중엔 오른 것도 내린 것도 있다.
⇒ **도달률**과 **승률(수익>0)**은 다른 숫자다. 둘 다 재서 어느 쪽을 쓸지 정한다
```

## 재는 것 — 조건 개수별로 (96차 5갈래)
```
표본 · **도달률**(+20% 닿음) · **승률**(수익>0) · 평균 · 중앙
최악 10% · 최악 1건 · 평균 보유일 · 걸친 해
```
⚠️ 브리핑에 쓸 숫자는 **사용자가 오해하지 않는 것**이어야 한다
"""
import bisect
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
_목표 = 20.0
_최대보유 = 40
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

    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c)
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
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 2e11:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -3.5:
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
            if (c1 - s20) / (2 * sd) > -1.0 or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > -10:
                continue
            b02 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b02 or not v0:
                continue
            매수 = v0[0] * b02[0]
            if 매수 <= 0:
                continue
            결과, 며칠 = None, _최대보유
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 며칠 = _목표 - _비용, max(1, h)
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과 = (끝[0] / 매수 - 1) * 100 - _비용
            갈래 = {
                "신호 깊이 (20일 −20%↓)": 낙 < -20,
                "금리 국면 (인하기)": 국면 == "인하",
                "한국 금리 (하락 중)": (한금 is not None and 한금 > 0.3),
                "시장 상황 (20일 −3%↓)": (시20 is not None and 시20 < -3),
                "크기 (시총 1,000억↓)": 시총 < 1e11,
            }
            사건.append({"날": 다음, "결과": 결과, "며칠": 며칠,
                         "도달": 결과 > _목표 - _비용 - 1e-9,
                         "점": sum(1 for x in 갈래.values() if x)})
    n = len(사건)
    print(f"  사건 {n:,}건 (상대갭 −3.5%p 기준)\n")

    print("  ══ ⭐⭐ **조건 개수별 — 도달률과 승률은 다른 숫자다** ══")
    print(f"    {'조건':<6}{'표본':>7}{'도달률':>9}{'승률':>8}{'평균':>9}"
          f"{'중앙':>9}{'최악10%':>9}{'가장나쁨':>10}{'평균보유':>9}{'해':>5}")
    for s in range(0, 6):
        a = [x for x in 사건 if x["점"] == s]
        if len(a) < 10:
            continue
        r = sorted(x["결과"] for x in a)
        도 = sum(1 for x in a if x["도달"]) / len(a) * 100
        승 = sum(1 for x in a if x["결과"] > 0) / len(a) * 100
        해 = len({x["날"][:4] for x in a})
        print(f"    {s}개{'':<3}{len(a):>6}건{도:>8.1f}%{승:>7.1f}%"
              f"{st.mean(r):>+8.2f}%{st.median(r):>+8.2f}%"
              f"{r[len(r)//10]:>+8.2f}%{r[0]:>+9.2f}%"
              f"{st.mean([x['며칠'] for x in a]):>8.1f}일{해:>4}해")
    a = 사건
    r = sorted(x["결과"] for x in a)
    도 = sum(1 for x in a if x["도달"]) / len(a) * 100
    승 = sum(1 for x in a if x["결과"] > 0) / len(a) * 100
    print(f"    {'전체':<6}{len(a):>6}건{도:>8.1f}%{승:>7.1f}%"
          f"{st.mean(r):>+8.2f}%{st.median(r):>+8.2f}%"
          f"{r[len(r)//10]:>+8.2f}%{r[0]:>+9.2f}%"
          f"{st.mean([x['며칠'] for x in a]):>8.1f}일"
          f"{len({x['날'][:4] for x in a}):>4}해")

    print(f"\n  ══ **왜 도달률과 승률이 다른가** ══")
    도달 = [x for x in 사건 if x["도달"]]
    안도 = [x for x in 사건 if not x["도달"]]
    print(f"    +20%에 닿아 목표가로 판 것   {len(도달):>5}건 "
          f"({len(도달)/n*100:.1f}%) — 전부 **+19.74%**로 확정")
    print(f"    40거래일 뒤 종가에 판 것     {len(안도):>5}건 "
          f"({len(안도)/n*100:.1f}%)")
    if 안도:
        r2 = sorted(x["결과"] for x in 안도)
        플 = sum(1 for x in 안도 if x["결과"] > 0)
        print(f"       그중 오른 것 {플}건 ({플/len(안도)*100:.1f}%) · "
              f"내린 것 {len(안도)-플}건")
        print(f"       평균 {st.mean(r2):+.2f}% · 중앙 {st.median(r2):+.2f}% · "
              f"가장 나쁨 {r2[0]:+.2f}%")
    print(f"\n    ⇒ **도달률 = 목표가로 팔린 비율** (그때 수익은 +19.74% 고정)")
    print(f"       **승률 = 결과가 0보다 큰 비율** (도달 + 안 닿았지만 오른 것)")
    print(f"       ⚠️ 브리핑에 「상승 확률」이라 쓰면 **틀린 말**이다")

    print(f"\n  ══ **최악은 얼마나 나쁜가** (브리핑에 같이 써야 한다) ══")
    print(f"    {'조건':<6}{'가장 나쁨':>11}{'최악 1%':>10}{'최악 5%':>10}"
          f"{'−10% 아래':>11}{'−20% 아래':>11}")
    for s in range(0, 6):
        a = [x for x in 사건 if x["점"] == s]
        if len(a) < 10:
            continue
        r = sorted(x["결과"] for x in a)
        아10 = sum(1 for x in r if x < -10) / len(r) * 100
        아20 = sum(1 for x in r if x < -20) / len(r) * 100
        print(f"    {s}개{'':<3}{r[0]:>+10.2f}%{r[max(0,len(r)//100)]:>+9.2f}%"
              f"{r[max(0,len(r)//20)]:>+9.2f}%{아10:>10.1f}%{아20:>10.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
