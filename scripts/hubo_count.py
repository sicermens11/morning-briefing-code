#!/usr/bin/env python3
r"""
hubo_count.py — **하루에 후보가 몇 개나 뜨나** (2026-09-09 신설)

## 왜 만들었나
```
사용자: 「"컴퍼니케이" 볼 후보에 나왔다가, 상대갭 3.5%p를 넘지 않아
        살 후보가 안 됐는데 오르고 있네?」
```
보니 **상대갭이 -0.0** 이었다. 그날 후보가 **1개뿐**이었기 때문이다.

## ⚠️⚠️ 구조 문제다
```
상대갭 = 그 종목 갭 − **후보들 갭의 중앙값**

후보가 1개면 -> 중앙값 = 자기 자신 -> 상대갭 = **언제나 0** -> 절대 못 산다
후보가 2개면 -> 하나는 +, 하나는 − -> 아래쪽 하나만 살 수 있다
후보가 3개면 -> 가운데가 기준 -> 아래 하나만
```
**후보가 적은 날은 규칙이 사실상 작동하지 않는다.**
이게 「1년에 10번밖에 안 산다」의 숨은 이유일 수 있다

이 스크립트는 **후보 수 분포**를 세어 그게 얼마나 자주 일어나는지 본다

쓰는 법:
    python scripts\hubo_count.py
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

_시작 = "20160401"
_시총하한, _시총상한 = 3e10, 2e11


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

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

    print("  후보 세는 중...", flush=True)
    하루수 = {}
    for i, d1 in enumerate(날):
        if i < 260 or d1 < _시작:
            continue
        n = 0
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < _시총하한 or 대금 < O._MIN_AMT or 시총 >= _시총상한:
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
            if kk is None or kk < 250 or 종계[code][kk - 20] <= 0:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0:
                continue
            if (c1 / sq[kk - 20] - 1) * 100 > -10.0:
                continue
            n += 1
        하루수[d1] = n

    v = list(하루수.values())
    v.sort()
    총 = len(v)
    칸 = collections.Counter()
    for n in v:
        if n == 0:
            칸["0개"] += 1
        elif n == 1:
            칸["1개"] += 1
        elif n <= 3:
            칸["2~3개"] += 1
        elif n <= 9:
            칸["4~9개"] += 1
        elif n <= 39:
            칸["10~39개"] += 1
        else:
            칸["40개 이상"] += 1

    print("\n" + "=" * 78)
    print("  하루에 후보가 몇 개나 뜨나  (2016-04 ~ · 지금 규칙 + 시총 하한 300억)")
    print("=" * 78)
    print(f"\n  거래일 {총:,}일 · 가운데 {v[총//2]}개 · 평균 {sum(v)/총:.1f}개")
    print(f"  가장 많은 날 {v[-1]}개 · 상위 10% {v[int(총*0.9)]}개")
    print(f"\n  {'후보 수':<12}{'날 수':>8}{'비율':>8}   {'뜻'}")
    뜻 = {"0개": "볼 것이 없다",
          "1개": "⚠️ **상대갭이 언제나 0 — 절대 못 산다**",
          "2~3개": "⚠️ 아래 하나만 살 수 있다",
          "4~9개": "상대갭이 조금 뜻을 갖는다",
          "10~39개": "쓸 만하다",
          "40개 이상": "40개로 자르는 게 뜻을 갖는 날"}
    막힘 = 0
    for 라 in ("0개", "1개", "2~3개", "4~9개", "10~39개", "40개 이상"):
        c = 칸.get(라, 0)
        print(f"  {라:<12}{c:>8,}{c/총*100:>7.1f}%   {뜻[라]}")
        if 라 in ("0개", "1개"):
            막힘 += c
    print(f"\n  ⚠️ **후보가 0~1개라 못 사는 날: {막힘:,}일 ({막힘/총*100:.1f}%)**")
    적 = sum(칸.get(k, 0) for k in ("0개", "1개", "2~3개"))
    print(f"  ⚠️ 후보 3개 이하라 **상대갭이 거의 무의미한 날: "
          f"{적:,}일 ({적/총*100:.1f}%)**")
    print("\n" + "=" * 78)
    print("  읽는 법")
    print("    - 후보가 적은 날은 **상대갭 규칙이 구조적으로 작동하지 않는다**")
    print("    - 고칠 방법 셋:")
    print("      ① 후보가 N개 미만이면 **시장 전체 갭 중앙값**을 기준으로 쓴다")
    print("      ② 후보가 적으면 상대갭 대신 **그냥 갭**(전날 종가 대비)을 쓴다")
    print("      ③ 조건을 풀어 후보 수 자체를 늘린다")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-09_173차_후보수분포.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
