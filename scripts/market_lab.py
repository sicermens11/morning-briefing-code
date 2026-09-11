#!/usr/bin/env python3
r"""
market_lab.py — **국면 필터를 실행 가능한 형태로 검증한다** (2026-09-02 신설)

⚠️⚠️⚠️ **1차 실험의 가장 큰 발견에서 나왔다.**
   `entry_lab` 결과: 갭①④ D+5가 **상승장 −1.33 / 하락장 +1.57**.
   거의 모든 신호가 **하락일에만 산다.**
   ⚠️ **그런데 「오늘이 하락일인지」는 그날 장이 끝나야 안다** — 아침 08:00에는 모른다.
      **미래를 보고 고른 것이라 그대로는 못 쓴다.**

**그래서 「아침에 알 수 있는 것」으로 대체 가능한지 잰다**
```
① 전일 시장 방향        어제 코스피가 내렸나           ← 가장 단순
② 전일 이틀 연속 방향    이틀 내리 내렸나
③ 20일선 대비 지수 위치  지수가 20일선 아래인가
④ 선물 베이시스         (선물 − 현물) 부호. 백워데이션이면 약세 신호
⑤ 국고채 3년 금리 방향   전일 대비 금리가 올랐나
⑥ 장단기 스프레드       10년 − 3년. 좁아지면 경기 둔화 신호
⑦ 원/달러 방향          전일 대비 원화가 약해졌나
⑧ 유가 방향            전일 대비
```
**모두 「전 거래일까지의 정보」라 아침 08:00에 알 수 있다.**

⚠️ 비교 기준: **「그날 실제 하락일」**(미래를 본 것, 상한선) 대비 몇 %를 재현하나.

⚠️ 매수 D+1 종가(look-ahead 회피) · 신호는 호재 공시 · 오염 종목 제외.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = (1, 5, 20)
_MIN = 60


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _선물():
    """{날짜: 베이시스pct} — 코스피200 선물(정규장 최근월) 기준."""
    표 = {}
    for f in glob.glob(os.path.join(O._DATA, "krx-extra", "선물", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        후보 = []
        for r in (d.get("자료", {}).get("fut_bydd_trd") or []):
            pn = str(r.get("PROD_NM") or "")
            if "코스피200 선물" not in pn and "코스피200선물" not in pn:
                continue
            if str(r.get("MKT_NM") or "") == "야간":
                continue
            선 = _n(r.get("TDD_CLSPRC"))
            현 = _n(r.get("SPOT_PRC"))
            if 선 and 현 and 현 > 0:
                후보.append((선 / 현 - 1) * 100)
        if 후보:
            표[d["기준일"]] = 후보[0]
    return 표


def _금리():
    """{날짜: {만기: 수익률}} — 지표물만."""
    표 = {}
    for f in glob.glob(os.path.join(O._DATA, "krx-extra", "국고채", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        하루 = {}
        for r in (d.get("자료", {}).get("kts_bydd_trd") or []):
            if str(r.get("GOVBND_ISU_TP_NM") or "") != "지표":
                continue
            만 = str(r.get("BND_EXP_TP_NM") or "")
            y = _n(r.get("CLSPRC_YD"))
            if 만 and y:
                하루[만] = y
        if 하루:
            표[d["기준일"]] = 하루
    return 표


def _유가():
    표 = {}
    for f in glob.glob(os.path.join(O._DATA, "krx-extra", "일반상품", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for r in (d.get("자료", {}).get("oil_bydd_trd") or []):
            if str(r.get("OIL_NM") or "") == "휘발유":
                v = _n(r.get("WT_DIS_AVG_PRC"))
                if v:
                    표[d["기준일"]] = v
    return 표


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O._주가()
    날 = sorted(주가)
    지수, 기본, 환율 = O._지수(), O._기본(), O._환율()
    공시 = O._공시(날)
    베 = _선물()
    금리 = _금리()
    유가 = _유가()
    print(f"  선물 {len(베)}일 · 국고채 {len(금리)}일 · 유가 {len(유가)}일 "
          f"· 환율 {len(환율)}일", flush=True)

    통 = {}
    맞춤 = {}

    def 담(k, v):
        s = 통.setdefault(k, [0.0, 0])
        s[0] += v
        s[1] += 1

    for i, d1 in enumerate(날):
        if i + 1 >= len(날) or i < 21:
            continue
        a0 = 지수.get(날[i + 1])
        if not a0 or not 지수.get(d1):
            continue
        전 = 날[i - 1]
        전전 = 날[i - 2]

        # ── 아침에 알 수 있는 국면 판정들 ──
        조건 = {}
        if 지수.get(전):
            조건["1 전일 하락"] = 지수[d1]["KOSPI"] < 지수[전]["KOSPI"]
        if 지수.get(전) and 지수.get(전전):
            조건["2 이틀 연속 하락"] = (지수[d1]["KOSPI"] < 지수[전]["KOSPI"]
                                        and 지수[전]["KOSPI"] < 지수[전전]["KOSPI"])
        창 = [지수[d]["KOSPI"] for d in 날[i - 20:i + 1] if 지수.get(d)]
        if len(창) >= 15:
            조건["3 지수 20일선 아래"] = 지수[d1]["KOSPI"] < st.mean(창)
        if d1 in 베:
            조건["4 백워데이션(베이시스<0)"] = 베[d1] < 0
        if d1 in 금리 and 전 in 금리:
            a, b = 금리[d1].get("3"), 금리[전].get("3")
            if a and b:
                조건["5 국고3년 금리 상승"] = a > b
            c, e = 금리[d1].get("10"), 금리[d1].get("3")
            f2, g = 금리[전].get("10"), 금리[전].get("3")
            if c and e and f2 and g:
                조건["6 장단기 스프레드 축소"] = (c - e) < (f2 - g)
        if d1 in 환율 and 전 in 환율:
            조건["7 원화 약세(환율↑)"] = 환율[d1] > 환율[전]
        if d1 in 유가 and 전 in 유가:
            조건["8 유가 상승"] = 유가[d1] > 유가[전]

        s1 = 주가[d1]
        ds = 공시.get(d1) or {}
        for code, r in ds.items():
            if "호재" not in r.get("성격", set()):
                continue
            v1 = s1.get(code)
            매수v = 주가[날[i + 1]].get(code)
            if not v1 or not 매수v:
                continue
            c1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (str(bb.get("상장일") or "") > "20240101")
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            매수가 = 매수v[0]
            for h in _H:
                j = i + 1 + h
                if j >= len(날) or not 지수.get(날[j]):
                    continue
                vv = 주가[날[j]].get(code)
                if not vv:
                    continue
                시장 = 지수[날[j]][장] / a0[장] - 1
                초 = ((vv[0] / 매수가 - 1) - 시장) * 100
                담(("0 전체(기준선)", h), 초)
                # 미래를 본 상한선
                담(("* 실제 하락일(미래·상한)" if 시장 <= 0 else "* 실제 상승일", h), 초)
                for 이름, 참 in 조건.items():
                    if 참:
                        담((이름, h), 초)
                        if h == 5:
                            맞춤.setdefault(이름, [0, 0])
                            맞춤[이름][0] += 1
                            맞춤[이름][1] += 1 if 시장 <= 0 else 0
        if i % 150 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print("\n  신호: 호재 공시 · 매수 D+1 종가 · 오염 종목 제외\n")
    차례 = ["0 전체(기준선)", "* 실제 하락일(미래·상한)", "* 실제 상승일",
            "1 전일 하락", "2 이틀 연속 하락", "3 지수 20일선 아래",
            "4 백워데이션(베이시스<0)", "5 국고3년 금리 상승",
            "6 장단기 스프레드 축소", "7 원화 약세(환율↑)", "8 유가 상승"]
    print(f"  {'국면 조건':<26}{'D+1':>15}{'D+5':>15}{'D+20':>15}{'하락일 적중':>12}")
    for 이름 in 차례:
        칸 = []
        for h in _H:
            s = 통.get((이름, h))
            칸.append(f"{s[0] / s[1]:+.3f}({s[1]:,})" if s and s[1] >= _MIN else "-")
        if all(c == "-" for c in 칸):
            continue
        m = 맞춤.get(이름)
        적 = f"{m[1] / m[0] * 100:>10.1f}%" if m and m[0] else ""
        print(f"  {이름:<26}" + "".join(f"{c:>15}" for c in 칸) + 적)

    print("\n  읽는 법")
    print("    - '실제 하락일'은 미래를 본 상한선이다. 아침에는 알 수 없다")
    print("    - 1~8번은 전 거래일까지의 정보라 아침 08:00에 알 수 있다")
    print("    - '하락일 적중'은 그 조건이 켜졌을 때 실제로 하락일이었던 비율이다")
    print("    - 상한선에 가까울수록 좋은 대체재다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
