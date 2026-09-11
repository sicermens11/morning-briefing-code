#!/usr/bin/env python3
r"""
fin_grid_lab.py — **138차 · 재무 문턱을 처음으로 격자로 훑는다** (2026-09-07)

## 왜 이게 제일 급한가
```
133차에서 공시 축에 **재무를 얹자 +185%**가 됐다 (낙폭 -67.5% -> -36.5%).
지금까지 검증한 신호 중 **가장 힘이 세다.**
그런데 그 문턱(잉여금 30% · 부채 80%)을 **격자로 훑은 적이 없다.**
61차에 「이 값으로도 11해 다 통과」를 확인한 게 전부다 — 다른 값과 견준 적이 없다
```
131차에서 「실제로 일하는 건 갭 문턱뿐」이었으니, **재무 × 갭** 둘을 같이 훑는다.
둘 다 우리 재료지만 **숫자를 한 번도 제대로 안 찾아봤다**

## 격자
```
잉여금비율 하한   0 · 10 · 20 · 30 · 50 · 70      (지금 30)
부채비율 상한   40 · 60 · 80 · 120 · 200 · 없음   (지금 80)
흑자          걸기 · 안 걸기
갭 문턱       -4.5 · -4.0 · -3.5 · -3.0 · -2.5    (지금 -3.5)
= 6 x 6 x 2 x 5 = **360칸**
고정          시총 500~2,000억 · 거래대금 1억 · 볼린저 -1.0 · 낙폭 -10 ·
              하루 4종목 · 나눠팔기 매도
```
⚠️ 격자 1등은 **답이 아니라 후보**다. 110차에서 격자 순위표가 못 쓸 것으로 판명났다.
   1등은 4관문에 걸어야 쓴다

⚠️⚠️ **수집에서 재무를 걸지 않는다.** 걸면 문턱 여섯 가지가 전부 같은 값이 된다
   (09-04에 실제로 당했다). 느슨하게 모으고 **시뮬에서 거른다**

쓰는 법:
    python scripts\fin_grid_lab.py
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
            # ⚠️ **재무를 여기서 걸지 않는다** — 격자로 훑을 것이기 때문이다.
            #    값만 붙여두고 시뮬에서 거른다
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
                "갭": g, "매수": 매수,
                "잉여금": fm.get("잉여금비율"),
                "부채": fm.get("부채비율"),
                "흑자": fm.get("흑자")})
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
                  and x["볼린저"] <= c["볼린저"]
                  and x["낙폭20"] <= c["낙폭20"]
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
                if v3 <= c["상대갭"]:
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
    기본틀["볼린저"], 기본틀["낙폭20"] = -1.0, -10
    기본틀["대금하한"] = 1.0

    잉여금들 = (0, 10, 20, 30, 50, 70)
    부채들 = (40, 60, 80, 120, 200, 9e9)
    흑자들 = (True, False)
    갭들 = (-4.5, -4.0, -3.5, -3.0, -2.5)

    def 재무거름(잉, 부, 흑):
        def _f(x):
            if x.get("잉여금") is None or x.get("부채") is None:
                return False
            if x["잉여금"] < 잉 or x["부채"] > 부:
                return False
            if 흑 and x.get("흑자") != 1.0:
                return False
            return True
        return _f

    print("=" * 100)
    print("  138차 · 재무 문턱 × 갭 문턱 격자 (360칸)")
    print("  고정: 시총 500~2,000억 · 거래대금 1억 · 볼린저 -1.0 · 낙폭 -10 · 나눠팔기")
    print("=" * 100)
    지금 = dict(기본틀)
    지금["상대갭"] = -3.5
    지금["거름"] = 재무거름(30, 80, True)
    기 = 시뮬(지금)
    print(머)
    표(기, "지금 규칙 (잉여금 30 · 부채 80 · 흑자 · 갭 -3.5)")

    칸들 = []
    돈 = 0
    for 잉 in 잉여금들:
        for 부 in 부채들:
            for 흑 in 흑자들:
                fn = 재무거름(잉, 부, 흑)
                n2 = sum(1 for x in 사건 if fn(x))
                if n2 < 2000:
                    continue
                for 갭 in 갭들:
                    c = dict(기본틀)
                    c["상대갭"] = 갭
                    c["거름"] = fn
                    r = 시뮬(c)
                    돈 += 1
                    if r["산"] < 40:
                        continue
                    점 = r["연"] / max(abs(r["낙"]), 3.0)
                    칸들.append((점, 잉, 부, 흑, 갭, r))
        print(f"    … 잉여금 {잉} 끝 · {돈}칸 돌림", flush=True)
    칸들.sort(key=lambda z: -z[0])

    print("\n  ── 돈÷낙폭 상위 15칸 ──")
    print(f"  {'잉여금':>7}{'부채':>8}{'흑자':>6}{'갭':>7}"
          f"{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}")
    for 점, 잉, 부, 흑, 갭, r in 칸들[:15]:
        부표 = "없음" if 부 > 1e8 else f"{부:.0f}"
        print(f"  {잉:>7}{부표:>8}{('O' if 흑 else 'X'):>6}{갭:>7.1f}"
              f"{r['끝']:>16,.0f}{r['연']:>8.2f}%{r['낙']:>7.1f}%"
              f"{r['산']:>7}{점:>9.2f}")

    print("\n  ── 끝 자산 상위 10칸 (참고) ──")
    for 점, 잉, 부, 흑, 갭, r in sorted(칸들, key=lambda z: -z[5]["끝"])[:10]:
        부표 = "없음" if 부 > 1e8 else f"{부:.0f}"
        print(f"  {잉:>7}{부표:>8}{('O' if 흑 else 'X'):>6}{갭:>7.1f}"
              f"{r['끝']:>16,.0f}{r['연']:>8.2f}%{r['낙']:>7.1f}%"
              f"{r['산']:>7}{점:>9.2f}")

    # ── 상위 5칸을 2025·26 제외로 ──
    print("\n" + "=" * 100)
    print("  상위 5칸을 **2025·26 제외**로 다시 — 앞뒤가 같은 방향인가")
    print("=" * 100)
    print(머)
    표(시뮬(지금, 끝년="2024"), "지금 규칙")
    for 점, 잉, 부, 흑, 갭, r in 칸들[:5]:
        c = dict(기본틀)
        c["상대갭"] = 갭
        c["거름"] = 재무거름(잉, 부, 흑)
        부표 = "없음" if 부 > 1e8 else f"{부:.0f}"
        표(시뮬(c, 끝년="2024"),
          f"잉여금{잉}·부채{부표}·흑자{'O' if 흑 else 'X'}·갭{갭}")
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
