#!/usr/bin/env python3
r"""
walk3_lab.py — **150차 · 지금 규칙 전체를 걷기 검증** (2026-09-08 신설)

## 사용자 질문
```
「백테스트와 걷기 테스트 차이가 뭐야?」
```
```
백테스트   16.7년을 **다 보고** 문턱을 정한 뒤 그 문턱으로 16.7년을 다시 훑는다
          -> 2016년에 살 때 **2026년을 이미 알고** 문턱을 정한 셈이다
걷기 검증   2011~2015 만 보고 문턱을 정한다 -> 그 문턱으로 **2016년만** 산다
          그다음 2011~2016 으로 다시 정한다 -> **2017년만** 산다 … 반복
          -> 실전과 **같은 방식**. 미래를 못 본다
```

## 우리는 **부분만** 했다
```
61차 (09-03)  **재무 문턱**만 걷기검증 -> 8/8해 통과 ✅
안 한 것       볼린저 · 낙폭 · 갭 문턱 — 전부 **전체 기간을 보고 정했다**
              124차 나눠팔기 · 147차 국면별 낙폭도 걷기검증 안 함
```
4관문의 「앞뒤 분할」도 시작년만 옮긴 것이지 **문턱을 그 시점 자료로만 정한 게 아니다.**
⇒ **지금 규칙 전체를 걷기검증한 적이 없다.** 남은 것 중 가장 큰 구멍이다

## 하는 일
```
해마다:
  ① 그 해 **이전 자료만** 보고 격자를 훑어 (볼린저 × 낙폭 × 갭) 문턱을 고른다
     — 고르는 잣대는 **돈÷낙폭** (98차에서 정한 것)
  ② 그 문턱으로 **그 해만** 산다
  ③ 다음 해로
견줌  ㉠ 지금 고정 문턱(-1.0 · -10 · -3.5)으로 같은 해를 산 것
      ㉡ 전체 기간을 보고 정한 문턱 (= 미래를 훔쳐본 것)
```
⚠️ **자본 시뮬로 한다** — 개별 거래 평균으로 하면 통과한 것도 무너진다
   [[walkforward-must-use-capital-sim]]
⚠️ 첫 해(2011~2015)는 배울 자료가 모자라 건너뛴다. 2016년부터 잰다

쓰는 법:
    python scripts\walk3_lab.py
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
    기본틀["대금하한"] = 1.0

    볼들 = (-1.5, -1.0, -0.5)
    낙들 = (-15, -10, -5)
    갭들 = (-4.5, -3.5, -2.5)

    def 문턱고르기(끝년):
        """그 해 **이전** 자료만 보고 돈÷낙폭이 가장 좋은 문턱을 고른다"""
        best = None
        for 볼 in 볼들:
            for 낙 in 낙들:
                for 갭 in 갭들:
                    c = dict(기본틀)
                    c["볼린저"], c["낙폭20"], c["상대갭"] = 볼, 낙, 갭
                    r = 시뮬(c, 끝년=끝년)
                    if r["산"] < 20:
                        continue
                    점 = r["연"] / max(abs(r["낙"]), 3.0)
                    if best is None or 점 > best[0]:
                        best = (점, 볼, 낙, 갭)
        return best

    print("=" * 104)
    print("  150차 · 지금 규칙 **전체**를 걷기 검증")
    print("  (그 해 이전만 보고 문턱을 정해 그 해를 산다 · 자본 시뮬)")
    print("=" * 104)
    print(f"\n  격자 {len(볼들)}x{len(낙들)}x{len(갭들)} = "
          f"{len(볼들)*len(낙들)*len(갭들)}칸 · 해마다 다시 고른다")
    print(f"\n  {'해':<6}{'고른 문턱 (볼/낙/갭)':<24}"
          f"{'걷기 결과':>14}{'지금 문턱':>14}{'차이':>9}")
    print("  " + "-" * 90)

    걷기합, 지금합, 이김, 짐 = [], [], 0, 0
    for y in range(2016, 2027):
        앞해 = str(y - 1)
        best = 문턱고르기(앞해)
        if not best:
            print(f"  {y:<6}배울 자료 부족")
            continue
        _, 볼, 낙, 갭 = best
        c = dict(기본틀)
        c["볼린저"], c["낙폭20"], c["상대갭"] = 볼, 낙, 갭
        걷 = 시뮬(c, 시작년=str(y), 끝년=str(y))
        지 = dict(기본틀)
        지["볼린저"], 지["낙폭20"], 지["상대갭"] = -1.0, -10, -3.5
        지r = 시뮬(지, 시작년=str(y), 끝년=str(y))
        a, b = 걷["끝"], 지r["끝"]
        차 = (a / b - 1) * 100 if b else 0
        if 차 > 0.01:
            이김 += 1
        elif 차 < -0.01:
            짐 += 1
        걷기합.append(a)
        지금합.append(b)
        print(f"  {y:<6}{f'{볼} / {낙} / {갭}':<24}"
              f"{a:>14,.0f}{b:>14,.0f}{차:>8.1f}%")

    if 걷기합:
        import statistics as _st
        print("  " + "-" * 90)
        print(f"  {'합':<6}{'':<24}{_st.mean(걷기합):>14,.0f}"
              f"{_st.mean(지금합):>14,.0f}")
        print(f"\n  ⇒ 걷기검증이 지금 문턱보다 **{이김}승 {짐}패**")
        print(f"     (해마다 500만원으로 새로 시작한 값이다 — 해끼리 견주려고)")

    # ── 전체를 통으로 ──
    print("\n" + "=" * 104)
    print("  견줌 — 통으로 돌린 것 (2016~)")
    print("=" * 104)
    print(머)
    지 = dict(기본틀)
    지["볼린저"], 지["낙폭20"], 지["상대갭"] = -1.0, -10, -3.5
    기 = 시뮬(지, 시작년="2016")
    표(기, "지금 문턱 (-1.0 / -10 / -3.5)")
    전체best = 문턱고르기(None)
    if 전체best:
        _, 볼, 낙, 갭 = 전체best
        c = dict(기본틀)
        c["볼린저"], c["낙폭20"], c["상대갭"] = 볼, 낙, 갭
        표(시뮬(c, 시작년="2016"),
          f"**전체를 보고 고른 문턱** ({볼}/{낙}/{갭}) ← 미래를 훔쳐본 것", 기)

    print("\n" + "=" * 104)
    print("  읽는 법")
    print("    - 걷기검증이 **지금 문턱과 비슷하면** 문턱이 안정적이라는 뜻이다")
    print("    - 걷기검증이 **크게 나쁘면** 지금 문턱은 미래를 훔쳐본 결과다")
    print("    - 해마다 고른 문턱이 **들쭉날쭉하면** 그 격자는 못 믿는다")
    print("=" * 104)

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
