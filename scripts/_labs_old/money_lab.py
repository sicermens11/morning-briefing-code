#!/usr/bin/env python3
r"""
money_lab.py — **노는 83%를 어떻게 쓸 것인가** (2026-09-03 · 62차)

⚠️⚠️ **왜 필요한가.** 61차까지로 신호는 섰다. 그런데 **자금의 17%만 쓴다.**
```
우리 재무 신호 (10.4년)   연 +18.38% · 낙폭 -34.6% · **투입비 16.9%**
같은 기간 코스피200        연 +14.89%
  ⚠️ 그런데 코스피200의 14.89%는 **거의 전부 2025~2026** 두 해다.
     2016-04~2024-12 8.8년은 **연 +3.14%**였다.
해별로 놓으면
  2022  지수 -26.2% vs 신호  +2.74%   → +28.9%p   폭락장에서 벌었다
  2024  지수 -11.2% vs 신호 +18.49%   → +29.7%p   하락장에서 벌었다
  2025  지수 +90.7% vs 신호 +23.11%   → **-67.6%p**  강세장에선 크게 졌다 (83%가 현금이라)
```

## 사용자가 **넷 다** 보라고 했다
```
① 평소엔 지수, 신호 뜨면 갈아탄다
② 한 종목에 더 크게 넣는다
③ 신호 조건을 낮춰 자금을 더 쓴다
④ 다른 신호를 더 찾는다   ← 63차에서 따로 한다
```

⚠️⚠️ **여기서 처음으로 유동성 상한을 넣는다.** 61차에서 쟀다:
   뽑힌 종목 거래대금 중앙 7.8억 · 하위25% 4.2억
   → **종목당 200만원까지는 거래대금의 1%를 안 넘는다**(7.8%만 넘음).
   1,000만원이면 60.8%가 넘는다. ⇒ 한 종목에 **거래대금의 1%**를 상한으로 건다.

⚠️⚠️ **지수는 배당을 뺀 값이다.** KODEX 200 TR은 배당 재투자라 **연 1.5~2%p 높다.**
   여기 지수 성적은 **낮게 잡힌 것**이니 그만큼 감안해서 읽어야 한다.
⚠️ 2026년 지수에 이상치가 있다(20260731 +19.98%). **2024-12까지로 자른 판**을 같이 낸다.
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


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    지수 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        v = (d.get("지수") or {}).get("코스피 200") or {}
        c = v.get("종가")
        if c:
            try:
                지수[d["기준일"]] = float(c)
            except (TypeError, ValueError):
                pass
    갭표, 시장갭, 앞종 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d["기준일"]] = 하루
        if len(하루) >= 100:
            시장갭[d["기준일"]] = st.median(list(하루.values()))

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

    # ── 후보 (조건 완화판까지 담는다) ──
    후보 = []   # (매수일i, 매수일, code, 상대갭, 시장갭, 볼, 20일, 재무, 전날거래대금, 매수단가)
    for i, d1 in enumerate(날):
        if i < 260 or i + 61 >= len(날):
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
            if g is None or (g - 시갭) > -2:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            fm = 재무값(code, d1)
            if not fm:
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -0.5 or sq[k - 20] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            if r20 > 0:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            후보.append((i + 1, 다음, code, g - 시갭, 시갭, 볼, r20, fm, 대금, 매수))
        if i % 800 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)
    print(f"  후보 {len(후보):,}건\n", flush=True)

    # ⚠️ 고정 숫자 조건 (61차 B에서 확인 — 데이터에서 문턱을 뽑지 않는다)
    def 좋재무(fm):
        return (fm.get("잉여금비율", -9e9) >= 30 and fm.get("부채비율", 9e9) <= 80
                and fm.get("흑자") == 1.0)

    def 고르기(rg=-3, bo=-1.0, rr=-10):
        return lambda x: (x[3] <= rg and x[5] <= bo and x[6] <= rr and 좋재무(x[7]))

    날인 = {d: i for i, d in enumerate(날)}

    def 시뮬(골, 비중, 보유, 지수기본, 이름, 끝날="20260902", 초기=5_000_000.0,
             유동상한=0.01):
        """지수기본=True면 **남는 돈으로 지수를 산다.**
        ⚠️ 유동상한: 한 종목에 **전날 거래대금의 이 비율**까지만 넣는다."""
        살것 = {}
        for x in 후보:
            if x[1] < _시작 or x[1] > 끝날:
                continue
            if 골(x):
                살것.setdefault(x[1], []).append(x)
        쓸날 = [d for d in 날 if _시작 <= d <= 끝날]
        현금 = 초기
        개별 = []           # (청산i, 투자금, 매수단가, code)
        지수주 = 0.0         # 지수에 넣은 「단위」 — 평가액 = 지수주 × 지수값
        기록, 투입 = [], []
        막힘 = 0
        for d in 쓸날:
            i = 날인[d]
            ix = 지수.get(d)
            # 1) 만기 청산
            남 = []
            for 청산, 금, 단가, code in 개별:
                if 청산 <= i:
                    v = 주가[날[min(청산, len(날) - 1)]].get(code)
                    현금 += (금 * (v[0] / 단가) if v else 금) * (1 - _비용 / 100)
                else:
                    남.append((청산, 금, 단가, code))
            개별 = 남
            # 2) 평가
            평가 = 현금 + (지수주 * ix if ix else 0)
            for 청산, 금, 단가, code in 개별:
                v = 주가[d].get(code)
                평가 += 금 * (v[0] / 단가) if v else 금
            # 3) 오늘 살 것
            오늘 = 살것.get(d) or []
            for x in 오늘:
                쓸 = min(평가 * 비중, x[8] * 유동상한)
                if 쓸 < 10_000:
                    continue
                if 쓸 > x[8] * 유동상한:
                    막힘 += 1
                # ⚠️ 지수를 들고 있으면 **그만큼 팔아서** 개별 종목을 산다
                if 쓸 > 현금 and 지수기본 and ix and 지수주 > 0:
                    필요 = 쓸 - 현금
                    팔 = min(필요, 지수주 * ix)
                    지수주 -= 팔 / ix
                    현금 += 팔 * (1 - _비용 / 100)
                if 쓸 > 현금:
                    continue
                현금 -= 쓸
                개별.append((min(i + 보유, len(날) - 1), 쓸, x[9], x[2]))
            # 4) 남는 돈으로 지수
            if 지수기본 and ix and 현금 > 평가 * 0.02:
                넣 = 현금 - 평가 * 0.01
                지수주 += 넣 / ix * (1 - _비용 / 100)
                현금 -= 넣
            기록.append((d, 평가))
            개별금 = sum(금 for _, 금, _, _ in 개별)
            투입.append(개별금 / 평가 if 평가 > 0 else 0)
        마지막 = 기록[-1][1] if 기록 else 초기
        해 = len(기록) / 245
        연 = ((마지막 / 초기) ** (1 / 해) - 1) * 100 if 마지막 > 0 and 해 > 0 else -100
        최고, 낙폭 = 초기, 0.0
        for _, v in 기록:
            최고 = max(최고, v)
            낙폭 = min(낙폭, v / 최고 - 1)
        해별 = {}
        for d, v in 기록:
            해별.setdefault(d[:4], []).append(v)
        플 = 전 = 0
        for y in sorted(해별):
            a = 해별[y]
            if len(a) < 60:
                continue
            전 += 1
            플 += 1 if a[-1] > a[0] else 0
        print(f"    {이름:<36}{마지막:>13,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{sum(투입)/max(1,len(투입))*100:>8.1f}%{f'{플}/{전}':>8}")
        return 연

    def 지수만(끝날, 초기=5_000_000.0):
        k = [d for d in 날 if _시작 <= d <= 끝날 and d in 지수]
        if len(k) < 100:
            return
        마지막 = 초기 * (지수[k[-1]] / 지수[k[0]])
        해 = len(k) / 245
        연 = ((마지막 / 초기) ** (1 / 해) - 1) * 100
        최고, 낙폭 = 지수[k[0]], 0.0
        for d in k:
            최고 = max(최고, 지수[d])
            낙폭 = min(낙폭, 지수[d] / 최고 - 1)
        해별 = {}
        for d in k:
            해별.setdefault(d[:4], []).append(지수[d])
        플 = 전 = 0
        for y in sorted(해별):
            a = 해별[y]
            if len(a) < 60:
                continue
            전 += 1
            플 += 1 if a[-1] > a[0] else 0
        print(f"    {'지수만 (코스피200 · 배당 제외)':<36}{마지막:>13,.0f}원"
              f"{연:>+8.2f}%{낙폭*100:>9.1f}%{'100.0%':>8}{f'{플}/{전}':>8}")

    for 끝날, 라 in (("20260902", "2016-04 ~ 2026-09 (10.4년)"),
                     ("20241230", "2016-04 ~ 2024-12 (8.8년) — **2025·2026 뺀 판**")):
        print(f"\n  ══════ {라} ══════")
        print(f"    {'전략':<36}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
              f"{'개별투입':>8}{'연도별':>8}")
        지수만(끝날)
        print("    ── ② 신호만 · 종목당 비중을 흔든다 ──")
        for 비 in (0.10, 0.20, 0.34, 0.50):
            시뮬(고르기(), 비, 20, False,
                 f"신호만 · 종목당 {비*100:.0f}% · D+20", 끝날)
        print("    ── ① **평소엔 지수, 신호 뜨면 갈아탄다** ──")
        for 비 in (0.10, 0.20, 0.34):
            시뮬(고르기(), 비, 20, True,
                 f"**지수+신호** · 종목당 {비*100:.0f}% · D+20", 끝날)
        시뮬(고르기(), 0.20, 40, True, "**지수+신호** · 20% · **D+40**", 끝날)
        print("    ── ③ 조건을 낮춰 자금을 더 쓴다 (지수 기본) ──")
        for rg, bo, rr, 라2 in ((-3, -1.0, -10, "기준"),
                                 (-2, -1.0, -10, "상대−2"),
                                 (-3, -0.7, -5, "볼−0.7·20일−5"),
                                 (-2, -0.5, 0, "상대−2·볼−0.5·20일0")):
            시뮬(고르기(rg, bo, rr), 0.20, 20, True,
                 f"지수+신호 · **{라2}**", 끝날)
        # ⚠️⚠️ **63차에서 나온 것.** 「재무 우량 + 시장 -0.6% 하락일」이 유일하게 살아남았다
        #   (+2.03% · 64.9% · 10/11해 · **겹침률 29.9%**). 섞으면 자금을 1.7배 쓴다.
        #   ⚠️ 평균은 내려간다(+10.05% -> +2.03%). **총액이 느는지는 해봐야 안다.**
        print("    ── ④ **63차 새 신호를 섞는다** (재무+시장-0.6%↓) ──")
        약 = lambda x: 좋재무(x[7]) and x[4] < -0.6      # noqa: E731
        둘 = lambda x: 고르기()(x) or 약(x)              # noqa: E731
        for 비 in (0.10, 0.20):
            시뮬(약, 비, 20, False,
                 f"**약한 신호만** · 종목당 {비*100:.0f}%", 끝날)
            시뮬(둘, 비, 20, False,
                 f"**둘 합침** · 종목당 {비*100:.0f}%", 끝날)
        시뮬(둘, 0.10, 40, False, "**둘 합침** · 10% · D+40", 끝날)
        시뮬(고르기(), 0.10, 20, False, "(견줌) 지금 신호만 · 10%", 끝날)

    print("\n  읽는 법")
    print("    - ⚠️ **지수는 배당을 뺀 값이다.** KODEX 200 TR은 연 1.5~2%p 높다")
    print("    - **개별투입** = 개별 종목에 들어간 비율. 나머지는 지수나 현금이다")
    print("    - 아래 판(2024-12까지)이 **지수가 평범했던 8.8년**이다. 여기가 진짜 시험이다")
    print("    - ⚠️ 한 종목에 **전날 거래대금의 1%**를 상한으로 걸었다(61차 유동성 결과)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
