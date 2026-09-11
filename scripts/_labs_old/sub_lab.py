#!/usr/bin/env python3
r"""
sub_lab.py — **100차. 보조 전략을 자본 시뮬로 확정한다** (2026-09-04)

## 99b가 남긴 물음
```
세 관문 통과 5종목 (2025·26 제외 평균 순)
   SK하이닉스 +1.06% · 주성엔지니어링 +0.89% · 리노공업 +0.76% ·
   동진쎄미켐 +0.58% · 원익IPS +0.20%
나눠 사기      1종목 **+1.06%** > 2종목 +0.97% > 3종목 +0.90% > 5종목 +0.70%
⇒ 평균으로는 **하이닉스 단독이 최고**다
```
⚠️ 그런데 이건 **평균 수익**이다. 「평균 수익은 돈이 아니다」를 세 번 겪었다.
   나눠 사면 **같은 날 여러 종목을 살 수 있어** 돈이 더 굴러갈 수도 있다.
   ⇒ **자본 시뮬로 다시 잰다**

## 재는 것
```
A ⭐⭐ 자본 시뮬 — 1·2·3·5종목 나눠 사기 (전체 · 2025·26 제외)
B 보유일 (5·10·15·20일) — 99b D에서 길수록 좋았다
C ⭐ **주력과 겹쳐서** — 자산 규모별 (90차·93차 다시, 확정 규칙으로)
D 낙폭·최악의 해·회복 기간
```
⚠️ 주력은 **98차 확정 규칙**을 쓴다 (시총 2천억 · 하루 4종목)
⚠️ 주수는 **원본 시가**로, 수익률은 **수정 비율**로 (53차 버그)
"""
import bisect
import datetime as dt
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
_YH = os.path.join(O._DATA, "yahoo")
# 98차 확정 규칙
확정 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 4}
미국 = ("NVDA", "AMAT", "LRCX", "SOXX", "KLAC", "WDC", "MU", "ASML")
# 99b에서 세 관문을 통과한 것만 (2025·26 제외 평균 순)
보조종목 = (("000660", "SK하이닉스"), ("036930", "주성엔지니어링"),
            ("058470", "리노공업"), ("005290", "동진쎄미켐"),
            ("240810", "원익IPS"))


