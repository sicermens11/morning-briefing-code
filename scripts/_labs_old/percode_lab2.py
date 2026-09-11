#!/usr/bin/env python3
r"""
percode_lab2.py — **216-2차 · 216차 검산** (2026-09-10 신설)

## 216차가 ✅ 로 나왔다. 그런데 믿으면 안 된다
```
종목마다 배운 규칙   앞 81.0%  ->  뒤 62.4%
모두 같은 규칙(지금)            뒤 56.7%   차이 +5.7%p
```

## ⚠️ 견줌이 **불공정**하다 — 이게 216차의 진짜 결함
```
종목별 규칙 :  앞 기간에서 **144칸 중 최고**를 골랐다
지금 규칙   :  앞 기간에서 **고른 게 아니다** (그냥 지금 쓰는 것)
=> 같은 절차를 밟지 않았다. 「고르기」라는 이득만큼 종목별이 유리하다
```
공정한 견줌은 **「앞 기간에서 고른 최고의 고정 규칙 하나」**를 모든 종목에 거는 것이다.

## 재는 것
```
A ⭐⭐ **공정한 견줌** — 앞에서 고른 고정 규칙 1개 vs 앞에서 고른 종목별 규칙
      => 차이가 사라지면 216차는 **「고르기 이득」**이었을 뿐이다
B ⭐  **기회 비율** — 216차에 빠졌던 것. 종목별 규칙은 후보를 얼마나 줄이나
C ⭐  **무작위 대조** — 앞 기간에서 규칙을 **아무렇게나** 골라 뒤에 쓴다 (200번)
D     종목마다 고른 규칙이 **극단으로 쏠렸나** (낙120-30% 같은)
```

쓰는 법:
    python scripts\percode_lab2.py
"""
import io
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20100104"
_앞최소 = 60
_뒤최소 = 20


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    가 = 날[len(날) // 2]
    print(f"  거래일 {len(날):,}일 · 앞 ~{가} · 뒤 {가}~", flush=True)

    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            계열.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(i)

    볼창 = (20, 60, 120)
    낙창 = (20, 60, 120)
    print("  사건 만드는 중...", flush=True)
    종목별 = {}
    for c, vs in 계열.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(120, len(vs)):
            if vs[k][1] / 1e8 < 100 or vs[k][2] / 1e8 < 1.0:
                continue
            c1 = 종[k]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100
            if not ((볼20 is not None and 볼20 <= -0.5) or 낙20 <= -5):
                continue
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            x = {"_날짜": 날[i], "_20": 뒤}
            for w in 볼창:
                m, sd = O.창평균표준(종, k, w)
                x[f"볼{w}"] = ((c1 - m) / (2 * sd)) if sd else None
            for w in 낙창:
                x[f"낙{w}"] = (c1 / 종[k - w] - 1) * 100 if k >= w else None
            종목별.setdefault(c, []).append(x)
    print(f"  종목 {len(종목별):,}개 · 사건 "
          f"{sum(len(v) for v in 종목별.values()):,}건", flush=True)

    격자 = [(f"볼{bw}", bt, f"낙{nw}", nt)
            for bw in 볼창 for bt in (-0.5, -1.0, -1.5, -2.0)
            for nw in 낙창 for nt in (-5, -10, -20, -30)]
    공통 = ("볼20", -1.0, "낙20", -10)

    def 맞나(x, 규):
        bk, bt, nk, nt = 규
        b, n = x.get(bk), x.get(nk)
        return (b is not None and b <= bt and n is not None and n <= nt)

    def 셈(칸, 최소):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (len(v), sum(1 for z in v if z > 0) / len(v) * 100)

    # ── 쓸 종목을 먼저 정하고, 앞·뒤를 한 번만 갈라 담는다 ──
    쓸 = {}
    for c, 줄 in 종목별.items():
        앞 = [x for x in 줄 if x["_날짜"] < 가]
        뒤 = [x for x in 줄 if x["_날짜"] >= 가]
        if len(앞) >= _앞최소 and len(뒤) >= _뒤최소:
            쓸[c] = (앞, 뒤)
    print(f"  쓸 종목 {len(쓸):,}개", flush=True)

    # 종목마다 격자 144칸을 **한 번만** 재서 표로 남긴다 (앞·뒤 따로)
    print("  격자 재는 중 (종목 x 144칸)...", flush=True)
    앞표, 뒤표 = {}, {}
    for c, (앞, 뒤) in 쓸.items():
        a, b = {}, {}
        for 규 in 격자:
            a[규] = 셈([x for x in 앞 if 맞나(x, 규)], 20)
            b[규] = 셈([x for x in 뒤 if 맞나(x, 규)], 10)
        앞표[c], 뒤표[c] = a, b

    print("\n" + "=" * 100)
    print("  216-2차 · ⭐⭐ **216차 검산**")
    print("     216차는 「앞에서 고른 종목별 규칙」을 「고른 적 없는 지금 규칙」과 견줬다.")
    print("     **같은 절차를 밟지 않은 견줌**이다. 여기서 바로잡는다")
    print("=" * 100)

    # ── A 공정한 견줌 ──
    print("\n  ── A ⭐⭐ **공정한 견줌** ──")
    print("     둘 다 **앞 기간에서 고른다**. 고정 규칙은 하나를 모두에게, "
          "종목별은 제각각")

    # 앞 기간에서 고른 **최고의 고정 규칙 하나** (모든 종목을 합쳐서)
    최고고정, 최고값 = None, -1
    for 규 in 격자:
        vs = [앞표[c][규][1] for c in 쓸 if 앞표[c][규]]
        if len(vs) < len(쓸) * 0.3:
            continue
        m = sum(vs) / len(vs)
        if m > 최고값:
            최고값, 최고고정 = m, 규

    def 뒤평균(고르기):
        """고르기(c) -> 규칙. 뒤 기간 이김률 평균과 건수 합."""
        v, n, 이긴 = [], 0, 0
        for c in 쓸:
            규 = 고르기(c)
            r = 뒤표[c].get(규) if 규 else None
            g = 뒤표[c].get(공통)
            if not r or not g:
                continue
            v.append(r[1])
            n += r[0]
            if r[1] > g[1]:
                이긴 += 1
        return ((sum(v) / len(v)) if v else None, len(v), n, 이긴)

    def 종목최고(c):
        좋, 값 = None, -1
        for 규 in 격자:
            r = 앞표[c][규]
            if r and r[1] > 값:
                값, 좋 = r[1], 규
        return 좋

    공평, 공건, 공수, _ = 뒤평균(lambda c: 공통)
    고평, 고건, 고수, 고이긴 = 뒤평균(lambda c: 최고고정)
    종평, 종건, 종수, 종이긴 = 뒤평균(종목최고)

    bk, bt, nk, nt = 최고고정
    print(f"\n     앞 기간 최고의 **고정** 규칙 = {bk}일 {bt:+.1f}σ · {nk}일 {nt}%")
    print(f"\n  {'':<40}{'뒤 이김':>10}{'뒤 건수':>12}{'기회':>9}")
    print(f"  {'① 지금 규칙 (고른 적 없음)':<40}"
          f"{공평:>9.1f}%{공수:>12,}{'100%':>9}")
    print(f"  {'② 앞에서 고른 **고정** 규칙 하나':<40}"
          f"{고평:>9.1f}%{고수:>12,}{고수/공수*100:>8.0f}%")
    print(f"  {'③ 앞에서 고른 **종목별** 규칙':<40}"
          f"{종평:>9.1f}%{종수:>12,}{종수/공수*100:>8.0f}%")

    차공정 = 종평 - 고평
    차216 = 종평 - 공평
    print(f"\n     216차가 본 차이 (③-①) = **{차216:+.1f}%p**  <- 불공정한 견줌")
    print(f"     ⭐ 공정한 차이 (③-②) = **{차공정:+.1f}%p**  <- 이게 진짜다")
    if 차공정 < 1.0:
        print("\n     ⇒ ❌ **종목별로 나눈 이득이 아니었다.**")
        print("        「앞 기간에서 골랐다」는 이득이 거의 전부다.")
        print("        고정 규칙 하나만 바꿔도 같은 값이 나온다")
    else:
        print(f"\n     ⇒ 종목별로 나눈 **진짜 이득 {차공정:+.1f}%p** 가 남는다")
    print(f"\n     ⚠️ 기회: 종목별은 지금 규칙의 **{종수/공수*100:.0f}%** "
          f"· 고정은 **{고수/공수*100:.0f}%**")
    if 종수 / 공수 < 0.5:
        print("        기회가 **절반 밑**이다 — 승률이 올라도 놓치는 게 더 많다")

    # ── B 무작위 대조 ──
    print("\n  ── C ⭐ **무작위 대조** — 앞에서 **아무 규칙이나** 골라 뒤에 쓴다 ──")
    print("     144칸에서 고르는 절차 자체가 만드는 이득을 잰다")
    rr = random.Random(20260910)
    무 = []
    for _ in range(200):
        r = 뒤평균(lambda c: rr.choice(격자))[0]
        if r is not None:
            무.append(r)
    무.sort()
    if 무:
        상위 = sum(1 for v in 무 if v < 종평) / len(무) * 100
        print(f"\n     무작위 200번: 가운데 {무[len(무)//2]:.1f}% · "
              f"위 5% {무[int(len(무)*0.95)]:.1f}% · 맨 위 {무[-1]:.1f}%")
        print(f"     종목별 규칙 {종평:.1f}% 는 무작위의 **상위 {100-상위:.0f}%**")
        print(f"     고정 규칙  {고평:.1f}% 는 무작위의 "
              f"**상위 {100 - sum(1 for v in 무 if v < 고평)/len(무)*100:.0f}%**")
        if 상위 < 75:
            print("     ⇒ ❌ **무작위와 구별이 안 된다**")

    # ── D 어디로 쏠렸나 ──
    print("\n  ── D 종목마다 고른 규칙이 **극단으로 쏠렸나** ──")
    쏠 = {}
    for c in 쓸:
        규 = 종목최고(c)
        if 규:
            쏠[규] = 쏠.get(규, 0) + 1
    총 = sum(쏠.values())
    극단 = sum(n for 규, n in 쏠.items() if 규[3] <= -20)
    느슨 = sum(n for 규, n in 쏠.items() if 규[1] >= -0.5)
    print(f"\n     낙폭 문턱 **-20% 이하**(더 많이 빠진 것)  "
          f"{극단:>6,}개 ({극단/총*100:.0f}%)")
    print(f"     볼린저 문턱 **-0.5σ**(느슨한 것)         "
          f"{느슨:>6,}개 ({느슨/총*100:.0f}%)")
    print(f"     격자에서 이 조건이 차지하는 몫: 낙폭 -20%↓ 50% · 볼 -0.5σ 25%")
    if 극단 / 총 > 0.6:
        print("     ⇒ ⚠️ **한쪽으로 쏠렸다.** 종목마다 다른 답이 나온 게 아니라")
        print("        **「더 많이 빠진 걸 산다」**가 종목마다 되풀이됐을 뿐이다")
        print("        (= 이미 아는 사실. 종목별로 나눈 것과 무관하다)")

    print("\n" + "=" * 100)
    print("  읽는 법")
    print("    - **A의 「공정한 차이」가 답이다.** 216차의 +5.7%p 는 견줌이 틀렸다")
    print("    - 공정한 차이가 1%p 밑이면 종목별 분할은 **값어치가 없다**")
    print("    - 기회가 절반 밑이면 승률이 올라도 **돈은 준다**")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_216-2차_종목별검산.txt")

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
