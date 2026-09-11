#!/usr/bin/env python3
r"""signal_lab.py — **신호를 한꺼번에 검정한다** (2026-09-01 신설)

⚠️⚠️ **네 겹 규칙을 지킨다** (2026-09-01에 결론이 다섯 번 뒤집히고서 정했다):
   ① **초과수익률**로 — 절대 수익률은 기간 효과에 속는다
   ② **시장 상승일/하락일**로 갈라서 — 안 그러면 「베타」를 「신호」로 착각한다
   ③ **표본을 늘려 재확인** — 24k→141k→231k→644k에서 매번 결론이 바뀌었다
   ④ **여러 지평(D+1·D+5·D+20)**으로 — D+1만 보면 반대 결론이 나온다
      (공시는 D+1 −0.162인데 D+20 +0.241로 뒤집힌다)

⚠️ 여기서 나오는 것은 **"이 지표가 예측력이 있나"**까지다.
   **"우리 등급이 작동하나"는 전 종목으로 못 답한다** — 우리 픽 데이터가 필요하다.

⚠️ 걸러내는 것: 시총 500억 미만·거래대금 1억 미만(호가가 얇아 수익률이 튄다).

쓰는 법:
    python scripts\signal_lab.py
    python scripts\signal_lab.py --from 20250101
"""
import datetime as dt
import glob
import io
import json
import os
import statistics as st
import sys

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_MIN_MC, _MIN_AMT = 5e10, 1e8
_H = (1, 5, 20)


def _날(s):
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))


def 만들기(부터=None):
    fs = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    일 = []
    for f in fs:
        d8 = os.path.basename(f)[:8]
        if 부터 and d8 < 부터:
            continue
        with io.open(f, encoding="utf-8-sig") as fp:
            일.append((d8, json.load(fp).get("종목") or {}))
    # 종목별 종가·거래량 계열 (날짜 인덱스와 나란히)
    계 = {}
    for idx, (_, s) in enumerate(일):
        for code, v in s.items():
            try:
                c = float(v["종가"]); q = float(v["거래량"])
            except (TypeError, ValueError, KeyError):
                continue
            if c > 0:
                계.setdefault(code, []).append((idx, c, q))
    # 시장 일별 평균 등락(국면 판정용)
    시장일 = []
    for idx, (_, s) in enumerate(일):
        r = [float(v["등락률"]) for v in s.values()
             if v.get("등락률") is not None and float(v.get("시총") or 0) >= _MIN_MC]
        시장일.append(st.mean(r) if r else 0.0)
    # 코스피 대용: 시장 20일 평균 위/아래
    누적 = []
    x = 100.0
    for r in 시장일:
        x *= (1 + r / 100)
        누적.append(x)
    국면 = []
    for i in range(len(누적)):
        if i < 20:
            국면.append(None)
        else:
            국면.append(누적[i] > st.mean(누적[i - 20:i]))
    return 일, 계, 시장일, 국면


