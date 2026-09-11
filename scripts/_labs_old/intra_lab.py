#!/usr/bin/env python3
r"""
intra_lab.py — **장중에 그 값까지 내려오면 사도 되나** (2026-09-04 · 108차)

## ⚠️ 사용자 질문에서 나왔다
```
*"4,600원보다 싸게 열린다는 건 만약 4700원으로 열렸다가
  4600원으로 돌아와도 매수해야한다는 뜻이야?"*

지금 규칙은 **시가만** 본다. 시가가 조건에 맞을 때만 산다.
장중에 그 값까지 내려와도 안 산다 — **백테스트가 그렇게만 샀기 때문**이다.
```

## 왜 재볼 값어치가 있나
```
지금까지 실패한 여덟 가지는 전부 **「살 기회를 줄이는 조건」**이었다.
이건 **늘리는 쪽**이다. 방향이 반대라 통할 수 있다.
   지금       시가가 조건에 맞는 날만 산다 -> 사는 날 4.3%
   만약       장중 저가가 조건에 닿으면 산다 -> 기회가 는다
```
⚠️ 다만 80차: **시가가 그날 저가인 경우 61.2%**. 시가가 이미 가장 싼 경우가 많다

## 재는 것
```
A ⭐⭐ **장중 지정가** — 시가는 미달인데 **장중 저가**가 문턱에 닿으면 산다
     문턱을 시가 기준으로 계산해 그 값에 지정가를 걸어둔다
B 얼마나 늘어나나   사는 건수 · 사는 날
C 시가 매수와 견주기 (같은 종목을 시가에 샀다면)
D ⭐⭐ 자본 시뮬 · 앞뒤 분할 · 2025·26 제외
E ⚠️ **덜 유리한 값에 산다** — 장중 저가는 그날 가장 싼 값이라
     실제로는 그 값에 못 살 수도 있다. 불리하게 잡아 다시 잰다
```
⚠️ **상대갭은 시가로 정해진다** (시장 중앙갭도 시가 기준).
   장중에는 상대갭이 안 바뀐다 — 문턱 가격만 정해두고 기다리는 것이다
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

_비용 = 0.26
_시작 = "20160401"
_시드 = 5_000_000.0
_목표 = 20.0
_최대보유 = 40
확정 = {"갭": -3.5, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "비중": 0.20, "종목수": 4}


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    # 비[날][종목] = (시가/종가, 고가/종가, 거래대금, **저가/종가**)
    비, 갭표, 시장갭, 앞종, 원시, 원저 = {}, {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                저 = float(v.get("저가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                if min(종c, 시, 고, 저) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거, 저 / 종c)
            원시.setdefault(d8, {})[c] = 시
            원저.setdefault(d8, {})[c] = 저
            pv = 앞종.get(c)
            앞종[c] = 종c
            if pv and pv > 0:
                g = (시 / pv - 1) * 100
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

    # ── 후보를 모은다 (갭 조건 없이. 갭은 뒤에서 건다) ──
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
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 확정["시총"]:
                continue
            g = 하루갭.get(code)
            if g is None:
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
            if (c1 / sq[kk - 20] - 1) * 100 > 확정["낙"]:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o시 = (원시.get(다음) or {}).get(code)
            o저 = (원저.get(다음) or {}).get(code)
            앞종가 = 종계[code][kk]          # 어제 **수정** 종가
            if not b0 or not v0 or not o시 or not o저 or 앞종가 <= 0:
                continue
            상갭 = g - 시갭
            # ⚠️ **문턱 가격**: 상대갭이 딱 확정["갭"]가 되는 시가
            #    갭 = (시가/어제종가 − 1)*100 이고 상갭 = 갭 − 시갭 이므로
            #    문턱갭 = 확정["갭"] + 시갭  ->  문턱가 = 어제종가 * (1 + 문턱갭/100)
            문턱갭 = 확정["갭"] + 시갭
            문턱비 = 1 + 문턱갭 / 100
            시가비 = v0[0] * b0[0] / 앞종가        # 수정 기준 시가 / 어제 종가
            저가비 = v0[0] * b0[3] / 앞종가        # 수정 기준 **저가** / 어제 종가
            사건.append({
                "인": i + 1, "날": 다음, "code": code, "상갭": 상갭,
                "앞종가": 앞종가, "문턱비": 문턱비,
                "시가비": 시가비, "저가비": 저가비,
                "원시": o시, "원저": o저, "대금": b0[2],
                "i": i, "kk": kk,
            })
    print(f"  후보 {len(사건):,}건", flush=True)

    # ── 매수가를 정해 결과를 계산한다 ──
    def 결과내기(x, 매수비):
        """매수비 = 수정 기준 매수가 / 어제 종가"""
        매수 = x["앞종가"] * 매수비
        if 매수 <= 0:
            return None
        i = x["i"]
        for h in range(0, _최대보유 + 1):
            j = i + 1 + h
            if j >= len(날):
                return None
            vv = 주가[날[j]].get(x["code"])
            b2 = (비.get(날[j]) or {}).get(x["code"])
            if not vv or not b2:
                break
            # ⚠️ 첫날은 매수 이후의 고가만 쓸 수 있다고 보수적으로 본다
            if vv[0] * b2[1] >= 매수 * (1 + _목표 / 100):
                return (_목표 - _비용, j)
        j = i + 1 + _최대보유
        if j >= len(날):
            return None
        끝 = 주가[날[j]].get(x["code"])
        if not 끝:
            return None
        return ((끝[0] / 매수 - 1) * 100 - _비용, j)

    # 세 가지 방식
    #   ① 시가매수      시가비 <= 문턱비 일 때 **시가**에 산다 (지금 규칙)
    #   ② 장중지정가    시가비 > 문턱비 인데 저가비 <= 문턱비 면 **문턱가**에 산다
    #   ③ 둘 다
    방식 = {}
    for 라 in ("시가", "장중", "둘다", "장중불리"):
        방식[라] = {}
    for x in 사건:
        시통 = x["시가비"] <= x["문턱비"]
        장통 = (not 시통) and (x["저가비"] <= x["문턱비"])
        if 시통:
            r = 결과내기(x, x["시가비"])
            if r:
                방식["시가"].setdefault(x["인"], []).append(
                    {**x, "결과": r[0], "청산": r[1], "매수원": x["원시"]})
                방식["둘다"].setdefault(x["인"], []).append(
                    {**x, "결과": r[0], "청산": r[1], "매수원": x["원시"]})
        if 장통:
            r = 결과내기(x, x["문턱비"])
            if r:
                매수원 = x["앞종가"] and x["원시"] * (x["문턱비"] / x["시가비"])
                방식["장중"].setdefault(x["인"], []).append(
                    {**x, "결과": r[0], "청산": r[1], "매수원": 매수원})
                방식["둘다"].setdefault(x["인"], []).append(
                    {**x, "결과": r[0], "청산": r[1], "매수원": 매수원})
            # ⚠️ **불리하게**: 문턱가가 아니라 그날 저가보다 1% 비싸게 샀다고 본다
            불 = x["저가비"] * 1.01
            if 불 <= x["시가비"]:
                r2 = 결과내기(x, 불)
                if r2:
                    방식["장중불리"].setdefault(x["인"], []).append(
                        {**x, "결과": r2[0], "청산": r2[1],
                         "매수원": x["원저"] * 1.01})
    for 라 in ("시가", "장중", "둘다", "장중불리"):
        n = sum(len(v) for v in 방식[라].values())
        print(f"    {라:<10}{n:>6}건 · {len(방식[라]):>5}일")

    시i = [j for j, d in enumerate(날) if d >= _시작][0]

    def 시뮬(묶, 시작년=None, 끝년=None):
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
                    현금 += q["주수"] * q["매수원"] * (1 + q["결과"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(q["주수"] * q["매수원"] for q in 보유)
            for x in sorted(묶.get(i, []),
                            key=lambda z: z["상갭"])[:확정["종목수"]]:
                쓸 = min(평 * 확정["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["매수원"]) if x["매수원"] else 0
                if 주수 < 1 or 주수 * x["매수원"] > 현금:
                    continue
                현금 -= 주수 * x["매수원"]
                보유.append({**x, "주수": 주수})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["매수원"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        c = ((끝 / _시드) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        return {"끝": 끝, "연": c, "낙": 낙, "산": 산}

    def 표(r, 라, 폭=26):
        print(f"    {라:<{폭}}{r['끝']:>15,.0f}원{r['연']:>+9.2f}%"
              f"{r['낙']:>8.1f}%{r['산']:>7}건")

    머 = f"    {'전략':<26}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}"

    print(f"\n  ══ A **개별 거래 성적** ══")
    print(f"    {'방식':<14}{'표본':>8}{'도달률':>9}{'승률':>8}{'평균':>9}"
          f"{'중앙':>9}{'가장나쁨':>10}")
    for 라 in ("시가", "장중", "장중불리", "둘다"):
        a = [x for v in 방식[라].values() for x in v]
        if len(a) < 20:
            print(f"    {라:<14}{len(a):>7}건  표본 부족")
            continue
        r = sorted(x["결과"] for x in a)
        도 = sum(1 for x in a if x["결과"] > _목표 - _비용 - 1e-9) / len(a) * 100
        승 = sum(1 for x in a if x["결과"] > 0) / len(a) * 100
        print(f"    {라:<14}{len(a):>7}건{도:>8.1f}%{승:>7.1f}%"
              f"{st.mean(r):>+8.2f}%{st.median(r):>+8.2f}%{r[0]:>+9.2f}%")

    print(f"\n  ══ B·D ⭐⭐ **자본 시뮬** ══")
    print(머)
    기 = 시뮬(방식["시가"])
    표(기, "① 시가만 (지금 규칙)")
    표(시뮬(방식["장중"]), "② 장중만 (시가는 미달)")
    둘 = 시뮬(방식["둘다"])
    표(둘, "③ **둘 다**")
    # 둘다 + 장중을 불리하게
    합불 = {}
    for i, v in 방식["시가"].items():
        합불.setdefault(i, []).extend(v)
    for i, v in 방식["장중불리"].items():
        합불.setdefault(i, []).extend(v)
    표(시뮬(합불), "④ 둘 다 (장중은 불리하게)")

    print(f"\n  ══ 앞뒤 분할 (뒤 기간 연평균) ══")
    print(f"    {'분할':<10}{'① 시가만':>12}{'③ 둘 다':>12}{'④ 불리하게':>12}")
    for 컷 in ("2019", "2020", "2021", "2022"):
        a = 시뮬(방식["시가"], 시작년=str(int(컷) + 1))["연"]
        b = 시뮬(방식["둘다"], 시작년=str(int(컷) + 1))["연"]
        c3 = 시뮬(합불, 시작년=str(int(컷) + 1))["연"]
        print(f"    {컷}이후{'':<3}{a:>+11.1f}%{b:>+11.1f}%{c3:>+11.1f}%")

    print(f"\n  ══ ⚠️ **2025·26 제외** ══")
    print(머)
    표(시뮬(방식["시가"], 끝년="2024"), "① 시가만")
    표(시뮬(방식["둘다"], 끝년="2024"), "③ 둘 다")
    표(시뮬(합불, 끝년="2024"), "④ 둘 다 (불리하게)")

    print(f"\n  ══ C **얼마나 늘어나나** ══")
    시날 = set(방식["시가"])
    장날 = set(방식["장중"])
    print(f"    시가로 살 수 있던 날      {len(시날):>5}일")
    print(f"    장중에만 닿은 날         {len(장날 - 시날):>5}일")
    print(f"    합치면                 {len(시날 | 장날):>5}일 "
          f"(**{len(시날|장날)/max(1,len(시날))*100-100:+.0f}%**)")

    print("\n  읽는 법")
    print("    - ③④가 ①보다 커야 **장중 매수를 허용**한다")
    print("    - ④는 그날 저가보다 1% 비싸게 샀다고 본 것이다 (보수적)")
    print("    - ⚠️ 80차: 시가가 그날 저가인 경우 61.2% — 시가가 이미 싼 경우가 많다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
