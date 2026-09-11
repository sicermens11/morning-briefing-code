#!/usr/bin/env python3
r"""
exec_lab.py — **실전 집행: 체결 가능성 · 추적손절 · 진짜 분산** (2026-09-02 · 15차)

⚠️⚠️ **내가 찾은 구멍 중 「실전」 쪽 셋을 한 번에 메운다.**
   지금까지 모든 시뮬은 **비현실적 가정**을 깔고 있었다.

## ① 체결 가능성 — **우리는 100% 체결을 가정했다**
```
⚠️ 상한가에 걸리면 못 산다 (한국은 ±30%)
⚠️ 거래정지면 못 산다
⚠️ 거래대금이 작으면 원하는 만큼 못 산다
```
→ **「신호가 떴는데 실제로 살 수 있었나」**를 센다. 못 사는 비율이 크면 성적이 허수다.

## ② 추적손절(trailing stop) — **한 번도 안 해봤다**
```
고정 손절   매수가 −5%에서 자른다        → 오른 뒤 되밀려도 안 잘린다
추적 손절   **최고가 대비** −N%에서 자른다  → 이익을 지킨다
```
→ 13차에서 「모멘텀엔 손절이 독」이었는데, **추적손절은 다를 수 있다.**

## ③ 진짜 분산 — **10종목이 다 같은 섹터면 분산이 아니다**
```
⚠️ 지금 시뮬은 「거래대금 큰 것부터 10개」를 담는다
   → 신고가 신호는 **같은 테마에 몰려서** 뜬다 (반도체·2차전지…)
   → 겉보기 10종목이 사실상 1종목일 수 있다
```
→ 뽑힌 종목들의 **같은 날 수익률 상관**을 재고, **섹터 분산 규칙**과 비교한다.

⚠️ 16.7년 · 신호는 크기별 최적(13차 결과)을 쓴다.
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


def _주가():
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"]); 고 = float(v["고가"]); 저 = float(v["저가"])
                if 종 <= 0:
                    continue
                하루[c] = (종, 고, 저, float(v.get("시총") or 0),
                           float(v.get("거래대금") or 0), float(v.get("등락률") or 0))
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    기본 = O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    # ── ① 체결 가능성 ──
    print(f"\n  ══ ① 체결 가능성 — 신호가 떴을 때 실제로 살 수 있었나 ══")
    총, 상한, 정지, 소액 = 0, 0, 0, 0
    상한폭 = []
    for i in range(250, len(날) - 21, 3):
        d1 = 날[i]
        for code, v in 주가[d1].items():
            c1, 고, 저, 시총, 대금, 등락 = v
            if 시총 < 1e12 or 대금 < O._MIN_AMT:
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            if c1 < max(종계[code][k - 250:k + 1]) * 0.999:
                continue          # 신고가 신호만
            총 += 1
            다 = 주가[날[i + 1]].get(code)
            if not 다:
                정지 += 1
                continue
            # 다음날 등락률이 +29% 넘으면 상한가로 못 샀을 수 있다
            if 다[5] >= 29.0:
                상한 += 1
                상한폭.append(다[5])
            if 다[4] < 5e8:      # 다음날 거래대금 5억 미만이면 담기 어렵다
                소액 += 1
    if 총:
        print(f"    신고가 신호 {총:,}건 (대형주, 3일마다 표본)")
        print(f"      다음날 거래정지·데이터없음   {정지:>7,}건  {정지/총*100:>5.2f}%")
        print(f"      다음날 상한가(+29%↑)       {상한:>7,}건  {상한/총*100:>5.2f}%")
        print(f"      다음날 거래대금 5억 미만      {소액:>7,}건  {소액/총*100:>5.2f}%")
        못 = (정지 + 상한) / 총 * 100
        print(f"    ⇒ **못 사는 비율 약 {못:.2f}%** — " +
              ("무시해도 된다" if 못 < 1 else "⚠️ 성적을 그만큼 깎아야 한다"))

    # ── ② 추적손절 ──
    print(f"\n  ══ ② 추적손절 vs 고정손절 (신고가+대형주 · D+20) ══")
    방식 = [("손절 없음", None, None), ("고정 −5%", -0.05, None), ("고정 −10%", -0.10, None),
            ("추적 −5%", None, -0.05), ("추적 −10%", None, -0.10), ("추적 −15%", None, -0.15)]
    결과 = {이름: [] for 이름, _, _ in 방식}
    for i in range(250, len(날) - 22, 2):
        d1 = 날[i]
        s1 = 주가[d1]
        후 = []
        수 = []
        for code, v in s1.items():
            c1, 고, 저, 시총, 대금, 등락 = v
            if 시총 < 1e12 or 대금 < O._MIN_AMT:
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            m = 주가[날[i + 1]].get(code)
            e = 주가[날[i + 21]].get(code)
            if not m or not e:
                continue
            수.append(e[0] / m[0] - 1)
            if c1 >= max(종계[code][k - 250:k + 1]) * 0.999:
                후.append((code, m[0]))
        if len(수) < 30 or not 후:
            continue
        기 = st.mean(수)
        for code, 매수 in 후:
            최고 = 매수
            for 이름, 고정, 추적 in 방식:
                팔 = None
                최고 = 매수
                for j in range(i + 2, i + 22):
                    vv = 주가[날[j]].get(code)
                    if not vv:
                        continue
                    if 고정 is not None and vv[2] <= 매수 * (1 + 고정):
                        팔 = 매수 * (1 + 고정)
                        break
                    if 추적 is not None:
                        if vv[2] <= 최고 * (1 + 추적):
                            팔 = 최고 * (1 + 추적)
                            break
                        최고 = max(최고, vv[1])
                if 팔 is None:
                    vv = 주가[날[i + 21]].get(code)
                    if not vv:
                        continue
                    팔 = vv[0]
                결과[이름].append(((팔 / 매수 - 1) - 기) * 100)
    print(f"    {'방식':<14}{'평균':>9}{'승률':>8}{'표본':>9}")
    for 이름, _, _ in 방식:
        a = 결과[이름]
        if len(a) < 300:
            continue
        승 = sum(1 for x in a if x > 0) / len(a) * 100
        print(f"    {이름:<14}{st.mean(a):>+8.3f}%{승:>7.1f}%{len(a):>9,}")
    print("    ⚠️ 추적손절은 **장중 저가 기준**이라 낙관적이다. 실제로는 더 나쁘다")

    # ── ③ 진짜 분산 ──
    print(f"\n  ══ ③ 진짜 분산 — 뽑힌 10종목이 서로 얼마나 같이 움직이나 ══")
    쌍상관, 무작위상관 = [], []
    rnd = random.Random(42)
    for i in range(300, len(날) - 25, 25):
        d1 = 날[i]
        후 = []
        전체 = []
        for code, v in 주가[d1].items():
            c1, 고, 저, 시총, 대금, 등락 = v
            if 시총 < 1e12 or 대금 < O._MIN_AMT:
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            전체.append(code)
            if c1 >= max(종계[code][k - 250:k + 1]) * 0.999:
                후.append((대금, code))
        후.sort(reverse=True)
        뽑 = [c for _, c in 후[:10]]
        if len(뽑) < 5 or len(전체) < 30:
            continue

        def 상관(목록):
            수 = {}
            for c in 목록:
                a = []
                for j in range(i + 1, i + 21):
                    x, y = 주가[날[j]].get(c), 주가[날[j - 1]].get(c)
                    if x and y:
                        a.append(x[0] / y[0] - 1)
                if len(a) >= 15:
                    수[c] = a
            cs = list(수)
            out = []
            for x in range(len(cs)):
                for y in range(x + 1, len(cs)):
                    A, B = 수[cs[x]], 수[cs[y]]
                    n = min(len(A), len(B))
                    if n < 15:
                        continue
                    A, B = A[:n], B[:n]
                    ma, mb = st.mean(A), st.mean(B)
                    sa = st.pstdev(A) or 1e-9
                    sb = st.pstdev(B) or 1e-9
                    out.append(sum((A[z] - ma) * (B[z] - mb) for z in range(n))
                               / n / (sa * sb))
            return out
        쌍상관 += 상관(뽑)
        무작위상관 += 상관(rnd.sample(전체, min(10, len(전체))))
    if 쌍상관 and 무작위상관:
        print(f"    신고가로 뽑은 10종목 서로 상관   {st.mean(쌍상관):+.3f}  (쌍 {len(쌍상관):,})")
        print(f"    무작위 10종목 서로 상관        {st.mean(무작위상관):+.3f}  (쌍 {len(무작위상관):,})")
        차 = st.mean(쌍상관) - st.mean(무작위상관)
        print(f"    ⇒ 차이 {차:+.3f} — " +
              ("⚠️ **같은 테마에 몰린다. 겉보기 10종목이 사실상 더 적다**" if 차 > 0.05
               else "무작위와 비슷하다. 분산은 제대로 된다"))
        print("    ⚠️ 상관이 높으면 종목 수를 늘려도 위험이 안 준다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
