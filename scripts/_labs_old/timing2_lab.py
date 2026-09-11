#!/usr/bin/env python3
r"""
timing2_lab.py — **아침에 언제 사야 하나 (일봉으로 근사)** (2026-09-02 · 41차)

⚠️⚠️ **사용자 취지.**
   *"장기 관점에서 매수하는 게 좋으니 초반 과열 상태가 가라앉고 10시쯤 일부 항목을 체크한 뒤
   매수하라 — 요런 게 나오면 좋지"*
   ⚠️ **분봉이 없어 10시 가격을 모른다.** 일봉(시가·고가·저가·종가)으로 근사한다.

## 39차가 깔아준 배경
```
16.7년 · 582만 관측치
  갭(전일종가→시가)  **+0.1356%/일** → 연 +33.2%
  장중(시가→종가)    **−0.0537%/일** → 연 −13.2%
⇒ **한국 주식은 밤사이 오르고 장중 빠진다.** 09:00~09:30 매수는 상승을 놓친 뒤다
⇒ 그렇다면 **장중에 더 기다렸다 사면** 더 싸게 살 수 있나? 그걸 여기서 잰다
```

## 재는 것 — 매수 방식 여섯
```
A 신호일 종가          그날 장 마감 직전에 산다 (지금까지 쓴 방식)
B 다음날 시가          09:00 개장가에 산다
C 다음날 시가 −1% 눌림   그날 **저가**가 거기까지 왔으면 체결로 본다
D 다음날 시가 −3% 눌림   (더 깊은 눌림 — 안 오면 못 산다)
E 다음날 종가          장 마감까지 기다린다  ← **「과열이 가라앉은 뒤」의 근사**
F 다음날 시가 +2% 돌파   그날 **고가**가 거기까지 갔으면 체결로 본다 (추격매수)
```
⚠️ C·D·F는 **못 사는 날이 생긴다.** 체결률을 같이 찍는다 — 체결률이 낮으면 실전에서 못 쓴다.
⚠️ 매도는 전부 **같은 시점**(D+20 종가)으로 고정한다. 매수 시점만 비교하려는 것이다.
⚠️ 갭 크기별로도 나눈다 — **갭 상승으로 출발한 종목은 다른가**.
⚠️ 판정은 절대 수익 + 승률, 그리고 **코스피를 뺀 값**도 나란히(38차 교훈).
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
_보유 = 20
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def _주가():
    """{날: {코드: (수정종가, 수정시가, 수정고가, 수정저가, 시총, 대금)}}"""
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
    지수, 기본 = O._지수(), O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    ixv, 앞x = [], None
    for d in 날:
        x = (지수.get(d) or {}).get("KOSPI") or 앞x
        if x:
            앞x = x
        ixv.append(x)
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    # 사건: 신고가 첫날 / 볼린저 하단 이탈 (16.7년 · 표본 큰 것만)
    사건 = {}
    앞상태 = {}
    for i, d1 in enumerate(날):
        if i < 250 or i + 2 + _보유 >= len(날):
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
            상태 = (신, 볼하)
            오늘[code] = 상태
            앞 = 앞상태.get(code)
            if 앞 is None:
                continue
            g = _크기(시총)
            if 신 and not 앞[0]:
                사건.setdefault("신고가 첫날", []).append((i, code, g))
            if 볼하 and not 앞[1]:
                사건.setdefault("볼린저 하단 이탈", []).append((i, code, g))
        앞상태 = 오늘
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일", flush=True)
    print("  " + " · ".join(f"{k} {len(v):,}건" for k, v in 사건.items()), flush=True)

    방식들 = [("A 신호일 종가", "종가0"), ("B 다음날 시가", "시가1"),
              ("C 시가 −1% 눌림", "눌림1"), ("D 시가 −3% 눌림", "눌림3"),
              ("E 다음날 종가", "종가1"), ("F 시가 +2% 돌파", "돌파2")]

    def 성과(목록, 방식):
        """(수익들, 코스피뺀것들, 체결률)"""
        절, 대, 시도, 체결 = [], [], 0, 0
        for (i, code, g) in 목록:
            시도 += 1
            나 = 주가[날[i + 1]].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝:
                continue
            _종1, 시1, 고1, 저1, _, _ = 나
            if 방식 == "종가0":
                매수 = 주가[날[i]][code][0]
                기준i = i
            elif 방식 == "시가1":
                매수, 기준i = 시1, i + 1
            elif 방식 == "종가1":
                매수, 기준i = 나[0], i + 1
            elif 방식 == "눌림1":
                목표 = 시1 * 0.99
                if 저1 > 목표:
                    continue          # 그만큼 안 내려왔다 = 못 샀다
                매수, 기준i = 목표, i + 1
            elif 방식 == "눌림3":
                목표 = 시1 * 0.97
                if 저1 > 목표:
                    continue
                매수, 기준i = 목표, i + 1
            else:                      # 돌파2
                목표 = 시1 * 1.02
                if 고1 < 목표:
                    continue
                매수, 기준i = 목표, i + 1
            if 매수 <= 0:
                continue
            체결 += 1
            r = (끝[0] / 매수 - 1) * 100 - _비용
            절.append(r)
            if ixv[기준i] and ixv[i + 1 + _보유]:
                대.append(r - (ixv[i + 1 + _보유] / ixv[기준i] - 1) * 100)
        return 절, 대, (체결 / 시도 * 100 if 시도 else 0)

    print(f"\n  ══ 매수 시점 비교 (매도는 전부 D+{_보유} 종가로 고정) ══")
    print("     ⚠️ 체결률이 낮으면 실전에서 못 쓴다. C·D·F는 못 사는 날이 생긴다")
    for 이름, 목록전 in 사건.items():
        for g, _, _ in 크기표:
            목록 = [x for x in 목록전 if x[2] == g]
            if len(목록) < 1000:
                continue
            print(f"\n  ── {이름} · {g} (사건 {len(목록):,}건) ──")
            print(f"    {'매수 방식':<16}{'절대':>9}{'코스피뺀것':>11}{'승률':>8}"
                  f"{'체결률':>8}{'표본':>9}")
            for 라벨, 키 in 방식들:
                절, 대, 체 = 성과(목록, 키)
                if len(절) < 300:
                    continue
                승 = sum(1 for x in 절 if x > 0) / len(절) * 100
                md = st.mean(대) if 대 else 0
                별 = "⭐" if (md > 0 and 승 >= 50) else ("  " if md > 0 else "❌")
                print(f"    {라벨:<16}{st.mean(절):>+8.2f}%{md:>+10.2f}%"
                      f"{승:>7.1f}%{체:>7.0f}%{len(절):>9,}{별}")

    # 갭 크기별
    print(f"\n\n  ══ **갭 상승으로 출발한 종목은 다른가** (다음날 시가 매수 · D+{_보유}) ══")
    print("     ⚠️ 갭 = 신호일 종가 → 다음날 시가")
    for 이름, 목록전 in 사건.items():
        print(f"\n  ── {이름} ──")
        print(f"    {'갭 구간':<16}" + "".join(f"{g:>22}" for g, _, _ in 크기표))
        칸들 = [("갭 −2%↓", -99, -2), ("갭 −2~0%", -2, 0), ("갭 0~2%", 0, 2),
                ("갭 2~5%", 2, 5), ("갭 5%↑", 5, 99)]
        for 라벨, lo, hi in 칸들:
            줄 = []
            for g, _, _ in 크기표:
                절, 대 = [], []
                for (i, code, gg) in 목록전:
                    if gg != g:
                        continue
                    앞 = 주가[날[i]].get(code)
                    나 = 주가[날[i + 1]].get(code)
                    끝 = 주가[날[i + 1 + _보유]].get(code)
                    if not 앞 or not 나 or not 끝 or 앞[0] <= 0:
                        continue
                    갭 = (나[1] / 앞[0] - 1) * 100
                    if not (lo <= 갭 < hi):
                        continue
                    r = (끝[0] / 나[1] - 1) * 100 - _비용
                    절.append(r)
                    if ixv[i + 1] and ixv[i + 1 + _보유]:
                        대.append(r - (ixv[i + 1 + _보유] / ixv[i + 1] - 1) * 100)
                if len(절) < 300:
                    줄.append("-")
                    continue
                승 = sum(1 for x in 절 if x > 0) / len(절) * 100
                md = st.mean(대) if 대 else 0
                줄.append(f"{md:+.2f}({승:.0f}%) {len(절)//1000}k")
            print(f"    {라벨:<16}" + "".join(f"{x:>22}" for x in 줄))

    print("\n  읽는 법")
    print("    - **A(신호일 종가)가 B(다음날 시가)보다 나으면** 39차와 일치한다")
    print("      (밤사이 오르니 전날 종가에 사는 게 유리)")
    print("    - **E(다음날 종가)가 B보다 나으면** 「과열이 가라앉길 기다려라」가 맞다")
    print("    - C·D는 눌림을 기다리는 것이다. **체결률과 같이 봐야 한다** —")
    print("      성적이 좋아도 체결률이 30%면 열 번 중 세 번만 산다")
    print("    - 갭 표에서 **갭이 클수록 나빠지면** 「갭 상승 출발은 쫓지 마라」가 된다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
