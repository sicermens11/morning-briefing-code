#!/usr/bin/env python3
r"""
sim2_lab.py — **비중을 자산 비례로 바꿔 다시 굴린다** (2026-09-02 · 54차)

⚠️⚠️ **53차에서 드러난 구조적 문제.**
```
신호 연 66건 × 보유 40일/245일 = 동시 보유 평균 **10.8개**
종목당 10만원 → 실제 투자금 **약 108만원**
3,000만원 중 **3.6%만 쓰고 나머지는 현금으로 논다**
⇒ 개별 거래가 +18.10%(승률 82.5%)여도 **전체 자산은 연 −0.1%**
```
⇒ **「10만원씩」은 자금이 작을 때의 규칙이다.** 자산 비례로 바꿔 다시 본다.

## 재는 것
```
비중 방식   ① 10만원 고정(53차)  ② 자산의 5% · 10% · 20%씩  ③ 자산÷(동시보유 목표수)
등급       최우선(상대−4%p↓) · 최우선+권고(−2%p↓)
매도       D+20 · D+40
초기자금    1,000만 · 3,000만
```
⚠️ **투입 비율**을 같이 찍는다 — 자산의 몇 %가 실제로 주식에 들어가 있었나.
   이게 낮으면 「신호가 드물어 자금이 논다」는 뜻이고, 신호를 더 찾아야 한다.
⚠️ 수익률 기반 회계(53차에서 두 번 버그를 고친 방식). 비용 0.26% · 손절 없음.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.0026


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    갭표, 시장갭, 원가 = {}, {}, {}
    앞종 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루, 원 = {}, {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            원[c] = (종, 시)
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        원가[d8] = 원
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
    print(f"  거래일 {len(날):,}", flush=True)

    뽑날 = {}
    총 = 0
    for i, d1 in enumerate(날):
        if i < 260 or i + 61 >= len(날):
            continue
        다음 = 날[i + 1]
        시갭 = 시장갭.get(다음)
        if 시갭 is None or 시갭 >= -0.3:
            continue
        하루갭 = 갭표.get(다음) or {}
        묶 = []
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0:
                continue
            if k < 20 or sq[k - 20] <= 0 or (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -2:
                continue
            묶.append((g - 시갭, 대금, code))
            총 += 1
        if 묶:
            묶.sort()
            뽑날[i + 1] = 묶
        if i % 900 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {총:,}", flush=True)
    년수 = (len(날) - 261) / 245
    print(f"  사건 {총:,}건 · 연 {총/년수:.0f}건", flush=True)

    def 수정단가(j, code, 시가여부=True):
        o, sv = 원가.get(날[j], {}).get(code), 주가.get(날[j], {}).get(code)
        if not o or not sv or o[0] <= 0:
            return None
        배 = sv[0] / o[0]
        return (o[1] * 배) if 시가여부 else sv[0]

    def 시뮬(초기, 방식, 보유일, 문턱, 하루최대=5):
        현금 = float(초기)
        보유 = []      # (청산j, code, 투자금, 수매수)
        곡선, 투입비 = [], []
        이긴 = 진 = 산 = 못 = 0
        for j in range(261, len(날)):
            남 = []
            for (끝j, code, 투자금, 수매수) in 보유:
                if j >= 끝j:
                    수팔 = 수정단가(j, code, True) or 수매수
                    받 = 투자금 * (수팔 / 수매수) * (1 - _비용 / 2)
                    현금 += 받
                    이긴 += 1 if 수팔 > 수매수 else 0
                    진 += 1 if 수팔 <= 수매수 else 0
                else:
                    남.append((끝j, code, 투자금, 수매수))
            보유 = 남
            평가 = 0.0
            for (_, code, 투자금, 수매수) in 보유:
                수now = 수정단가(j, code, False) or 수매수
                평가 += 투자금 * (수now / 수매수)
            총자산 = 현금 + 평가
            if j in 뽑날 and 총자산 > 0:
                든 = {c for (_, c, _, _) in 보유}
                오늘 = 0
                for 상대, 대금, code in 뽑날[j]:
                    if 상대 > 문턱 or 오늘 >= 하루최대 or code in 든:
                        continue
                    수매수 = 수정단가(j, code, True)
                    o = 원가.get(날[j], {}).get(code)
                    if not 수매수 or 수매수 <= 0 or not o or o[1] <= 0:
                        continue
                    if 방식 == "10만원":
                        투자금 = max(1, int(100_000 // o[1])) * o[1]
                    else:
                        투자금 = 총자산 * float(방식.rstrip("%")) / 100
                    투자금 *= (1 + _비용 / 2)
                    if 투자금 > 현금 or 투자금 <= 0:
                        못 += 1
                        continue
                    현금 -= 투자금
                    보유.append((j + 보유일, code, 투자금, 수매수))
                    든.add(code)
                    산 += 1
                    오늘 += 1
            평가2 = 0.0
            for (_, code, 투자금, 수매수) in 보유:
                수now = 수정단가(j, code, False) or 수매수
                평가2 += 투자금 * (수now / 수매수)
            자산 = 현금 + 평가2
            곡선.append(자산)
            투입비.append(평가2 / 자산 * 100 if 자산 > 0 else 0)
        for (_, code, 투자금, 수매수) in 보유:
            수팔 = 수정단가(len(날) - 1, code, False) or 수매수
            현금 += 투자금 * (수팔 / 수매수) * (1 - _비용 / 2)
        최고, 낙 = 곡선[0] if 곡선 else 1, 0.0
        for x in 곡선:
            최고 = max(최고, x)
            낙 = min(낙, x / 최고 - 1)
        거 = 이긴 + 진
        return (현금, 낙 * 100, (이긴 / 거 * 100 if 거 else 0), 산, 못,
                st.mean(투입비) if 투입비 else 0, 곡선)

    있 = [d for d in 날[261:] if 지수.get(d)]
    지연 = ((지수[있[-1]]["KOSPI"] / 지수[있[0]]["KOSPI"]) ** (1 / 년수) - 1) * 100
    print(f"\n  ══ 비중 방식 × 등급 × 매도 (초기 3,000만 · 하루 5개) ══")
    print(f"     기간 {날[261][:4]}~{날[-1][:4]} ({년수:.1f}년) · 코스피 연 {지연:+.1f}%")
    print(f"    {'등급':<12}{'비중':<9}{'매도':<7}{'최종자산':>15}{'배수':>7}"
          f"{'연환산':>9}{'낙폭':>8}{'투입비':>8}{'매수':>7}{'승률':>7}{'못산':>7}")
    최선 = None
    for 라, 문턱 in (("최우선", -4), ("최우선+권고", -2)):
        for 방식 in ("10만원", "5%", "10%", "20%"):
            for 보유일 in (20, 40):
                자산, 낙, 승, 산, 못, 투입, 곡선 = 시뮬(30_000_000, 방식, 보유일, 문턱)
                배수 = 자산 / 30_000_000
                연 = (배수 ** (1 / 년수) - 1) * 100 if 배수 > 0 else -100
                표 = "⭐" if 연 > 지연 else "  "
                print(f"    {라:<12}{방식:<9}{'D+'+str(보유일):<7}{자산:>14,.0f}원"
                      f"{배수:>7.2f}{연:>8.1f}%{낙:>7.1f}%{투입:>7.1f}%"
                      f"{산:>7,}{승:>6.0f}%{못:>7,}{표}")
                if 최선 is None or 연 > 최선[0]:
                    최선 = (연, 라, 방식, 보유일, 곡선)

    # ⚠️ 여러 조합의 연도별을 다 찍는다 — **한 해 편중**을 오늘 세 번 당했다
    #    (20차 2020년 · 37차 2025년 · 54차 2013년)
    print(f"\n  ══ ⚠️ **한 해 편중 검사** — 가장 좋은 해를 빼면 어떻게 되나 ══")
    for 라, 문턱, 방식, 보유일 in (("최우선", -4, "10%", 40),
                                   ("최우선", -4, "20%", 40),
                                   ("최우선+권고", -2, "10%", 40),
                                   ("최우선+권고", -2, "20%", 40)):
        _, _, _, _, _, _, 곡선2 = 시뮬(30_000_000, 방식, 보유일, 문턱)
        해별2, 앞v2 = {}, None
        for j2, d in enumerate(날[261:261 + len(곡선2)]):
            y = d[:4]
            if y not in 해별2:
                해별2[y] = [앞v2 if 앞v2 is not None else 곡선2[j2], 곡선2[j2]]
            해별2[y][1] = 곡선2[j2]
            앞v2 = 곡선2[j2]
        수들 = []
        for y in sorted(해별2):
            a0, a1 = 해별2[y]
            수들.append((y, (a1 / a0 - 1) * 100 if a0 else 0))
        플2 = sum(1 for _, x in 수들 if x > 0)
        최고해 = max(수들, key=lambda x: x[1])
        남 = [x for x in 수들 if x[0] != 최고해[0]]
        곱 = 1.0
        for _, x in 남:
            곱 *= (1 + x / 100)
        연없 = (곱 ** (1 / max(1, len(남))) - 1) * 100
        곱전 = 1.0
        for _, x in 수들:
            곱전 *= (1 + x / 100)
        연전 = (곱전 ** (1 / max(1, len(수들))) - 1) * 100
        print(f"\n  ── {라} · {방식} · D+{보유일} ──")
        print("    " + " · ".join(f"{y[2:]} {x:+.0f}" for y, x in 수들))
        print(f"    {len(수들)}해 중 {플2}해 수익 ({플2/len(수들)*100:.0f}%) · "
              f"연평균 {연전:+.1f}%")
        print(f"    ⚠️ **가장 좋은 해({최고해[0]} {최고해[1]:+.0f}%)를 빼면 "
              f"연평균 {연없:+.1f}%** ({연없-연전:+.1f}%p)")

    if 최선:
        print(f"\n  ══ 연도별 상세 (「{최선[1]}」 · {최선[2]} · D+{최선[3]}) ══")
        곡선 = 최선[4]
        해별, 앞v = {}, None
        for j, d in enumerate(날[261:261 + len(곡선)]):
            y = d[:4]
            if y not in 해별:
                해별[y] = [앞v if 앞v is not None else 곡선[j], 곡선[j]]
            해별[y][1] = 곡선[j]
            앞v = 곡선[j]
        지해, 앞x = {}, None
        for d in 날[261:]:
            x = (지수.get(d) or {}).get("KOSPI")
            if not x:
                continue
            y = d[:4]
            if y not in 지해:
                지해[y] = [앞x if 앞x else x, x]
            지해[y][1] = x
            앞x = x
        print(f"    {'해':<7}{'자산':>15}{'수익률':>10}{'코스피':>10}{'차이':>10}")
        플, 전 = 0, 0
        for y in sorted(해별):
            a0, a1 = 해별[y]
            수 = (a1 / a0 - 1) * 100 if a0 else 0
            지 = ((지해[y][1] / 지해[y][0] - 1) * 100) if y in 지해 and 지해[y][0] else 0
            전 += 1
            플 += 1 if 수 > 0 else 0
            표 = "⭐" if 수 > 지 else ("  " if 수 > 0 else "❌")
            print(f"    {y:<7}{a1:>14,.0f}원{수:>+9.1f}%{지:>+9.1f}%{수-지:>+9.1f}%{표}")
        print(f"    ⇒ **{전}해 중 {플}해 수익 ({플/전*100:.0f}%)**")

    print("\n  읽는 법")
    print("    - **'투입비'가 핵심이다** — 자산의 몇 %가 실제로 주식에 들어가 있었나")
    print("      낮으면 신호가 드물어 자금이 노는 것이다 → 신호를 더 찾아야 한다")
    print("    - '10만원'과 '20%'를 견주면 **비중 규칙이 얼마나 중요한지** 나온다")
    print("    - ⚠️ 비중을 키우면 낙폭도 커진다. 수익만 보지 않는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
