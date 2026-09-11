#!/usr/bin/env python3
r"""
corr_lab.py — **194차 · 상관으로 무리 만들기** (2026-09-09 신설)

## 왜 만드나 — 분류표가 틀렸다
```
사용자: 「여태까지 섹터 테스트가 **표준산업분류로 돌았다면 다시 테스트** 해야하는 거 아니야?」

맞다. 지금까지 여덟 시험이 쓴 「섹터」는 두 겹으로 뭉개져 있었다:
  industry.json 63종  ->  _업종map 으로 다시 20종  ->  KRX 업종지수
  · 63종에 **「선박」이 아예 없다**(0개). 조선 본선은 「기타운송장비」다
  · 방산도 「기타운송장비」 -> 20종에서 **「운송장비·부품」** = **자동차(127종목)와 같은 칸**
    => 「조선이 업종 대비 얼마나 빠졌나」를 잰다면서 실은 **「자동차 대비」**를 쟀다
  · 반도체 소부장 26종목은 기계·장비(12)·전자부품(6)·의료광학(4)·화학(2)
    => **한 무리가 아니라 네 무리로 흩어져** 있었다
  · AI 소프트웨어는 **「출판」(7)**
```

## 이 시험의 수 — 분류표를 안 쓴다
```
「같이 움직이는 종목」을 **자료에서 직접 찾는다.**
  · 전체 종목에 적용된다 (가치사슬 맵은 140종목뿐이라 전체 시장엔 못 쓴다)
  · 분류 오류가 원천적으로 없다
  · 사용자의 「반도체는 같이 오르고 같이 내린다」를 분류표 없이 확인한다
```

## ⚠️⚠️ 시장 요인을 **반드시 뺀다**
```
그냥 상관을 재면 **전 종목이 한 덩어리**가 된다 — 시장이 빠지면 다 같이 빠지니까.
그래서 종목 수익률에서 **그날 시장 평균**을 뺀 **잔차**로 상관을 잰다.
그래야 「시장 말고 **이 무리만의** 공통 움직임」이 보인다
```

## ⚠️ 미리보기(look-ahead) 막기
```
무리는 **그 해가 시작되기 전 120거래일**로 만든다.
그 무리를 그 해 동안 쓴다. 그 해 자료로 무리를 만들면 미리보기가 된다
```

## 재는 것
```
A  해마다 무리가 몇 개·얼마나 큰가          <- 가장 큰 무리가 수백이면 문턱이 낮은 것
B  ⭐ **무리에 이름 붙이기** — 대표 종목 셋
     (사용자 걱정: 「무리 이름이 없어 브리핑에서 설명하기 어렵다」)
C  ⭐ **가치사슬 14섹터와 얼마나 겹치나**    <- 이 방법이 맞는지 스스로 채점
D  ⭐ **무리 안 「같이 빠졌나」** (188차를 진짜 무리로 다시)
E  무리 크기가 클수록 「같이 빠짐」이 센가
F  ⭐ **업종형 무리 vs 테마형 무리** (2026-09-09 더함)
     194차에서 이름 없는 무리가 **대북 경협주**로 밝혀졌다 —
     아난티(숙박)·남해화학(화학)·대아티아이(전기장비) · 업종 여섯 갈래에 상관 0.61
     ⚠️ 업종 분류는 무리를 **만드는 데는 안 쓴다.** 만들어진 무리의 **성격을 재는 데만** 쓴다
```

쓰는 법:
    python scripts\corr_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from chain_map import 읽기 as 맵읽기  # noqa: E402

_시작 = "20100104"
_창 = 120            # 무리를 만들 때 보는 거래일
_최소시총 = 300       # 억
# ⚠️ 문턱 0.5 에선 **200종목이 한 덩어리**가 됐다 (현대차·기아·KB금융).
# 사슬처럼 이어진 것(chaining)이라 0.6·0.65 로 올려 다시 잰다 -> 195차
_쓸문턱 = float(os.environ.get("MUNTEOK") or 0.5)


class 이음:
    """union-find — 상관이 문턱을 넘는 것끼리 잇는다"""

    def __init__(self):
        self.p = {}

    def 찾기(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def 잇기(self, a, b):
        ra, rb = self.찾기(a), self.찾기(b)
        if ra != rb:
            self.p[rb] = ra

    def 무리들(self):
        난것 = {}
        for x in self.p:
            난것.setdefault(self.찾기(x), []).append(x)
        return 난것


def 무리만들기(잔차, 문턱):
    r"""{코드: [표준화된 잔차]} -> {대표: [코드들]}

    ⚠️ 137만 쌍을 다 본다. 표준화해 뒀으므로 상관 = 내적 / n
    """
    코들 = sorted(잔차)
    n = len(코들)
    if n < 2:
        return {}
    길 = len(잔차[코들[0]])
    u = 이음()
    for c in 코들:
        u.찾기(c)
    for i in range(n):
        a = 잔차[코들[i]]
        for j in range(i + 1, n):
            b = 잔차[코들[j]]
            s = 0.0
            for k in range(길):
                s += a[k] * b[k]
            if s / 길 >= 문턱:
                u.잇기(코들[i],코들[j])
    return {k: v for k, v in u.무리들().items() if len(v) >= 3}


def _업종():
    """{코드: 업종명} — **무리를 나누려는 게 아니라 무리의 성격을 재려는 것**이다.

    ⚠️ 이 분류(표준산업분류 63종)는 조선·방산·반도체를 못 가른다.
       그래서 무리를 **만드는 데는 절대 안 쓴다.** 만들어진 무리가
       「한 업종에 몰렸나(업종형) / 흩어졌나(테마형)」를 재는 데만 쓴다
    """
    import json
    p = os.path.join(O._DATA, "industry.json")
    if not os.path.exists(p):
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}
    return {c: str((v or {}).get("업종명") or "") for c, v in d.items()}


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    자리 = {d: i for i, d in enumerate(날)}
    print(f"  거래일 {len(날):,}일 · {날[0]} ~ {날[-1]}", flush=True)

    이름 = {}
    try:
        import json
        z = json.load(io.open(os.path.join(O._DATA, "stock-base.json"),
                              encoding="utf-8-sig"))["종목"]
        이름 = {c: v.get("이름") or c for c, v in z.items()}
    except Exception:  # noqa: BLE001
        pass

    맵 = 맵읽기()
    가치 = {}
    for s, 들 in 맵.items():
        for _, c in 들:
            if c and c not in 가치:
                가치[c] = s

    # ── 해마다 무리를 만든다 (그 해 시작 **전** 120일로) ──
    해들 = sorted({d[:4] for d in 날})[1:]     # 첫 해는 앞자료가 모자라 뺀다
    무리해 = {}          # 해 -> {대표: [코드]}
    무리속 = {}          # (해, 코드) -> 대표
    for 해 in 해들:
        첫 = next((d for d in 날 if d[:4] == 해), None)
        if 첫 is None:
            continue
        끝 = 자리[첫] - 1
        시 = 끝 - _창 + 1
        if 시 < 1:
            continue
        구간 = 날[시:끝 + 1]
        # 그 구간 내내 살아 있고 크기가 되는 종목만
        후 = None
        for d in 구간:
            오 = {c for c, v in 주가[d].items()
                  if v[1] / 1e8 >= _최소시총 and v[2] / 1e8 >= 1.0}
            후 = 오 if 후 is None else (후 & 오)
        후 = sorted(후 or [])
        if len(후) < 50:
            continue
        # 일간 수익률
        수익 = {}
        for c in 후:
            줄 = []
            좋 = True
            for k in range(1, len(구간)):
                앞 = 주가[구간[k - 1]].get(c)
                뒤 = 주가[구간[k]].get(c)
                if not 앞 or not 뒤 or 앞[0] <= 0:
                    좋 = False
                    break
                줄.append(뒤[0] / 앞[0] - 1)
            if 좋:
                수익[c] = 줄
        if len(수익) < 50:
            continue
        길 = len(next(iter(수익.values())))
        # ⚠️⚠️ **시장 요인을 뺀다** — 안 빼면 전 종목이 한 덩어리가 된다
        시장 = [sum(수익[c][k] for c in 수익) / len(수익) for k in range(길)]
        잔차 = {}
        for c, 줄 in 수익.items():
            z2 = [줄[k] - 시장[k] for k in range(길)]
            m, sd = O.빠른평균표준(z2)
            if not sd:
                continue
            잔차[c] = [(v - m) / sd for v in z2]
        무 = 무리만들기(잔차, _쓸문턱)
        무리해[해] = 무
        for 대, 들 in 무.items():
            for c in 들:
                무리속[(해, c)] = 대
        print(f"  {해}년 · 종목 {len(잔차):,} -> **무리 {len(무)}개** "
              f"(가장 큰 무리 {max((len(v) for v in 무.values()), default=0)}종목)",
              flush=True)

    # ⭐⭐ **무리를 파일로 남긴다** (2026-09-09) — 다른 시험이 읽어 쓴다.
    #    무리를 만드는 데 10분이 드는데 197·198차가 **같은 무리**를 써야 한다.
    #    ⚠️ 문턱마다 따로 남긴다 — 0.5 와 0.6 은 아주 다르다 (200종목 vs 41종목)
    무리저장 = os.path.join(O._DATA, f"_무리_{int(_쓸문턱 * 100)}.json")
    try:
        import json as _j
        with io.open(무리저장, "w", encoding="utf-8") as _sf:
            _j.dump({"문턱": _쓸문턱, "창": _창, "만든날": 날[-1],
                     "해마다": {해: {대: 들 for 대, 들 in 무.items()}
                              for 해, 무 in 무리해.items()}},
                    _sf, ensure_ascii=False)
        print(f"  무리를 남겼다 -> {os.path.basename(무리저장)}", flush=True)
    except Exception as _e:  # noqa: BLE001
        print(f"  ⚠️ 무리를 못 남겼다: {type(_e).__name__}", flush=True)

    print("\n" + "=" * 104)
    print("  194차 · **상관으로 무리 만들기** (분류표를 안 쓴다)")
    print("  사용자: 「여태까지 섹터 테스트가 **표준산업분류로 돌았다면 다시 테스트** 해야하는 거 아니야?」")
    print(f"  {날[0]} ~ {날[-1]} · 창 {_창}일 · 문턱 상관 {_쓸문턱}")
    print("  ⚠️ 무리는 **그 해가 시작되기 전** 120일로 만든다 (미리보기 막기)")
    print("  ⚠️ **시장 요인을 뺀 잔차**로 잰다 — 안 빼면 전 종목이 한 덩어리가 된다")
    print("=" * 104)

    # ══ A ══
    print("\n  ── A **해마다 무리가 몇 개 생겼나** ──")
    print(f"  {'해':<8}{'무리':>7}{'묶인 종목':>10}{'가장 큰 무리':>13}{'평균 크기':>10}")
    for 해 in sorted(무리해):
        무 = 무리해[해]
        크 = [len(v) for v in 무.values()]
        if not 크:
            print(f"  {해:<8}{0:>7}")
            continue
        print(f"  {해:<8}{len(무):>7}{sum(크):>10}{max(크):>13}{sum(크)/len(크):>10.1f}")

    # ══ B ══
    막 = sorted(무리해)[-1] if 무리해 else None
    if 막:
        print(f"\n  ── B ⭐ **무리에 이름 붙이기** ({막}년 · 큰 무리 열둘) ──")
        print("     대표는 그 무리에서 **시총이 큰 종목 셋**이다")
        첫 = next(d for d in 날 if d[:4] == 막)
        시총 = {c: v[1] / 1e8 for c, v in 주가[첫].items()}
        무 = sorted(무리해[막].items(), key=lambda kv: -len(kv[1]))[:12]
        for 대, 들 in 무:
            들2 = sorted(들, key=lambda c: -시총.get(c, 0))
            머 = " · ".join(f"{이름.get(c, c)}" for c in 들2[:3])
            # 그 무리에 가치사슬 섹터가 있으면 같이 보여준다 (채점용)
            섹 = {}
            for c in 들:
                s = 가치.get(c)
                if s:
                    섹[s] = 섹.get(s, 0) + 1
            꼬 = ("   [가치사슬: "
                  + ", ".join(f"{k} {v}" for k, v in
                              sorted(섹.items(), key=lambda kv: -kv[1])[:2]) + "]"
                  ) if 섹 else ""
            print(f"  {len(들):>3}종목  {머[:46]:<48}{꼬}")

    # ══ C ══
    print("\n  ── C ⭐ **가치사슬 14섹터와 얼마나 겹치나** (이 방법이 맞는지 채점) ──")
    print("     가치사슬 종목 둘이 **같은 무리**에 들어간 비율")
    print(f"  {'섹터':<22}{'종목':>5}{'같은 무리에':>12}{'가장 큰 덩어리':>14}")
    if 막:
        무속 = {c: 대 for 대, 들 in 무리해[막].items() for c in 들}
        for s in sorted(맵):
            코 = [c for _, c in 맵[s] if c and c in 무속]
            if len(코) < 3:
                print(f"  {s:<22}{len(코):>5}{'(무리에 든 게 셋 미만)':>26}")
                continue
            뭉 = {}
            for c in 코:
                뭉[무속[c]] = 뭉.get(무속[c], 0) + 1
            큰 = max(뭉.values())
            print(f"  {s:<22}{len(코):>5}{len(뭉):>9}무리{큰:>11}종목")

    # ══ D ══
    print("\n  ── D ⭐⭐ **무리 안 「같이 빠졌나」** (188차를 진짜 무리로 다시) ──")
    print("     ⚠️ 188차는 뭉개진 업종지수로 쟀다. 여기서는 **같이 움직이는 것끼리** 재본다")
    사건 = []
    for i, d in enumerate(날):
        해 = d[:4]
        if 해 not in 무리해 or i + 20 >= len(날):
            continue
        for c, v in 주가[d].items():
            대 = 무리속.get((해, c))
            if 대 is None:
                continue
            k = i - 20
            if k < 0:
                continue
            앞 = 주가[날[k]].get(c)
            if not 앞 or v[1] / 1e8 < _최소시총 or v[2] / 1e8 < 1.0:
                continue
            끝 = 주가[날[i + 20]].get(c)
            사건.append({"code": c, "무리": 대, "_날짜": d,
                         "낙20": (v[0] / 앞[0] - 1) * 100,
                         "_20": (O.폐지손실 if not 끝 else (끝[0] / v[0] - 1) * 100)})
    print(f"     사건 {len(사건):,}건", flush=True)

    # 그날 그 무리의 낙폭 중앙값
    묶 = {}
    for x in 사건:
        묶.setdefault((x["_날짜"], x["무리"]), []).append(x["낙20"])
    중 = {}
    for k, v in 묶.items():
        v.sort()
        중[k] = v[len(v) // 2]
    for x in 사건:
        m = 중.get((x["_날짜"], x["무리"]))
        x["무리낙폭"] = m
        x["무리대비"] = x["낙20"] - m if m is not None else None

    해수 = max(len({d[:4] for d in 날}), 1)

    def 세기(칸):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 200:
            return None
        return (len(칸), len(칸) / 해수,
                sum(1 for z in v if z > 0) / len(v) * 100, sum(v) / len(v))

    def 찍(라, r, 폭=40):
        if r is None:
            print(f"  {라:<{폭}}{'표본 부족':>28}")
        else:
            print(f"  {라:<{폭}}{r[0]:>9,}{r[1]:>8.0f}{r[2]:>9.1f}%{r[3]:>+9.2f}")

    머 = f"  {'':<40}{'건수':>9}{'1년에':>8}{'20일 이김':>10}{'평균':>9}"
    깊 = [x for x in 사건 if x["낙20"] <= -20]
    print(머)
    찍("[견줌] 20일 -20%↓ 빠진 것 전부", 세기(깊))
    print()
    for 라, lo, hi in (("무리가 **올라 있다** (+5%↑)", 5, 9e9),
                       ("무리가 제자리 (-5~+5%)", -5, 5),
                       ("무리도 빠짐 (-5~-10%)", -10, -5),
                       ("무리도 많이 (-10~-20%)", -20, -10),
                       ("**무리가 폭락 (-20%↓)**", -9e9, -20)):
        찍(라, 세기([x for x in 깊 if x["무리낙폭"] is not None
                    and lo <= x["무리낙폭"] < hi]))
    print()
    찍("**나만 빠짐** (무리보다 15%p 넘게 더)",
       세기([x for x in 깊 if x["무리대비"] is not None and x["무리대비"] <= -15]))
    찍("**같이 빠짐** (무리와 비슷 ±10%p)",
       세기([x for x in 깊 if x["무리대비"] is not None
             and -10 <= x["무리대비"] <= 10]))

    # ══ E ══
    print("\n  ── E **무리가 클수록 「같이 빠짐」이 센가** ──")
    print(머)
    크기 = {}
    for 해, 무 in 무리해.items():
        for 대, 들 in 무.items():
            크기[(해, 대)] = len(들)
    for 라, lo, hi in (("무리 3~5종목", 3, 6), ("무리 6~10종목", 6, 11),
                       ("무리 11~20종목", 11, 21), ("무리 21종목↑", 21, 9999)):
        칸 = [x for x in 깊
              if lo <= 크기.get((x["_날짜"][:4], x["무리"]), 0) < hi
              and x["무리대비"] is not None and -10 <= x["무리대비"] <= 10]
        찍(f"{라} · 같이 빠짐", 세기(칸))

    # ══ F ══
    print("\n  ── F ⭐⭐ **업종형 무리 vs 테마형 무리** ──")
    print("     194차에서 이름 없는 무리를 열어보니 **대북 경협주**였다 —")
    print("     아난티(숙박)·남해화학(화학)·대아티아이(전기장비)·좋은사람들(의복)")
    print("     업종 여섯 갈래인데 평균 상관 0.61. **테마주는 업종으로 안 잡힌다**")
    산업 = _업종()
    if not 산업:
        print("     ⚠️ industry.json 을 못 읽었다 — F절을 건너뛴다")
    else:
        # 무리마다 「업종 쏠림」 = 가장 많은 업종의 비율
        쏠림 = {}
        for 해, 무 in 무리해.items():
            for 대, 들 in 무.items():
                셈 = {}
                for c in 들:
                    나 = 산업.get(c) or "?"
                    셈[나] = 셈.get(나, 0) + 1
                쏠림[(해, 대)] = max(셈.values()) / len(들)
        for x in 사건:
            x["업종쏠림"] = 쏠림.get((x["_날짜"][:4], x["무리"]))

        print(f"\n   [무리 성격마다 「같이 빠짐」이 다른가]")
        print(머)
        for 라, lo, hi in (("**테마형** (한 업종 비중 40% 미만)", 0.0, 0.4),
                           ("섞임 (40~70%)", 0.4, 0.7),
                           ("**업종형** (한 업종 70%↑)", 0.7, 1.01)):
            칸 = [x for x in 깊 if x.get("업종쏠림") is not None
                  and lo <= x["업종쏠림"] < hi]
            찍(f"{라} · 전부", 세기(칸))
            찍(f"  └ 나만 빠짐",
               세기([x for x in 칸 if x["무리대비"] is not None
                     and x["무리대비"] <= -15]))
            찍(f"  └ **같이 빠짐**",
               세기([x for x in 칸 if x["무리대비"] is not None
                     and -10 <= x["무리대비"] <= 10]))
            print()

        # 어느 쪽이 얼마나 되나
        전 = [x for x in 사건 if x.get("업종쏠림") is not None]
        if 전:
            테 = sum(1 for x in 전 if x["업종쏠림"] < 0.4)
            업 = sum(1 for x in 전 if x["업종쏠림"] >= 0.7)
            print(f"   무리에 든 사건 {len(전):,}건 중 "
                  f"**테마형 {테/len(전)*100:.0f}%** · "
                  f"업종형 {업/len(전)*100:.0f}% · "
                  f"섞임 {(len(전)-테-업)/len(전)*100:.0f}%")

        # 막해의 무리를 성격별로 보여준다
        if 막:
            print(f"\n   [{막}년 무리를 성격별로 — 큰 것부터]")
            첫2 = next(d for d in 날 if d[:4] == 막)
            시총2 = {c: v[1] / 1e8 for c, v in 주가[첫2].items()}
            줄들 = sorted(무리해[막].items(), key=lambda kv: -len(kv[1]))[:14]
            for 대, 들 in 줄들:
                s = 쏠림.get((막, 대))
                꼴 = ("**테마형**" if s is not None and s < 0.4
                      else ("업종형" if s is not None and s >= 0.7 else "섞임"))
                들2 = sorted(들, key=lambda c: -시총2.get(c, 0))
                머2 = " · ".join(이름.get(c, c) for c in 들2[:3])
                업들 = sorted({산업.get(c) or "?" for c in 들})
                print(f"   {len(들):>3}종목 {꼴:<8}{머2[:40]:<42}"
                      f"업종 {len(업들)}가지")

    print("\n" + "=" * 104)
    print("  읽는 법")
    print("    - **C 가 이 방법의 채점표다.** 가치사슬 섹터가 한 무리로 뭉치면 방법이 맞은 것이다")
    print("    - A 에서 「가장 큰 무리」가 수백 종목이면 **문턱이 낮은 것**이다 (다 이어져 버렸다)")
    print("    - D 를 188차(뭉개진 업종)와 견준다 — 차이가 커지면 분류가 문제였던 것이다")
    print("    - ⚠️ 무리는 해마다 바뀐다. 브리핑에 쓰려면 **대표 종목으로 이름**을 붙여야 한다(B)")
    print("    - ⭐ F 에서 테마형과 업종형이 갈리면 **무리 성격마다 규칙을 달리** 볼 값어치가 있다")
    print("      (테마주는 재무와 무관하게 움직인다 — 우리 재무 조건과 궁합이 다를 수 있다)")
    print("=" * 104)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-09_194차_상관무리.txt")

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
