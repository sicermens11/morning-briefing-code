#!/usr/bin/env python3
r"""
walk_lab.py — **옛날 데이터가 얼마나 쓸모 있나 (워크포워드)** (2026-09-02 · 30차)

⚠️⚠️ **사용자 지적.**
   *"시장은 항상 변하니까 한국 시장을 16.7년을 통으로 보는 것보다 단위를 나눠서 분석하는 것도
   필요한 것 같아. 2010년이랑 2026년 한국 시장은 다를 텐데, 16.7년 데이터가 그러니까
   2026년도 그럴 것이다라고 하는 건 맞지 않을 수도 있을 것 같아."*

## 맞다. 오늘 데이터가 이미 증거를 보여줬다
```
27차  학습에선 넓은 신호가 낫고 검증에선 좁은 신호가 낫다 — **부호가 정반대**
22차  소형 52주 신고가  2022 −3.12 · 2024 −2.17 · 2025 +1.08 · 2026 +1.22
      대형 52주 신고가  2024 +0.18 · 2025 +0.30 · 2026 **+3.23**
24차  코스피−보통종목 격차  2015 −21%p · 2021 −14%p · 2026 **+65%p**
```
⚠️ **나는 16.7년 평균을 내서 「이 신호는 t=4.2다」라고 말해왔다. 평균이 시대차를 덮고 있었다.**

## 그렇다고 「최근만 보자」도 답이 아니다 — **어느 쪽이 나은지를 재야 한다**
```
매년 초에 **직전 N년 데이터만** 보고 신호를 고른다  →  **그 다음 1년**에 실제로 통했나
  N = 3년 / 5년 / 10년 / 전체(2010년부터)
```
⚠️ 이게 워크포워드다. **실전과 똑같은 순서**다 — 미래를 안 보고 과거만 보고 고른다.
```
3년이 전체보다 나으면  → **오래된 데이터는 버려야 한다** (시대차가 크다)
전체가 3년보다 나으면  → 시대차보다 **표본 크기**가 중요하다
둘 다 비슷하면        → 신호가 시대를 타지 않는다
```

## 재는 방법
```
① 매년 초, 직전 N년으로 신호 11종 × 크기 3구간의 **초과수익 순위**를 매긴다
② 그중 **가장 좋았던 것 하나**를 골라 그 해에 쓴다
③ 그 해 실제 성적을 기록한다 → 16번 반복(2011~2026)
④ N별로 **평균 성적 · 이긴 해 수**를 비교한다
```
⚠️ 비교 기준은 「아무 신호도 안 쓴 것」(그 크기 구간 평균 = 0)이다.
⚠️ 수정주가 적용 · D+20 · 자기 크기 구간 대비 · 오염 제외.
"""
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = 20
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]
신호이름 = ["A 52주 신고가", "B RSI 과매수", "C 볼린저 상단", "D 수급강도",
            "E 20일선 위", "F 볼린저 하단", "G RSI 과매도", "H 20일선 아래",
            "I 거래량 3배↑", "J 모멘텀 2개↑", "K 반전 2개↑"]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금", "거래량"))
    날 = sorted(주가)
    수급 = O._수급()
    기본 = O._기본()
    종계, 량계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            량계.setdefault(c, []).append(v[3])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    # (해, 신호, 크기) -> [초과%]  — 한 번만 계산해두고 여러 창으로 잘라 쓴다
    통 = {}
    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + _H >= len(날):
            continue
        해 = d1[:4]
        fl = 수급.get(d1) or {}
        후보 = {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금, 량 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            if ((자리.get(code) or {}).get(d1) or 0) < 250:
                continue
            m = 주가[날[i + 1]].get(code)
            e = 주가[날[i + 1 + _H]].get(code)
            if not m or not e:
                continue
            후보.setdefault(_크기(시총), []).append((code, v, e[0] / m[0] - 1))
        기준 = {g: st.mean([r for _, _, r in a]) for g, a in 후보.items() if len(a) >= 15}
        for g, a in 후보.items():
            if g not in 기준:
                continue
            for code, v, r in a:
                c1, 시총, 대금, 량 = v
                k = (자리.get(code) or {}).get(d1)
                sq = 종계[code]
                초 = (r - 기준[g]) * 100
                s20 = st.mean(sq[k - 19:k + 1])
                sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
                볼 = (c1 - s20) / (2 * sd)
                변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
                상 = st.mean([max(0, x) for x in 변]) or 1e-9
                하 = st.mean([max(0, -x) for x in 변]) or 1e-9
                rsi = 100 - 100 / (1 + 상 / 하)
                고 = max(sq[k - 250:k + 1])
                f = fl.get(code) or {}
                강 = (((f.get("외국인") or 0) + (f.get("기관") or 0)) * c1 / 시총 * 100
                      if 시총 > 0 else 0)
                평량 = st.mean(량계[code][k - 20:k]) or 1
                A = bool(고) and c1 >= 고 * 0.999
                B, C = rsi >= 70, 볼 >= 1.0
                D, E = 강 >= 0.5, c1 > s20
                F, G, Hh = 볼 <= -1.0, rsi <= 30, c1 < s20
                I = 량 >= 평량 * 3
                J = sum([A, B, C]) >= 2
                K = sum([F, G, Hh]) >= 2
                for 이름, 켜 in zip(신호이름, [A, B, C, D, E, F, G, Hh, I, J, K]):
                    if 켜:
                        통.setdefault((해, 이름, g), []).append(초)
        if i % 500 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    해들 = sorted({k[0] for k in 통})
    print(f"  해 {len(해들)}개 · 칸 {len(통):,}개\n", flush=True)

    def 창성적(해목록, 이름, g):
        a = []
        for y in 해목록:
            a += 통.get((y, 이름, g)) or []
        return a

    창들 = [("직전 3년", 3), ("직전 5년", 5), ("직전 10년", 10), ("전체(2010~)", 99)]
    결과 = {이름: [] for 이름, _ in 창들}
    고른것 = {이름: [] for 이름, _ in 창들}

    print("  ══ 매년: 직전 N년으로 고른 「최고 신호」가 그 해에 통했나 ══")
    print("     ⚠️ 실전과 똑같은 순서다 — 미래를 안 보고 과거만 보고 고른다\n")
    print(f"    {'해':<6}" + "".join(f"{이름:>26}" for 이름, _ in 창들))
    for yi, y in enumerate(해들):
        if yi < 3:            # 앞 3해는 훈련 창을 못 만든다
            continue
        줄 = []
        for 창이름, N in 창들:
            앞해 = 해들[max(0, yi - N):yi]
            최고, 최고값 = None, None
            for 이름 in 신호이름:
                for g, _, _ in 크기표:
                    a = 창성적(앞해, 이름, g)
                    if len(a) < 500:
                        continue
                    m = st.mean(a)
                    if 최고값 is None or m > 최고값:
                        최고값, 최고 = m, (이름, g)
            if 최고 is None:
                줄.append("-")
                continue
            b = 통.get((y, 최고[0], 최고[1])) or []
            if len(b) < 100:
                줄.append("-")
                continue
            실 = st.mean(b)
            결과[창이름].append(실)
            고른것[창이름].append((y, 최고, 실))
            표 = "⭐" if 실 > 0 else "  "
            줄.append(f"{최고[0][:1]}·{최고[1]} {최고값:+.2f}→{실:+.2f}{표}")
        print(f"    {y:<6}" + "".join(f"{x:>26}" for x in 줄))

    print(f"\n  ══ 판정 ══")
    print(f"    {'창':<14}{'평균 실제성적':>14}{'이긴 해':>10}{'표본해':>8}{'t값':>8}")
    for 창이름, _ in 창들:
        a = 결과[창이름]
        if not a:
            continue
        이김 = sum(1 for x in a if x > 0)
        t = (st.mean(a) / ((st.pstdev(a) or 1e-9) / math.sqrt(len(a)))) if len(a) > 2 else 0
        print(f"    {창이름:<14}{st.mean(a):>+13.3f}%{이김:>8}/{len(a)}{len(a):>8}{t:>8.1f}")

    print("\n  ══ 어떤 신호가 뽑혔나 (직전 3년 창) ══")
    앞 = None
    for y, 최고, 실 in 고른것.get("직전 3년", []):
        바뀜 = "  " if 앞 == 최고 else "🔄"
        print(f"    {y}  {바뀜} {최고[0]:<16} {최고[1]:<4} → 실제 {실:+.2f}%")
        앞 = 최고
    print("\n  ══ 어떤 신호가 뽑혔나 (전체 창) ══")
    앞 = None
    for y, 최고, 실 in 고른것.get("전체(2010~)", []):
        바뀜 = "  " if 앞 == 최고 else "🔄"
        print(f"    {y}  {바뀜} {최고[0]:<16} {최고[1]:<4} → 실제 {실:+.2f}%")
        앞 = 최고

    print("\n  읽는 법")
    print("    - **3년 창이 전체 창보다 나으면 → 오래된 데이터는 버려야 한다** (시대차가 크다)")
    print("    - 전체 창이 나으면 → 시대차보다 **표본 크기**가 중요하다")
    print("    - '🔄'가 잦으면 **뽑히는 신호가 계속 바뀐다** = 안정된 신호가 없다는 뜻이다")
    print("    - ⚠️ 평균 실제성적이 0 근처면 **어느 창을 써도 소용없다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
