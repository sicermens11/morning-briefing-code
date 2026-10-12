#!/usr/bin/env python3
r"""
insider_cluster_lab.py — **임원·주요주주 여럿이 함께 산 종목** (2026-10-12 · 사용자 10/8 「다음에 잴 10가지」)

· dart-exec(임원·주요주주 소유 보고 · 2024-09~ · 약 1년) — 증감 > 0 = 산 것
· 신호: 보고일(접수일) 기준 14일 안에 **서로 다른 사람 N명(2·3)** 이 산 날 · 같은 종목은 20거래일 안 다시 안 셈
· 견줌: 한 명만 산 날
· 다음 거래일 종가에 샀다고 보고 5·20·60거래일 뒤 수익 − 같은 기간 대상 전체 평균(시장 대비) · 시총 300억↑
⚠️ 1년치라 표본이 작다 — 참고용 · 계좌 시뮬 아님
쓰는 법: python scripts\insider_cluster_lab.py → data/_labs/<날>_임원함께매수.txt
"""
import bisect
import datetime as dt
import glob
import io
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_밖 = io.open(os.path.join(O._DATA, "_labs", f"{dt.date.today():%Y-%m-%d}_임원함께매수.txt"), "w", encoding="utf-8")


def 찍기(s=""):
    print(s, flush=True)
    _밖.write(s + "\n")


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def main():
    주가 = O.수정주가(("시총",))
    날 = sorted(주가)
    자 = {d: i for i, d in enumerate(날)}
    # 날마다 시장(대상 전체) 평균 수익 h일
    def 시장(i, h):
        if i + h >= len(날):
            return None
        a, b = 주가[날[i]], 주가[날[i + h]]
        rs = [b[c][0] / v[0] - 1 for c, v in a.items() if v[0] and len(v) > 1 and v[1] and v[1] >= 300e8 and b.get(c) and b[c][0]]
        return st.mean(rs) * 100 if rs else None
    _시캐시 = {}
    결 = {"한 명": {5: [], 20: [], 60: []}, "2명↑": {5: [], 20: [], 60: []}, "3명↑": {5: [], 20: [], 60: []}}
    for f in glob.glob(os.path.join(O._DATA, "dart-exec", "*.json")):
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        code = j.get("종목") or os.path.basename(f)[:6]
        산 = sorted((str(z.get("접수일") or "").replace("-", ""), z.get("성명") or "") for z in (j.get("이력") or [])
                   if (_n(z.get("증감")) or 0) > 0 and z.get("접수일"))
        if not 산:
            continue
        마지막 = -999
        for k, (d8, _) in enumerate(산):
            d0 = (dt.date(int(d8[:4]), int(d8[4:6]), int(d8[6:])) - dt.timedelta(days=14)).strftime("%Y%m%d")
            사람 = {p for (dd, p) in 산[: k + 1] if d0 < dd <= d8}
            i = bisect.bisect_right(날, d8)            # 보고일 다음 거래일
            if i >= len(날) or i - 마지막 < 20:
                continue
            v = 주가[날[i]].get(code)
            if not v or not v[0] or len(v) < 2 or not v[1] or v[1] < 300e8:
                continue
            마지막 = i
            갈 = "3명↑" if len(사람) >= 3 else ("2명↑" if len(사람) >= 2 else "한 명")
            for h in (5, 20, 60):
                if i + h >= len(날):
                    continue
                e = 주가[날[i + h]].get(code)
                if not e or not e[0]:
                    continue
                if (i, h) not in _시캐시:
                    _시캐시[(i, h)] = 시장(i, h)
                m = _시캐시[(i, h)]
                if m is None:
                    continue
                r = (e[0] / v[0] - 1) * 100 - 0.26
                결[갈][h].append(r - m)
                if 갈 == "3명↑":
                    결["2명↑"][h].append(r - m)
    찍기("=" * 96)
    찍기("  임원·주요주주 여럿이 14일 안에 함께 산 종목 — 다음 거래일 종가 매수 · 시장(시총 300억↑ 전체) 대비 · 비용 0.26%")
    찍기("  ⚠️ dart-exec 2024-09~ 약 1년치 — 표본이 작다 · 참고용")
    찍기("=" * 96)
    찍기(f"  {'갈래':<8}" + "".join(f"{f'{h}일 건수':>10}{f'{h}일 시장 대비':>14}{'이긴 비율':>10}" for h in (5, 20, 60)))
    for 갈, t in 결.items():
        줄 = f"  {갈:<8}"
        for h in (5, 20, 60):
            v = t[h]
            줄 += (f"{len(v):>10}{st.mean(v):>+13.2f}%{sum(1 for z in v if z > 0) / len(v) * 100:>9.0f}%" if v else f"{0:>10}{'—':>14}{'—':>10}")
        찍기(줄)
    찍기("  (2명↑ 줄에 3명↑ 도 들어 있다)")
    찍기("  [대조] 임원 함께 끝")


if __name__ == "__main__":
    main()
