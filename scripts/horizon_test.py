#!/usr/bin/env python3
r"""horizon_test.py — **D+1 · D+5 · D+20을 함께 잰다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 2026-09-01에 만든 전 종목 실험들(`market_wide_test`·`feature_wide_test`·
   `disclosure_wide_test`)이 전부 **D+1(다음날)만** 쟀다. 그런데 **브리핑이 보는 것은 D+5**다.
   하루 뒤는 잡음이 크다 — **가장 중요한 지평을 안 재고 결론을 냈다.**
   ⚠️ 표본을 늘릴 때마다 결론이 네 번 바뀐 그 위험과 같은 종류다. 지평이 바뀌면 또 바뀔 수 있다.

⚠️⚠️ **세 겹 규칙은 그대로다**: ① 초과수익률 ② 시장 상승일/하락일 ③ 표본을 늘려 재확인.
   여기에 **④ 여러 지평**을 더한다.

⚠️ 지평은 **거래일 기준**이다. 캐시에 빠진 날이 있으면 그만큼 실제 간격이 벌어지므로,
   **연속으로 이어지는 구간에서만** 잰다(달력 간격이 지평×2일을 넘으면 버린다).

쓰는 법:
    python scripts\horizon_test.py
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


def 돌리기():
    fs = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    일 = []
    for f in fs:
        with io.open(f, encoding="utf-8-sig") as fp:
            일.append((os.path.basename(f)[:8], json.load(fp).get("종목") or {}))
    공시 = {}
    for f in glob.glob(os.path.join(_DATA, "dart-daily", "*.json")):
        with io.open(f, encoding="utf-8-sig") as fp:
            g = json.load(fp)
        공시[os.path.basename(f)[:8]] = {x.get("종목코드")
                                         for x in (g.get("챙길공시") or []) if x.get("종목코드")}
    행 = []
    for i, (d1, s1) in enumerate(일):
        for h in _H:
            j = i + h
            if j >= len(일):
                continue
            d2, s2 = 일[j]
            # ⚠️ 빠진 날이 많으면 실제 간격이 벌어진다. 지평×2일(달력)을 넘으면 버린다.
            if (_날(d2) - _날(d1)).days > h * 2 + 4:
                continue
            시장 = [float(x["종가"]) / float(s1[k]["종가"]) - 1
                    for k, x in s2.items()
                    if k in s1 and float(s1[k].get("시총") or 0) >= _MIN_MC
                    and float(s1[k].get("종가") or 0) > 0]
            if not 시장:
                continue
            시장평 = st.mean(시장)
            코드 = 공시.get(d1)
            for code, v1 in s1.items():
                v2 = s2.get(code)
                if not v2:
                    continue
                try:
                    c1, c2 = float(v1["종가"]), float(v2["종가"])
                    시총, 대금 = float(v1["시총"]), float(v1["거래대금"])
                    등락 = float(v1["등락률"])
                    고, 저 = float(v1["고가"]), float(v1["저가"])
                except (TypeError, ValueError, KeyError):
                    continue
                if c1 <= 0 or 시총 < _MIN_MC or 대금 < _MIN_AMT:
                    continue
                행.append({"h": h, "초과": ((c2 / c1 - 1) - 시장평) * 100, "시장": 시장평,
                           "등락": 등락, "변동": (고 - 저) / c1 * 100, "시총": 시총,
                           "공시": (code in 코드) if 코드 is not None else None})
    return 행


def 비교(행, 이름, 조건):
    a = [x["초과"] for x in 행 if 조건(x)]
    b = [x["초과"] for x in 행 if not 조건(x)]
    if len(a) < 100 or len(b) < 100:
        return None
    return len(a), st.mean(a) - st.mean(b)


def main():
    행 = 돌리기()
    조건들 = [
        ("공시 있음", lambda x: x["공시"] is True),
        ("갭④ 무반응(<1%)", lambda x: abs(x["등락"]) < 1),
        ("전날 급등(+5%↑)", lambda x: x["등락"] >= 5),
        ("전날 급락(−5%↓)", lambda x: x["등락"] <= -5),
        ("변동폭 5%↑", lambda x: x["변동"] >= 5),
        ("시총 3천억 미만", lambda x: x["시총"] < 3e11),
    ]
    for 라벨, 필터 in [("전체", lambda x: True),
                       ("시장 상승", lambda x: x["시장"] > 0),
                       ("시장 하락", lambda x: x["시장"] <= 0)]:
        print(f"\n  [{라벨}]")
        print(f"    {'조건':22s}" + "".join(f"{'D+'+str(h):>16s}" for h in _H))
        for 이름, c in 조건들:
            줄 = f"    {이름:22s}"
            for h in _H:
                부분 = [x for x in 행 if x["h"] == h and 필터(x)]
                r = 비교(부분, 이름, c)
                줄 += f"{(f'{r[1]:+.3f} (n={r[0]//1000}k)' if r else '—'):>16s}"
            print(줄)
    return 0


if __name__ == "__main__":
    sys.exit(main())
