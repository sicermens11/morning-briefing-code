#!/usr/bin/env python3
r"""strategy_duel.py — **우리 조합 vs 데이터가 말하는 조합** (2026-09-01 신설)

⚠️⚠️ 지금까지 지표를 **하나씩** 쟀다. 실제 전략은 **조합**이다. 여기서는 조합끼리 겨룬다.

⚠️ **못 재는 것을 먼저 밝힌다.**
   - **갭②(미보도)**: 전 종목 과거 뉴스가 없다. 잴 방법이 없다.
   - **갭③(수급)**: KRX에 투자자별 매매동향 API가 **없다**(404 확인). 전 종목 소급 불가.
   ⇒ 여기서 재는 「우리 조합」은 **갭①+갭④ 근사**다. 갭②③이 결과를 뒤집을 수 있으므로
     **"갭 전략이 졌다"고 결론내면 안 된다.**

⚠️ 네 겹 규칙(초과수익률 · 상승/하락 · 표본 · 여러 지평)은 그대로다.

쓰는 법: python scripts\strategy_duel.py
"""
import datetime as dt
import glob
import io
import json
import os
import re
import statistics as st
import sys

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_MIN_MC, _MIN_AMT = 5e10, 1e8
_H = (1, 5, 20)
_호재 = ("단일판매", "공급계약", "수주", "자기주식취득", "자기주식소각", "무상증자",
         "현금ㆍ현물배당", "영업양수", "타법인주식및출자증권취득")
_악재 = ("유상증자", "전환사채", "신주인수권부사채", "교환사채", "거래정지", "상장폐지",
         "소송등의제기", "감자", "자기주식처분", "관리종목", "횡령", "배임")


def _성격(n):
    n = re.sub(r"\[[^\]]*\]", "", n or "")
    if any(k in n for k in _악재):
        return "악재"
    return "호재" if any(k in n for k in _호재) else "중립"


def _날(s):
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))


def 만들기():
    fs = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    일 = []
    for f in fs:
        d8 = os.path.basename(f)[:8]
        with io.open(f, encoding="utf-8-sig") as fp:
            시세 = json.load(fp).get("종목") or {}
        정보 = {}
        p = os.path.join(_DATA, "dart-daily", f"{d8}.json")
        if os.path.exists(p):
            with io.open(p, encoding="utf-8-sig") as fp:
                g = json.load(fp)
            번호 = []
            for x in (g.get("챙길공시") or []):
                code, 번 = x.get("종목코드"), (x.get("접수번호") or "")
                if not code or len(번) < 14:
                    continue
                순 = int(번[8:])
                번호.append(순)
                r = 정보.setdefault(code, {"성격": set(), "순번": []})
                r["성격"].add(_성격(x.get("공시명")))
                r["순번"].append(순)
            중 = st.median(번호) if 번호 else 0
            for r in 정보.values():
                r["늦음"] = max(r["순번"]) > 중
        일.append((d8, 시세, 정보))
    return 일


def 행만들기(일):
    계 = {}
    for idx, (_, s, _i) in enumerate(일):
        for code, v in s.items():
            try:
                c = float(v["종가"]); q = float(v["거래량"])
            except (TypeError, ValueError, KeyError):
                continue
            if c > 0:
                계.setdefault(code, []).append((idx, c, q))
    위치 = {c: {i: j for j, (i, _, _) in enumerate(v)} for c, v in 계.items()}
    행 = []
    for i, (d1, s1, 정보) in enumerate(일):
        시장h = {}
        for h in _H:
            j = i + h
            if j >= len(일) or (_날(일[j][0]) - _날(d1)).days > h * 2 + 4:
                continue
            s2 = 일[j][1]
            m = [float(x["종가"]) / float(s1[k]["종가"]) - 1 for k, x in s2.items()
                 if k in s1 and float(s1[k].get("시총") or 0) >= _MIN_MC
                 and float(s1[k].get("종가") or 0) > 0]
            if m:
                시장h[h] = (s2, st.mean(m))
        if not 시장h:
            continue
        for code, v1 in s1.items():
            try:
                c1 = float(v1["종가"]); 시총 = float(v1["시총"]); 대금 = float(v1["거래대금"])
                등락 = float(v1["등락률"]); 거래량 = float(v1["거래량"])
            except (TypeError, ValueError, KeyError):
                continue
            if c1 <= 0 or 시총 < _MIN_MC or 대금 < _MIN_AMT:
                continue
            j0 = 위치.get(code, {}).get(i)
            if j0 is None or j0 < 60:
                continue
            계열 = 계[code]
            종 = [c for _, c, _ in 계열[max(0, j0 - 120):j0 + 1]]
            량 = [q for _, _, q in 계열[max(0, j0 - 20):j0 + 1]]
            평량 = st.mean(량[-21:-1]) if len(량) >= 21 else 0
            r = 정보.get(code) or {}
            성 = r.get("성격", set())
            f = {"등락": 등락, "시총": 시총,
                 "무반응": abs(등락) < 1,
                 "신고가": c1 >= max(종[-61:]) if len(종) >= 61 else False,
                 "20일선위": c1 > st.mean(종[-21:-1]) if len(종) >= 21 else False,
                 "거래량배": (거래량 / 평량) if 평량 > 0 else None,
                 "회전율": 거래량 / (시총 / c1) * 100 if c1 > 0 else 0,
                 "호재": "호재" in 성, "악재": "악재" in 성,
                 "늦음": r.get("늦음")}
            # MACD (12·26 EMA 차 vs 9 EMA)
            if len(종) >= 35:
                def ema(v, n):
                    k = 2 / (n + 1); e = v[0]
                    for x in v[1:]:
                        e = x * k + e * (1 - k)
                    return e
                macd = ema(종[-26:], 12) - ema(종[-26:], 26)
                f["MACD양"] = macd > 0
            for h, (s2, 시장평) in 시장h.items():
                v2 = s2.get(code)
                if not v2:
                    continue
                try:
                    c2 = float(v2["종가"])
                except (TypeError, ValueError, KeyError):
                    continue
                g = dict(f)
                g["h"] = h
                g["초과"] = ((c2 / c1 - 1) - 시장평) * 100
                g["시장"] = 시장평
                행.append(g)
    return 행


