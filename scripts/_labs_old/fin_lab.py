#!/usr/bin/env python3
r"""
fin_lab.py — **연간 재무 11년치를 파고든다** (2026-09-03 · 59차)

⚠️⚠️ **58차에서 나온 것.** 안 쓰고 있던 `dart-fin`(2015~2025)이 답이었다.
```
바탕(상대−3 · **시장 조건 없음** · 볼−1 · 20일−10)   +2.48% · 53.2% · 9/11해
잉여금비율 상위1/3                                 **+9.70% · 71.2% · 10/11해**
부채비율 하위1/3                                    +6.47% · 59.4% · **11/11해**
흑자 기업만                                        +5.15% · 60.3% · **11/11해**
```
**「시장이 빠진 날」을 기다리지 않아도 듣는다.** 이게 「투입비 24%」를 푸는 길일 수 있다.

⚠️⚠️ **58차 표의 「연간」 칸에 버그가 있었다.** ③은 2016-04부터라 10.4년인데
   16.7년으로 나눴다 → **빈도가 1.6배 낮게 찍혔다.** 여기선 재무가 있는 구간의 년수로 나눈다.

## 재는 것
```
A 재무 단독      각 지표 · 여러 문턱 (시장·기술 조건 없이 재무만으로 뽑으면?)
B 재무 겹치기    잉여금 + 흑자 + 부채비율 … 둘셋을 겹치면 더 좋아지나
C 재무 + 시장    폭락일 조건을 얹으면 (58차 ①과 견줄 수 있다)
D 빈도-성적 곡선 각 조합의 **연 신호일**을 정확히 재서 「일상용」이 있는지 본다
```
⚠️ **look-ahead**: Y년 사업보고서는 Y+1년 3월말 공시 → **Y+1년 4월 1일부터** 쓴다.
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · D+20 · 비용 0.26% · **날짜 단위** · 연도별 3분의 2.
⚠️ 다중검정: 조합을 많이 보므로 **연도별 통과**를 반드시 함께 본다.
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
_보유 = 20
_시작 = "20160401"      # ⚠️ 2015년치를 처음 쓸 수 있는 날


def 요약(날별, 이름, 년수, 폭=38):
    if len(날별) < 8:
        print(f"    {이름:<{폭}}신호일 {len(날별)}일 — 표본 부족")
        return None
    수 = [st.mean(v) for v in 날별.values()]
    승 = sum(1 for x in 수 if x > 0) / len(수) * 100
    해별 = {}
    for d, v in 날별.items():
        해별.setdefault(d[:4], []).append(st.mean(v))
    전 = 플 = 0
    for y, arr in 해별.items():
        if len(arr) < 3:
            continue
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
    a = sorted(수)
    종 = sum(len(v) for v in 날별.values())
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 8
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/년수:>7.1f}일{f'{플}/{전}':>8}{len(날별):>7}일{종:>8}종{별}")
    return st.mean(수), 승, len(날별), 플, 전


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가)]
    기본 = O._기본()
    재무 = 연간재무()
    print(f"  연간재무 {len(재무):,}종목", flush=True)
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

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

    # ── 후보: 재무가 있는 구간만. 기술 조건은 느슨하게 잡고 뒤에서 거른다 ──
    후보 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
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
            if g is None or (g - 시갭) > -1:
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
            if sq[k - 20] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            후보.append((다음, (끝[0] / 매수 - 1) * 100 - _비용,
                         g - 시갭, 시갭, 볼, r20, fm))
        if i % 800 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)

    쓴날 = [d for d in 날 if d >= _시작]
    년수 = len(쓴날) / 245
    print(f"  후보 {len(후보):,}건 · {_시작}부터 {년수:.1f}년 "
          f"({len(쓴날):,}거래일)\n", flush=True)

    def 모으기(*조건):
        t = {}
        for d, r, rg, mg, bb, rr, fm in 후보:
            if all(c(rg, mg, bb, rr, fm) for c in 조건):
                t.setdefault(d, []).append(r)
        return t

    기술 = lambda rg, mg, bb, rr, fm: rg <= -3 and bb <= -1.0 and rr <= -10  # noqa: E731
    머 = (f"    {'조합':<38}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'신호일':>8}{'종목':>9}")

    print("  ══ A 재무 지표 단독 — **시장 조건 없이** (바탕: 상대−3·볼−1·20일−10) ══")
    print(머)
    요약(모으기(기술), "바탕 (재무 조건 없음)", 년수)
    지표 = ["잉여금비율", "부채비율", "ROE", "ROA", "영업이익률", "순이익률", "유동비율"]
    상하 = {}
    for 항 in 지표:
        값 = sorted(fm[항] for _, _, rg, mg, bb, rr, fm in 후보
                    if 항 in fm and rg <= -3 and bb <= -1.0 and rr <= -10)
        if len(값) < 300:
            print(f"    {항:<38}표본 {len(값)} — 부족")
            continue
        상하[항] = (값[len(값) // 4],값[len(값) // 2], 값[len(값) * 3 // 4])
        for 라, 문 in (("상위1/4", 값[len(값) * 3 // 4]), ("상위1/2", 값[len(값) // 2])):
            요약(모으기(기술, lambda rg, mg, bb, rr, fm, a=항, x=문:
                       a in fm and fm[a] >= x), f"{항} {라} (≥{문:.1f})", 년수)
        for 라, 문 in (("하위1/4", 값[len(값) // 4]), ("하위1/2", 값[len(값) // 2])):
            요약(모으기(기술, lambda rg, mg, bb, rr, fm, a=항, x=문:
                       a in fm and fm[a] <= x), f"{항} {라} (≤{문:.1f})", 년수)
    요약(모으기(기술, lambda rg, mg, bb, rr, fm: fm.get("흑자") == 1.0),
         "흑자 기업만", 년수)

    print("\n  ══ B 재무를 겹친다 ══")
    print(머)
    잉 = 상하.get("잉여금비율")
    부 = 상하.get("부채비율")
    영 = 상하.get("영업이익률")
    유 = 상하.get("유동비율")
    겹 = []
    if 잉:
        겹.append(("잉여금 상위1/2", lambda fm: fm.get("잉여금비율", -9e9) >= 잉[1]))
        겹.append(("잉여금 상위1/4", lambda fm: fm.get("잉여금비율", -9e9) >= 잉[2]))
    if 부:
        겹.append(("부채비율 하위1/2", lambda fm: fm.get("부채비율", 9e9) <= 부[1]))
    if 영:
        겹.append(("영업이익률 상위1/2", lambda fm: fm.get("영업이익률", -9e9) >= 영[1]))
    if 유:
        겹.append(("유동비율 상위1/2", lambda fm: fm.get("유동비율", -9e9) >= 유[1]))
    흑 = ("흑자", lambda fm: fm.get("흑자") == 1.0)
    겹.append(흑)
    for i in range(len(겹)):
        for j in range(i + 1, len(겹)):
            n1, f1 = 겹[i]
            n2, f2 = 겹[j]
            요약(모으기(기술, lambda rg, mg, bb, rr, fm, a=f1, b=f2: a(fm) and b(fm)),
                 f"{n1} + {n2}", 년수)
    if 잉 and 부:
        요약(모으기(기술, lambda rg, mg, bb, rr, fm:
                   fm.get("잉여금비율", -9e9) >= 잉[1]
                   and fm.get("부채비율", 9e9) <= 부[1]
                   and fm.get("흑자") == 1.0), "잉여금↑ + 부채↓ + 흑자 (셋)", 년수)

    print("\n  ══ C 재무 + 시장 조건 (폭락일을 얹으면) ══")
    print(머)
    for 문, 라 in ((0.5, "시장 무관"), (0.0, "시장 −0.0%↓"),
                   (-0.3, "시장 −0.3%↓"), (-0.6, "시장 −0.6%↓")):
        요약(모으기(기술, lambda rg, mg, bb, rr, fm, x=문: mg < x),
             f"바탕 · {라}", 년수)
        if 잉:
            요약(모으기(기술,
                       lambda rg, mg, bb, rr, fm, x=문:
                       mg < x and fm.get("잉여금비율", -9e9) >= 잉[1]),
                 f"잉여금 상위1/2 · {라}", 년수)

    print("\n  ══ D 기술 조건도 함께 흔든다 (재무는 「잉여금 상위1/2 + 흑자」 고정) ══")
    print(머)
    if 잉:
        좋재무 = lambda fm: (fm.get("잉여금비율", -9e9) >= 잉[1]  # noqa: E731
                            and fm.get("흑자") == 1.0)
        for rg문, bb문, rr문 in ((-4, -1.0, -10), (-3, -1.0, -10), (-2, -1.0, -10),
                                 (-3, -0.7, -5), (-3, -0.5, 0), (-2, -0.5, 0),
                                 (-1, -0.5, 0), (-1, 0.0, 99)):
            요약(모으기(lambda rg, mg, bb, rr, fm, a=rg문, b=bb문, c=rr문:
                       rg <= a and bb <= b and rr <= c and 좋재무(fm)),
                 f"상대{rg문} · 볼{bb문:+.1f} · 20일{rr문}", 년수)

    print("\n  읽는 법")
    print("    - **연 40일 이상 + 승률 60%↑ + 연도별 3분의 2**면 브리핑에 쓸 수 있다")
    print("    - A에 시장 조건이 없다 — **폭락을 기다리지 않는 신호**를 찾는 게 목표다")
    print(f"    - ⚠️ {_시작}부터 {년수:.1f}년뿐이다. 연도가 11개를 못 넘는다")
    print("    - ⚠️ 조합을 많이 봤다(다중검정). **연도별이 통과 못 하면 버린다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
