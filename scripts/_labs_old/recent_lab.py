#!/usr/bin/env python3
r"""
recent_lab.py — **207차 · 최근 3년 역방향 탐색** (2026-09-10 신설)

## 왜 순서를 뒤집나
```
지금까지는 **전 기간에서 찾아 최근에 써봤다.** 전부 무너졌다:
  204차  낙20 -30%      63.0% -> **40.4%** (아무 날 43.5%보다 나쁘다)
  205차  성격 12개 칸    **전부 무너짐** (-7.4 ~ -37.2%p) · 살아남은 칸 **0개**
  206차  규모 단독       68.9% -> **53.0%**
=> **「깊게 빠진 것을 산다」가 2023년부터 안 통한다**

그래서 **거꾸로 간다**: 최근 3년에서 **뭐가 통하는지 먼저 찾고**,
그게 앞 기간에도 통했는지 **거꾸로 확인**한다
```

## 판정 기준 (먼저 밝힌다 — [[judge-criteria-need-user-check]])
```
① 최근 3년(2023~)에 **바탕보다 뚜렷이 높다** (+5%p 이상)
② **앞 기간(2010~2022)에도 나쁘지 않다** (바탕 밑으로 안 떨어진다)
③ 최근 3년 후보가 **1년 100개 이상** (실전에서 쓸 수 있어야 한다)
⚠️ ②가 없으면 **최근에만 우연히 좋은 것**을 고르게 된다.
   최근 3년에서 고르는 것 자체가 그 구간에 대한 과적합이기 때문이다
```

쓰는 법:
    python scripts\recent_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20100104"
_최근 = "2023"


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일 · {날[0]} ~ {날[-1]}", flush=True)

    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            계열.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(i)

    볼창 = (10, 20, 60, 120, 250)
    낙창 = (10, 20, 40, 60, 120)
    print("  사건 만드는 중...", flush=True)
    사건 = []
    for c, vs in 계열.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(250, len(vs)):
            시총억 = vs[k][1] / 1e8
            if 시총억 < 100 or vs[k][2] / 1e8 < 1.0:
                continue
            c1 = 종[k]
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            x = {"해": 날[i][:4], "시총억": 시총억, "_20": 뒤}
            싼가 = False
            for w in 볼창:
                m, sd = O.창평균표준(종, k, w)
                v2 = ((c1 - m) / (2 * sd)) if sd else None
                x[f"볼{w}"] = v2
                if v2 is not None and v2 <= -0.5:
                    싼가 = True
            for w in 낙창:
                v3 = (c1 / 종[k - w] - 1) * 100 if k >= w else None
                x[f"낙{w}"] = v3
                if v3 is not None and v3 <= -5:
                    싼가 = True
            # ⚠️ 램 — 아무 데도 안 걸리는 것은 안 남긴다
            if not 싼가:
                continue
            사건.append(x)
    print(f"  사건 {len(사건):,}건", flush=True)

    최근 = [x for x in 사건 if x["해"] >= _최근]
    앞 = [x for x in 사건 if x["해"] < _최근]
    해수최 = max(len({x["해"] for x in 최근}), 1)
    해수앞 = max(len({x["해"] for x in 앞}), 1)
    print(f"  최근 {len(최근):,}건({해수최}해) · 앞 {len(앞):,}건({해수앞}해)",
          flush=True)

    def 셈(칸, 해수, 최소=200):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (len(v), len(v) / 해수,
                sum(1 for z in v if z > 0) / len(v) * 100, sum(v) / len(v))

    바탕최 = 셈(최근, 해수최)
    바탕앞 = 셈(앞, 해수앞)

    print("\n" + "=" * 100)
    print("  207차 · **최근 3년 역방향 탐색**")
    print("  ⚠️ 순서를 뒤집는다 — 최근에 통하는 것을 **먼저 찾고** 앞 기간에 거꾸로 확인")
    print("  ⚠️ 판정: ① 최근에 바탕+5%p 이상 ② 앞에서도 바탕 밑이 아님 ③ 1년 100개 이상")
    print("=" * 100)
    if 바탕최 and 바탕앞:
        print(f"\n  바탕(느슨한 후보 전부)  최근 **{바탕최[2]:.1f}%** ({바탕최[0]:,}건)"
              f" · 앞 **{바탕앞[2]:.1f}%** ({바탕앞[0]:,}건)")

    # ── A 단독 재료 ──
    print("\n  ── A **단독 재료** — 볼린저만 / 낙폭만 ──")
    print(f"  {'재료':<20}{'최근 이김':>10}{'최근 1년':>10}"
          f"{'앞 이김':>9}{'차이':>8}   판정")
    단독 = []
    for w in 볼창:
        for 문 in (-0.5, -1.0, -1.5, -2.0, -2.5):
            단독.append((f"볼{w}일 {문:+.1f}σ",
                        lambda x, a=w, b=문: (x.get(f"볼{a}") is not None
                                             and x[f"볼{a}"] <= b)))
    for w in 낙창:
        for 문 in (-5, -10, -20, -30, -40):
            단독.append((f"낙{w}일 {문}%",
                        lambda x, a=w, b=문: (x.get(f"낙{a}") is not None
                                             and x[f"낙{a}"] <= b)))
    산것 = []
    for 라, fn in 단독:
        r최 = 셈([x for x in 최근 if fn(x)], 해수최)
        r앞 = 셈([x for x in 앞 if fn(x)], 해수앞)
        if not r최 or not r앞 or not 바탕최 or not 바탕앞:
            continue
        좋최 = r최[2] - 바탕최[2]
        좋앞 = r앞[2] - 바탕앞[2]
        되나 = (좋최 >= 5 and 좋앞 >= 0 and r최[1] >= 100)
        if 되나:
            산것.append((라, fn, r최, r앞))
        표 = "  ⭐ **된다**" if 되나 else ""
        if 좋최 >= 3 or 되나:
            print(f"  {라:<20}{r최[2]:>9.1f}%{r최[1]:>10.0f}"
                  f"{r앞[2]:>8.1f}%{r최[2]-r앞[2]:>+7.1f}p{표}")
    print(f"\n     ⇒ **단독으로 된 것 {len(산것)}개**")

    # ── B 두 재료 격자 ──
    print("\n  ── B ⭐⭐ **볼린저 × 낙폭 격자** (최근 3년 기준) ──")
    print("     ⚠️ 최근에서 고르는 것 자체가 과적합이다 —"
          " **앞 기간 성적을 반드시 같이 본다**")
    격자 = []
    for bw in 볼창:
        for bt in (-0.5, -1.0, -1.5, -2.0):
            for nw in 낙창:
                for nt in (-5, -10, -20, -30):
                    격자.append((bw, bt, nw, nt))
    결과 = []
    for bw, bt, nw, nt in 격자:
        def fn(x, a=bw, b=bt, c2=nw, d=nt):
            v1, v2 = x.get(f"볼{a}"), x.get(f"낙{c2}")
            return (v1 is not None and v1 <= b
                    and v2 is not None and v2 <= d)
        r최 = 셈([x for x in 최근 if fn(x)], 해수최)
        if not r최 or r최[1] < 100:
            continue
        r앞 = 셈([x for x in 앞 if fn(x)], 해수앞)
        if not r앞:
            continue
        결과.append(((bw, bt, nw, nt), r최, r앞))
    결과.sort(key=lambda z: -z[1][2])
    print(f"\n  {'규칙':<30}{'최근 이김':>10}{'최근 1년':>10}"
          f"{'앞 이김':>9}{'차이':>8}   판정")
    된것 = []
    for (bw, bt, nw, nt), r최, r앞 in 결과[:25]:
        좋최 = r최[2] - 바탕최[2]
        좋앞 = r앞[2] - 바탕앞[2]
        되나 = (좋최 >= 5 and 좋앞 >= 0)
        if 되나:
            된것.append(((bw, bt, nw, nt), r최, r앞))
        표 = "  ⭐ **된다**" if 되나 else ("  ⚠️ 최근에만" if 좋앞 < 0 else "")
        print(f"  볼{bw}일 {bt:+.1f}σ · 낙{nw}일 {nt}%".ljust(32)
              + f"{r최[2]:>9.1f}%{r최[1]:>10.0f}"
              f"{r앞[2]:>8.1f}%{r최[2]-r앞[2]:>+7.1f}p{표}")
    print(f"\n     ⇒ 최근 상위 25개 중 **앞에서도 된 것 {len(된것)}개**")

    # ── C 최근에만 좋은 것 vs 둘 다 좋은 것 ──
    print("\n  ── C ⭐ **최근에만 좋은 것**은 몇 개인가 (과적합 재기) ──")
    최근만 = sum(1 for _, r최, r앞 in 결과
                 if (r최[2] - 바탕최[2]) >= 5 and (r앞[2] - 바탕앞[2]) < 0)
    둘다 = sum(1 for _, r최, r앞 in 결과
               if (r최[2] - 바탕최[2]) >= 5 and (r앞[2] - 바탕앞[2]) >= 0)
    앞만 = sum(1 for _, r최, r앞 in 결과
               if (r최[2] - 바탕최[2]) < 5 and (r앞[2] - 바탕앞[2]) >= 5)
    print(f"     격자 {len(결과):,}칸 중")
    print(f"       **둘 다 좋다**       {둘다:,}칸")
    print(f"       최근에만 좋다      {최근만:,}칸  ⚠️ 이만큼이 우연일 수 있다")
    print(f"       앞에서만 좋았다     {앞만:,}칸  ⚠️ 지금까지 내가 고르던 것들")

    print("\n" + "=" * 100)
    print("  읽는 법")
    print("    - ⭐ **된다**  = 최근에 바탕+5%p 이상이고 **앞에서도 바탕 밑이 아니다**")
    print("    - ⚠️ 최근에만 = 앞 기간엔 바탕보다 나빴다. **우연일 수 있다**")
    print("    - C 의 「앞에서만 좋았다」가 **지금까지 내가 고르던 것들**이다")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_207차_최근3년역방향.txt")

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
