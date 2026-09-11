#!/usr/bin/env python3
r"""
cons_lab.py — **컨센서스(애널리스트)가 값을 하나** (2026-09-04 · 106차)

## ⚠️ 왜 이제야 재나
```
87차에 하려다 밀렸다. 그동안 「미검증」으로 남아 있었다.
사용자 질문: *"종목 추천에 ... 실적발표 애널리스트, 증권가 의견 ... 반영돼?"*
-> ⑥ 액션플랜은 쓰고 있는데, **우리 검증된 규칙(⑦)은 안 쓴다.**
   안 쓰는 게 맞는지 **재본 적이 없다.** 여기서 잰다
```

## 자료 (peek.py로 먼저 확인함)
```
data/consensus/{YYYYMM}.json  81개월 · **2020-01 ~ 2026-09**
   {"달":202609, "건수":3, "리포트":[{날짜·목표주가·의견·작성자·제목·증권사·코드}]}
⚠️ **6.7년뿐이다** (주가는 10.4년). 표본이 줄어든다
⚠️ 시차: 리포트 날짜가 **신호 전날까지**인 것만 쓴다
```

## 재는 것
```
A 리포트가 최근에 있었나   (30·90·180일 안)
B ⭐ **목표주가 대비 상승여력**  (목표주가 ÷ 현재가 − 1)
C 의견                  매수·중립 등
D 커버리지               증권사가 몇 곳이나 보나
E ⭐⭐ **자본 시뮬**      원판을 이기나 (여섯 번 다 졌다)
```
⚠️ 판정: 도달률 + 연도별 + **자본 시뮬** + 2025·26 제외
"""
import collections
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
_시작 = "20200101"       # ⚠️ 컨센서스가 2020년부터라 여기 맞춘다
_목표 = 20.0
_최대보유 = 40
확정 = {"갭": -3.5, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "비중": 0.20, "종목수": 4}


