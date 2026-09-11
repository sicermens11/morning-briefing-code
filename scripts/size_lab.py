#!/usr/bin/env python3
r"""
size_lab.py — **시총·거래대금·거래량 어느 기준이 좋은가** (2026-09-07 신설)

## 왜
```
사용자 질문 9번: 「시가총액, 거래대금, 거래량 어떤 기준이 좋을지」
지금 규칙은  시총 500억~2,000억  +  거래대금 1억 이상  만 쓴다.
**거래량은 한 번도 안 썼다** (record_pick·verify_all 에 0회).
어느 기준이 나은지 **재본 적이 없다**
```

## 재는 것 — 전부 **실전 절차(후보 40개 중앙갭)**로
```
A 시총 상한       1000 / 1500 / 2000 / 3000 / 5000 / 없음(억)
B 시총 하한       300 / 500 / 800 / 1200 (억)
C 거래대금 하한    0.5 / 1 / 3 / 5 / 10 (억)
D 거래량 하한     1만 / 5만 / 10만 / 30만 주
E 회전율         거래대금 ÷ 시총 (하루에 몇 % 가 손바뀜하나)
   ⚠️ 이건 **크기와 무관한 활발함**이다. 거래대금은 큰 회사가 무조건 크다
```
⚠️ 하나만 바꾸고 나머지는 확정값으로 둔다 (요소분해와 같은 방식).
⚠️ **원판보다 끝 자산이 커야** 바꿀 값어치가 있다.

쓰는 법:
    python scripts\size_lab.py
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

    기준 = 시뮬(확정)
    for 끝년, 라 in ((None, "전체 기간"), ("2024", "2025·26 제외")):
        기 = 시뮬(확정, 끝년=끝년)
        print("=" * 96)
        print(f"  ══ {라} ══   (기준 = 지금 규칙: 시총 500~2,000억 · 대금 1억↑)")
        print("=" * 96)
        print(머)
        표(기, "기준 (지금 규칙)")

        print(f"\n    ── A 시총 **상한** ──")
        for v in (1000, 1500, 2000, 3000, 5000, 999999):
            c = dict(확정)
            c["시총상한"] = v
            표(시뮬(c, 끝년=끝년),
              f"상한 {v:,}억" if v < 999999 else "상한 없음", 기)

        print(f"\n    ── B 시총 **하한** ──")
        for v in (100, 300, 500, 800, 1200):
            c = dict(확정)
            c["시총하한"] = v
            표(시뮬(c, 끝년=끝년), f"하한 {v:,}억", 기)

        print(f"\n    ── C 거래대금 **하한** ──")
        for v in (0.0, 0.5, 1.0, 3.0, 5.0, 10.0):
            c = dict(확정)
            c["대금하한"] = v
            표(시뮬(c, 끝년=끝년), f"거래대금 {v:.1f}억↑", 기)

        print(f"\n    ── D 거래량 **하한** (한 번도 안 써본 것) ──")
        for v in (0, 10_000, 50_000, 100_000, 300_000):
            c = dict(확정)
            c["거래량하한"] = v
            표(시뮬(c, 끝년=끝년),
              f"거래량 {v:,}주↑" if v else "거래량 조건 없음", 기)

        print(f"\n    ── E 회전율 하한 (대금÷시총) ──")
        for v in (0.0, 0.3, 0.5, 1.0, 2.0):
            c = dict(확정)
            c["회전율하한"] = v
            표(시뮬(c, 끝년=끝년),
              f"회전율 {v:.1f}%↑" if v else "회전율 조건 없음", 기)
        print()

    # ── ⭐ 자산 규모별 — **거래대금 하한이 정말 이득인가** ──
    #    ⚠️ 시뮬은 「거래대금의 1%까지만 산다」로 제한한다.
    #       5천만원짜리 종목이면 **50만원어치밖에 못 산다.**
    #       자산이 커지면 그 종목은 사실상 못 사는 것이다
    print("=" * 96)
    print("  == 자산 규모별 — 거래대금 하한이 자산이 커져도 이득인가 ==")
    print("=" * 96)
    for 시드 in (5_000_000, 50_000_000, 200_000_000):
        print("")
        print("    -- 시드 " + format(시드 / 1e8, ".2f") + "억 --")
        print(머)
        기2 = 시뮬(확정, 시드=시드)
        표(기2, "기준 - 대금 1억↑")
        for v in (0.5, 3.0, 5.0):
            c = dict(확정)
            c["대금하한"] = v
            표(시뮬(c, 시드=시드), "거래대금 " + format(v, ".1f") + "억↑", 기2)
    print("")
    print("=" * 96)
    print("  읽는 법")
    print("    - **기준보다 끝 자산이 크고 낙폭이 안 나빠져야** 바꿀 값어치가 있다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("    - 조건을 조이면 산 것이 줄어든다 — 그만큼 기회를 버리는 것이다")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
