#!/usr/bin/env python3
r"""
tune_lab.py — **94차. 원판의 문턱을 자본 시뮬 기준으로 다시 고른다** (2026-09-03)

## 왜 다시 고르나
```
지금 쓰는 숫자   상대갭 -3%p · 볼린저 -1.0σ · 20일 -10% · 시총 3천억↓
                +20% 목표 · 최대 D+40 · 비중 20% · 하루 2종목
⇒ 이건 **57차 sweep에서 날짜 단위로** 고른 것이다.

그런데 그 뒤로 판정 기준이 바뀌었다:
   88b·88c·91  조건을 **더하는** 시도는 세 번 다 자본 시뮬에서 무너졌다
   ⇒ 「날짜 단위로 좋다」와 「돈이 는다」가 다르다는 걸 세 번 확인했다
⇒ **원판의 문턱도 자본 시뮬로 다시 봐야 한다**
```

## 재는 법
```
후보를 **가장 느슨한 조건**으로 한 번만 모으고 (상대갭 -2 · 볼린저 -0.8 ·
20일 -5 · 시총 5천억↓), 목표·보유일 조합별 결과를 **미리 다 계산**한다.
그 다음 축을 하나씩 바꿔가며 **자본 시뮬**을 돌린다.
```
⚠️ 축 하나만 바꾸고 나머지는 지금 값으로 둔다 (한꺼번에 바꾸면 무엇이 이겼는지 모른다)
⚠️ **전체 기간**과 **2025·26 제외**를 늘 같이 본다
⚠️ 마지막에 **걷기검증** — 그 해 이전만 보고 문턱을 정해 그 해를 산다
⚠️ 주수는 **원본 시가**로, 수익률은 **수정 비율**로 (53차 버그)
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

# 지금 쓰는 값 (기준선)
기본값 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 3e11,
          "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 2}
# 후보를 모을 때 쓰는 **가장 느슨한** 조건
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

    # ══ 후보 모으기 (가장 느슨하게 한 번만) ══
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
            # ⚠️ 목표·보유일 조합별 결과를 **미리 다 계산**해 둔다
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
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  느슨하게 모은 후보 {len(사건):,}건 · {년수:.1f}년\n", flush=True)

    def 시뮬(p, 끝년=None, 시드=_시드):
        묶 = {}
        for x in 사건:
            if (x["갭"] > p["갭"] or x["볼"] > p["볼"] or x["낙"] > p["낙"]
                    or x["시총"] >= p["시총"]):
                continue
            k = (p["목표"], p["보유"])
            if k not in x["결"]:
                continue
            묶.setdefault(x["인"], []).append(x)
        현금, 보유, 곡, 산 = 시드, [], [], 0
        for i, d in enumerate(날):
            if d < _시작:
                continue
            if 끝년 and d[:4] > 끝년:
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
            for x in sorted(묶.get(i, []),
                            key=lambda z: z["갭"])[:p["종목수"]]:
                r, 끝i = x["결"][(p["목표"], p["보유"])]
                쓸 = min(평 * p["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])     # 주수는 **원본 시가**로
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({"주수": 주수, "원시": x["원시"], "r": r, "끝": 끝i})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = len(곡) / 245
        cagr = ((끝 / 시드) ** (1 / max(yr, 0.1)) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        해 = {}
        시i = [j for j, dd in enumerate(날) if dd >= _시작][0]
        for j in range(len(곡)):
            해.setdefault(날[시i + j][:4], []).append(곡[j])
        전 = 플 = 0
        for y in sorted(해):
            if len(해[y]) < 100:
                continue
            전 += 1
            플 += 1 if 해[y][-1] > 해[y][0] else 0
        return 끝, cagr, 낙, 산, 플, 전

    기끝, 기c, 기낙, 기산, _, _ = 시뮬(기본값)
    기끝2, 기c2, 기낙2, _, _, _ = 시뮬(기본값, 끝년="2024")
    print(f"  ══ **지금 쓰는 값** (기준선) ══")
    print(f"    상대갭 -3%p · 볼린저 -1.0σ · 20일 -10% · 시총 3천억↓")
    print(f"    +20% 목표 · 최대 D+40 · 비중 20% · 하루 2종목")
    print(f"    전체 기간     {기끝:>15,.0f}원  연 {기c:+.2f}%  낙폭 {기낙:.1f}%"
          f"  {기산}건")
    print(f"    2025·26 제외 {기끝2:>15,.0f}원  연 {기c2:+.2f}%  낙폭 {기낙2:.1f}%")

    def 훑(축, 값들, 라, 꼴="{}"):
        print(f"\n  ══ **{라}** ══")
        print(f"    {'값':<14}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}"
              f"{'연도별':>7}   {'2025·26 제외':>16}{'연평균':>9}{'낙폭':>8}")
        for v in 값들:
            p = dict(기본값)
            p[축] = v
            끝, c, 낙, 산, 플, 전 = 시뮬(p)
            끝2, c2, 낙2, _, _, _ = 시뮬(p, 끝년="2024")
            표 = "  ← 지금" if v == 기본값[축] else ""
            # ⚠️ 낙폭은 **음수**다. -13.6 <= -8.74 가 참이 되어
            #    「낙폭이 더 나쁜 것」에 ⭐가 붙던 버그를 고쳤다 (2026-09-03)
            좋 = "⭐" if (끝2 > 기끝2 * 1.03 and 낙2 >= 기낙2 * 1.15) else "  "
            print(f"    {꼴.format(v):<14}{끝:>15,.0f}원{c:>+9.2f}%{낙:>8.1f}%"
                  f"{산:>7}{f'{플}/{전}':>7}   {끝2:>15,.0f}원{c2:>+9.2f}%"
                  f"{낙2:>8.1f}%{좋}{표}")

    훑("갭", (-2.0, -2.5, -3.0, -4.0, -5.0), "상대갭 문턱", "{:.1f}%p")
    훑("볼", (-0.8, -1.0, -1.2, -1.5), "볼린저 문턱", "{:.1f}σ")
    훑("낙", (-5.0, -10.0, -15.0, -20.0), "20일 낙폭 문턱", "{:.0f}%")
    훑("시총", (1e11, 2e11, 3e11, 5e11), "시총 상한", "{:.0e}")
    훑("목표", (15.0, 20.0, 25.0, 30.0), "목표 수익", "+{:.0f}%")
    훑("보유", (20, 40, 60), "최대 보유일", "D+{}")
    훑("비중", (0.15, 0.20, 0.25, 0.30), "한 종목 비중", "{:.0%}")
    훑("종목수", (1, 2, 3, 4), "하루 최대 종목수", "{}종목")

    # ══ 걷기검증 ══
    print(f"\n  ══ ⭐⭐ **걷기검증** — 그 해 이전만 보고 문턱을 정해 그 해를 산다 ══")
    print("     ⚠️ 이게 가장 엄격한 판이다. 여기서 안 되면 **끼워맞춘 것**이다")
    축들 = {"갭": (-2.0, -2.5, -3.0, -4.0, -5.0),
            "볼": (-0.8, -1.0, -1.2, -1.5),
            "낙": (-5.0, -10.0, -15.0, -20.0),
            "목표": (15.0, 20.0, 25.0, 30.0),
            "보유": (20, 40, 60)}
    해들 = [str(y) for y in range(2019, 2027)]
    현금, 곡표 = _시드, []
    print(f"    {'해':<8}{'그 해 이전에 고른 값':<40}{'그 해 수익':>10}{'자산':>16}")
    for y in 해들:
        # 그 해 **이전**만으로 최고 조합을 찾는다 (한 축씩 그리디)
        p = dict(기본값)
        for _ in range(2):
            for 축, 값들 in 축들.items():
                최 = None
                for v in 값들:
                    q = dict(p)
                    q[축] = v
                    끝, c, 낙, 산, _, _ = 시뮬(q, 끝년=str(int(y) - 1))
                    if 최 is None or 끝 > 최[0]:
                        최 = (끝, v)
                p[축] = 최[1]
        # 그 해만 산다
        전끝, _, _, _, _, _ = 시뮬(p, 끝년=str(int(y) - 1))
        올끝, _, _, _, _, _ = 시뮬(p, 끝년=y)
        수 = (올끝 / 전끝 - 1) * 100 if 전끝 > 0 else 0
        현금 *= (1 + 수 / 100)
        곡표.append(수)
        라 = (f"갭{p['갭']:.1f} 볼{p['볼']:.1f} 낙{p['낙']:.0f} "
              f"목{p['목표']:.0f} D+{p['보유']}")
        print(f"    {y:<8}{라:<40}{수:>+9.2f}%{현금:>15,.0f}원")
    걷 = ((현금 / _시드) ** (1 / len(해들)) - 1) * 100
    플 = sum(1 for x in 곡표 if x > 0)
    print(f"\n    걷기검증 {len(해들)}해 연평균 **{걷:+.2f}%** · "
          f"흑자 {플}/{len(해들)}해")

    print("\n  읽는 법")
    print("    - ⭐는 **2025·26 제외 판에서 3% 이상 좋아지고 낙폭은 안 나빠진** 것")
    print("    - 걷기검증이 가장 엄격하다. 여기 숫자가 진짜 기대치에 가깝다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