def main():
    # ── 컨센서스 (peek.py로 구조 확인함) ──
    리포트 = collections.defaultdict(list)   # 종목 -> [(YYYYMMDD, 목표, 의견, 증권사)]
    총건 = 0
    for f in sorted(glob.glob(os.path.join(O._DATA, "consensus", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for it in (d.get("리포트") or []):
            if not isinstance(it, dict):
                continue
            c = str(it.get("코드") or "").zfill(6)
            날 = "".join(ch for ch in str(it.get("날짜") or "") if ch.isdigit())
            if not c or c == "000000" or len(날) != 8:
                continue
            try:
                목 = float(str(it.get("목표주가") or 0).replace(",", "") or 0)
            except ValueError:
                목 = 0.0
            리포트[c].append((날, 목, str(it.get("의견") or ""),
                             str(it.get("증권사") or "")))
            총건 += 1
    for c in 리포트:
        리포트[c].sort()
    print(f"  컨센서스 {총건:,}건 · 종목 {len(리포트):,}개")
    # ⚠️ 파싱 0건이면 멈춘다 (2026-09-04 교훈)
    if 총건 == 0:
        print("  ⚠️⚠️ **파싱 0건이다.** 필드명이 바뀌었을 수 있다. 멈춘다")
        print("     확인: python scripts/peek.py data/consensus --전부")
        return 2
    의견수 = collections.Counter(x[2] for v in 리포트.values() for x in v)
    print(f"  의견 갈래: " + " · ".join(f"{k or '(빈칸)'}({v:,})"
                                       for k, v in 의견수.most_common(6)))

    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종, 원시, 원종 = {}, {}, {}, {}, {}, {}
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
            원종.setdefault(d8, {})[c] = 종c        # ⚠️ **원본** 종가 (목표주가 비교용)
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

    import bisect
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
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 확정["시총"]:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > 확정["갭"]:
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
            if (c1 - s20) / (2 * sd) > 확정["볼"] or sq[kk - 20] <= 0:
                continue
            if (c1 / sq[kk - 20] - 1) * 100 > 확정["낙"]:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            # ── 컨센서스 (⚠️ **신호 전날까지**만) ──
            줄2 = 리포트.get(code) or []
            앞 = [x for x in 줄2 if x[0] <= d1]
            며칠 = None
            여력 = None
            의견 = ""
            증권사수 = 0
            if 앞:
                마 = 앞[-1]
                import datetime as dt2
                try:
                    며칠 = (dt2.datetime.strptime(d1, "%Y%m%d")
                            - dt2.datetime.strptime(마[0], "%Y%m%d")).days
                except Exception:
                    며칠 = None
                의견 = 마[2]
                # 목표주가는 **원본 종가**와 견준다 (수정주가와 섞으면 안 된다)
                현 = (원종.get(d1) or {}).get(code)
                if 마[1] > 0 and 현 and 현 > 0:
                    여력 = (마[1] / 현 - 1) * 100
                최근 = [x for x in 앞 if x[0] >= str(int(d1) - 10000)]
                증권사수 = len({x[3] for x in 최근 if x[3]})
            결과, 청산 = None, None
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + _목표 / 100):
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
            사건.append({"인": i + 1, "날": 다음, "code": code, "결과": 결과,
                         "청산": 청산, "원시": o0, "대금": b0[2],
                         "상갭": g - 시갭,
                         "며칠": 며칠, "여력": 여력, "의견": 의견,
                         "증권사수": 증권사수})
    n = len(사건)
    if n == 0:
        print("  ⚠️ 사건이 없다")
        return 1
    바닥 = sum(1 for x in 사건 if x["결과"] > _목표 - _비용 - 1e-9) / n * 100
    년수 = len([d for d in 날 if d >= _시작]) / 245
    있 = sum(1 for x in 사건 if x["며칠"] is not None)
    print(f"\n  사건 {n:,}건 · 기본 도달률 {바닥:.1f}% · {년수:.1f}년")
    print(f"  그중 컨센서스가 있는 것 **{있}건 ({있/n*100:.1f}%)**\n")

    def 재기(a, 라, 폭=28):
        if len(a) < 15:
            print(f"    {라:<{폭}}{len(a):>6}건  표본 부족")
            return
        d2 = sum(1 for x in a if x["결과"] > _목표 - _비용 - 1e-9) / len(a) * 100
        묶 = {}
        for x in a:
            묶.setdefault(x["날"][:4], []).append(x["결과"])
        전 = 플 = 0
        for y, arr in 묶.items():
            if len(arr) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        별 = "⭐" if (abs(d2 - 바닥) > 5 and 전 >= 5
                     and 플 / 전 >= 2 / 3) else "  "
        print(f"    {라:<{폭}}{len(a):>6}건{d2:>8.1f}%{d2-바닥:>+8.1f}%p"
              f"{st.mean([x['결과'] for x in a]):>+9.2f}%{f'{플}/{전}':>7}{별}")

    머 = (f"    {'조건':<28}{'표본':>8}{'도달률':>8}{'기본대비':>8}"
          f"{'평균':>9}{'연도별':>7}")

    print("  ══ A **리포트가 최근에 있었나** ══")
    print(머)
    for lo, hi, 라 in ((0, 30, "30일 안에 리포트 있음"),
                       (30, 90, "30~90일"), (90, 180, "90~180일"),
                       (180, 9999, "180일 넘음")):
        재기([x for x in 사건 if x["며칠"] is not None
              and lo <= x["며칠"] < hi], 라)
    재기([x for x in 사건 if x["며칠"] is None], "**리포트가 아예 없음**")

    print(f"\n  ══ B ⭐ **목표주가 대비 상승여력** ══")
    print("     (목표주가 ÷ 어제 종가 − 1) · ⚠️ 원본 종가와 견줬다")
    print(머)
    for lo, hi, 라 in ((-9999, 0, "목표주가 **아래** (여력 음수)"),
                       (0, 20, "여력 0~20%"), (20, 50, "여력 20~50%"),
                       (50, 100, "여력 50~100%"), (100, 9999, "여력 100%↑")):
        재기([x for x in 사건 if x["여력"] is not None
              and lo <= x["여력"] < hi], 라)

    print(f"\n  ══ C **의견** ══")
    print(머)
    for 의, cnt in 의견수.most_common(6):
        if not 의:
            continue
        재기([x for x in 사건 if x["의견"] == 의], 의[:26])

    print(f"\n  ══ D **몇 곳이나 보나** (최근 1년 증권사 수) ══")
    print(머)
    for lo, hi, 라 in ((0, 1, "0곳 (아무도 안 봄)"), (1, 2, "1곳"),
                       (2, 4, "2~3곳"), (4, 9999, "4곳 이상")):
        재기([x for x in 사건 if lo <= x["증권사수"] < hi], 라)

    # ══ E 자본 시뮬 ══
    print(f"\n  ══ E ⭐⭐ **자본 시뮬** — 원판을 이기나 (여섯 번 다 졌다) ══")
    묶날 = {}
    for x in 사건:
        묶날.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]

    def 시뮬(거름, 라, 끝년=None, 폭=32):
        현금, 보유, 곡, 산 = 5_000_000.0, [], [], 0
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
            골 = [x for x in 묶날.get(i, []) if 거름(x)]
            for x in sorted(골, key=lambda z: z["상갭"])[:확정["종목수"]]:
                쓸 = min(평 * 확정["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({**x, "주수": 주수})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        c = ((끝 / 5_000_000) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        print(f"    {라:<{폭}}{끝:>15,.0f}원{c:>+9.2f}%{낙:>8.1f}%{산:>7}건")

    print(f"    {'전략':<32}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")
    시뮬(lambda x: True, "원판 (컨센서스 안 봄)")
    시뮬(lambda x: x["며칠"] is None, "+ 리포트 **없는** 것만")
    시뮬(lambda x: x["며칠"] is not None, "+ 리포트 있는 것만")
    시뮬(lambda x: x["며칠"] is not None and x["며칠"] <= 90,
         "+ 90일 안 리포트 있는 것만")
    시뮬(lambda x: x["여력"] is not None and x["여력"] >= 20,
         "+ 상승여력 20%↑만")
    시뮬(lambda x: x["여력"] is not None and x["여력"] >= 50,
         "+ 상승여력 50%↑만")
    시뮬(lambda x: not (x["여력"] is not None and x["여력"] < 0),
         "+ 목표주가 아래인 것 **제외**")
    print(f"\n    ⚠️ 2025·26 제외")
    시뮬(lambda x: True, "원판", 끝년="2024")
    시뮬(lambda x: x["며칠"] is None, "+ 리포트 없는 것만", 끝년="2024")
    시뮬(lambda x: x["여력"] is not None and x["여력"] >= 20,
         "+ 상승여력 20%↑만", 끝년="2024")
    시뮬(lambda x: not (x["여력"] is not None and x["여력"] < 0),
         "+ 목표주가 아래 제외", 끝년="2024")

    print("\n  읽는 법")
    print("    - E에서 원판을 못 이기면 **⑦ 규칙에 안 넣는다** (여섯 번 겪었다)")
    print("    - ⚠️ 기간이 6.7년뿐이라 10.4년 결과와 직접 견주면 안 된다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
