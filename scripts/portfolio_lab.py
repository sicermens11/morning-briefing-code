#!/usr/bin/env python3
r"""
portfolio_lab.py — **하루 몇 종목 · 비중 몇 %가 최선인가** (2026-09-07 신설)

## 왜 (과제②)
```
「하루 4종목 · 비중 20%」는 94b·98차에서 정했고 104차 4관문을 통과했다.
그런데 그건 전부 **전종목중앙갭**으로 잰 것이다.
2026-09-07 에 실전 절차(**후보 40개 중앙갭**)로 고쳤으니 **다시 재야 한다**
```

## 재는 것 — 전부 실전 절차(후보 40개 중앙갭)
```
A 하루 몇 종목      1 / 2 / 3 / 4 / 5 / 6
B 비중             10 / 15 / 20 / 25 / 30 %
C ⭐ 둘의 조합       종목수 x 비중 (하루 최대 노출이 같아도 결과가 다른가)
   4종목x20% = 80%  ·  2종목x40% = 80%  — 같은 노출인데 성적이 다르면
   **분산 자체에 값어치가 있다**는 뜻이다
D 후보수           20 / 40 / 60 / 전부 (08:00에 몇 개를 브리핑에 싣나)
```
⚠️ **원판보다 끝 자산이 크고 낙폭이 안 나빠져야** 바꾼다.
⚠️ 자산 규모에 따라 답이 뒤집히는지도 본다 (과제①에서 그런 일이 있었다)

쓰는 법:
    python scripts\portfolio_lab.py
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

    def 시뮬(c, 끝년=None, 시드=None):
        시드 = 시드 or _시드
        현금, 보유, 곡, 산 = 시드, [], [], 0
        for i in range(시i, len(날)):
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
            골 = sorted([x for x in 칸 if x["갭"] - 중 <= c["상대갭"]],
                        key=lambda z: z["갭"] - 중)
            for x in 골[:c["하루상한"]]:
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

    for 끝년, 라 in ((None, "전체 기간"), ("2024", "2025·26 제외")):
        기 = 시뮬(확정, 끝년=끝년)
        print("=" * 96)
        print("  == " + 라 + " ==   (기준 = 지금 규칙: 하루 4종목 · 비중 20%)")
        print("=" * 96)
        print(머)
        표(기, "기준 (4종목 x 20%)")

        print("")
        print("    -- A 하루 몇 종목 --")
        for v in (1, 2, 3, 4, 5, 6):
            c = dict(확정)
            c["하루상한"] = v
            표(시뮬(c, 끝년=끝년), str(v) + "종목", 기)

        print("")
        print("    -- B 비중 --")
        for v in (0.10, 0.15, 0.20, 0.25, 0.30):
            c = dict(확정)
            c["비중"] = v
            표(시뮬(c, 끝년=끝년), "비중 " + str(int(v * 100)) + "%", 기)

        print("")
        print("    -- D 목표 x 보유일 (**한 번도 안 재봤다**) --")
        for 목 in (5, 10, 15, 20, 25, 30, 40):
            for 보 in (10, 20, 40, 60, 90):
                c = dict(확정)
                c["목표"], c["최대보유"] = 목, 보
                표(시뮬(c, 끝년=끝년),
                  "목표 " + str(목) + "% · 보유 " + str(보) + "일", 기)

        print("")
        print("    -- C 같은 노출인데 나누면 다른가 --")
        for 종, 비중값 in ((1, 0.80), (2, 0.40), (4, 0.20), (8, 0.10)):
            c = dict(확정)
            c["하루상한"], c["비중"] = 종, 비중값
            표(시뮬(c, 끝년=끝년),
              str(종) + "종목 x " + str(int(비중값 * 100)) + "% (노출 80%)", 기)
        for 종, 비중값 in ((1, 0.40), (2, 0.20), (4, 0.10)):
            c = dict(확정)
            c["하루상한"], c["비중"] = 종, 비중값
            표(시뮬(c, 끝년=끝년),
              str(종) + "종목 x " + str(int(비중값 * 100)) + "% (노출 40%)", 기)
        print("")

    # -- D 자산 규모별로도 4종목이 최선인가 --
    print("=" * 96)
    print("  == 자산 규모별 — 종목수가 자산에 따라 뒤집히나 ==")
    print("=" * 96)
    for 시드 in (5_000_000, 50_000_000, 200_000_000):
        print("")
        print("    -- 시드 " + format(시드 / 1e8, ".2f") + "억 --")
        print(머)
        기2 = 시뮬(확정, 시드=시드)
        표(기2, "기준 (4종목)")
        for v in (2, 3, 5, 6):
            c = dict(확정)
            c["하루상한"] = v
            표(시뮬(c, 시드=시드), str(v) + "종목", 기2)
    print("")

    print("=" * 96)
    print("  읽는 법")
    print("    - 기준보다 끝 자산이 크고 낙폭이 안 나빠져야 바꾼다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("    - C에서 노출이 같은데 성적이 다르면 **분산 자체에 값어치**가 있다")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
