#!/usr/bin/env python3
r"""
sector_lab.py — **대형주 + 주요 산업 섹터를 자본 시뮬로** (2026-09-07 신설)

## 왜
```
사용자 지시: 「반도체, AI, 조선, 방산 등 대한민국 주요산업 및 수출산업은
              꼭 테스트해봤으면 좋겠다」

섹터 목록은 data/value-chain-map.md 에 이미 있다 (14개 · 118종목).
지금까지 섹터를 **선정 조건으로 써 본 적이 없다** —
  65b 섹터 로테이션(지수 기준)과 89차 가치사슬(엔비디아→하이닉스)은 기각됐지만
  **「이 섹터 안에서만 지금 규칙을 돌리면?」은 안 해봤다**
```

## 재는 것 — 전부 실전 절차(후보 N개 중앙갭) · 자본 시뮬
```
A 대형주 1~10조     신호 지도에서 **갭이 볼린저의 2.3배**였다 → 갭 위주로 짠다
                   ⚠️ 초대형(10조↑)은 69종목뿐이라 뺀다.
                     삼성전자(1,494조)와 삼양식품(10.7조)에 같은 규칙은 무리다
B 14개 섹터        각 섹터 안에서만 지금 규칙을 돌린다
                   ⚠️ 섹터당 3~11종목이라 **표본이 얇다.** 그래서 문턱을 크게
                     완화해 후보를 만들고, 그래도 안 되면 「못 잰다」고 적는다
C 섹터 묶음         반도체+AI / 조선+방산 처럼 붙여서 표본을 키운다
```
⚠️ **소형 규칙(5,433만 · 연 +25.67% · 낙폭 -5.8%)과 견준다.** 못 이기면 안 쓴다
⚠️ 중형주는 이미 기각됐다 (연 +2.67% · 낙폭 -55.7%)
⚠️ 표본이 30건 미만이면 **성적을 믿지 않는다** — 「표본 부족」이라고 적는다

쓰는 법:
    python scripts\sector_lab.py
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
_느볼 = -0.3      # 수집용 느슨한 값 — 훑는 값보다 넓어야 한다
_느낙 = 0.0
# 소형 규칙 (견줄 대상)
소형 = {"잉여금": 30, "부채": 80, "흑자필수": True, "상대갭": -3.5,
        "볼린저": -1.0, "낙폭20": -10, "목표": 20, "최대보유": 40,
        "비중": 0.20, "하루상한": 4,
        "시총하한": 500, "시총상한": 2000, "대금하한": 1.0, "거래량하한": 0,
        "회전율하한": 0.0}
# 중형 출발점 — 소형 규칙을 그대로 중형 구간에 건 것
확정 = {**소형, "시총하한": 3000, "시총상한": 10000}


def 섹터표():
    """value-chain-map.md 에서 섹터 -> 종목코드 (2026-09-07)

    ⚠️ 이름으로 짝짓는다. 비상장이거나 이름이 다르면 못 찾는다 (10개).
       못 찾은 것은 조용히 빠지므로 **개수를 반드시 찍는다**
    """
    import re as _re
    p = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data", "value-chain-map.md")
    if not os.path.exists(p):
        return {}
    t2 = io.open(p, encoding="utf-8").read()
    g = sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json")))
    이름표 = {}
    for f in g[-1:]:
        d = json.load(io.open(f, encoding="utf-8-sig"))
        for c, v in d["종목"].items():
            n = (v.get("이름") or "").strip()
            if n:
                이름표.setdefault(n, c)
    out = {}
    for s in _re.split(r"^### ", t2, flags=_re.M)[1:]:
        라 = s.split("\n")[0].strip()
        라 = _re.sub(r"\s*\(.*", "", 라).strip()
        m = _re.search(r"`\"(.+?)\[", s, _re.S)
        if not m:
            continue
        코 = [이름표[n.strip()] for n in m.group(1).split(" OR ")
              if n.strip() in 이름표]
        if 코:
            out[라] = set(코)
    return out


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
            if 시총 < 1e10 or 시총 >= 2e13:
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
            # ⚠️⚠️ **훑을 값은 수집에서 걸지 않는다** (2026-09-07 고침).
            #    size_lab 을 베낄 때 볼린저 -1.0 · 낙폭 -10 이 여기 박혀 있어서
            #    시뮬에서 완화해도 **없는 것을 못 만들었다** — 9가지가 전부
            #    같은 값(6,586,181원 · 52건)으로 나왔다. 그게 버그의 신호였다
            if 볼 > _느볼 or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > _느낙:
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
                  and x["회전율"] >= c["회전율하한"]
                  and x["볼린저"] <= c["볼린저"]
                  and x["낙폭20"] <= c["낙폭20"]
                  and (not c.get("섹터")
                       or x["code"] in c["섹터"])]
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
    섹 = 섹터표()
    print("=" * 96)
    print("  == A 대형주 1~10조 — 갭 위주로 ==")
    print("=" * 96)
    print(머)
    소 = 시뮬(소형)
    표(소, "소형 500~2천억 (지금 규칙)")
    대 = {**소형, "시총하한": 10000, "시총상한": 100000}
    표(시뮬(대), "대형 1~10조 (같은 문턱)", 소)
    print("")
    print("    -- 문턱 완화 (대형은 덜 빠진다) --")
    for 볼 in (-0.3, -0.5, -0.7, -1.0):
        for 낙 in (0, -3, -5, -10):
            c = dict(대)
            c["볼린저"], c["낙폭20"] = 볼, 낙
            표(시뮬(c), "볼" + str(볼) + " 낙" + str(낙) + "%", 소)
    print("")
    print("    -- 갭 위주 (지도에서 갭이 볼린저의 2.3배였다) --")
    for 갭 in (-1.5, -2.0, -2.5, -3.0, -3.5):
        c = dict(대)
        c["볼린저"], c["낙폭20"], c["상대갭"] = -0.3, 0, 갭
        표(시뮬(c), "볼-0.3 낙0% · 갭" + format(갭, "+.1f"), 소)

    print("")
    print("=" * 96)
    print("  == B 14개 섹터 — 그 안에서만 지금 규칙 ==")
    print("=" * 96)
    print("  ⚠️ 섹터당 3~11종목이라 표본이 얇다. 30건 미만이면 믿지 않는다")
    print(머)
    표(소, "소형 (지금 규칙 · 견줄 대상)")
    묶음 = [(k, v) for k, v in sorted(섹.items(), key=lambda z: -len(z[1]))]
    for 라, 코 in 묶음:
        c = {**소형, "시총하한": 0, "시총상한": 9999999,
             "볼린저": -0.3, "낙폭20": 0, "상대갭": -2.0, "섹터": 코}
        r = 시뮬(c)
        꼬 = "" if r["산"] >= 30 else "  ⚠️표본부족"
        표(r, 라[:16] + " (" + str(len(코)) + "종목)" + 꼬)

    print("")
    print("    -- C 섹터 묶음 (표본을 키운다) --")
    # ⚠️⚠️ 이름을  으로 쓰면 **시뮬이 쓰는 날짜별 사건 딕셔너리를 덮어쓴다**
    #    (2026-09-07: 그래서 C절이 전부 「산 것 0건」에 같은 값이 나왔다.
    #      를 덮어쓴 것과 같은 유형 — 한글 이름 충돌이 오늘만 세 번째다)
    섹묶음 = {
        "반도체+AI+로봇": ("반도체/HBM 소부장", "AI 소프트웨어", "휴머노이드/로봇"),
        "조선+해운": ("조선 기자재", "조선 본선", "해운"),
        "방산+우주": ("방산", "우주/스페이스X"),
        "원전+전력": ("원전 기자재", "전력 인프라/변압기"),
        "바이오+의료": ("바이오 CDMO", "의료기기/디지털헬스"),
        "전체 118종목": tuple(섹.keys()),
    }
    for 라, ks in 섹묶음.items():
        코 = set()
        for k in ks:
            코 |= 섹.get(k, set())
        if not 코:
            continue
        c = {**소형, "시총하한": 0, "시총상한": 9999999,
             "볼린저": -0.3, "낙폭20": 0, "상대갭": -2.0, "섹터": 코}
        r = 시뮬(c)
        꼬 = "" if r["산"] >= 30 else "  ⚠️표본부족"
        표(r, 라 + " (" + str(len(코)) + "종목)" + 꼬, 소)

    print("")

    print("=" * 96)
    print("  읽는 법")
    print("    - **기준보다 끝 자산이 크고 낙폭이 안 나빠져야** 바꿀 값어치가 있다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("    - 섹터는 표본이 얇다. **30건 미만이면 믿지 않는다**")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
