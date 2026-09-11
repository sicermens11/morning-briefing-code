#!/usr/bin/env python3
r"""
gate_lab.py — **후보 조합에 4관문 + 오차 시뮬을 건다** (2026-09-07 신설)

## 왜
```
2026-09-07 crosscheck_lab 에서 나온 것:
  실전 절차(후보중앙갭)로 재면 **AutoSearch 8위 조합이 1등**이고
  우리 확정 규칙보다 **58% 낫다** (8,729만 vs 5,509만, 낙폭도 -6% vs -9%)
그런데 그건 **288,560개 중 상위를 고른 것**이라 우연일 수 있다
⇒ 여기서 **4관문 + 오차 시뮬**을 걸어 진짜인지 본다
```

## 4관문 (104차와 같은 기준)
```
① 앞뒤 분할     ~2019·~2020·~2021·~2022 뒤 기간이 **다 흑자**
② 2025·26 제외  빼고도 무너지지 않는다
③ 무작위 대비   무작위 문턱 300개 분포에서 **상위 25% 안**
④ 낙폭         원판보다 크게 나빠지지 않는다 (1.3배 이내)
```
## 오차 시뮬
```
08:50 예상체결가는 실제 시가와 어긋난다. 그 크기를 아직 모른다.
⇒ 갭에 ±0.3/0.5/1.0%p 오차를 넣고도 버티는지 본다
```
⚠️ **모든 계산은 「후보 40개로 좁힌 뒤 그 안의 중앙갭」**이다 (실전 절차).

쓰는 법:
    python scripts\gate_lab.py
저장: `data/_labs/<날짜>_관문.txt` (직접 리디렉션)
"""
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
_후보수 = 40
컷들 = ("2019", "2020", "2021", "2022")

우리 = {"이름": "우리 확정 규칙",
        "잉여금": 30, "부채": 80, "흑자필수": True, "상대갭": -3,
        "볼린저": -1.0, "낙폭20": -10, "시총상한": 2000, "목표": 20,
        "최대보유": 40, "비중": 0.20, "하루상한": 4, "시장갭조건": None}
