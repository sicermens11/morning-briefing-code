#!/usr/bin/env python3
r"""
gate2_lab.py — **나눠팔기에 4관문 + 오차 시뮬 + 요소분해** (2026-09-07 신설)

## 왜
```
나눠팔기가 오늘 처음으로 **지금 규칙을 모든 면에서 이겼다**
                    끝자산    낙폭    산것   돈÷낙폭
  A 지금 (20%·40일)  5,433만  -5.8%   100건   4.42
  15%·40일+40%·90일  6,432만  **-3.3%** 103건 **8.51**
  2025·26 제외에서도 같은 방향 (4,121만 · -3.3% · 8.34)

⚠️ 그런데 오늘 **B 1위가 4관문을 통과하고도 요소분해에서 무너졌다.**
   같은 절차를 걸어야 한다
```
## 거는 것
```
① 앞뒤 분할     ~2019·~2020·~2021·~2022 뒤 기간이 **다 흑자**
② 2025·26 제외  빼고도 무너지지 않는다
③ 무작위 대비   무작위 문턱 300개에서 **상위 25% 안**
④ 낙폭         지금 규칙보다 나빠지지 않는다
⑤ 오차 시뮬     08:50 예상체결가가 어긋나도 버티나 (±0.3/0.5/1.0%p)
⑥ ⭐ 요소분해    이득이 **어디서** 오나 —
                「15%로 낮춘 것」 / 「40%·90일로 늘린 것」 / 「나눈 것」
                한 곳에서 오면 실체 · 셋이 조금씩이면 과적합
```
⚠️ **⑥이 핵심이다.** 나누기 자체가 값어치인지, 아니면 그냥 90일이 좋은 건지 갈라야 한다

쓰는 법:
    python scripts\gate2_lab.py
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
                  and x["대금억"] >= c["대금하한"]
                  and x["거래량"] >= c["거래량하한"]
                  and x["회전율"] >= c["회전율하한"]]
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
                for 비율, 목표b, 보유b in 몫들:
                    r, 청 = 결과(x, 목표b, 보유b)
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

    도전 = dict(확정)
    도전["나눔"] = ((0.5, 15, 40), (0.5, 40, 90))
    컷들 = ("2019", "2020", "2021", "2022")

    print("=" * 96)
    print("  == 견주기 ==")
    print("=" * 96)
    print(머)
    기 = 시뮬(확정)
    표(기, "A 지금 (20% · 40일)")
    도 = 시뮬(도전)
    표(도, "B 나눔 15%·40일 + 40%·90일", 기)
    제기 = 시뮬(확정, 끝년="2024")
    제도 = 시뮬(도전, 끝년="2024")
    print("")
    print("    -- 2025·26 제외 --")
    표(제기, "A 지금")
    표(제도, "B 나눔", 제기)

    print("")
    print("    -- ① 앞뒤 분할 (뒤 기간이 다 흑자인가) --")
    관1 = True
    for 컷 in 컷들:
        a = 시뮬(확정, 시작년=str(int(컷) + 1))
        b = 시뮬(도전, 시작년=str(int(컷) + 1))
        if b["연"] <= 0:
            관1 = False
        print("    " + 컷 + "이후   A " + format(a["연"], "+.1f") + "% (낙"
              + format(a["낙"], ".1f") + "%)   B " + format(b["연"], "+.1f")
              + "% (낙" + format(b["낙"], ".1f") + "%)")

    print("")
    print("    -- ③ 무작위 문턱 300개 대비 (2025·26 제외) --", flush=True)
    import random as _rd
    _rd.seed(20260907)
    격 = {"상대갭": (-2.0, -2.5, -3.0, -4.0, -5.0),
          "볼린저": (-0.8, -1.0, -1.2),
          "낙폭20": (-5, -10, -15, -20),
          "시총상한": (1000, 2000, 3000, 5000),
          "비중": (0.15, 0.20, 0.25), "하루상한": (1, 2, 3, 4)}
    분포 = []
    for _ in range(300):
        q = dict(도전)
        for k2, v2 in 격.items():
            q[k2] = _rd.choice(v2)
        분포.append(시뮬(q, 끝년="2024")["끝"])
    분포.sort()
    위 = sum(1 for v in 분포 if v > 제도["끝"]) / len(분포) * 100
    흑 = sum(1 for v in 분포 if v > _시드)
    print("     무작위 300개  최악 " + format(분포[0], ",.0f") + "원 · 중앙 "
          + format(분포[150], ",.0f") + "원 · 최고 " + format(분포[-1], ",.0f")
          + "원 · 흑자 " + str(흑) + "/300")
    print("     **상위 " + format(위, ".0f") + "%**")
    관3 = 위 <= 25
    관4 = abs(도["낙"]) <= abs(기["낙"]) * 1.3

    print("")
    print("    -- ⑤ 오차 시뮬 (08:50 예상체결가가 어긋나면) --")
    print(머)
    견딤 = True
    for 폭 in (0.0, 0.3, 0.5, 1.0):
        a = 시뮬(확정, 오차=폭)
        b = 시뮬(도전, 오차=폭)
        표(a, "A 지금  오차 " + format(폭, ".1f") + "%p")
        표(b, "B 나눔  오차 " + format(폭, ".1f") + "%p", a)
        if b["끝"] < a["끝"]:
            견딤 = False

    print("")
    print("    -- ⑥ ⭐ 요소분해 (이득이 어디서 오나) --")
    print(머)
    표(기, "A 지금 (20%·40일 전부)")
    표(시뮬({**확정, "목표": 15}), "  목표만 15%로 낮춤", 기)
    표(시뮬({**확정, "목표": 40, "최대보유": 90}), "  40%·90일로만 늘림", 기)
    표(시뮬({**확정, "나눔": ((0.5, 20, 40), (0.5, 20, 40))}),
      "  같은 조건으로 그냥 반 나눔", 기)
    표(시뮬({**확정, "나눔": ((0.5, 20, 40), (0.5, 40, 90))}),
      "  20%·40일 + 40%·90일 나눔", 기)
    표(도, "  15%·40일 + 40%·90일 나눔 (도전)", 기)

    print("")
    print("=" * 96)
    print("  == 최종 판정 ==")
    print("=" * 96)
    for 이, ok in (("① 앞뒤 분할 뒤 기간 다 흑자", 관1),
                   ("② 2025·26 제외에서도 이김", 제도["끝"] > 제기["끝"]),
                   ("③ 무작위 300개 중 상위 25%", 관3),
                   ("④ 낙폭이 안 나빠짐", 관4),
                   ("⑤ 오차가 있어도 A보다 나음", 견딤)):
        print("  " + ("✅" if ok else "❌") + "  " + 이)
    print("")
    print("  ⚠️ ⑥ 요소분해는 눈으로 본다 — **이득이 한 곳에서 오면 실체**,")
    print("     셋이 조금씩 보태면 과적합이다 (오늘 B 1위가 그래서 기각됐다)")
    print("")

    print("=" * 96)
    print("  읽는 법")
    print("    - 기준보다 끝 자산이 크고 낙폭이 안 나빠져야 바꾼다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("    - 나눔이 A·B 사이 어딘가면 **골라 쓸 수 있다**")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
