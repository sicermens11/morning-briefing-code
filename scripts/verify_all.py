#!/usr/bin/env python3
r"""
verify_all.py — **104차. 「1차 결과」를 한 번에 검증한다** (2026-09-04)

## ⚠️⚠️ 왜 만들었나
```
2026-09-04 하루에 **네 번 결론을 뒤집었다.**
   「처음으로 조건 추가가 이겼다」 -> 졌다  (자사주처분 갈래를 빠뜨림)
   「3종목 분산이 최선」         -> 1종목  (순위에 표본 짧은 종목이 섞임)
   「후보 20~40개」            -> 0~1개  (**안 재보고 말함**)
   「지수로 대신하면 된다」       -> 낙폭 4배
⇒ 원인은 **1차 결과를 결론처럼 말한 것**이다.
   여기서는 「1차 결과」들을 **한 번에 제대로** 걸어 정리한다
```

## 검증 기준 — 넷을 다 넘어야 「검증됨」
```
① 앞뒤 분할     네 분할점(~2019·~2020·~2021·~2022)에서 **뒤 기간**이 다 흑자
② 2025·26 제외  빼고도 원판보다 낫거나 같다
③ 무작위 대비   무작위 300개 분포에서 **상위 25% 안**
④ 낙폭         원판보다 크게 나빠지지 않는다 (1.3배 이내)
```

## 무엇을 거나
```
A ① 시총 2천억 · 하루 4종목        (98·94b차 1차 결과)
B ② 보조 전략 하이닉스 20일         (100b차 1차 결과)
C ④ 실전 절차 — 후보 N개 + 후보중앙갭 (101·102·103차 1차 결과)
D 최종 판정표
```
⚠️ ③ 증자·감자는 자료가 75%뿐이라 **여기서 안 건다.** 내일 자료 받고 따로 잰다
⚠️ 주수는 **원본 시가**로, 수익률은 **수정 비율**로 (53차 버그)
"""
import bisect
import datetime as dt
import glob
import io
import json
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_시드 = 5_000_000.0
옛판 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 3e11,
        "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 2}
