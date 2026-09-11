#!/usr/bin/env python3
r"""
port_lab.py — **종목의 조합: 몇 개를 어떻게 묶을 것인가** (2026-09-03 · 77차)

⚠️⚠️ **사용자 아이디어.**
   *"승률 수익률을 위해 한 종목이 아니라, 여러 종목을 사서 하락을 방어할 수 있는지도
     테스트하고 있나보네. 이게 검증되면 브리핑엔 이유를 설명하고, 세트로 추천해도 좋을 것 같아."*
   *"조건의 조합 뿐만 아니라, 종목의 조합도 보는 거 좋네"*

## 지금까지 안 본 것
```
봤다    **조건**의 조합 (재무 x 갭 x 볼린저 x 미국 x 매도규칙)
봤다    한 종목에 **얼마씩** (10% · 20% · 34% · 50%)
⚠️ **안 봤다**  **동시에 몇 종목**을 들 것인가
⚠️ **안 봤다**  같은 날 여러 개가 뜨면 **다 사나 골라 사나**
⚠️ **안 봤다**  **어떤 종목끼리 묶어야** 서로를 방어하나
```

## 왜 「어떤 조합인가」가 중요한가
```
같은 날 3종목이 떠도 **셋이 같은 이유로 빠졌다면 같이 더 빠진다.**
분산은 **서로 다르게 움직일 때만** 효과가 있다.
⚠️ 우리에겐 **업종 분류가 없다**(기본()의 「업종」은 소속부다).
   ⇒ 대신 **시총 구간 · 상대갭 크기 · 20일 낙폭 · 재무 등급**으로 나눈다
```

## 재는 것
```
A 종목 수 상한   하루 1개만 / 2개 / 3개 / 5개 / 무제한
B 고르는 기준    같은 날 여러 개면 무엇을 먼저 사나
                 (상대갭 큰 순 / 재무 좋은 순 / 거래대금 큰 순 / 무작위)
C ⭐ **조합의 성격**  같은 시총 구간끼리 vs 흩어서
                 같은 낙폭대끼리 vs 흩어서
D 동시 보유 수와 낙폭의 관계 — **몇 개부터 방어가 되나**
E ⭐ **세트 추천** — 실제로 묶어 추천할 만한 조합이 있나
```
⚠️ 매도는 **76차에서 확정한 「목표 +20% 지정가 · 최대 D+40 · 손절 없음」**을 쓴다.
⚠️ 판정: 자본 시뮬(초기 500만) · 낙폭 · 연도별 · 2025·26 뺀 판까지.
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
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_최대보유 = 40
_목표 = 20.0


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
    저비, 고비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                저 = float(v.get("저가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                if min(종, 시, 저, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            저비.setdefault(d8, {})[c] = 저 / 종
            고비.setdefault(d8, {})[c] = 고 / 종
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

    # ── 신호 + 76차 매도 규칙으로 (수익, 보유일) 미리 계산 ──
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
            r20 = (c1 / sq[k - 20] - 1) * 100
            if r20 > -10:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            # 76차 매도 규칙: 목표 +20% 지정가 · 최대 D+40 · 손절 없음
            수익 = None
            보유 = _최대보유
            for h in range(0, _최대보유):
                j = i + 1 + h
                if j >= len(날):
                    break
                dd = 날[j]
                v2 = 주가[dd].get(code)
                if not v2:
                    break
                hi = (고비.get(dd) or {}).get(code, 1.0) * v2[0]
                if hi >= 매수 * (1 + _목표 / 100):
                    수익, 보유 = _목표 - _비용, max(1, h)
                    break
            if 수익 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                수익, 보유 = (끝[0] / 매수 - 1) * 100 - _비용, _최대보유
            사건.append({
                "날": 다음, "code": code, "수익": 수익, "보유": 보유,
                "시총": 시총, "대금": 대금, "상대갭": g - 시갭,
                "낙폭20": r20, "잉여금": fm.get("잉여금비율"),
                "부채": fm.get("부채비율"), "i": i + 1})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    날별 = {}
    for x in 사건:
        날별.setdefault(x["날"], []).append(x)
    많은날 = sorted((len(v) for v in 날별.values()), reverse=True)
    print(f"  사건 {len(사건):,}건 · 신호일 {len(날별)}일 · {년수:.1f}년")
    print(f"  하루 신호 수: 중앙 {st.median(많은날):.0f}개 · 최대 {많은날[0]}개 "
          f"· 1개뿐인 날 {sum(1 for v in 많은날 if v == 1)}일 "
          f"({sum(1 for v in 많은날 if v == 1)/len(많은날)*100:.0f}%)\n", flush=True)

    def 시뮬(이름, 하루상한=None, 고르기=None, 비중=0.20, 끝날="20260902",
             흩기=None, 시드=0):
        rng = random.Random(시드)
        현금, 보유, 기록, 투입 = 5_000_000.0, [], [], []
        동시 = []
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
            오늘 = list(날별.get(d) or [])
            if 고르기:
                오늘 = 고르기(오늘, rng)
            if 흩기:
                오늘 = 흩기(오늘)
            if 하루상한:
                오늘 = 오늘[:하루상한]
            for x in 오늘:
                쓸 = min(평가 * 비중, x["대금"] * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                보유.append((min(x["i"] + x["보유"], len(날) - 1), 쓸, x["수익"]))
            기록.append((d, 평가))
            투입.append(sum(금 for _, 금, _ in 보유) / 평가 if 평가 > 0 else 0)
            동시.append(len(보유))
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
        print(f"    {이름:<34}{마지막:>13,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{sum(투입)/max(1,len(투입))*100:>8.1f}%{st.mean(동시):>7.1f}개"
              f"{f'{플}/{전}':>8}")
        return 연, 낙폭

    머 = (f"    {'전략':<34}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
          f"{'투입비':>8}{'동시':>8}{'연도별':>8}")

    for 끝날, 라 in (("20260902", "2016-04 ~ 2026-09 (10.4년)"),
                     ("20241230", "2016-04 ~ 2024-12 (8.8년) — 2025·26 뺌")):
        print("\n  ══════ " + 라 + " ══════")
        print("  ── A 하루에 **몇 종목**까지 살 것인가 (상대갭 큰 순) ──")
        print(머)
        크게 = (lambda a, r: sorted(a, key=lambda x: x["상대갭"]))
        for n in (1, 2, 3, 5, None):
            시뮬(f"하루 최대 {n if n else '무제한'}개", 하루상한=n, 고르기=크게,
                 끝날=끝날)

    print("\n  ══════ B **고르는 기준** (하루 3개 · 10.4년) ══════")
    print(머)
    기준들 = (("상대갭 큰 순", lambda a, r: sorted(a, key=lambda x: x["상대갭"])),
              ("상대갭 작은 순", lambda a, r: sorted(a, key=lambda x: -x["상대갭"])),
              ("20일 낙폭 큰 순", lambda a, r: sorted(a, key=lambda x: x["낙폭20"])),
              ("잉여금 많은 순", lambda a, r: sorted(a, key=lambda x: -(x["잉여금"] or 0))),
              ("부채 적은 순", lambda a, r: sorted(a, key=lambda x: (x["부채"] or 9e9))),
              ("거래대금 큰 순", lambda a, r: sorted(a, key=lambda x: -x["대금"])),
              ("시총 작은 순", lambda a, r: sorted(a, key=lambda x: x["시총"])),
              ("무작위", lambda a, r: r.sample(a, len(a))))
    for 라, f in 기준들:
        시뮬(라, 하루상한=3, 고르기=f)

    print("\n  ══════ C ⭐ **조합의 성격** — 흩어야 방어가 되나 (하루 3개) ══════")
    print("     ⚠️ 업종 분류가 없어 **시총 구간 · 낙폭대**로 나눈다")

    def 흩기시총(a):
        """시총 구간(소·중·대)이 겹치지 않게 고른다."""
        def 구간(x):
            m = x["시총"] / 1e8
            return 0 if m < 500 else (1 if m < 1500 else 2)
        본, 남 = [], []
        쓴 = set()
        for x in sorted(a, key=lambda z: z["상대갭"]):
            g = 구간(x)
            (본 if g not in 쓴 else 남).append(x)
            쓴.add(g)
        return 본 + 남

    def 흩기낙폭(a):
        def 구간(x):
            r = x["낙폭20"]
            return 0 if r < -25 else (1 if r < -15 else 2)
        본, 남, 쓴 = [], [], set()
        for x in sorted(a, key=lambda z: z["상대갭"]):
            g = 구간(x)
            (본 if g not in 쓴 else 남).append(x)
            쓴.add(g)
        return 본 + 남
    print(머)
    시뮬("그냥 상대갭 큰 순 (기준선)", 하루상한=3, 고르기=크게)
    시뮬("**시총 구간을 흩어서**", 하루상한=3, 고르기=크게, 흩기=흩기시총)
    시뮬("**20일 낙폭대를 흩어서**", 하루상한=3, 고르기=크게, 흩기=흩기낙폭)

    print("\n  ══════ D 종목 수 x 비중 (10.4년) ══════")
    print(머)
    for n, 비 in ((1, 0.34), (2, 0.34), (3, 0.20), (3, 0.34),
                   (5, 0.20), (5, 0.15), (None, 0.20), (None, 0.10)):
        시뮬(f"하루 {n if n else '무제한'}개 · 종목당 {비*100:.0f}%",
             하루상한=n, 고르기=크게, 비중=비)

    print("\n  읽는 법")
    print("    - A에서 **몇 개부터 낙폭이 줄어드는지**가 「세트」의 근거다")
    print("    - B에서 기준별 차이가 크면 **브리핑에서 순서를 정해줘야** 한다")
    print("    - C에서 흩는 게 나으면 **성격이 다른 것끼리 묶어 추천**한다")
    print("    - ⚠️ 매도는 76차 규칙(목표 +20% · 최대 D+40 · 손절 없음)을 썼다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
