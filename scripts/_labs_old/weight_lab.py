#!/usr/bin/env python3
r"""
weight_lab.py — **88c차. 미국 신호를 「문지기」 말고 「비중」으로 쓴다** (2026-09-03)

## 88b가 알려준 것
```
미국 기술 −1.5%↓  도달률 75.2% → **84.5%**  (분명히 좋아진다)
그런데 자본 시뮬   원판 +35.80% → **+21.56%**  (**더 나빠진다**)
이유: **산 것 195건 → 68건.** 남은 돈이 예금에서 논다
```
⇒ **문지기로 쓰면 손해다.** 그럼 어떻게 쓰나?

## 여기서 재는 것 — 세 가지 쓰는 법
```
① 문지기   조건 맞는 날만 산다              ← 88b에서 **졌다**
② 비중     조건 맞으면 크게, 아니면 작게      ← **이걸 잰다**
③ 점수     여러 지표를 세어 0~4점, 점수만큼 비중  ← 사용자가 원한 **점수제**
```
살 날은 **그대로 195건**을 두고, 힘만 옮긴다.

⚠️ 판정은 **끝 자산**으로만 한다. 도달률·평균은 참고다.
⚠️ 주수는 **원본 시가**로, 수익률은 **수정 비율**로 (53차 버그)
"""
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
_목표 = 20.0
_최대보유 = 40
_YH = os.path.join(O._DATA, "yahoo")
_아시아 = {"IDX_HSI", "IDX_TWII"}

# 88b에서 **연도별 9해 이상**을 통과한 것만 (미국13주·중국은 해가 몰려 뺀다)
점수축 = (("XLK", -1.0, "미국 기술"), ("SOXX", -1.0, "반도체"),
          ("QQQ", -1.0, "나스닥100"), ("IDX_HSI", -0.5, "홍콩"),
          ("IDX_TWII", -0.5, "대만"))


