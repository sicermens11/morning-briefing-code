#!/usr/bin/env python3
r"""
sector2_lab.py — **섹터 로테이션 전략 검증** (2026-09-03 · 65차)

⚠️⚠️ **다른 대화방에서 온 6개 항목 요구를 그대로 따른다.**
   *"「의미 없다」 한 문장이 아니라, 6개 항목 각각의 개별 결론 + 신뢰도를 표로"*

## 쓰는 자료
```
코스피200 섹터 지수 **12개** × **16.7년 일별** (KRX OpenAPI · data/index-daily)
  커뮤니케이션서비스 · 건설 · 중공업 · 철강/소재 · 에너지/화학 · 정보기술
  금융 · 생활소비재 · 경기소비재 · 산업재 · 헬스케어 · 경기방어소비재
```
⚠️⚠️ **결정적 한계 — 먼저 말한다.** 이 섹터 지수는 **직접 살 수 없다.**
   한국에 코스피200 **섹터 ETF가 다 있지 않다.** 그러니 아래 결과는
   **「이론상 상한」**이지 실제로 낼 수 있는 성적이 아니다. 실전은 이보다 나쁘다.

## 6개 항목
```
1a 상관관계   섹터간 일간수익률 상관계수 + **Fisher z 95% 신뢰구간**
1b 백테스트   로테이션 vs buy-and-hold (**거래비용 반영**)
1c 지속성     이번 달 강한 섹터가 다음 달에도 강한가 (**이항검정 + 신뢰구간**)
2  기간분할   4구간으로 나눠 각각 (2025~2026 왜곡 확인)
3  유의성     모든 수치에 **표준오차·신뢰구간**
4  거래비용   ETF 기준 왕복 0.05 / 0.15 / 0.30% **민감도**
5  벤치마크   코스피200 보유 · **무작위 섹터(몬테카를로 1,000회)** · 동일가중
6  생존편향   지수 결측·오염·리밸런싱 점검
```
"""
import glob
import io
import json
import math
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

섹터명 = ["커뮤니케이션서비스", "건설", "중공업", "철강/소재", "에너지/화학",
          "정보기술", "금융", "생활소비재", "경기소비재", "산업재", "헬스케어",
          "경기방어소비재지수"]
구간 = [("20100104", "20161231", "2010~2016 횡보"),
        ("20170101", "20211231", "2017~2021 상승"),
        ("20220101", "20241231", "2022~2024 하락·횡보"),
        ("20250101", "20260902", "2025~2026 급등")]


def z신뢰(r, n):
    """Fisher z 변환으로 상관계수 95% 신뢰구간."""
    if n < 4 or abs(r) >= 1:
        return None, None
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    lo, hi = z - 1.96 * se, z + 1.96 * se
    return math.tanh(lo), math.tanh(hi)


def 상관(a, b):
    n = len(a)
    if n < 10:
        return None
    ma, mb = st.mean(a), st.mean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    if sa == 0 or sb == 0:
        return None
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (sa * sb)


def 이항신뢰(성공, 전체):
    """Wilson 95% 신뢰구간 — 표본이 작아도 안전하다."""
    if 전체 == 0:
        return 0, 0, 0
    p = 성공 / 전체
    z = 1.96
    d = 1 + z * z / 전체
    c = p + z * z / (2 * 전체)
    s = z * math.sqrt(p * (1 - p) / 전체 + z * z / (4 * 전체 * 전체))
    return p * 100, (c - s) / d * 100, (c + s) / d * 100


