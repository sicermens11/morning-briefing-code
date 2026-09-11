#!/usr/bin/env python3
r"""
sector_mom_lab.py — **229차 · 섹터마다 모멘텀이 통하나** (2026-09-10 신설)

## 사용자 물음
```
「그럼 **모멘텀 섹터별로는** 테스트해봤어?」
```

## ⚠️ 안 했다
```
224차  소형주 전체에서 모멘텀      ✅ (전부 실패)
227차  **규모별** 모멘텀          ✅ (네 규모대 전부 실패)
섹터별 모멘텀                    ❌ **안 함**
=> 가치사슬 시험(198~202차)은 섹터별이었지만 **재료에 모멘텀이 없었다**.
   낙폭·볼린저만 봤다
```

## 왜 섹터마다 다를 수 있나
```
방산·조선  수주 사이클이 길다 -> 추세가 **오래 갈** 수 있다
바이오     임상 결과 하나로 뒤집힌다 -> 추세가 **안 갈** 수 있다
반도체     업황 주기를 탄다
=> 재봐야 안다
```

## 재는 것
```
A ⭐⭐⭐ 섹터마다 **오름 재료** (20·60·120일 오름 · 볼린저 위)
B ⭐⭐  섹터마다 **내림 재료** (견줌용 — 어느 쪽이 나은지 보려고)
C ⭐⭐  섹터마다 **추세 이어짐** (60일 오름 + 20일도 오름)
D ⭐   섹터마다 **눌림목** (60일 오름 + 5일 눌림)
```

## 판정 기준 (먼저 밝힌다)
```
① 그 **섹터의 바탕**보다 +5%p 이상
② **세 구간 다** 같은 방향
③ 1년에 **10건 이상**
⚠️ 섹터마다 종목이 7~26개뿐이다. 표본이 작으니 **문턱을 엄하게** 본다
```

쓰는 법:
    python scripts\sector_mom_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import chain_map as CM  # noqa: E402

_시작 = "20160101"


def main():
    섹터맵 = CM.섹터표()
    if not 섹터맵:
        # chain_map 의 짜임새를 모르면 여기서 멈춘다 (짐작하지 않는다)
        후보 = [k for k in dir(CM) if not k.startswith("_")]
        print(f"  ⚠️ chain_map 에서 섹터맵을 못 얻었다. 있는 것: {후보}")
        return 1
    print(f"  섹터맵 {len(섹터맵):,}종목", flush=True)

    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일", flush=True)

    종계, 있는날 = {}, {}
    자리 = {d: i for i, d in enumerate(날)}
    for d in 날:
        for c, v in 주가[d].items():
            if c in 섹터맵:
                종계.setdefault(c, []).append(v)
                있는날.setdefault(c, []).append(자리[d])
    print(f"  섹터에 든 종목 {len(종계):,}개", flush=True)

    print("  사건 만드는 중... ⚠️ **크기·방향 둘 다 안 건다**", flush=True)
    사건 = []
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        섹 = 섹터맵[c]
        for k in range(120, len(vs)):
            if vs[k][2] / 1e8 < 1.0:
                continue
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            c1 = 종[k]
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            일간 = [(종[q] / 종[q - 1] - 1) * 100
                    for q in range(k - 59, k + 1) if 종[q - 1] > 0]
            평 = sum(일간) / len(일간) if 일간 else 0
            평소 = ((sum((z - 평) ** 2 for z in 일간) / len(일간)) ** 0.5
                    if len(일간) > 30 else None)
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            사건.append({
                "섹": 섹, "해": 날[i][:4], "_20": 뒤, "볼20": 볼20,
                "낙5": (c1 / 종[k - 5] - 1) * 100 if 종[k - 5] > 0 else None,
                "낙20": 낙20,
                "낙60": (c1 / 종[k - 60] - 1) * 100 if 종[k - 60] > 0 else None,
                "낙120": (c1 / 종[k - 120] - 1) * 100 if 종[k - 120] > 0 else None,
                "표준낙": ((낙20 / (평소 * (20 ** 0.5)))
                           if (평소 and 평소 > 0 and 낙20 is not None) else None),
            })
    print(f"  사건 **{len(사건):,}건**", flush=True)

    해수 = len(날) / 245
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"))

    def 점(칸, 최소=120):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(v))

    재료 = []
    for w in (20, 60, 120):
        for 문 in (5, 10, 20, 30):
            재료.append((f"**오름** {w}일 ≥+{문}%",
                         lambda x, a=w, b=문: (x[f"낙{a}"] is not None
                                               and x[f"낙{a}"] >= b)))
    for 문 in (0.5, 1.0, 1.5):
        재료.append((f"**오름** 볼20 ≥{문:+.1f}σ",
                     lambda x, a=문: x["볼20"] is not None and x["볼20"] >= a))
    재료.append(("**추세** 60일+20% & 20일+5%",
                 lambda x: (x["낙60"] is not None and x["낙60"] >= 20
                            and x["낙20"] is not None and x["낙20"] >= 5)))
    재료.append(("**추세** 120일+30% & 20일+5%",
                 lambda x: (x["낙120"] is not None and x["낙120"] >= 30
                            and x["낙20"] is not None and x["낙20"] >= 5)))
    재료.append(("**눌림목** 60일+20% & 5일-5%",
                 lambda x: (x["낙60"] is not None and x["낙60"] >= 20
                            and x["낙5"] is not None and x["낙5"] <= -5)))
    재료.append(("[견줌] 내림 20일 ≤-10%",
                 lambda x: x["낙20"] is not None and x["낙20"] <= -10))
    재료.append(("[견줌] 내림 20일 ≤-20%",
                 lambda x: x["낙20"] is not None and x["낙20"] <= -20))
    재료.append(("[견줌] 평소 등락폭 -2.0배↓",
                 lambda x: x["표준낙"] is not None and x["표준낙"] <= -2.0))

    섹들 = sorted({x["섹"] for x in 사건})
    print("\n" + "=" * 104)
    print("  229차 · ⭐⭐⭐ **섹터마다 모멘텀이 통하나**")
    print("     224차(전체)·227차(규모별) 에서 모멘텀은 **전부 실패**했다.")
    print("     섹터마다 성격이 다를 수 있다 — 방산·조선은 수주 사이클이 길다")
    print("     ⚠️ 섹터마다 종목이 7~26개뿐이다. 표본이 작으니 엄하게 본다")
    print("=" * 104)

    통한섹터 = []
    for 섹 in 섹들:
        칸0 = [x for x in 사건 if x["섹"] == 섹]
        바 = 점(칸0)
        if not 바:
            continue
        print(f"\n   [{섹}]  {len(칸0):,}건 · 1년 {len(칸0)/해수:,.0f}건"
              f" · **바탕 {바[0]:.1f}%**")
        print(f"  {'재료':<28}{'건수':>9}{'1년에':>7}{'이김':>8}"
              f"{'바탕대비':>9}  [구간별]")
        줄들 = []
        for 이름, fn in 재료:
            칸 = [x for x in 칸0 if fn(x)]
            r = 점(칸)
            if not r:
                continue
            방 = []
            for _, a, b in 구간:
                c1 = 점([x for x in 칸 if a <= x["해"] <= b], 40)
                b1 = 점([x for x in 칸0 if a <= x["해"] <= b], 40)
                if c1 and b1:
                    방.append(c1[0] - b1[0])
            고름 = len(방) == 3 and all(v > 0 for v in 방)
            줄들.append((r[0] - 바[0], 이름, r, 고름, 방))
        줄들.sort(key=lambda z: -z[0])
        for 차, 이름, r, 고름, 방 in 줄들[:8]:
            쓸 = r[2] / 해수 >= 10
            오름 = 이름.startswith("**오름**") or 이름.startswith("**추세**")
            표 = ("  ⭐ **된다**" if (고름 and 차 >= 5 and 쓸) else
                  "  ~" if 차 >= 3 else "")
            if 오름 and 고름 and 차 >= 5 and 쓸:
                표 = "  ⭐⭐⭐ **모멘텀이 된다**"
                통한섹터.append((섹, 이름, 차))
            방말 = " ".join(f"{v:+.0f}" for v in 방)
            print(f"  {이름:<28}{r[2]:>9,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
                  f"{차:>+8.1f}p  [{방말}]{표}")

    print("\n" + "=" * 104)
    if 통한섹터:
        print(f"  ⇒ ⭐⭐⭐ **모멘텀이 통한 섹터 {len(통한섹터)}개**")
        for 섹, 이름, 차 in 통한섹터:
            print(f"       {섹:<24}{이름:<28}{차:+.1f}p")
        print("\n     ⚠️ 표본이 작다. **자본 시뮬과 무작위 대조**로 다시 걸러야 한다")
    else:
        print("  ⇒ ❌ **어느 섹터에서도 모멘텀이 안 된다**")
        print("     224차(전체) · 227차(규모별) 에 이어 **섹터별도 실패**다")
    print("=" * 104)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_229차_섹터별모멘텀.txt")

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
