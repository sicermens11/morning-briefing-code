#!/usr/bin/env python3
r"""
small_lab.py — **소액으로도 되나 (1주 단위 제약)** (2026-09-03 · 87차)

⚠️⚠️ **사용자 지적.**
   *"보통 개인은 하루에 200만원씩 투자 못하니까 소액으로 매수하는 경우도
     충분히 테스트되어야 해"*
   *"실제 매수를 한다고 했을 때는 하루 10만원 이내 1만원 5만원도 괜찮지?"*

## 지금까지 모든 시뮬이 놓친 것
```
자본 시뮬은 **소수점 단위로 산다**고 가정했다 (금액을 그냥 나눴다)
실제로는 **1주 단위**로만 산다:
  1만원인데 주가가 12,000원 -> **1주도 못 산다**
  1만원인데 주가가  3,000원 -> 3주 = 9,000원 (원하는 1만원이 아니다)
⇒ 소액일수록 **원하는 비중을 못 맞춘다.** 그게 성적에 얼마나 영향을 주나
```

⚠️⚠️⚠️ **53차에서 이 부분으로 버그를 냈다.**
```
「주수는 **원본** 시가로, 금액은 **수정** 시가로」 섞어 계산해
10만원 사려다 1,000만원을 썼다.
⇒ 이번엔 **명확히 나눈다**:
   주수 계산   **원본 주가** (실제로 그 값에 산다)
   수익률 계산  **수정 주가 비율** (액면분할을 반영해야 맞다)
   실제 투자금 = 주수 x 원본 주가
```

## 재는 것
```
A 주가 분포     우리 신호 종목이 얼마짜리인가
B ⭐ **1주도 못 사는 비율** — 자산 규모별로
C 자산 규모별 성적 — 10만 / 30만 / 50만 / 100만 / 300만 / 500만 / 1000만원
D 한 종목 최소 금액을 정하면 (1만 / 3만 / 5만 / 10만원)
E ⭐ **수수료 최소금액**이 있으면 소액이 얼마나 불리한가
```
⚠️ 매도는 76차 규칙(목표 +20% 지정가 · 최대 D+40 · 손절 없음).
⚠️ 하루 최대 2종목 (77차).
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
_목표 = 20.0
_최대보유 = 40


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    날인 = {d: i for i, d in enumerate(날)}
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    # ⚠️ **원본 시가**를 따로 담는다 — 주수 계산에 쓴다
    원본시, 비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                if min(종, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            원본시.setdefault(d8, {})[c] = 시
            비.setdefault(d8, {})[c] = (시 / 종, 고 / 종)
            p = 앞종.get(c)
            앞종[c] = 종
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
        if i < 260 or i + 1 + _최대보유 >= len(날):
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
            # ⚠️⚠️ 주수는 **원본 시가**로, 수익률은 **수정 비율**로 (53차 버그 방지)
            원시 = (원본시.get(다음) or {}).get(code)
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not 원시 or not b0 or not v0 or 원시 <= 0:
                continue
            수정매수 = v0[0] * b0[0]
            if 수정매수 <= 0:
                continue
            결과, 며칠 = None, _최대보유
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    break
                if vv[0] * bb2[1] >= 수정매수 * (1 + _목표 / 100):
                    결과, 며칠 = _목표 - _비용, max(1, h)
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과 = (끝[0] / 수정매수 - 1) * 100 - _비용
            사건.append({"날": 다음, "code": code, "원시": 원시,
                        "결과": 결과, "며칠": 며칠, "상대갭": g - 시갭,
                        "대금": 대금, "i": i + 1})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    날별 = {}
    for x in 사건:
        날별.setdefault(x["날"], []).append(x)
    print(f"  사건 {len(사건):,}건 · 신호일 {len(날별)}일 · {년수:.1f}년\n",
          flush=True)

    # ══ A 주가 분포 ══
    v = sorted(x["원시"] for x in 사건)
    print("  ══ A **신호 종목의 실제 주가** (매수 시점) ══")
    for q, 라 in ((0, "최저"), (10, "하위10%"), (25, "하위25%"), (50, "중앙"),
                  (75, "상위25%"), (90, "상위10%"), (100, "최고")):
        print(f"    {라:<10}{v[min(len(v)-1, len(v)*q//100)]:>12,.0f}원")

    # ══ B 1주도 못 사는 비율 ══
    print("\n  ══ B ⭐ **한 종목에 얼마를 넣으면 1주도 못 사나** ══")
    print(f"    {'한 종목 금액':<16}{'1주도 못 삼':>14}{'1주만':>10}"
          f"{'2~4주':>10}{'5주 이상':>10}")
    for 금 in (10_000, 30_000, 50_000, 100_000, 200_000, 500_000):
        못 = sum(1 for x in 사건 if x["원시"] > 금)
        한 = sum(1 for x in 사건 if 금 / x["원시"] >= 1 and 금 / x["원시"] < 2)
        둘 = sum(1 for x in 사건 if 2 <= 금 / x["원시"] < 5)
        다 = sum(1 for x in 사건 if 금 / x["원시"] >= 5)
        n = len(사건)
        print(f"    {금:>10,}원  {못/n*100:>12.1f}%{한/n*100:>9.1f}%"
              f"{둘/n*100:>9.1f}%{다/n*100:>9.1f}%")

    # ══ C·D 자산 규모별 시뮬 ══
    def 시뮬(초기, 이름, 비중=0.20, 최소금액=0, 수수료최소=0, 끝날="20260902"):
        """⚠️ **주수는 원본 주가로 계산한다.** 1주 미만은 못 산다."""
        현금, 보유, 기록 = float(초기), [], []
        못산, 산것 = 0, 0
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            남 = []
            for 청산i, 금, r in 보유:
                if 청산i <= i:
                    현금 += 금 * (1 + r / 100)
                else:
                    남.append((청산i, 금, r))
            보유 = 남
            평가 = 현금 + sum(금 for _, 금, _ in 보유)
            for x in sorted(날별.get(d) or [], key=lambda z: z["상대갭"])[:2]:
                쓸 = min(평가 * 비중, x["대금"] * 0.01)
                if 최소금액 and 쓸 < 최소금액:
                    쓸 = 최소금액
                if 쓸 > 현금:
                    continue
                # ⚠️⚠️ **1주 단위**. 주수는 원본 주가로
                주수 = int(쓸 // x["원시"])
                if 주수 < 1:
                    못산 += 1
                    continue
                실제 = 주수 * x["원시"]
                # ⚠️ 수수료 최소금액이 있으면 소액이 불리하다
                수수 = max(실제 * 0.0015, 수수료최소) if 수수료최소 else 0
                if 실제 + 수수 > 현금:
                    continue
                현금 -= (실제 + 수수)
                산것 += 1
                # 매도 시 수수료도
                순 = x["결과"] - (수수료최소 / 실제 * 100 if 수수료최소 else 0)
                보유.append((min(x["i"] + x["며칠"], len(날) - 1), 실제, 순))
            기록.append((d, 평가))
        마지막 = 기록[-1][1] if 기록 else float(초기)
        해 = len(기록) / 245
        연 = ((마지막 / 초기) ** (1 / 해) - 1) * 100 if 마지막 > 0 else -100
        최고, 낙폭 = float(초기), 0.0
        for _, v2 in 기록:
            최고 = max(최고, v2)
            낙폭 = min(낙폭, v2 / 최고 - 1)
        해별 = {}
        for d, v2 in 기록:
            해별.setdefault(d[:4], []).append(v2)
        플 = 전 = 0
        for y in sorted(해별):
            a = 해별[y]
            if len(a) < 60:
                continue
            전 += 1
            플 += 1 if a[-1] > a[0] else 0
        print(f"    {이름:<26}{마지막:>15,.0f}원{연:>+8.2f}%{낙폭*100:>8.1f}%"
              f"{산것:>7}건{못산:>7}건{f'{플}/{전}':>8}")

    머 = (f"    {'전략':<26}{'끝 자산':>16}{'연평균':>8}{'낙폭':>8}"
          f"{'산 것':>7}{'못산':>7}{'연도별':>8}")
    print("\n  ══ C ⭐ **자산 규모별** (자산의 20%씩 · 1주 단위) ══")
    print(머)
    for 초 in (100_000, 300_000, 500_000, 1_000_000, 3_000_000,
               5_000_000, 10_000_000, 30_000_000):
        시뮬(초, f"자산 {초/10000:,.0f}만원")

    print("\n  ══ D **한 종목 최소 금액을 정하면** (자산 100만원) ══")
    print("     ⚠️ 비중 20%면 20만원인데, 최소금액을 더 낮게 잡으면 더 자주 살 수 있다")
    print(머)
    for 최소 in (0, 10_000, 30_000, 50_000, 100_000):
        시뮬(1_000_000, f"최소 {최소/10000:,.0f}만원" if 최소 else "최소 없음",
             최소금액=최소)

    print("\n  ══ E ⭐ **수수료 최소금액**이 있으면 (자산 100만원) ══")
    print("     ⚠️ 증권사에 따라 건당 최소 수수료가 있다. 소액일수록 불리하다")
    print(머)
    for 수 in (0, 100, 500, 1000, 2000):
        시뮬(1_000_000, f"건당 최소 {수:,}원" if 수 else "최소 수수료 없음",
             수수료최소=수)

    print("\n  ══ ⚠️ 2025·26 뺀 판 (자산 50만·100만·500만) ══")
    print(머)
    for 초 in (500_000, 1_000_000, 5_000_000):
        시뮬(초, f"자산 {초/10000:,.0f}만원", 끝날="20241230")

    print("\n  읽는 법")
    print("    - B에서 **1주도 못 사는 비율**이 높으면 그 금액으로는 어렵다")
    print("    - C에서 **자산이 작을수록 연평균이 떨어지면** 소액의 한계다")
    print("    - ⚠️⚠️ 주수는 **원본 주가**로, 수익률은 **수정 비율**로 계산했다")
    print("       (53차에서 이 둘을 섞어 10만원 사려다 1,000만원을 쓴 적이 있다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
