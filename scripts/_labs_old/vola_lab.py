#!/usr/bin/env python3
r"""
vola_lab.py — **191-2차 · 섹터 안 규모별 「등락폭」** (2026-09-09 신설)

## 왜 다시 재나 — 내가 물은 것과 다른 걸 쟀다
```
사용자: 「반도체 AI 종목 중에서도 삼성이나 sk하이닉스 같은 대형주는 **등락폭이 작을 것** 같고,
        관련 소부장 종목이 **볼린저, 등락폭이 클 것** 같은데,
        매수 타이밍만 알면, 오히려 **소부장 소형주가 더 큰 수익**을 낼 수 있는 거잖아?」

191차 A-2 에서 이걸 재려다가 **변동성이 아니라 평균 수익률**을 냈다.
「+1.1% -> +3.7%」로 찍혀 나온 건 등락폭이 아니라 **20일 뒤 평균 수익**이었다.
=> 여기서 제대로 잰다
```

## 재는 것 — 「등락폭」을 네 가지로 나눠 본다
```
① **하루 등락의 들쭉날쭉함** (일간 수익률 표준편차 · 연율)   <- 교과서적 변동성
② **볼린저 띠 폭** (2σ ÷ 20일 평균) — 사용자가 「볼린저」라고 한 그것
③ **20일에 -20% 넘게 빠지는 일이 얼마나 잦나**             <- ⭐ 이게 **기회의 수**다
④ **20일에 +20% 넘게 오르는 일이 얼마나 잦나**             <- ⭐ 이게 **먹을 폭**이다
```
⚠️ 우리 목표는 **매수 기회 포착**이다. ③이 많아야 살 일이 생기고,
   ④가 커야 산 뒤에 먹을 것이 있다. ①②는 그 뒷받침이다

## 나누는 법 — 191차와 같다
```
**그날 그 섹터 안에서** 아래 1/3 · 가운데 · 위 1/3
⚠️ 절대 시총으로 자르면 안 된다 — 맵 140종목 중 1조 이상이 70개라
   300~2,000억으로 자르면 조선 본선·원전이 통째로 사라진다 (191차에서 확인)
```

쓰는 법:
    python scripts\vola_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from chain_map import 읽기 as 맵읽기  # noqa: E402

_시작 = "20100104"


def main():
    맵 = 맵읽기()
    섹터표 = {}
    for s, 들 in 맵.items():
        for _, c in 들:
            if c and c not in 섹터표:
                섹터표[c] = s

    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일 · 가치사슬 {len(섹터표)}종목", flush=True)

    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            if c in 섹터표:
                계열.setdefault(c, []).append(v)
                있는날.setdefault(c, []).append(i)

    사건 = []
    for c, vs in 계열.items():
        종 = [z[0] for z in vs]
        ii = 있는날[c]
        for k in range(20, len(vs) - 20):
            시총억 = vs[k][1] / 1e8
            if 시총억 <= 0 or vs[k][2] / 1e8 < 1.0:
                continue
            c1 = 종[k]
            m, sd = O.창평균표준(종, k, 20)
            # ── ① 하루 등락의 들쭉날쭉함 (20일치 일간 수익률 표준편차) ──
            일 = []
            for z in range(k - 19, k + 1):
                앞 = 종[z - 1]
                if 앞 > 0:
                    일.append(종[z] / 앞 - 1)
            if len(일) < 15:
                continue
            _, 일sd = O.빠른평균표준(일)
            사건.append({
                "code": c, "섹터": 섹터표[c], "_날짜": 날[ii[k]], "시총억": 시총억,
                "하루변동": 일sd * (252 ** 0.5) * 100,        # 연율 %
                "띠폭": (4 * sd / m * 100) if (m and sd) else None,   # 2σ 위아래
                "낙20": (c1 / 종[k - 20] - 1) * 100,
                "앞20": (종[k + 20] / c1 - 1) * 100,
            })
    print(f"  사건 {len(사건):,}건", flush=True)

    # ── 그날 그 섹터 안에서 규모를 나눈다 ──
    하루 = {}
    for x in 사건:
        하루.setdefault((x["_날짜"], x["섹터"]), []).append(x)
    for 칸 in 하루.values():
        if len(칸) < 3:
            for x in 칸:
                x["규모칸"] = None
            continue
        칸.sort(key=lambda z: z["시총억"])
        n = len(칸)
        for j, x in enumerate(칸):
            x["규모칸"] = ("작은 쪽" if j < n / 3
                          else ("가운데" if j < n * 2 / 3 else "큰 쪽"))

    def 재기(칸):
        if len(칸) < 300:
            return None
        하 = [x["하루변동"] for x in 칸]
        띠 = [x["띠폭"] for x in 칸 if x["띠폭"] is not None]
        낙 = [x["낙20"] for x in 칸]
        앞 = [x["앞20"] for x in 칸]
        return {
            "n": len(칸),
            "시총": sorted(x["시총억"] for x in 칸)[len(칸) // 2],
            "하루변동": sum(하) / len(하),
            "띠폭": (sum(띠) / len(띠)) if 띠 else 0,
            "크게빠짐": sum(1 for z in 낙 if z <= -20) / len(낙) * 100,
            "크게오름": sum(1 for z in 앞 if z >= 20) / len(앞) * 100,
            "앞평균": sum(앞) / len(앞),
        }

    print("\n" + "=" * 104)
    print("  191-2차 · **섹터 안 규모별 「등락폭」**")
    print("  사용자: 「대형주는 등락폭이 작을 것 같고, 소부장이 볼린저·등락폭이 클 것 같은데,")
    print("          매수 타이밍만 알면 오히려 **소부장 소형주가 더 큰 수익**을 낼 수 있는 거잖아?」")
    print(f"  {날[0]} ~ {날[-1]}")
    print("=" * 104)

    머 = (f"  {'섹터':<20}{'규모':<8}{'중간시총':>10}{'하루등락':>9}"
          f"{'볼린저띠':>9}{'-20%빠짐':>10}{'+20%오름':>10}{'20일평균':>9}")

    print("\n  ── A **전체** ──")
    print(머)
    for 규 in ("작은 쪽", "가운데", "큰 쪽"):
        r = 재기([x for x in 사건 if x.get("규모칸") == 규])
        if r:
            print(f"  {'[가치사슬 전체]':<20}{규:<8}{r['시총']:>9,.0f}억"
                  f"{r['하루변동']:>8.1f}%{r['띠폭']:>8.1f}%"
                  f"{r['크게빠짐']:>9.1f}%{r['크게오름']:>9.1f}%{r['앞평균']:>+8.2f}%")

    print("\n  ── B **섹터마다** ──")
    print(머)
    섹들 = sorted({x["섹터"] for x in 사건})
    for s in 섹들:
        칸s = [x for x in 사건 if x["섹터"] == s]
        첫 = True
        for 규 in ("작은 쪽", "가운데", "큰 쪽"):
            r = 재기([x for x in 칸s if x.get("규모칸") == 규])
            이름 = s if 첫 else ""
            첫 = False
            if not r:
                print(f"  {이름:<20}{규:<8}{'표본 부족':>10}")
                continue
            print(f"  {이름:<20}{규:<8}{r['시총']:>9,.0f}억"
                  f"{r['하루변동']:>8.1f}%{r['띠폭']:>8.1f}%"
                  f"{r['크게빠짐']:>9.1f}%{r['크게오름']:>9.1f}%{r['앞평균']:>+8.2f}%")

    print("\n  ── C ⭐ **사용자 가설 셋을 하나씩 판정** ──")
    작 = 재기([x for x in 사건 if x.get("규모칸") == "작은 쪽"])
    큰 = 재기([x for x in 사건 if x.get("규모칸") == "큰 쪽"])
    if 작 and 큰:
        for 라, k, 단 in (("① 작은 쪽이 **하루 등락**이 크다", "하루변동", "%"),
                          ("② 작은 쪽이 **볼린저 띠**가 넓다", "띠폭", "%"),
                          ("③ 작은 쪽이 **크게 빠지는 일이 잦다** (= 기회가 많다)",
                           "크게빠짐", "%"),
                          ("④ 작은 쪽이 **크게 오르는 일이 잦다** (= 먹을 폭이 크다)",
                           "크게오름", "%")):
            차 = 작[k] - 큰[k]
            판 = "✅ 맞다" if 차 > 0 else "❌ 아니다"
            print(f"  {라:<44}작은 {작[k]:>6.1f}{단}  큰 {큰[k]:>6.1f}{단}"
                  f"  차이 {차:>+6.1f}p  {판}")
        차 = 작["앞평균"] - 큰["앞평균"]
        판 = "✅ 맞다" if 차 > 0 else "❌ 아니다"
        print(f"  {'⑤ 그래서 작은 쪽이 **더 번다**':<44}"
              f"작은 {작['앞평균']:>+6.2f}%  큰 {큰['앞평균']:>+6.2f}%"
              f"  차이 {차:>+6.2f}p  {판}")

    print("\n" + "=" * 104)
    print("  읽는 법")
    print("    - ③ 이 우리 목표(**매수 기회 포착**)에 제일 가깝다 — 살 일이 얼마나 자주 생기나")
    print("    - ④ 는 산 뒤에 먹을 것이 있나 — ③과 ④가 같이 커야 값어치가 있다")
    print("    - ⑤ 는 **아무 날이나 산** 값이다. 규칙을 걸면 달라진다 (191차 C절이 그것)")
    print("=" * 104)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-09_191-2차_규모별등락폭.txt")

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