도전 = {"이름": "B 1위 (AutoSearch 8위)",
        "잉여금": 20, "부채": 100, "흑자필수": True, "상대갭": -3,
        "볼린저": -1.0, "낙폭20": -5, "시총상한": 1000, "목표": 20,
        "최대보유": 40, "비중": 0.25, "하루상한": 4, "시장갭조건": None}


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    _사라짐 = O.사라진종목(주가, 날)   # ⚠️ 상장폐지를 손실로 센다
    print(f"  중간에 사라진 종목 {len(_사라짐):,}개 — 상장폐지는 {O.폐지손실:.0f}% 손실로 센다", flush=True)
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

    print("  후보 모으는 중 (갭 조건 없이)...", flush=True)
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        if 시장갭.get(다음) is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 5e11:
                continue
            fm = 재무값(code, d1)
            if not fm:
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
            if 볼 > -0.7 or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > -5:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            g = 하루갭.get(code)
            if not b0 or not v0 or not o0 or g is None:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            사건.append({
                "인": i + 1, "code": code, "원시": o0, "대금": b0[2],
                "볼린저": 볼, "낙폭20": 낙, "시총": 시총 / 1e8, "갭": g,
                "시장갭": 시장갭[다음], "매수": 매수,
                "잉여금": fm.get("잉여금비율"), "부채": fm.get("부채비율"),
                "흑자": fm.get("흑자")})
    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  후보 {len(사건):,}건 · {len(묶):,}일\n", flush=True)

    캐시 = {}

    def 결과(x, 목표, 보유):
        키 = (x["인"], x["code"], 목표, 보유)
        if 키 in 캐시:
            return 캐시[키]
        i = x["인"] - 1
        r, 청 = None, None
        for h in range(0, 보유 + 1):
            j = i + 1 + h
            if j >= len(날):
                break
            vv = 주가[날[j]].get(x["code"])
            b2 = (비.get(날[j]) or {}).get(x["code"])
            if not vv or not b2:
                break
            if vv[0] * b2[1] >= x["매수"] * (1 + 목표 / 100):
                r, 청 = 목표 - _비용, j
                break
        if r is None:
            j = i + 1 + 보유
            끝 = 주가[날[j]].get(x["code"]) if j < len(날) else None
            # ⚠️⚠️ **상장폐지를 손실로 센다** (2026-09-08 고침).
            #    전에는 자료가 없으면 그 거래를 **지웠다** —
            #    913종목(25%)이 중간에 사라졌고 성적이 부풀려졌다
            if not 끝 and x["code"] in _사라짐:
                캐시[키] = (O.폐지손실 - _비용, min(j, len(날) - 1))
                return 캐시[키]
            if not 끝:
                캐시[키] = (None, None)
                return 캐시[키]
            r, 청 = (끝[0] / x["매수"] - 1) * 100 - _비용, j
        캐시[키] = (r, 청)
        return 캐시[키]

    def 시뮬(c, 시작년=None, 끝년=None, 오차=0.0, 씨=20260907):
        rng = random.Random(씨)
        시작i = 시i
        if 시작년:
            a = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = a[0] if a else 시i
        현금, 보유, 곡, 산 = _시드, [], [], 0
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
            칸 = [x for x in (묶.get(i) or [])
                  if (x["잉여금"] or -9e9) >= c["잉여금"]
                  and (x["부채"] or 9e9) <= c["부채"]
                  and (not c["흑자필수"] or x["흑자"] == 1.0)
                  and x["볼린저"] <= c["볼린저"]
                  and x["낙폭20"] <= c["낙폭20"]
                  and x["시총"] < c["시총상한"]]
            if c.get("시장갭조건") is not None:
                칸 = [x for x in 칸 if x["시장갭"] < c["시장갭조건"]]
            # ⚠️ **좁힌 뒤 그 안에서** 중앙갭 (08:50에 보이는 것이 이것뿐)
            칸 = sorted(칸, key=lambda z: z["낙폭20"])[:_후보수]
            if len(칸) < 3:
                곡.append(평)
                continue
            중 = st.median([x["갭"] for x in 칸])
            잰 = []
            for x in 칸:
                v = x["갭"] - 중
                if 오차:
                    v += rng.gauss(0, 오차)
                if v <= c["상대갭"]:
                    잰.append((v, x))
            for _, x in sorted(잰, key=lambda z: z[0])[:c["하루상한"]]:
                r, 청 = 결과(x, c["목표"], c["최대보유"])
                if r is None:
                    continue
                쓸 = min(평 * c["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({"주수": 주수, "원시": x["원시"],
                             "결과": r, "청산": 청})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        해 = max(len(곡) / 245, 0.1)
        연 = ((끝 / _시드) ** (1 / 해) - 1) * 100 if 끝 > 0 else -100
        최고, 낙 = _시드, 0.0
        for v in 곡:
            최고 = max(최고, v)
            낙 = min(낙, v / 최고 - 1)
        return {"끝": 끝, "연": 연, "낙": 낙 * 100, "산": 산}

    머 = f"    {'':<34}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}"

    def 표(r, 라):
        print(f"    {라:<34}{r['끝']:>15,.0f}원{r['연']:>+8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}", flush=True)

    판정표 = []
    for c in (우리, 도전):
        이 = c["이름"]
        print("=" * 84)
        print(f"  ══ {이} ══")
        print(f"     잉{c['잉여금']}부{c['부채']}{'흑' if c['흑자필수'] else ''} "
              f"갭{c['상대갭']}볼{c['볼린저']}낙{c['낙폭20']} 시총{c['시총상한']} "
              f"목표{c['목표']}보유{c['최대보유']} {int(c['비중']*100)}%x{c['하루상한']}")
        print("=" * 84)
        print(머)
        원 = 시뮬(c)
        표(원, "원판 (전체 기간)")
        제 = 시뮬(c, 끝년="2024")
        표(제, "2025·26 제외")

        print(f"\n    ── ① 앞뒤 분할 (뒤 기간) ──")
        분 = []
        for 컷 in 컷들:
            r = 시뮬(c, 시작년=str(int(컷) + 1))
            분.append(r)
            print(f"    {컷}이후  {r['연']:+.1f}%  낙폭 {r['낙']:.1f}%")
        관1 = all(r["연"] > 0 for r in 분)
        관2 = 제["연"] > 0

        print(f"\n    ── ③ 무작위 문턱 300개 대비 (2025·26 제외) ──", flush=True)
        random.seed(20260907)
        격 = {"상대갭": (-2.0, -2.5, -3.0, -4.0, -5.0),
              "볼린저": (-0.8, -1.0, -1.2),
              "낙폭20": (-5.0, -10.0, -15.0, -20.0),
              "시총상한": (1000, 2000, 3000, 5000),
              "비중": (0.15, 0.20, 0.25), "하루상한": (1, 2, 3, 4)}
        분포 = []
        for _ in range(300):
            q = dict(c)
            for k, v in 격.items():
                q[k] = random.choice(v)
            분포.append(시뮬(q, 끝년="2024")["끝"])
        분포.sort()
        위 = sum(1 for v in 분포 if v > 제["끝"]) / len(분포) * 100
        흑 = sum(1 for v in 분포 if v > _시드)
        print(f"     무작위 300개  최악 {분포[0]:,.0f}원 · "
              f"중앙 {분포[150]:,.0f}원 · 최고 {분포[-1]:,.0f}원 · 흑자 {흑}/300")
        print(f"     **상위 {위:.0f}%**")
        관3 = 위 <= 25
        # ④ 낙폭 — 우리 규칙의 낙폭 1.3배 이내여야 한다 (우리 자신은 기준이라 통과)
        if c is 우리:
            기준낙 = abs(원["낙"])
            우리["_기준낙"] = 기준낙
            관4 = True
        else:
            관4 = abs(원["낙"]) <= 우리.get("_기준낙", 99) * 1.3

        print(f"\n    ── ⭐ 오차 시뮬 (08:50 예상체결가 오차) ──")
        print(머)
        오결 = {}
        for 폭 in (0.0, 0.3, 0.5, 1.0):
            r = 시뮬(c, 오차=폭)
            오결[폭] = r
            표(r, "오차 없음" if not 폭 else f"오차 ±{폭:.1f}%p")
        견딤 = all(오결[p]["끝"] > _시드 * 3 for p in (0.3, 0.5, 1.0))

        판정표.append((이, 원, 제, 관1, 관2, 관3, 관4, 견딤, 오결))
        print()

    print("=" * 84)
    print("  ══ 최종 판정 ══")
    print("=" * 84)
    print(f"  {'':<24}{'①앞뒤':>7}{'②제외':>7}{'③무작위':>8}{'④낙폭':>7}"
          f"{'오차견딤':>9}{'전체연':>9}{'낙폭':>7}")
    for 이, 원, 제, k1, k2, k3, k4, 견, 오 in 판정표:
        print(f"  {이:<24}{'✅' if k1 else '❌':>7}{'✅' if k2 else '❌':>7}"
              f"{'✅' if k3 else '❌':>8}{'✅' if k4 else '❌':>7}"
              f"{'✅' if 견 else '❌':>9}{원['연']:>+8.1f}%{원['낙']:>6.1f}%")
    print("\n  읽는 법")
    print("    - 넷을 다 넘고 **오차에도 버텨야** 규칙을 바꿀 값어치가 있다")
    print("    - 오차 견딤 = ±0.3/0.5/1.0%p 에서 모두 자산 3배 이상")
    return 0


if __name__ == "__main__":
    sys.exit(main())
