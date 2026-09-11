#!/usr/bin/env python3
r"""
consensus_lab.py — **조건부-C(목표주가·투자의견)가 실제로 신호인가** (2026-09-01 신설)

⚠️⚠️ **점수표에서 가장 큰 감점인데 지금까지 한 번도 검증을 못 했다.**
```
목표주가 상향  +1  ·  목표주가 하향/매도의견  **−2**  ·  투자의견 강등  **−1**
```
과거 컨센서스가 없었기 때문이다. 오늘 한경컨센서스로 10,158건을 받아 처음 잰다.

**어떻게 재나 — 네 겹 규칙**([[finish-data-before-concluding]])
```
① 초과수익률로            **실제 지수**(index-daily) 대비. 단순평균이 아니다
② 시장 상승일/하락일 갈라서   베타를 걷어낸다
③ 표본을 밝히고            n을 항상 같이 쓴다
④ 여러 지평               D+1 · D+5 · D+20
```
⚠️ **같은 종목·같은 증권사의 직전 목표주가와 비교한다.** 증권사마다 눈높이가 달라서
   서로 다른 증권사끼리 비교하면 상향/하향이 아니라 **증권사 차이**를 재게 된다.

⚠️ 리포트는 그날 나온다 → **다음 거래일 종가부터** 잰다(look-ahead 방지).
"""
import glob
import io
import json
import os
import statistics as st
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_H = (1, 5, 20)
_MIN = 30          # 이 미만이면 "—"로 둔다


def _주가():
    표 = {}
    for f in sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        표[d["기준일"]] = d["종목"]
    return 표


def _지수():
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "index-daily", "*.json")):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        z = d.get("지수") or {}
        a, b = (z.get("코스피") or {}).get("종가"), (z.get("코스닥") or {}).get("종가")
        if a and b:
            표[d["기준일"]] = {"KOSPI": a, "KOSDAQ": b}
    return 표


def _리포트():
    out = []
    for f in sorted(glob.glob(os.path.join(_DATA, "consensus", "*.json"))):
        out += json.load(io.open(f, encoding="utf-8-sig"))["리포트"]
    out.sort(key=lambda r: r["날짜"])
    return out


def main():
    주가, 지수, 리포 = _주가(), _지수(), _리포트()
    날 = sorted(주가)
    자리 = {d: i for i, d in enumerate(날)}
    print(f"  주가 {len(날)}일 · 지수 {len(지수)}일 · 리포트 {len(리포):,}건", flush=True)

    # 같은 (종목, 증권사)의 직전 목표주가
    직전 = {}
    행 = []
    for r in 리포:
        c, s, t = r.get("코드"), r.get("증권사"), r.get("목표주가")
        if not c or not s:
            continue
        d8 = r["날짜"].replace("-", "")
        키 = (c, s)
        앞 = 직전.get(키)
        if t:
            직전[키] = t
        if not 앞 or not t:
            continue
        방향 = "상향" if t > 앞 * 1.01 else ("하향" if t < 앞 * 0.99 else "유지")
        폭 = (t / 앞 - 1) * 100
        # ⚠️ 리포트 당일이 거래일이 아닐 수 있다 → 그 이후 첫 거래일을 기준일로
        i = None
        for k in range(0, 6):
            cand = 자리.get(d8)
            if cand is not None:
                i = cand
                break
            d8 = f"{int(d8)+1}"
        if i is None or i + max(_H) >= len(날):
            continue
        v1 = 주가[날[i]].get(c)
        if not v1 or not v1.get("종가"):
            continue
        장 = "KOSDAQ" if "KOSDAQ" in str(v1.get("시장", "")).upper() else "KOSPI"
        for h in _H:
            j = i + h
            v2 = 주가[날[j]].get(c)
            a, b = 지수.get(날[i]), 지수.get(날[j])
            if not v2 or not v2.get("종가") or not a or not b:
                continue
            시장 = b[장] / a[장] - 1
            초과 = ((v2["종가"] / v1["종가"] - 1) - 시장) * 100
            행.append({"방향": 방향, "폭": 폭, "h": h, "초과": 초과, "시장": 시장,
                       "의견": (r.get("의견") or "").lower()})

    print(f"  비교 가능한 쌍 {len({(x['h']) for x in 행}) and len(행)//len(_H):,}건\n", flush=True)

    조건 = [("목표주가 상향", lambda x: x["방향"] == "상향"),
            ("목표주가 유지", lambda x: x["방향"] == "유지"),
            ("목표주가 하향", lambda x: x["방향"] == "하향"),
            ("  하향 −10%↓", lambda x: x["방향"] == "하향" and x["폭"] <= -10),
            ("  상향 +10%↑", lambda x: x["방향"] == "상향" and x["폭"] >= 10),
            ("의견 buy 계열", lambda x: x["의견"] in ("buy", "매수")),
            ("의견 hold/중립", lambda x: x["의견"] in ("hold", "중립", "neutral")),
            ("의견 not rated", lambda x: "not" in x["의견"] or x["의견"] in ("nr", "n/a")),
            ]
    for 이름, 걸 in (("전체", lambda x: True),
                     ("시장 상승", lambda x: x["시장"] > 0),
                     ("시장 하락", lambda x: x["시장"] <= 0)):
        print(f"  [{이름}]")
        print(f"    {'조건':<20}{'D+1':>17}{'D+5':>17}{'D+20':>17}")
        for 라벨, c in 조건:
            칸 = []
            for h in _H:
                v = [x["초과"] for x in 행 if x["h"] == h and 걸(x) and c(x)]
                칸.append(f"{st.mean(v):+.3f} (n={len(v)})" if len(v) >= _MIN else "—")
            print(f"    {라벨:<20}{칸[0]:>17}{칸[1]:>17}{칸[2]:>17}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
