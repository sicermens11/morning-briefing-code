#!/usr/bin/env python3
r"""
decay_lab.py — **204차 · 최근 3년이 왜 약해졌나** (2026-09-10 신설)

## 판정 기준 (먼저 밝힌다)
```
「지금 규칙의 성적이 **최근에 떨어졌나**」를 먼저 확인하고,
떨어졌다면 **무엇 때문인지** 넷으로 갈라 본다.
⚠️ 이 시험은 **판정이 아니라 진단**이다. 통과/탈락이 없다
```

## 왜
```
202차  2024~2026 에 기존OR섹터가 **+0.9%p** (다른 구간은 +2.0~+5.9%p)
203차  2023~2026 에 기존OR규모가 **-4.9%p** (앞 구간은 +4.5~+9.9%p)
=> **최근이 약하다.** 규칙을 아무리 잘 찾아도 최근에 안 통하면 쓸 수 없다
```

## 갈라 볼 넷
```
A  **지금 규칙 자체**가 해마다 어땠나 (기준선)
B  **후보 수**가 줄었나 — 살 게 없어진 것인가
C  **빠진 종목이 덜 돌아오나** — 같은 -10% 라도 회복이 달라졌나
D  ⭐ **무엇이 달라졌나** — 시장 변동성 · 낙폭 분포 · 섹터 쏠림
E  ⭐ **재료별로** 최근에 약해진 것과 안 약해진 것을 가른다
```

쓰는 법:
    python scripts\decay_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20100104"


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일 · {날[0]} ~ {날[-1]}", flush=True)

    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            계열.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(i)

    print("  사건 만드는 중 (볼-0.5σ 또는 -5% 만)...", flush=True)
    사건 = []
    for c, vs in 계열.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(120, len(vs)):
            시총억 = vs[k][1] / 1e8
            if 시총억 < 100 or vs[k][2] / 1e8 < 1.0:
                continue
            c1 = 종[k]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100
            # ⚠️ 램 — 만들 때부터 좁힌다
            if not ((볼 is not None and 볼 <= -0.5) or 낙20 <= -5):
                continue
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            m120, sd120 = O.창평균표준(종, k, 120)
            사건.append({
                "code": c, "해": 날[i][:4], "시총억": 시총억,
                "볼20": 볼,
                "볼120": ((c1 - m120) / (2 * sd120)) if sd120 else None,
                "낙20": 낙20,
                "낙60": (c1 / 종[k - 60] - 1) * 100 if k >= 60 else None,
                "_20": 뒤,
                # 그 종목의 20일 변동성 (하루 등락의 들쭉날쭉함)
                "변동": None,
            })
    print(f"  사건 {len(사건):,}건", flush=True)

    해목 = sorted({x["해"] for x in 사건})

    def 셈(칸):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 100:
            return None
        return (len(v), sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v))

    def 지금(x):
        return (x["볼20"] is not None and x["볼20"] <= -1.0
                and x["낙20"] <= -10.0 and 300 <= x["시총억"] < 2000)

    print("\n" + "=" * 96)
    print("  204차 · **최근 3년이 왜 약해졌나** (진단)")
    print("  ⚠️ 이 시험은 판정이 아니라 **진단**이다. 통과/탈락이 없다")
    print("=" * 96)

    # ── A 지금 규칙이 해마다 ──
    print("\n  ── A **지금 규칙**이 해마다 어땠나 (기준선) ──")
    print(f"  {'해':<8}{'후보':>9}{'이김':>9}{'평균':>9}")
    전 = []
    for 해 in 해목:
        r = 셈([x for x in 사건 if x["해"] == 해 and 지금(x)])
        if not r:
            print(f"  {해:<8}{'표본 부족':>9}")
            continue
        전.append((해, r))
        print(f"  {해:<8}{r[0]:>9,}{r[1]:>8.1f}%{r[2]:>+9.2f}")
    if len(전) >= 6:
        앞 = [r for 해, r in 전 if 해 <= "2022"]
        뒤 = [r for 해, r in 전 if 해 >= "2023"]
        if 앞 and 뒤:
            a1 = sum(r[1] for r in 앞) / len(앞)
            a2 = sum(r[1] for r in 뒤) / len(뒤)
            print(f"\n     ⇒ ~2022 평균 **{a1:.1f}%** · 2023~ 평균 **{a2:.1f}%** "
                  f"({a2 - a1:+.1f}%p)")

    # ── B 후보 수가 줄었나 ──
    print("\n  ── B **후보 수**가 줄었나 — 살 게 없어진 것인가 ──")
    print(f"  {'해':<8}{'느슨한 후보':>12}{'지금 규칙':>11}{'비율':>8}")
    for 해 in 해목:
        전체 = sum(1 for x in 사건 if x["해"] == 해)
        지 = sum(1 for x in 사건 if x["해"] == 해 and 지금(x))
        print(f"  {해:<8}{전체:>12,}{지:>11,}"
              f"{(지 / 전체 * 100 if 전체 else 0):>7.1f}%")

    # ── C 빠진 종목이 덜 돌아오나 ──
    print("\n  ── C **같은 낙폭이라도 회복이 달라졌나** ──")
    print(f"  {'해':<8}{'-10~-20%':>12}{'-20~-30%':>12}{'-30%↓':>12}")
    for 해 in 해목:
        말 = []
        for lo, hi in ((-20, -10), (-30, -20), (-9e9, -30)):
            칸 = [x for x in 사건 if x["해"] == 해
                  and lo <= x["낙20"] < hi]
            r = 셈(칸)
            말.append(f"{r[1]:>11.1f}%" if r else f"{'—':>12}")
        print(f"  {해:<8}" + "".join(말))

    # ── D 무엇이 달라졌나 ──
    print("\n  ── D ⭐ **무엇이 달라졌나** ──")
    print(f"  {'해':<8}{'평균 낙폭':>10}{'평균 볼20':>11}"
          f"{'-20%↓ 비율':>12}{'중간 시총':>11}")
    for 해 in 해목:
        칸 = [x for x in 사건 if x["해"] == 해]
        if len(칸) < 100:
            continue
        낙 = [x["낙20"] for x in 칸]
        볼 = [x["볼20"] for x in 칸 if x["볼20"] is not None]
        시 = sorted(x["시총억"] for x in 칸)
        깊 = sum(1 for z in 낙 if z <= -20) / len(낙) * 100
        print(f"  {해:<8}{sum(낙)/len(낙):>+9.1f}%"
              f"{(sum(볼)/len(볼) if 볼 else 0):>10.2f}σ"
              f"{깊:>11.1f}%{시[len(시)//2]:>10,.0f}억")

    # ── E 재료별로 최근에 약해진 것 ──
    print("\n  ── E ⭐⭐ **재료별로** — 최근에 약해진 것과 안 약해진 것 ──")
    print(f"  {'재료':<28}{'~2022':>10}{'2023~':>10}{'차이':>9}{'후보(2023~)':>12}")
    재료들 = (
        ("지금 규칙 (볼20 -1.0σ · 낙20 -10%)", 지금),
        ("볼20 -1.5σ", lambda x: x["볼20"] is not None and x["볼20"] <= -1.5),
        ("볼120 -1.0σ", lambda x: x["볼120"] is not None and x["볼120"] <= -1.0),
        ("볼120 -1.5σ", lambda x: x["볼120"] is not None and x["볼120"] <= -1.5),
        ("낙20 -20%", lambda x: x["낙20"] <= -20),
        ("낙20 -30%", lambda x: x["낙20"] <= -30),
        ("낙60 -20%", lambda x: x["낙60"] is not None and x["낙60"] <= -20),
        ("낙60 -30%", lambda x: x["낙60"] is not None and x["낙60"] <= -30),
        ("작은 것 (300~800억)", lambda x: 300 <= x["시총억"] < 800),
        ("큰 것 (800~2,000억)", lambda x: 800 <= x["시총억"] < 2000),
    )
    for 라, fn in 재료들:
        앞칸 = [x for x in 사건 if x["해"] <= "2022" and fn(x)]
        뒤칸 = [x for x in 사건 if x["해"] >= "2023" and fn(x)]
        r1, r2 = 셈(앞칸), 셈(뒤칸)
        if not r1 or not r2:
            print(f"  {라:<28}{'표본 부족':>10}")
            continue
        차 = r2[1] - r1[1]
        표 = "  ⚠️" if 차 <= -5 else ("  ⭐" if 차 >= 0 else "")
        print(f"  {라:<28}{r1[1]:>9.1f}%{r2[1]:>9.1f}%{차:>+8.1f}p"
              f"{r2[0]:>12,}{표}")

    print("\n" + "=" * 96)
    print("  읽는 법")
    print("    - A 가 기준선이다. 여기가 떨어졌으면 **시장이 달라진 것**이다")
    print("    - B 가 줄었으면 **살 게 없어진 것**이고, 안 줄었으면 **잘 안 맞는 것**이다")
    print("    - E 에서 ⭐ 가 붙은 재료는 **최근에도 안 약해진 것**이다 — 거기서 시작한다")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_204차_최근약화진단.txt")

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
