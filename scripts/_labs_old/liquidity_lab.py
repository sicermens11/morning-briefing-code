#!/usr/bin/env python3
r"""
liquidity_lab.py — **223차 · 거래대금 한도가 실제로 걸리나** (2026-09-10 신설)

## 사용자 물음
```
「그렇게 부자가 아니라서 **「거래대금 1%」를 넘는 일은 없을 것 같은데?**
 그래서 거래대금 1% 이내로 산다는 그게 **고려해야할 사항이 아닌 것 같은데**..
 소형주 포함해서!」
```

## ⚠️ 실제 후보 6개를 보니 **짐작과 달랐다**
```
아이크래프트 21억 · 컴퍼니케이 6억 · 웅진 6억
우림피티에스  3억 · 젝시믹스   3억 · **디엔에프 2억**
=> 1% 면 **200만~2,100만원**. 소형주라 거래대금 자체가 작다
```
표본이 6개뿐이라 **10.4년 전체**로 다시 잰다.

## 셈법
```
한 종목에 넣는 돈 = 자산 x 비중(20%)
제약: 자산 x 0.20 <= 거래대금 x 0.01
  =>  **거래대금 >= 자산 x 20배**
자산   500만원 -> 거래대금 **1억** 이상 필요
자산 1,000만원 -> **2억**
자산 3,000만원 -> **6억**
자산 5,000만원 -> **10억**
자산   1억원  -> **20억**
```

## 재는 것
```
A ⭐⭐ 후보의 **거래대금 분포** (10.4년 전체)
B ⭐⭐ **자산 규모마다** 몇 %가 한도에 걸리나
C ⭐  걸릴 때 **얼마나** 못 사나 (한도가 20% 비중의 몇 %인가)
```

쓰는 법:
    python scripts\liquidity_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20160101"
_비중 = 0.20
_대금몫 = 0.01


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일", flush=True)

    종계 = {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])

    자리 = {}
    for c in 종계:
        자리[c] = 0

    # 후보 = 지금 규칙의 **기술·크기 조건** (재무는 뺀다 — 거래대금 분포에는
    # 큰 영향이 없고, 재무를 넣으면 무거워진다. ⚠️ 이 한계를 밝혀 둔다)
    print("  후보 모으는 중... (지금 규칙의 기술·크기 조건)", flush=True)
    대금들 = []
    for c, sq in 종계.items():
        i = 0
        for d in 날:
            v = 주가[d].get(c)
            if not v:
                continue
            i += 1
            k = i - 1
            if k < 20:
                continue
            시억 = v[1] / 1e8
            대억 = v[2] / 1e8
            if not (300 <= 시억 < 2000) or 대억 < 1.0:
                continue
            c1 = sq[k]
            m, sd = O.창평균표준(sq, k, 20)
            if not sd:
                continue
            볼 = (c1 - m) / (2 * sd)
            if sq[k - 20] <= 0:
                continue
            낙 = (c1 / sq[k - 20] - 1) * 100
            if 볼 <= -1.0 and 낙 <= -10.0:
                대금들.append(대억)

    대금들.sort()
    n = len(대금들)
    print(f"  후보 **{n:,}건**", flush=True)
    if not n:
        print("  ⚠️ 후보가 없다")
        return 1

    print("\n" + "=" * 92)
    print("  223차 · ⭐⭐ **거래대금 한도가 실제로 걸리나**")
    print("     사용자: 「부자가 아니라서 넘는 일은 없을 것 같은데?」")
    print("     ⚠️ 재무 조건은 뺐다 (거래대금 분포에는 영향이 작다)")
    print("=" * 92)

    print("\n  ── A ⭐⭐ 후보의 **거래대금 분포** ──")
    for p in (1, 5, 10, 25, 50, 75, 90, 99):
        v = 대금들[min(n - 1, int(n * p / 100))]
        print(f"     아래에서 {p:>2}%  {v:>8.1f}억"
              f"   (1% = {v*100:>7,.0f}만원)")

    print("\n  ── B ⭐⭐ **자산 규모마다** 몇 %가 한도에 걸리나 ──")
    print("     한 종목에 **자산의 20%**를 넣는다고 할 때")
    print(f"\n  {'자산':>12}{'한 종목':>11}{'필요 거래대금':>14}"
          f"{'걸리는 후보':>12}{'':>4}")
    for 자산 in (5e6, 1e7, 2e7, 3e7, 5e7, 1e8, 2e8, 5e8):
        한종목 = 자산 * _비중
        필요억 = 한종목 / _대금몫 / 1e8
        걸림 = sum(1 for v in 대금들 if v < 필요억)
        비 = 걸림 / n * 100
        표 = ("  ✅ 거의 안 걸린다" if 비 < 5
              else "  ⚠️ 꽤 걸린다" if 비 < 40
              else "  ❌ **크게 걸린다**")
        print(f"  {자산/1e4:>10,.0f}만{한종목/1e4:>9,.0f}만"
              f"{필요억:>12.1f}억{비:>11.0f}%{표}")

    print("\n  ── C ⭐ 걸릴 때 **얼마나** 못 사나 ──")
    print("     한도가 「20% 비중」의 몇 %인가 (100%면 다 살 수 있다)")
    print(f"\n  {'자산':>12}{'가운데 후보에서':>18}{'아래 25% 후보에서':>20}")
    for 자산 in (1e7, 3e7, 5e7, 1e8):
        한종목 = 자산 * _비중
        for 라, p in (("", 50), ("", 25)):
            pass
        중 = 대금들[n // 2] * 1e8 * _대금몫
        하 = 대금들[n // 4] * 1e8 * _대금몫
        print(f"  {자산/1e4:>10,.0f}만{min(100, 중/한종목*100):>16.0f}%"
              f"{min(100, 하/한종목*100):>19.0f}%")

    print("\n" + "=" * 92)
    print("  읽는 법")
    print("    - **걸리는 후보 5% 밑**이면 사용자 말이 맞다 — 신경 안 써도 된다")
    print("    - 40% 넘으면 **브리핑에 표시**해야 한다")
    print("      (금액은 안 내보내고 「자산의 몇 %까지」만 비율로)")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_223차_거래대금한도.txt")

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
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