def main():
    지표 = {}
    for f in sorted(glob.glob(os.path.join(_YH, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        키 = os.path.basename(f)[:-5]
        종 = d.get("종가") or {}
        if len(종) < 500:
            continue
        k = sorted(종)
        변 = {}
        for j in range(1, len(k)):
            p = 종[k[j - 1]]
            if p:
                변[k[j]] = (종[k[j]] / p - 1) * 100
        지표[키] = 변

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
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                거 = float(v.get("거래대금") or 0)
                if min(종, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종, 고 / 종, 거)
            원시.setdefault(d8, {})[c] = 시
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

    # 각 한국 날짜에 쓸 수 있는 값 (아시아는 하루 늦게)
    쓸값 = {}
    for 키 in set(k for k, _, _ in 점수축):
        변 = 지표.get(키) or {}
        ek = sorted(변)
        t = {}
        for i, d in enumerate(날):
            기준 = 날[i - 1] if (키 in _아시아 and i > 0) else d
            앞 = [x for x in ek if x < 기준]
            if not 앞:
                continue
            전 = max(앞)
            try:
                if (dt.datetime.strptime(기준, "%Y%m%d")
                        - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                    continue
            except Exception:
                pass
            t[d] = 변[전]
        쓸값[키] = t

    # 날짜별 **점수** 0~5 (몇 개가 빠졌나)
    점수 = {}
    for d in 날:
        s = 0
        for 키, 문, _ in 점수축:
            v = (쓸값.get(키) or {}).get(d)
            if v is not None and v <= 문:
                s += 1
        점수[d] = s

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
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -3:
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
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0 or sq[k - 20] <= 0:
                continue
            if (c1 / sq[k - 20] - 1) * 100 > -10:
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
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    break
                if vv[0] * bb2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 청산 = _목표 - _비용, j
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            사건.append({"날": 다음, "인": i + 1, "청산": 청산, "code": code,
                         "결과": 결과, "원시": o0, "대금": b0[2],
                         "점": 점수[다음], "상대갭": g - 시갭,
                         "도달": 결과 > _목표 - _비용 - 1e-9})
    n = len(사건)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  사건 {n:,}건 · {년수:.1f}년\n", flush=True)

    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)

    def 시뮬(비중함, 라, 시드=5_000_000.0, 최대=2, 끝년=None):
        현금, 보유, 곡, 산것, 총액 = 시드, [], [], 0, 0.0
        for i in range(len(날)):
            if 끝년 and 날[i][:4] > 끝년:
                break
            남 = []
            for p in 보유:
                if p["청산"] <= i:
                    현금 += p["주수"] * p["원시"] * (1 + p["결과"] / 100)
                else:
                    남.append(p)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(p["주수"] * p["원시"] for p in 보유)
            for x in sorted(묶.get(i, []), key=lambda z: z["상대갭"])[:최대]:
                w = 비중함(x)
                if w <= 0:
                    continue
                쓸 = min(평 * w, 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])   # 주수는 **원본 시가**로
                if 주수 < 1:
                    continue
                실 = 주수 * x["원시"]
                if 실 > 현금:
                    continue
                현금 -= 실
                총액 += 실
                보유.append({**x, "주수": 주수})
                산것 += 1
            곡.append(평)
        끝 = 현금 + sum(p["주수"] * p["원시"] for p in 보유)
        yr = len(곡) / 245
        cagr = ((끝 / 시드) ** (1 / max(yr, 0.1)) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        해 = {}
        for j in range(len(곡)):
            해.setdefault(날[j][:4], []).append(곡[j])
        전 = 플 = 0
        for y in sorted(해):
            if len(해[y]) < 100:
                continue
            전 += 1
            플 += 1 if 해[y][-1] > 해[y][0] else 0
        print(f"    {라:<28}{끝:>15,.0f}원{cagr:>+9.2f}%{낙:>8.1f}%"
              f"{산것:>7}건{f'{플}/{전}':>8}")
        return cagr

    머 = (f"    {'전략':<28}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}"
          f"{'산 것':>7}{'연도별':>8}")

    # ── 점수 분포부터 ──
    분 = {}
    for x in 사건:
        분.setdefault(x["점"], []).append(x)
    print("  ══ 먼저 **점수별로 정말 다른가** ══")
    print("     점수 = 미국기술·반도체·나스닥·홍콩·대만 중 **몇 개가 빠졌나**")
    print(f"    {'점수':<10}{'표본':>9}{'도달률':>9}{'평균':>10}{'비율':>9}")
    for s in sorted(분):
        a = 분[s]
        print(f"    {s}점{'':<7}{len(a):>8}건"
              f"{sum(1 for x in a if x['도달'])/len(a)*100:>8.1f}%"
              f"{st.mean([x['결과'] for x in a]):>+9.2f}%"
              f"{len(a)/n*100:>8.1f}%")

    print(f"\n  ══ ① **문지기** (88b 재확인 · 살 날이 준다) ══")
    print(머)
    시뮬(lambda x: 0.20, "원판 · 항상 20%")
    시뮬(lambda x: 0.20 if x["점"] >= 1 else 0.0, "1점 이상만 산다")
    시뮬(lambda x: 0.20 if x["점"] >= 3 else 0.0, "3점 이상만 산다")

    print(f"\n  ══ ② ⭐ **비중** (살 날은 그대로 · 힘만 옮긴다) ══")
    print(머)
    for 큰, 작 in ((0.25, 0.15), (0.30, 0.10), (0.30, 0.15), (0.35, 0.10)):
        시뮬(lambda x, a=큰, b=작: a if x["점"] >= 1 else b,
             f"1점↑ {큰*100:.0f}% / 아니면 {작*100:.0f}%")
    for 큰, 작 in ((0.30, 0.15), (0.35, 0.15), (0.40, 0.15)):
        시뮬(lambda x, a=큰, b=작: a if x["점"] >= 3 else b,
             f"3점↑ {큰*100:.0f}% / 아니면 {작*100:.0f}%")

    print(f"\n  ══ ③ ⭐⭐ **점수제** (0~5점을 그대로 비중으로) ══")
    print(머)
    for 바닥, 칸 in ((0.10, 0.04), (0.10, 0.06), (0.15, 0.04), (0.05, 0.06)):
        시뮬(lambda x, b=바닥, s=칸: min(0.40, b + s * x["점"]),
             f"{바닥*100:.0f}% + 점수×{칸*100:.0f}%p")

    print(f"\n  ══ ④ **하루 살 수 있는 종목 수**를 점수로 ══")
    print(머)
    시뮬(lambda x: 0.20, "항상 2종목 (원판)", 최대=2)
    시뮬(lambda x: 0.20, "항상 3종목", 최대=3)
    시뮬(lambda x: 0.20 if x["점"] >= 1 else 0.15, "3종목 + 비중 20/15%", 최대=3)

    print(f"\n  ══ ⑤ ⚠️ **2025·26 제외** (그 두 해가 다 한 게 아닌지) ══")
    print(머)
    시뮬(lambda x: 0.20, "원판", 끝년="2024")
    시뮬(lambda x: min(0.40, 0.10 + 0.06 * x["점"]), "점수제 10%+점수×6%p",
         끝년="2024")
    시뮬(lambda x: 0.30 if x["점"] >= 1 else 0.10, "1점↑ 30% / 아니면 10%",
         끝년="2024")

    print("\n  읽는 법")
    print("    - ②③이 ①(원판 20%)보다 커야 미국 신호가 **진짜 쓸모**가 있다")
    print("    - ⑤에서도 이겨야 2025·26 덕이 아니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
