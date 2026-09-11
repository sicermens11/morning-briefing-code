#!/usr/bin/env python3
r"""
fair_lab.py — **공정 비교 + 자본 시뮬 + 매도 시점** (2026-09-03 · 60차)

⚠️⚠️ **59차에서 나온 것.** 재무를 넣으니 원래 신호보다 나았다.
```
                        평균      승률    하위25%   연간    연도별
원래 신호(날짜 단위)      +6.91%  65.9%   −3.78%   7.7일  13/15해   16.7년
잉여금↑+부채↓+흑자     +10.53%  74.8%   −0.74%  12.6일  11/11해   10.4년
```
⚠️⚠️ **그런데 기간이 다르다.** 재무는 2016-04부터라 10.4년뿐이다.
   **같은 10.4년으로 잘라 견주지 않으면 공정하지 않다.** 그게 ①이다.

## 재는 것
```
① **공정 비교** — 원래 신호를 20160401부터로 잘라 재무 조합과 나란히
② **매도 시점** — D+5 · 10 · 20 · 40 · 60. 지금 D+20이 최적인가
③ **자본 시뮬** — 초기 500만 · 자산의 N%씩 · 실제로 돈이 느나
   ⚠️⚠️ 53차 버그 재발 방지: **주수를 쓰지 않는다.**
      (청산일, 투자금, 매수시_수정단가)로 담고
      매도금 = 투자금 × (수정단가_매도 / 수정단가_매수)
④ **투입비** — 자금의 몇 %가 실제로 일하나
```
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · 비용 0.26% · **날짜 단위** · 연도별 3분의 2.
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


def 재기(날별, 이름, 년수, 폭=32):
    if len(날별) < 8:
        print(f"    {이름:<{폭}}신호일 {len(날별)}일 — 부족")
        return None
    수 = [st.mean(v) for v in 날별.values()]
    승 = sum(1 for x in 수 if x > 0) / len(수) * 100
    해 = {}
    for d, v in 날별.items():
        해.setdefault(d[:4], []).append(st.mean(v))
    전 = 플 = 0
    for y, arr in 해.items():
        if len(arr) < 3:
            continue
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
    a = sorted(수)
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 8
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/년수:>7.1f}일{f'{플}/{전}':>8}{len(날별):>7}일{별}")
    return st.mean(수), 승


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
    갭표, 시장갭, 앞종 = {}, {}, {}
    원시 = {}
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
            원시.setdefault(d["기준일"], {})[c] = 시
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

    # ── 후보 (매도 시점을 여러 개 담는다) ──
    보유들 = (5, 10, 20, 40, 60)
    후보 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + max(보유들) >= len(날):
            continue
        다음 = 날[i + 1]
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
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            수익 = {}
            for h in 보유들:
                끝 = 주가[날[i + 1 + h]].get(code)
                if 끝:
                    수익[h] = (끝[0] / 매수 - 1) * 100 - _비용
            if 20 not in 수익:
                continue
            후보.append((다음, code, 수익, g - 시갭, 시갭, 볼, r20,
                         재무값(code, d1), 매수, i + 1))
        if i % 800 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)
    print(f"  후보 {len(후보):,}건\n", flush=True)

    # 문턱 (59차에서 나온 값)
    잉값 = sorted(x[7]["잉여금비율"] for x in 후보
                  if x[7] and "잉여금비율" in x[7] and x[0] >= _시작)
    부값 = sorted(x[7]["부채비율"] for x in 후보
                  if x[7] and "부채비율" in x[7] and x[0] >= _시작)
    잉문, 부문 = 잉값[len(잉값) // 2], 부값[len(부값) // 2]
    print(f"  문턱: 잉여금비율 ≥{잉문:.1f}% · 부채비율 ≤{부문:.1f}%\n")

    def 기술(x, rg=-3, bo=-1.0, rr=-10):
        return x[3] <= rg and x[5] <= bo and x[6] <= rr

    def 좋재무(x):
        m = x[7]
        return bool(m) and m.get("잉여금비율", -9e9) >= 잉문 \
            and m.get("부채비율", 9e9) <= 부문 and m.get("흑자") == 1.0

    def 모으기(고르기, 보유=20, 부터=None):
        t = {}
        for x in 후보:
            if 부터 and x[0] < 부터:
                continue
            if 보유 not in x[2]:
                continue
            if 고르기(x):
                t.setdefault(x[0], []).append(x[2][보유])
        return t

    쓴 = [d for d in 날 if d >= _시작]
    년A, 년B = len(날) / 245, len(쓴) / 245
    머 = (f"    {'조합':<32}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'신호일':>8}")

    print(f"  ══ ① 공정 비교 — **같은 {년B:.1f}년({_시작}부터)으로 잘라** ══")
    print(머)
    print(f"    ── 16.7년 전체 (참고) ──")
    재기(모으기(lambda x: 기술(x, -4)), "원래 신호 (상대−4·시장무관)", 년A)
    재기(모으기(lambda x: 기술(x, -4) and x[4] < -0.3),
         "원래 신호 (상대−4·시장−0.3)", 년A)
    print(f"    ── {_시작}부터 {년B:.1f}년 — **여기가 공정한 비교다** ──")
    재기(모으기(lambda x: 기술(x, -4), 부터=_시작), "원래 신호 (상대−4·시장무관)", 년B)
    재기(모으기(lambda x: 기술(x, -4) and x[4] < -0.3, 부터=_시작),
         "원래 신호 (상대−4·시장−0.3)", 년B)
    재기(모으기(lambda x: 기술(x, -3), 부터=_시작), "기술만 (상대−3·시장무관)", 년B)
    재기(모으기(lambda x: 기술(x, -3) and 좋재무(x), 부터=_시작),
         "**+재무(잉여금↑부채↓흑자)**", 년B)
    재기(모으기(lambda x: 기술(x, -4) and 좋재무(x), 부터=_시작),
         "**+재무 · 상대−4**", 년B)
    재기(모으기(lambda x: 기술(x, -3) and 좋재무(x) and x[4] < -0.3, 부터=_시작),
         "**+재무 · 시장−0.3**", 년B)

    print(f"\n  ══ ② 매도 시점 — D+5 ~ D+60 ══")
    print(머)
    for h in 보유들:
        재기(모으기(lambda x: 기술(x, -3) and 좋재무(x), 보유=h, 부터=_시작),
             f"+재무 · **D+{h}**", 년B)
    print()
    for h in 보유들:
        재기(모으기(lambda x: 기술(x, -4), 보유=h, 부터=_시작),
             f"원래 신호 · D+{h}", 년B)

    # ── ③ 자본 시뮬 ──
    print(f"\n  ══ ③ 자본 시뮬 — 초기 500만원 ══")
    print("     ⚠️⚠️ **주수를 쓰지 않는다.** 53차 버그(원본가/수정가 섞기) 재발 방지")

    def 시뮬(고르기, 비율, 보유, 이름, 부터=_시작, 초기=5_000_000.0):
        날인 = {d: i for i, d in enumerate(날)}
        살것 = {}
        for x in 후보:
            if x[0] < 부터 or 보유 not in x[2] or not 고르기(x):
                continue
            살것.setdefault(x[0], []).append(x)
        현금, 보유중 = 초기, []      # (청산i, 투자금, 매수단가, code)
        기록, 투입일 = [], []
        for d in [z for z in 날 if z >= 부터]:
            i = 날인[d]
            남 = []
            for 청산, 금, 단가, code in 보유중:
                if 청산 <= i:
                    끝 = 주가[날[min(청산, len(날) - 1)]].get(code)
                    if 끝:
                        현금 += 금 * (끝[0] / 단가) * (1 - _비용 / 100)
                    else:
                        현금 += 금            # 자료 없으면 원금 회수로 본다
                else:
                    남.append((청산, 금, 단가, code))
            보유중 = 남
            평가 = 현금
            for 청산, 금, 단가, code in 보유중:
                v = 주가[d].get(code)
                평가 += 금 * (v[0] / 단가) if v else 금
            for x in 살것.get(d, []):
                쓸 = 평가 * 비율
                if 쓸 > 현금 or 쓸 < 10_000:
                    continue
                # ⚠️ 매수 단가는 **수정 시가** = 전날 수정종가 × (1 + 갭/100)
                단가 = x[8]
                현금 -= 쓸
                보유중.append((min(i + 보유, len(날) - 1), 쓸, 단가, x[1]))
            기록.append((d, 평가))
            투입일.append(1 - 현금 / 평가 if 평가 > 0 else 0)
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
        print(f"    {이름:<32}{마지막:>13,.0f}원{연:>+8.2f}%/년"
              f"{낙폭*100:>9.1f}%{sum(투입일)/max(1,len(투입일))*100:>8.1f}%"
              f"{f'{플}/{전}':>8}")
        return 연

    print(f"    {'조합':<32}{'끝 자산':>14}{'연평균':>12}{'최대낙폭':>9}"
          f"{'투입비':>8}{'연도별':>8}")
    for 비율 in (0.10, 0.20, 0.34):
        시뮬(lambda x: 기술(x, -3) and 좋재무(x), 비율, 20,
             f"+재무 · 자산의 {비율*100:.0f}%씩 · D+20")
    for h in (10, 40, 60):
        시뮬(lambda x: 기술(x, -3) and 좋재무(x), 0.20, h,
             f"+재무 · 20%씩 · **D+{h}**")
    시뮬(lambda x: 기술(x, -4), 0.20, 20, "원래 신호 · 20%씩 · D+20")
    시뮬(lambda x: 기술(x, -2) and 좋재무(x), 0.20, 20,
         "+재무 · **상대−2**(빈도↑) · 20%씩")

    print("\n  읽는 법")
    print("    - ①의 아래 칸끼리만 견준다. **위 칸(16.7년)과 섞어 보면 안 된다**")
    print("    - ③의 **투입비**가 낮으면 자금이 노는 것이다 — 신호가 드물다는 뜻")
    print("    - ③의 **최대낙폭**은 「이만큼 깨지는 구간을 견뎌야 한다」는 뜻이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
