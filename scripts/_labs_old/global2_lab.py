#!/usr/bin/env python3
r"""
global2_lab.py — **88b차. 88차의 1등이 가짜여서 다시 잰다** (2026-09-03)

## 88차에서 무엇이 틀렸나
```
1등 「미국13주 −0.5%↓」 +13.8%p  ← **가짜였다**
   금리는 값 자체가 %다. 그 값의 **변화율**을 재면 안 된다.
   2021년 금리 평균 **0.02%** → 0.01%로 가면 **−50%**
   ⇒ −0.5% 조건이 2020년 116회 · 2021년 88회 vs 2024년 **20회**
   ⇒ 이건 신호가 아니라 **「저금리였던 해」를 고르는 장치**다
```
⇒ 여기서는 금리를 **bp(0.01%p) 변화폭**으로 다시 잰다.

## 두 번째 문제 — **표본이 줄면 신호 빈도도 준다**
```
88차는 「그 조건이 맞은 날의 사건」만 봤다.
조건을 걸수록 도달률은 오르지만 **살 날이 줄어든다.**
평균 수익이 좋아도 **1년에 3번밖에 못 사면 돈은 안 는다.**
⇒ 여기서는 **자본 시뮬**로 끝 자산까지 낸다 (「평균 수익은 돈이 아니다」)
```

## 재는 것
```
A 금리를 **bp**로 다시            (13주·5년·10년·30년)
B ⭐ **XLK vs IWM** 최종 답
C 아시아 (⚠️ 하루 늦게)
D ⭐⭐ 상위 후보 **자본 시뮬**      — 조건을 걸면 **돈**이 더 느나
```
⚠️ 연도별은 **9해 이상 표본이 있는 것만** ⭐를 준다 (88차는 2/2에도 ⭐를 줬다)
"""
import datetime as dt
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
_YH = os.path.join(O._DATA, "yahoo")
아시아 = {"IDX_N225", "000001.SS", "IDX_HSI", "IDX_TWII"}
금리 = {"IDX_IRX", "IDX_FVX", "IDX_TNX", "IDX_TYX"}


