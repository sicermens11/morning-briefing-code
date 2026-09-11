#!/usr/bin/env python3
r"""
rebound_lab.py — **149차 · 급등 뒤 되돌림을 가려낸다** (2026-09-08 신설)

## 사용자 지적 (아이크래프트)
```
「7월말에 급상승하다가 하락이던 중이었는데, 애초에 규칙에 안 맞는 거 아니야?」
```
확인해보니 **규칙에는 맞았다.** 그런데 흐름이 전혀 달랐다:
```
20260626   2,340원   저점
20260819   8,010원   고점 (**+242%**)
20260903   4,550원   추천 기준일 (고점 대비 -43%)

20일 낙폭  -20.3%   ✅ 통과 (문턱 -10%)
볼린저     -1.03σ   ✅ 통과 (문턱 -1.0)
재무       잉여금 95.6% · 부채 77.8% · 흑자   ✅ 전부 통과
60일 낙폭  **+61.6%**  ← 두 달 전보다 여전히 62% 높다
```
⇒ 우리 규칙은 **20일만 본다.** 그래서 전혀 다른 둘을 같은 걸로 본다:
```
사려던 것   꾸준하던 종목이 **이유 없이** 빠진 것
실제로 산 것 **3배 급등한 뒤** 되돌리는 것
```

## 재는 것
```
① 세기      지금 후보·매수 중 **급등 되돌림이 몇 건인가**
            (거르기 전에 세야 한다 — 안 그러면 후보가 줄어 좋아 보이는 걸 못 가른다)
② 60일 낙폭  0% 이하 · -5% 이하 · -10% 이하를 **함께** 요구하면
③ 고점 대비  최근 60일 고점 대비 -40%/-50% 넘게 빠진 것을 **빼면**
④ 60일선     60일선 아래인 것만 사면  (145차: 「60일선 대비」가 -18.06으로 셌다)
⑤ 반대       급등 되돌림**만** 사면 (그게 오히려 좋을 수도 있다)
```
⚠️ 조건을 더하는 계열은 스물여섯 번 중 대부분이 졌다.
   다만 이건 **「빠졌다」의 정의를 고치는 것**이라 성격이 다르다

쓰는 법:
    python scripts\rebound_lab.py
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
            # ── 60일 지표 (149차) ──
            낙60, 선60, 고대비 = None, None, None
            if kk >= 60:
                if sq[kk - 60] > 0:
                    낙60 = (c1 / sq[kk - 60] - 1) * 100
                s60 = st.mean(sq[kk - 59:kk + 1])
                if s60 > 0:
                    선60 = (c1 / s60 - 1) * 100
                고 = max(sq[kk - 59:kk + 1])
                if 고 > 0:
                    고대비 = (c1 / 고 - 1) * 100
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
                "갭": g, "매수": 매수,
                "낙폭60": 낙60, "60일선": 선60, "고점대비": 고대비})
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

    기본틀 = dict(확정)
    기본틀["나눔"] = ((0.5, 15, 40), (0.5, 40, 90))
    기본틀["시총하한"], 기본틀["시총상한"] = 500, 2000
    기본틀["볼린저"], 기본틀["낙폭20"], 기본틀["상대갭"] = -1.0, -10, -3.5
    기본틀["대금하한"] = 1.0
    # ⭐ 147차 채택분을 깔고 간다
    기본틀["낙사다리"] = [(-10, -5), (999, -10)]

    def 있(x, k):
        return x.get(k) is not None

    # ── ① 먼저 센다 ──
    후보들 = [x for x in 사건
              if 500 <= x["시총억"] < 2000 and x["대금억"] >= 1.0
              and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10]
    print("=" * 100)
    print("  149차 · 급등 뒤 되돌림을 가려낸다")
    print("=" * 100)
    print(f"\n  ① 먼저 센다 — 우리 후보 {len(후보들):,}건 중")
    for 라, fn in (
            ("60일 낙폭이 **플러스** (두 달 전보다 높다)",
             lambda x: 있(x, "낙폭60") and x["낙폭60"] > 0),
            ("60일 낙폭 +30% 넘음 (크게 올라 있다)",
             lambda x: 있(x, "낙폭60") and x["낙폭60"] > 30),
            ("60일선 **위**에 있다",
             lambda x: 있(x, "60일선") and x["60일선"] > 0),
            ("60일 고점 대비 -40% 넘게 빠짐",
             lambda x: 있(x, "고점대비") and x["고점대비"] < -40),
            ("60일 고점 대비 -50% 넘게 빠짐",
             lambda x: 있(x, "고점대비") and x["고점대비"] < -50)):
        n = sum(1 for x in 후보들 if fn(x))
        print(f"     {라:<44}{n:>7,}건 ({n/max(len(후보들),1)*100:>5.1f}%)")

    갈래 = [
        ("── ② 60일 낙폭도 함께 요구하면 ──", None),
        ("60일 낙폭 0% 이하", lambda x: 있(x, "낙폭60") and x["낙폭60"] <= 0),
        ("60일 낙폭 -5% 이하", lambda x: 있(x, "낙폭60") and x["낙폭60"] <= -5),
        ("60일 낙폭 -10% 이하", lambda x: 있(x, "낙폭60") and x["낙폭60"] <= -10),
        ("── ③ 급등 되돌림을 빼면 ──", None),
        ("60일 낙폭 +30% 넘는 것 제외",
         lambda x: not (있(x, "낙폭60") and x["낙폭60"] > 30)),
        ("고점 대비 -40% 넘게 빠진 것 제외",
         lambda x: not (있(x, "고점대비") and x["고점대비"] < -40)),
        ("고점 대비 -50% 넘게 빠진 것 제외",
         lambda x: not (있(x, "고점대비") and x["고점대비"] < -50)),
        ("── ④ 60일선 ──", None),
        ("60일선 **아래**만", lambda x: 있(x, "60일선") and x["60일선"] < 0),
        ("60일선 -10% 아래만", lambda x: 있(x, "60일선") and x["60일선"] < -10),
        ("── ⑤ 반대로 — 급등 되돌림**만** 사면 ──", None),
        ("60일 낙폭 +30% 넘는 것만",
         lambda x: 있(x, "낙폭60") and x["낙폭60"] > 30),
        ("고점 대비 -40% 넘게 빠진 것만",
         lambda x: 있(x, "고점대비") and x["고점대비"] < -40),
        ("60일선 위에 있는 것만",
         lambda x: 있(x, "60일선") and x["60일선"] > 0),
    ]

    for 끝년, 라 in ((None, "전체 기간"), ("2024", "2025·26 제외")):
        print("\n" + "=" * 100)
        print("  == " + 라 + " ==   (147차 채택분을 깔고)")
        print("=" * 100)
        print(머)
        기 = 시뮬(기본틀, 끝년=끝년)
        표(기, "지금 (60일은 안 본다)")
        for 이름, fn in 갈래:
            if fn is None:
                print("")
                print("    " + 이름)
                continue
            n2 = sum(1 for x in 후보들 if fn(x))
            if n2 < 500:
                print(f"    {이름:<38}후보 {n2:>6,}건 — **표본 부족**")
                continue
            c2 = dict(기본틀)
            c2["거름"] = fn
            표(시뮬(c2, 끝년=끝년), f"{이름} [{n2:,}건]", 기)
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
