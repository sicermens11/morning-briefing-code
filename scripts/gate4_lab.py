#!/usr/bin/env python3
r"""
gate4_lab.py — **147차 · 「시장이 빠진 날엔 덜 빠진 것도 산다」에 4관문** (2026-09-08)

## 무엇을 검증하나
```
지금    20일 낙폭이 -10% 넘게 빠진 것만 산다 (언제나)
바꿈    시장(코스닥)이 20일에 -10% 넘게 빠진 날에는 **-5%만 빠져도 산다**
        그 밖의 날에는 그대로 -10%
```
142차 B절 결과 — **두 기간 다 이겼다**:
```
              끝 자산    낙폭    산 것   돈÷낙폭
지금          6,432만  -3.3%   103건    8.50
전체 기간     7,331만  -3.2%   104건   **9.11**  (+14%)
2025·26 제외  4,353만  -3.2%    75건   **8.69**  (+6%)
```
⭐ 낙폭이 안 나빠지고 돈이 늘었다. 스물다섯 번 기각 중 **매수 쪽에서 처음** 나온 것

## 왜 말이 되나 (사후 설명이 아니라 앞선 근거)
```
140·145차: **시장 낙폭**이 스물여덟 지표 중 가장 셌다
           시장이 크게 빠진 날 산 것은 40일 뒤 +24.4%, 안 빠진 날은 -0.4%
⇒ 시장이 통째로 빠질 땐 -5%만 빠져도 이미 싸다.
  평소엔 -10%를 요구해야 하지만, 그때는 문턱을 낮춰도 된다
```

## 관문
```
A 앞뒤 분할   시작년을 2015·2019·2021 로 옮겨도 이기나
B 연도별      해마다 몇 승 몇 패
C 무작위 대조  **아무 날에나 문턱을 낮추면** 어떻게 되나 200번
             — 「시장이 빠진 날」이라는 게 정말 값어치가 있나를 가른다
D 오차 시뮬    08:50 예상체결가 오차 ±0.3 / 0.5 / 1.0%p
E 문턱 자리    -5 / -8 / -12 · 시장 문턱 -5 / -10 / -15
```
⚠️ 넷 다 통과해야 규칙을 바꾼다

쓰는 법:
    python scripts\gate4_lab.py
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
            # ⚠️⚠️ **여기서 문턱을 걸지 않는다** — 격자로 훑을 것이기 때문이다.
            #    수집에서 미리 걸면 문턱 아홉 가지가 전부 같은 값이 된다
            #    (09-04에 실제로 당했다). 느슨하게 모으고 **시뮬에서 거른다**
            if 볼 > 0.5 or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > 0:
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
    # ══ 지수 붙이기 ══ (2026-09-07 신설)
    print("  지수 읽는 중...", flush=True)
    지수 = {}          # 날짜 -> {지수이름: 종가}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        하루 = {}
        for 이름2, v2 in (d2.get("지수") or {}).items():
            try:
                하루[이름2] = float(str(v2.get("종가")).replace(",", ""))
            except (TypeError, ValueError, AttributeError):
                pass
        if 하루:
            지수[d2.get("기준일") or os.path.basename(f)[:8]] = 하루
    print(f"    지수 {len(지수):,}일", flush=True)

    def 지수계열(이름2):
        """날 순서대로 늘어놓은 종가 (없는 날은 None)"""
        return [(지수.get(d) or {}).get(이름2) for d in 날]

    _계열캐시 = {}

    def 낙폭(이름2, i2, n=20):
        """i2 자리에서 n일 전 대비 몇 % 인가"""
        sq = _계열캐시.get(이름2)
        if sq is None:
            sq = 지수계열(이름2)
            _계열캐시[이름2] = sq
        if i2 < n or i2 >= len(sq):
            return None
        a, b = sq[i2 - n], sq[i2]
        if not a or not b:
            return None
        return (b / a - 1) * 100

    def 변동성(이름2, i2, n=20):
        sq = _계열캐시.get(이름2)
        if sq is None:
            sq = 지수계열(이름2)
            _계열캐시[이름2] = sq
        if i2 < n or i2 >= len(sq):
            return None
        칸 = [x for x in sq[i2 - n:i2 + 1] if x]
        if len(칸) < n * 0.8:
            return None
        일간 = [(칸[j] / 칸[j - 1] - 1) * 100 for j in range(1, len(칸))
                if 칸[j - 1]]
        return st.pstdev(일간) if len(일간) > 3 else None

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

    def 시뮬2(c, 고른날):
        c2 = dict(c)
        c2["무작위날"] = 고른날
        return 시뮬(c2)

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
            # ── 오늘 국면에 따라 **문턱을 정한다** (142차) ──
            시낙오늘 = 낙폭("코스닥", i)

            def _사다리(키, 기본, 시낙오늘=None):
                사 = c.get(키)
                if not 사 or 시낙오늘 is None:
                    return 기본
                for 문턱, 값 in 사:
                    if 시낙오늘 <= 문턱:
                        return 값
                return 기본

            # ⚠️ 무작위 대조: 「시장이 빠진 날」 대신 **아무 날이나** 고른 것
            무 = c.get("무작위날")
            if 무 is not None:
                낙문턱 = -5 if i in 무 else -10
                볼문턱 = c["볼린저"]
                갭문턱 = c["상대갭"]
            else:
                볼문턱 = _사다리("볼사다리", c["볼린저"], 시낙오늘)
                낙문턱 = _사다리("낙사다리", c["낙폭20"], 시낙오늘)
                갭문턱 = _사다리("갭사다리", c["상대갭"], 시낙오늘)

            칸 = [x for x in (묶.get(i) or [])
                  if c["시총하한"] <= x["시총억"] < c["시총상한"]
                  and x["볼린저"] <= 볼문턱
                  and x["낙폭20"] <= 낙문턱
                  and x["대금억"] >= c["대금하한"]
                  and x["거래량"] >= c["거래량하한"]
                  and x["회전율"] >= c["회전율하한"]]
            # ⚠️ 수급 거름은 **40개로 좁히기 전**에 건다.
            #    수급은 전날 자료라 08:00에 이미 알 수 있기 때문이다
            거름 = c.get("거름")
            if 거름:
                칸 = [x for x in 칸 if 거름(x)]
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
                if v3 <= 갭문턱:
                    잰.append((v3, x))
            # ⚠️ 기본은 **갭이 큰 순**이다. 고르기가 있으면 그 순서로 바꾼다.
            #    문턱(상대갭 -3.5%p)은 그대로라 **후보 수는 안 변한다**
            고르기 = c.get("고르기")
            if 고르기:
                골 = sorted([z[1] for z in 잰], key=고르기)
            else:
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

    import random as _rnd

    기본틀 = dict(확정)
    기본틀["나눔"] = ((0.5, 15, 40), (0.5, 40, 90))
    기본틀["시총하한"], 기본틀["시총상한"] = 500, 2000
    기본틀["볼린저"], 기본틀["낙폭20"], 기본틀["상대갭"] = -1.0, -10, -3.5
    기본틀["대금하한"] = 1.0

    도전 = dict(기본틀)
    도전["낙사다리"] = [(-10, -5), (999, -10)]

    def 끝자산(r):
        return (r or {}).get("끝") or 0.0

    print("=" * 100)
    print("  147차 · 「시장이 -10%↓ 빠진 날엔 -5%만 빠져도 산다」 4관문")
    print("=" * 100)

    # ── A 앞뒤 분할 ──
    print("\n" + "=" * 100)
    print("  A 앞뒤 분할")
    print("=" * 100)
    print(머)
    for 시작년, 라 in ((None, "전체 (2011~)"), ("2015", "2015~"),
                       ("2019", "2019~"), ("2021", "2021~")):
        기 = 시뮬(기본틀, 시작년=시작년)
        표(기, f"[{라}] 지금")
        표(시뮬(도전, 시작년=시작년), f"[{라}] **국면별 낙폭**", 기)
        print("")

    # ── B 연도별 ──
    print("=" * 100)
    print("  B 연도별")
    print("=" * 100)
    이김, 짐, 같 = 0, 0, 0
    print(f"  {'해':<8}{'지금':>16}{'국면별':>18}{'차이':>10}")
    for y in range(2011, 2027):
        a = 끝자산(시뮬(기본틀, 시작년=str(y), 끝년=str(y)))
        b = 끝자산(시뮬(도전, 시작년=str(y), 끝년=str(y)))
        if not a or not b:
            continue
        차 = (b / a - 1) * 100
        if 차 > 0.01:
            이김 += 1
        elif 차 < -0.01:
            짐 += 1
        else:
            같 += 1
        print(f"  {y:<8}{a:>16,.0f}{b:>18,.0f}{차:>9.1f}%")
    print(f"\n  ⇒ **{이김}승 {짐}패 {같}무**")

    # ── C 무작위 대조 ──
    print("\n" + "=" * 100)
    print("  C ⭐ 무작위 대조 — **아무 날에나** 문턱을 낮추면?")
    print("     (같은 날 수만큼 무작위로 골라 낙폭 문턱을 -5로 낮춘다)")
    print("=" * 100)
    낙칸 = [(i2, 낙폭("코스닥", i2)) for i2 in range(260, len(날))]
    빠진날 = {i2 for i2, v in 낙칸 if v is not None and v <= -10}
    전체날 = [i2 for i2, v in 낙칸 if v is not None]
    print(f"    시장이 -10%↓ 빠진 날 {len(빠진날):,}일 / 전체 {len(전체날):,}일 "
          f"({len(빠진날)/max(len(전체날),1)*100:.1f}%)")
    분포 = []
    for s in range(200):
        _r = _rnd.Random(5000 + s)
        고른날 = set(_r.sample(전체날, min(len(빠진날), len(전체날))))
        c = dict(기본틀)
        c["무작위날"] = 고른날
        c["낙사다리"] = None
        분포.append(끝자산(시뮬2(c, 고른날)))
        if (s + 1) % 50 == 0:
            print(f"    {s+1}/200 돌림", flush=True)
    분포 = [v for v in 분포 if v]
    분포.sort()
    나 = 끝자산(시뮬(도전))
    기본값 = 끝자산(시뮬(기본틀))
    위 = sum(1 for v in 분포 if v < 나)
    print(f"\n  무작위 {len(분포)}번 — 가장 나쁨 {분포[0]:,.0f} · "
          f"중앙 {분포[len(분포)//2]:,.0f} · 가장 좋음 {분포[-1]:,.0f}")
    print(f"  지금 (문턱 안 낮춤)  {기본값:>14,.0f}")
    print(f"  **시장이 빠진 날에만 낮춤**  {나:>14,.0f}  → 상위 "
          f"{(1-위/max(len(분포),1))*100:.0f}%")
    print(f"  ⇒ 상위 25% 안에 "
          f"{'**든다** ✅' if (1-위/max(len(분포),1)) <= 0.25 else '못 든다 ❌'}")

    # ── D 오차 시뮬 ──
    print("\n" + "=" * 100)
    print("  D 오차 시뮬")
    print("=" * 100)
    print(머)
    for 오차 in (0.0, 0.3, 0.5, 1.0):
        기 = 시뮬(기본틀, 오차=오차)
        표(기, f"오차 ±{오차}%p · 지금")
        표(시뮬(도전, 오차=오차), f"오차 ±{오차}%p · **국면별 낙폭**", 기)
        print("")

    # ── E 문턱 자리 ──
    print("=" * 100)
    print("  E 문턱을 조금 옮겨도 버티나 (한 자리에서만 좋으면 과적합이다)")
    print("=" * 100)
    print(머)
    기 = 시뮬(기본틀)
    표(기, "지금")
    for 시장문턱 in (-5, -10, -15):
        for 느슨 in (-3, -5, -8):
            c = dict(기본틀)
            c["낙사다리"] = [(시장문턱, 느슨), (999, -10)]
            표(시뮬(c), f"시장 {시장문턱}%↓ → 낙폭 {느슨}%", 기)
    print("")

    print("=" * 96)
    print("  읽는 법")
    print("    - 기준보다 끝 자산이 크고 낙폭이 안 나빠져야 바꾼다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("    - 기준보다 **끝 자산이 크고 낙폭이 안 나빠져야** 쓸 값어치가 있다")
    print("    - **산 것 수가 기준과 비슷해야** 제대로 견준 것이다")
    print("      (거르기가 아니라 고르기라 후보 수는 안 변한다)")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