def main():
    지표 = {}
    for f in sorted(glob.glob(os.path.join(_YH, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        키 = os.path.basename(f)[:-5]
        종 = d.get("종가") or {}
        if len(종) < 500:
            continue
        k = sorted(종)
        변 = {}
        for j in range(1, len(k)):
            p = 종[k[j - 1]]
            if p is None:
                continue
            # 금리는 **bp 변화폭**. 값이 이미 %라 변화율을 쓰면 안 된다
            if 키 in 금리:
                변[k[j]] = (종[k[j]] - p) * 100
            elif p:
                변[k[j]] = (종[k[j]] / p - 1) * 100
        지표[키] = {"이름": d.get("이름") or 키, "변": 변,
                    "아시아": 키 in 아시아, "금리": 키 in 금리}

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
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                거 = float(v.get("거래대금") or 0)
                if min(종, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종, 고 / 종, 거)
            원시.setdefault(d8, {})[c] = 시
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

    쓸값 = {}
    for 키, v in 지표.items():
        ek = sorted(v["변"])
        t = {}
        for i, d in enumerate(날):
            기준 = 날[i - 1] if (v["아시아"] and i > 0) else d
            앞 = [x for x in ek if x < 기준]
            if not 앞:
                continue
            전 = max(앞)
            try:
                if (dt.datetime.strptime(기준, "%Y%m%d")
                        - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                    continue
            except Exception:
                pass
            t[d] = v["변"][전]
        쓸값[키] = t

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
        if 다음 < _시작:
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
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0 or sq[k - 20] <= 0:
                continue
            if (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결과, 며칠, 청산 = None, _최대보유, None
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    break
                if vv[0] * bb2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 며칠, 청산 = _목표 - _비용, max(1, h), j
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            사건.append({"날": 다음, "인": i + 1, "청산": 청산, "code": code,
                         "결과": 결과, "며칠": 며칠, "원시": o0,
                         "도달": 결과 > _목표 - _비용 - 1e-9,
                         "대금": b0[2], "상대갭": g - 시갭})
    n = len(사건)
    기준도달 = sum(1 for x in 사건 if x["도달"]) / n * 100
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  사건 {n:,}건 · 기준선 도달률 {기준도달:.1f}% · {년수:.1f}년\n",
          flush=True)

    def 재기(a, 라, 폭=24):
        if len(a) < 30:
            return None
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        m = st.mean([x["결과"] for x in a])
        해 = {}
        for x in a:
            해.setdefault(x["날"][:4], []).append(x["결과"])
        전 = 플 = 0
        for y, arr in 해.items():
            if len(arr) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        별 = "⭐" if (d2 - 기준도달 > 4 and 전 >= 9 and 플 / 전 >= 2 / 3) else "  "
        print(f"    {라:<{폭}}{len(a):>7}건{d2:>8.1f}%{d2-기준도달:>+8.1f}%p"
              f"{m:>+9.2f}%{f'{플}/{전}':>8}{별}")
        return (d2 - 기준도달, 전)

    머 = (f"    {'지표':<24}{'표본':>9}{'도달률':>8}{'기준대비':>9}"
          f"{'평균':>9}{'연도별':>8}")
    승 = {}

    print("  ══ A **금리를 bp(0.01%p) 변화폭으로 다시** ══")
    print("     ⚠️ 88차는 변화율로 재서 「저금리였던 해」를 골랐다. 그건 가짜다")
    print(머)
    for 키 in ("IDX_IRX", "IDX_FVX", "IDX_TNX", "IDX_TYX"):
        t = 쓸값.get(키) or {}
        for 문 in (-3, -5, -8):
            a = [x for x in 사건 if t.get(x["날"]) is not None and t[x["날"]] <= 문]
            r = 재기(a, f"{지표[키]['이름']} {문}bp↓")
            if r and r[1] >= 9 and r[0] > 3:
                승[f"{키}{문}"] = (r[0], 키, 문, a)

    print(f"\n  ══ B ⭐⭐ **XLK(기술) vs IWM(소형주)** — 최종 답 ══")
    print(머)
    for 키 in ("XLK", "IWM", "QQQ", "SOXX", "SPY"):
        t = 쓸값.get(키) or {}
        for 문 in (-1.0, -1.5, -2.0):
            a = [x for x in 사건 if t.get(x["날"]) is not None and t[x["날"]] <= 문]
            r = 재기(a, f"{지표[키]['이름']} {문}%↓")
            if r and r[1] >= 9 and r[0] > 3:
                승[f"{키}{문}"] = (r[0], 키, 문, a)

    print(f"\n  ══ C **아시아** (⚠️ 하루 늦게 반영) ══")
    print(머)
    for 키 in ("IDX_HSI", "IDX_TWII", "000001.SS", "IDX_N225"):
        t = 쓸값.get(키) or {}
        for 문 in (-0.5, -1.0):
            a = [x for x in 사건 if t.get(x["날"]) is not None and t[x["날"]] <= 문]
            r = 재기(a, f"{지표[키]['이름']} {문}%↓")
            if r and r[1] >= 9 and r[0] > 3:
                승[f"{키}{문}"] = (r[0], 키, 문, a)

    print(f"\n  ══ D ⭐⭐ **자본 시뮬** — 조건을 걸면 **돈**이 더 느나 ══")
    print("     자산 500만원 · 20%씩 · 하루 2종목 · 1주 단위 · 현금 연 2.5%")
    print("     ⚠️ 도달률이 올라도 **살 날이 줄면** 돈은 덜 는다")

    def 시뮬(고른, 라):
        현금, 보유 = 5_000_000.0, []
        묶 = {}
        for x in 고른:
            묶.setdefault(x["인"], []).append(x)
        곡, 산것 = [], 0
        for i in range(len(날)):
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
                쓸 = min(평 * 0.20, 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])   # 주수는 **원본 시가**로
                if 주수 < 1:
                    continue
                실 = 주수 * x["원시"]
                if 실 > 현금:
                    continue
                현금 -= 실
                보유.append({**x, "주수": 주수})
                산것 += 1
            곡.append(평)
        끝 = 현금 + sum(p["주수"] * p["원시"] for p in 보유)
        cagr = ((끝 / 5_000_000) ** (1 / 년수) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        해 = {}
        for j, d in enumerate(날):
            해.setdefault(d[:4], []).append(곡[j])
        전 = 플 = 0
        for y in sorted(해):
            if y < "2016" or len(해[y]) < 100:
                continue
            전 += 1
            플 += 1 if 해[y][-1] > 해[y][0] else 0
        print(f"    {라:<26}{끝:>15,.0f}원{cagr:>+9.2f}%{낙:>8.1f}%"
              f"{산것:>7}건{f'{플}/{전}':>8}")
        return cagr

    print(f"    {'전략':<26}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}"
          f"{'산 것':>7}{'연도별':>8}")
    기준c = 시뮬(사건, "조건 없음 (원판)")
    for r, 키, 문, a in sorted(승.values(), reverse=True)[:10]:
        표 = "bp↓" if 지표[키]["금리"] else "%↓"
        시뮬(a, f"+ {지표[키]['이름']} {문}{표}")

    print(f"\n  읽는 법")
    print(f"    - D의 **끝 자산**이 원판({기준c:+.2f}%)보다 커야 진짜 쓸모다")
    print("    - 도달률만 오르고 끝 자산이 줄면 **살 날이 줄어든 것**이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
