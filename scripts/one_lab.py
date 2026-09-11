#!/usr/bin/env python3
r"""
one_lab.py — **148차 · 하나로 다 팔까, 나눠 팔까** (2026-09-08 신설)

## 사용자 지적
```
「신호별 매도 타이밍은 지금이 최선이라는 결론이야? +40일?」
```
**「최선」은 돈÷낙폭 기준이었고 끝 자산으로는 아니었다.** 146차 표를 다시 보면:
```
매도 방식                  끝 자산    낙폭   돈÷낙폭
+15% / 40일             4,454만  -5.3%   4.43
**+40% / 90일 하나로**   **8,263만** -11.9%  2.59  ← 끝 자산 1위
반 +15%/40 · 반 +40%/90  6,432만  -3.3%  **8.50** ← 돈÷낙폭 1위
```

## 그리고 이건 **안 재본 자리**였다
```
124차  나눠팔기를 채택할 때 견준 것 = 「+20%/40일 **하나**」(5,433만)
       「+40%/90일 하나」와는 **안 견줬다**
139차  900칸 격자를 훑었는데 **비율이 0.4/0.5/0.6뿐**이라
       「하나로 다 파는 것」(비율 1.0)이 **격자에 없었다**
```
146차에서 우연히 드러났다. **매도 격자에 구멍이 있었다**

## 그리고 앞 몫 40일도 의심스럽다
145차: 우리가 쓰는 **20일 낙폭 신호는 90일까지 계속 커진다**
```
20일 낙폭  5일 -2.01 → 20일 -11.95 → 40일 -16.77 → 90일 **-24.85**
```
⇒ 오래 들고 있을수록 좋은 신호인데 앞 몫을 40일에 자르는 게 맞나?

## 재는 것
```
A 하나로 다 팔기      목표 10~60% × 기한 20~120일  (격자)
B 나눔 비율 전 구간    0.0 · 0.2 · 0.4 · 0.5 · 0.6 · 0.8 · 1.0
C 앞 몫 기한을 늘리면   40 → 60 · 90 · 120일
D 둘 다 보여준다       **돈÷낙폭 1등**(안전)과 **끝 자산 1등**(공격)
```
⚠️ 어느 쪽을 고를지는 **낙폭을 얼마나 견디느냐**의 문제다.
   내가 정하지 않고 나란히 놓는다

쓰는 법:
    python scripts\one_lab.py
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_시드 = 5_000_000.0
_후보수 = 40
확정 = {"잉여금": 30, "부채": 80, "흑자필수": True, "상대갭": -3.5,
        "볼린저": -1.0, "낙폭20": -10, "목표": 20, "최대보유": 40,
        "비중": 0.20, "하루상한": 4,
        "시총하한": 500, "시총상한": 2000, "대금하한": 1.0, "거래량하한": 0,
        "회전율하한": 0.0}


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    _사라짐 = O.사라진종목(주가, 날)   # ⚠️ 상장폐지를 손실로 센다
    print(f"  중간에 사라진 종목 {len(_사라짐):,}개 — 상장폐지는 {O.폐지손실:.0f}% 손실로 센다", flush=True)
    # ⚠️ 짧은 한글 이름 덮어쓰기로 하루에 다섯 번 당했다 — 훑기 전에 못 박는다
    assert isinstance(날, list) and len(날) > 1000, ('거래일 목록이 깨졌다', len(날))
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 앞종, 원시, 거량 = {}, {}, {}, {}, {}
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
                량 = float(v.get("거래량") or 0)
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            거량.setdefault(d8, {})[c] = 량
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루

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

    print("  후보 모으는 중 (크기 조건도 느슨하게)...", flush=True)
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            # ⚠️ **크기 조건을 여기서 걸지 않는다** — 훑을 대상이기 때문이다.
            #    아주 작은 것(100억)과 아주 큰 것(50조)만 잘라 낸다
            if 시총 < 1e10 or 시총 >= 5e13:
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 확정["잉여금"]
                    and fm.get("부채비율", 9e9) <= 확정["부채"]
                    and fm.get("흑자") == 1.0):
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
            if 볼 > 확정["볼린저"] or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > 확정["낙폭20"]:
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
            량 = (거량.get(d1) or {}).get(code) or 0
            사건.append({
                "인": i + 1, "code": code, "원시": o0, "대금": b0[2],
                "볼린저": 볼, "낙폭20": 낙,
                "시총억": 시총 / 1e8, "대금억": 대금 / 1e8, "거래량": 량,
                "회전율": (대금 / 시총 * 100) if 시총 > 0 else 0,
                "갭": g, "매수": 매수})
    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  후보 {len(사건):,}건 · {len(묶):,}일\n", flush=True)

    캐시 = {}

    def 결과(x, 목표, 보유, 상태=None):
        """상태: None(기한) · "20일선"(종가가 20일선 위) · "볼0"(볼린저 0 위)

        ⚠️ 목표가에 먼저 닿으면 그걸로 판다. 상태는 **기한 대신** 쓰는 것이다
        """
        키 = (x["인"], x["code"], 목표, 보유, 상태)
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
            # ⭐ 상태 청산 — 날짜가 아니라 **회복됐을 때** 판다
            if 상태 and h >= 1:
                kk2 = (자리.get(x["code"]) or {}).get(날[j])
                if kk2 is not None and kk2 >= 20:
                    sq2 = 종계[x["code"]]
                    m20 = st.mean(sq2[kk2 - 19:kk2 + 1])
                    회복 = False
                    if 상태 == "20일선":
                        회복 = sq2[kk2] > m20
                    else:
                        sd2 = st.pstdev(sq2[kk2 - 19:kk2 + 1]) or 1e-9
                        회복 = (sq2[kk2] - m20) / (2 * sd2) > 0
                    if 회복:
                        r, 청 = (vv[0] / x["매수"] - 1) * 100 - _비용, j
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

    def 시뮬(c, 끝년=None, 시드=None, 시작년=None, 오차=0.0):
        import random as _r2
        _rng = _r2.Random(20260907)
        시드 = 시드 or _시드
        시작i = 시i
        if 시작년:
            _a = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = _a[0] if _a else 시i
        현금, 보유, 곡, 산 = 시드, [], [], 0
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
                  if c["시총하한"] <= x["시총억"] < c["시총상한"]
                  and x["대금억"] >= c["대금하한"]
                  and x["거래량"] >= c["거래량하한"]
                  and x["회전율"] >= c["회전율하한"]]
            칸 = sorted(칸, key=lambda z: z["낙폭20"])[:_후보수]
            if len(칸) < 3:
                곡.append(평)
                continue
            중 = st.median([x["갭"] for x in 칸])
            잰 = []
            for x in 칸:
                v3 = x["갭"] - 중
                if 오차:
                    v3 += _rng.gauss(0, 오차)
                if v3 <= c["상대갭"]:
                    잰.append((v3, x))
            골 = [z[1] for z in sorted(잰, key=lambda z: z[0])]
            for x in 골[:c["하루상한"]]:
                # ⚠️ 나눔이 있으면 **주수를 쪼개** 두 몫으로 만든다.
                #    한 종목에 들어가는 총액은 같다 (자산 20%)
                몫들 = c.get("나눔") or ((1.0, c["목표"], c["최대보유"]),)
                쓸 = min(평 * c["비중"], 현금, x["대금"] * 0.01)
                총주수 = int(쓸 // x["원시"])
                if 총주수 < len(몫들) or 총주수 * x["원시"] > 현금:
                    continue
                넣음 = False
                for 몫 in 몫들:
                    비율, 목표b, 보유b = 몫[0], 몫[1], 몫[2]
                    상태b = 몫[3] if len(몫) > 3 else None
                    r, 청 = 결과(x, 목표b, 보유b, 상태b)
                    if r is None:
                        continue
                    주수 = int(총주수 * 비율)
                    if 주수 < 1 or 주수 * x["원시"] > 현금:
                        continue
                    현금 -= 주수 * x["원시"]
                    보유.append({"주수": 주수, "원시": x["원시"],
                                 "결과": r, "청산": 청})
                    넣음 = True
                if 넣음:
                    산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        해 = max(len(곡) / 245, 0.1)
        연 = ((끝 / 시드) ** (1 / 해) - 1) * 100 if 끝 > 0 else -100
        최고, 낙 = 시드, 0.0
        for v in 곡:
            최고 = max(최고, v)
            낙 = min(낙, v / 최고 - 1)
        return {"끝": 끝, "연": 연, "낙": 낙 * 100, "산": 산}

    머 = f"    {'':<28}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}"

    def 표(r, 라, 기=None):
        점 = r["연"] / max(abs(r["낙"]), 3.0)
        꼬 = ""
        if 기:
            늘 = (r["끝"] / 기["끝"] - 1) * 100
            꼬 = f"  ({늘:+.0f}%)"
        print(f"    {라:<28}{r['끝']:>15,.0f}원{r['연']:>+8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}{점:>9.2f}{꼬}", flush=True)

    지금틀 = dict(확정)
    지금틀["나눔"] = ((0.5, 15, 40), (0.5, 40, 90))
    # ⭐ 147차 채택분을 깔고 간다
    지금틀["낙사다리"] = [(-10, -5), (999, -10)] \
        if "낙사다리" in str(확정) or True else None

    머2 = (f"  {'매도 방식':<38}{'끝 자산':>15}{'연평균':>9}"
           f"{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}")

    def 줄(라, 몫들):
        c = dict(지금틀)
        c["나눔"] = 몫들
        r = 시뮬(c)
        점 = r["연"] / max(abs(r["낙"]), 3.0)
        print(f"  {라:<38}{r['끝']:>15,.0f}{r['연']:>8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}{점:>9.2f}")
        return (점, r["끝"], 라, 몫들, r)

    모음 = []
    print("=" * 100)
    print("  148차 · 하나로 다 팔까, 나눠 팔까")
    print("=" * 100)
    print("\n  ── 지금 ──")
    print(머2)
    모음.append(줄("반 +15%/40일 · 반 +40%/90일 (지금)",
                   ((0.5, 15, 40), (0.5, 40, 90))))

    print("\n  ── A 하나로 다 팔기 ──")
    print(머2)
    for 목표 in (10, 15, 20, 25, 30, 40, 50, 60):
        for 기한 in (20, 40, 60, 90, 120):
            모음.append(줄(f"+{목표}% / {기한}일 하나로", ((1.0, 목표, 기한),)))

    print("\n  ── B 나눔 비율 전 구간 (+15%/40일 : +40%/90일) ──")
    print(머2)
    for 앞 in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0):
        if 앞 == 0.0:
            모음.append(줄("0:100 (= +40%/90일 하나)", ((1.0, 40, 90),)))
        elif 앞 == 1.0:
            모음.append(줄("100:0 (= +15%/40일 하나)", ((1.0, 15, 40),)))
        else:
            모음.append(줄(f"{int(앞*100)}:{int((1-앞)*100)}",
                           ((앞, 15, 40), (1 - 앞, 40, 90))))

    print("\n  ── C 앞 몫 기한을 늘리면 ──")
    print(머2)
    for 앞기한 in (40, 60, 90, 120):
        모음.append(줄(f"반 +15%/{앞기한}일 · 반 +40%/120일",
                       ((0.5, 15, 앞기한), (0.5, 40, 120))))
    for 앞목표 in (20, 25, 30):
        모음.append(줄(f"반 +{앞목표}%/60일 · 반 +40%/120일",
                       ((0.5, 앞목표, 60), (0.5, 40, 120))))

    print("\n" + "=" * 100)
    print("  D 두 잣대로 나란히")
    print("=" * 100)
    print("\n  ── 돈÷낙폭 1등 다섯 (안전 쪽) ──")
    print(머2)
    for 점, 끝, 라, 몫, r in sorted(모음, key=lambda z: -z[0])[:5]:
        print(f"  {라:<38}{r['끝']:>15,.0f}{r['연']:>8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}{점:>9.2f}")
    print("\n  ── 끝 자산 1등 다섯 (공격 쪽) ──")
    print(머2)
    for 점, 끝, 라, 몫, r in sorted(모음, key=lambda z: -z[1])[:5]:
        print(f"  {라:<38}{r['끝']:>15,.0f}{r['연']:>8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}{점:>9.2f}")

    print("\n" + "=" * 100)
    print("  ── 위 다섯을 2025·26 제외로 다시 ──")
    print("=" * 100)
    print(머2)
    본것 = set()
    for 점, 끝, 라, 몫, r in (sorted(모음, key=lambda z: -z[0])[:3]
                              + sorted(모음, key=lambda z: -z[1])[:3]):
        if 라 in 본것:
            continue
        본것.add(라)
        c = dict(지금틀)
        c["나눔"] = 몫
        r2 = 시뮬(c, 끝년="2024")
        점2 = r2["연"] / max(abs(r2["낙"]), 3.0)
        print(f"  {라:<38}{r2['끝']:>15,.0f}{r2['연']:>8.2f}%"
              f"{r2['낙']:>7.1f}%{r2['산']:>7}{점2:>9.2f}")

    print("\n" + "=" * 100)
    print("  읽는 법")
    print("    - **어느 쪽을 고를지는 낙폭을 얼마나 견디느냐**의 문제다")
    print("    - 끝 자산이 크면 낙폭도 크다. 공짜는 없다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("=" * 100)

    print("=" * 96)
    print("  읽는 법")
    print("    - 기준보다 끝 자산이 크고 낙폭이 안 나빠져야 바꾼다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("    - 지금(15%+40%)보다 **끝 자산이 크고 낙폭이 안 나빠져야** 바꾼다")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
