#!/usr/bin/env python3
r"""
wide_lab.py — **조건 25개를 전수 조합해 새 신호를 찾는다** (2026-09-02 · 50차)

⚠️⚠️ **사용자 지적.**
   *"이긴 조합에서만 붙이면, 새로운 조합은 못 찾는 거 아니야?"*
   ⚠️ 맞다. 48차(`combo3_lab`)는 **탐색이 아니라 개선**이다.
      「신고가 + 수급 + 재무」처럼 완전히 다른 조합은 영영 안 나온다.

## 그래서 **넓게 전수 탐색**한다
```
조건 25개를 1·2·3개씩  =  25 + 300 + 2,300 = **2,625 조합** × 크기 3 = 7,875칸
⚠️ 다중검정이 심각하다 → **연도별 문턱(3분의 2)** + 표본 400건으로 거른다
```

## 조건 25개 — 안 쓴 데이터를 최대한 넣는다
```
가격 반전(5)   볼하단 · 볼−2σ · RSI≤30 · 60일최저 · 20일−10%↓
가격 모멘텀(5) 신고가 · RSI≥70 · 볼상단 · 20일선위 · 20일+10%↑
갭(3)         갭−2%↓ · 갭0~2% · 갭+2%↑
거래(2)       거래량3배↑ · 거래량0.5배↓(한산)
수급(4)       외국인순매수 · 기관순매수 · 둘다 · 수급강도0.5%↑
재무(3)       영업이익흑자 · 영업이익률5%↑ · 순이익흑자
시장(2)       코스닥 · 코스피
국면(1)       약세장
```
⚠️ 판정: **절대 수익** · 승률 · 연도별 · 다음날 시가 매수 · D+20 · 비용 0.26%.
⚠️ 재무는 분기말+75일부터 쓴다(look-ahead 방지).
"""
import glob
import io
import itertools
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_보유 = 20
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]

