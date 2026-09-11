#!/usr/bin/env python3
r"""
regime2_lab.py — **국면을 판정해 갈아타면 나아지나** (2026-09-03 · 64차)

⚠️⚠️ **사용자 질문에서 나왔다.**
> *"1980년대는 한국, 1990년대는 미국, 2000년대는 한국, 2010년대는 미국 — 10년 단위로
>   번갈아 우세… 긴 횡보기 뒤에 특정 촉매로 급격히 몰아서 오르고 다시 조정·횡보.
>   너도 고려하고 어느 정도 예측할 수 있어?"*

## 답을 둘로 나눈다
```
❌ 10년 주기 예측    **못 한다.** 표본 4개(1980·1990·2000·2010년대)다.
                    우리가 신호에 요구한 기준(연도별 3분의 2·걷기검증)을 대면 즉시 기각된다.
                    게다가 우리 데이터는 2010년부터라 그 이전은 확인조차 못 한다.
✅ **국면 판정**     **시험할 수 있다.** 200일 이평 위/아래는 그날까지의 값으로 재니
                    look-ahead가 없다. 「지금이 어떤 국면인가」를 판정해 갈아타 본다.
```

## 확인된 사실 (같은 날 잰 것)
```
코스피200 16.7년 연 +9.57%
  상위 10일(0.24%) 제외 → 연 +3.76%    상위 20일 제외 → 연 **+0.13%**
  하위 10일 제외 → 연 +16.15%          하위 20일 제외 → 연 **+20.73%**
⇒ 「몰아서 오른다」는 **사실**이고, 그 상위일은 **폭락 직후에 몰린다**
   (20200320·24·25 = 코로나 반등 · 2026년 3~8월 급변 구간)
⇒ **나쁜 날을 피하는 효과가 좋은 날을 잡는 것보다 크다**
```

## 재는 것
```
A 국면 판정 자체가 되나 — 200일 이평 위/아래로 나눈 뒤 지수 성적이 정말 다른가
B 갈아타기      이평 위=지수 · 아래=신호 / 아래=현금 / 아래=신호+현금
C 이평 길이     60·120·200일 중 뭐가 나은가
D 우리 신호의 국면별 성적 — 급등기에 약하다는 게 사실인가
```
⚠️ **look-ahead 금지**: 그날 국면은 **전날까지의** 이평으로 판정한다.
⚠️ 지수는 배당 제외 값이다(KODEX 200 TR은 연 1.5~2%p 높다).
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
    ik = sorted(지수)
    # ⚠️ 국면: **전날까지의** N일 이평. 그날 값을 안 쓴다
    이평 = {}
    for N in (60, 120, 200):
        t = {}
        for j in range(N, len(ik)):
            t[ik[j]] = st.mean([지수[ik[x]] for x in range(j - N, j)])
        이평[N] = t

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

    def 좋재무(fm):
        return bool(fm) and fm.get("잉여금비율", -9e9) >= 30 \
            and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0

    후보 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 41 >= len(날):
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
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            fm = 재무값(code, d1)
            if not 좋재무(fm):
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
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            끝 = 주가[날[i + 21]].get(code)
            if not 끝:
                continue
            후보.append((i + 1, 다음, code, 대금, 매수,
                         (끝[0] / 매수 - 1) * 100 - _비용))
        if i % 800 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)
    print(f"  후보 {len(후보):,}건\n", flush=True)

    쓸날 = [d for d in 날 if _시작 <= d <= "20260902" and d in 지수]
    날인 = {d: i for i, d in enumerate(날)}

    def 위인가(d, N):
        m = 이평[N].get(d)
        return None if m is None else (지수[d] > m)

    # ── A 국면 판정이 되나 ──
    print("  ══ A **국면 판정 자체가 되나** — 이평 위/아래로 나눈 지수 성적 ══")
    print(f"    {'이평':<10}{'국면':<10}{'날수':>8}{'하루평균':>11}{'연환산':>11}"
          f"{'승률':>8}")
    for N in (60, 120, 200):
        for 위, 라 in ((True, "위 (강세)"), (False, "아래 (약세)")):
            r = []
            for j in range(1, len(쓸날)):
                d0, d1 = 쓸날[j - 1], 쓸날[j]
                w = 위인가(d0, N)
                if w is None or w != 위:
                    continue
                r.append(지수[d1] / 지수[d0] - 1)
            if len(r) < 100:
                continue
            m = st.mean(r)
            승 = sum(1 for x in r if x > 0) / len(r) * 100
            print(f"    {N}일{'':<6}{라:<10}{len(r):>8}{m*100:>+10.3f}%"
                  f"{((1+m)**245-1)*100:>+10.1f}%{승:>7.1f}%")

    # ── 시뮬 ──
    def 시뮬(이름, 지수언제, 신호언제, N=200, 비중=0.10, 보유=20,
             끝날="20260902", 초기=5_000_000.0):
        """지수언제(d)->bool · 신호언제(d)->bool"""
        살것 = {}
        for x in 후보:
            if _시작 <= x[1] <= 끝날:
                살것.setdefault(x[1], []).append(x)
        현금, 개별, 지수주 = 초기, [], 0.0
        기록 = []
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            ix = 지수.get(d)
            남 = []
            for 청산, 금, 단가, code in 개별:
                if 청산 <= i:
                    v = 주가[날[min(청산, len(날) - 1)]].get(code)
                    현금 += (금 * (v[0] / 단가) if v else 금) * (1 - _비용 / 100)
                else:
                    남.append((청산, 금, 단가, code))
            개별 = 남
            평가 = 현금 + (지수주 * ix if ix else 0)
            for 청산, 금, 단가, code in 개별:
                v = 주가[d].get(code)
                평가 += 금 * (v[0] / 단가) if v else 금
            # 신호 매수
            if 신호언제(d):
                for x in 살것.get(d) or []:
                    쓸 = min(평가 * 비중, x[3] * 0.01)
                    if 쓸 < 10_000:
                        continue
                    if 쓸 > 현금 and ix and 지수주 > 0:
                        팔 = min(쓸 - 현금, 지수주 * ix)
                        지수주 -= 팔 / ix
                        현금 += 팔 * (1 - _비용 / 100)
                    if 쓸 > 현금:
                        continue
                    현금 -= 쓸
                    개별.append((min(i + 보유, len(날) - 1), 쓸, x[4], x[2]))
            # 지수 보유 여부
            원함 = 지수언제(d) and ix
            if 원함 and 현금 > 평가 * 0.02:
                넣 = 현금 - 평가 * 0.01
                지수주 += 넣 / ix * (1 - _비용 / 100)
                현금 -= 넣
            elif not 원함 and 지수주 > 0 and ix:
                현금 += 지수주 * ix * (1 - _비용 / 100)
                지수주 = 0.0
            기록.append((d, 평가))
        마지막 = 기록[-1][1] if 기록 else 초기
        해 = len(기록) / 245
        연 = ((마지막 / 초기) ** (1 / 해) - 1) * 100 if 마지막 > 0 else -100
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
        print(f"    {이름:<40}{마지막:>13,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{f'{플}/{전}':>8}")

    참 = lambda d: True        # noqa: E731
    거짓 = lambda d: False     # noqa: E731
    for 끝날, 라 in (("20260902", "2016-04 ~ 2026-09 (10.4년)"),
                     ("20241230", "2016-04 ~ 2024-12 (8.8년) — **지수가 평범했던 판**")):
        print(f"\n  ══════ B 갈아타기 · {라} ══════")
        print(f"    {'전략':<40}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}{'연도별':>8}")
        시뮬("항상 지수", 참, 거짓, 끝날=끝날)
        시뮬("항상 신호 (지수 안 삼)", 거짓, 참, 끝날=끝날)
        for N in (60, 120, 200):
            시뮬(f"**{N}일선 위=지수 · 아래=신호**",
                 lambda d, n=N: 위인가(d, n) is True,
                 lambda d, n=N: 위인가(d, n) is False, N=N, 끝날=끝날)
            시뮬(f"{N}일선 위=지수 · 아래=현금",
                 lambda d, n=N: 위인가(d, n) is True, 거짓, N=N, 끝날=끝날)
        시뮬("200일선 위=지수 · **신호는 늘 산다**",
             lambda d: 위인가(d, 200) is True, 참, 끝날=끝날)

    # ── D 우리 신호의 국면별 성적 ──
    print("\n  ══ D **우리 신호는 급등기에 약한가** ══")
    print(f"    {'국면':<28}{'평균':>9}{'승률':>8}{'신호일':>8}{'종목':>8}")
    for N in (120, 200):
        for 위, 라 in ((True, f"{N}일선 **위** (강세)"),
                       (False, f"{N}일선 **아래** (약세)")):
            t = {}
            for i1, d, code, 대금, 매수, r in 후보:
                if 위인가(d, N) is 위:
                    t.setdefault(d, []).append(r)
            if len(t) < 8:
                continue
            수 = [st.mean(v) for v in t.values()]
            승 = sum(1 for x in 수 if x > 0) / len(수) * 100
            print(f"    {라:<28}{st.mean(수):>+8.2f}%{승:>7.1f}%{len(t):>8}"
                  f"{sum(len(v) for v in t.values()):>8}")

    print("\n  읽는 법")
    print("    - A에서 **위/아래 성적 차이가 크면** 국면 판정이 값어치 있다")
    print("    - B에서 갈아타기가 「항상 신호」를 못 이기면 **국면 판정은 소용없다**")
    print("    - ⚠️ 이평은 **전날까지**로 잰다. look-ahead 없다")
    print("    - ⚠️ 지수는 배당 제외다. KODEX 200 TR은 연 1.5~2%p 높다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
