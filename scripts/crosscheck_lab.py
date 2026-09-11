#!/usr/bin/env python3
r"""
crosscheck_lab.py — **AutoSearch 상위를 「실전 절차」로 다시 잰다** (2026-09-07 신설)

## ⚠️⚠️ 왜 만들었나
```
auto_search.py:232   "상대갭": g - 시갭      시갭 = **시장 전체 중앙갭**
우리 실전 절차                              **후보 40개 중앙갭**
                                           (08:50엔 40개 예상체결가만 볼 수 있다)
⇒ 주말에 돌린 **288,560개가 우리가 못 하는 규칙들의 순위표**였다.
  차이도 작지 않다 — 후보 40개 기준으로 9,769만 vs 8,253만 (-15%)
```
⚠️ auto_search 에서 갭 필터를 빼면 후보가 13,874 -> 108,492건(8배)이 되어
   28만 개 훑기가 50시간 -> 400시간이 된다. **실용적이지 않다.**
⇒ auto_search 는 **빠른 1차 선별**로 두고, 여기서 **상위만 실전 절차로 재검증**한다

## 재는 것
```
같은 조합을 두 잣대로 돌려 견준다
  A 전종목중앙갭   auto_search 가 쓰는 것 (실전 불가)
  B 후보중앙갭     우리가 실제로 하는 것
⇒ **순위가 A에서 B로 옮겨가는지**가 핵심이다.
  안 옮겨가면 auto_search 순위표는 **선별 도구로도 못 쓴다**
```

쓰는 법:
    python scripts\crosscheck_lab.py              상위 10개 + 우리 규칙
    python scripts\crosscheck_lab.py --개수 20
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
_후보수 = 40                    # 08:00에 브리핑이 주는 개수
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RS = os.path.join(_BASE, "data", "_search", "결과.jsonl")

# 우리 확정 규칙 (record_pick.py 와 같은 값)
우리 = {"잉여금": 30, "부채": 80, "흑자필수": True, "상대갭": -3,
        "볼린저": -1.0, "낙폭20": -10, "시총상한": 2000, "목표": 20,
        "최대보유": 40, "비중": 0.20, "하루상한": 4,
        "미국조건": None, "시장갭조건": None}


def 점수(z):
    연 = z["걷기"]["연"]
    낙 = abs(z["전체"]["낙폭"]) or 3.0
    return 연 / max(낙, 3.0)


def 상위뽑기(n):
    """세 판 통과 + 표본 충분 + 모든 해 흑자 + 제외판 25%↑ + 낙폭 15% 이내"""
    좋 = []
    if not os.path.exists(_RS):
        return 좋
    for x in io.open(_RS, encoding="utf-8"):
        x = x.strip()
        if not x:
            continue
        try:
            z = json.loads(x)
        except ValueError:
            continue
        if not z.get("통과"):
            continue
        t = z["전체"]
        if (t["신호일"] >= 100 and t["플"] == t["전"] == 11
                and z["제외판"]["연"] >= 25 and abs(t["낙폭"]) <= 15):
            z["점"] = 점수(z)
            좋.append(z)
    좋.sort(key=lambda z: -z["점"])
    return 좋[:n]


def main():
    개수 = 10
    if "--개수" in sys.argv:
        개수 = int(sys.argv[sys.argv.index("--개수") + 1])

    상위 = 상위뽑기(개수)
    print("=" * 92)
    print("  AutoSearch 상위를 **실전 절차(후보중앙갭)**로 다시 잰다")
    print("=" * 92)
    print(f"  견줄 조합 {len(상위)}개 + 우리 확정 규칙 1개\n")

    # ── 자료 ──
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종, 원시 = {}, {}, {}, {}, {}
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
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

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

    # ── ⚠️ **갭 조건 없이** 모은다. 40개를 고르려면 갭을 몰라야 한다 ──
    #    (08:00에는 갭이 아직 없다. 갭은 09:00 시가로 정해진다)
    print("  후보 모으는 중 (갭 조건 없이 · 몇 분 걸린다)...", flush=True)
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 5e11:
                continue
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
            if 볼 > -0.7 or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > -5:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            g = 하루갭.get(code)
            if g is None:
                continue
            사건.append({
                "인": i + 1, "날": 다음, "code": code, "원시": o0,
                "대금": b0[2], "볼린저": 볼, "낙폭20": 낙,
                "시총": 시총 / 1e8, "갭": g, "시장갭": 시갭,
                "상대갭": g - 시갭,
                "잉여금": fm.get("잉여금비율"), "부채": fm.get("부채비율"),
                "흑자": fm.get("흑자"),
                "주가i": i + 1})
    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  후보 {len(사건):,}건 · {len(묶):,}일\n", flush=True)

    # 청산 결과를 미리 계산해 둔다 (조합마다 목표·보유가 달라 캐시는 키를 나눈다)
    결과캐시 = {}

    def 결과내기(x, 목표, 보유):
        키 = (x["인"], x["code"], 목표, 보유)
        v = 결과캐시.get(키)
        if v is not None:
            return v
        i = x["인"] - 1
        매수 = 주가[날[x["인"]]][x["code"]][0] * 비[날[x["인"]]][x["code"]][0]
        r, 청 = None, None
        for h in range(0, 보유 + 1):
            j = i + 1 + h
            if j >= len(날):
                break
            vv = 주가[날[j]].get(x["code"])
            b2 = (비.get(날[j]) or {}).get(x["code"])
            if not vv or not b2:
                break
            if vv[0] * b2[1] >= 매수 * (1 + 목표 / 100):
                r, 청 = 목표 - _비용, j
                break
        if r is None:
            j = i + 1 + 보유
            if j >= len(날):
                결과캐시[키] = (None, None)
                return (None, None)
            끝 = 주가[날[j]].get(x["code"])
            if not 끝:
                결과캐시[키] = (None, None)
                return (None, None)
            r, 청 = (끝[0] / 매수 - 1) * 100 - _비용, j
        결과캐시[키] = (r, 청)
        return (r, 청)

    def 시뮬(c, 잣대, 끝년=None):
        """잣대: '전종목' = 시장 전체 중앙갭 / '후보' = 후보 N개 중앙갭"""
        현금, 보유, 곡, 산 = _시드, [], [], 0
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
            # ── 08:00에 아는 조건만 걸어 후보를 좁힌다 ──
            칸 = [x for x in (묶.get(i) or [])
                  if (x["잉여금"] or -9e9) >= c["잉여금"]
                  and (x["부채"] or 9e9) <= c["부채"]
                  and (not c["흑자필수"] or x["흑자"] == 1.0)
                  and x["볼린저"] <= c["볼린저"]
                  and x["낙폭20"] <= c["낙폭20"]
                  and x["시총"] < c["시총상한"]]
            if c.get("시장갭조건") is not None:
                칸 = [x for x in 칸 if x["시장갭"] < c["시장갭조건"]]
            if not 칸:
                곡.append(평)
                continue
            if 잣대 == "후보":
                # ⚠️ **좁힌 뒤에** 그 안에서 중앙갭을 낸다 — 08:50에 보는 것이 이것뿐이다
                칸 = sorted(칸, key=lambda z: z["낙폭20"])[:_후보수]
                if len(칸) < 3:
                    곡.append(평)
                    continue
                중 = st.median([x["갭"] for x in 칸])
                def 상(x, _중=중):
                    return x["갭"] - _중
            else:
                def 상(x):
                    return x["상대갭"]
            골 = sorted([x for x in 칸 if 상(x) <= c["상대갭"]], key=상)
            for x in 골[:c["하루상한"]]:
                r, 청 = 결과내기(x, c["목표"], c["최대보유"])
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
        연 = ((끝 / _시드) ** (1 / 해) - 1) * 100 if 끝 > 0 else -100
        최고, 낙 = _시드, 0.0
        for v in 곡:
            최고 = max(최고, v)
            낙 = min(낙, v / 최고 - 1)
        return {"끝": 끝, "연": 연, "낙": 낙 * 100, "산": 산}

    def 라벨(c):
        s = (f"잉{c['잉여금']}부{c['부채']}{'흑' if c['흑자필수'] else ''} "
             f"갭{c['상대갭']}볼{c['볼린저']}낙{c['낙폭20']} "
             f"시총{c['시총상한']} 목표{c['목표']}보유{c['최대보유']} "
             f"{int(c['비중']*100)}%x{c['하루상한']}")
        return s + (" 시장갭" if c.get("시장갭조건") else "")

    줄들 = [("**우리 확정 규칙**", 우리)]
    for n, z in enumerate(상위, 1):
        줄들.append((f"AutoSearch {n}위", z["조건"]))

    머 = (f"  {'조합':<16}{'A 전종목중앙갭':>28}{'B 후보중앙갭':>28}"
          f"{'B/A':>8}")
    print(머)
    print(f"  {'':<16}{'끝자산':>16}{'연':>7}{'낙폭':>5}"
          f"{'끝자산':>16}{'연':>7}{'낙폭':>5}{'':>8}")
    모음 = []
    for 라, c in 줄들:
        a = 시뮬(c, "전종목")
        b = 시뮬(c, "후보")
        모음.append((라, c, a, b))
        print(f"  {라:<16}{a['끝']:>15,.0f}원{a['연']:>+6.1f}%{a['낙']:>5.0f}%"
              f"{b['끝']:>15,.0f}원{b['연']:>+6.1f}%{b['낙']:>5.0f}%"
              f"{b['끝']/max(a['끝'],1)*100:>7.0f}%", flush=True)

    # ── 순위가 옮겨가나 ──
    print("\n" + "=" * 92)
    print("  ══ 순위가 A에서 B로 옮겨가나 ══")
    A순 = sorted(range(len(모음)), key=lambda k: -모음[k][2]["끝"])
    B순 = sorted(range(len(모음)), key=lambda k: -모음[k][3]["끝"])
    print(f"  {'조합':<16}{'A 등수':>8}{'B 등수':>8}{'움직임':>10}")
    for k, (라, c, a, b) in enumerate(모음):
        ai, bi = A순.index(k) + 1, B순.index(k) + 1
        print(f"  {라:<16}{ai:>8}{bi:>8}{bi-ai:>+10}")
    n = len(모음)
    같 = sum(1 for k in range(n) if A순.index(k) == B순.index(k))
    print(f"\n  등수가 그대로인 것 {같}/{n}개")
    print("  ⚠️ 크게 뒤바뀌면 auto_search 순위표는 **선별 도구로도 못 쓴다**")

    print("\n  ── 조합 ──")
    for 라, c, a, b in 모음:
        print(f"    {라:<16}{라벨(c)}")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    sys.exit(main())
