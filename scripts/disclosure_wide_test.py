#!/usr/bin/env python3
r"""disclosure_wide_test.py — **공시가 난 종목이 다음날 시장보다 오르나** (2026-09-01 신설)

⚠️⚠️ **갭①의 완전한 재현은 아니다.** 갭①은 *"재료가 **장 마감 후** 발생"*인데
   **DART 응답에 접수 시각이 없다**(접수번호만 있고 시분초가 없다). 장중 공시와
   장후 공시를 못 가른다. ⇒ 여기서 재는 것은 **"재료가 났나"**까지다.
   **갭①이 검증됐다고 말하면 안 된다.**

⚠️ 그래도 값이 있다 — 지금까지 "공시가 난 종목이 실제로 오르나"를 **한 번도 재본 적이 없다.**
   브리핑 픽은 하루 3.2건뿐이라 표본이 안 됐다. 전 종목이면 하루 수십~수백 건이다.

⚠️⚠️ **세 겹으로 잰다** (2026-09-01 규칙):
   ① 초과수익률로 · ② 시장 상승일/하락일로 갈라서 · ③ 표본을 늘려 재확인.
   같은 데이터로도 재는 법에 따라 결론이 세 번 뒤집힌 적이 있다.

⚠️ `챙길공시`만 쓴다. `정보성`(기타시장안내·거래정지 등)은 재료가 아니다.

쓰는 법:
    python scripts\disclosure_wide_test.py
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


def _날(s):
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))


def 돌리기():
    krx = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    일 = []
    for f in krx:
        d8 = os.path.basename(f)[:8]
        공시 = os.path.join(_DATA, "dart-daily", f"{d8}.json")
        if not os.path.exists(공시):
            continue
        with io.open(f, encoding="utf-8-sig") as fp:
            시세 = json.load(fp).get("종목") or {}
        with io.open(공시, encoding="utf-8-sig") as fp:
            g = json.load(fp)
        코드 = {x.get("종목코드") for x in (g.get("챙길공시") or []) if x.get("종목코드")}
        일.append((d8, 시세, 코드))
    if len(일) < 5:
        return {"ok": False, "이유": f"공시+시세가 함께 있는 날이 {len(일)}일뿐이다"}

    행 = []
    for i in range(len(일) - 1):
        (d1, s1, 코드), (d2, s2, _) = 일[i], 일[i + 1]
        if (_날(d2) - _날(d1)).days > 3:
            continue
        시장 = [float(x["종가"]) / float(s1[k]["종가"]) - 1
                for k, x in s2.items()
                if k in s1 and float(s1[k].get("시총") or 0) >= _MIN_MC
                and float(s1[k].get("종가") or 0) > 0]
        if not 시장:
            continue
        시장평 = st.mean(시장)
        for code, v1 in s1.items():
            v2 = s2.get(code)
            if not v2:
                continue
            try:
                c1, c2 = float(v1["종가"]), float(v2["종가"])
                시총, 대금 = float(v1["시총"]), float(v1["거래대금"])
                등락 = float(v1["등락률"])
            except (TypeError, ValueError, KeyError):
                continue
            if c1 <= 0 or 시총 < _MIN_MC or 대금 < _MIN_AMT:
                continue
            행.append({"공시": code in 코드, "무반응": abs(등락) < 1,
                       "초과": ((c2 / c1 - 1) - 시장평) * 100, "시장": 시장평})
    return {"ok": True, "행": 행, "날수": len(일)}


def 비교(행, 이름, 조건):
    a = [x["초과"] for x in 행 if 조건(x)]
    b = [x["초과"] for x in 행 if not 조건(x)]
    if len(a) < 50 or len(b) < 50:
        return
    print(f"    {이름:26s} n={len(a):6,d} {st.mean(a):+6.3f}%p  vs  "
          f"{st.mean(b):+6.3f}%p  →  {st.mean(a)-st.mean(b):+6.3f}%p")


def main():
    r = 돌리기()
    if not r.get("ok"):
        print(json.dumps(r, ensure_ascii=False))
        return 1
    행 = r["행"]
    print(f"  공시+시세가 함께 있는 날 {r['날수']}일 · 관측 {len(행):,}건\n")
    for 라벨, 부분 in [("전체", 행),
                       ("시장 상승일", [x for x in 행 if x["시장"] > 0]),
                       ("시장 하락일", [x for x in 행 if x["시장"] <= 0])]:
        print(f"  [{라벨}] {len(부분):,}건")
        비교(부분, "공시 있음", lambda x: x["공시"])
        # ⚠️ 갭① + 갭④에 가장 가까운 조합: 재료가 났는데도 주가가 안 움직였다
        비교(부분, "공시 있음 + 무반응(<1%)", lambda x: x["공시"] and x["무반응"])
        비교(부분, "공시 없음 + 무반응", lambda x: (not x["공시"]) and x["무반응"])
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
