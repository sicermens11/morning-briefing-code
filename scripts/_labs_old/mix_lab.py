#!/usr/bin/env python3
r"""
mix_lab.py — **90차. 두 전략을 겹쳐 굴리면** (2026-09-03)

## 왜 겹치나
```
주력  소형주 급락 줍기
      자산 100만원 연 +33.50%  ->  3,000만원 연 +22.37%   ← **커지면 약해진다**
      이유: 신호 종목 중앙 주가 4,735원. **거래대금 한계**에 걸린다

보조  엔비디아 -2%↓ -> 삼성·하이닉스 5일 (89b)
      2025·26 제외 연 +8.46% (늘 들고 있기는 -4.53%)  낙폭 -28.5%
      **대형주라 유동성이 사실상 무한하다**

⇒ 주력이 못 삼키는 돈을 보조가 받아준다면?
```

## 재는 것
```
자산 100만 · 500만 · 3,000만 · 1억 · 3억  각각에서
   A 주력만
   B 보조만
   C ⭐ 주력 먼저, **남는 현금**을 보조로
   D 반반 나눠서
```
⚠️ 판정: 끝 자산 · **낙폭** · 연도별 · **2025·26 제외**
⚠️ 주수는 **원본 시가**로, 수익률은 **수정 비율**로 (53차 버그)
⚠️ 주력은 하루 거래대금의 1%까지만 산다 (실제로 살 수 있는 만큼)
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
_보조종목 = (("005930", "삼성전자"), ("000660", "SK하이닉스"))
_보조일 = 5


def main():
    # ── 엔비디아 등락 (한국 날짜에 쓸 수 있는 값) ──
    종 = json.load(io.open(os.path.join(_YH, "NVDA.json"),
                           encoding="utf-8-sig")).get("종가") or {}
    k = sorted(종)
    nv = {}
    for j in range(1, len(k)):
        pv = 종[k[j - 1]]
        if pv:
            nv[k[j]] = (종[k[j]] / pv - 1) * 100

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

    ek = sorted(nv)
    쓸nv = {}
    for d in 날:
        앞 = [x for x in ek if x < d]
        if not 앞:
            continue
        전 = max(앞)
        try:
            if (dt.datetime.strptime(d, "%Y%m%d")
                    - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                continue
        except Exception:
            pass
        쓸nv[d] = nv[전]

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

    # ══ 주력 사건 ══
    주력 = {}
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
            주력.setdefault(i + 1, []).append(
                {"청산": 청산, "결과": 결과, "원시": o0, "대금": b0[2],
                 "상대갭": g - 시갭})

    # ══ 보조 사건 (엔비디아 −2%↓ → 삼성·하이닉스) ══
    선 = {}
    for c, n in _보조종목:
        s = {}
        for d in 날:
            v = 주가[d].get(c)
            if v:
                s[d] = v[0]
        선[c] = s
    보조 = {}
    for i, d in enumerate(날):
        if d < _시작 or 쓸nv.get(d) is None or 쓸nv[d] > -2:
            continue
        j = i + _보조일 - 1
        if j >= len(날):
            continue
        묶 = []
        for c, n in _보조종목:
            s = 선[c]
            b = (비.get(d) or {}).get(c)
            v0, v1 = s.get(d), s.get(날[j])
            o0 = (원시.get(d) or {}).get(c)
            if not b or not v0 or not v1 or not o0:
                continue
            # ⚠️ 비[날][종목]은 (시가/종가, 고가/종가, 거래대금) 세 값이다
            묶.append({"청산": j, "결과": (v1 / (v0 * b[0]) - 1) * 100 - _비용,
                       "원시": o0, "대금": 9e15})
        if 묶:
            보조[i] = 묶
    print(f"  주력 신호일 {len(주력)}일 · 보조 신호일 {len(보조)}일\n", flush=True)

    년수 = len([d for d in 날 if d >= _시작]) / 245

    def 시뮬(시드, 주몫, 보몫, 라, 끝년=None):
        """주몫·보몫 = 각 전략에 쓸 자산 비율 상한 (0이면 안 씀)"""
        현금, 보유, 곡 = float(시드), [], []
        주n = 보n = 0
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
            보중 = sum(p["주수"] * p["원시"] for p in 보유 if p.get("보"))
            # ── 주력 (먼저) ──
            if 주몫 > 0:
                for x in sorted(주력.get(i, []), key=lambda z: z["상대갭"])[:2]:
                    쓸 = min(평 * 0.20, 현금, x["대금"] * 0.01)
                    주수 = int(쓸 // x["원시"])     # 주수는 **원본 시가**로
                    if 주수 < 1:
                        continue
                    실 = 주수 * x["원시"]
                    if 실 > 현금:
                        continue
                    현금 -= 실
                    보유.append({**x, "주수": 주수, "보": False})
                    주n += 1
            # ── 보조 (남는 돈으로) ──
            if 보몫 > 0 and i in 보조 and 보중 <= 0:
                여 = min(현금, 평 * 보몫)
                for x in 보조[i]:
                    금 = 여 / len(보조[i])
                    주수 = int(금 // x["원시"])
                    if 주수 < 1:
                        continue
                    실 = 주수 * x["원시"]
                    if 실 > 현금:
                        continue
                    현금 -= 실
                    보유.append({**x, "주수": 주수, "보": True})
                    보n += 1
            곡.append(평)
        끝 = 현금 + sum(p["주수"] * p["원시"] for p in 보유)
        yr = len(곡) / 245
        cagr = ((끝 / 시드) ** (1 / max(yr, 0.1)) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        해 = {}
        for j2 in range(len(곡)):
            해.setdefault(날[[x for x in range(len(날))
                             if 날[x] >= _시작][0] + j2][:4], []).append(곡[j2])
        전 = 플 = 0
        for y in sorted(해):
            if len(해[y]) < 100:
                continue
            전 += 1
            플 += 1 if 해[y][-1] > 해[y][0] else 0
        print(f"    {라:<22}{끝:>17,.0f}원{cagr:>9.2f}%{낙:>8.1f}%"
              f"{주n:>7}{보n:>6}{f'{플}/{전}':>8}")
        return cagr

    머 = (f"    {'전략':<22}{'끝 자산':>18}{'연평균':>9}{'낙폭':>8}"
          f"{'주력':>7}{'보조':>6}{'연도별':>8}")

    for 시드 in (1_000_000, 5_000_000, 30_000_000, 100_000_000, 300_000_000):
        print(f"  ══ 자산 {시드:,}원 ══")
        print(머)
        시뮬(시드, 1, 0, "A 주력만")
        시뮬(시드, 0, 0.5, "B 보조만 (50%씩)")
        시뮬(시드, 1, 0.3, "C ⭐ 주력 + 남는 돈 30%")
        시뮬(시드, 1, 0.5, "C2 주력 + 남는 돈 50%")
        print()

    print("  ══ ⚠️ **2025·26 제외** (자산 3,000만 · 1억) ══")
    for 시드 in (30_000_000, 100_000_000):
        print(f"    자산 {시드:,}원")
        print(머)
        시뮬(시드, 1, 0, "A 주력만", 끝년="2024")
        시뮬(시드, 0, 0.5, "B 보조만", 끝년="2024")
        시뮬(시드, 1, 0.3, "C 주력 + 남는 돈 30%", 끝년="2024")
        print()

    print("  읽는 법")
    print("    - C가 A보다 커야 보조를 붙일 값어치가 있다")
    print("    - ⚠️ 자산이 작을 때는 A가 이기는 게 정상이다 (주력이 다 삼킨다)")
    print("    - ⚠️ 낙폭이 같이 커지면 그만큼 위험을 산 것이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
