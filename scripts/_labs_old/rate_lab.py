#!/usr/bin/env python3
r"""
rate_lab.py — **금리 국면별로 우리 전략이 어떻게 다른가** (2026-09-03 · 91차)

⚠️⚠️ **사용자 지목.** *"금리는 필요하지 않아? 국채금리, 중앙은행 금리!
   지금 한참 금리 인상으로 화제니까"*

## 88차에서 뭘 잘못했나
```
금리를 **하루 변화율**로 쟀다 -> 「저금리였던 해」를 고르는 **가짜**였다
bp 변화폭으로 다시 재도 약했다
⇒ **하루 변동은 잡음이다.** 국면은 다른 이야기다
```

## 여기서 재는 것 — **수준과 국면**
```
A 금리 **수준**       0~1% · 1~3% · 3~5% · 5%↑ 구간별로 우리 전략 성적
B 금리 **국면**       인상기 · 인하기 · 동결기 (3개월 변화로 나눈다)
C ⭐ **장단기 역전**   (10년물 − 2년물) < 0 = 침체 신호. 그때 사면?
D **금리 변경일 전후**  목표금리가 바뀐 날 ±5일
E ⭐⭐ **자본 시뮬**   국면에 따라 비중을 바꾸면 돈이 더 느나
```

⚠️⚠️ **표본이 적다는 걸 먼저 밝힌다.**
   10.4년에 국면이 대여섯 번뿐이다. 연도별 3분의 2 판정을 그대로 쓸 수 없다.
   ⇒ **국면마다 몇 해가 들어있는지**를 같이 적는다. 한 해짜리 국면은 믿지 않는다

⚠️ 시차: 금리는 미국 것이라 T-1일 값이 T일 새벽에 확정된다. 그대로 쓸 수 있다
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
_목표 = 20.0
_최대보유 = 40
_FR = os.path.join(O._DATA, "fred")
_YH = os.path.join(O._DATA, "yahoo")


def 읽금리(p, 키="값"):
    if not os.path.exists(p):
        return {}
    d = json.load(io.open(p, encoding="utf-8-sig"))
    return d.get(키) or d.get("종가") or {}


def 앞값(표, ks, d):
    """d **이전**의 가장 가까운 값 (그날 값은 안 쓴다 — 미리보기 방지)"""
    import bisect
    i = bisect.bisect_left(ks, d)
    return 표[ks[i - 1]] if i > 0 else None


def main():
    기준 = 읽금리(os.path.join(_FR, "AV_FEDFUNDS.json"))
    년2 = 읽금리(os.path.join(_FR, "AV_DGS2.json"))
    년10 = 읽금리(os.path.join(_YH, "IDX_TNX.json"), "종가")
    if not 기준:
        print("  ⚠️ 미국 기준금리 자료가 없다 (data/fred/AV_FEDFUNDS.json)")
        return 1
    k기, k2, k10 = sorted(기준), sorted(년2), sorted(년10)
    print(f"  기준금리 {len(기준):,}일 · 2년물 {len(년2):,}일 · "
          f"10년물 {len(년10):,}일\n", flush=True)

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

    # ── 날짜별 금리 상태 ──
    상태 = {}
    for i, d in enumerate(날):
        if d < _시작:
            continue
        r = 앞값(기준, k기, d)
        if r is None:
            continue
        # 3개월(63거래일) 전 대비 변화
        전 = 날[max(0, i - 63)]
        r0 = 앞값(기준, k기, 전)
        국면 = "모름"
        if r0 is not None:
            차 = r - r0
            국면 = "인상" if 차 >= 0.20 else ("인하" if 차 <= -0.20 else "동결")
        v2 = 앞값(년2, k2, d)
        v10 = 앞값(년10, k10, d)
        역전 = (v10 - v2) if (v2 is not None and v10 is not None) else None
        상태[d] = {"수준": r, "국면": 국면, "차": 역전}

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

    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작 or 다음 not in 상태:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -3:
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
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
            if (c1 - s20) / (2 * sd) > -1.0 or sq[kk - 20] <= 0:
                continue
            if (c1 / sq[kk - 20] - 1) * 100 > -10:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결과, 청산 = None, None
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                bb2 = (비.get(날[j]) or {}).get(code)
                if not vv or not bb2:
                    break
                if vv[0] * bb2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 청산 = _목표 - _비용, j
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            사건.append({"날": 다음, "인": i + 1, "청산": 청산, "결과": 결과,
                         "원시": o0, "대금": b0[2], "상대갭": g - 시갭,
                         "도달": 결과 > _목표 - _비용 - 1e-9,
                         **상태[다음]})
    n = len(사건)
    기준도달 = sum(1 for x in 사건 if x["도달"]) / n * 100
    기준평균 = st.mean([x["결과"] for x in 사건])
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  사건 {n:,}건 · 기준선 도달률 {기준도달:.1f}% · "
          f"평균 {기준평균:+.2f}% · {년수:.1f}년\n", flush=True)

    def 재기(a, 라, 폭=26):
        if len(a) < 20:
            print(f"    {라:<{폭}}{len(a):>7}건   ⚠️ 표본 부족")
            return
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        m = st.mean([x["결과"] for x in a])
        해 = sorted({x["날"][:4] for x in a})
        전 = 플 = 0
        묶 = {}
        for x in a:
            묶.setdefault(x["날"][:4], []).append(x["결과"])
        for y, arr in 묶.items():
            if len(arr) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        # ⚠️ 몇 해에 걸쳐 있는지를 반드시 같이 본다
        경 = "⚠️" if len(해) <= 2 else "  "
        print(f"    {라:<{폭}}{len(a):>7}건{d2:>8.1f}%{d2-기준도달:>+8.1f}%p"
              f"{m:>+9.2f}%{f'{플}/{전}':>7}  {경}{','.join(h[2:] for h in 해)}")

    머 = (f"    {'구간':<26}{'표본':>9}{'도달률':>8}{'기준대비':>9}"
          f"{'평균':>9}{'연도별':>7}  {'걸친 해'}")

    # ══ A 수준 ══
    print("  ══ A **금리 수준별** ══")
    print("     미국 기준금리가 몇 %일 때 우리 전략이 잘 됐나")
    print(머)
    for 아, 위, 라 in ((0, 1, "0~1% (제로금리)"), (1, 3, "1~3%"),
                      (3, 5, "3~5%"), (5, 99, "5%↑ (고금리)")):
        재기([x for x in 사건 if 아 <= x["수준"] < 위], 라)

    # ══ B 국면 ══
    print(f"\n  ══ B **금리 국면별** (3개월 변화로 나눈다) ══")
    print("     인상 = 3개월새 +0.20%p↑ · 인하 = −0.20%p↓ · 나머지 동결")
    print(머)
    for g in ("인상", "동결", "인하"):
        재기([x for x in 사건 if x["국면"] == g], f"{g}기")

    # ══ C 장단기 역전 ══
    print(f"\n  ══ C ⭐ **장단기 역전** (10년물 − 2년물) ══")
    print("     0보다 작으면 **역전**. 예로부터 침체 신호로 본다")
    print(머)
    있 = [x for x in 사건 if x.get("차") is not None]
    print(f"     (금리차를 아는 사건 {len(있):,}/{n:,}건)")
    재기([x for x in 있 if x["차"] < 0], "역전 (10Y < 2Y)")
    재기([x for x in 있 if 0 <= x["차"] < 1], "정상 0~1%p")
    재기([x for x in 있 if x["차"] >= 1], "가파름 1%p↑")

    # ══ D 금리 변경일 ══
    print(f"\n  ══ D **금리가 바뀐 날 언저리** ══")
    변 = []
    for j in range(1, len(k기)):
        if k기[j] < "20150101":
            continue
        if abs(기준[k기[j]] - 기준[k기[j - 1]]) >= 0.10:
            변.append(k기[j])
    print(f"     기준금리가 0.10%p 이상 바뀐 날 {len(변)}일 (2015~)")
    변셋 = set()
    날인 = {d: i for i, d in enumerate(날)}
    for v in 변:
        앞 = [d for d in 날 if d >= v]
        if 앞:
            i = 날인[앞[0]]
            for o in range(-3, 4):
                if 0 <= i + o < len(날):
                    변셋.add(날[i + o])
    print(머)
    재기([x for x in 사건 if x["날"] in 변셋], "변경일 ±3거래일")
    재기([x for x in 사건 if x["날"] not in 변셋], "그 외")

    # ══ E 자본 시뮬 ══
    print(f"\n  ══ E ⭐⭐ **자본 시뮬** — 국면으로 비중을 바꾸면 ══")
    print("     자산 500만원 · 20%씩 · 하루 2종목 · 1주 단위 · 현금 연 2.5%")
    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)

    def 시뮬(비중함, 라, 끝년=None):
        현금, 보유, 곡, 산 = 5_000_000.0, [], [], 0
        for i, d in enumerate(날):
            if d < _시작:
                continue
            if 끝년 and d[:4] > 끝년:
                break
            남 = []
            for p in 보유:
                if p["청산"] <= i:
                    현금 += p["주수"] * p["원시"] * (1 + p["결과"] / 100)
                else:
                    남.append(p)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(p["주수"] * p["원시"] for p in 보유)
            for x in sorted(묶.get(i, []), key=lambda z: z["상대갭"])[:2]:
                w = 비중함(x)
                if w <= 0:
                    continue
                쓸 = min(평 * w, 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])    # 주수는 **원본 시가**로
                if 주수 < 1:
                    continue
                실 = 주수 * x["원시"]
                if 실 > 현금:
                    continue
                현금 -= 실
                보유.append({**x, "주수": 주수})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(p["주수"] * p["원시"] for p in 보유)
        yr = len(곡) / 245
        cagr = ((끝 / 5_000_000) ** (1 / max(yr, 0.1)) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        print(f"    {라:<30}{끝:>15,.0f}원{cagr:>+9.2f}%{낙:>8.1f}%{산:>7}건")
        return cagr

    print(f"    {'전략':<30}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")
    시뮬(lambda x: 0.20, "원판 (늘 20%)")
    시뮬(lambda x: 0.30 if x["국면"] == "인하" else 0.15, "인하기 30% / 아니면 15%")
    시뮬(lambda x: 0.30 if x["국면"] == "인상" else 0.15, "인상기 30% / 아니면 15%")
    시뮬(lambda x: 0.30 if x["수준"] < 2 else 0.15, "저금리 30% / 아니면 15%")
    시뮬(lambda x: 0.30 if x["수준"] >= 3 else 0.15, "고금리 30% / 아니면 15%")
    시뮬(lambda x: 0.30 if (x.get("차") is not None and x["차"] < 0)
         else 0.15, "역전 때 30% / 아니면 15%")
    print("\n    ⚠️ 2025·26 제외")
    시뮬(lambda x: 0.20, "원판", 끝년="2024")
    시뮬(lambda x: 0.30 if x["국면"] == "인하" else 0.15, "인하기 30%/15%",
         끝년="2024")
    시뮬(lambda x: 0.30 if x["수준"] >= 3 else 0.15, "고금리 30%/15%",
         끝년="2024")

    print("\n  읽는 법")
    print("    - ⚠️ 표시는 **두 해 이하**에만 걸쳐 있는 구간이다. 믿지 않는다")
    print("    - E에서 원판을 확실히 이기지 못하면 금리를 볼 이유가 없다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
