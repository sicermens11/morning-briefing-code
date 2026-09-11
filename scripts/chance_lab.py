#!/usr/bin/env python3
r"""
chance_lab.py — **153차 · 기회를 늘린다** (2026-09-08 신설)

## 사용자 지적 둘
```
①「1년에 10번만 산다고? 너무 적어. 매수 기회 포착이 아니라 **불포착**이야」
②「기대 수익률을 계산해서 **그보다 조금 낮은 지점**을 매도 시점으로 하면?」
③「조금 비싸게 사는 대신 기회를 잡는 게 훨씬 나아. **수익 극대화가 아니어도 된다**」
```

## 왜 ②가 ①의 답이 되나
```
지금    모든 종목에 **같은 목표**(+15%/+40%)를 건다
        30% 빠진 종목과 12% 빠진 종목의 되돌림 여지가 같을 리 없다
바꾸면  그 종목이 기대할 만한 만큼보다 **조금 낮게** 걸면 더 자주 닿는다
        -> 빨리 팔리면 **그 돈이 다시 일한다**
143차:  현금이 **79.6%** 놀고 있었다. 47일씩 들고 있는 게 이유다
        회전이 빨라지면 **기회가 저절로 는다**
```

## 재는 것
```
A ⭐ 기회 표     설정마다 「1년에 몇 번 사나 · 낙폭이 얼마인가」를 나란히
                -> 보고 **어디까지 견딜지 고르실 수 있게**
B 종목별 목표    목표 = **그 종목 낙폭 x 비율** (0.3 / 0.5 / 0.7 / 1.0)
                예) 30% 빠진 종목에 비율 0.5 -> 목표 +15%
                    12% 빠진 종목에 비율 0.5 -> 목표 +6%
C 변동성 기반    목표 = 그 종목 20일 변동성 x k
D 둘을 섞기      기회를 늘리는 설정 + 종목별 목표
```
⚠️ 잣대를 바꾼다. 지금까지 **돈÷낙폭 하나**로 줄 세웠는데,
   여기서는 **기회 수**를 앞에 놓고 낙폭을 나란히 보여준다

쓰는 법:
    python scripts\chance_lab.py
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
            # 20일 일간 변동성(%) — 종목별 목표에 쓴다
            _일 = [(sq[j2] / sq[j2 - 1] - 1) * 100
                   for j2 in range(kk - 19, kk + 1) if sq[j2 - 1] > 0]
            변동 = st.pstdev(_일) if len(_일) > 5 else None
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
                "갭": g, "매수": 매수, "변동성": 변동})
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
                    # ── 153차: 종목별 목표 ──
                    낙비 = c.get("낙폭비")
                    if 낙비 is not None and x.get("낙폭20") is not None:
                        목표b = max(3.0, abs(x["낙폭20"]) * 낙비)
                    변비 = c.get("변동비")
                    if 변비 is not None and x.get("변동성") is not None:
                        목표b = max(3.0, x["변동성"] * 변비)
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
    기본틀["낙사다리"] = [(-10, -5), (999, -10)]     # 147차 채택분

    모음 = []

    def 재기(라, c, 끝년=None):
        r = 시뮬(c, 끝년=끝년)
        해 = 10.4 if 끝년 is None else 8.4
        모음.append((r["산"] / 해, r, 라))
        return r

    print("=" * 108)
    print("  153차 · 기회를 늘린다")
    print("  ⚠️ 잣대를 바꾼다 — **1년에 몇 번 사나**를 앞에 놓는다")
    print("=" * 108)

    # ── A 기회 표 ──
    설정들 = [
        ("지금 (갭 -3.5)", {}),
        ("갭 -3.0", {"상대갭": -3.0}),
        ("갭 -2.5", {"상대갭": -2.5}),
        ("갭 -2.0", {"상대갭": -2.0}),
        ("시장 -10%↓ 갭-2.0 / 그밖 -3.5",
         {"갭사다리": [(-10, -2.0), (999, -3.5)]}),
        ("시장 -5%↓ 갭-2.5 / 그밖 -3.5",
         {"갭사다리": [(-5, -2.5), (999, -3.5)]}),
        ("시장 -5%↓ 갭-2.0 / 그밖 -3.0",
         {"갭사다리": [(-5, -2.0), (999, -3.0)]}),
        ("하루 8종목까지", {"하루상한": 8}),
        ("볼린저 -0.5 (느슨)", {"볼린저": -0.5}),
        ("낙폭 -5% (느슨)", {"낙폭20": -5, "낙사다리": None}),
    ]
    print(f"\n  {'설정':<34}{'1년에':>7}{'산 것':>7}{'끝 자산':>15}"
          f"{'낙폭':>8}{'현금':>8}")
    print("  " + "-" * 90)
    for 라, 바꿀 in 설정들:
        c = dict(기본틀)
        c.update(바꿀)
        r = 재기(라, c)
        print(f"  {라:<34}{r['산']/10.4:>6.1f}번{r['산']:>7}"
              f"{r['끝']:>15,.0f}{r['낙']:>7.1f}%{'':>8}")

    # ── A-2 낮은 고정 목표 ──
    # 사용자: 「1000원에 사서 2000원 목표인데 1200·1300원에 팔아도 괜찮다.
    #          다만 1% 미만은 좀 그렇다」
    print("\n" + "=" * 108)
    print("  A-2 목표를 낮게 잡으면 — **자주 닿고 회전이 빨라진다**")
    print("=" * 108)
    print(f"\n  {'설정':<34}{'1년에':>7}{'산 것':>7}{'끝 자산':>15}"
          f"{'낙폭':>8}{'돈÷낙폭':>9}")
    print("  " + "-" * 90)
    for 목 in (3, 5, 8, 10, 12, 15, 20):
        for 기한 in (10, 20, 40):
            c = dict(기본틀)
            c["나눔"] = ((1.0, 목, 기한),)
            r = 시뮬(c)
            if r["산"] < 30:
                continue
            print(f"  {f'+{목}% / {기한}일 하나로':<34}{r['산']/10.4:>6.1f}번"
                  f"{r['산']:>7}{r['끝']:>15,.0f}{r['낙']:>7.1f}%"
                  f"{r['연']/max(abs(r['낙']),3):>9.2f}")
    for 앞목, 앞기, 뒤목, 뒤기 in ((5, 10, 15, 40), (8, 20, 20, 60),
                                   (10, 20, 25, 60)):
        c = dict(기본틀)
        c["나눔"] = ((0.5, 앞목, 앞기), (0.5, 뒤목, 뒤기))
        r = 시뮬(c)
        print(f"  {f'반 +{앞목}%/{앞기}일 · 반 +{뒤목}%/{뒤기}일':<34}"
              f"{r['산']/10.4:>6.1f}번{r['산']:>7}{r['끝']:>15,.0f}"
              f"{r['낙']:>7.1f}%{r['연']/max(abs(r['낙']),3):>9.2f}")

    # ── B 종목별 목표 (낙폭 기반) ──
    print("\n" + "=" * 108)
    print("  B ⭐ 종목별 목표 — **그 종목 낙폭 × 비율**")
    print("     예) 30% 빠진 종목에 0.5 → 목표 +15% · 12% 빠진 종목 → +6%")
    print("=" * 108)
    print(f"\n  {'설정':<34}{'1년에':>7}{'산 것':>7}{'끝 자산':>15}"
          f"{'낙폭':>8}{'돈÷낙폭':>9}")
    print("  " + "-" * 90)
    기 = 시뮬(기본틀)
    print(f"  {'지금 (고정 +15% / +40%)':<34}{기['산']/10.4:>6.1f}번"
          f"{기['산']:>7}{기['끝']:>15,.0f}{기['낙']:>7.1f}%"
          f"{기['연']/max(abs(기['낙']),3):>9.2f}")
    # ⚠⚠ **`비` 는 시가/종가 비율 딕셔너리다 (73줄).**
    #    여기서 덮어써 153차가 B절에서 죽었다 (2026-09-08)
    for 낙폭비 in (0.3, 0.5, 0.7, 1.0, 1.5):
        for 기한 in (20, 40, 60):
            c = dict(기본틀)
            c["낙폭비"] = 낙폭비
            c["나눔"] = ((1.0, 15, 기한),)     # 목표는 낙폭비가 덮어쓴다
            r = 시뮬(c)
            if r["산"] < 30:
                continue
            print(f"  {f'낙폭×{낙폭비} · {기한}일':<34}{r['산']/10.4:>6.1f}번"
                  f"{r['산']:>7}{r['끝']:>15,.0f}{r['낙']:>7.1f}%"
                  f"{r['연']/max(abs(r['낙']),3):>9.2f}")

    # ── C 변동성 기반 ──
    print("\n" + "=" * 108)
    print("  C 종목별 목표 — **20일 변동성 × k**")
    print("=" * 108)
    print(f"\n  {'설정':<34}{'1년에':>7}{'산 것':>7}{'끝 자산':>15}"
          f"{'낙폭':>8}{'돈÷낙폭':>9}")
    print("  " + "-" * 90)
    for k in (2, 3, 5, 8):
        for 기한 in (20, 40, 60):
            c = dict(기본틀)
            c["변동비"] = k
            c["나눔"] = ((1.0, 15, 기한),)
            r = 시뮬(c)
            if r["산"] < 30:
                continue
            print(f"  {f'변동성×{k} · {기한}일':<34}{r['산']/10.4:>6.1f}번"
                  f"{r['산']:>7}{r['끝']:>15,.0f}{r['낙']:>7.1f}%"
                  f"{r['연']/max(abs(r['낙']),3):>9.2f}")

    # ── D 섞기 ──
    print("\n" + "=" * 108)
    print("  D 기회를 늘리는 설정 + 종목별 목표")
    print("=" * 108)
    print(f"\n  {'설정':<40}{'1년에':>7}{'산 것':>7}{'끝 자산':>15}{'낙폭':>8}")
    print("  " + "-" * 90)
    for 갭라, 갭바꿀 in (("시장-10%↓갭-2.0", {"갭사다리": [(-10, -2.0), (999, -3.5)]}),
                        ("갭 -2.5", {"상대갭": -2.5})):
        for 낙폭비 in (0.5, 0.7):
            for 기한 in (20, 40):
                c = dict(기본틀)
                c.update(갭바꿀)
                c["낙폭비"] = 낙폭비
                c["나눔"] = ((1.0, 15, 기한),)
                r = 시뮬(c)
                if r["산"] < 30:
                    continue
                print(f"  {f'{갭라} + 낙폭×{낙폭비}·{기한}일':<40}"
                      f"{r['산']/10.4:>6.1f}번{r['산']:>7}"
                      f"{r['끝']:>15,.0f}{r['낙']:>7.1f}%")

    print("\n" + "=" * 108)
    print("  읽는 법")
    print("    - **1년에 몇 번 사는가**를 먼저 보고, 그 낙폭을 견딜 수 있나 정한다")
    print("    - 낙폭은 **계좌 전체가 최고점에서 얼마나 깎였나**다 (종목 하나가 아니다)")
    print("    - 수익 극대화가 목표가 아니라면 **기회가 많고 낙폭이 견딜 만한 것**을 고른다")
    print("=" * 108)

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
    # ⚠️⚠️ **스스로 파일에 남긴다** (2026-09-08).
    #    전에는 손으로 `> 파일` 로 받아 적었는데, 줄서기로 돌리니
    #    화면으로 나가고 **사라졌다**. 153차가 그렇게 날아갔다
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT") or "2026-09-08_153차_기회표.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
