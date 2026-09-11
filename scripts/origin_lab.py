#!/usr/bin/env python3
r"""
origin_lab.py — **어느 출발점이 가장 좋은가** (2026-09-01 신설)

⚠️⚠️⚠️ **이 프로젝트의 전제를 처음으로 의심하는 시험이다.**
   사용자가 짚었다: *"우리 브리핑의 핵심이 공시인 건 주식을 잘 몰랐을 때 어쩌다 공시 기준으로
   종목을 발굴한 거지? 굳이 공시여야 할 이유는 없어!"*
   → **맞다.** 나는 「핵심은 공시」라고 여러 번 말했는데 그건 **현재 구현을 설명한 것**이지
      **그래야 할 근거를 댄 게 아니었다.**

⚠️ 그리고 이 편향이 시험 전체에 깔려 있었다:
```
공시 있는 종목만 보는 시험   entry · detail · cost · risk · exit · grade · gap_all  (7개)
전 종목을 보는 시험         omni · stability · reverse · combo                    (4개)
```

**여덟 가지 출발점을 같은 잣대로 나란히 잰다**
```
① 공시(호재)          지금 쓰는 것
② 공시(갭①④)         지금 쓰는 것 중 가장 좁힌 것
③ 수급 동반매수        외국인·기관 둘 다 순매수
④ 수급 강도           순매수금액 ÷ 시총 0.5% 이상
⑤ 52주 신고가         신고가 돌파
⑥ 거래량 3배          20일 평균 거래대금 대비 3배 이상
⑦ F-Score 6점 이상    재무 튼튼
⑧ 강한 시장 소속       코스피/코스닥 중 20일 상대강도가 높은 쪽에 속함
```

**세 가지를 같이 낸다 — 하나만 보면 오판한다**
```
성적     D+1 · D+5 · D+20 초과수익 (실제 지수 대비)
빈도     하루 평균 몇 종목이 뽑히나   ← 성적이 좋아도 하루 0.1건이면 못 쓴다
적중률   뽑은 것 중 그날 상위 5%에 든 비율  ← 무작위면 5%다. 5%보다 높아야 의미가 있다
```
⚠️ **셋은 서로 상충한다.** 좁힐수록 성적은 오르고 빈도·적중 표본은 준다.

⚠️ 매수 D+1 종가(look-ahead 회피) · 오염 종목(관리·SPAC·신규상장·리츠) 제외 · 표본 명시.
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = (1, 5, 20)
_MIN = 100

출발들 = [
    "1 공시(호재)",
    "2 공시(갭1+4)",
    "3 수급 동반매수",
    "4 수급강도 0.5%+",
    "5 52주 신고가",
    "6 거래량 3배+",
    "7 F-Score 6점+",
    "8 강한 시장 소속",
]


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O._주가()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)
    fsc = O._fscore()
    print(f"  준비 완료 · F-Score {len(fsc):,}종목", flush=True)

    # 종목별 시계열 (신고가·거래량 평균용)
    종가계, 대금계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종가계.setdefault(c, []).append(v[0])
            대금계.setdefault(c, []).append(v[2])
            자리.setdefault(c, {})[d] = len(종가계[c]) - 1

    통, 뽑힘, 적중 = {}, {}, {}
    날수 = 0

    def 담(k, v):
        s = 통.setdefault(k, [0.0, 0])
        s[0] += v
        s[1] += 1

    for i, d1 in enumerate(날):
        if i + 1 >= len(날):
            break
        a0 = 지수.get(날[i + 1])
        if not a0:
            continue
        날수 += 1
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}

        강한장 = None
        if i >= 20 and 지수.get(날[i - 20]):
            p, q = 지수[d1], 지수[날[i - 20]]
            강한장 = "KOSPI" if (p["KOSPI"] / q["KOSPI"]) >= (p["KOSDAQ"] / q["KOSDAQ"]) \
                else "KOSDAQ"

        오늘 = []
        for code, v1 in s1.items():
            c1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            더럽 = (("관리종목" in 부) or ("SPAC" in 부)
                    or (str(bb.get("상장일") or "") > "20240101")
                    or (bb.get("증권구분") not in (None, "주권")))
            if 더럽:
                continue
            매수v = 주가[날[i + 1]].get(code)
            if not 매수v:
                continue

            r = ds.get(code) or {}
            f = fl.get(code) or {}
            외 = f.get("외국인") or 0
            기 = f.get("기관") or 0
            k = (자리.get(code) or {}).get(d1)
            신고 = False
            거3 = False
            if k is not None and k >= 240:
                신고 = c1 >= max(종가계[code][k - 240:k + 1]) * 0.999
            if k is not None and k >= 20:
                평 = st.mean(대금계[code][k - 20:k]) or 1
                거3 = 대금 >= 평 * 3
            F = max([v for 적, v in (fsc.get(code) or {}).items() if 적 <= d1], default=None)
            강도 = ((외 + 기) * c1 / 시총 * 100) if 시총 > 0 else 0

            출발 = []
            if "호재" in r.get("성격", set()):
                출발.append(출발들[0])
                if r.get("분") is not None and r["분"] >= 930 and abs(등락) < 1:
                    출발.append(출발들[1])
            if 외 > 0 and 기 > 0:
                출발.append(출발들[2])
            if 강도 >= 0.5:
                출발.append(출발들[3])
            if 신고:
                출발.append(출발들[4])
            if 거3:
                출발.append(출발들[5])
            if F is not None and F >= 6:
                출발.append(출발들[6])
            if 강한장 and ((강한장 == "KOSDAQ") == bool(코스닥)):
                출발.append(출발들[7])

            오늘.append((code, 매수v[0], 코스닥, 출발))

        if len(오늘) < 100:
            continue

        # 그날 D+5 초과수익 상위 5% (적중률 기준)
        상위 = set()
        j5 = i + 1 + 5
        if j5 < len(날) and 지수.get(날[j5]):
            점 = []
            for code, 매수가, 코스닥, _ in 오늘:
                vv = 주가[날[j5]].get(code)
                if not vv:
                    continue
                장 = "KOSDAQ" if 코스닥 else "KOSPI"
                점.append(((vv[0] / 매수가 - 1) - (지수[날[j5]][장] / a0[장] - 1), code))
            점.sort()
            상위 = {c for _, c in 점[-max(1, len(점) // 20):]}

        for code, 매수가, 코스닥, 출발 in 오늘:
            if not 출발:
                continue
            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            for o in 출발:
                뽑힘[o] = 뽑힘.get(o, 0) + 1
                if code in 상위:
                    적중[o] = 적중.get(o, 0) + 1
            for h in _H:
                j = i + 1 + h
                if j >= len(날) or not 지수.get(날[j]):
                    continue
                vv = 주가[날[j]].get(code)
                if not vv:
                    continue
                시장 = 지수[날[j]][장] / a0[장] - 1
                초 = ((vv[0] / 매수가 - 1) - 시장) * 100
                국면 = "상승" if 시장 > 0 else "하락"
                for o in 출발:
                    담((o, "전체", h), 초)
                    담((o, 국면, h), 초)
        if i % 100 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print(f"\n  거래일 {날수}일 · 매수 D+1 종가 · 오염 종목 제외\n")
    print(f"  {'출발점':<18}{'국면':<5}{'D+1':>14}{'D+5':>14}{'D+20':>14}"
          f"{'하루뽑힘':>10}{'상위5% 적중':>13}")
    for o in 출발들:
        빈 = 뽑힘.get(o, 0) / max(1, 날수)
        적 = (적중.get(o, 0) / max(1, 뽑힘.get(o, 1))) * 100
        for 국면 in ("전체", "상승", "하락"):
            칸 = []
            for h in _H:
                s = 통.get((o, 국면, h))
                칸.append(f"{s[0] / s[1]:+.2f}({s[1] // 1000}k)"
                          if s and s[1] >= _MIN else "-")
            if all(c == "-" for c in 칸):
                continue
            꼬리 = f"{빈:>10.1f}{적:>12.1f}%" if 국면 == "전체" else ""
            print(f"  {o if 국면 == '전체' else '':<18}{국면:<5}"
                  + "".join(f"{c:>14}" for c in 칸) + 꼬리)

    print("\n  주의: 셋을 같이 봐야 한다.")
    print("    - 성적이 좋아도 하루 0.1종목이면 못 쓴다(자본이 논다)")
    print("    - 성적이 좋아도 상위5% 적중이 낮으면 대부분을 놓치는 것이다")
    print("    - 상위5% 적중은 무작위로 뽑으면 5%다. 5%보다 높아야 의미가 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
