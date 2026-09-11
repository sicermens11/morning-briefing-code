#!/usr/bin/env python3
r"""
price_lab.py — **137차 · 주가 수준(가격대)이 성적에 영향을 주나** (2026-09-07)

## 사용자 질문에서 나왔다
```
「삼성전자 20만원이 1% 오르면 2천원, 5만원 종목이 4% 올라야 2천원.
  %만 보면 5만원짜리가 커 보이지만 결국 같은 것 아니야?」
```
⚠️ **주당 금액은 성적과 무관하다.** 같은 돈을 넣으면 싼 주식을 더 많이 산다:
```
1,000만원의 20% = 200만원
  20만원짜리 -> 10주.  1% 오르면 주당 2,000원 x 10주 =  2만원  = 자본의 1%
   5만원짜리 -> 40주.  4% 오르면 주당 2,000원 x 40주 =  8만원  = 자본의 4%
```
「주당 2,000원」이 같아도 **주수가 4배**라 돈은 4배다.
주식분할을 하면 주가는 반이 되고 주수는 두 배가 된다 — 수익은 그대로다.
⇒ 우리 시뮬은 **이미 금액으로 잰다**: 자산 20%를 원본 시가로 나눠 주수를 만들고,
  끝에 실제 돈(6,432만원)을 낸다. 발표하는 %는 **자본 대비**이지 주당이 아니다

## 그런데 **한 번도 안 본 것**이 여기 있다 — 가격대
```
호가 단위가 가격대마다 다르다. 2,000원짜리의 1틱과 20만원짜리의 1틱은
**자기 주가 대비 비율이 다르다.** 그게 곧 **보이지 않는 거래비용**이다
지금 시뮬은 왕복 비용을 **0.26% 하나로 고정**해 놓았다 — 가격대를 안 본다
```

## 재는 것
```
A 호가 단위를 **자료에서 직접 잰다** (원본 시가들의 최소 간격)
  -> 가격대마다 1틱이 주가의 몇 %인가
B 가격대별 성적 (1천원 미만 · 1~5천 · 5천~1만 · 1~5만 · 5만~20만 · 20만 이상)
C 가격대별로 **비용을 틱으로 바꿔** 다시 잰다 (0.26% 고정 대신)
```

쓰는 법:
    python scripts\price_lab.py
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

    import collections as _co

    기본틀 = dict(확정)
    기본틀["나눔"] = ((0.5, 15, 40), (0.5, 40, 90))
    기본틀["시총하한"], 기본틀["시총상한"] = 500, 2000
    기본틀["볼린저"], 기본틀["낙폭20"], 기본틀["상대갭"] = -1.0, -10, -3.5

    구간 = [("1천원 미만", 0, 1000), ("1~5천원", 1000, 5000),
            ("5천~1만원", 5000, 10000), ("1~5만원", 10000, 50000),
            ("5~20만원", 50000, 200000), ("20만원 이상", 200000, 9e9)]

    # ── A 호가 단위를 자료에서 직접 잰다 ──
    print("=" * 96)
    print("  A 호가 단위 — **자료에서 직접 쟀다** (원본 시가들의 최소 간격)")
    print("=" * 96)
    값들 = _co.defaultdict(set)
    for d3 in 날[::7]:
        for code, o in (원시.get(d3) or {}).items():
            try:
                v = float(o)
            except (TypeError, ValueError):
                continue
            if v <= 0:
                continue
            for 라, 하, 상 in 구간:
                if 하 <= v < 상:
                    값들[라].add(int(round(v)))
                    break
    print(f"  {'가격대':<14}{'표본':>9}{'호가 단위':>10}{'1틱이 주가의':>14}")
    틱표 = {}
    for 라, 하, 상 in 구간:
        s = sorted(값들.get(라) or [])
        if len(s) < 200:
            print(f"  {라:<14}{len(s):>9,}   표본 부족")
            continue
        # 이웃한 값들의 차이 중 **가장 흔한 양수**가 호가 단위다
        차 = _co.Counter()
        for j in range(1, len(s)):
            d = s[j] - s[j - 1]
            if 0 < d <= 5000:
                차[d] += 1
        틱 = 차.most_common(1)[0][0] if 차 else None
        가운데 = s[len(s) // 2]
        # ⚠️⚠️ **여기서 `비` 를 쓰면 안 된다** — 시가/종가 비율 딕셔너리를 덮어쓴다.
        #    메모리에 적어놨는데 오늘 여섯 번째로 당했다 (2026-09-07)
        틱비 = (틱 / 가운데 * 100) if (틱 and 가운데) else None
        틱표[라] = (틱, 틱비)
        print(f"  {라:<14}{len(s):>9,}{(틱 if 틱 else 0):>10,}"
              f"{(틱비 if 틱비 else 0):>13.3f}%")
    print("\n  ⇒ 1틱이 주가에서 차지하는 비율이 **가격대마다 다르다.**")
    print("     이것이 지금 시뮬이 안 보고 있는 **보이지 않는 비용**이다")

    # ── B 가격대별 성적 ──
    print("\n" + "=" * 96)
    print("  B 가격대별 성적 (지금 규칙 그대로 · 비용 0.26% 고정)")
    print("=" * 96)
    print(머)
    기 = 시뮬(기본틀)
    표(기, "전체 (가격대 안 가림)")
    for 라, 하, 상 in 구간:
        fn = (lambda x, 하=하, 상=상: 하 <= (x.get("원시") or 0) < 상)
        n2 = sum(1 for x in 사건 if fn(x))
        if n2 < 200:
            print(f"    {라:<24}후보 {n2:>6,}건 — **표본 부족**")
            continue
        c2 = dict(기본틀)
        c2["거름"] = fn
        표(시뮬(c2), f"{라} [{n2:,}건]", 기)

    print("\n" + "=" * 96)
    print("  B-2 같은 것을 2025·26 제외로")
    print("=" * 96)
    print(머)
    기2 = 시뮬(기본틀, 끝년="2024")
    표(기2, "전체 (가격대 안 가림)")
    for 라, 하, 상 in 구간:
        fn = (lambda x, 하=하, 상=상: 하 <= (x.get("원시") or 0) < 상)
        n2 = sum(1 for x in 사건 if fn(x))
        if n2 < 200:
            continue
        c2 = dict(기본틀)
        c2["거름"] = fn
        표(시뮬(c2, 끝년="2024"), f"{라} [{n2:,}건]", 기2)

    # ── C 저가주를 빼면? ──
    print("\n" + "=" * 96)
    print("  C 싼 주식을 빼면 나아지나 (틱 비용이 큰 쪽)")
    print("=" * 96)
    print(머)
    표(기, "전체")
    for 문턱 in (1000, 2000, 5000, 10000):
        fn = (lambda x, m=문턱: (x.get("원시") or 0) >= m)
        n2 = sum(1 for x in 사건 if fn(x))
        if n2 < 200:
            continue
        c2 = dict(기본틀)
        c2["거름"] = fn
        표(시뮬(c2), f"{문턱:,}원 이상만 [{n2:,}건]", 기)
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
