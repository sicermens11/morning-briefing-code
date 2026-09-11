#!/usr/bin/env python3
r"""disclosure_lab.py — **공시를 갈라서 검정한다** (2026-09-01 신설)

⚠️⚠️ 앞선 `disclosure_wide_test`는 **"공시가 났다"를 통째로** 쟀다. 그 결과가
   D+1 −0.162 · D+5 −0.231 · **D+20 +0.241**이었는데, 셋을 안 갈랐기 때문에 뜻이 흐렸다:
   ① `챙길공시`에 **유상증자·CB·거래정지 같은 악재가 섞였다**
   ② 우리 갭①은 **「장 마감 후」** 공시인데 **장중 공시가 섞였다**
   ③ 하루에 여러 건 난 종목과 한 건 난 종목을 같이 셌다

**접수번호로 시각 순서를 안다** — `YYYYMMDD` + 6자리 순번. 앞자리가 `9`면 거래소(KRX),
`0`이면 금감원(DART) 접수다. **각 계열 안에서 순번이 클수록 늦게 접수된 것**이다.
⚠️ **절대 시각이 아니다.** "그날 접수분 중 늦은 쪽"이라는 상대 순서일 뿐이므로,
   **「장 마감 후」의 대리지표**로만 쓴다. 갭①이 검증됐다고 말하면 안 된다.

⚠️ 네 겹 규칙(초과수익률 · 상승/하락 갈라서 · 표본 늘려 · 여러 지평)은 그대로다.

쓰는 법: python scripts\disclosure_lab.py
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

# ⚠️ 공시명으로 성격을 가른다. 애매한 것은 **중립으로 둔다** — 억지로 나누면 없는 패턴이 생긴다.
_호재 = ("단일판매", "공급계약", "수주", "자기주식취득", "자기주식소각", "무상증자",
         "현금ㆍ현물배당", "영업양수", "타법인주식및출자증권취득")
_악재 = ("유상증자", "전환사채", "신주인수권부사채", "교환사채", "거래정지", "상장폐지",
         "소송등의제기", "감자", "자기주식처분", "관리종목", "횡령", "배임")


def _성격(공시명: str) -> str:
    n = re.sub(r"\[[^\]]*\]", "", 공시명 or "")
    if any(k in n for k in _악재):
        return "악재"
    if any(k in n for k in _호재):
        return "호재"
    return "중립"


def _날(s):
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))


def 만들기():
    fs = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    일 = []
    for f in fs:
        d8 = os.path.basename(f)[:8]
        p = os.path.join(_DATA, "dart-daily", f"{d8}.json")
        if not os.path.exists(p):
            continue
        with io.open(f, encoding="utf-8-sig") as fp:
            시세 = json.load(fp).get("종목") or {}
        with io.open(p, encoding="utf-8-sig") as fp:
            g = json.load(fp)
        정보 = {}
        번호들 = []
        for x in (g.get("챙길공시") or []):
            code = x.get("종목코드")
            번 = x.get("접수번호") or ""
            if not code or len(번) < 14:
                continue
            순 = int(번[8:])
            번호들.append(순)
            r = 정보.setdefault(code, {"건수": 0, "성격": set(), "순번": []})
            r["건수"] += 1
            r["성격"].add(_성격(x.get("공시명")))
            r["순번"].append(순)
        # 그날 순번의 중앙값으로 늦음/이름을 가른다(계열이 섞여 있으므로 상대 위치만 본다)
        중 = st.median(번호들) if 번호들 else 0
        for r in 정보.values():
            r["늦음"] = max(r["순번"]) > 중
        일.append((d8, 시세, 정보))
    return 일


def 행만들기(일):
    행 = []
    for i, (d1, s1, 정보) in enumerate(일):
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
        for code, v1 in s1.items():
            try:
                c1 = float(v1["종가"]); 시총 = float(v1["시총"]); 대금 = float(v1["거래대금"])
                등락 = float(v1["등락률"])
            except (TypeError, ValueError, KeyError):
                continue
            if c1 <= 0 or 시총 < _MIN_MC or 대금 < _MIN_AMT:
                continue
            r = 정보.get(code)
            for h, (s2, 시장평) in 시장h.items():
                v2 = s2.get(code)
                if not v2:
                    continue
                try:
                    c2 = float(v2["종가"])
                except (TypeError, ValueError, KeyError):
                    continue
                행.append({"h": h, "초과": ((c2 / c1 - 1) - 시장평) * 100, "시장": 시장평,
                           "무반응": abs(등락) < 1,
                           "공시": bool(r), "건수": (r or {}).get("건수", 0),
                           "성격": (r or {}).get("성격", set()),
                           "늦음": (r or {}).get("늦음")})
    return 행


조건들 = [
    ("공시 있음(전체)", lambda x: x["공시"]),
    ("호재 공시", lambda x: "호재" in x["성격"]),
    ("악재 공시", lambda x: "악재" in x["성격"]),
    ("중립만", lambda x: x["공시"] and x["성격"] == {"중립"}),
    ("호재 + 악재 없음", lambda x: "호재" in x["성격"] and "악재" not in x["성격"]),
    ("공시 2건 이상", lambda x: x["건수"] >= 2),
    ("늦게 접수(장후 추정)", lambda x: x["늦음"] is True),
    ("일찍 접수(장중 추정)", lambda x: x["늦음"] is False),
    ("호재 + 늦게 + 무반응", lambda x: "호재" in x["성격"] and x["늦음"] is True and x["무반응"]),
]


def main():
    일 = 만들기()
    행 = 행만들기(일)
    print(f"  공시+시세가 함께 있는 날 {len(일)}일 · 관측 {len(행):,}건")
    for 라벨, 필터 in [("전체", lambda x: True),
                       ("시장 상승", lambda x: x["시장"] > 0),
                       ("시장 하락", lambda x: x["시장"] <= 0)]:
        print(f"\n  [{라벨}]")
        print(f"    {'조건':24s}" + "".join(f"{'D+'+str(h):>16s}" for h in _H))
        for 이름, c in 조건들:
            줄 = f"    {이름:24s}"
            for h in _H:
                부분 = [x for x in 행 if x["h"] == h and 필터(x)]
                a = [x["초과"] for x in 부분 if c(x)]
                b = [x["초과"] for x in 부분 if not c(x)]
                if len(a) < 150 or len(b) < 150:
                    줄 += f"{'—':>16s}"
                else:
                    줄 += f"{f'{st.mean(a)-st.mean(b):+.3f} (n={len(a)})':>16s}"
            print(줄)
    return 0


if __name__ == "__main__":
    sys.exit(main())
