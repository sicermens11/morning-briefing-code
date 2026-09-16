#!/usr/bin/env python3
r"""
percode_lab.py — **216차 · 개별 종목별 규칙** (2026-09-10 신설)

## 사용자가 「둘 다」로 답한 것 중 남은 하나
```
「규모나 섹터나, **종목에 맞춰서** 하고, 다음 많은 기회를 찾고」
205차  종목 **성격별**(변동성·거래대금·회전율·주가대) -> 12칸 **전부 무너짐**
216차  **개별 종목마다** — 삼성전자용 규칙, 한미반도체용 규칙
```

## 판정 기준 (먼저 밝힌다 — [[judge-criteria-need-user-check]])
```
① **앞 8년에서 종목마다** 규칙을 찾아 **뒤 8년에 그대로** 써본다
② 뒤 기간에 「모든 종목 같은 규칙」보다 나아야 통과다
③ ⚠️ **무너지면 그게 답이다** — 「종목별로 나누면 과적합된다」를 숫자로 확인하는 것이니
   실패해도 소득이다
```

## ⚠️ 표본이 문제다
```
한 종목의 16.7년 = **4,175일**, 그중 신호가 걸리는 건 **수십 번**.
수십 번으로 규칙을 고르면 거의 **우연**이다.
=> **앞 기간에 신호가 60번 이상** 걸린 종목만 본다
```

쓰는 법:
    python scripts\percode_lab.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import rule_def as R  # noqa: E402   ⭐ 2026-09-16 — 「지금 규칙」 값은 여기서만

_시작 = "20100104"
_앞최소 = 60          # 앞 기간에 이만큼은 걸려야 규칙을 고른다
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
            시총억 = vs[k][1] / 1e8
            if 시총억 < 100 or vs[k][2] / 1e8 < 1.0:
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

    def 맞나(x, 규):
        bk, bt, nk, nt = 규
        b, n = x.get(bk), x.get(nk)
        return (b is not None and b <= bt and n is not None and n <= nt)

    def 셈(칸, 최소):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (len(v), sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v))

    # 모두 같은 규칙 = 지금 규칙
    공통 = ("볼20", R.볼린저문턱, "낙20", R.낙폭20문턱)   # ⭐ 손으로 적힌 값이 얼어 있었다 (2026-09-16)

    print("\n" + "=" * 100)
    print("  216차 · **개별 종목별 규칙**")
    print("  ⚠️ 판정: 앞 8년에서 종목마다 찾은 규칙이 **뒤 8년에도** 통하나")
    print("     무너지면 그게 답이다 — 「종목별로 나누면 과적합된다」")
    print("=" * 100)

    쓸종목, 이긴종목 = 0, 0
    앞모두, 뒤모두, 뒤공통 = [], [], []
    골랐던규칙 = {}
    종목규칙 = {}          # ⭐ code -> 규 (gate7_lab 이 읽어 뒤 기간 자본 시뮬로 잰다 · 2026-09-15)
    for c, 줄 in 종목별.items():
        앞 = [x for x in 줄 if x["_날짜"] < 가]
        뒤 = [x for x in 줄 if x["_날짜"] >= 가]
        if len(앞) < _앞최소 or len(뒤) < _뒤최소:
            continue
        좋 = None
        for 규 in 격자:
            추 = [x for x in 앞 if 맞나(x, 규)]
            r = 셈(추, 20)
            if r and (좋 is None or r[1] > 좋[1][1]):
                좋 = (규, r)
        if not 좋:
            continue
        규, r앞 = 좋
        r뒤 = 셈([x for x in 뒤 if 맞나(x, 규)], 10)
        r공 = 셈([x for x in 뒤 if 맞나(x, 공통)], 10)
        if not r뒤 or not r공:
            continue
        쓸종목 += 1
        골랐던규칙[규] = 골랐던규칙.get(규, 0) + 1
        종목규칙[c] = list(규)
        앞모두.append(r앞[1])
        뒤모두.append(r뒤[1])
        뒤공통.append(r공[1])
        if r뒤[1] > r공[1]:
            이긴종목 += 1

    print(f"\n  앞 기간에 **{_앞최소}번 이상** 걸린 종목 **{쓸종목:,}개**")
    if 쓸종목:
        print(f"\n  {'':<28}{'앞 이김':>10}{'뒤 이김':>10}")
        print(f"  {'종목마다 배운 규칙':<28}"
              f"{sum(앞모두)/len(앞모두):>9.1f}%{sum(뒤모두)/len(뒤모두):>9.1f}%")
        print(f"  {'모두 같은 규칙 (지금)':<28}{'':>10}"
              f"{sum(뒤공통)/len(뒤공통):>9.1f}%")
        차 = sum(뒤모두)/len(뒤모두) - sum(뒤공통)/len(뒤공통)
        떨 = sum(뒤모두)/len(뒤모두) - sum(앞모두)/len(앞모두)
        print(f"\n     ⇒ 뒤 기간 차이 **{차:+.1f}%p** · "
              f"앞→뒤 **{떨:+.1f}%p**")
        print(f"     ⇒ 종목마다 배운 규칙이 이긴 종목 "
              f"**{이긴종목:,}/{쓸종목:,}개 ({이긴종목/쓸종목*100:.0f}%)**")
        판 = ("✅ **종목별로 나눌 값어치가 있다**" if 차 > 0 and 이긴종목/쓸종목 > 0.55
              else "❌ **과적합이다 — 종목별로 나누면 안 된다**")
        print(f"     ⇒ {판}")

        # 어떤 규칙이 많이 뽑혔나
        print("\n  ── 종목마다 고른 규칙 — 많이 뽑힌 순 ──")
        for 규, n in sorted(골랐던규칙.items(), key=lambda z: -z[1])[:10]:
            bk, bt, nk, nt = 규
            print(f"     {bk}일 {bt:+.1f}σ · {nk}일 {nt}%"
                  f"{n:>8}개 종목 ({n/쓸종목*100:>4.1f}%)")
        print(f"     서로 다른 규칙 **{len(골랐던규칙)}가지** / 격자 {len(격자)}칸")
        # ⭐ 「몇 가지로 몰리나」 — 사용자 지적 (2026-09-15). 상위 5 규칙이 종목의 몇 % 를 덮나
        _상위 = sorted(골랐던규칙.values(), reverse=True)
        _덮 = sum(_상위[:5]) / max(쓸종목, 1) * 100
        print(f"     ⭐ 상위 5 규칙이 종목의 **{_덮:.0f}%** 를 덮는다 "
              f"(절반 넘으면 몰린 것 · 그 아래면 제각각)")
        # ⭐ 표 저장 — gate7_lab 「종목마다 배운 규칙을 돈으로」 절이 읽는다
        _밖 = os.path.join(O._DATA, "percode-rules.json")
        json.dump({"앞끝": 가, "규칙": 종목규칙}, io.open(_밖, "w", encoding="utf-8"),
                  ensure_ascii=False)
        print(f"     ✅ 종목 {len(종목규칙):,}개 규칙 저장 → {_밖}")
        if len(골랐던규칙) > 쓸종목 * 0.3:
            print("     ⚠️ 규칙이 **제각각**이다 — 종목마다 다른 답이 나왔다는 것은")
            print("        **우연**일 가능성이 크다")

    print("\n" + "=" * 100)
    print("  읽는 법")
    print("    - **뒤 기간이 답이다.** 앞에서 좋은 건 당연하다(거기서 골랐으니)")
    print("    - 이긴 종목이 **절반 안팎**이면 동전 던지기와 같다 — 과적합이다")
    print("    - 규칙이 제각각일수록 우연이다. 한두 가지로 몰리면 그게 진짜 신호다")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_216차_개별종목별.txt")

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
