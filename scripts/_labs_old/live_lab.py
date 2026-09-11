#!/usr/bin/env python3
r"""
live_lab.py — **101차. 08:00에 확정할 수 있는 규칙인가** (2026-09-04)

## ⚠️⚠️ 오늘 아침에 발견한 실전 문제
```
우리 주력 규칙의 핵심 **상대갭 -3%p**는
   (오늘 시가 ÷ 어제 종가 - 1) − 시장 전체 중앙 갭
⇒ **오늘 시가를 알아야 계산된다.**
⇒ **08:00 브리핑 시점에는 알 수 없다.**

백테스트에서는 시가를 다 알고 있으니 문제가 안 보였다.
실전에서는 **08:30~09:00 동시호가**를 봐야 안다.
```

## 그래서 무엇을 재나
```
A ⭐⭐ **갭 조건을 빼면** 얼마나 나빠지나 (08:00에 확정 가능한 규칙)
B **갭 대신 어제 것으로** — 어제 갭 · 어제 종가 위치로 대신할 수 있나
C ⭐ **두 단계로 나누면** — 08:00에 후보를 좁히고 09:00에 갭으로 고른다
     후보를 몇 개까지 좁혀야 실제로 볼 만한가
D ⚠️ 갭 문턱을 얼마나 느슨하게 해도 되나 (동시호가로 대충 봐도 되나)
```
⚠️ 판정: **자본 시뮬** · 2025·26 제외 · 낙폭
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
확정 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 4}


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
                저 = float(v.get("저가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                if min(종c, 시, 고, 저) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거, 저 / 종c)
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

    # ── 후보 모으기 (갭 조건 **없이**) ──
    #    갭은 나중에 걸 수 있게 값만 들고 다닌다
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
        어제갭 = 갭표.get(d1) or {}
        어제시갭 = 시장갭.get(d1)
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 확정["시총"]:
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
            g = 하루갭.get(code)
            상갭 = (g - 시갭) if g is not None else None
            # ⚠️ **어제** 갭 (08:00에 이미 안다)
            g2 = 어제갭.get(code)
            어상갭 = (g2 - 어제시갭) if (g2 is not None
                                        and 어제시갭 is not None) else None
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
                         "청산": 청산, "원시": o0, "대금": b0[2],
                         "상갭": 상갭, "어상갭": 어상갭, "볼": 볼, "낙": 낙,
                         "시총": 시총})
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    갭있 = [x for x in 사건 if x["상갭"] is not None]
    통과 = [x for x in 갭있 if x["상갭"] <= 확정["갭"]]
    print(f"  08:00에 아는 조건만으로 고른 후보 {len(사건):,}건")
    print(f"  그중 갭 -3%p까지 통과 {len(통과):,}건 "
          f"({len(통과)/len(사건)*100:.1f}%)\n", flush=True)

    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)

    def 시뮬(거름, 순서, 라, 끝년=None, 종목수=None, 폭=34):
        현금, 보유, 곡, 산 = _시드, [], [], 0
        N = 종목수 or 확정["종목수"]
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
            골 = [x for x in 묶.get(i, []) if 거름(x)]
            for x in sorted(골, key=순서)[:N]:
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
        return 끝, c, 낙

    def 갭순(x):
        return x["상갭"] if x["상갭"] is not None else 99

    머 = (f"    {'전략':<34}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}"
          f"{'연도별':>8}")

    print("  ══ A ⭐⭐ **갭 조건을 빼면** (08:00에 확정 가능한 규칙) ══")
    print(머)
    기끝, 기c, 기낙 = 시뮬(lambda x: x["상갭"] is not None
                           and x["상갭"] <= 확정["갭"], 갭순,
                           "⭐ 지금 규칙 (갭 -3%p · 09:00에 확정)")
    시뮬(lambda x: True, lambda x: x["낙"], "갭 조건 **없음** · 20일낙폭 깊은 순")
    시뮬(lambda x: True, lambda x: x["볼"], "갭 조건 없음 · 볼린저 깊은 순")
    시뮬(lambda x: True, lambda x: x["시총"], "갭 조건 없음 · 시총 작은 순")
    시뮬(lambda x: True, lambda x: -x["대금"], "갭 조건 없음 · 거래대금 큰 순")

    print(f"\n  ══ B **어제 갭으로 대신하면** (08:00에 이미 안다) ══")
    print(머)
    for 문 in (-2.0, -3.0, -4.0):
        시뮬(lambda x, m=문: x["어상갭"] is not None and x["어상갭"] <= m,
             lambda x: x["어상갭"] if x["어상갭"] is not None else 99,
             f"**어제** 상대갭 {문}%p 아래")

    print(f"\n  ══ C ⭐ **두 단계로 나누면** ══")
    print("     08:00에 후보를 N개로 좁히고, 09:00에 그중 갭이 깊은 것을 산다")
    print("     ⇒ 실전에서 동시호가로 **몇 종목만 보면 되나**")
    print(머)
    for N in (5, 10, 20, 40, 999):
        # 08:00 후보를 20일 낙폭 깊은 순으로 N개로 좁힌 뒤 갭 조건을 건다
        def 거름(x, n=N):
            같 = sorted(묶.get(x["인"], []), key=lambda z: z["낙"])[:n]
            return (x in 같 and x["상갭"] is not None
                    and x["상갭"] <= 확정["갭"])
        라 = f"08:00 후보 {N}개로 좁힘" if N < 999 else "좁히지 않음 (지금 규칙)"
        시뮬(거름, 갭순, 라)

    print(f"\n  ══ D ⚠️ **갭 문턱을 얼마나 느슨하게 해도 되나** ══")
    print("     동시호가는 정확하지 않다. 문턱이 어긋나면 얼마나 손해인가")
    print(머)
    for 문 in (-1.0, -2.0, -2.5, -3.0, -3.5, -4.0, -5.0):
        시뮬(lambda x, m=문: x["상갭"] is not None and x["상갭"] <= m, 갭순,
             f"갭 {문}%p 아래")

    print(f"\n  ══ E ⚠️ **2025·26 제외** ══")
    print(머)
    시뮬(lambda x: x["상갭"] is not None and x["상갭"] <= 확정["갭"], 갭순,
         "지금 규칙 (갭 -3%p)", 끝년="2024")
    시뮬(lambda x: True, lambda x: x["낙"], "갭 조건 없음 · 20일낙폭 순",
         끝년="2024")
    for N in (10, 20):
        def 거름2(x, n=N):
            같 = sorted(묶.get(x["인"], []), key=lambda z: z["낙"])[:n]
            return (x in 같 and x["상갭"] is not None
                    and x["상갭"] <= 확정["갭"])
        시뮬(거름2, 갭순, f"08:00 후보 {N}개 + 09:00 갭", 끝년="2024")

    print("\n  읽는 법")
    print("    - A에서 갭 없는 판이 크게 지면 **갭은 빼면 안 된다** (09:00 확인 필수)")
    print("    - C에서 후보를 좁혀도 성적이 유지되면 **실전에서 볼 종목이 적어진다**")
    print("    - D에서 문턱이 조금 어긋나도 성적이 버티면 **동시호가로 대충 봐도 된다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
