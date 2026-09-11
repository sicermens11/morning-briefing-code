#!/usr/bin/env python3
r"""
final_lab.py — **95차. 최종 통합 검증** (2026-09-03)

## 지금까지 확정된 것
```
주력  잉여금비율>=30% · 부채비율<=80% · 흑자 · 소형주
      + 상대갭 -3%p + 볼린저 -1.0σ + 20일 -10% + 관리종목·SPAC 제외
      + 다음날 시가 매수 · +20% 지정가 · 최대 D+40 · 손절 없음
      94b 개선 제안: **시총 3천억 -> 2천억 · 하루 2종목 -> 4종목**
보조  미국 반도체 아무거나 -2%↓ -> 다음날 SK하이닉스 · 10일 보유 (93차)
      ⇒ 자산 1억부터 값을 한다
맥락  금리 인상기 도달률 65.2% · 인하기 87.8% (91차) — 규칙이 아니라 신뢰도 표시
```

## ⚠️⚠️ 여기서 던지는 질문 — **끼워맞춘 게 아닌가**
```
94b가 남긴 두 사실이 서로 반대 방향을 가리킨다:
   ⚠️ 매년 문턱을 다시 고르면 연 +11.14%뿐이다
   ⭐ 그런데 **무작위 문턱 200개가 하나도 빠짐없이 흑자**였다 (최악 8.8년 +57%)
⇒ 「문턱이 특별해서 되는 게 아니라 **전략의 뼈대가 되는 것**」일 가능성이 크다
   그걸 여기서 확인한다
```

## 재는 것
```
A ⭐⭐ **앞으로 고르고 뒤로 검증** — 2016~2020으로 문턱 고르고 **2021~2026을 산다**
     (이게 가장 정직한 판이다. 미래를 안 보고 고른 값으로 미래를 산다)
B 순열검정 — **신호 날짜를 뒤섞어** 같은 성적이 나오나 (500번)
C 무작위 종목 — 신호 종목 대신 **아무 종목이나** 사면 (500번)
D 비용을 올려보면 — 0.26% · 0.5% · 1.0% · 2.0%
E 미끄러짐 — 시가보다 **불리하게** 사면 (+0.3% · +0.5% · +1.0%)
F 최악의 해·최악의 구간
G 최종 요약
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

_시작 = "20160401"
_시드 = 5_000_000.0
지금 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 3e11,
        "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 2}
개선 = {**지금, "시총": 2e11, "종목수": 4}
_느 = {"갭": -2.0, "볼": -0.8, "낙": -5.0, "시총": 5e11}
_목표들 = (15.0, 20.0, 25.0, 30.0)
_보유들 = (20, 40, 60)


def main():
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

    def 결과내기(i, code, 매수, 목들=_목표들, 보들=_보유들, 비용=0.26):
        결 = {}
        for 목 in 목들:
            닿 = None
            for h in range(0, max(보들) + 1):
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
            for 보 in 보들:
                if 닿 and 닿[0] <= 보:
                    결[(목, 보)] = (목 - 비용, 닿[1])
                else:
                    j = i + 1 + 보
                    if j >= len(날):
                        continue
                    끝 = 주가[날[j]].get(code)
                    if not 끝:
                        continue
                    결[(목, 보)] = ((끝[0] / 매수 - 1) * 100 - 비용, j)
        return 결

    # ── 후보 모으기 (느슨하게) ──
    사건 = []
    후보풀 = {}      # 날짜 -> 그날 살 수 있던 **모든** 종목 (무작위 견줌용)
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
        전체 = []
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 5e11:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            전체.append((code, v0[0] * b0[0], o0, b0[2]))
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
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결 = 결과내기(i, code, 매수)
            if not 결:
                continue
            사건.append({"인": i + 1, "날": 다음, "code": code, "갭": 상갭,
                         "볼": 볼, "낙": 낙, "시총": 시총, "원시": o0,
                         "대금": b0[2], "결": 결})
        if 전체:
            후보풀[i + 1] = 전체
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  신호 {len(사건):,}건 · 후보풀 {len(후보풀):,}일\n", flush=True)

    def 시뮬(p, 목록=None, 시작년=None, 끝년=None, 시드=_시드, 슬립=0.0):
        묶 = {}
        for x in (목록 if 목록 is not None else 사건):
            if (x["갭"] > p["갭"] or x["볼"] > p["볼"] or x["낙"] > p["낙"]
                    or x["시총"] >= p["시총"]):
                continue
            if (p["목표"], p["보유"]) not in x["결"]:
                continue
            묶.setdefault(x["인"], []).append(x)
        현금, 보유, 곡, 산 = 시드, [], [], 0
        시작i = 시i
        if 시작년:
            c2 = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = c2[0] if c2 else 시i
        for i in range(시작i, len(날)):
            if 끝년 and 날[i][:4] > 끝년:
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
                r -= 슬립       # ⚠️ 시가보다 불리하게 샀다고 치는 몫
                쓸 = min(평 * p["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({"주수": 주수, "원시": x["원시"], "r": r, "끝": 끝i})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        cagr = ((끝 / 시드) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        return 끝, cagr, 낙, 산, 곡

    # ══ A 앞으로 고르고 뒤로 검증 ══
    print("  ══ A ⭐⭐ **2016~2020으로 문턱을 고르고 2021~2026을 산다** ══")
    print("     ⚠️ 미래를 안 보고 고른 값으로 미래를 사는 것. 가장 정직한 판이다")
    축들 = {"갭": (-2.0, -2.5, -3.0, -4.0, -5.0),
            "볼": (-0.8, -1.0, -1.2, -1.5),
            "낙": (-5.0, -10.0, -15.0, -20.0),
            "시총": (1e11, 2e11, 3e11, 5e11),
            "목표": (15.0, 20.0, 25.0, 30.0),
            "보유": (20, 40, 60),
            "비중": (0.15, 0.20, 0.25),
            "종목수": (1, 2, 3, 4)}
    골 = dict(지금)
    for _ in range(3):
        for 축, 값들 in 축들.items():
            최 = None
            for v in 값들:
                q = dict(골)
                q[축] = v
                끝, _, _, _, _ = 시뮬(q, 끝년="2020")
                if 최 is None or 끝 > 최[0]:
                    최 = (끝, v)
            골[축] = 최[1]
    print(f"     2016~2020만 보고 고른 값:")
    print(f"       갭 {골['갭']:.1f}%p · 볼린저 {골['볼']:.1f}σ · 20일 {골['낙']:.0f}% "
          f"· 시총 {골['시총']:.0e} · 목표 +{골['목표']:.0f}% · D+{골['보유']} "
          f"· 비중 {골['비중']:.0%} · {골['종목수']}종목")
    print(f"\n    {'전략':<26}{'2016~2020 (고른 판)':>22}{'2021~2026 (검증)':>22}"
          f"{'연평균':>9}{'낙폭':>8}")
    for p, 라 in ((지금, "지금 값"), (개선, "94b 개선안"), (골, "⭐ 앞으로 고른 값")):
        a, ac, an, _, _ = 시뮬(p, 끝년="2020")
        b, bc, bn, _, _ = 시뮬(p, 시작년="2021")
        print(f"    {라:<26}{a:>15,.0f}원{ac:>+7.1f}%{b:>15,.0f}원{bc:>+7.1f}%"
              f"{bc:>9.2f}%{bn:>8.1f}%")
    print("     ⚠️ 「앞으로 고른 값」이 뒤 기간에서 지금 값보다 나쁘면,")
    print("        **문턱 최적화가 소용없다**는 뜻이다 (그래도 전략은 살아있다)")

    # ══ B 순열검정 ══
    print(f"\n  ══ B **순열검정** — 신호 **날짜를 뒤섞으면** (300번) ══")
    print("     같은 종목·같은 수를 사되 **날짜만 아무렇게나**")
    random.seed(20260903)
    실제, _, _, _, _ = 시뮬(개선)
    인들 = sorted(후보풀)
    분포 = []
    for _ in range(300):
        섞 = []
        for x in 사건:
            섞.append({**x, "인": random.choice(인들)})
        v, _, _, _, _ = 시뮬(개선, 목록=섞)
        분포.append(v)
    분포.sort()
    이 = sum(1 for v in 분포 if v >= 실제)
    print(f"     실제        {실제:>15,.0f}원")
    print(f"     섞은 것 중앙  {분포[len(분포)//2]:>15,.0f}원")
    print(f"     섞은 것 최고  {분포[-1]:>15,.0f}원")
    print(f"     섞은 게 이긴 횟수 {이}/300  →  **p = {이/300:.4f}**")

    # ══ C 무작위 종목 ══
    print(f"\n  ══ C **무작위 종목** — 같은 날 **아무 종목이나** 사면 (300번) ══")
    쓸인 = sorted({x["인"] for x in 사건})
    # ⚠️⚠️ 300번마다 결과를 새로 계산하면 몇 시간 걸린다.
    #    -> 각 날의 후보 중 **12종목만 미리 뽑아 결과를 한 번만** 계산해 두고
    #       거기서 골라 쓴다 (2026-09-03 고침)
    미리 = {}
    for i in 쓸인:
        풀 = 후보풀.get(i) or []
        if not 풀:
            continue
        칸 = []
        for code, 매수, o0, 대금 in random.sample(풀, min(12, len(풀))):
            r = 결과내기(i - 1, code, 매수,
                         목들=(개선["목표"],), 보들=(개선["보유"],))
            if r:
                칸.append({"인": i, "갭": -99, "볼": -99, "낙": -99,
                           "시총": 0, "원시": o0, "대금": 대금, "결": r})
        if 칸:
            미리[i] = 칸
    print(f"     (미리 계산한 무작위 후보 {sum(len(v) for v in 미리.values()):,}건)",
          flush=True)
    분포2 = []
    for _ in range(300):
        무 = []
        for i, 칸 in 미리.items():
            무.extend(random.sample(칸, min(4, len(칸))))
        v, _, _, _, _ = 시뮬(개선, 목록=무)
        분포2.append(v)
    분포2.sort()
    이2 = sum(1 for v in 분포2 if v >= 실제)
    print(f"     실제        {실제:>15,.0f}원")
    print(f"     무작위 중앙   {분포2[len(분포2)//2]:>15,.0f}원")
    print(f"     무작위 최고   {분포2[-1]:>15,.0f}원")
    print(f"     무작위가 이긴 횟수 {이2}/300  →  **p = {이2/300:.4f}**")

    print("\n  (D~G는 second half에서 이어짐)")
    # ══ D 비용 ══
    print(f"\n  ══ D **비용을 올려보면** ══")
    print(f"    {'비용':<14}{'끝 자산':>16}{'연평균':>9}   "
          f"{'2025·26 제외':>15}{'연평균':>9}")
    for 비용 in (0.26, 0.5, 1.0, 2.0):
        더 = 비용 - 0.26
        a, ac, _, _, _ = 시뮬(개선, 슬립=더)
        b, bc, _, _, _ = 시뮬(개선, 끝년="2024", 슬립=더)
        print(f"    {비용:>6.2f}%       {a:>15,.0f}원{ac:>+9.2f}%   "
              f"{b:>14,.0f}원{bc:>+9.2f}%")

    # ══ E 미끄러짐 ══
    print(f"\n  ══ E **시가보다 불리하게 사면** (미끄러짐) ══")
    print(f"    {'불리한 몫':<14}{'끝 자산':>16}{'연평균':>9}   "
          f"{'2025·26 제외':>15}{'연평균':>9}")
    for s in (0.0, 0.3, 0.5, 1.0, 2.0):
        a, ac, _, _, _ = 시뮬(개선, 슬립=s)
        b, bc, _, _, _ = 시뮬(개선, 끝년="2024", 슬립=s)
        print(f"    +{s:>4.1f}%        {a:>15,.0f}원{ac:>+9.2f}%   "
              f"{b:>14,.0f}원{bc:>+9.2f}%")

    # ══ F 최악 ══
    print(f"\n  ══ F **최악의 해·최악의 구간** ══")
    _, _, 낙, _, 곡 = 시뮬(개선)
    해 = {}
    for j in range(len(곡)):
        해.setdefault(날[시i + j][:4], []).append(곡[j])
    수 = {y: (a[-1] / a[0] - 1) * 100 for y, a in 해.items() if len(a) > 60}
    나쁜 = sorted(수.items(), key=lambda z: z[1])[:3]
    print(f"     가장 나쁜 해: " + " · ".join(f"{y}년 {v:+.2f}%" for y, v in 나쁜))
    print(f"     가장 큰 낙폭: **{낙:.1f}%**")
    # 연속 하락 구간
    피 = 0.0
    시작 = None
    최장 = 0
    for j, v in enumerate(곡):
        if v >= 피:
            피 = v
            if 시작 is not None:
                최장 = max(최장, j - 시작)
            시작 = None
        elif 시작 is None:
            시작 = j
    if 시작 is not None:
        최장 = max(최장, len(곡) - 시작)
    print(f"     가장 오래 원금 회복을 못 한 기간: **{최장}거래일** "
          f"(약 {최장/21:.1f}개월)")

    print(f"\n  ══ G **최종 요약** ══")
    for p, 라 in ((지금, "지금 값"), (개선, "94b 개선안")):
        a, ac, an, 산a, _ = 시뮬(p)
        b, bc, bn, _, _ = 시뮬(p, 끝년="2024")
        c, cc, cn, _, _ = 시뮬(p, 시작년="2021")
        print(f"    {라}")
        print(f"      전체 10.4년   {a:>14,.0f}원  연 {ac:+.2f}%  낙폭 {an:.1f}%"
              f"  {산a}건")
        print(f"      2025·26 제외 {b:>14,.0f}원  연 {bc:+.2f}%  낙폭 {bn:.1f}%")
        print(f"      2021~2026    {c:>14,.0f}원  연 {cc:+.2f}%  낙폭 {cn:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
