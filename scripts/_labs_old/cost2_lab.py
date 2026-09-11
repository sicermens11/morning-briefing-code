#!/usr/bin/env python3
r"""
cost2_lab.py — **거래비용이 0.26%가 맞나** (2026-09-03 · 85차)

⚠️⚠️ **79번의 시험이 전부 왕복 0.26%를 썼다.** 그게 맞는지 확인한 적이 없다.

## 한국 주식 거래비용의 구조
```
매수  위탁수수료만 (증권거래세 없음)
매도  위탁수수료 + **증권거래세**

위탁수수료  증권사·계좌마다 다르다. 온라인 **0.015% 안팎**, 무료 이벤트도 흔하다
증권거래세  ⚠️ **연도별로 달랐다.** 단계적으로 내려왔다
```

⚠️⚠️ **내 지식으로 정확한 연도별 세율을 확신할 수 없다.**
   그래서 **하나로 못 박지 않고 여러 값으로 민감도를 본다.**
   사용자가 실제 증권사 수수료를 알려주면 그 값으로 다시 잰다.

## 재는 것
```
A 왕복 비용을 0.0 ~ 1.0%까지 흔들어 **어디서 무너지나**
B **연도별로 다른 비용**을 넣으면 (과거는 비싸고 최근은 싸다)
C 매도 방법별 민감도 — 목표 +10%(자주 판다)가 +20%보다 비용에 취약한가
D ⭐ **손익분기 비용** — 이 전략이 죽는 비용은 얼마인가
```
⚠️ 판정: 자본 시뮬 · 낙폭 · 연도별 · 2025·26 뺀 판.
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

_시작 = "20160401"
_최대보유 = 40

# ⚠️ **참고용 추정치다. 확신할 수 없다.**
#   한국 증권거래세는 단계적으로 내려왔다. 대략적인 흐름만 반영한다.
#   실제 값을 알면 여기를 고친다.
연도별세 = {"2016": 0.30, "2017": 0.30, "2018": 0.30, "2019": 0.25,
            "2020": 0.25, "2021": 0.23, "2022": 0.23, "2023": 0.20,
            "2024": 0.18, "2025": 0.15, "2026": 0.15}
_수수료 = 0.015 * 2      # 매수+매도 위탁수수료


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    날인 = {d: i for i, d in enumerate(날)}
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                if min(종, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종, 고 / 종)
            p = 앞종.get(c)
            앞종[c] = 종
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

    # ── 신호 + 경로 (비용은 나중에 뺀다) ──
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _최대보유 >= len(날):
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
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
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
            if (c1 - s20) / (2 * sd) > -1.0 or sq[k - 20] <= 0:
                continue
            if (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            길 = []
            ok = True
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    ok = False
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    ok = False
                    break
                길.append((vv[0], vv[0] * bb2[1]))
            if not ok:
                continue
            사건.append({"날": 다음, "code": code, "매수": 매수, "길": 길,
                        "상대갭": g - 시갭, "대금": 대금, "i": i + 1})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    날별 = {}
    for x in 사건:
        날별.setdefault(x["날"], []).append(x)
    print(f"  사건 {len(사건):,}건 · 신호일 {len(날별)}일 · {년수:.1f}년\n",
          flush=True)

    def 팔기(x, 비용, 목표=20.0):
        """비용은 **왕복 %**. 목표가 None이면 D+40 종가."""
        매수 = x["매수"]
        if 목표 is not None:
            for h, (종2, 고2) in enumerate(x["길"], 0):
                if 고2 >= 매수 * (1 + 목표 / 100):
                    return 목표 - 비용, max(1, h)
        끝 = x["길"][min(_최대보유, len(x["길"])) - 1][0]
        return (끝 / 매수 - 1) * 100 - 비용, _최대보유

    def 비용내기(날짜, 방식):
        if 방식 == "고정":
            return None      # 바깥에서 준다
        해 = 날짜[:4]
        return _수수료 + 연도별세.get(해, 0.20)

    def 자본(이름, 비용=None, 연도별=False, 목표=20.0, 끝날="20260902"):
        현금, 보유, 기록 = 5_000_000.0, [], []
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            남 = []
            for 청산i, 금, r in 보유:
                if 청산i <= i:
                    현금 += 금 * (1 + r / 100)
                else:
                    남.append((청산i, 금, r))
            보유 = 남
            평가 = 현금 + sum(금 for _, 금, _ in 보유)
            for x in sorted(날별.get(d) or [], key=lambda z: z["상대갭"])[:2]:
                c = (비용내기(x["날"], "연도별") if 연도별 else 비용)
                r, h = 팔기(x, c, 목표)
                쓸 = min(평가 * 0.20, x["대금"] * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                보유.append((min(x["i"] + h, len(날) - 1), 쓸, r))
            기록.append((d, 평가))
        마지막 = 기록[-1][1] if 기록 else 5_000_000.0
        해 = len(기록) / 245
        연 = ((마지막 / 5_000_000.0) ** (1 / 해) - 1) * 100 if 마지막 > 0 else -100
        최고, 낙폭 = 5_000_000.0, 0.0
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
        print(f"    {이름:<34}{마지막:>14,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{f'{플}/{전}':>8}")
        return 연

    머 = (f"    {'비용':<34}{'끝 자산':>15}{'연평균':>8}{'최대낙폭':>9}{'연도별':>8}")
    print("  ══ A **왕복 비용을 흔들면** (목표 +20% · 10.4년) ══")
    print(머)
    for c in (0.0, 0.15, 0.20, 0.26, 0.35, 0.50, 0.75, 1.00, 1.50):
        자본(f"왕복 {c:.2f}%" + ("  ← 지금 쓰는 값" if abs(c - 0.26) < 1e-9 else ""),
             비용=c)

    print("\n  ══ B **연도별 세율**을 넣으면 ══")
    print("     ⚠️ 참고용 추정치다. 실제 값을 알면 다시 잰다")
    print(f"     2016~18 {연도별세['2016']:.2f}% · 2020 {연도별세['2020']:.2f}%"
          f" · 2023 {연도별세['2023']:.2f}% · 2025~26 {연도별세['2025']:.2f}%"
          f" (+ 수수료 {_수수료:.3f}%)")
    print(머)
    자본("고정 0.26% (지금)", 비용=0.26)
    자본("**연도별 세율**", 연도별=True)

    print("\n  ══ C **매도 방법별 민감도** — 자주 파는 게 비용에 약한가 ══")
    print(머)
    for 목 in (10.0, 20.0, 30.0, None):
        라 = f"목표 +{목:.0f}%" if 목 else "D+40만"
        for c in (0.26, 0.50, 1.00):
            자본(f"{라} · 비용 {c:.2f}%", 비용=c, 목표=목)
        print()

    print("  ══ D ⭐ **손익분기 비용** — 이 전략이 죽는 비용은 ══")
    print(머)
    for c in (2.0, 3.0, 4.0, 5.0):
        자본(f"왕복 {c:.1f}%", 비용=c)

    print("\n  ══ ⚠️ 2025·26 뺀 판 ══")
    print(머)
    for c in (0.26, 0.50, 1.00):
        자본(f"왕복 {c:.2f}%", 비용=c, 끝날="20241230")
    자본("연도별 세율", 연도별=True, 끝날="20241230")

    print("\n  읽는 법")
    print("    - ⚠️⚠️ **연도별 세율은 내 추정치다.** 실제 증권사 수수료를 알면 다시 잰다")
    print("    - A에서 **0.26%가 실제보다 비싼지 싼지**가 핵심이다")
    print("       실제는 대략 **수수료 0.03% + 거래세 0.15~0.20% = 0.18~0.23%**로 보인다")
    print("       ⇒ 우리는 **보수적으로** 잡아왔을 가능성이 크다")
    print("    - C에서 목표 +10%(자주 판다)가 비용에 더 민감해야 정상이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