전략 = [
    # ⚠️ 갭②(미보도)는 전 종목 과거 뉴스가 없어 직접 못 잰다.
    #    **「공시가 났는데 거래량이 안 늘었다」**를 대리지표로 쓴다 — 시장이 아직 모른다는 뜻.
    ("[갭②근사] 호재+거래량 1배↓", lambda x: x["호재"] and 0 < (x["거래량배"] or 9) <= 1),
    ("[갭②반대] 호재+거래량 3배↑", lambda x: x["호재"] and (x["거래량배"] or 0) >= 3),
    ("[갭①②④] 호재+한산+무반응", lambda x: x["호재"] and 0 < (x["거래량배"] or 9) <= 1 and x["무반응"]),
    ("[최선?] 소형주뺀 호재+한산", lambda x: x["호재"] and x["시총"] >= 3e11 and 0 < (x["거래량배"] or 9) <= 1),
    ("[우리] 호재+늦게+무반응", lambda x: x["호재"] and x["늦음"] is True and x["무반응"]),
    ("[우리] 호재+무반응", lambda x: x["호재"] and x["무반응"]),
    ("[우리] 호재만", lambda x: x["호재"] and not x["악재"]),
    ("[대안] 호재+신고가", lambda x: x["호재"] and x["신고가"]),
    ("[대안] 호재+20일선위", lambda x: x["호재"] and x["20일선위"]),
    ("[대안] 호재+거래량2배", lambda x: x["호재"] and (x["거래량배"] or 0) >= 2),
    ("[대안] 신고가+거래량2배", lambda x: x["신고가"] and (x["거래량배"] or 0) >= 2),
    ("[대안] 신고가+20일선위", lambda x: x["신고가"] and x["20일선위"]),
    ("[단독] MACD 양", lambda x: x.get("MACD양") is True),
    ("[단독] 회전율 5%↑", lambda x: x["회전율"] >= 5),
    ("[단독] 회전율 0.5%↓", lambda x: x["회전율"] <= 0.5),
    ("[제외] 소형주 뺀 호재", lambda x: x["호재"] and x["시총"] >= 3e11),
]


def main():
    일 = 만들기()
    행 = 행만들기(일)
    print(f"  거래일 {len(일)}일 · 관측 {len(행):,}건")
    for 라벨, 필터 in [("전체", lambda x: True),
                       ("시장 상승", lambda x: x["시장"] > 0),
                       ("시장 하락", lambda x: x["시장"] <= 0)]:
        print(f"\n  [{라벨}]")
        print(f"    {'전략':26s}" + "".join(f"{'D+'+str(h):>17s}" for h in _H))
        for 이름, c in 전략:
            줄 = f"    {이름:26s}"
            for h in _H:
                부분 = [x for x in 행 if x["h"] == h and 필터(x)]
                a = [x["초과"] for x in 부분 if c(x)]
                b = [x["초과"] for x in 부분 if not c(x)]
                if len(a) < 150 or len(b) < 150:
                    줄 += f"{'—':>17s}"
                else:
                    줄 += f"{f'{st.mean(a)-st.mean(b):+.3f} (n={len(a)})':>17s}"
            print(줄)
    return 0


if __name__ == "__main__":
    sys.exit(main())
