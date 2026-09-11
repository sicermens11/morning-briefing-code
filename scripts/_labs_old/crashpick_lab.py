#!/usr/bin/env python3
r"""
crashpick_lab.py — **211차 · 시장 폭락일에 무엇을 고르나** (2026-09-10 신설)

## 왜
```
210차: **기존 OR 시장낙폭≤-7%** 가 4관문을 통과했다
       1년 5,700개 · **70.0%** (+9.5%p) · 기회 **323%**
그런데 시장이 -7% 빠진 날은 **1년에 13일**뿐이고,
그 며칠에 후보가 **수백 개**씩 몰린다.
=> **하루 4종목을 어떻게 고를지**가 정해져 있지 않다
```
⚠️ 187차에서 「고르는 순서는 무작위와 0.5%p 차이뿐」이 나왔지만
   그건 **후보가 적을 때**(하루 몇 개) 잰 것이다.
   후보가 **수백 개**일 때도 그런지는 **모른다**

## 판정 기준 (먼저 밝힌다)
```
폭락일에 후보를 어떤 순서로 고를 때 **상위 4개의 20일 이김**이 가장 높은가.
① 무작위와 **+3%p 이상** 차이나야 뜻이 있다
② 열일곱 해 중 **12해 이상**에서 무작위보다 나아야 한다 (우연 배제)
```

쓰는 법:
    python scripts\crashpick_lab.py
"""
import glob
import io
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20100104"
_문턱 = -7.0
_고를수 = 4


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일", flush=True)

    # 시장 20일 낙폭
    시장 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        v = (d2.get("지수") or {}).get("코스피")
        if isinstance(v, dict):
            try:
                시장[d2.get("기준일") or os.path.basename(f)[:8]] = \
                    float(str(v.get("종가")).replace(",", ""))
            except (TypeError, ValueError):
                pass
    시날 = sorted(시장)
    시낙 = {}
    for i2, d in enumerate(시날):
        if i2 >= 20 and 시장[시날[i2 - 20]] > 0:
            시낙[d] = (시장[d] / 시장[시날[i2 - 20]] - 1) * 100
    폭락일 = [d for d in 날 if (시낙.get(d) or 0) <= _문턱]
    print(f"  시장 20일 낙폭 ≤ {_문턱}% 인 날 **{len(폭락일)}일**", flush=True)

    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            계열.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(i)

    폭집 = set(폭락일)
    print("  폭락일 후보 모으는 중...", flush=True)
    하루 = {}
    for c, vs in 계열.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(120, len(vs)):
            i = ii[k]
            d8 = 날[i]
            if d8 not in 폭집:
                continue
            시총억 = vs[k][1] / 1e8
            대금억 = vs[k][2] / 1e8
            if 시총억 < 100 or 대금억 < 1.0:
                continue
            j = i + 20
            if j >= len(날):
                continue
            c1 = 종[k]
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            m20, sd20 = O.창평균표준(종, k, 20)
            m60, _ = O.창평균표준(종, k, 60)
            갭 = (갭표.get(d8) or {}).get(c)
            일 = []
            for z in range(k - 19, k + 1):
                앞 = 종[z - 1]
                if 앞 > 0:
                    일.append(종[z] / 앞 - 1)
            _, 일sd = O.빠른평균표준(일) if len(일) >= 15 else (0, 0)
            하루.setdefault(d8, []).append({
                "code": c, "해": d8[:4],
                "볼20": ((c1 - m20) / (2 * sd20)) if sd20 else None,
                "낙20": (c1 / 종[k - 20] - 1) * 100,
                "낙60": (c1 / 종[k - 60] - 1) * 100 if k >= 60 else None,
                "시총억": 시총억, "대금억": 대금억,
                "회전율": (대금억 / 시총억 * 100) if 시총억 > 0 else 0,
                "갭": 갭,
                "변동": 일sd * (252 ** 0.5) * 100 if 일sd else None,
                "60일선대비": ((c1 / m60 - 1) * 100) if m60 else None,
                "_20": 뒤,
            })
    쓸날 = [d for d in sorted(하루) if len(하루[d]) >= _고를수]
    총 = sum(len(하루[d]) for d in 쓸날)
    print(f"  쓸 수 있는 폭락일 **{len(쓸날)}일** · 후보 {총:,}개"
          f" (하루 평균 **{총/max(1,len(쓸날)):.0f}개**)", flush=True)

    def 고르기(라, 키, 거꾸로=False, 씨=None):
        """날마다 그 순서로 상위 4개를 고른다 -> (이김%, 평균, 뽑은 수)"""
        모 = []
        for d in 쓸날:
            칸 = [x for x in 하루[d] if x.get(키) is not None] if 키 else list(하루[d])
            if len(칸) < _고를수:
                continue
            if 키 is None:
                r = random.Random(씨 or 0)
                r.shuffle(칸)
            else:
                칸.sort(key=lambda z: z[키], reverse=거꾸로)
            모 += 칸[:_고를수]
        v = [z["_20"] for z in 모 if z.get("_20") is not None]
        if len(v) < 100:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(v))

    print("\n" + "=" * 100)
    print("  211차 · **시장 폭락일에 무엇을 고르나**")
    print(f"  시장 20일 낙폭 ≤ {_문턱}% 인 날, 후보 중 **상위 {_고를수}개**를 고른다")
    print("  ⚠️ 판정: 무작위와 **+3%p 이상** 차이나고 **12해 이상**에서 나아야 뜻이 있다")
    print("=" * 100)

    # 무작위 기준선 (씨 여럿)
    무 = [고르기("무작위", None, 씨=s) for s in range(20)]
    무 = [z for z in 무 if z]
    무이 = sum(z[0] for z in 무) / len(무)
    무평 = sum(z[1] for z in 무) / len(무)
    print(f"\n  [기준선] **무작위 20번** — 이김 **{무이:.1f}%** · 평균 {무평:+.2f}%")

    순서들 = (
        ("갭 깊은 순", "갭", False),
        ("갭 얕은 순", "갭", True),
        ("20일 낙폭 깊은 순", "낙20", False),
        ("20일 낙폭 **얕은** 순", "낙20", True),
        ("60일 낙폭 깊은 순", "낙60", False),
        ("볼린저 낮은 순", "볼20", False),
        ("볼린저 **높은** 순", "볼20", True),
        ("시총 작은 순", "시총억", False),
        ("시총 큰 순", "시총억", True),
        ("거래대금 많은 순", "대금억", True),
        ("회전율 높은 순", "회전율", True),
        ("변동성 낮은 순", "변동", False),
        ("변동성 높은 순", "변동", True),
        ("60일선 위인 순", "60일선대비", True),
        ("60일선 아래인 순", "60일선대비", False),
    )
    print(f"\n  {'고르는 순서':<24}{'이김':>8}{'평균':>9}{'무작위 대비':>12}{'뽑은 수':>9}")
    난것 = []
    for 라, 키, 거꾸로 in 순서들:
        r = 고르기(라, 키, 거꾸로)
        if not r:
            print(f"  {라:<24}{'표본 부족':>8}")
            continue
        차 = r[0] - 무이
        표 = "  ⭐" if 차 >= 3 else ("  ⚠️" if 차 <= -3 else "")
        난것.append((라, 키, 거꾸로, r, 차))
        print(f"  {라:<24}{r[0]:>7.1f}%{r[1]:>+9.2f}{차:>+11.1f}p{r[2]:>9,}{표}")

    # ── 해마다 몇 번 이기나 ──
    좋 = [z for z in 난것 if z[4] >= 3]
    if 좋:
        print("\n  ── ⭐ **무작위보다 +3%p 이상 나은 것** — 해마다 몇 승인가 ──")
        해목 = sorted({x["해"] for d in 쓸날 for x in 하루[d]})
        for 라, 키, 거꾸로, r, 차 in 좋:
            승 = 0
            셈 = 0
            for 해 in 해목:
                해날 = [d for d in 쓸날 if d[:4] == 해]
                if not 해날:
                    continue
                모1, 모2 = [], []
                for d in 해날:
                    칸 = [x for x in 하루[d] if x.get(키) is not None]
                    if len(칸) < _고를수:
                        continue
                    칸2 = sorted(칸, key=lambda z: z[키], reverse=거꾸로)
                    모1 += 칸2[:_고를수]
                    rr = random.Random(777)
                    칸3 = list(칸)
                    rr.shuffle(칸3)
                    모2 += 칸3[:_고를수]
                v1 = [z["_20"] for z in 모1 if z.get("_20") is not None]
                v2 = [z["_20"] for z in 모2 if z.get("_20") is not None]
                if len(v1) < 20 or len(v2) < 20:
                    continue
                셈 += 1
                if (sum(1 for z in v1 if z > 0) / len(v1)
                        > sum(1 for z in v2 if z > 0) / len(v2)):
                    승 += 1
            판 = "✅" if (셈 and 승 >= 12) else "❌"
            print(f"     {라:<24}**{승}승 {셈-승}패** / {셈}해  {판}")

    # ══ ⭐⭐ 212차 — **후보를 좁히면** ══
    print("\n" + "=" * 100)
    print("  212차 · ⭐⭐ **고르는 순서가 아니라 후보 조건**")
    print("     211차: 15가지 순서 중 **14가지가 무작위보다 나빴다**")
    print("     => 순서로는 못 이긴다. **아예 후보에서 빼는 것**이 답일 수 있다")
    print("     ⚠️ 판정: 안 좁혔을 때(무작위)보다 **+3%p 이상**,"
          " 하루 **4개 이상** 남고, **8해 이상** 승")
    print("=" * 100)

    def 좁혀서(라, 거르기):
        """조건으로 좁힌 뒤 **무작위 4개** — 순서를 안 쓴다"""
        모, 날수, 총후보 = [], 0, 0
        for d in 쓸날:
            칸 = [x for x in 하루[d] if 거르기(x)]
            if len(칸) < _고를수:
                continue
            날수 += 1
            총후보 += len(칸)
            r = random.Random(4242)
            칸2 = list(칸)
            r.shuffle(칸2)
            모 += 칸2[:_고를수]
        v = [z["_20"] for z in 모 if z.get("_20") is not None]
        if len(v) < 100:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(v), 날수,
                총후보 / max(1, 날수))

    조건들 = (
        ("[견줌] 안 좁힘", lambda x: True),
        ("시총 300억↑", lambda x: (x.get("시총억") or 0) >= 300),
        ("시총 800억↑", lambda x: (x.get("시총억") or 0) >= 800),
        ("시총 2,000억↑", lambda x: (x.get("시총억") or 0) >= 2000),
        ("시총 5,000억↑", lambda x: (x.get("시총억") or 0) >= 5000),
        ("대금 3억↑", lambda x: (x.get("대금억") or 0) >= 3),
        ("대금 10억↑", lambda x: (x.get("대금억") or 0) >= 10),
        ("회전율 4%↓", lambda x: (x.get("회전율") or 0) <= 4),
        ("회전율 1.5%↓", lambda x: (x.get("회전율") or 0) <= 1.5),
        ("변동성 50%↓", lambda x: (x.get("변동") or 999) <= 50),
        ("변동성 35%↓", lambda x: (x.get("변동") or 999) <= 35),
        ("⭐ **혼자 더 빠진 것 빼기**(낙20 ≥ -25%)",
         lambda x: (x.get("낙20") or 0) >= -25),
        ("⭐ 혼자 더 빠진 것 빼기(낙20 ≥ -15%)",
         lambda x: (x.get("낙20") or 0) >= -15),
        ("⭐ 60일선 -25% 위",
         lambda x: (x.get("60일선대비") or -999) >= -25),
        ("시총 800억↑ **AND** 회전율 4%↓",
         lambda x: ((x.get("시총억") or 0) >= 800
                    and (x.get("회전율") or 0) <= 4)),
        ("시총 800억↑ AND 낙20 ≥ -25%",
         lambda x: ((x.get("시총억") or 0) >= 800
                    and (x.get("낙20") or 0) >= -25)),
    )
    기 = 좁혀서("[견줌]", lambda x: True)
    print(f"\n  {'후보 조건':<34}{'이김':>8}{'평균':>9}"
          f"{'대비':>8}{'날':>6}{'하루 후보':>9}")
    좋것 = []
    for 라, fn in 조건들:
        r = 좁혀서(라, fn)
        if not r:
            print(f"  {라:<34}{'표본 부족':>8}")
            continue
        차 = r[0] - (기[0] if 기 else 0)
        표 = "  ⭐" if (차 >= 3 and r[4] >= _고를수) else ""
        if 차 >= 3 and r[4] >= _고를수:
            좋것.append((라, fn, r, 차))
        print(f"  {라:<34}{r[0]:>7.1f}%{r[1]:>+9.2f}{차:>+7.1f}p"
              f"{r[3]:>6}{r[4]:>9.0f}{표}")

    if 좋것:
        print("\n  ── ⭐ 좋은 것 — **해마다 몇 승인가** ──")
        해목2 = sorted({x["해"] for d in 쓸날 for x in 하루[d]})
        for 라, fn, r, 차 in 좋것:
            승, 셈 = 0, 0
            for 해 in 해목2:
                해날 = [d for d in 쓸날 if d[:4] == 해]
                모1, 모2 = [], []
                for d in 해날:
                    전 = 하루[d]
                    후 = [x for x in 전 if fn(x)]
                    rr = random.Random(4242)
                    if len(후) >= _고를수:
                        a = list(후)
                        rr.shuffle(a)
                        모1 += a[:_고를수]
                    if len(전) >= _고를수:
                        b = list(전)
                        random.Random(4242).shuffle(b)
                        모2 += b[:_고를수]
                v1 = [z["_20"] for z in 모1 if z.get("_20") is not None]
                v2 = [z["_20"] for z in 모2 if z.get("_20") is not None]
                if len(v1) < 20 or len(v2) < 20:
                    continue
                셈 += 1
                if (sum(1 for z in v1 if z > 0) / len(v1)
                        > sum(1 for z in v2 if z > 0) / len(v2)):
                    승 += 1
            판 = "✅" if (셈 and 승 >= 8) else "❌"
            print(f"     {라:<34}**{승}승 {셈-승}패** / {셈}해  {판}")
    else:
        print("\n     ⇒ **좁혀서 나아지는 조건이 없다**")

    # ══ ⭐⭐ 213차 — **앞뒤로 갈라 확인** ══
    print("\n" + "=" * 100)
    print("  213차 · ⭐⭐ **앞뒤로 갈라 확인** (과적합 재기)")
    print("     ⚠️ 회전율 4% · 변동성 50% 는 **내가 전 기간을 보고 고른 문턱**이다.")
    print("        203·208차가 바로 이 지점에서 무너졌다")
    print("     ⚠️ 판정: **앞뒤 둘 다** 「안 좁힘」보다 나아야 하고,")
    print("        **문턱을 바꿔도** 방향이 같아야 한다")
    print("=" * 100)

    가운데 = 쓸날[len(쓸날) // 2] if 쓸날 else None

    def 반쪽(거르기, 앞이냐):
        모, 날수, 총 = [], 0, 0
        for d in 쓸날:
            if 앞이냐 and d >= 가운데:
                continue
            if (not 앞이냐) and d < 가운데:
                continue
            칸 = [x for x in 하루[d] if 거르기(x)]
            if len(칸) < _고를수:
                continue
            날수 += 1
            총 += len(칸)
            r = random.Random(4242)
            칸2 = list(칸)
            r.shuffle(칸2)
            모 += 칸2[:_고를수]
        v = [z["_20"] for z in 모 if z.get("_20") is not None]
        if len(v) < 60:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                len(v), 총 / max(1, 날수))

    문턱들 = (
        ("[견줌] 안 좁힘", lambda x: True),
        ("회전율 2%↓", lambda x: (x.get("회전율") or 0) <= 2),
        ("회전율 3%↓", lambda x: (x.get("회전율") or 0) <= 3),
        ("회전율 4%↓", lambda x: (x.get("회전율") or 0) <= 4),
        ("회전율 6%↓", lambda x: (x.get("회전율") or 0) <= 6),
        ("변동성 35%↓", lambda x: (x.get("변동") or 999) <= 35),
        ("변동성 50%↓", lambda x: (x.get("변동") or 999) <= 50),
        ("변동성 65%↓", lambda x: (x.get("변동") or 999) <= 65),
        ("회전율 4%↓ AND 변동성 50%↓",
         lambda x: ((x.get("회전율") or 0) <= 4
                    and (x.get("변동") or 999) <= 50)),
    )
    기앞 = 반쪽(lambda x: True, True)
    기뒤 = 반쪽(lambda x: True, False)
    print(f"\n     앞 {쓸날[0]}~{가운데} · 뒤 {가운데}~{쓸날[-1]}")
    print(f"\n  {'후보 조건':<28}{'앞 이김':>9}{'앞 대비':>9}"
          f"{'뒤 이김':>9}{'뒤 대비':>9}{'하루':>7}   판정")
    for 라, fn in 문턱들:
        a = 반쪽(fn, True)
        b = 반쪽(fn, False)
        if not a or not b:
            print(f"  {라:<28}{'표본 부족':>9}")
            continue
        차a = a[0] - (기앞[0] if 기앞 else 0)
        차b = b[0] - (기뒤[0] if 기뒤 else 0)
        되나 = (차a > 0 and 차b > 0 and b[2] >= _고를수)
        표 = "  ✅ **둘 다 낫다**" if 되나 else ("  ❌" if 라 != "[견줌] 안 좁힘" else "")
        print(f"  {라:<28}{a[0]:>8.1f}%{차a:>+8.1f}p"
              f"{b[0]:>8.1f}%{차b:>+8.1f}p{b[2]:>7.0f}{표}")

    print("\n" + "=" * 100)
    print("  읽는 법")
    print("    - **무작위가 기준선이다.** 187차에서 「순서는 뜻이 없다」가 나왔는데")
    print("      그건 후보가 적을 때였다. 여기선 하루 수백 개다")
    print("    - ⭐ 는 +3%p 이상 · 해마다 12승 이상이어야 진짜다")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_211차_폭락일고르기.txt")

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
