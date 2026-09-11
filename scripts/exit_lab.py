#!/usr/bin/env python3
r"""
exit_lab.py — **언제 팔아야 하나 · 얼마나 오를 수 있었나** (2026-09-01 신설)

⚠️⚠️ **지금까지 「N일 뒤 종가에 판다」만 봤다.** 실제로는 그 사이에 더 올랐다가 내려온다.
```
지금까지    D+5 종가 수익률만 본다
안 본 것    보유 중 **고가 기준 최대 상승폭** — 실제로 얼마나 벌 수 있었나
           목표가 도달률 — +3% / +5% / +10%에 며칠 안에 닿나
           그 목표에서 팔았다면 성적이 얼마인가
```

⚠️⚠️ **이걸 알아야 「언제 파나」를 정할 수 있다.**
   최대 상승폭이 크고 종가 수익률이 작으면 → **너무 오래 들고 있는 것**이다.
   최대 상승폭이 종가 수익률과 비슷하면 → 목표가 매도는 의미가 없다.

⚠️ **목표가 매도는 낙관 쪽으로 치우친다** — 장중 고가에 정확히 팔았다고 가정하기 때문이다.
   실제 체결가는 더 나쁘다. 그래서 **상한선으로만 읽는다.**

⚠️ 매수 D+1 종가(look-ahead 회피). 신호는 갭①④(호재+장후+무반응+정상종목).
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_보유 = (1, 3, 5, 10, 20)
_목표 = (0.03, 0.05, 0.10)


def _주가full():
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"]); 고 = float(v["고가"]); 저 = float(v["저가"])
                if 종 <= 0:
                    continue
                하루[c] = (종, 고, 저, float(v.get("시총") or 0),
                           float(v.get("거래대금") or 0), float(v.get("등락률") or 0),
                           1 if "KOSDAQ" in str(v.get("시장", "")).upper() else 0)
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def main():
    print("  자료 읽는 중…", flush=True)
    주가 = _주가full()
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    공시 = O._공시(날)

    최대 = {h: [] for h in _보유}       # 고가 기준 최대 상승(%)
    종가 = {h: [] for h in _보유}       # 종가 기준 수익(%)
    도달 = {t: [] for t in _목표}       # 목표 도달까지 걸린 일수(20일 안에 못 닿으면 None)
    목표성적 = {t: [] for t in _목표}    # 목표에서 팔았을 때 20일 기준 성적

    for i, d1 in enumerate(날):
        if i + 1 >= len(날):
            break
        a0 = 지수.get(날[i + 1])
        if not a0:
            continue
        s1 = 주가[d1]
        for code, r in (공시.get(d1) or {}).items():
            if "호재" not in r.get("성격", set()):
                continue
            if r.get("분") is None or r["분"] < 930:
                continue
            v1 = s1.get(code)
            매수v = 주가[날[i + 1]].get(code)
            if not v1 or not 매수v:
                continue
            종1, 고1, 저1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or abs(등락) >= 1:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if ("관리종목" in 부) or ("SPAC" in 부) or \
               (str(bb.get("상장일") or "") > "20240101") or \
               (bb.get("증권구분") not in (None, "주권")):
                continue
            매수가 = 매수v[0]
            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            # 보유 기간별 최대 상승 / 종가 수익
            for h in _보유:
                j = i + 1 + h
                if j >= len(날) or not 지수.get(날[j]):
                    continue
                시장 = 지수[날[j]][장] / a0[장] - 1
                고들 = [주가[날[k]].get(code)[1] for k in range(i + 1, j + 1)
                        if 주가[날[k]].get(code)]
                vv = 주가[날[j]].get(code)
                if not 고들 or not vv:
                    continue
                최대[h].append(((max(고들) / 매수가 - 1) - 시장) * 100)
                종가[h].append(((vv[0] / 매수가 - 1) - 시장) * 100)
            # 목표가 도달
            for t in _목표:
                선 = 매수가 * (1 + t)
                닿 = None
                for k in range(i + 1, min(i + 21, len(날))):
                    vv = 주가[날[k]].get(code)
                    if vv and vv[1] >= 선:
                        닿 = k - i
                        break
                도달[t].append(닿)
                j = min(i + 21, len(날)) - 1
                if 지수.get(날[j]):
                    시장 = 지수[날[j]][장] / a0[장] - 1
                    if 닿 is not None:
                        목표성적[t].append((t - 시장) * 100)
                    else:
                        vv = 주가[날[j]].get(code)
                        if vv:
                            목표성적[t].append(((vv[0] / 매수가 - 1) - 시장) * 100)
        if i % 150 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print("\n  신호: 호재 + 장 마감 후 + 무반응 + 정상종목 · 매수 D+1 종가\n")
    print("  ══ 보유 중 최대 상승 vs 종가 수익 (초과수익 기준) ══")
    print(f"  {'보유':<7}{'건수':>7}{'최대상승(고가)':>16}{'종가수익':>12}{'차이':>10}  읽는 법")
    for h in _보유:
        if len(최대[h]) < 30:
            continue
        a, b = st.mean(최대[h]), st.mean(종가[h])
        말 = ("⚠️ 너무 오래 든다 — 목표가 매도를 볼 것" if a - b >= 3
              else "· 목표가 매도 실익 적음")
        print(f"  D+{h:<5}{len(최대[h]):>7,}{a:>+15.2f}%{b:>+11.2f}%{a-b:>+9.2f}  {말}")

    print("\n  ══ 목표가 도달률 (20일 안, 장중 고가 기준) ══")
    print(f"  {'목표':<8}{'도달률':>9}{'평균 소요일':>12}{'그때 팔았다면(20일)':>22}")
    for t in _목표:
        a = 도달[t]
        if not a:
            continue
        닿 = [x for x in a if x is not None]
        비 = len(닿) / len(a) * 100
        일 = st.mean(닿) if 닿 else 0
        성 = st.mean(목표성적[t]) if 목표성적[t] else 0
        print(f"  +{int(t*100):<7}%{비:>8.1f}%{일:>11.1f}일{성:>+21.2f}%")
    print("\n  ⚠️⚠️ **목표가 매도는 낙관 쪽으로 치우친다** — 장중 고가에 정확히 팔았다고")
    print("     가정하기 때문이다. 실제 체결가는 더 나쁘다. **상한선으로만 읽는다.**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