def 행만들기(일, 계, 시장일, 국면):
    위치 = {code: {i: (j, c, q) for j, (i, c, q) in enumerate(v)} for code, v in 계.items()}
    행 = []
    for i, (d1, s1) in enumerate(일):
        # 지평별 시장 평균 (한 번만 계산)
        시장h = {}
        for h in _H:
            j = i + h
            if j >= len(일):
                continue
            if (_날(일[j][0]) - _날(d1)).days > h * 2 + 4:
                continue
            s2 = 일[j][1]
            m = [float(x["종가"]) / float(s1[k]["종가"]) - 1
                 for k, x in s2.items()
                 if k in s1 and float(s1[k].get("시총") or 0) >= _MIN_MC
                 and float(s1[k].get("종가") or 0) > 0]
            if m:
                시장h[h] = (s2, st.mean(m))
        if not 시장h:
            continue
        for code, v1 in s1.items():
            try:
                c1 = float(v1["종가"]); 시총 = float(v1["시총"]); 대금 = float(v1["거래대금"])
                등락 = float(v1["등락률"]); 고 = float(v1["고가"]); 저 = float(v1["저가"])
                거래량 = float(v1["거래량"])
            except (TypeError, ValueError, KeyError):
                continue
            if c1 <= 0 or 시총 < _MIN_MC or 대금 < _MIN_AMT:
                continue
            좌 = 위치.get(code, {}).get(i)
            if not 좌:
                continue
            j0 = 좌[0]
            계열 = 계[code]
            if j0 < 60:
                continue
            종가들 = [c for _, c, _ in 계열[max(0, j0 - 120):j0 + 1]]
            거래량들 = [q for _, _, q in 계열[max(0, j0 - 20):j0 + 1]]
            f = {"등락": 등락, "변동": (고 - 저) / c1 * 100, "시총": 시총,
                 "국면": 국면[i], "요일": _날(d1).weekday()}
            n = len(종가들)
            if n >= 21:
                f["20일선위"] = c1 > st.mean(종가들[-21:-1])
            if n >= 61:
                f["신고가60"] = c1 >= max(종가들[-61:])
                f["신저가60"] = c1 <= min(종가들[-61:])
            if len(거래량들) >= 21 and st.mean(거래량들[-21:-1]) > 0:
                f["거래량배수"] = 거래량 / st.mean(거래량들[-21:-1])
            # 연속 상승/하락
            연 = 0
            for t in range(len(종가들) - 1, 0, -1):
                if 종가들[t] > 종가들[t - 1]:
                    if 연 < 0: break
                    연 += 1
                elif 종가들[t] < 종가들[t - 1]:
                    if 연 > 0: break
                    연 -= 1
                else:
                    break
                if abs(연) >= 6: break
            f["연속"] = 연
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


조건들 = [
    ("20일선 위", lambda x: x.get("20일선위") is True),
    ("60일 신고가", lambda x: x.get("신고가60") is True),
    ("60일 신저가", lambda x: x.get("신저가60") is True),
    ("거래량 3배↑", lambda x: (x.get("거래량배수") or 0) >= 3),
    ("거래량 0.5배↓(한산)", lambda x: 0 < (x.get("거래량배수") or 9) <= 0.5),
    ("3일 연속 상승", lambda x: x.get("연속", 0) >= 3),
    ("3일 연속 하락", lambda x: x.get("연속", 0) <= -3),
    ("시장 20일선 위(국면)", lambda x: x.get("국면") is True),
    ("월요일", lambda x: x.get("요일") == 0),
    ("금요일", lambda x: x.get("요일") == 4),
    ("신고가 + 거래량 3배", lambda x: x.get("신고가60") is True and (x.get("거래량배수") or 0) >= 3),
    ("무반응 + 한산", lambda x: abs(x["등락"]) < 1 and 0 < (x.get("거래량배수") or 9) <= 0.5),
]


def main():
    부터 = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else None
    일, 계, 시장일, 국면 = 만들기(부터)
    행 = 행만들기(일, 계, 시장일, 국면)
    print(f"  거래일 {len(일)}일 · 관측 {len(행):,}건"
          f"{' (' + 부터 + ' 이후)' if 부터 else ''}")
    for 라벨, 필터 in [("전체", lambda x: True),
                       ("시장 상승", lambda x: x["시장"] > 0),
                       ("시장 하락", lambda x: x["시장"] <= 0)]:
        print(f"\n  [{라벨}]")
        print(f"    {'조건':22s}" + "".join(f"{'D+'+str(h):>16s}" for h in _H))
        for 이름, c in 조건들:
            줄 = f"    {이름:22s}"
            for h in _H:
                부분 = [x for x in 행 if x["h"] == h and 필터(x)]
                a = [x["초과"] for x in 부분 if c(x)]
                b = [x["초과"] for x in 부분 if not c(x)]
                if len(a) < 200 or len(b) < 200:
                    줄 += f"{'—':>16s}"
                else:
                    줄 += f"{f'{st.mean(a)-st.mean(b):+.3f} ({len(a)//1000}k)':>16s}"
            print(줄)
    return 0


if __name__ == "__main__":
    sys.exit(main())
