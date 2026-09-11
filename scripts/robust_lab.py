#!/usr/bin/env python3
r"""
robust_lab.py — **98차. 낙폭까지 보고 문턱을 고른다 (최종 확정)** (2026-09-04 새벽)

## 95차·95b가 알려준 것
```
95차 A   2016~2020으로 **돈만 보고** 문턱을 골랐더니
         뒤 6년 연 **+1.4%** · 낙폭 **-38.5%**  ← 참사

95b B    같은 분할에서 **낙폭도 같이 보고** 골랐더니
         뒤 6년 연 **+22.9%** · 낙폭 -16.8%
         네 분할 모두 +23~32%로 안정

95b D    문턱을 **아무렇게나** 고른 300개의 2021년 이후 성적
         가장 나쁨 +0.7% · 중앙 +17.2% · **흑자 300/300**
```
⇒ **문턱을 정확히 맞출 필요는 없다. 다만 「돈만 보고 고르면」 위험하다**

## 여기서 최종 확정한다
```
A 고르는 잣대를 여러 가지로  — 돈만 / 돈÷낙폭 / 돈−낙폭×k / 최악의 해
B ⭐ **모든 분할에서 골고루 좋은 문턱** — 네 분할의 뒤 기간 평균으로
C ⭐⭐ **문턱을 안 고르고 「가운데」를 쓰면** — 각 축의 중간값
D 최종 후보 서넛을 **2021년 이후** 성적으로 겨룬다
E ⚠️ 최종안의 **연도별·최악·회복기간**
```
⚠️ 여기서 나오는 값이 **실제로 쓸 규칙**이다. 더 만지지 않는다
⚠️ 주수는 **원본 시가**로, 수익률은 **수정 비율**로 (53차 버그)
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
_시드 = 5_000_000.0
지금 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 3e11,
        "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 2}
개선 = {**지금, "시총": 2e11, "종목수": 4}
_느 = {"갭": -2.0, "볼": -0.8, "낙": -5.0, "시총": 5e11}
_목표들 = (15.0, 20.0, 25.0, 30.0)
_보유들 = (20, 40, 60)
축들 = {"갭": (-2.0, -2.5, -3.0, -4.0, -5.0),
        "볼": (-0.8, -1.0, -1.2, -1.5),
        "낙": (-5.0, -10.0, -15.0, -20.0),
        "시총": (1e11, 2e11, 3e11, 5e11),
        "목표": (15.0, 20.0, 25.0, 30.0),
        "보유": (20, 40, 60),
        "비중": (0.15, 0.20, 0.25),
        "종목수": (1, 2, 3, 4)}


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
    print(f"  신호 {len(사건):,}건\n", flush=True)

    def 시뮬(p, 시작년=None, 끝년=None, 시드=_시드, 해별=False):
        묶 = {}
        for x in 사건:
            if (x["갭"] > p["갭"] or x["볼"] > p["볼"] or x["낙"] > p["낙"]
                    or x["시총"] >= p["시총"]):
                continue
            if (p["목표"], p["보유"]) not in x["결"]:
                continue
            묶.setdefault(x["인"], []).append(x)
        시작i = 시i
        if 시작년:
            c2 = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = c2[0] if c2 else 시i
        현금, 보유, 곡, 산 = 시드, [], [], 0
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
        if 해별:
            해 = {}
            for j in range(len(곡)):
                해.setdefault(날[시작i + j][:4], []).append(곡[j])
            수 = {y: (a[-1] / a[0] - 1) * 100
                  for y, a in 해.items() if len(a) > 60}
            # 원금 회복까지 가장 오래 걸린 기간
            피2 = 0.0
            시작 = None
            최장 = 0
            for j, v in enumerate(곡):
                if v >= 피2:
                    피2 = v
                    if 시작 is not None:
                        최장 = max(최장, j - 시작)
                    시작 = None
                elif 시작 is None:
                    시작 = j
            if 시작 is not None:
                최장 = max(최장, len(곡) - 시작)
            return cagr, 낙, 산, 수, 최장
        return cagr, 낙, 산, None, None

    def 고르기(끝년, 잣대):
        p = dict(지금)
        for _ in range(3):
            for 축, 값들 in 축들.items():
                최 = None
                for v in 값들:
                    q = dict(p)
                    q[축] = v
                    c, n, _, _, _ = 시뮬(q, 끝년=끝년)
                    s = 잣대(c, n)
                    if 최 is None or s > 최[0]:
                        최 = (s, v)
                p[축] = 최[1]
        return p

    def 라벨(p):
        return (f"갭{p['갭']:.1f} 볼{p['볼']:.1f} 낙{p['낙']:.0f} "
                f"시총{p['시총']/1e11:.0f}천억 목{p['목표']:.0f} D+{p['보유']} "
                f"비{p['비중']:.0%} {p['종목수']}종목")

    잣대들 = (
        ("돈만", lambda c, n: c),
        ("돈 ÷ 낙폭", lambda c, n: c / max(abs(n), 3.0)),
        ("돈 − 낙폭×1", lambda c, n: c + n),          # n은 음수
        ("돈 − 낙폭×2", lambda c, n: c + 2 * n),
        ("돈, 낙폭 15% 안", lambda c, n: c if n >= -15 else -999),
    )

    # ══ A 잣대를 여러 가지로 ══
    print("  ══ A **고르는 잣대를 여러 가지로** ══")
    print("     2016~2020으로 고르고 2021~2026을 산다")
    print(f"    {'잣대':<18}{'앞 기간':>9}{'뒤 기간':>9}{'뒤 낙폭':>9}   {'고른 값'}")
    for 라, 잣 in 잣대들:
        p = 고르기("2020", 잣)
        앞c, _, _, _, _ = 시뮬(p, 끝년="2020")
        뒤c, 뒤n, _, _, _ = 시뮬(p, 시작년="2021")
        print(f"    {라:<18}{앞c:>+8.1f}%{뒤c:>+8.1f}%{뒤n:>8.1f}%   {라벨(p)}")

    # ══ B 모든 분할에서 골고루 ══
    print(f"\n  ══ B ⭐ **네 분할 모두에서 골고루 좋은 문턱** ══")
    print("     ~2019 · ~2020 · ~2021 · ~2022 로 각각 고르고, **뒤 기간 평균**으로 판정")
    컷들 = ("2019", "2020", "2021", "2022")
    후보 = {}
    for 라, 잣 in 잣대들:
        수 = []
        낙수 = []
        for 컷 in 컷들:
            p = 고르기(컷, 잣)
            c, n, _, _, _ = 시뮬(p, 시작년=str(int(컷) + 1))
            수.append(c)
            낙수.append(n)
        후보[라] = (st.mean(수), st.mean(낙수))
        print(f"    {라:<18}뒤 기간 평균 {st.mean(수):>+7.1f}%  "
              f"낙폭 평균 {st.mean(낙수):>6.1f}%  "
              f"(각 {' '.join(f'{x:+.0f}' for x in 수)})")

    # ══ C 가운데를 쓰면 ══
    print(f"\n  ══ C ⭐⭐ **문턱을 안 고르고 「가운데」를 쓰면** ══")
    가운데 = {}
    for 축, 값들 in 축들.items():
        가운데[축] = sorted(값들)[len(값들) // 2]
    print(f"     가운데 값 = {라벨(가운데)}")
    후보안 = {"지금 값": 지금, "94b 개선안": 개선, "가운데": 가운데}
    print(f"    {'전략':<16}", end="")
    for 컷 in 컷들:
        print(f"{컷[2:]}이후".rjust(10), end="")
    print(f"{'평균':>9}{'낙폭평균':>10}")
    for 라, p in 후보안.items():
        수, 낙수 = [], []
        print(f"    {라:<16}", end="")
        for 컷 in 컷들:
            c, n, _, _, _ = 시뮬(p, 시작년=str(int(컷) + 1))
            수.append(c)
            낙수.append(n)
            print(f"{c:>+9.1f}%", end="")
        print(f"{st.mean(수):>+8.1f}%{st.mean(낙수):>9.1f}%")

    # ══ D 최종 겨루기 ══
    print(f"\n  ══ D ⭐⭐ **최종 후보 겨루기** (2021년 이후) ══")
    최종 = dict(후보안)
    for 라, 잣 in 잣대들[1:3]:
        최종[f"{라}로 고름(~2020)"] = 고르기("2020", 잣)
    print(f"    {'전략':<26}{'연평균':>9}{'낙폭':>8}{'산 것':>7}   {'값'}")
    성적 = {}
    for 라, p in 최종.items():
        c, n, 산, _, _ = 시뮬(p, 시작년="2021")
        성적[라] = (c, n)
        print(f"    {라:<26}{c:>+8.1f}%{n:>8.1f}%{산:>7}   {라벨(p)}")

    # ══ E 최종안 자세히 ══
    print(f"\n  ══ E **최종안 자세히** ══")
    고른 = max(성적, key=lambda k: 성적[k][0] / max(abs(성적[k][1]), 3.0))
    p = 최종[고른]
    print(f"     ⭐ 돈÷낙폭으로 가장 나은 것: **{고른}**")
    print(f"        {라벨(p)}")
    for 시작, 끝, 라 in ((None, "2024", "2016~2024 (2025·26 제외)"),
                        ("2021", None, "2021~2026"),
                        (None, None, "전체 10.4년")):
        c, n, 산, 수, 최장 = 시뮬(p, 시작년=시작, 끝년=끝, 해별=True)
        print(f"     {라:<24}연 {c:+.2f}%  낙폭 {n:.1f}%  {산}건  "
              f"회복 최장 {최장}일({최장/21:.1f}개월)")
        if 수:
            나쁜 = sorted(수.items(), key=lambda z: z[1])[:3]
            print(f"        나쁜 해: " +
                  " · ".join(f"{y} {v:+.1f}%" for y, v in 나쁜))

    print("\n  읽는 법")
    print("    - B에서 **잣대별 뒤 기간 평균**이 가장 높은 게 옳은 고르는 법이다")
    print("    - C의 「가운데」가 나쁘지 않으면 **최적화를 아예 안 해도 된다**")
    print("    - E의 2021~2026 성적이 **실제로 기대할 수 있는 값**에 가장 가깝다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
