#!/usr/bin/env python3
r"""feature_wide_test.py — **기술지표를 전 종목에 대입해 검증한다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** `features` 38개 중 **13개는 주가만으로 계산된다.** 그중 다섯은
   `강화-TA`의 입력인데, 이 신호는 브리핑 픽 19건 중 **18건(95%)**에 붙으면서
   **점수는 0**이다. "점수에 넣을지"를 2026-09-12로 미뤄뒀는데,
   전 종목에 대입하면 **오늘 답할 수 있다.**

⚠️⚠️ **세 겹으로 잰다** (2026-09-01에 세 번 결론이 바뀌고서 정한 규칙):
   ① **초과수익률**로 — 절대 수익률은 기간 효과에 속는다
   ② **시장 상승일/하락일로 갈라서** — 안 그러면 「베타」를 「신호」로 착각한다
   ③ **표본을 늘려 재확인** — 18일 결론이 82일에서, 82일 결론이 127일에서 흔들렸다

⚠️ 못 재는 것: 재무 11개(DART)·수급 4개·공매도 3개·컨센서스 5개·뉴스빈도·섹터.
   그리고 **갭①②는 뉴스가 있어야** 판정되므로 여기서 검증되지 않는다.

쓰는 법:
    python scripts\feature_wide_test.py
    python scripts\feature_wide_test.py --from 20260301   # 기간을 잘라서
"""
import glob
import io
import json
import os
import statistics as st
import sys
import datetime as dt

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_MIN_MC, _MIN_AMT = 5e10, 1e8          # 시총 500억·거래대금 1억 미만은 뺀다(호가가 얇다)


def _날(s):
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))


def 불러오기(부터=None):
    fs = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    일 = []
    for f in fs:
        d8 = os.path.basename(f)[:8]
        if 부터 and d8 < 부터:
            continue
        with io.open(f, encoding="utf-8-sig") as fp:
            일.append((d8, json.load(fp).get("종목") or {}))
    return 일


def 지표(계열):
    """종가 계열(과거→현재)에서 기술지표를 낸다. 길이가 모자라면 None."""
    n = len(계열)
    out = {}
    c = 계열[-1]
    if n >= 21:
        sma20 = st.mean(계열[-20:])
        out["20일선위"] = c > sma20
        out["상대강도_20일"] = (c / 계열[-21] - 1) * 100
    if n >= 61:
        out["상대강도_60일"] = (c / 계열[-61] - 1) * 100
    if n >= 121:
        out["상대강도_120일"] = (c / 계열[-121] - 1) * 100
    if n >= 15:
        오, 내 = [], []
        for i in range(-14, 0):
            차 = 계열[i] - 계열[i - 1]
            (오 if 차 > 0 else 내).append(abs(차))
        au, ad = (sum(오) / 14), (sum(내) / 14)
        out["RSI14"] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def 돌리기(부터=None):
    일 = 불러오기(부터)
    if len(일) < 25:
        return {"ok": False, "이유": f"거래일이 {len(일)}일뿐이다 — 25일 이상 필요"}
    # 종목별 종가 계열을 이어 붙인다(빠진 날은 건너뛴다 — 계열 길이만 짧아진다)
    계열 = {}
    for _, s in 일:
        for code, v in s.items():
            try:
                c = float(v["종가"])
            except (TypeError, ValueError, KeyError):
                continue
            if c > 0:
                계열.setdefault(code, []).append(c)
    행 = []
    for i in range(len(일) - 1):
        (d1, s1), (d2, s2) = 일[i], 일[i + 1]
        if (_날(d2) - _날(d1)).days > 3:      # 이어지지 않은 날은 뺀다
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
                고, 저 = float(v1["고가"]), float(v1["저가"])
            except (TypeError, ValueError, KeyError):
                continue
            if c1 <= 0 or 시총 < _MIN_MC or 대금 < _MIN_AMT:
                continue
            계 = 계열.get(code, [])
            끝 = None
            for j in range(len(계) - 1, -1, -1):
                if abs(계[j] - c1) < 1e-9:
                    끝 = j
                    break
            if 끝 is None or 끝 < 20:
                continue
            f = 지표(계[:끝 + 1])
            f["ATR14pct"] = (고 - 저) / c1 * 100
            f["시가총액"] = 시총
            f["거래대금"] = 대금
            f["초과"] = ((c2 / c1 - 1) - 시장평) * 100
            f["시장"] = 시장평
            행.append(f)
    return {"ok": True, "행": 행, "거래일": len(일)}


def 비교(행, 이름, 조건):
    a = [x["초과"] for x in 행 if 조건(x)]
    b = [x["초과"] for x in 행 if not 조건(x)]
    if len(a) < 100 or len(b) < 100:
        return None
    return {"이름": 이름, "n맞음": len(a), "평균맞음": round(st.mean(a), 3),
            "n아님": len(b), "평균아님": round(st.mean(b), 3),
            "차이": round(st.mean(a) - st.mean(b), 3)}


def main():
    부터 = None
    if "--from" in sys.argv:
        부터 = sys.argv[sys.argv.index("--from") + 1]
    r = 돌리기(부터)
    if not r.get("ok"):
        print(json.dumps(r, ensure_ascii=False))
        return 1
    행 = r["행"]
    print(f"  거래일 {r['거래일']}일 · 관측 {len(행):,}건"
          f"{' (' + 부터 + ' 이후)' if 부터 else ''}\n")
    조건들 = [
        ("20일선 위", lambda x: x.get("20일선위") is True),
        ("RSI14 > 70 (과매수)", lambda x: (x.get("RSI14") or 50) > 70),
        ("RSI14 < 30 (과매도)", lambda x: (x.get("RSI14") or 50) < 30),
        ("상대강도20 > +10%", lambda x: (x.get("상대강도_20일") or 0) > 10),
        ("상대강도20 < −10%", lambda x: (x.get("상대강도_20일") or 0) < -10),
        ("상대강도120 > +30%", lambda x: (x.get("상대강도_120일") or 0) > 30),
        ("ATR14 > 5% (변동 큼)", lambda x: x.get("ATR14pct", 0) > 5),
        ("시총 3천억 미만", lambda x: x["시가총액"] < 3e11),
        ("거래대금 100억+", lambda x: x["거래대금"] >= 1e10),
    ]
    for 라벨, 부분 in [("전체", 행),
                       ("시장 상승일", [x for x in 행 if x["시장"] > 0]),
                       ("시장 하락일", [x for x in 행 if x["시장"] <= 0])]:
        print(f"  [{라벨}] {len(부분):,}건")
        for 이름, c in 조건들:
            v = 비교(부분, 이름, c)
            if not v:
                continue
            print(f"    {v['이름']:22s} n={v['n맞음']:6,d} {v['평균맞음']:+6.3f}%p  vs  "
                  f"{v['평균아님']:+6.3f}%p  →  {v['차이']:+6.3f}%p")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
