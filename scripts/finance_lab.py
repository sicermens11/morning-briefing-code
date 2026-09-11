#!/usr/bin/env python3
r"""finance_lab.py — **재무가 주가에 붙는가** (2026-09-01 신설)

⚠️ `data/dart-fin/{연도}.json`은 DART `fnlttMultiAcnt`(다중회사 주요계정)로 받은
   전 종목 연간 재무다(5개씩 531회 호출, 2,526종목 확보).
⚠️⚠️ **연간 재무는 그 해가 끝나야 확정된다.** 2024년 재무를 2024년 주가에 대면
   **미래를 보고 판단하는 것(look-ahead)**이 된다.
   ⇒ **2024년 재무는 2025-04 이후 주가에만, 2025년 재무는 2026-04 이후에만** 댄다.
   (사업보고서 제출 기한이 3월 말이므로 4월부터 공개된 것으로 본다.)

⚠️ 네 겹 규칙(초과수익률 · 상승/하락 · 표본 · 여러 지평)은 그대로다.

쓰는 법: python scripts\finance_lab.py
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


def _재무(code, d8, fin):
    """그 시점에 **이미 공개된** 가장 최근 연간 재무."""
    y = int(d8[:4]); m = int(d8[4:6])
    쓸해 = y - 1 if m >= 4 else y - 2
    return (fin.get(str(쓸해)) or {}).get(code)


def 지표(f):
    out = {}
    자산 = f.get("자산총계"); 부채 = f.get("부채총계"); 자본 = f.get("자본총계")
    매출 = f.get("매출액"); 영익 = f.get("영업이익"); 순익 = f.get("당기순이익(손실)")
    유동자산 = f.get("유동자산"); 유동부채 = f.get("유동부채")
    if 자본 and 자본 > 0 and 부채 is not None:
        out["부채비율"] = 부채 / 자본 * 100
    if 유동부채 and 유동부채 > 0 and 유동자산 is not None:
        out["유동비율"] = 유동자산 / 유동부채 * 100
    if 매출 and 매출 > 0:
        if 영익 is not None:
            out["영업이익률"] = 영익 / 매출 * 100
        if 순익 is not None:
            out["순이익률"] = 순익 / 매출 * 100
    if 자본 and 자본 > 0 and 순익 is not None:
        out["ROE"] = 순익 / 자본 * 100
    out["_자본"] = 자본
    out["_순익"] = 순익
    return out


def main():
    fin = {}
    for f in glob.glob(os.path.join(_DATA, "dart-fin", "*.json")):
        with io.open(f, encoding="utf-8-sig") as fp:
            fin[os.path.basename(f)[:4]] = json.load(fp)
    fs = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    일 = []
    for f in fs:
        with io.open(f, encoding="utf-8-sig") as fp:
            일.append((os.path.basename(f)[:8], json.load(fp).get("종목") or {}))
    행 = []
    for i, (d1, s1) in enumerate(일):
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
            f0 = _재무(code, d1, fin)
            if not f0:
                continue
            try:
                c1 = float(v1["종가"]); 시총 = float(v1["시총"]); 대금 = float(v1["거래대금"])
            except (TypeError, ValueError, KeyError):
                continue
            if c1 <= 0 or 시총 < _MIN_MC or 대금 < _MIN_AMT:
                continue
            g0 = 지표(f0)
            if g0.get("_순익") is not None and 시총 > 0:
                g0["PER"] = 시총 / g0["_순익"] if g0["_순익"] > 0 else None
            if g0.get("_자본"):
                g0["PBR"] = 시총 / g0["_자본"] if g0["_자본"] > 0 else None
            for h, (s2, 시장평) in 시장h.items():
                v2 = s2.get(code)
                if not v2:
                    continue
                try:
                    c2 = float(v2["종가"])
                except (TypeError, ValueError, KeyError):
                    continue
                r = dict(g0)
                r["h"] = h
                r["초과"] = ((c2 / c1 - 1) - 시장평) * 100
                r["시장"] = 시장평
                r["시총"] = 시총
                행.append(r)
    조건 = [
        ("부채비율 200%↑", lambda x: (x.get("부채비율") or 0) >= 200),
        ("부채비율 100%↓", lambda x: 0 <= (x.get("부채비율") or 999) <= 100),
        ("순이익 적자", lambda x: (x.get("_순익") or 0) < 0),
        ("영업이익률 10%↑", lambda x: (x.get("영업이익률") or -99) >= 10),
        ("영업이익률 0%↓", lambda x: (x.get("영업이익률") or 99) < 0),
        ("ROE 15%↑", lambda x: (x.get("ROE") or -99) >= 15),
        ("PER 10배↓", lambda x: 0 < (x.get("PER") or 999) <= 10),
        ("PER 30배↑", lambda x: (x.get("PER") or 0) >= 30),
        ("PBR 1배↓", lambda x: 0 < (x.get("PBR") or 999) <= 1),
        ("PBR 3배↑", lambda x: (x.get("PBR") or 0) >= 3),
        ("유동비율 100%↓", lambda x: 0 < (x.get("유동비율") or 999) <= 100),
    ]
    print(f"  관측 {len(행):,}건 (재무가 이미 공개된 시점만)")
    for 라벨, 필터 in [("전체", lambda x: True),
                       ("시장 상승", lambda x: x["시장"] > 0),
                       ("시장 하락", lambda x: x["시장"] <= 0)]:
        print(f"\n  [{라벨}]")
        print(f"    {'조건':22s}" + "".join(f"{'D+'+str(h):>17s}" for h in _H))
        for 이름, c in 조건:
            줄 = f"    {이름:22s}"
            for h in _H:
                부분 = [x for x in 행 if x["h"] == h and 필터(x)]
                a = [x["초과"] for x in 부분 if c(x)]
                b = [x["초과"] for x in 부분 if not c(x)]
                if len(a) < 200 or len(b) < 200:
                    줄 += f"{'—':>17s}"
                else:
                    줄 += f"{f'{st.mean(a)-st.mean(b):+.3f} ({len(a)//1000}k)':>17s}"
            print(줄)
    return 0


if __name__ == "__main__":
    sys.exit(main())