축 = ["볼하단", "볼−2σ", "RSI≤30", "60일최저", "20일−10%↓",
      "신고가", "RSI≥70", "볼상단", "20일선위", "20일+10%↑",
      "갭−2%↓", "갭0~2%", "갭+2%↑",
      "거래량3배", "거래량한산",
      "외인순매수", "기관순매수", "외인+기관", "수급강도",
      "영업흑자", "영업률5%", "순이익흑자",
      "코스닥", "코스피", "약세장"]


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
                량 = float(v.get("거래량") or 0)
            except (TypeError, ValueError):
                시총 = 대금 = 량 = 0.0
            하루[c] = (종, 시, 등, 시총, 대금, 량, str(v.get("시장") or ""))
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 등, 시총, 대금, 량, 시장) in 원[d].items():
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
            하루[c] = (수, 시 * 배, 시총, 대금, 량, 시장)
        out[d] = 하루
    return out


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본, 수급 = O._지수(), O._기본(), O._수급()
    분기 = O._분기재무()
    종계, 량계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            량계.setdefault(c, []).append(v[4])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    ixv, 앞x = [], None
    for d in 날:
        x = (지수.get(d) or {}).get("KOSPI") or 앞x
        if x:
            앞x = x
        ixv.append(x)
    약세 = {}
    for i, d in enumerate(날):
        약세[d] = (i >= 200 and ixv[i] and ixv[i - 200]
                   and ixv[i] / ixv[i - 200] - 1 <= -0.10)
    print(f"  거래일 {len(날):,} · 재무 {len(분기):,}종목", flush=True)

    def 재무값(code, d8, 항목):
        줄 = 분기.get(code)
        if not 줄:
            return None
        val = None
        for 적용, 값 in 줄:
            if 적용 <= d8:
                v = 값.get(항목)
                if v is not None:
                    val = v
            else:
                break
        return val

    관측 = []      # (해, 크기, 비트, 수익)
    비트 = {이름: 1 << i for i, 이름 in enumerate(축)}
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        fl = 수급.get(d1) or {}
        약 = 약세.get(d1)
        for code, v in 주가[d1].items():
            c1, _시, 시총, 대금, 량, 시장 = v
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
            나 = 주가[날[i + 1]].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝 or 나[1] <= 0:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            고250 = max(sq[k - 250:k + 1])
            평량 = st.mean(량계[code][k - 20:k]) or 1
            f = fl.get(code) or {}
            외 = f.get("외국인") or 0
            기 = f.get("기관") or 0
            갭 = (나[1] / c1 - 1) * 100
            최근 = (c1 / sq[k - 20] - 1) * 100 if k >= 20 and sq[k - 20] > 0 else 0
            영 = 재무값(code, d1, "영업이익")
            률 = 재무값(code, d1, "영업이익률")
            순 = 재무값(code, d1, "당기순이익")
            b = 0
            if 볼 <= -1.0:
                b |= 비트["볼하단"]
            if 볼 <= -2.0:
                b |= 비트["볼−2σ"]
            if rsi <= 30:
                b |= 비트["RSI≤30"]
            if k >= 60 and c1 <= min(sq[k - 59:k + 1]) * 1.001:
                b |= 비트["60일최저"]
            if 최근 <= -10:
                b |= 비트["20일−10%↓"]
            if 고250 and c1 >= 고250 * 0.999:
                b |= 비트["신고가"]
            if rsi >= 70:
                b |= 비트["RSI≥70"]
            if 볼 >= 1.0:
                b |= 비트["볼상단"]
            if c1 > s20:
                b |= 비트["20일선위"]
            if 최근 >= 10:
                b |= 비트["20일+10%↑"]
            if 갭 <= -2:
                b |= 비트["갭−2%↓"]
            elif 갭 < 2:
                b |= 비트["갭0~2%"]
            else:
                b |= 비트["갭+2%↑"]
            if 량 >= 평량 * 3:
                b |= 비트["거래량3배"]
            if 량 <= 평량 * 0.5:
                b |= 비트["거래량한산"]
            if 외 > 0:
                b |= 비트["외인순매수"]
            if 기 > 0:
                b |= 비트["기관순매수"]
            if 외 > 0 and 기 > 0:
                b |= 비트["외인+기관"]
            if 시총 > 0 and (외 + 기) * c1 / 시총 * 100 >= 0.5:
                b |= 비트["수급강도"]
            if 영 is not None and 영 > 0:
                b |= 비트["영업흑자"]
            if 률 is not None and 률 >= 5:
                b |= 비트["영업률5%"]
            if 순 is not None and 순 > 0:
                b |= 비트["순이익흑자"]
            if "KOSDAQ" in 시장.upper():
                b |= 비트["코스닥"]
            else:
                b |= 비트["코스피"]
            if 약:
                b |= 비트["약세장"]
            r = (끝[0] / 나[1] - 1) * 100 - _비용
            관측.append((d1[:4], _크기(시총), b, r))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 관측 {len(관측):,}", flush=True)
    print(f"  관측 {len(관측):,}건", flush=True)

    # 크기별로 나눠 담기 (반복 필터를 빠르게)
    크기별 = {g: [(y, b, r) for y, gg, b, r in 관측 if gg == g] for g, _, _ in 크기표}
    년수 = len(날) / 245
    결과 = []
    잰칸 = 0
    for 개수 in (1, 2, 3):
        for 조합 in itertools.combinations(축, 개수):
            마스크 = 0
            for c in 조합:
                마스크 |= 비트[c]
            for g, _, _ in 크기표:
                a = [(y, r) for y, b, r in 크기별[g] if (b & 마스크) == 마스크]
                if len(a) < 400:
                    continue
                잰칸 += 1
                수 = [r for _, r in a]
                승 = sum(1 for x in 수 if x > 0) / len(수) * 100
                해별 = {}
                for y, r in a:
                    해별.setdefault(y, []).append(r)
                전 = 플 = 0
                for y, arr in 해별.items():
                    if len(arr) < 15:
                        continue
                    전 += 1
                    플 += 1 if st.mean(arr) > 0 else 0
                통과 = 전 >= 10 and 플 / 전 >= 2 / 3
                결과.append((st.mean(수), 승, len(수), len(수) / 년수, 플, 전,
                             통과, " + ".join(조합), g, 개수))
        print(f"    조건 {개수}개 완료 · 누적 칸 {잰칸:,}", flush=True)

    print(f"\n  ══ 전수 탐색 결과 — 잰 칸 {잰칸:,}개 ══")
    for 개수 in (1, 2, 3):
        묶 = [x for x in 결과 if x[9] == 개수 and x[6]]
        묶.sort(reverse=True)
        print(f"\n  ── 조건 {개수}개 · **연도별 통과**한 것 중 상위 15 ──")
        print(f"    {'조합':<46}{'크기':<6}{'절대':>9}{'승률':>7}"
              f"{'연간':>8}{'연도별':>8}{'표본':>9}")
        for m, 승, n, 연, 플, 전, _t, 이름, g, _c in 묶[:15]:
            별 = "⭐" if (m > 0 and 승 >= 55) else ("○" if m > 0 else "❌")
            print(f"    {이름:<46}{g:<6}{m:>+8.2f}%{승:>6.0f}%"
                  f"{연:>7.0f}건{f'{플}/{전}':>8}{n:>9,}{별}")

    print(f"\n\n  ══ 🏆 **전체 상위 25** (연도별 통과 · 절대 + · 승률 55%↑) ══")
    산 = [x for x in 결과 if x[6] and x[0] > 0 and x[1] >= 55]
    산.sort(reverse=True)
    print(f"    {'조합':<46}{'크기':<6}{'절대':>9}{'승률':>7}"
          f"{'연간':>8}{'연도별':>8}{'표본':>9}")
    for m, 승, n, 연, 플, 전, _t, 이름, g, _c in 산[:25]:
        print(f"    {이름:<46}{g:<6}{m:>+8.2f}%{승:>6.0f}%"
              f"{연:>7.0f}건{f'{플}/{전}':>8}{n:>9,}")
    print(f"\n    통과 {len(산)}개 / 잰 칸 {잰칸:,}개 ({len(산)/max(1,잰칸)*100:.1f}%)")
    print("    ⚠️ 우연이면 문턱을 넘는 비율이 훨씬 낮아야 한다. 비율이 높으면 진짜 신호가 있다는 뜻")

    print("\n  읽는 법")
    print("    - **연도별 통과**가 1차 관문이다. 못 넘으면 특정 해에 몰린 것이다")
    print("    - 조건 개수가 늘수록 성적이 오르면 **조합이 값어치 있다**")
    print("    - ⚠️ 칸이 수천 개다. 우연히 좋은 게 반드시 섞인다 — 연도별로 거른 뒤에도 의심한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
