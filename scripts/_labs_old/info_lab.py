#!/usr/bin/env python3
r"""
info_lab.py — **지도2에서 값이 있던 신호를 자본 시뮬로** (2026-09-07 신설)

## 지도2(평균 수익)가 가리킨 것 — 소형주 기준선 대비 D+20
```
⑪ 증권사 리포트      **+2.76%p**  (표본 1,190)   가장 강하다
⑧ 그밖의 공시         +1.61%p    (29,983)
⑬ 임원 지분 증가       +0.96%p    (2,793)
⑦ 챙길공시(중요)       **-0.56%p**  <- 오히려 나쁘다
⑨ 계약 공시          **-1.23%p**  <- 수주가 나오면 나쁘다
⑩ 계약 매출10%↑      **-1.51%p**
```
## 재는 것 — 두 갈래
```
A **더하기** — 그 신호가 있는 것만 산다 (후보가 줄어든다)
B ⭐ **빼기** — 그 신호가 있는 것을 뺀다 (후보가 덜 줄어든다)
   지금까지 기각한 열둘은 전부 **좋은 것을 고르는** 조건이었다.
   **나쁜 것을 빼는** 조건은 안 해봤다 (97d 증자·감자 하나뿐)
```
⚠️ 평균이 좋아도 자본 시뮬에서 **열한 번 졌다**. 여기서 재는 건 전부 돈이다
⚠️ **소형 규칙(5,433만 · 연 +25.67% · 낙폭 -5.8%)을 못 이기면 안 쓴다**

쓰는 법:
    python scripts\info_lab.py
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

    # ── 신호 자료 (2026-09-07) ──
    print("  신호 자료 읽는 중...", flush=True)
    챙길, 그밖, 계약, 리포트, 임원 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            dd = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = dd.get("기준일")
        if not d8:
            continue
        for k, 통 in (("챙길공시", 챙길), ("그밖의공시", 그밖)):
            통[d8] = {str(x.get("종목코드") or "").zfill(6)
                      for x in (dd.get(k) or []) if x.get("종목코드")}
    for f in sorted(glob.glob(os.path.join(O._DATA, "contract", "*.json"))):
        try:
            dd = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        for _, x in (dd.get("건") or {}).items():
            c2, 날짜2 = x.get("코드"), str(x.get("날짜") or "")
            if c2 and len(날짜2) == 8:
                계약.setdefault(날짜2, set()).add(str(c2).zfill(6))
    for f in sorted(glob.glob(os.path.join(O._DATA, "consensus", "*.json"))):
        try:
            dd = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        for x in (dd.get("리포트") or []):
            c2 = x.get("코드")
            날짜2 = str(x.get("날짜") or "").replace("-", "")
            if c2 and len(날짜2) == 8:
                리포트.setdefault(날짜2, set()).add(str(c2).zfill(6))
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-exec", "*.json"))):
        try:
            dd = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        c2 = str(dd.get("종목") or "").zfill(6)
        for x in (dd.get("이력") or []):
            날짜2 = str(x.get("접수일") or "").replace("-", "")
            if len(날짜2) != 8:
                continue
            try:
                v2 = float(str(x.get("증감") or 0).replace(",", ""))
            except (TypeError, ValueError):
                v2 = 0.0
            if v2 > 0:
                임원.setdefault(날짜2, set()).add(c2)

    # ⚠️ **안전장치** — `날`(거래일 목록)이 성한지 확인 (2026-09-07 네 번 당했다)
    assert isinstance(날, list) and len(날) > 1000, (
        "거래일 목록이 망가졌다: " + repr(날)[:80])

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
                "갭": g, "매수": 매수,
                "챙길": code in (챙길.get(d1) or set()),
                "그밖": code in (그밖.get(d1) or set()),
                "계약": code in (계약.get(d1) or set()),
                "리포트": code in (리포트.get(d1) or set()),
                "임원증가": code in (임원.get(d1) or set())})
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
                       or x["code"] in c["섹터"])
                  and all(x[k2] for k2 in c.get("있어야", ()))
                  and not any(x[k2] for k2 in c.get("없어야", ()))]
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
    print("=" * 96)
    print("  == A 더하기 — 그 신호가 있는 것만 산다 ==")
    print("=" * 96)
    print(머)
    기 = 시뮬(소형)
    표(기, "소형 (지금 규칙)")
    for 키, 라 in (("리포트", "⑪ 증권사 리포트 난 것만"),
                   ("그밖", "⑧ 그밖의 공시 난 것만"),
                   ("임원증가", "⑬ 임원 지분 증가한 것만"),
                   ("챙길", "⑦ 챙길공시 난 것만"),
                   ("계약", "⑨ 계약 공시 난 것만")):
        c = {**소형, "있어야": (키,)}
        표(시뮬(c), 라, 기)

    print("")
    print("=" * 96)
    print("  == B ⭐ 빼기 — 그 신호가 있는 것을 뺀다 ==")
    print("=" * 96)
    print("  ⚠️ 지금까지 기각한 열둘은 전부 **좋은 것을 고르는** 조건이었다")
    print(머)
    표(기, "소형 (지금 규칙)")
    for 키, 라 in (("챙길", "⑦ 챙길공시 난 것 **빼기**"),
                   ("계약", "⑨ 계약 공시 난 것 **빼기**"),
                   ("그밖", "⑧ 그밖의 공시 난 것 빼기 (견줄 것)")):
        c = {**소형, "없어야": (키,)}
        표(시뮬(c), 라, 기)
    c = {**소형, "없어야": ("챙길", "계약")}
    표(시뮬(c), "⑦+⑨ 둘 다 빼기", 기)

    print("")
    print("  ⚠️ 2025·26 제외")
    print(머)
    기2 = 시뮬(소형, 끝년="2024")
    표(기2, "소형 (지금 규칙)")
    for 키, 라 in (("리포트", "⑪ 리포트 난 것만"),
                   ("그밖", "⑧ 그밖의 공시 난 것만")):
        표(시뮬({**소형, "있어야": (키,)}, 끝년="2024"), 라, 기2)
    for 키, 라 in (("챙길", "⑦ 챙길공시 **빼기**"),
                   ("계약", "⑨ 계약 공시 **빼기**")):
        표(시뮬({**소형, "없어야": (키,)}, 끝년="2024"), 라, 기2)
    표(시뮬({**소형, "없어야": ("챙길", "계약")}, 끝년="2024"),
      "⑦+⑨ 둘 다 빼기", 기2)
    print("")

    print("=" * 96)
    print("  읽는 법")
    print("    - **기준보다 끝 자산이 크고 낙폭이 안 나빠져야** 바꿀 값어치가 있다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("    - **빼기**가 이기면 새로운 길이다 — 후보를 덜 줄이면서 손실을 막는다")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
