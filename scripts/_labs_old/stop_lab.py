#!/usr/bin/env python3
r"""
stop_lab.py — **손절·익절을 「최악 제한」 관점에서 다시 잰다** (2026-09-02 · 43차)

⚠️⚠️ **오늘 두 번 「손절은 독」이라고 했는데, 수익만 보고 최악은 안 쟀다.**
```
13·15차  고정 −5%·−10% · 추적 −5/−10/−15%  → 전부 **성적을 깎았다**
18·21차  목표 +10% 익절 → 개별 거래 평균은 2.4배, 자본 시뮬은 **차이 없음**
⚠️ 전부 **초과수익·포트폴리오** 틀에서 쟀다. 그 틀이 잘못됐다고 35차에서 인정했다
```

## 사용자 지적으로 판정 기준을 바꾼다
```
*"기존 브리핑처럼 발굴가, 진입가(확인), 손절가 이런 걸 명시해줘도 되고"*
⚠️ **손절의 목적은 수익 증대가 아니라 최악 제한일 수 있다.**
   평균이 +5%인데 하위 25%가 −20%라면, 손절이 그걸 −10%로 막는 건 값어치가 있다.
   수익이 +5%→+4%로 줄어도 **최악이 반토막**이면 이득이다.
```

## 그래서 **다섯 가지를 같이** 낸다
```
① 평균 수익      ② 승률      ③ 중앙값
④ **하위 25%**  ← 못 될 때 얼마나 잃나. 이게 핵심이다
⑤ **최악 5%**   ← 정말 나쁠 때. 마음이 못 버티는 지점
```

## 재는 것
```
매수    사건 다음날 시가
사건    ① 볼린저 하단 이탈(16.7년) ② 신고가 첫날(16.7년)
규칙    손절 없음 / 고정 −5% · −8% · −12% / 추적 −8% · −15% /
        익절 +10% · +20% / 손절−8%+익절+20% (양쪽)
청산    최대 D+60. 규칙에 안 걸리면 D+60 종가
```
⚠️ 손절·익절 판정은 **장중 저가·고가**로 한다 — 실제로 그 가격에 걸린다.
   ⚠️ 단 **체결가를 정확히 그 값으로 가정**하는 건 낙관적이다. 갭으로 건너뛰면 더 나쁘게 체결된다.
   → **갭 건너뜀을 반영한다**: 시가가 이미 손절선 아래면 **시가에 팔린다**.
⚠️ 판정은 절대 수익. 왕복비용 0.26%.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_최대 = 60
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def _주가():
    원 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                if 종 <= 0:
                    continue
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                저 = float(v.get("저가") or 0) or 종
            except (TypeError, ValueError, KeyError):
                continue
            등 = v.get("등락률")
            try:
                등 = float(등) if 등 not in (None, "") else None
            except (TypeError, ValueError):
                등 = None
            if 등 is not None and abs(등) > 31.0:
                등 = None
            try:
                시총 = float(v.get("시총") or 0)
                대금 = float(v.get("거래대금") or 0)
            except (TypeError, ValueError):
                시총 = 대금 = 0.0
            하루[c] = (종, 시, 고, 저, 등, 시총, 대금)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 고, 저, 등, 시총, 대금) in 원[d].items():
            p, s = 앞원.get(c), 앞수.get(c)
            if p is None or s is None:
                수 = 종
            elif 등 is not None:
                수 = s * (1 + 등 / 100.0)
            else:
                r = 종 / p - 1 if p > 0 else 0.0
                수 = s * (1 + (0.0 if abs(r) > 0.32 else r))
            if 수 <= 0:
                수 = s if s and s > 0 else 종
            배 = 수 / 종 if 종 else 1.0
            앞원[c], 앞수[c] = 종, 수
            하루[c] = (수, 시 * 배, 고 * 배, 저 * 배, 시총, 대금)
        out[d] = 하루
    return out


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

    사건 = {}
    앞상태 = {}
    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + _최대 >= len(날):
            앞상태 = {}
            continue
        오늘 = {}
        for code, v in 주가[d1].items():
            c1, _시, _고, _저, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
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
            고250 = max(sq[k - 250:k + 1])
            신 = bool(고250) and c1 >= 고250 * 0.999
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼하 = (c1 - s20) / (2 * sd) <= -1.0
            상태 = (볼하, 신)
            오늘[code] = 상태
            앞 = 앞상태.get(code)
            if 앞 is None:
                continue
            g = _크기(시총)
            if 볼하 and not 앞[0]:
                사건.setdefault("볼린저 하단 이탈", []).append((i, code, g))
            if 신 and not 앞[1]:
                사건.setdefault("신고가 첫날", []).append((i, code, g))
        앞상태 = 오늘
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일", flush=True)
    print("  " + " · ".join(f"{k} {len(v):,}건" for k, v in 사건.items()), flush=True)

    규칙들 = [("손절 없음", None, None, None),
              ("고정 −5%", -5, None, None), ("고정 −8%", -8, None, None),
              ("고정 −12%", -12, None, None),
              ("추적 −8%", None, -8, None), ("추적 −15%", None, -15, None),
              ("익절 +10%", None, None, 10), ("익절 +20%", None, None, 20),
              ("−8% & +20%", -8, None, 20)]

    def 성과(목록, 손절, 추적, 익절):
        결과, 든날 = [], []
        for (i, code, g) in 목록:
            나 = 주가[날[i + 1]].get(code)
            if not 나 or 나[1] <= 0:
                continue
            매수 = 나[1]
            팔 = None
            일 = _최대
            최고 = 매수
            # ⚠️ 매수 당일(시가 매수)부터 판정한다. 그날 장중도 걸릴 수 있다
            for j in range(i + 1, i + 1 + _최대):
                v = 주가[날[j]].get(code)
                if not v:
                    continue
                종, 시, 고, 저, _, _ = v
                # ⚠️ **갭 건너뜀 반영** — 시가가 이미 선을 넘었으면 시가에 팔린다
                손선 = 매수 * (1 + 손절 / 100) if 손절 is not None else None
                추선 = 최고 * (1 + 추적 / 100) if 추적 is not None else None
                익선 = 매수 * (1 + 익절 / 100) if 익절 is not None else None
                선 = max([x for x in (손선, 추선) if x is not None], default=None)
                if 선 is not None:
                    if j > i + 1 and 시 <= 선:
                        팔, 일 = 시, j - i - 1
                        break
                    if 저 <= 선:
                        팔, 일 = 선, j - i - 1
                        break
                if 익선 is not None:
                    if j > i + 1 and 시 >= 익선:
                        팔, 일 = 시, j - i - 1
                        break
                    if 고 >= 익선:
                        팔, 일 = 익선, j - i - 1
                        break
                최고 = max(최고, 고)
            if 팔 is None:
                e = 주가[날[i + _최대]].get(code)
                if not e:
                    continue
                팔 = e[0]
            결과.append((팔 / 매수 - 1) * 100 - _비용)
            든날.append(일)
        return 결과, 든날

    print(f"\n  ══ 손절·익절 — **최악이 얼마나 주는지**를 같이 본다 (매수 D+1 시가 · 최대 D+{_최대}) ══")
    print("     ⚠️ 갭 건너뜀 반영 — 시가가 이미 선을 넘었으면 시가에 팔린 것으로 계산")
    for 이름, 목록전 in 사건.items():
        for g, _, _ in 크기표:
            목록 = [x for x in 목록전 if x[2] == g]
            if len(목록) < 3000:
                continue
            print(f"\n  ── {이름} · {g} (사건 {len(목록):,}건) ──")
            print(f"    {'규칙':<14}{'평균':>9}{'승률':>8}{'중앙값':>9}"
                  f"{'하위25%':>10}{'최악5%':>10}{'평균보유':>9}")
            바닥 = None
            for 라벨, 손, 추, 익 in 규칙들:
                a, 일 = 성과(목록, 손, 추, 익)
                if len(a) < 1000:
                    continue
                a2 = sorted(a)
                n = len(a2)
                승 = sum(1 for x in a2 if x > 0) / n * 100
                하25 = a2[n // 4]
                최5 = a2[n // 20]
                if 라벨 == "손절 없음":
                    바닥 = (st.mean(a2), 하25, 최5)
                표 = ""
                if 바닥 and 라벨 != "손절 없음":
                    수익차 = st.mean(a2) - 바닥[0]
                    최악차 = 하25 - 바닥[1]
                    # ⚠️ **수익이 준 것보다 최악이 더 많이 좋아지면** 값어치가 있다
                    if 최악차 > abs(수익차) * 1.0 and 최악차 > 0:
                        표 = "⭐"
                    elif 최악차 > 0:
                        표 = "○"
                print(f"    {라벨:<14}{st.mean(a2):>+8.2f}%{승:>7.1f}%"
                      f"{st.median(a2):>+8.2f}%{하25:>+9.2f}%{최5:>+9.2f}%"
                      f"{st.mean(일):>8.1f}일{표}")

    print("\n  읽는 법")
    print("    - ⭐ = **수익이 준 것보다 최악이 더 많이 좋아졌다** → 손절이 값어치 있다")
    print("    - ○ = 최악은 좋아졌지만 수익을 더 많이 내줬다 → 취향 문제다")
    print("    - 표 없음 = 최악도 안 좋아졌다 → **그 규칙은 순수한 손해**다")
    print("    - '평균보유'가 짧아지면 자본이 빨리 돈다(포트폴리오에선 이득, 개별로는 무관)")
    print("    - ⚠️ 갭 건너뜀을 반영했지만 여전히 낙관적이다 — 실제로는 호가가 비어 더 나쁠 수 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
