#!/usr/bin/env python3
r"""
risk_lab.py — **얼마나 잃을 수 있나** (2026-09-01 신설)

⚠️⚠️ **지금까지 「평균」만 봤다.** 평균 +1.5%는 「반은 +10%, 반은 −7%」일 수도 있다.
   **자동매매를 논하려면 평균이 아니라 「최악」을 알아야 한다.**

**재는 것**
```
승률           플러스로 끝난 비율
분포           하위 5% · 25% · 중앙 · 상위 75% · 95%
최악 한 건      가장 크게 잃은 거래
보유 중 최대낙폭  사는 순간부터 파는 순간까지 **장중 저가 기준** 최대 하락
연속 손실       몇 번 연속으로 잃을 수 있나  ← 자동매매가 멈추는 지점
종목 수 효과     1·3·5·10종목에 나눠 담으면 변동이 얼마나 줄어드나
```

⚠️ **평균이 좋아도 최악이 크면 자동매매는 못 돌린다** — 원금이 먼저 녹는다.
⚠️ 매수는 **D+1 종가**(look-ahead 회피). 신호는 갭①④(호재+장후+무반응+정상종목).
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

_H = (1, 5, 20)


def _주가full():
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"]); 저 = float(v["저가"])
                if 종 <= 0:
                    continue
                하루[c] = (종, 저, float(v.get("시총") or 0),
                           float(v.get("거래대금") or 0), float(v.get("등락률") or 0),
                           1 if "KOSDAQ" in str(v.get("시장", "")).upper() else 0)
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def _몫(a, p):
    if not a:
        return None
    a = sorted(a)
    k = (len(a) - 1) * p
    f = int(k)
    return a[f] if f + 1 >= len(a) else a[f] + (a[f + 1] - a[f]) * (k - f)


def main():
    print("  자료 읽는 중…", flush=True)
    주가 = _주가full()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)

    거래 = {h: [] for h in _H}       # 초과수익 목록
    낙폭 = {h: [] for h in _H}       # 보유 중 최대낙폭(%)
    순서 = []                        # (날짜, D+5 초과) — 연속 손실용

    for i, d1 in enumerate(날):
        if i + 1 >= len(날):
            break
        a0 = 지수.get(날[i + 1])
        if not a0:
            continue
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        for code, r in (공시.get(d1) or {}).items():
            if "호재" not in r.get("성격", set()):
                continue
            if r.get("분") is None or r["분"] < 930:
                continue
            v1 = s1.get(code)
            매수v = 주가[날[i + 1]].get(code)
            if not v1 or not 매수v:
                continue
            종1, 저1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or abs(등락) >= 1:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if ("관리종목" in 부) or ("SPAC" in 부) or \
               (str(bb.get("상장일") or "") > "20240101") or \
               (bb.get("증권구분") not in (None, "주권")):
                continue
            매수가 = 매수v[0]
            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            for h in _H:
                j = i + 1 + h
                if j >= len(날) or not 지수.get(날[j]):
                    continue
                vv = 주가[날[j]].get(code)
                if not vv:
                    continue
                시장 = 지수[날[j]][장] / a0[장] - 1
                초 = ((vv[0] / 매수가 - 1) - 시장) * 100
                거래[h].append(초)
                # 보유 중 최대낙폭 (장중 저가 기준)
                저들 = [주가[날[k]].get(code)[1] for k in range(i + 1, j + 1)
                        if 주가[날[k]].get(code)]
                if 저들:
                    낙폭[h].append((min(저들) / 매수가 - 1) * 100)
                if h == 5:
                    순서.append((d1, 초))
        if i % 150 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print("\n  신호: 호재 + 장 마감 후 + 무반응 + 정상종목 · 매수 D+1 종가\n")
    print(f"  {'지평':<6}{'건수':>7}{'평균':>9}{'승률':>7}"
          f"{'하위5%':>9}{'25%':>8}{'중앙':>8}{'75%':>8}{'상위95%':>9}{'최악':>9}")
    for h in _H:
        a = 거래[h]
        if len(a) < 30:
            continue
        승 = sum(1 for x in a if x > 0) / len(a) * 100
        print(f"  D+{h:<4}{len(a):>7,}{st.mean(a):>+9.2f}{승:>6.0f}%"
              f"{_몫(a,.05):>+9.2f}{_몫(a,.25):>+8.2f}{_몫(a,.5):>+8.2f}"
              f"{_몫(a,.75):>+8.2f}{_몫(a,.95):>+9.2f}{min(a):>+9.2f}")

    print(f"\n  ══ 보유 중 최대낙폭 (장중 저가 기준) ══")
    print(f"  {'지평':<6}{'평균':>9}{'중앙':>9}{'하위25%':>10}{'하위5%':>10}{'최악':>10}")
    for h in _H:
        a = 낙폭[h]
        if len(a) < 30:
            continue
        print(f"  D+{h:<4}{st.mean(a):>+9.2f}{_몫(a,.5):>+9.2f}"
              f"{_몫(a,.25):>+10.2f}{_몫(a,.05):>+10.2f}{min(a):>+10.2f}")

    # 연속 손실
    순서.sort()
    현, 최 = 0, 0
    for _, x in 순서:
        현 = 현 + 1 if x <= 0 else 0
        최 = max(최, 현)
    print(f"\n  ══ 연속 손실 (D+5, 시간순 {len(순서):,}건) ══")
    print(f"  최장 연속 손실 **{최}회**  ⚠️ 자동매매가 멈추는 지점이다")

    # 종목 수 분산 효과
    a = 거래[5]
    if len(a) >= 200:
        print(f"\n  ══ 종목 수 분산 효과 (D+5, 무작위 1,000회 표본) ══")
        print(f"  {'종목수':<8}{'평균':>9}{'표준편차':>10}{'손실확률':>10}")
        rnd = random.Random(42)
        for n in (1, 3, 5, 10):
            표본 = [st.mean(rnd.sample(a, n)) for _ in range(1000)]
            손 = sum(1 for x in 표본 if x <= 0) / len(표본) * 100
            print(f"  {n:<8}{st.mean(표본):>+9.2f}{st.pstdev(표본):>10.2f}{손:>9.0f}%")
        print("  ⚠️ 종목을 나눠 담으면 **평균은 그대로인데 흔들림이 줄어든다.**")
        print("     10만원으로 1~2종목만 사면 이 효과를 못 얻는다.")
    print("\n  ⚠️⚠️ 평균이 좋아도 **최악이 크면 자동매매는 못 돌린다** — 원금이 먼저 녹는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
