#!/usr/bin/env python3
r"""
sector_slice_lab.py — **섹터를 시간축으로 쪼갠다** (2026-09-02 · 9차)

⚠️⚠️ **사용자 요청의 「섹터별」 부분.**
   업종지수 **71개**를 쓴다. 개별 종목 잡음이 없고 16.7년 전체가 있다.

**두 가지를 낸다**
```
① 섹터 × 시간   어느 섹터가 어느 달·분기·계절에 강했나  (계절성)
② 섹터 순환     지난 N개월 강했던 섹터가 다음에도 강한가 (모멘텀) 아니면 뒤집히나 (반전)
```
⚠️ ②가 실전에 쓸모 있다 — **「지금 어느 섹터를 봐야 하나」**에 답한다.

⚠️⚠️ **다중검정 위험이 크다.** 섹터 71 × 월 12 = 852칸이면 우연히 좋은 게 수십 개 나온다.
   → **학습(2010~2017) / 검증(2018~2026)** 을 갈라 **둘 다 좋은 것만** 표시한다.

⚠️ 잣대는 **코스피 대비 초과수익**(섹터지수끼리는 시총가중 문제가 덜하다).
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_경계 = "20180101"
_H = 20              # 20거래일 뒤


def main():
    print("  자료 읽는 중...", flush=True)
    지수 = O._지수()
    날 = sorted(지수)
    # 모든 날에 있는 업종만
    공통 = None
    for d in 날:
        s = set(지수[d].get("업종") or {})
        공통 = s if 공통 is None else (공통 & s)
    업종 = sorted(공통 or [])
    print(f"  거래일 {len(날):,} · 모든 날에 있는 업종 {len(업종)}개", flush=True)

    계절 = {12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄",
            6: "여름", 7: "여름", 8: "여름", 9: "가을", 10: "가을", 11: "가을"}

    # ① 섹터 × 시간
    통 = {}
    # ② 섹터 순환: (지난 3개월 순위 구간, 구간) -> 다음 20일 초과
    순환 = {}

    for i in range(60, len(날) - _H):
        d1, d2 = 날[i], 날[i + _H]
        u1 = 지수[d1].get("업종") or {}
        u2 = 지수[d2].get("업종") or {}
        시장 = 지수[d2]["KOSPI"] / 지수[d1]["KOSPI"] - 1
        구간 = "학습" if d1 < _경계 else "검증"
        m = int(d1[4:6])

        # 지난 60거래일 섹터 수익률 순위
        j = i - 60
        u0 = 지수[날[j]].get("업종") or {}
        지난 = []
        for u in 업종:
            a, b = u0.get(u), u1.get(u)
            if a and b:
                지난.append((b / a - 1, u))
        지난.sort(reverse=True)
        순 = {u: r for r, (_, u) in enumerate(지난)}
        n = len(지난)

        for u in 업종:
            a, b = u1.get(u), u2.get(u)
            if not a or not b:
                continue
            초 = ((b / a - 1) - 시장) * 100
            for 축, 칸 in (("월", f"{m:02d}월"), ("분기", f"{(m-1)//3+1}분기"),
                           ("계절", 계절[m])):
                통.setdefault((u, 축, 칸, 구간), []).append(초)
            통.setdefault((u, "전체", "-", 구간), []).append(초)
            if u in 순 and n >= 20:
                p = 순[u] / n
                띠 = ("상위20%" if p < 0.2 else "상위20~40%" if p < 0.4 else
                      "중간" if p < 0.6 else "하위20~40%" if p < 0.8 else "하위20%")
                순환.setdefault((띠, 구간), []).append(초)
        if i % 500 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    # ── ② 섹터 순환 (실전에 쓸모 있다) ──
    print(f"\n{'='*80}")
    print("  ① 섹터 순환 — 지난 3개월 강했던 섹터가 다음 20일에도 강한가")
    print(f"{'='*80}")
    print(f"  {'지난 3개월 순위':<16}{'전체':>18}{'학습':>18}{'검증':>18}  판정")
    for 띠 in ("상위20%", "상위20~40%", "중간", "하위20~40%", "하위20%"):
        모, 줄 = [], {}
        for g in ("학습", "검증"):
            a = 순환.get((띠, g)) or []
            모 += a
            줄[g] = (st.mean(a), len(a)) if len(a) >= 200 else None
        if len(모) < 200:
            continue
        판 = ""
        if 줄["학습"] and 줄["검증"]:
            판 = ("⭐ 둘 다 +" if 줄["학습"][0] > 0 and 줄["검증"][0] > 0
                  else "❌ 둘 다 −" if 줄["학습"][0] < 0 and 줄["검증"][0] < 0
                  else "· 뒤집힘")
        def f(x):
            return f"{x[0]:+.3f}% ({x[1]//1000}k)" if x else "-"
        print(f"  {띠:<16}{f((st.mean(모), len(모))):>18}"
              f"{f(줄['학습']):>18}{f(줄['검증']):>18}  {판}")
    print("\n  ⚠️ 상위가 +면 **섹터 모멘텀**, 하위가 +면 **섹터 반전**이다")

    # ── ② 섹터 × 계절 (학습·검증 둘 다 좋은 것만) ──
    print(f"\n{'='*80}")
    print("  ② 섹터 × 시간 — 학습·검증 **둘 다 +**인 칸만 (다중검정 방어)")
    print(f"{'='*80}")
    for 축 in ("계절", "분기", "월"):
        골 = []
        for u in 업종:
            칸들 = sorted({c for (uu, a, c, g) in 통 if uu == u and a == 축})
            for 칸 in 칸들:
                ha = 통.get((u, 축, 칸, "학습")) or []
                va = 통.get((u, 축, 칸, "검증")) or []
                if len(ha) < 150 or len(va) < 150:
                    continue
                h, v = st.mean(ha), st.mean(va)
                if h > 0 and v > 0:
                    골.append((min(h, v), u, 칸, h, v, len(ha) + len(va)))
        골.sort(reverse=True)
        print(f"\n  ── {축} · 둘 다 + 인 칸 {len(골)}개 (상위 10) ──")
        if not 골:
            print("    없음")
            continue
        print(f"    {'업종':<26}{'칸':<10}{'학습':>10}{'검증':>10}{'표본':>9}")
        for _, u, 칸, h, v, n in 골[:10]:
            print(f"    {u[:24]:<26}{칸:<10}{h:>+9.3f}%{v:>+9.3f}%{n:>9,}")

    # ── ③ 섹터 전체 성적 (16.7년) ──
    print(f"\n{'='*80}")
    print("  ③ 섹터별 16.7년 성적 (코스피 대비 · D+20 평균)")
    print(f"{'='*80}")
    줄 = []
    for u in 업종:
        ha = 통.get((u, "전체", "-", "학습")) or []
        va = 통.get((u, "전체", "-", "검증")) or []
        if len(ha) < 200 or len(va) < 200:
            continue
        h, v = st.mean(ha), st.mean(va)
        줄.append((min(h, v), u, h, v))
    줄.sort(reverse=True)
    print(f"  {'업종':<28}{'학습':>11}{'검증':>11}  판정")
    for _, u, h, v in 줄[:8]:
        print(f"  {u[:26]:<28}{h:>+10.3f}%{v:>+10.3f}%  " +
              ("⭐ 둘 다 +" if h > 0 and v > 0 else "· 뒤집힘"))
    print(f"  {'…':<28}")
    for _, u, h, v in 줄[-5:]:
        print(f"  {u[:26]:<28}{h:>+10.3f}%{v:>+10.3f}%  " +
              ("❌ 둘 다 −" if h < 0 and v < 0 else "· 뒤집힘"))
    print("\n  ⚠️ 섹터 71개 × 월 12 = 852칸이라 **우연히 좋은 칸이 반드시 나온다**")
    print("     학습·검증 둘 다 +인 것만 봐도 우연이 섞인다. 표본 크기를 같이 볼 것")
    return 0


if __name__ == "__main__":
    sys.exit(main())
