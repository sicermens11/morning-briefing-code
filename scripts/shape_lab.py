#!/usr/bin/env python3
r"""
shape_lab.py — **얼마나 빠졌나가 아니라 「어떻게」 빠졌나** (2026-09-05 주말)

## ⚠️ 사용자 질문에서 나왔다
```
*"우리가 테스트하는 조건이 하루 조합 조건이야? 아니면 과거 수치의 흐름까지
  테스트해본거야?"*

지금 조건을 갈라보면
   하루      상대갭 -3.5%p · 시총 · 거래대금
   20일 흐름  볼린저 -1.0σ · 20일 낙폭 -10%
   1년       잉여금·부채·흑자
⇒ **「얼마나」 빠졌나만 본다. 「어떻게」 빠졌나는 한 번도 안 봤다**
   (31차 flow_lab은 **옛 신호**(대형 과매수)에 대한 것이었다)
```

## 재는 것 — 흐름의 **모양**
```
A 며칠째 연속 하락 중인가        1일 · 2일 · 3일 · 4일 이상
B ⭐ **하루에 다 빠졌나 서서히 빠졌나**
     20일 낙폭 중 **가장 큰 하루**가 차지하는 몫
     한 방에 빠진 것(뉴스) vs 서서히 흘러내린 것(수급)
C 빠지는 **속도**              최근 5일 낙폭 vs 그 앞 15일 낙폭
D 어제·그제도 **갭 하락**이었나
E ⭐ **더 긴 기간**             60일·120일 낙폭 (지금은 20일만 본다)
F 20일선 **아래에 며칠째** 있나
G ⭐⭐ 자본 시뮬               살아남은 것을 실제로 붙여본다
```
⚠️ 흐름 조건은 대개 **살 기회를 줄이는 쪽**이다. 그런 조건은 지금까지 **아홉 번 다 졌다**.
   그래도 안 해봤으니 잰다. **자본 시뮬에서 원판을 못 이기면 안 쓴다**
"""
import glob
import io
import datetime as dt
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

    사건 = []
    for i, d1 in enumerate(날):
        if i < 300 or i + 1 >= len(날):
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
            if kk is None or kk < 260:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > 확정["볼"] or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > 확정["낙"]:
                continue
            # ── 흐름의 모양 ──
            일별 = []
            for j in range(kk - 19, kk + 1):
                if sq[j - 1] > 0:
                    일별.append((sq[j] / sq[j - 1] - 1) * 100)
            # A 며칠째 연속 하락
            연속 = 0
            for r in reversed(일별):
                if r < 0:
                    연속 += 1
                else:
                    break
            # B 가장 큰 하루가 차지하는 몫
            최악하루 = min(일별) if 일별 else 0
            몫 = (최악하루 / 낙 * 100) if 낙 < 0 else None
            # C 속도 — 최근 5일 vs 앞 15일
            최근5 = ((sq[kk] / sq[kk - 5] - 1) * 100) if sq[kk - 5] > 0 else None
            앞15 = ((sq[kk - 5] / sq[kk - 20] - 1) * 100) \
                if sq[kk - 20] > 0 else None
            가속 = None
            if 최근5 is not None and 앞15 is not None:
                가속 = 최근5 - 앞15      # 음수면 최근에 더 빠르게 빠짐
            # D 어제·그제 갭
            앞갭 = 0
            for o in (0, 1):
                dd = 날[i - o]
                gg = (갭표.get(dd) or {}).get(code)
                sg = 시장갭.get(dd)
                if gg is not None and sg is not None and (gg - sg) <= -1.5:
                    앞갭 += 1
            # E 더 긴 기간
            낙60 = ((c1 / sq[kk - 60] - 1) * 100) if kk >= 60 and \
                sq[kk - 60] > 0 else None
            낙120 = ((c1 / sq[kk - 120] - 1) * 100) if kk >= 120 and \
                sq[kk - 120] > 0 else None
            # F 20일선 아래 며칠째
            아래 = 0
            for j in range(kk, max(kk - 60, 20), -1):
                m20 = st.mean(sq[j - 19:j + 1])
                if sq[j] < m20:
                    아래 += 1
                else:
                    break
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
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + _목표 / 100):
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
            사건.append({"인": i + 1, "날": 다음, "결과": 결과, "청산": 청산,
                         "원시": o0, "대금": b0[2], "상갭": g - 시갭,
                         "연속": 연속, "몫": 몫, "가속": 가속, "앞갭": 앞갭,
                         "낙60": 낙60, "낙120": 낙120, "선아래": 아래,
                         "도달": 결과 > _목표 - _비용 - 1e-9})
    n = len(사건)
    if n == 0:
        print("  ⚠️ 사건이 없다")
        return 1
    바닥 = sum(1 for x in 사건 if x["도달"]) / n * 100
    print(f"  사건 {n:,}건 · 기본 도달률 {바닥:.1f}%\n")

    def 재기(a, 라, 폭=26):
        if len(a) < 20:
            print(f"    {라:<{폭}}{len(a):>6}건  표본 부족")
            return
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        묶 = {}
        for x in a:
            묶.setdefault(x["날"][:4], []).append(x["결과"])
        전 = 플 = 0
        for y, arr in 묶.items():
            if len(arr) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        별 = "⭐" if (abs(d2 - 바닥) > 5 and 전 >= 7
                     and 플 / 전 >= 2 / 3) else "  "
        print(f"    {라:<{폭}}{len(a):>6}건{d2:>8.1f}%{d2-바닥:>+8.1f}%p"
              f"{st.mean([x['결과'] for x in a]):>+9.2f}%{f'{플}/{전}':>7}{별}")

    머 = (f"    {'조건':<26}{'표본':>8}{'도달률':>8}{'기본대비':>8}"
          f"{'평균':>9}{'연도별':>7}")

    print("  ══ A **며칠째 연속 하락 중인가** ══")
    print(머)
    for lo, hi, 라 in ((0, 1, "0일 (어제는 올랐다)"), (1, 2, "1일째"),
                       (2, 3, "2일째"), (3, 4, "3일째"),
                       (4, 99, "4일 이상")):
        재기([x for x in 사건 if lo <= x["연속"] < hi], 라)

    print(f"\n  ══ B ⭐ **한 방에 빠졌나 서서히 빠졌나** ══")
    print("     20일 낙폭 중 가장 큰 하루가 차지하는 몫")
    print(머)
    for lo, hi, 라 in ((0, 25, "25% 미만 (서서히)"), (25, 50, "25~50%"),
                       (50, 80, "50~80%"), (80, 9e9, "80%↑ (한 방에)")):
        재기([x for x in 사건 if x["몫"] is not None
              and lo <= x["몫"] < hi], 라)

    print(f"\n  ══ C **빠지는 속도** (최근 5일 − 앞 15일) ══")
    print(머)
    for lo, hi, 라 in ((-9e9, -10, "최근에 훨씬 빨라짐"),
                       (-10, -3, "빨라짐"), (-3, 3, "비슷"),
                       (3, 9e9, "느려짐")):
        재기([x for x in 사건 if x["가속"] is not None
              and lo <= x["가속"] < hi], 라)

    print(f"\n  ══ D **어제·그제도 갭 하락이었나** ══")
    print(머)
    for k, 라 in ((0, "오늘만 갭 하락"), (1, "어제도"), (2, "이틀 다")):
        재기([x for x in 사건 if x["앞갭"] == k], 라)

    print(f"\n  ══ E ⭐ **더 긴 기간** (지금은 20일만 본다) ══")
    print(머)
    for lo, hi, 라 in ((-9e9, -40, "60일 −40%↓"), (-40, -25, "−25~−40%"),
                       (-25, -10, "−10~−25%"), (-10, 9e9, "−10%보다 얕음")):
        재기([x for x in 사건 if x["낙60"] is not None
              and lo <= x["낙60"] < hi], f"60일 {라.split(' ')[-1]}")
    print()
    for lo, hi, 라 in ((-9e9, -50, "120일 −50%↓"), (-50, -30, "−30~−50%"),
                       (-30, -10, "−10~−30%"), (-10, 9e9, "−10%보다 얕음")):
        재기([x for x in 사건 if x["낙120"] is not None
              and lo <= x["낙120"] < hi], f"120일 {라.split(' ')[-1]}")

    print(f"\n  ══ F **20일선 아래에 며칠째** ══")
    print(머)
    for lo, hi, 라 in ((0, 3, "2일 이하"), (3, 8, "3~7일"),
                       (8, 20, "8~19일"), (20, 9e9, "20일 이상")):
        재기([x for x in 사건 if lo <= x["선아래"] < hi], 라)

    # ══ G 자본 시뮬 ══
    print(f"\n  ══ G ⭐⭐ **자본 시뮬** — 아홉 번 다 여기서 졌다 ══")
    묶날 = {}
    for x in 사건:
        묶날.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]

    def 시뮬(거름, 라, 끝년=None, 폭=30):
        현금, 보유, 곡, 산 = 5_000_000.0, [], [], 0
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
            골 = [x for x in 묶날.get(i, []) if 거름(x)]
            for x in sorted(골, key=lambda z: z["상갭"])[:확정["종목수"]]:
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
        c = ((끝 / 5_000_000) ** (1 / yr) - 1) * 100
        피 = 낙2 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙2 = min(낙2, (v / 피 - 1) * 100)
        print(f"    {라:<{폭}}{끝:>15,.0f}원{c:>+9.2f}%{낙2:>8.1f}%{산:>7}건")

    print(f"    {'전략':<30}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")
    for 끝년 in (None, "2024"):
        if 끝년:
            print(f"\n    ⚠️ 2025·26 제외")
        시뮬(lambda x: True, "원판", 끝년=끝년)
        시뮬(lambda x: x["연속"] >= 2, "+ 2일 이상 연속 하락만", 끝년=끝년)
        시뮬(lambda x: x["몫"] is not None and x["몫"] < 50,
             "+ 서서히 빠진 것만 (한 방 아님)", 끝년=끝년)
        시뮬(lambda x: x["몫"] is not None and x["몫"] >= 50,
             "+ 한 방에 빠진 것만", 끝년=끝년)
        시뮬(lambda x: x["낙60"] is None or x["낙60"] > -40,
             "+ 60일 −40% 넘게 안 빠진 것만", 끝년=끝년)
        시뮬(lambda x: x["선아래"] < 8, "+ 20일선 아래 7일 이하만", 끝년=끝년)

    # ══ H 요일 ══ (2026-09-04 추가)
    # ⚠️ 왜 여기서 또 재나: intraday_lab ⑤절에서 **평균**으로는 이미 봤다
    #    (월 -0.0672% 꼴찌 · 화 +0.1513% 1등, 관측치 580만).
    #    그걸 보고 「월요일 빼자」를 **평균만으로 기각**했는데,
    #    우리는 「평균 수익은 돈이 아니다」로 아홉 번 데였다. **돈으로 다시 잰다**
    # ⚠️ 매수일은 x["날"]이다 (신호는 그 전날 종가)
    def 요일(x):
        try:
            return dt.date(int(x["날"][:4]), int(x["날"][4:6]),
                           int(x["날"][6:])).weekday()
        except (ValueError, TypeError, KeyError):
            return -1

    print(f"\n  ══ H **요일** — 평균으로는 월요일이 꼴찌였다. 돈으로는? ══")
    print(f"    {'전략':<30}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")
    for 끝년 in (None, "2024"):
        if 끝년:
            print(f"\n    ⚠️ 2025·26 제외")
        시뮬(lambda x: True, "원판 (요일 안 가림)", 끝년=끝년)
        for w, 이름 in enumerate(("월", "화", "수", "목", "금")):
            시뮬(lambda x, _w=w: 요일(x) != _w,
                 f"+ {이름}요일 매수 **빼면**", 끝년=끝년)
        시뮬(lambda x: 요일(x) in (1, 2), "+ 화·수만 산다", 끝년=끝년)

    print("\n  읽는 법")
    print("    - H에서 **원판보다 끝 자산이 커야** 요일 조건을 건다.")
    print("      평균이 나쁜 요일을 빼도 **살 기회가 20%씩 사라진다** —")
    print("      그 손해가 평균 개선보다 크면 안 쓴다")
    print("    - 흐름 조건은 대개 **살 기회를 줄이는 쪽**이다.")
    print("      그런 조건은 지금까지 **아홉 번 다 졌다**")
    print("    - G에서 원판을 못 이기면 **안 쓴다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