def main():
    # ── 미국 신호 ──
    쓸 = {}
    for 심 in 미국:
        p = os.path.join(_YH, 심 + ".json")
        if not os.path.exists(p):
            continue
        종 = json.load(io.open(p, encoding="utf-8-sig")).get("종가") or {}
        k = sorted(종)
        e = {}
        for j in range(1, len(k)):
            pv = 종[k[j - 1]]
            if pv:
                e[k[j]] = (종[k[j]] / pv - 1) * 100
        쓸[심] = (e, sorted(e))

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

    # 한국 날짜별 「미국 반도체 아무거나 −2%↓」
    신호일 = set()
    for d in 날:
        if d < _시작:
            continue
        for 심, (e, ks) in 쓸.items():
            j = bisect.bisect_left(ks, d)
            if j == 0:
                continue
            전 = ks[j - 1]
            try:
                if (dt.datetime.strptime(d, "%Y%m%d")
                        - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                    continue
            except Exception:
                pass
            if e[전] <= -2:
                신호일.add(d)
                break

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

    # ── 주력 사건 (98차 확정 규칙) ──
    주력 = {}
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
            if g is None or (g - 시갭) > 확정["갭"]:
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
            주력.setdefault(i + 1, []).append(
                {"청산": 청산, "결과": 결과, "원시": o0, "대금": b0[2],
                 "상대갭": g - 시갭})

    # ── 보조 사건 ──
    선 = {}
    for c, n in 보조종목:
        선[c] = {d: 주가[d][c][0] for d in 날 if 주가[d].get(c)}

    def 보조만들기(N, 보유일=10):
        out = {}
        골 = [c for c, n in 보조종목[:N]]
        for i, d in enumerate(날):
            if d not in 신호일:
                continue
            j = i + 보유일 - 1
            if j >= len(날):
                continue
            묶 = []
            for c in 골:
                s = 선[c]
                b = (비.get(d) or {}).get(c)
                v0, v1 = s.get(d), s.get(날[j])
                o0 = (원시.get(d) or {}).get(c)
                if not b or not v0 or not v1 or not o0:
                    continue
                묶.append({"청산": j,
                           "결과": (v1 / (v0 * b[0]) - 1) * 100 - _비용,
                           "원시": o0, "대금": 9e15})
            if 묶:
                out[i] = 묶
        return out

    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  주력 신호일 {len(주력)}일 · 보조 신호일 {len(신호일)}일 "
          f"({len(신호일)/(len(날)-시i)*100:.0f}%)\n", flush=True)

    def 시뮬(시드, 주on, 보조, 보몫, 라, 끝년=None, 해별=False):
        현금, 보유, 곡 = float(시드), [], []
        주n = 보n = 0
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
            보중 = sum(q["주수"] * q["원시"] for q in 보유 if q.get("보"))
            if 주on:
                for x in sorted(주력.get(i, []),
                                key=lambda z: z["상대갭"])[:확정["종목수"]]:
                    쓸2 = min(평 * 확정["비중"], 현금, x["대금"] * 0.01)
                    주수 = int(쓸2 // x["원시"])   # 주수는 **원본 시가**로
                    if 주수 < 1 or 주수 * x["원시"] > 현금:
                        continue
                    현금 -= 주수 * x["원시"]
                    보유.append({**x, "주수": 주수, "보": False})
                    주n += 1
            if 보몫 > 0 and 보조 and i in 보조 and 보중 <= 0:
                칸 = 보조[i]
                몫 = min(현금, 평 * 보몫) / len(칸)
                for x in 칸:
                    주수 = int(몫 // x["원시"])
                    if 주수 < 1 or 주수 * x["원시"] > 현금:
                        continue
                    현금 -= 주수 * x["원시"]
                    보유.append({**x, "주수": 주수, "보": True})
                    보n += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        cagr = ((끝 / 시드) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        print(f"    {라:<28}{끝:>16,.0f}원{cagr:>+9.2f}%{낙:>8.1f}%"
              f"{주n:>7}{보n:>6}")
        if 해별:
            해 = {}
            for j2 in range(len(곡)):
                해.setdefault(날[시i + j2][:4], []).append(곡[j2])
            수 = {y: (a[-1] / a[0] - 1) * 100
                  for y, a in 해.items() if len(a) > 60}
            나쁜 = sorted(수.items(), key=lambda z: z[1])[:3]
            print("       나쁜 해: " +
                  " · ".join(f"{y} {v:+.1f}%" for y, v in 나쁜))
        return cagr, 낙

    머 = (f"    {'전략':<28}{'끝 자산':>17}{'연평균':>9}{'낙폭':>8}"
          f"{'주력':>7}{'보조':>6}")

    print("  ══ A ⭐⭐ **보조만 · 몇 종목에 나눠 살까** (자본 시뮬) ══")
    print(f"     자산 5,000만원 · 신호 나면 자산의 50%를 N종목에 나눠 · 20일 보유")
    print(머)
    # B절에서 **20일 보유가 가장 좋았다**(2025·26 제외 +13.38% vs 10일 +10.30%).
    # 그래서 C·D절은 **20일**로 돈다 (첫 실행은 10일로 돌려 틀렸다)
    _보유일 = 20
    보조표 = {N: 보조만들기(N, _보유일) for N in (1, 2, 3, 5)}
    for N in (1, 2, 3, 5):
        이름 = " + ".join(n for _, n in 보조종목[:N])
        시뮬(50_000_000, False, 보조표[N], 0.5, f"{N}종목 ({이름[:18]})")
    print("\n    ⚠️ 2025·26 제외")
    for N in (1, 2, 3, 5):
        시뮬(50_000_000, False, 보조표[N], 0.5, f"{N}종목", 끝년="2024")

    print(f"\n  ══ B **며칠 들고 있나** (3종목) ══")
    print(머)
    for h in (5, 10, 15, 20):
        시뮬(50_000_000, False, 보조만들기(3, h), 0.5, f"{h}일 보유")
    print("\n    ⚠️ 2025·26 제외")
    for h in (5, 10, 15, 20):
        시뮬(50_000_000, False, 보조만들기(3, h), 0.5, f"{h}일 보유",
             끝년="2024")

    print(f"\n  ══ C ⭐ **주력(98차 확정)과 겹쳐서 · 자산 규모별** ══")
    최 = max((1, 2, 3, 5),
             key=lambda N: 시뮬(50_000_000, False, 보조표[N], 0.5,
                               f"(고르는 중 {N}종목)", 끝년="2024")[0])
    print(f"\n     ⭐ 2025·26 제외 기준 가장 나은 것: **{최}종목**")
    골 = 보조표[최]
    for 시드 in (5_000_000, 30_000_000, 100_000_000, 300_000_000):
        print(f"\n     자산 {시드:,}원")
        print(머)
        시뮬(시드, True, None, 0, "A 주력만")
        시뮬(시드, False, 골, 0.5, f"B 보조만 ({최}종목)")
        시뮬(시드, True, 골, 0.3, "C 주력 + 보조 30%")
        시뮬(시드, True, 골, 0.5, "C2 주력 + 보조 50%")

    print(f"\n  ══ D ⚠️ **2025·26 제외** (자산 3,000만 · 1억) ══")
    for 시드 in (30_000_000, 100_000_000):
        print(f"     자산 {시드:,}원")
        print(머)
        시뮬(시드, True, None, 0, "A 주력만", 끝년="2024", 해별=True)
        시뮬(시드, True, 골, 0.3, "C 주력 + 보조 30%", 끝년="2024", 해별=True)

    print("\n  읽는 법")
    print("    - A에서 **평균 수익 순위(1종목 최고)와 자본 순위가 다르면**")
    print("      「평균 수익은 돈이 아니다」가 또 맞은 것이다")
    print("    - C·D에서 C가 A를 이겨야 보조를 붙일 값어치가 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
