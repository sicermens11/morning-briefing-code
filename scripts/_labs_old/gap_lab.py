#!/usr/bin/env python3
r"""
gap_lab.py — **102차. 시장 중앙갭을 지수로 대신할 수 있나** (2026-09-04)

## ⚠️⚠️ 실전 절차의 전제가 아직 안 검증됐다
```
우리 규칙의 핵심은 **상대갭** = 그 종목 갭 − **시장 전체 중앙 갭**
백테스트에서는 **전 종목(2,700개) 갭의 중앙값**을 썼다.

그런데 실전 08:50 동시호가에서는 **2,700개 갭을 계산할 수 없다.**
   -> 코스피·코스닥 **지수 예상 등락률**로 대신해야 한다
   -> **그게 중앙값과 같은가? 안 재봤다.**
```
⚠️ 다를 수 있는 이유
```
지수는 **시가총액 가중**이다. 삼성전자 하나가 크게 움직이면 지수가 끌려간다.
중앙값은 **종목 수 기준**이다. 작은 종목 1,350번째 값이다.
⇒ 대형주가 크게 움직인 날 둘이 크게 갈릴 수 있다
```

## 재는 것
```
A 얼마나 다른가        중앙갭 vs 지수갭 (코스피·코스닥·둘 합침)
B ⭐⭐ **바꿔서 시뮬**  지수갭으로 상대갭을 재면 성적이 얼마나 달라지나
C ⭐ **어긋난 날**     둘이 크게 갈린 날은 언제이고 그날 성적은
D 대안               지수 대신 **08:00 후보 종목들의 갭 중앙값**으로 하면
                    (후보 40개는 실전에서 볼 수 있다)
E ⚠️ 아예 안 빼면      상대갭 대신 **그냥 갭**을 쓰면 (52차 결론 재확인)
```
⚠️ 판정: **자본 시뮬** · 2025·26 제외 · 낙폭
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
확정 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 4}
_IDX = os.path.join(O._DATA, "index-daily")


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # ── 종목별 갭 · 시장 중앙갭 · 시총가중갭 ──
    비, 갭표, 중앙갭, 가중갭, 앞종, 원시 = {}, {}, {}, {}, {}, {}
    시총표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루, 무게 = {}, {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                # ⚠️ 필드 이름은 **시총**이다 ("시가총액"이 아니다)
                시총v = float(v.get("시총") or 0)
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
                    if 시총v > 0:
                        무게[c] = 시총v
        갭표[d8] = 하루
        if len(하루) >= 100:
            중앙갭[d8] = st.median(list(하루.values()))
            # 시총 가중 평균 갭 = **지수 갭에 가장 가까운 값**
            공 = [c for c in 하루 if c in 무게]
            총 = sum(무게[c] for c in 공)
            if 총 > 0:
                가중갭[d8] = sum(하루[c] * 무게[c] for c in 공) / 총

    # ── 실제 지수 갭 ──
    # ⚠️⚠️ **못 쓴다.** index-daily에는 **종가와 등락률만** 있고 **시가가 없다.**
    #    지수의 시가(갭)를 계산할 수 없다.
    #    ⇒ **시총가중갭**으로 대신한다. 지수가 시총 가중이니 가장 가까운 값이다
    지수갭 = {}
    for f in sorted(glob.glob(os.path.join(_IDX, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = d.get("기준일") or os.path.basename(f)[:8]
        항 = d.get("지수") or d.get("종목") or {}
        벌 = []
        if isinstance(항, dict):
            for k, v in 항.items():
                if not isinstance(v, dict):
                    continue
                이 = str(v.get("이름") or v.get("지수명") or k)
                if not any(w in 이 for w in ("코스피", "코스닥", "KOSPI",
                                             "KOSDAQ")):
                    continue
                if any(w in 이 for w in ("선물", "인버스", "레버", "TR",
                                         "채권", "배당")):
                    continue
                try:
                    종c = float(v.get("종가") or v.get("현재가") or 0)
                    시 = float(v.get("시가") or 0)
                except (TypeError, ValueError):
                    continue
                if 종c > 0 and 시 > 0:
                    벌.append((이, 시, 종c))
        if 벌:
            지수갭[d8] = 벌
    print(f"  지수 자료 {len(지수갭):,}일", flush=True)

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

    # ══ A 얼마나 다른가 ══
    공날 = [d for d in 날 if d >= _시작 and d in 중앙갭 and d in 가중갭]
    차 = [가중갭[d] - 중앙갭[d] for d in 공날]
    print(f"\n  ══ A **시총가중갭(지수 대용) vs 중앙갭** ══")
    print(f"     {len(공날):,}일")
    print(f"     차이(가중 − 중앙)  평균 {st.mean(차):+.3f}%p · "
          f"중앙 {st.median(차):+.3f}%p")
    print(f"     차이의 절대값      평균 {st.mean([abs(x) for x in 차]):.3f}%p")
    ab = sorted(abs(x) for x in 차)
    print(f"     |차이| 하위50% {ab[len(ab)//2]:.3f}%p · "
          f"상위10% {ab[int(len(ab)*0.9)]:.3f}%p · 최대 {ab[-1]:.3f}%p")
    큰 = sum(1 for x in 차 if abs(x) > 0.5)
    print(f"     **0.5%p 넘게 어긋난 날 {큰}일 ({큰/len(차)*100:.1f}%)**")
    큰1 = sum(1 for x in 차 if abs(x) > 1.0)
    print(f"     1.0%p 넘게 어긋난 날 {큰1}일 ({큰1/len(차)*100:.1f}%)")

    # ── 사건 모으기 (갭은 나중에 여러 기준으로 건다) ──
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작 or 다음 not in 중앙갭 or 다음 not in 가중갭:
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
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > 확정["볼"] or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > 확정["낙"]:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결과, 청산 = None, None
            for h in range(0, 확정["보유"] + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + 확정["목표"] / 100):
                    결과, 청산 = 확정["목표"] - _비용, j
                    break
            if 결과 is None:
                j = i + 1 + 확정["보유"]
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            사건.append({"인": i + 1, "날": 다음, "code": code, "결과": 결과,
                         "청산": 청산, "원시": o0, "대금": b0[2], "갭": g,
                         "중앙": 중앙갭[다음], "가중": 가중갭[다음],
                         "낙": 낙})
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"\n  후보 {len(사건):,}건", flush=True)

    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)

    def 시뮬(상갭함, 문, 라, 끝년=None, 폭=32):
        현금, 보유, 곡, 산 = _시드, [], [], 0
        for i in range(시i, len(날)):
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
            골 = [x for x in 묶.get(i, []) if 상갭함(x) <= 문]
            for x in sorted(골, key=상갭함)[:확정["종목수"]]:
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
            해.setdefault(날[시i + j][:4], []).append(곡[j])
        전 = 플 = 0
        for y in sorted(해):
            if len(해[y]) < 100:
                continue
            전 += 1
            플 += 1 if 해[y][-1] > 해[y][0] else 0
        print(f"    {라:<{폭}}{끝:>15,.0f}원{c:>+9.2f}%{낙:>8.1f}%{산:>7}건"
              f"{f'{플}/{전}':>8}")
        return 끝

    머 = (f"    {'기준':<32}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}"
          f"{'연도별':>8}")
    중앙식 = lambda x: x["갭"] - x["중앙"]      # noqa: E731
    가중식 = lambda x: x["갭"] - x["가중"]      # noqa: E731
    맨갭 = lambda x: x["갭"]                    # noqa: E731

    print(f"\n  ══ B ⭐⭐ **지수(시총가중)로 바꿔서 시뮬** ══")
    print(머)
    for 문 in (-3.0, -3.5):
        시뮬(중앙식, 문, f"⭐ 중앙갭 기준 {문}%p (백테스트)")
        시뮬(가중식, 문, f"시총가중갭 기준 {문}%p (실전 대용)")

    print(f"\n  ══ C **어긋난 날은 어떤가** ══")
    어긋 = [x for x in 사건 if abs(x["가중"] - x["중앙"]) > 0.5]
    안어 = [x for x in 사건 if abs(x["가중"] - x["중앙"]) <= 0.5]
    for a, 라 in ((어긋, "둘이 0.5%p 넘게 어긋난 날"),
                  (안어, "안 어긋난 날")):
        b = [x for x in a if 중앙식(x) <= -3.0]
        if len(b) < 20:
            continue
        도 = sum(1 for x in b if x["결과"] > 확정["목표"] - 0.3)
        print(f"    {라:<28}{len(b):>6}건  도달률 {도/len(b)*100:>5.1f}%  "
              f"평균 {st.mean([x['결과'] for x in b]):+.2f}%")
    # 두 기준이 서로 다른 판정을 내리는 건 수
    엇 = sum(1 for x in 사건
             if (중앙식(x) <= -3.0) != (가중식(x) <= -3.0))
    통 = sum(1 for x in 사건 if 중앙식(x) <= -3.0)
    print(f"    ⇒ 두 기준의 **판정이 갈리는 건 {엇}건** "
          f"(중앙 기준 통과 {통}건 대비 {엇/max(1,통)*100:.1f}%)")

    print(f"\n  ══ D ⭐ **후보들끼리의 갭 중앙값으로 하면** ══")
    print("     08:00 후보 40개는 실전에서 볼 수 있다. 그것들의 중앙값을 쓰면?")
    후중 = {}
    for i, 칸 in 묶.items():
        if len(칸) >= 3:
            후중[i] = st.median([x["갭"] for x in 칸])
    후보식 = lambda x: x["갭"] - 후중.get(x["인"], x["중앙"])   # noqa: E731
    print(머)
    for 문 in (-3.0, -3.5):
        시뮬(후보식, 문, f"후보들 갭 중앙값 기준 {문}%p")

    print(f"\n  ══ E ⚠️ **아예 안 빼면** (52차 결론 재확인) ══")
    print(머)
    for 문 in (-3.0, -4.0, -5.0):
        시뮬(맨갭, 문, f"그냥 갭 {문}% (시장 안 뺌)")

    print(f"\n  ══ F ⚠️ **2025·26 제외** ══")
    print(머)
    시뮬(중앙식, -3.0, "중앙갭 -3.0%p", 끝년="2024")
    시뮬(가중식, -3.0, "시총가중갭 -3.0%p", 끝년="2024")
    시뮬(후보식, -3.0, "후보 중앙값 -3.0%p", 끝년="2024")
    시뮬(맨갭, -3.0, "그냥 갭 -3.0%", 끝년="2024")

    print("\n  읽는 법")
    print("    - B에서 시총가중갭이 중앙갭과 비슷하면 **지수로 대신해도 된다**")
    print("    - D가 좋으면 **후보 40개만으로 시장 갭을 어림잡을 수 있다**")
    print("      (실전에서 가장 쉬운 방법이다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
