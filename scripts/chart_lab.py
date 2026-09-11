#!/usr/bin/env python3
r"""
chart_lab.py — **차트(기술적) 분석 전면 재검증** (2026-09-02 · 10차)

⚠️⚠️ **왜 다시 하나.** `stability_lab`에서 기술지표 8종을 이미 쟀는데 **전부 음수**였다.
   그런데 그건 **시총가중 잣대**였다 — 2차에서 시총가중이 착시를 만드는 게 확인됐다.
   **동일가중으로 다시 재고, 안 해본 것을 더한다.**

⚠️ 그리고 `stability_lab` 결과를 상대 순위로 읽으면 **한국은 「반전」 성향**이 보였다:
```
20일선  아래(−0.13) > 위(−1.86)      RSI  과매도(−0.87) > 과매수(−2.07)
볼린저   하단(−0.46) > 상단(−2.19)
```
→ **「돌파하면 산다」가 아니라 「빠진 걸 산다」**를 가리킨다. 그 방향으로 조합해 본다.

**재는 것**
```
① 추세      골든크로스(20>60 전환) · 데드크로스 · 20일선 위/아래 · 60일선 위/아래
② 모멘텀    RSI 과매수/과매도 · 스토캐스틱 · MACD 시그널 교차
③ 변동성    볼린저 상단/하단/스퀴즈(밴드 수축)
④ 거래량    OBV 방향 · 거래량 급증(3배) · **돌파 × 거래량 교차**
⑤ 갭       갭상승 3%↑ · 갭하락 3%↓
⑥ 캔들      망치형 · 장악형 · 도지
⑦ **반전 조합**  볼린저 하단 + RSI 과매도 + 20일선 아래  ← 위 관찰에서 나온 가설
```

⚠️⚠️ **다중검정 계산을 반드시 붙인다**(9차에서 배웠다).
   축이 N개면 아무 효과가 없어도 **N × 25%** 개가 「학습·검증 둘 다 +」로 나온다.

⚠️ 잣대 **동일가중** · 매수 D+1 종가 · D+20 보유 · 오염 제외 · 16.7년.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = 20
_경계 = "20180101"
_MIN = 400


def _주가():
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"]); 시 = float(v["시가"])
                고 = float(v["고가"]); 저 = float(v["저가"])
                if 종 <= 0 or 시 <= 0:
                    continue
                하루[c] = (종, 시, 고, 저, float(v.get("시총") or 0),
                           float(v.get("거래대금") or 0), float(v.get("거래량") or 0))
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def _ema(vals, n, 앞=None):
    k = 2 / (n + 1)
    e = 앞 if 앞 is not None else vals[0]
    for v in vals:
        e = v * k + e * (1 - k)
    return e


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    기본 = O._기본()
    종, 고계, 저계, 량계, 자리 = {}, {}, {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종.setdefault(c, []).append(v[0])
            고계.setdefault(c, []).append(v[2])
            저계.setdefault(c, []).append(v[3])
            량계.setdefault(c, []).append(v[6])
            자리.setdefault(c, {})[d] = len(종[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종):,}", flush=True)

    통 = {}

    def 담(축, 구간, v):
        통.setdefault((축, 구간), []).append(v)

    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + _H >= len(날):
            continue
        구간 = "학습" if d1 < _경계 else "검증"
        s1 = 주가[d1]
        후보, 수익 = [], []
        for code, v in s1.items():
            if v[4] < O._MIN_MC or v[5] < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            m = 주가[날[i + 1]].get(code)
            e = 주가[날[i + 1 + _H]].get(code)
            if not m or not e:
                continue
            # ⚠️⚠️ 기준선 불일치 버그(2026-09-02 발견).
            #    기준선은 「모든 후보」로 계산하는데 집계는 「상장 250일 넘은 것」만 했다.
            #    → 신규상장 종목이 기준에만 들어가 **모든 축이 +0.05% 정도 밀렸다.**
            #    여기서 미리 걸러 기준선과 집계 대상을 **같게** 맞춘다.
            if ((자리.get(code) or {}).get(d1) or 0) < 250:
                continue
            후보.append((code, v, e[0] / m[0] - 1))
            수익.append(e[0] / m[0] - 1)
        if len(후보) < 100:
            continue
        기준 = st.mean(수익)

        for code, v, r in 후보:
            c1, 시, 고, 저, 시총, 대금, 량 = v
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종[code]
            초 = (r - 기준) * 100

            s20 = st.mean(sq[k - 19:k + 1])
            s60 = st.mean(sq[k - 59:k + 1])
            s20b = st.mean(sq[k - 20:k])
            s60b = st.mean(sq[k - 60:k])
            sd20 = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼상, 볼하 = s20 + 2 * sd20, s20 - 2 * sd20
            폭 = (볼상 - 볼하) / s20 * 100
            폭b = None
            if k >= 80:
                s20c = st.mean(sq[k - 39:k - 19])
                sdc = st.pstdev(sq[k - 39:k - 19]) or 1e-9
                폭b = (4 * sdc) / s20c * 100
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            최고14 = max(고계[code][k - 13:k + 1])
            최저14 = min(저계[code][k - 13:k + 1])
            스토 = (c1 - 최저14) / (최고14 - 최저14) * 100 if 최고14 > 최저14 else 50
            e12, e26 = _ema(sq[max(0, k - 60):k + 1], 12), _ema(sq[max(0, k - 60):k + 1], 26)
            macd = e12 - e26
            e12b, e26b = _ema(sq[max(0, k - 61):k], 12), _ema(sq[max(0, k - 61):k], 26)
            macdb = e12b - e26b
            평량 = st.mean(량계[code][k - 20:k]) or 1
            전종 = sq[k - 1]
            갭 = (시 / 전종 - 1) * 100
            몸통 = abs(c1 - 시)
            전체 = 고 - 저 or 1e-9
            아래꼬리 = min(c1, 시) - 저

            축들 = []
            축들.append(("A 골든크로스(20>60 전환)", s20 > s60 and s20b <= s60b))
            축들.append(("A 데드크로스(20<60 전환)", s20 < s60 and s20b >= s60b))
            축들.append(("A 20일선 위", c1 > s20))
            축들.append(("A 20일선 아래", c1 <= s20))
            축들.append(("A 60일선 위", c1 > s60))
            축들.append(("B RSI 과매수(70↑)", rsi >= 70))
            축들.append(("B RSI 과매도(30↓)", rsi <= 30))
            축들.append(("B 스토캐스틱 80↑", 스토 >= 80))
            축들.append(("B 스토캐스틱 20↓", 스토 <= 20))
            축들.append(("B MACD 상향교차", macd > 0 and macdb <= 0))
            축들.append(("B MACD 하향교차", macd < 0 and macdb >= 0))
            축들.append(("C 볼린저 상단 밖", c1 > 볼상))
            축들.append(("C 볼린저 하단 밖", c1 < 볼하))
            축들.append(("C 볼린저 스퀴즈(밴드축소)", 폭b is not None and 폭 < 폭b * 0.7))
            축들.append(("D 거래량 3배↑", 량 >= 평량 * 3))
            축들.append(("D 거래량 0.5배↓", 량 <= 평량 * 0.5))
            축들.append(("E 갭상승 3%↑", 갭 >= 3))
            축들.append(("E 갭하락 3%↓", 갭 <= -3))
            축들.append(("F 망치형(아래꼬리 길다)", 아래꼬리 > 전체 * 0.6 and 몸통 < 전체 * 0.3))
            축들.append(("F 도지(몸통 작다)", 몸통 < 전체 * 0.1))
            # ⭐ 교차: 돌파 × 거래량
            축들.append(("G 볼린저상단 + 거래량3배", c1 > 볼상 and 량 >= 평량 * 3))
            축들.append(("G 볼린저상단 + 거래량평범", c1 > 볼상 and 량 < 평량 * 1.5))
            축들.append(("G 20일선위 + 거래량3배", c1 > s20 and 량 >= 평량 * 3))
            # ⭐ 반전 조합 (stability_lab 관찰에서 나온 가설)
            반전2 = (c1 < 볼하) and rsi <= 30
            반전3 = 반전2 and c1 <= s20
            축들.append(("H 반전2 (볼린저하단+RSI과매도)", 반전2))
            축들.append(("H 반전3 (+20일선 아래)", 반전3))
            축들.append(("H 반전3 + 대형주", 반전3 and 시총 >= 1e12))
            축들.append(("H 반전3 + 거래량3배", 반전3 and 량 >= 평량 * 3))

            for 이름, 참 in 축들:
                if 참:
                    담(이름, 구간, 초)
            담("0 전 종목(기준선)", 구간, 초)
        if i % 400 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    축이름 = sorted({a for (a, _) in 통})
    print(f"\n  D+{_H} · 동일가중 대비 초과수익 · 16.7년\n")
    print(f"  {'축':<30}{'전체':>17}{'학습':>17}{'검증':>17}  판정")
    둘다 = 0
    잰것 = 0
    for a in 축이름:
        ha = 통.get((a, "학습")) or []
        va = 통.get((a, "검증")) or []
        모 = ha + va
        if len(모) < _MIN:
            continue
        def f(x):
            return f"{st.mean(x):+.3f}% ({len(x)//1000}k)" if len(x) >= _MIN // 2 else "-"
        판 = ""
        if len(ha) >= _MIN // 2 and len(va) >= _MIN // 2:
            잰것 += 1
            h, v = st.mean(ha), st.mean(va)
            if h > 0 and v > 0:
                판 = "⭐ 둘 다 +"
                둘다 += 1
            elif h < 0 and v < 0:
                판 = "❌ 둘 다 −"
            else:
                판 = "· 뒤집힘"
        print(f"  {a:<30}{f(모):>17}{f(ha):>17}{f(va):>17}  {판}")

    print(f"\n  ══ 다중검정 계산 ══")
    print(f"    잰 축 {잰것}개 · 아무 효과 없어도 「둘 다 +」 기대 {잰것*0.25:.1f}개")
    print(f"    **실제 {둘다}개**  → " +
          ("⚠️ 우연 수준이거나 그 이하. 신호 없음" if 둘다 <= 잰것 * 0.25
           else "우연 기대보다 많다. 살펴볼 값어치가 있다"))
    print("\n  읽는 법")
    print("    - 동일가중 기준이라 '0 전 종목'이 0에 가까워야 정상이다")
    print("    - ⭐만 후보다. 그중에서도 표본이 큰 것을 본다")
    print("    - G(돌파×거래량)와 H(반전 조합)가 이번에 처음 재는 것이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
