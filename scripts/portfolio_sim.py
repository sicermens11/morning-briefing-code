#!/usr/bin/env python3
r"""
portfolio_sim.py — **실제 자본을 굴려본다** (2026-09-02 · 2차)

⚠️⚠️ **지금까지는 「거래 하나의 평균 초과수익」만 봤다.** 그건 실제 성적이 아니다.
```
안 본 것   자본이 얼마나 노는가 · 동시에 몇 종목을 들 수 있나
          비용·세금을 매 거래마다 뺐을 때 남는가 · 최대 낙폭은 얼마인가
          시장을 이겼나 (인덱스 대비)
```
**이 스크립트는 648일을 하루씩 굴리며 계좌 잔고를 추적한다.**

**규칙 (1차 실험에서 살아남은 것만)**
```
매수 신호   전략마다 다름 (아래 전략표)
매수 시점   신호 다음 거래일 **종가**  ← look-ahead 회피 (D+1 시가는 데이터에 없음)
매도       D+5 종가 · 또는 손절 −5%(장중 저가 기준) 먼저 닿으면 그때
종목당 비중  자본 ÷ 최대보유종목수 (기본 5)
비용       왕복 0.26% (세금 0.18 + 수수료 0.03 + 슬리피지 0.05⚠️가정)
```
⚠️ **손절은 저가 기준이라 낙관적이다.** 갭하락하면 실제로는 더 나쁘다.
⚠️ **체결은 100% 가정한다.** 거래대금 1억↑ 종목만 담으므로 소액에선 무리 없는 가정이다.

**비교 대상**: 같은 기간 **코스피 그냥 보유**(인덱스). 그걸 못 이기면 할 이유가 없다.
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.0026          # 왕복
_보유일 = 5
_손절 = -0.05
_최대종목 = 5


def _주가full():
    import glob
    import io
    import json
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"]); 저 = float(v["저가"])
                if 종 <= 0:
                    continue
                하루[c] = (종, 저, float(v.get("시총") or 0),
                           float(v.get("거래대금") or 0), float(v.get("등락률") or 0),
                           1 if "KOSDAQ" in str(v.get("시장", "")).upper() else 0)
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가full()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)
    fsc = O._fscore()

    종가계, 대금계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종가계.setdefault(c, []).append(v[0])
            대금계.setdefault(c, []).append(v[2])
            자리.setdefault(c, {})[d] = len(종가계[c]) - 1
    print(f"  준비 완료 · 거래일 {len(날)}", flush=True)

    # 날짜별 신호 미리 계산
    신호일 = {}
    for i, d1 in enumerate(날):
        if i < 21:
            continue
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}
        창 = [지수[d]["KOSPI"] for d in 날[i - 20:i + 1] if 지수.get(d)]
        조정 = len(창) >= 15 and 지수.get(d1) and 지수[d1]["KOSPI"] < st.mean(창)
        하루 = {}
        for code, v1 in s1.items():
            c1, 저, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (str(bb.get("상장일") or "") > "20240101")
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            rr = ds.get(code) or {}
            f = fl.get(code) or {}
            외 = f.get("외국인") or 0
            기 = f.get("기관") or 0
            k = (자리.get(code) or {}).get(d1)
            신고 = 거3 = False
            if k is not None and k >= 240:
                신고 = c1 >= max(종가계[code][k - 240:k + 1]) * 0.999
            if k is not None and k >= 20:
                평 = st.mean(대금계[code][k - 20:k]) or 1
                거3 = 대금 >= 평 * 3
            강도 = ((외 + 기) * c1 / 시총 * 100) if 시총 > 0 else 0
            호재 = "호재" in rr.get("성격", set())
            장후 = rr.get("분") is not None and rr["분"] >= 930
            하루[code] = {"호재": 호재, "장후": 장후, "무반응": abs(등락) < 1,
                          "강도": 강도, "신고": 신고, "거3": 거3, "조정": 조정,
                          "대형": 시총 >= 1e12, "대금": 대금}
        신호일[d1] = 하루

    # ⚠️ 3차(momentum_lab) 결과를 반영했다:
    #    ① 모멘텀은 **대형주에서만** 작동한다 (소형주 D+60 −1.58)
    #    ② 모멘텀에 **손절은 독이다** (없음 D+60 +1.54 vs −5% −2.39)
    #    ③ **길게 들어야 한다** (D+5 +1.31 → D+20 +4.24)
    #    그래서 전략마다 (보유일, 손절)을 따로 준다.
    전략 = [
        ("A 갭1 (호재+장후)", lambda x: x["호재"] and x["장후"]),
        ("B 갭1+4 (기존규칙)", lambda x: x["호재"] and x["장후"] and x["무반응"]),
        ("C 갭1 + 20일선아래", lambda x: x["호재"] and x["장후"] and x["조정"]),
        ("D 수급강도 0.5%+", lambda x: x["강도"] >= 0.5),
        ("E 수급강도 + 20일선", lambda x: x["강도"] >= 0.5 and x["조정"]),
        ("F 52주 신고가", lambda x: x["신고"]),
        ("G 신고가 + 20일선", lambda x: x["신고"] and x["조정"]),
        ("H 호재 + 20일선아래", lambda x: x["호재"] and x["조정"]),
        ("I 대형주+신고가 D20 무손절", lambda x: x["신고"] and x["대형"], 20, None),
        ("J 대형주+신고가 D60 무손절", lambda x: x["신고"] and x["대형"], 60, None),
        ("K 대형주+신고가 D20 -10%", lambda x: x["신고"] and x["대형"], 20, -0.10),
        ("L 신고가전체 D20 무손절", lambda x: x["신고"], 20, None),
        ("M 대형주+신고가 D20 10종목", lambda x: x["신고"] and x["대형"], 20, None, 10),
    ]

    print("\n  규칙: 매수 신호 다음날 종가 · D+5 종가 매도 · 손절 -5% · "
          f"최대 {_최대종목}종목 · 왕복비용 {_비용*100:.2f}%\n")
    print(f"  {'전략':<22}{'최종배수':>9}{'연환산':>9}{'거래수':>8}{'승률':>7}"
          f"{'최대낙폭':>9}{'투입일비율':>10}")

    결과 = []
    for 항 in 전략:
        이름, fn = 항[0], 항[1]
        보유일 = 항[2] if len(항) > 2 else _보유일
        컷비 = 항[3] if len(항) > 3 else _손절
        최대 = 항[4] if len(항) > 4 else _최대종목
        잔고 = 1.0
        보유 = []          # [(청산일idx, 청산방식, 코드, 매수가, 몫, 손절선)]
        곡선 = [1.0]
        이긴 = 진 = 0
        for i, d1 in enumerate(날):
            # ── 청산 ──
            남 = []
            for (끝i, code, 매수가, 몫, 컷, 산i) in 보유:
                v = 주가[날[i]].get(code)
                팔 = None
                # ⚠️⚠️ **매수 당일은 손절 검사에서 뺀다.** 매수가는 그날 **종가**인데
                #    그날 장중 저가는 **사기 전에 이미 지나간 값**이다.
                #    이걸 안 빼면 변동 5% 넘는 종목이 사자마자 손절 처리돼 승률이 박살난다.
                if v and i > 산i and 컷 is not None and v[1] <= 컷:
                    팔 = 컷
                elif i >= 끝i:
                    팔 = v[0] if v else 매수가
                if 팔 is None:
                    남.append((끝i, code, 매수가, 몫, 컷, 산i))
                    continue
                수익 = (팔 / 매수가 - 1) - _비용
                잔고 += 몫 * 수익
                이긴 += 1 if 수익 > 0 else 0
                진 += 1 if 수익 <= 0 else 0
            보유 = 남
            # ── 매수 ──
            자리수 = 최대 - len(보유)
            if 자리수 > 0 and i + 1 < len(날):
                후보 = [(v["대금"], c) for c, v in (신호일.get(d1) or {}).items() if fn(v)]
                후보.sort(reverse=True)          # 거래대금 큰 것부터
                산것 = 0
                for _, code in 후보:
                    if 산것 >= 자리수:
                        break
                    v2 = 주가[날[i + 1]].get(code)
                    if not v2:
                        continue
                    몫 = 잔고 / 최대
                    보유.append((i + 1 + 보유일, code, v2[0], 몫,
                                 (v2[0] * (1 + 컷비)) if 컷비 is not None else None, i + 1))
                    산것 += 1
            곡선.append(잔고)
        # 성과
        최고 = 곡선[0]
        낙폭 = 0.0
        for x in 곡선:
            최고 = max(최고, x)
            낙폭 = min(낙폭, x / 최고 - 1)
        년 = len(날) / 245
        연 = (잔고 ** (1 / 년) - 1) * 100 if 잔고 > 0 else -100
        총 = 이긴 + 진
        투입 = sum(1 for x in 곡선 if x != 1.0) / max(1, len(곡선))
        결과.append((이름, 잔고, 연, 총, 이긴 / max(1, 총) * 100, 낙폭 * 100))
        print(f"  {이름:<22}{잔고:>9.3f}{연:>8.1f}%{총:>8,}{이긴/max(1,총)*100:>6.0f}%"
              f"{낙폭*100:>8.1f}%{투입*100:>9.0f}%")

    # 인덱스 비교
    있는날 = [d for d in 날 if 지수.get(d)]
    a, b = 지수[있는날[0]], 지수[있는날[-1]]
    년 = len(날) / 245
    for 이름, k in (("* 코스피 그냥 보유", "KOSPI"), ("* 코스닥 그냥 보유", "KOSDAQ")):
        배 = b[k] / a[k]
        print(f"  {이름:<22}{배:>9.3f}{(배 ** (1 / 년) - 1) * 100:>8.1f}%")

    print("\n  읽는 법")
    print("    - '최종배수' 1.0이면 본전. 코스피 배수를 못 넘으면 인덱스가 낫다")
    print("    - '최대낙폭'은 계좌가 고점 대비 얼마나 줄었나. 이게 크면 못 버틴다")
    print("    - '투입일비율'은 자본이 일하고 있던 날의 비율")
    print("    - 손절은 저가 기준이라 낙관적이다. 갭하락하면 실제로는 더 나쁘다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
