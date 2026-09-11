#!/usr/bin/env python3
r"""
size_rule_lab.py — **227차 · 규모마다 제 규칙을 찾는다** (2026-09-10 신설)

## 사용자 지적 (원문)
```
「"대형주에 맞는 「다른 문턱」은 한 번도 안 재봤습니다." 그래 그러니까
 내가 **규모별로도 적용할 수 있는 규칙이 있을지 테스트해보자고 했잖아!!!**」
「모멘텀 **또 기존 규칙에 얹혀서** 테스트 한거 아니야?」
```

## ⚠️ 지적이 맞다 — 224차(모멘텀)는 **소형주에서만** 쟀다
```
momentum_lab.py:  if not (300 <= 시억 < 2000): continue
=> 방향은 안 걸었지만 **크기를 걸었다**.
   「소형주가 오를 때」만 봤고 **「삼성전자가 오를 때」는 안 봤다**
```

## 이 시험이 다른 점
```
① **규모대마다 따로** 판을 깐다 (소형/중형/대형/초대형)
② 각 판에서 **재료를 전부** 훑는다 (낙폭·볼린저·모멘텀·밸류·거래량·표준화)
③ 견줌은 **그 규모대의 바탕** — 소형주 성적과 직접 대지 않는다
④ 기존 규칙에 **얹지 않는다.** 규모대마다 **혼자 서는 규칙**을 찾는다
```

## 판정 기준 (먼저 밝힌다)
```
① 그 규모대 **바탕보다 +5%p** 이상
② **세 구간 다** 같은 방향 (2016~19 / 2020~22 / 2023~26)
③ 1년에 **10건 이상** (못 쓰는 규칙은 소용없다)
⚠️ 규모대마다 **다른 규칙이 나와도 된다.** 그게 이 시험의 목적이다
```

쓰는 법:
    python scripts\size_rule_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20160101"

_규모 = (("소형 300~2,000억", 300, 2000),
         ("중형 2,000억~1조", 2000, 10000),
         ("대형 1조~10조", 10000, 100000),
         ("초대형 10조↑", 100000, 9e9))


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일", flush=True)

    종계, 있는날 = {}, {}
    자리 = {d: i for i, d in enumerate(날)}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(자리[d])

    print("  사건 만드는 중... ⚠️ **크기·방향 둘 다 안 건다**", flush=True)
    사건 = []
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        거 = [z[2] for z in vs]
        for k in range(120, len(vs)):
            시억 = vs[k][1] / 1e8
            if 시억 < 300 or vs[k][2] / 1e8 < 1.0:
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
            m60, sd60 = O.창평균표준(종, k, 60)
            볼60 = ((c1 - m60) / (2 * sd60)) if sd60 else None
            낙5 = (c1 / 종[k - 5] - 1) * 100 if 종[k - 5] > 0 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            낙60 = (c1 / 종[k - 60] - 1) * 100 if 종[k - 60] > 0 else None
            낙120 = (c1 / 종[k - 120] - 1) * 100 if 종[k - 120] > 0 else None
            일간 = [(종[q] / 종[q - 1] - 1) * 100
                    for q in range(k - 59, k + 1) if 종[q - 1] > 0]
            평 = sum(일간) / len(일간) if 일간 else 0
            평소 = ((sum((z - 평) ** 2 for z in 일간) / len(일간)) ** 0.5
                    if len(일간) > 30 else None)
            표준낙 = (낙20 / (평소 * (20 ** 0.5))) if (평소 and 평소 > 0
                                                     and 낙20 is not None) else None
            평거 = sum(거[k - 20:k]) / 20 if k >= 20 else None
            거배 = (거[k] / 평거) if (평거 and 평거 > 0) else None
            최고250 = max(종[max(0, k - 250):k + 1])
            고대비 = (c1 / 최고250 - 1) * 100 if 최고250 > 0 else None
            사건.append({
                "해": 날[i][:4], "_20": 뒤, "시억": 시억,
                "볼20": 볼20, "볼60": 볼60, "낙5": 낙5, "낙20": 낙20,
                "낙60": 낙60, "낙120": 낙120, "표준낙": 표준낙,
                "거배": 거배, "고대비": 고대비, "평소": 평소,
            })
    print(f"  사건 **{len(사건):,}건**", flush=True)

    해수 = len(날) / 245
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"))

    def 점(칸, 최소=150):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(v))

    # ── 재료 모음 — **내림 쪽과 오름 쪽을 다 넣는다** ──
    재료 = []
    for w in (20, 60, 120):
        for 문 in (-30, -20, -10, -5):
            재료.append((f"낙{w}일 ≤{문}%",
                         lambda x, a=w, b=문: (x[f"낙{a}"] is not None
                                               and x[f"낙{a}"] <= b)))
        for 문 in (5, 10, 20, 30):
            재료.append((f"낙{w}일 ≥+{문}% (오름)",
                         lambda x, a=w, b=문: (x[f"낙{a}"] is not None
                                               and x[f"낙{a}"] >= b)))
    for 문 in (-2.0, -1.5, -1.0, -0.5):
        재료.append((f"볼20 ≤{문:+.1f}σ",
                     lambda x, a=문: x["볼20"] is not None and x["볼20"] <= a))
    for 문 in (0.5, 1.0, 1.5):
        재료.append((f"볼20 ≥{문:+.1f}σ (오름)",
                     lambda x, a=문: x["볼20"] is not None and x["볼20"] >= a))
    for 문 in (-2.0, -1.5, -1.0):
        재료.append((f"볼60 ≤{문:+.1f}σ",
                     lambda x, a=문: x["볼60"] is not None and x["볼60"] <= a))
    for 문 in (-2.5, -2.0, -1.5, -1.0, -0.5):
        재료.append((f"평소 등락폭의 {문:+.1f}배↓",
                     lambda x, a=문: (x["표준낙"] is not None
                                      and x["표준낙"] <= a)))
    for 문 in (2, 3, 5):
        재료.append((f"거래량 {문}배↑",
                     lambda x, a=문: x["거배"] is not None and x["거배"] >= a))
    for a, b in ((-3, 0), (-10, -3), (-40, -20), (-99, -40)):
        재료.append((f"250일 최고 대비 {a}~{b}%",
                     lambda x, p=a, q=b: (x["고대비"] is not None
                                          and p <= x["고대비"] < q)))
    재료.append(("5일 ≤-5% (짧게 눌림)",
                 lambda x: x["낙5"] is not None and x["낙5"] <= -5))
    재료.append(("5일 ≥+5% (짧게 튐)",
                 lambda x: x["낙5"] is not None and x["낙5"] >= 5))

    print("\n" + "=" * 108)
    print("  227차 · ⭐⭐⭐ **규모마다 제 규칙을 찾는다**")
    print("     사용자: 「**규모별로도 적용할 수 있는 규칙이 있을지**"
          " 테스트해보자고 했잖아!!!」")
    print("     ⚠️ 224차(모멘텀)는 **소형주에서만** 쟀다 — 크기를 걸어 놨었다")
    print("     ⚠️ 여기서는 **규모대마다 따로 판을 깔고** 재료를 전부 훑는다")
    print("     ⚠️ 견줌은 **그 규모대의 바탕**이다. 소형주 성적과 직접 대지 않는다")
    print("=" * 108)

    for 라, lo, hi in _규모:
        칸0 = [x for x in 사건 if lo <= x["시억"] < hi]
        바 = 점(칸0)
        print(f"\n{'=' * 108}")
        if not 바:
            print(f"  [{라}]  **표본 부족** ({len(칸0):,}건)")
            continue
        print(f"  [{라}]  {len(칸0):,}건 · 1년 {len(칸0)/해수:,.0f}건"
              f" · **바탕 이김 {바[0]:.1f}%** · 평균 {바[1]:+.2f}%")
        print("=" * 108)
        줄들 = []
        for 이름, fn in 재료:
            칸 = [x for x in 칸0 if fn(x)]
            r = 점(칸)
            if not r:
                continue
            방 = []
            for _, a, b in 구간:
                c1 = 점([x for x in 칸 if a <= x["해"] <= b], 50)
                b1 = 점([x for x in 칸0 if a <= x["해"] <= b], 50)
                if c1 and b1:
                    방.append(c1[0] - b1[0])
            고름 = len(방) == 3 and all(v > 0 for v in 방)
            차 = r[0] - 바[0]
            해건 = r[2] / 해수
            줄들.append((차, 이름, r, 고름, 방, 해건))
        줄들.sort(key=lambda z: -z[0])
        print(f"  {'재료':<26}{'건수':>9}{'1년에':>7}{'이김':>8}"
              f"{'평균':>8}{'바탕대비':>9}  [구간별]")
        보임 = 0
        for 차, 이름, r, 고름, 방, 해건 in 줄들:
            if 차 < 2 and 보임 >= 12:
                continue
            보임 += 1
            if 보임 > 18:
                break
            쓸 = 해건 >= 10
            표 = ("  ⭐ **된다**" if (고름 and 차 >= 5 and 쓸)
                  else "  (1년 10건 미만)" if (고름 and 차 >= 5)
                  else "  ~" if 차 >= 3 else "")
            방말 = " ".join(f"{v:+.0f}" for v in 방)
            print(f"  {이름:<26}{r[2]:>9,}{해건:>7.0f}{r[0]:>7.1f}%"
                  f"{r[1]:>+8.2f}{차:>+8.1f}p  [{방말}]{표}")
        된것 = [z for z in 줄들 if z[3] and z[0] >= 5 and z[5] >= 10]
        if 된것:
            print(f"\n     ⇒ ⭐ **이 규모대에서 되는 재료 {len(된것)}개**: "
                  + " · ".join(z[1] for z in 된것[:5]))
        else:
            print("\n     ⇒ ❌ **되는 재료가 없다** (바탕 +5%p · 세 구간 · 1년 10건)")

    print("\n" + "=" * 108)
    print("  읽는 법")
    print("    - **규모대마다 다른 재료가 나와도 된다.** 그게 이 시험의 목적이다")
    print("    - 오름 쪽 재료(「(오름)」 표시)가 어느 규모대에서 되는지 본다")
    print("      -> 되면 **그 규모대에서는 모멘텀이 통한다**는 뜻이다")
    print("    - 「평소 등락폭의 N배↓」가 여러 규모대에서 되면")
    print("      **규모별 문턱을 따로 안 정해도** 된다")
    print("=" * 108)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_227차_규모별제규칙.txt")

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