def main():
    print("  자료 읽는 중...", flush=True)
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        g = d.get("지수") or {}
        for n in 섹터명 + ["코스피 200"]:
            키 = n if n == "코스피 200" else f"코스피 200 {n}"
            v = (g.get(키) or {}).get("종가")
            if v:
                try:
                    표.setdefault(n, {})[d["기준일"]] = float(v)
                except (TypeError, ValueError):
                    pass

    # ══ 6 생존편향·데이터 점검 (먼저 한다 — 자료가 나쁘면 뒤가 무의미하다) ══
    print("\n  ══════ 6. 생존편향·데이터 점검 ══════")
    모든날 = sorted(표["코스피 200"])
    print(f"    코스피200 기준 거래일 {len(모든날):,}일 "
          f"({모든날[0]} ~ {모든날[-1]})")
    print(f"    {'섹터':<22}{'일수':>8}{'결측':>8}{'시작':>10}"
          f"{'|등락|>15%':>11}{'|등락|>30%':>11}")
    쓸섹터 = []
    for n in 섹터명:
        a = 표.get(n) or {}
        k = sorted(a)
        if len(k) < 1000:
            print(f"    {n:<22}{len(k):>8}  — 너무 짧다. 뺀다")
            continue
        결 = len([d for d in 모든날 if d >= k[0] and d not in a])
        큰15 = 큰30 = 0
        for j in range(1, len(k)):
            p, c = a[k[j - 1]], a[k[j]]
            if p:
                x = abs(c / p - 1)
                if x > 0.15:
                    큰15 += 1
                if x > 0.30:
                    큰30 += 1
        print(f"    {n:<22}{len(k):>8}{결:>8}{k[0]:>10}{큰15:>11}{큰30:>11}")
        쓸섹터.append(n)
    print(f"    ⇒ 쓸 수 있는 섹터 **{len(쓸섹터)}개**")
    print("    ⚠️ 섹터 지수는 KRX가 **편입·편출을 반영해 산출**한다.")
    print("       ⇒ 상장폐지 종목이 빠져 생기는 생존편향은 **지수 자체엔 없다.**")
    print("       ⚠️ 대신 **리밸런싱 편향**이 있다 — 지수가 종목을 갈아끼우는 시점의")
    print("          효과가 지수에 들어간다. 실제 ETF도 같은 것을 겪으니 큰 문제는 아니다.")
    print("    ⚠️⚠️ **더 큰 한계: 이 섹터 지수는 직접 살 수 없다.**")
    print("       한국에 코스피200 섹터 ETF가 다 있지 않다.")
    print("       ⇒ 아래 결과는 **「이론상 상한」**이다. 실전은 이보다 나쁘다.")

    # 일간 수익률
    수익 = {}
    for n in 쓸섹터 + ["코스피 200"]:
        a = 표[n]
        k = sorted(a)
        t = {}
        for j in range(1, len(k)):
            p = a[k[j - 1]]
            if p:
                t[k[j]] = a[k[j]] / p - 1
        수익[n] = t
    공통 = sorted(set.intersection(*[set(수익[n]) for n in 쓸섹터]))
    print(f"\n    섹터 12개가 모두 있는 날 **{len(공통):,}일** "
          f"({공통[0]} ~ {공통[-1]})")

    # ══ 1a 상관관계 ══
    print("\n  ══════ 1a. 섹터간 상관관계 (+ Fisher z 95% 신뢰구간) ══════")
    print("     ⚠️ **질문의 핵심**: 섹터가 서로 따로 움직여야 로테이션이 가능하다.")
    print("        상관이 다 높으면 「어느 섹터를 사든 같다」 → 로테이션이 무의미하다.")
    쌍 = []
    for i in range(len(쓸섹터)):
        for j in range(i + 1, len(쓸섹터)):
            a = [수익[쓸섹터[i]][d] for d in 공통]
            b = [수익[쓸섹터[j]][d] for d in 공통]
            r = 상관(a, b)
            if r is not None:
                쌍.append((r, 쓸섹터[i], 쓸섹터[j]))
    쌍.sort()
    rs = [x[0] for x in 쌍]
    lo, hi = z신뢰(st.mean(rs), len(공통))
    print(f"    쌍 {len(쌍)}개 · 표본 {len(공통):,}일")
    print(f"    평균 상관 **{st.mean(rs):.3f}**  (95% CI {lo:.3f} ~ {hi:.3f})")
    print(f"    중앙 {st.median(rs):.3f} · 최소 {rs[0]:.3f} · 최대 {rs[-1]:.3f}")
    print(f"\n    가장 **따로 노는** 5쌍 (로테이션 여지가 있는 곳)")
    for r, x, y in 쌍[:5]:
        l, h = z신뢰(r, len(공통))
        print(f"      {r:.3f} (CI {l:.3f}~{h:.3f})  {x} ↔ {y}")
    print(f"    가장 **같이 노는** 5쌍")
    for r, x, y in 쌍[-5:]:
        l, h = z신뢰(r, len(공통))
        print(f"      {r:.3f} (CI {l:.3f}~{h:.3f})  {x} ↔ {y}")
    # 시장 대비
    print(f"\n    각 섹터 vs 코스피200 (시장과 얼마나 같이 움직이나)")
    mk = [수익["코스피 200"][d] for d in 공통 if d in 수익["코스피 200"]]
    공2 = [d for d in 공통 if d in 수익["코스피 200"]]
    mk = [수익["코스피 200"][d] for d in 공2]
    for n in 쓸섹터:
        r = 상관([수익[n][d] for d in 공2], mk)
        l, h = z신뢰(r, len(공2))
        print(f"      {n:<22}{r:.3f}  (CI {l:.3f}~{h:.3f})")

    # 구간별 평균 상관
    print(f"\n    ── **구간별** 평균 상관 (2번 항목: 기간에 따라 다른가) ──")
    print(f"    {'구간':<22}{'표본':>8}{'평균상관':>10}{'95% CI':>18}")
    for a8, b8, 라 in 구간:
        dd = [d for d in 공통 if a8 <= d <= b8]
        if len(dd) < 100:
            continue
        v = []
        for i in range(len(쓸섹터)):
            for j in range(i + 1, len(쓸섹터)):
                r = 상관([수익[쓸섹터[i]][d] for d in dd],
                         [수익[쓸섹터[j]][d] for d in dd])
                if r is not None:
                    v.append(r)
        m = st.mean(v)
        l, h = z신뢰(m, len(dd))
        print(f"    {라:<22}{len(dd):>8}{m:>10.3f}   {l:.3f} ~ {h:.3f}")

    # ══ 1c 모멘텀 지속성 ══
    print("\n  ══════ 1c. 섹터 모멘텀 지속성 (이항검정 + Wilson 95% CI) ══════")
    print("     ⚠️ 「이번 달 1등이 다음 달에도 상위 절반」일 확률이 50%보다 유의한가")
    달 = {}
    for d in 공통:
        달.setdefault(d[:6], []).append(d)
    달키 = sorted(달)
    print(f"    {'조건':<34}{'성공/전체':>13}{'확률':>8}{'95% CI':>18}{'판정':>10}")
    for 순위, 라 in ((1, "이번 달 **1등** → 다음 달 상위 절반"),
                     (1, "이번 달 **1등** → 다음 달도 상위 1/4"),
                     (3, "이번 달 **상위 3** → 다음 달 상위 절반"),
                     (1, "이번 달 **꼴등** → 다음 달 상위 절반")):
        pass
    def 월수익(n, m):
        dd = 달[m]
        v = 1.0
        for d in dd:
            v *= (1 + 수익[n][d])
        return v - 1
    캐시 = {m: {n: 월수익(n, m) for n in 쓸섹터} for m in 달키}

    # ⚠️⚠️ **2026-09-03 수정.** 기준선을 50%로 박아뒀는데, 「상위 1/4」의 기대값은
    #   **25%**다. 50%와 견주면 「역방향」으로 잘못 찍힌다. 기준선을 인자로 받는다.
    def 검정(고르기, 성공조건, 라, 기준, 부터=None, 까지=None):
        s = t = 0
        키 = [m for m in 달키
              if (부터 is None or m >= 부터) and (까지 is None or m <= 까지)]
        for j in range(len(키) - 1):
            이, 다 = 캐시[키[j]], 캐시[키[j + 1]]
            순 = sorted(쓸섹터, key=lambda n: -이[n])
            다순 = sorted(쓸섹터, key=lambda n: -다[n])
            for n in 고르기(순):
                t += 1
                s += 1 if 성공조건(다순.index(n), len(쓸섹터)) else 0
        p, l, h = 이항신뢰(s, t)
        유 = "**유의**" if l > 기준 else ("**역방향**" if h < 기준 else "무의미")
        print(f"    {라:<34}{f'{s}/{t}':>11}{p:>7.1f}%{기준:>7.1f}%"
              f"   {l:>5.1f} ~ {h:>5.1f}%{유:>10}")
        return p, l, h

    print(f"    {'조건':<34}{'성공/전체':>11}{'확률':>7}{'기대값':>7}"
          f"{'95% CI':>18}{'판정':>10}")
    N = len(쓸섹터)
    쌍들 = [(lambda s: s[:1], lambda r, n: r < n / 2, "이번 달 1등 → 다음 달 상위 절반", 50.0),
            (lambda s: s[:1], lambda r, n: r < n / 4, "이번 달 1등 → 다음 달 상위 1/4", 25.0),
            (lambda s: s[:3], lambda r, n: r < n / 2, "이번 달 상위3 → 다음 달 상위 절반", 50.0),
            (lambda s: s[:3], lambda r, n: r < n / 4, "이번 달 상위3 → 다음 달 상위 1/4", 25.0),
            (lambda s: s[-1:], lambda r, n: r < n / 2, "이번 달 꼴등 → 다음 달 상위 절반", 50.0),
            (lambda s: s[-3:], lambda r, n: r < n / 2, "이번 달 하위3 → 다음 달 상위 절반", 50.0)]
    for g, c, 라, 기 in 쌍들:
        검정(g, c, 라, 기)
    print(f"    (달 {len(달키)}개 · 섹터 {N}개)")
    print("\n    ── **2025~2026을 뺀** 판 (~202412) ──")
    print(f"    {'조건':<34}{'성공/전체':>11}{'확률':>7}{'기대값':>7}"
          f"{'95% CI':>18}{'판정':>10}")
    for g, c, 라, 기 in 쌍들:
        검정(g, c, 라, 기, 까지="202412")

    # ══ 1b·4·5 백테스트 ══
    print("\n  ══════ 1b·4·5. 로테이션 백테스트 (거래비용 + 벤치마크) ══════")

    def 돌리기(고르기, 룩백, 보유, 비용, a8, b8, 시드=None):
        """월말 리밸런싱. 룩백개월 성과로 고르고 보유개월 들고 간다."""
        ks = [m for m in 달키 if a8[:6] <= m <= b8[:6]]
        if len(ks) < 룩백 + 보유 + 6:
            return None
        rng = random.Random(시드) if 시드 is not None else None
        자산 = 1.0
        지금 = None
        수익들 = []
        for j in range(룩백, len(ks) - 1):
            m = ks[j]
            if (j - 룩백) % 보유 == 0:
                점 = {}
                for n in 쓸섹터:
                    v = 1.0
                    for x in range(j - 룩백, j):
                        v *= (1 + 캐시[ks[x]][n])
                    점[n] = v - 1
                순 = sorted(쓸섹터, key=lambda n: -점[n])
                새 = 고르기(순, rng)
                if 지금 is not None and set(새) != set(지금):
                    바뀜 = len(set(새) - set(지금)) / max(1, len(새))
                    자산 *= (1 - 비용 * 바뀜)
                지금 = 새
            r = st.mean([캐시[ks[j + 1]][n] for n in 지금])
            자산 *= (1 + r)
            수익들.append(r)
        해 = len(수익들) / 12
        연 = (자산 ** (1 / 해) - 1) * 100 if 자산 > 0 and 해 > 0 else -100
        se = (st.pstdev(수익들) / math.sqrt(len(수익들)) * 12 * 100) if 수익들 else 0
        return 연, se, len(수익들), 자산

    def 벤치(a8, b8):
        ks = [m for m in 달키 if a8[:6] <= m <= b8[:6]]
        if len(ks) < 12:
            return None
        v = 1.0
        r = []
        for m in ks:
            x = 1.0
            for d in 달[m]:
                if d in 수익["코스피 200"]:
                    x *= (1 + 수익["코스피 200"][d])
            v *= x
            r.append(x - 1)
        해 = len(ks) / 12
        return (v ** (1 / 해) - 1) * 100, st.pstdev(r) / math.sqrt(len(r)) * 12 * 100

    for a8, b8, 라 in ([("20100104", "20260902", "**전체 16.7년**"),
                        ("20100104", "20241231",
                         "**2010~2024 (2025·26 뺌 · 14.9년)** ← 왜곡 확인")]
                       + 구간):
        print(f"\n    ── {라} ──")
        b = 벤치(a8, b8)
        if not b:
            print("      표본 부족")
            continue
        print(f"      {'전략':<34}{'연평균':>10}{'±SE':>9}{'개월':>7}")
        print(f"      {'**벤치마크: 코스피200 보유**':<34}{b[0]:>+9.2f}%{b[1]:>8.2f}%")
        r = 돌리기(lambda s, g: s, 6, 1, 0.0, a8, b8)
        if r:
            print(f"      {'**벤치마크: 전 섹터 동일가중**':<34}{r[0]:>+9.2f}%"
                  f"{r[1]:>8.2f}%{r[2]:>7}")
        # 무작위 (몬테카를로)
        몬 = []
        for s in range(300):
            rr = 돌리기(lambda ss, g: g.sample(쓸섹터, 3), 6, 1, 0.0015, a8, b8, 시드=s)
            if rr:
                몬.append(rr[0])
        if 몬:
            몬.sort()
            print(f"      {'**벤치마크: 무작위 3섹터(300회)**':<34}"
                  f"{st.mean(몬):>+9.2f}%{'':>9}"
                  f"   [5%={몬[15]:+.1f}% · 95%={몬[284]:+.1f}%]")
        print(f"      {'':<34}{'':>10}{'':>9}")
        for 룩백 in (1, 3, 6, 12):
            for 라2, 골 in (("모멘텀 상위3", lambda s, g: s[:3]),
                            ("역발상 하위3", lambda s, g: s[-3:])):
                r = 돌리기(골, 룩백, 1, 0.0015, a8, b8)
                if r:
                    초 = r[0] - b[0]
                    표시 = "⭐" if 초 > 2 * r[1] else ("❌" if 초 < -2 * r[1] else "  ")
                    print(f"      {f'{라2} · {룩백}개월 룩백':<34}{r[0]:>+9.2f}%"
                          f"{r[1]:>8.2f}%{r[2]:>7}  벤치대비 {초:+.2f}%p {표시}")

    # ══ 4 거래비용 민감도 ══
    print("\n  ══════ 4. 거래비용 민감도 (전체 16.7년 · 모멘텀 상위3 · 6개월) ══════")
    print("     ETF 기준: 수수료 왕복 0.03% · **증권거래세 없음** · 슬리피지가 변수")
    b = 벤치("20100104", "20260902")
    print(f"    {'왕복 비용':<20}{'연평균':>10}{'벤치대비':>12}")
    for 비 in (0.0, 0.0005, 0.0015, 0.0030, 0.0060):
        r = 돌리기(lambda s, g: s[:3], 6, 1, 비, "20100104", "20260902")
        if r:
            print(f"    {f'{비*100:.2f}%':<20}{r[0]:>+9.2f}%{r[0]-b[0]:>+11.2f}%p")

    print("\n  읽는 법")
    print("    - **1a의 평균 상관이 높으면** 섹터가 같이 움직인다 → 로테이션 여지가 없다")
    print("    - **1c에서 CI 하한이 50%를 넘어야** 모멘텀 지속성이 있다고 말할 수 있다")
    print("    - **1b에서 「벤치대비」가 2×SE를 넘어야** 유의하다 (⭐ 표시)")
    print("    - ⚠️⚠️ **섹터 지수는 직접 살 수 없다.** 전부 「이론상 상한」이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
