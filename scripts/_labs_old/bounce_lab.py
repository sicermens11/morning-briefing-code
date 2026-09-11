#!/usr/bin/env python3
r"""
bounce_lab.py — **136차 · 빠진 뒤 정말 안 돌아오나** (2026-09-07 신설)

## 사용자 질문에서 나왔다
```
「소형주에서만 작동한다는 건 대형주·중형주는 계속 상승한다는 말이야?」
```
**그렇게 말할 근거가 나한테 없다.** 134차는 「자본 시뮬 성적이 나빴다」만 보여줬고,
왜 나빴는지는 안 봤다. 셋 중 어느 것인지 갈라야 한다:
```
① 대형주는 애초에 **덜 빠진다** -> 살 기회가 적다 (표본 30·75건이 그 신호일 수 있다)
② 빠지면 **이유가 있어서** 안 돌아온다
③ 그냥 **덜 오른다** (되돌림 폭이 작다)
```

## 재는 것 (자본 시뮬이 아니라 **되돌림 그 자체**)
```
규모마다
  a) 20일 -10% 넘게 빠진 사건이 **몇 건**인가 (전체 종목-날 대비 몇 %)
  b) 그 뒤 20 / 40 / 90거래일 수익률의 **중앙값·평균·이긴 비율**
  c) ⭐ 견줌: **같은 규모에서 아무 날이나 산 경우**의 같은 기간 수익률
     -> b - c 가 **되돌림의 값어치**다. 0이면 「빠진 걸 사도 소용없다」
```
⚠️ 여기서는 갭도 매도 규칙도 안 쓴다. **순수하게 되돌아오나만** 본다

쓰는 법:
    python scripts\bounce_lab.py
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

    import random as _rnd

    # ── 앞으로 n거래일 뒤 수익률 (수정주가로) ──
    def 앞수익(code, i2, n):
        j = i2 + n
        if j >= len(날):
            return None
        a = 주가[날[i2]].get(code)
        b = 주가[날[j]].get(code)
        if not a or not b or a[0] <= 0:
            return None
        return (b[0] / a[0] - 1) * 100

    규모들 = [("소형 500~2,000억", 500, 2000),
              ("중형 2,000억~1조", 2000, 10000),
              ("대형 1조 이상", 10000, 9e9)]

    # ── 빠진 사건 (사건에는 볼린저 ≤ +0.5 · 낙폭 ≤ 0 만 걸려 있다) ──
    빠짐 = {라: [] for 라, _, _ in 규모들}
    for x in 사건:
        if x["볼린저"] is None or x["낙폭20"] is None:
            continue
        if not (x["볼린저"] <= -1.0 and x["낙폭20"] <= -10):
            continue
        for 라, 하, 상 in 규모들:
            if 하 <= x["시총억"] < 상:
                빠짐[라].append(x)
                break

    # ── 견줄 것: 같은 규모에서 **아무 날이나** (무작위 표본) ──
    _r = _rnd.Random(20260907)
    아무 = {라: [] for 라, _, _ in 규모들}
    날수 = len(날)
    for 라, 하, 상 in 규모들:
        뽑 = 0
        while 뽑 < 4000:
            i2 = _r.randrange(260, 날수 - 95)
            하루 = 주가[날[i2]]
            if not 하루:
                continue
            code = _r.choice(list(하루))
            v = 하루[code]
            시총억 = v[1] / 1e8
            if not (하 <= 시총억 < 상):
                continue
            if v[2] < 1e8:              # 거래대금 1억 미만은 뺀다
                continue
            아무[라].append((code, i2))
            뽑 += 1

    def 통계(항목, 뽑기):
        """(건수, 중앙, 평균, 이긴비율)"""
        칸 = []
        for it in 항목:
            r = 뽑기(it)
            if r is not None:
                칸.append(r)
        if len(칸) < 30:
            return len(칸), None, None, None
        칸.sort()
        return (len(칸), 칸[len(칸) // 2], sum(칸) / len(칸),
                sum(1 for v in 칸 if v > 0) / len(칸) * 100)

    전체종목날 = sum(len(주가[d]) for d in 날[260:])
    print("=" * 100)
    print("  136차 · 빠진 뒤 정말 안 돌아오나  (갭·매도규칙 안 씀 · 순수 되돌림)")
    print("=" * 100)

    for 라, 하, 상 in 규모들:
        ev = 빠짐[라]
        rd = 아무[라]
        print(f"\n  ══ {라} ══")
        print(f"    20일 -10%↓ + 볼린저 -1.0↓ 사건: **{len(ev):,}건**")
        print(f"    {'기간':<8}{'빠진 것':>30}{'아무 날이나':>30}{'차이':>10}")
        print(f"    {'':<8}{'중앙':>9}{'평균':>9}{'이김%':>9}"
              f"{'중앙':>10}{'평균':>9}{'이김%':>9}{'':>10}")
        for n in (20, 40, 90):
            n1, m1, a1, w1 = 통계(ev, lambda x, n=n: 앞수익(x["code"],
                                                            x["인"] - 1, n))
            n2, m2, a2, w2 = 통계(rd, lambda it, n=n: 앞수익(it[0], it[1], n))
            if m1 is None or m2 is None:
                print(f"    {n}일{'':<4}표본 부족 ({n1} / {n2})")
                continue
            print(f"    {n}일{'':<4}{m1:>9.2f}{a1:>9.2f}{w1:>9.1f}"
                  f"{m2:>10.2f}{a2:>9.2f}{w2:>9.1f}{(a1-a2):>10.2f}")
        if 전체종목날:
            print(f"    (사건 빈도: 전체 종목-날의 "
                  f"{len(ev)/전체종목날*100:.2f}%)")

    print("\n" + "=" * 100)
    print("  읽는 법")
    print("    - **차이**(빠진 것 평균 - 아무 날이나 평균)가 되돌림의 값어치다")
    print("    - 차이가 0에 가까우면 「빠진 걸 사도 소용없다」는 뜻이다")
    print("    - 사건 **건수**가 적으면 「살 기회가 없다」는 뜻이지")
    print("      「빠져도 안 돌아온다」는 뜻이 아니다 — 둘을 갈라 봐야 한다")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    sys.exit(main())
