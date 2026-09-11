#!/usr/bin/env python3
r"""
daily_lab.py — **하루에 후보가 몇 개나 뜨고 얼마나 바뀌나** (2026-09-04 · 103차)

## ⚠️ 왜 재나
```
101차에서 「08:00 후보 20~40개」라고 했는데 **실제 숫자를 확인 안 했다.**
   101차: 후보 21,867건 / 2,556일 = 하루 **8.6개**  ← 평균은 이것
   오늘(09-04) record_pick이 뽑은 것은 **4개**
⇒ 「20~40개」는 근거 없는 말이었다. 제대로 잰다
```

## 재는 것
```
A 하루에 몇 개나 뜨나    평균·중앙·분포·0개인 날
B ⭐ **얼마나 바뀌나**   어제 후보와 오늘 후보가 몇 개나 겹치나
C 며칠이나 머무나       한 종목이 후보에 연속으로 며칠 있나
D 그중 몇 개나 사게 되나  갭 -3.5%p까지 통과하는 것
E ⭐ **요일·달·해별**   몰리는 때가 있나
F 브리핑에 몇 개를 실을까  상위 N개로 잘랐을 때 놓치는 것
```
⚠️ 조건은 **98차 확정 규칙**의 08:00분 (갭 제외)
"""
import collections
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_시작 = "20160401"
확정 = {"갭": -3.5, "볼": -1.0, "낙": -10.0, "시총": 2e11}


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    갭표, 시장갭, 앞종 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                if 종c <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            p = 앞종.get(c)
            앞종[c] = 종c
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

    # 날짜(= 신호 기준일) -> 후보 종목 집합
    후보 = {}
    삼것 = {}
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        하루갭 = 갭표.get(다음) or {}
        벌, 살 = [], []
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 확정["시총"]:
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
            if kk is None or kk < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > 확정["볼"] or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > 확정["낙"]:
                continue
            벌.append((code, 낙))
            g = 하루갭.get(code)
            if (g is not None and 시갭 is not None
                    and (g - 시갭) <= 확정["갭"]):
                살.append(code)
        후보[d1] = sorted(벌, key=lambda z: z[1])
        삼것[d1] = 살
    ks = sorted(후보)
    수 = [len(후보[d]) for d in ks]
    print(f"  {len(ks):,}일 · {len(ks)/245:.1f}년\n")

    # ══ A 몇 개나 ══
    print("  ══ A **하루에 후보가 몇 개나 뜨나** ══")
    수s = sorted(수)
    print(f"     평균 **{st.mean(수):.1f}개** · 중앙 **{st.median(수):.0f}개**")
    for q, 라 in ((0, "가장 적음"), (10, "하위10%"), (25, "하위25%"),
                  (50, "중앙"), (75, "상위25%"), (90, "상위10%"),
                  (99, "상위1%"), (100, "가장 많음")):
        i2 = min(len(수s) - 1, int(len(수s) * q / 100))
        print(f"     {라:<10}{수s[i2]:>4}개")
    for n in (0, 1, 3, 5, 10, 20, 40):
        c = sum(1 for x in 수 if x <= n)
        print(f"     {n:>2}개 이하인 날  {c:>5}일 ({c/len(수)*100:>5.1f}%)")

    # ══ B 얼마나 바뀌나 ══
    print(f"\n  ══ B ⭐ **어제 후보와 오늘 후보가 얼마나 겹치나** ══")
    겹, 새 = [], []
    for j in range(1, len(ks)):
        a = {c for c, _ in 후보[ks[j - 1]]}
        b = {c for c, _ in 후보[ks[j]]}
        if not b:
            continue
        겹.append(len(a & b) / len(b) * 100)
        새.append(len(b - a))
    print(f"     오늘 후보 중 **어제도 있던 것 {st.mean(겹):.1f}%** "
          f"(중앙 {st.median(겹):.1f}%)")
    print(f"     오늘 **새로 들어온 것 평균 {st.mean(새):.1f}개**")
    print(f"     ⇒ **{'거의 그대로다' if st.mean(겹) > 70 else ('절반쯤 바뀐다' if st.mean(겹) > 40 else '매일 크게 바뀐다')}**")

    # ══ C 며칠이나 머무나 ══
    print(f"\n  ══ C **한 종목이 후보에 며칠이나 머무나** ══")
    머 = collections.Counter()
    현재 = {}
    for d in ks:
        오 = {c for c, _ in 후보[d]}
        for c in list(현재):
            if c not in 오:
                머[현재.pop(c)] += 1
        for c in 오:
            현재[c] = 현재.get(c, 0) + 1
    for v in 현재.values():
        머[v] += 1
    총 = sum(머.values())
    누 = 0
    print(f"     {'머문 날':<10}{'건수':>8}{'비율':>8}{'누적':>8}")
    for k2 in sorted(머):
        if k2 > 10:
            break
        누 += 머[k2]
        print(f"     {k2}일{'':<7}{머[k2]:>7}건{머[k2]/총*100:>7.1f}%"
              f"{누/총*100:>7.1f}%")
    긴 = sum(v for k2, v in 머.items() if k2 > 10)
    print(f"     10일 초과{'':<3}{긴:>7}건{긴/총*100:>7.1f}%")

    # ══ D 몇 개나 사게 되나 ══
    print(f"\n  ══ D **후보 중 실제로 사게 되는 것** (갭 {확정['갭']}%p 통과) ══")
    산수 = [len(삼것[d]) for d in ks]
    print(f"     평균 **{st.mean(산수):.2f}개** · 살 게 있는 날 "
          f"{sum(1 for x in 산수 if x)}일 "
          f"({sum(1 for x in 산수 if x)/len(산수)*100:.1f}%)")
    for n in (0, 1, 2, 4):
        c = sum(1 for x in 산수 if x == n) if n else sum(
            1 for x in 산수 if x == 0)
        print(f"     {n}개인 날  {c:>5}일 ({c/len(산수)*100:>5.1f}%)")
    c = sum(1 for x in 산수 if x > 4)
    print(f"     4개 초과   {c:>5}일 ({c/len(산수)*100:>5.1f}%)  "
          f"← 하루 4종목 상한에 걸린다")

    # ══ E 해별 ══
    print(f"\n  ══ E **해마다 다른가** ══")
    해 = {}
    for d in ks:
        해.setdefault(d[:4], []).append(len(후보[d]))
    print(f"     {'해':<8}{'평균 후보':>10}{'가장 많은 날':>12}{'0개인 날':>10}")
    for y in sorted(해):
        a = 해[y]
        print(f"     {y:<8}{st.mean(a):>9.1f}개{max(a):>10}개"
              f"{sum(1 for x in a if x == 0):>8}일")

    # ══ F 브리핑에 몇 개 ══
    print(f"\n  ══ F ⭐ **브리핑에 상위 N개만 실으면 몇 개를 놓치나** ══")
    print("     (후보를 20일 낙폭 깊은 순으로 자른다)")
    print(f"     {'싣는 수':<10}{'놓치는 매수':>12}{'놓침 비율':>11}")
    전체산 = sum(len(삼것[d]) for d in ks)
    for N in (5, 10, 15, 20, 30, 40):
        놓 = 0
        for d in ks:
            상 = {c for c, _ in 후보[d][:N]}
            놓 += sum(1 for c in 삼것[d] if c not in 상)
        print(f"     {N}개{'':<7}{놓:>10}건{놓/max(1,전체산)*100:>10.1f}%")

    print("\n  읽는 법")
    print("    - A·E로 **브리핑에 몇 칸을 잡아야 하는지** 정한다")
    print("    - B가 높으면 **어제와 거의 같아** 매일 볼 필요가 적다")
    print("    - F에서 놓침이 적은 N이 **실을 개수**다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