새판 = {"갭": -3.0, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "목표": 20.0, "보유": 40, "비중": 0.20, "종목수": 4}
_느 = {"볼": -0.8, "낙": -5.0, "시총": 5e11}
미국 = ("NVDA", "AMAT", "LRCX", "SOXX", "KLAC", "WDC", "MU", "ASML")
_YH = os.path.join(O._DATA, "yahoo")
컷들 = ("2019", "2020", "2021", "2022")
판정 = []


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종, 원시 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

    def 재무값(code, d8):
        줄 = 재무.get(code)
        if not 줄:
            return None
        m = None
        for 적용, v in 줄:
            if 적용 <= d8:
                m = v
            else:
                break
        return m

    # ── 후보를 **가장 느슨하게** 한 번만 모은다 ──
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= _느["시총"]:
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > _느["볼"] or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > _느["낙"]:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            g = 하루갭.get(code)
            결과, 청산 = None, None
            for h in range(0, 새판["보유"] + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + 새판["목표"] / 100):
                    결과, 청산 = 새판["목표"] - _비용, j
                    break
            if 결과 is None:
                j = i + 1 + 새판["보유"]
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            사건.append({"인": i + 1, "날": 다음, "code": code, "결과": 결과,
                         "청산": 청산, "원시": o0, "대금": b0[2],
                         "볼": 볼, "낙": 낙, "시총": 시총,
                         "갭": g, "중앙": 시갭,
                         "상갭": (g - 시갭) if g is not None else None})
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    print(f"  느슨한 후보 {len(사건):,}건 · {len(묶):,}일\n", flush=True)

    # ⚠️ `상갭함=후보속` 을 넘기면 **좁힌 뒤 그 안에서** 중앙갭을 낸다.
    #    (전에는 `후보식`이 좁히기 전 전체 중앙값을 미리 계산했다)
    후보속 = object()

    def 시뮬(p, 목록=None, 상갭함=None, 시작년=None, 끝년=None,
             시드=_시드, 좁힘=None):
        상갭함 = 상갭함 or (lambda x: x["상갭"] if x["상갭"] is not None else 99)
        원천 = 묶 if 목록 is None else 목록
        시작i = 시i
        if 시작년:
            c2 = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = c2[0] if c2 else 시i
        현금, 보유, 곡, 산 = float(시드), [], [], 0
        for i in range(시작i, len(날)):
            if 끝년 and 날[i][:4] > 끝년:
                break
            남 = []
            for q in 보유:
                if q["청산"] <= i:
                    현금 += q["주수"] * q["원시"] * (1 + q["결과"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
            칸 = 원천.get(i) or []
            # ⚠️⚠️ **좁히기 전에 08:00에 아는 조건을 먼저 다 건다** (2026-09-04 고침)
            #    처음엔 안 걸고 좁혀서, 후보 40개 안에 **시총 2천억 넘는 종목**이
            #    자리를 차지했다 -> 원판의 -52%라는 **틀린 값**이 나왔다.
            #    실전에서 브리핑은 **시총·볼린저·20일낙폭을 통과한 것만** 준다
            if 좁힘:
                앞 = [x for x in 칸
                      if x["볼"] <= p["볼"] and x["낙"] <= p["낙"]
                      and x["시총"] < p["시총"]]
                칸 = sorted(앞, key=lambda z: z["낙"])[:좁힘]
            # ⚠️⚠️ **좁힌 뒤 그 안에서 중앙갭을 낸다** (2026-09-07 고침).
            #    전에는 `후보식`이 **좁히기 전 느슨한 후보 전부**의 중앙값을 썼다.
            #    실전은 08:00에 40개로 좁혀 브리핑에 싣고 08:50에 **그 40개만** 본다.
            #    그래서 과대평가였다 — 우리 규칙 +30.82% -> 실제 +25.8%
            _식 = 상갭함
            if 상갭함 is 후보속:
                _벌 = [x["갭"] for x in 칸 if x["갭"] is not None]
                if len(_벌) < 3:
                    곡.append(평)
                    continue
                _중 = st.median(_벌)

                def _식(x, _m=_중):
                    return (x["갭"] - _m) if x["갭"] is not None else 99
            골 = [x for x in 칸
                  if x["볼"] <= p["볼"] and x["낙"] <= p["낙"]
                  and x["시총"] < p["시총"] and _식(x) <= p["갭"]]
            for x in sorted(골, key=_식)[:p["종목수"]]:
                쓸 = min(평 * p["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({**x, "주수": 주수})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        c = ((끝 / 시드) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        return {"끝": 끝, "연": c, "낙": 낙, "산": 산}

    def 표(r, 라, 폭=30):
        print(f"    {라:<{폭}}{r['끝']:>15,.0f}원{r['연']:>+9.2f}%"
              f"{r['낙']:>8.1f}%{r['산']:>7}건")

    머 = (f"    {'전략':<30}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")

    # ══ A 시총 2천억 · 하루 4종목 ══
    print("  ══ A **① 시총 2천억 · 하루 4종목** (98·94b차 1차 결과) ══")
    print(머)
    옛 = 시뮬(옛판)
    새 = 시뮬(새판)
    표(옛, "옛판 (3천억 · 2종목)")
    표(새, "새판 (2천억 · 4종목)")
    print(f"\n    ── 검증 ① 앞뒤 분할 (뒤 기간) ──")
    print(f"    {'분할':<12}{'옛판':>12}{'새판':>12}{'옛 낙폭':>10}{'새 낙폭':>10}")
    A뒤옛, A뒤새 = [], []
    for 컷 in 컷들:
        a = 시뮬(옛판, 시작년=str(int(컷) + 1))
        b = 시뮬(새판, 시작년=str(int(컷) + 1))
        A뒤옛.append(a["연"])
        A뒤새.append(b["연"])
        print(f"    {컷}이후{'':<5}{a['연']:>+11.1f}%{b['연']:>+11.1f}%"
              f"{a['낙']:>9.1f}%{b['낙']:>9.1f}%")
    print(f"    평균{'':<8}{st.mean(A뒤옛):>+11.1f}%{st.mean(A뒤새):>+11.1f}%")
    print(f"\n    ── 검증 ② 2025·26 제외 ──")
    옛2 = 시뮬(옛판, 끝년="2024")
    새2 = 시뮬(새판, 끝년="2024")
    표(옛2, "옛판")
    표(새2, "새판")
    print(f"\n    ── 검증 ③ 무작위 문턱 300개 대비 (2025·26 제외) ──")
    random.seed(20260904)
    격 = {"갭": (-2.0, -2.5, -3.0, -4.0, -5.0),
          "볼": (-0.8, -1.0, -1.2), "낙": (-5.0, -10.0, -15.0, -20.0),
          "시총": (1e11, 2e11, 3e11, 5e11), "비중": (0.15, 0.20, 0.25),
          "종목수": (1, 2, 3, 4)}
    분포 = []
    for _ in range(300):
        q = dict(새판)
        for k2, v2 in 격.items():
            q[k2] = random.choice(v2)
        분포.append(시뮬(q, 끝년="2024")["끝"])
    분포.sort()

    def 위(v):
        return 100 - sum(1 for x in 분포 if x < v) / len(분포) * 100
    print(f"     무작위 300개  최악 {분포[0]:,.0f}원 · "
          f"중앙 {분포[len(분포)//2]:,.0f}원 · 최고 {분포[-1]:,.0f}원 · "
          f"흑자 {sum(1 for x in 분포 if x > _시드)}/300")
    print(f"     옛판 상위 {위(옛2['끝']):.0f}% · **새판 상위 {위(새2['끝']):.0f}%**")
    A합 = (min(A뒤새) > 0 and 새2["끝"] >= 옛2["끝"]
           and 위(새2["끝"]) <= 25 and abs(새["낙"]) <= abs(옛["낙"]) * 1.3)
    판정.append(("① 시총 2천억 · 하루 4종목", A합,
                 f"뒤기간 최악 {min(A뒤새):+.1f}% · "
                 f"25·26제외 {새2['끝']/옛2['끝']*100-100:+.1f}% · "
                 f"상위 {위(새2['끝']):.0f}% · 낙폭 {새['낙']:.1f}%"))

    # ══ B 보조 전략 ══
    print(f"\n  ══ B **② 보조 전략 (하이닉스 20일)** (100b차 1차 결과) ══")
    쓸 = {}
    for 심 in 미국:
        p2 = os.path.join(_YH, 심 + ".json")
        if not os.path.exists(p2):
            continue
        종 = json.load(io.open(p2, encoding="utf-8-sig")).get("종가") or {}
        k = sorted(종)
        e = {}
        for j in range(1, len(k)):
            pv = 종[k[j - 1]]
            if pv:
                e[k[j]] = (종[k[j]] / pv - 1) * 100
        쓸[심] = (e, sorted(e))
    신호일 = set()
    for d in 날:
        if d < _시작:
            continue
        for 심, (e, ks) in 쓸.items():
            j = bisect.bisect_left(ks, d)
            if j == 0:
                continue
            전 = ks[j - 1]
            try:
                if (dt.datetime.strptime(d, "%Y%m%d")
                        - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                    continue
            except Exception:
                pass
            if e[전] <= -2:
                신호일.add(d)
                break
    하 = {d: 주가[d]["000660"][0] for d in 날 if 주가[d].get("000660")}

    def 보조시뮬(날들, 보유일=20, 시드=50_000_000.0, 시작년=None, 끝년=None):
        골 = set(날들)
        현금, 보유, 곡, 산 = 시드, [], [], 0
        시작i = 시i
        if 시작년:
            c2 = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = c2[0] if c2 else 시i
        for i in range(시작i, len(날)):
            d = 날[i]
            if 끝년 and d[:4] > 끝년:
                break
            남 = []
            for q in 보유:
                if q["끝"] <= i:
                    현금 += q["금"] * (1 + q["r"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(q["금"] for q in 보유)
            if d in 골 and not 보유:
                j = i + 보유일 - 1
                b = (비.get(d) or {}).get("000660")
                v0, v1 = 하.get(d), 하.get(날[j]) if j < len(날) else None
                if b and v0 and v1:
                    금 = min(현금 * 0.5, 평 * 0.5)
                    if 금 > 1000:
                        현금 -= 금
                        보유.append({"금": 금, "끝": j,
                                     "r": (v1 / (v0 * b[0]) - 1) * 100 - _비용})
                        산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["금"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        c = ((끝 / 시드) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        return {"끝": 끝, "연": c, "낙": 낙, "산": 산}

    쓸날 = [d for d in 날 if d >= _시작]
    실제 = 보조시뮬(sorted(신호일))
    늘 = 보조시뮬(쓸날)
    print(머)
    표(실제, f"보조 (신호 {len(신호일)}일)")
    표(늘, "⚠️ 늘 들고 있기")
    print(f"\n    ── 검증 ① 앞뒤 분할 (뒤 기간) ──")
    B뒤 = []
    print(f"    {'분할':<12}{'보조':>12}{'늘 들기':>12}{'낙폭':>10}")
    for 컷 in 컷들:
        a = 보조시뮬(sorted(신호일), 시작년=str(int(컷) + 1))
        b = 보조시뮬(쓸날, 시작년=str(int(컷) + 1))
        B뒤.append(a["연"])
        print(f"    {컷}이후{'':<5}{a['연']:>+11.1f}%{b['연']:>+11.1f}%"
              f"{a['낙']:>9.1f}%")
    print(f"    평균{'':<8}{st.mean(B뒤):>+11.1f}%")
    print(f"\n    ── 검증 ② 2025·26 제외 ──")
    실2 = 보조시뮬(sorted(신호일), 끝년="2024")
    늘2 = 보조시뮬(쓸날, 끝년="2024")
    표(실2, "보조")
    표(늘2, "⚠️ 늘 들고 있기")
    print(f"\n    ── 검증 ③ 무작위 날짜 300번 (2025·26 제외) ──")
    분포2 = []
    for _ in range(300):
        분포2.append(보조시뮬(random.sample(쓸날, len(신호일)),
                              끝년="2024")["끝"])
    분포2.sort()
    이 = sum(1 for x in 분포2 if x >= 실2["끝"])
    print(f"     무작위 중앙 {분포2[len(분포2)//2]:,.0f}원 · "
          f"최고 {분포2[-1]:,.0f}원")
    print(f"     실제 {실2['끝']:,.0f}원  →  **p = {이/300:.4f}**")
    B합 = (min(B뒤) > 0 and 실2["끝"] > 늘2["끝"] and 이 / 300 < 0.05)
    판정.append(("② 보조 전략 (하이닉스 20일)", B합,
                 f"뒤기간 최악 {min(B뒤):+.1f}% · "
                 f"늘들기 대비 {실2['끝']/max(1,늘2['끝'])*100-100:+.0f}% · "
                 f"p={이/300:.4f} · 낙폭 {실제['낙']:.1f}%"))

    # ══ C 실전 절차 ══
    print(f"\n  ══ C **④ 실전 절차** (101·102·103차 1차 결과) ══")
    print("     08:00에 후보 N개로 좁히고, 09:00에 **후보들 갭 중앙값** 기준으로 산다")
    후중 = {}
    for i, 칸 in 묶.items():
        벌 = [x["갭"] for x in 칸 if x["갭"] is not None]
        if len(벌) >= 3:
            후중[i] = st.median(벌)
    후보식 = (lambda x: (x["갭"] - 후중[x["인"]])
              if (x["갭"] is not None and x["인"] in 후중) else 99)
    print(머)
    표(새, "기준: 전 종목 중앙갭 · 안 좁힘")
    for N in (10, 20, 40, None):
        for 식, 라2 in ((None, "전종목중앙갭"), (후보속, "후보중앙갭")):
            r = 시뮬(새판, 상갭함=식, 좁힘=N)
            표(r, f"후보 {N or '전부'}개 · {라2}")
    print(f"\n    ── 2025·26 제외 ──")
    print(머)
    표(새2, "기준: 전 종목 중앙갭 · 안 좁힘")
    C뒤 = None
    for N in (20, 40):
        for 식, 라2 in ((None, "전종목중앙갭"), (후보속, "후보중앙갭")):
            r = 시뮬(새판, 상갭함=식, 좁힘=N, 끝년="2024")
            표(r, f"후보 {N}개 · {라2}")
            if N == 40 and 식 is 후보속:
                C뒤 = r
    print(f"\n    ── 검증 ① 앞뒤 분할 (후보 40개 · 후보중앙갭) ──")
    C값 = []
    for 컷 in 컷들:
        r = 시뮬(새판, 상갭함=후보속, 좁힘=40, 시작년=str(int(컷) + 1))
        C값.append(r["연"])
        print(f"    {컷}이후  {r['연']:+.1f}%  낙폭 {r['낙']:.1f}%")
    # ── ⭐ 상대갭 문턱 훑기 — **「조건 없음」까지** (2026-09-04 신설) ──
    #    ⚠️ 왜: 2026-09-04에 후보 4개가 **전부 올랐는데**(평균 +4.66%)
    #       상대갭 조건이 넷 다 걸러서 **아무것도 안 샀다.**
    #       격자에는 갭 -2/-3/-4/-5 만 있고 **「조건 없음」이 없다.** 한 번도 안 재봤다
    #    ⇒ 「후보를 그냥 사면?」을 여기서 잰다. +99 는 사실상 조건 없음이다
    #    ⚠️ 조건을 **없애는** 쪽이라 지금까지 아홉 번 진 「조건 더하기」와 반대 방향이다.
    #       그래서 더 재볼 값어치가 있다
    print(f"\n    ── ⭐ 상대갭 문턱 훑기 (후보 40개 · 후보중앙갭) ──")
    print(머)
    for gv in (99.0, 0.0, -1.0, -2.0, -2.5, -3.0, -3.5, -4.0, -5.0):
        p2 = dict(새판)
        p2["갭"] = gv
        라 = "갭 조건 **없음**" if gv >= 90 else f"상대갭 {gv:+.1f}%p 이하"
        표(시뮬(p2, 상갭함=후보속, 좁힘=40), 라)
    print(f"\n    ⚠️ 2025·26 제외")
    for gv in (99.0, 0.0, -2.0, -3.0, -3.5, -4.0, -5.0):
        p2 = dict(새판)
        p2["갭"] = gv
        라 = "갭 조건 **없음**" if gv >= 90 else f"상대갭 {gv:+.1f}%p 이하"
        표(시뮬(p2, 상갭함=후보속, 좁힘=40, 끝년="2024"), 라)

    # ── ⭐⭐ 예상체결가 **오차 시뮬** (2026-09-07 신설) ──
    #    ⚠️ 왜: 백테스트는 **실제 시가**로 갭을 재는데 실전은 **08:50 예상체결가**로 잰다.
    #       그 차이 때문에 실전 문턱을 -3.0 대신 **-3.5**로 뒀다 (101차).
    #       그런데 **그 오차를 한 번도 안 재봤다.** 여유가 적정한지 과한지 모른다
    #    ⇒ 갭에 오차를 일부러 섞고 문턱별로 견준다.
    #       오차가 크면 -3.5 같은 **여유 있는 문턱이 유리**해야 한다.
    #       그렇지 않다면 여유는 **그냥 손해**다
    #    ⚠️ 씨앗을 고정한다. 안 그러면 돌릴 때마다 순위가 바뀐다
    print(f"\n    ── ⭐⭐ 예상체결가 오차 시뮬 (후보 40개 · 후보중앙갭) ──")
    print("       08:50 예상체결가가 실제 시가와 ±얼마나 어긋나는지 모른다.")
    print("       그래서 **일부러 오차를 넣고** 문턱별 성적을 본다")
    print(머)
    for 폭 in (0.0, 0.3, 0.5, 1.0, 2.0):
        if 폭:
            print(f"\n    ── 오차 ±{폭:.1f}%p (정규분포, 표준편차) ──")
        else:
            print(f"\n    ── 오차 없음 (지금 백테스트) ──")
        for gv in (-2.5, -3.0, -3.5, -4.0):
            _rng = random.Random(20260907)

            def _상갭(x, _p=폭, _r=_rng):
                v = 후보식(x)
                if v >= 99 or not _p:      # 값이 없으면 오차도 안 더한다
                    return v
                return v + _r.gauss(0, _p)

            p3 = dict(새판)
            p3["갭"] = gv
            표(시뮬(p3, 상갭함=_상갭, 좁힘=40),
              f"상대갭 {gv:+.1f}%p 이하")

    # ── 계좌 낙폭을 **파일로 내보낸다** (2026-09-04 신설) ──
    #    ⚠️ 왜: 브리핑에는 「가장 나빴던 거래 -36.1%」만 있었다. 그건 **한 종목**이다.
    #       자산의 20%씩만 넣으니 **계좌**는 그만큼 안 빠진다. 읽는 사람은
    #       「내 돈이 36% 날아간다」로 읽는데, 정작 결정에 필요한
    #       **계좌 낙폭**은 어디에도 없었다
    #    ⚠️ **여기서 내보내는 이유**: build_rule_cases.py 는 거래 단위 통계만 낸다.
    #       거기에 자본 시뮬을 새로 만들면 숫자가 두 벌이 되어 갈라진다.
    #       **이미 제대로 재는 여기**서 내보내고 브리핑은 읽기만 한다
    try:
        _분할 = [{"시작": 컷, "연": round(시뮬(
            새판, 상갭함=후보속, 좁힘=40, 시작년=str(int(컷) + 1))["연"], 1),
            "낙폭": round(시뮬(
                새판, 상갭함=후보속, 좁힘=40,
                시작년=str(int(컷) + 1))["낙"], 1)} for 컷 in 컷들]
        _낙들 = [x["낙폭"] for x in _분할] + (
            [round(C뒤["낙"], 1)] if C뒤 else [])
        _몫 = {
            "만든날": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "출처": "verify_all.py 검증 ① (후보 40개 · 후보중앙갭)",
            "시작자산": _시드,
            "연평균": round(C뒤["연"], 2) if C뒤 else None,
            "계좌낙폭": round(C뒤["낙"], 1) if C뒤 else None,
            "최악낙폭": min(_낙들) if _낙들 else None,
            "분할": _분할,
        }
        _p = os.path.join(os.path.dirname(O._DATA), "data", "rule-capital.json")
        io.open(_p, "w", encoding="utf-8").write(
            json.dumps(_몫, ensure_ascii=False, indent=1))
        print(f"\n    → 계좌 낙폭을 {os.path.basename(_p)} 에 남겼다 "
              f"(연 {_몫['연평균']}% · 낙폭 {_몫['계좌낙폭']}% · "
              f"최악 {_몫['최악낙폭']}%)")
    except Exception as e:
        print(f"\n    ⚠️ 계좌 낙폭 내보내기 실패: {type(e).__name__} {e}")

    C합 = (C뒤 is not None and min(C값) > 0
           and C뒤["끝"] >= 새2["끝"] * 0.7)
    판정.append(("④ 실전 절차 (후보 40개 + 후보중앙갭)", C합,
                 f"뒤기간 최악 {min(C값):+.1f}% · "
                 f"원판 대비 {C뒤['끝']/새2['끝']*100-100:+.0f}%"
                 if C뒤 else "못 잼"))

    # ══ D 최종 판정 ══
    print(f"\n{'='*78}")
    print("  ══ D **최종 판정** ══")
    print(f"{'='*78}")
    for 이름, ok, 설 in 판정:
        print(f"  {'✅ 검증됨' if ok else '⚠️ 조건부'}  {이름}")
        print(f"            {설}")
    print(f"\n  ⚠️ ③ 증자·감자는 자료가 75%뿐이라 여기서 안 걸었다.")
    print(f"     내일(09-05 00:10) 나머지 988종목을 받고 따로 잰다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
