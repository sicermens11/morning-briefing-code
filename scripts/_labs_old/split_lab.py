#!/usr/bin/env python3
r"""
split_lab.py — **95b차. 95차 A의 경고가 진짜인가** (2026-09-03)

## 95차 A가 낸 경고
```
2016~2020으로 문턱을 고르고 2021~2026을 샀더니
   앞 5년 +55.8%  ->  뒤 6년 **+1.4%** · 낙폭 **-38.5%**
⇒ 「연 +30%」는 믿을 숫자가 아니다
```

## ⚠️ 그런데 **분할을 한 번만** 했다
```
그 한 번이 하필 나쁜 값을 고른 것일 수 있다.
그리디 탐색이 **낙폭을 아예 안 봤다.** 돈만 보고 골랐다.
-> 갭 -2.0%p · 낙 -5% · 비중 25% · D+60 이라는 **공격적인 값**을 골랐고
   2021~22 하락장에서 무너졌다
```

## 여기서 재는 것
```
A ⭐ **분할점을 바꿔가며** — 2019·2020·2021·2022로 나눠 각각 앞으로 고르고 뒤로 검증
B ⭐⭐ **낙폭을 보고 고르면** — 돈만 보지 말고 「돈 ÷ 낙폭」으로 고르면 달라지나
C ⭐⭐ **아예 고르지 말고 보수적 기본값**을 쓰면 (문턱 최적화를 포기)
D 무작위 문턱 200개의 **뒤 기간** 성적 — 문턱을 아무렇게나 잡아도 되나
```
⚠️ 결론이 「최적화하지 말라」로 나와도 그게 답이다. **끼워맞추지 않는 게 목표다**
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
# ⭐ **보수적 기본값** — 최적화 없이, 「가운데를 고른다」는 원칙만으로 정한 값
보수 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "목표": 20.0, "보유": 40, "비중": 0.15, "종목수": 3}
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
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  신호 {len(사건):,}건\n", flush=True)

    def 시뮬(p, 시작년=None, 끝년=None, 시드=_시드):
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
        현금, 보유, 곡 = 시드, [], []
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
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        cagr = ((끝 / 시드) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        return cagr, 낙

    def 고르기(끝년, 점수법):
        p = dict(지금)
        for _ in range(3):
            for 축, 값들 in 축들.items():
                최 = None
                for v in 값들:
                    q = dict(p)
                    q[축] = v
                    c, n = 시뮬(q, 끝년=끝년)
                    s = 점수법(c, n)
                    if 최 is None or s > 최[0]:
                        최 = (s, v)
                p[축] = 최[1]
        return p

    def 라벨(p):
        return (f"갭{p['갭']:.1f} 볼{p['볼']:.1f} 낙{p['낙']:.0f} "
                f"시총{p['시총']/1e11:.0f}천억 목{p['목표']:.0f} D+{p['보유']} "
                f"비{p['비중']:.0%} {p['종목수']}종목")

    # ══ A 분할점을 바꿔가며 ══
    print("  ══ A ⭐ **분할점을 바꿔가며** (돈만 보고 고름 — 95차와 같은 방식) ══")
    print(f"    {'분할':<12}{'앞 기간':>10}{'뒤 기간':>10}{'뒤 낙폭':>9}   "
          f"{'고른 값'}")
    for 컷 in ("2019", "2020", "2021", "2022"):
        p = 고르기(컷, lambda c, n: c)
        앞c, _ = 시뮬(p, 끝년=컷)
        뒤c, 뒤n = 시뮬(p, 시작년=str(int(컷) + 1))
        print(f"    ~{컷}       {앞c:>+9.1f}%{뒤c:>+9.1f}%{뒤n:>8.1f}%   {라벨(p)}")

    # ══ B 낙폭을 보고 고르면 ══
    print(f"\n  ══ B ⭐⭐ **낙폭도 보고 고르면** (돈 ÷ 낙폭으로 고름) ══")
    print(f"    {'분할':<12}{'앞 기간':>10}{'뒤 기간':>10}{'뒤 낙폭':>9}   "
          f"{'고른 값'}")
    for 컷 in ("2019", "2020", "2021", "2022"):
        p = 고르기(컷, lambda c, n: c / max(abs(n), 3.0))
        앞c, _ = 시뮬(p, 끝년=컷)
        뒤c, 뒤n = 시뮬(p, 시작년=str(int(컷) + 1))
        print(f"    ~{컷}       {앞c:>+9.1f}%{뒤c:>+9.1f}%{뒤n:>8.1f}%   {라벨(p)}")

    # ══ C 아예 고르지 않으면 ══
    print(f"\n  ══ C ⭐⭐ **아예 고르지 말고 고정값을 쓰면** ══")
    print("     (최적화를 포기하고, 뒤 기간마다 같은 값을 쓴다)")
    print(f"    {'전략':<26}", end="")
    for 컷 in ("2019", "2020", "2021", "2022"):
        print(f"{컷[2:]}이후".rjust(11), end="")
    print(f"{'평균':>10}")
    for p, 라 in ((지금, "지금 값"), (개선, "94b 개선안"),
                  (보수, "⭐ 보수적 기본값")):
        수 = []
        print(f"    {라:<26}", end="")
        for 컷 in ("2019", "2020", "2021", "2022"):
            c, n = 시뮬(p, 시작년=str(int(컷) + 1))
            수.append(c)
            print(f"{c:>+10.1f}%", end="")
        print(f"{st.mean(수):>+9.1f}%")
    print(f"    (보수적 기본값 = {라벨(보수)})")

    # ══ D 무작위 문턱의 뒤 기간 성적 ══
    print(f"\n  ══ D **무작위 문턱 300개의 「2021년 이후」 성적** ══")
    print("     문턱을 아무렇게나 잡아도 되나")
    random.seed(20260903)
    분포 = []
    for _ in range(300):
        p = {축: random.choice(v) for 축, v in 축들.items()}
        c, n = 시뮬(p, 시작년="2021")
        분포.append((c, n))
    cs = sorted(x[0] for x in 분포)
    ns = sorted(x[1] for x in 분포)
    흑 = sum(1 for c in cs if c > 0)
    print(f"     연평균  가장 나쁨 {cs[0]:+.1f}%  하위25% {cs[len(cs)//4]:+.1f}%  "
          f"중앙 {cs[len(cs)//2]:+.1f}%  상위25% {cs[3*len(cs)//4]:+.1f}%  "
          f"가장 좋음 {cs[-1]:+.1f}%")
    print(f"     낙폭    가장 나쁨 {ns[0]:.1f}%  중앙 {ns[len(ns)//2]:.1f}%  "
          f"가장 좋음 {ns[-1]:.1f}%")
    print(f"     ⭐ **흑자인 조합 {흑}/300 ({흑/3:.0f}%)**")
    for p, 라 in ((지금, "지금 값"), (개선, "94b 개선안"), (보수, "보수적 기본값")):
        c, n = 시뮬(p, 시작년="2021")
        위 = sum(1 for x in cs if x < c) / len(cs) * 100
        print(f"     {라:<16}{c:>+7.1f}%  낙폭 {n:>6.1f}%  → 상위 {100-위:.0f}%")

    print("\n  읽는 법")
    print("    - A가 분할점마다 다 나쁘면 **문턱 최적화는 하지 말아야 한다**")
    print("    - B가 A보다 나으면 **낙폭도 함께 봐야 한다**는 뜻이다")
    print("    - D에서 흑자 비율이 높으면 **문턱을 대충 잡아도 된다**는 뜻이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
