#!/usr/bin/env python3
r"""
bigcap_lab.py — **226차 · 대형주 전용 문턱** (2026-09-10 신설)

## 사용자 물음
```
「지금 우리 대상이 **시총 300~2,000억 소형주**야? 그렇게 테스트하고 섹터별로
 했는데도 결국 소형주야? 섹터별로 하면 **SK하이닉스나 삼성전자가 나올 수도**
 있는 거 아니야?」
```

## ⚠️ 지금까지 대형주는 「표본 부족」으로 끝났다
```
220차 [크기 해제 — 시총 구간별]
  시총   100~300억      751건   **78.3%**  +18.77
  시총   300~500억    3,785건     67.4%    +9.56
  시총 500~2,000억   21,904건     60.1%    +4.89   <- 지금 대상
  시총  2,000억~1조    5,120건     55.1%    +2.69
  시총      1조 이상   **표본 부족**                <- 삼성전자·SK하이닉스
```

## ⚠️ 그런데 이건 **소형주 문턱을 그대로 들이댄** 결과다
```
지금 문턱: 20일 낙폭 **-10%** · 볼린저 **-1.0σ**
=> 대형주는 20일에 -10% 빠지는 일이 **드물다**. 그래서 표본이 없다
=> 대형주에겐 **-3%나 -5%가 소형주의 -10%만큼 큰 사건**일 수 있다
=> **규모마다 문턱을 달리** 해서 재야 한다. 한 번도 안 해봤다
```

## 재는 것
```
A ⭐⭐⭐ **규모 x 낙폭 문턱** 격자 — 구간마다 어디가 봉우리인가
B ⭐⭐⭐ **규모 x 볼린저 문턱** 격자
C ⭐⭐  규모마다 **몇 번 걸리나** (1년에 몇 건) — 쓸 수 있는 빈도인가
D ⭐⭐  대형주 **표준화 낙폭** — 그 종목의 평소 등락폭 대비 몇 배 빠졌나
E ⭐⭐⭐ 대형주 규칙을 기존과 **OR** — 기회가 늘고 승률이 지켜지나
```

## 판정 기준 (먼저 밝힌다)
```
① 바탕(같은 규모대 아무 날)보다 나아야 한다 — ⚠️ **규모대별 바탕**과 견준다
② **세 구간 다** 같은 방향 (2016~19 / 2020~22 / 2023~26)
③ 1년에 **10건 이상**은 걸려야 쓸 수 있다
⚠️ 소형주(60.1%)와 직접 견주지 않는다. 대형주는 원래 덜 오른다.
   물음은 「대형주가 소형주보다 나은가」가 아니라
   **「대형주 안에서 골라낼 수 있는가」**다
```

쓰는 법:
    python scripts\bigcap_lab.py
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

    print("  사건 만드는 중... ⚠️ **크기 제한 없이** 담는다", flush=True)
    사건 = []
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(60, len(vs)):
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
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            낙60 = (c1 / 종[k - 60] - 1) * 100 if 종[k - 60] > 0 else None
            # 그 종목의 **평소 등락폭** (60일 일간 표준편차) 대비 몇 배 빠졌나
            일간 = [(종[q] / 종[q - 1] - 1) * 100
                    for q in range(k - 59, k + 1) if 종[q - 1] > 0]
            평소 = (sum((z - sum(일간) / len(일간)) ** 2 for z in 일간)
                    / len(일간)) ** 0.5 if len(일간) > 30 else None
            표준낙 = (낙20 / (평소 * (20 ** 0.5))) if (평소 and 평소 > 0
                                                     and 낙20 is not None) else None
            사건.append({
                "해": 날[i][:4], "_20": 뒤, "시억": 시억,
                "볼20": 볼20, "낙20": 낙20, "낙60": 낙60, "표준낙": 표준낙,
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

    # 규모대마다 사건과 **그 규모대의 바탕**
    규모칸, 규모바탕 = {}, {}
    for 라, lo, hi in _규모:
        칸 = [x for x in 사건 if lo <= x["시억"] < hi]
        규모칸[라] = 칸
        규모바탕[라] = 점(칸)

    print("\n" + "=" * 104)
    print("  226차 · ⭐⭐⭐ **대형주 전용 문턱**")
    print("     ⚠️ 지금까지 대형주는 **소형주 문턱(-10%·-1.0σ)을 그대로** 들이대")
    print("        「표본 부족」으로 끝났다. 대형주는 그렇게 안 빠진다")
    print("     ⚠️ 물음은 「대형주가 소형주보다 나은가」가 아니라")
    print("        **「대형주 안에서 골라낼 수 있는가」** 다")
    print("=" * 104)

    print("\n  ── 규모대별 **바탕** (아무 날 아무 종목) ──")
    for 라, _, _2 in _규모:
        r = 규모바탕[라]
        if r:
            print(f"     {라:<20}{r[2]:>10,}건  1년 {r[2]/해수:>6,.0f}건  "
                  f"이김 **{r[0]:.1f}%**  평균 {r[1]:+.2f}%")
        else:
            print(f"     {라:<20}{'표본 부족':>10}")

    머 = (f"  {'문턱':<26}{'건수':>9}{'1년에':>7}{'이김':>8}"
          f"{'평균':>8}{'바탕대비':>9}  [구간별]")

    def 줄(라, 칸이름, fn):
        칸0 = 규모칸[칸이름]
        바 = 규모바탕[칸이름]
        칸 = [x for x in 칸0 if fn(x)]
        r = 점(칸)
        if not r or not 바:
            n = len([x for x in 칸 if x.get("_20") is not None])
            print(f"  {라:<26}{n:>9,}{n/해수:>7.0f}{'표본 부족':>17}")
            return None
        방 = []
        for _, a, b in 구간:
            c1 = 점([x for x in 칸 if a <= x["해"] <= b], 60)
            b1 = 점([x for x in 칸0 if a <= x["해"] <= b], 60)
            if c1 and b1:
                방.append(c1[0] - b1[0])
        고름 = len(방) == 3 and all(v > 0 for v in 방)
        차 = r[0] - 바[0]
        쓸 = r[2] / 해수 >= 10
        표 = ("  ⭐ **된다**" if (고름 and 차 >= 5 and 쓸)
              else "  ~" if 차 >= 3 else "")
        if not 쓸 and 차 >= 3:
            표 = "  (1년 10건 미만)"
        방말 = " ".join(f"{v:+.0f}" for v in 방)
        print(f"  {라:<26}{r[2]:>9,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
              f"{r[1]:>+8.2f}{차:>+8.1f}p  [{방말}]{표}")
        return r

    # ── A 규모 x 낙폭 문턱 ──
    print("\n  ── A ⭐⭐⭐ **규모 x 낙폭 문턱** ──")
    for 라, _, _2 in _규모:
        if not 규모바탕[라]:
            continue
        print(f"\n   [{라}]  바탕 {규모바탕[라][0]:.1f}%")
        print(머)
        for 문 in (-3, -5, -7, -10, -15, -20):
            줄(f"20일 낙폭 ≤{문}%", 라,
               lambda x, a=문: x["낙20"] is not None and x["낙20"] <= a)

    # ── B 규모 x 볼린저 ──
    print("\n  ── B ⭐⭐⭐ **규모 x 볼린저 문턱** ──")
    for 라, _, _2 in _규모:
        if not 규모바탕[라]:
            continue
        print(f"\n   [{라}]  바탕 {규모바탕[라][0]:.1f}%")
        print(머)
        for 문 in (-0.5, -1.0, -1.5, -2.0):
            줄(f"볼린저 ≤{문:+.1f}σ", 라,
               lambda x, a=문: x["볼20"] is not None and x["볼20"] <= a)

    # ── C 규모 x 둘 다 (지금 규칙 꼴) ──
    print("\n  ── C ⭐⭐ **규모마다 「볼린저 AND 낙폭」** — 지금 규칙 꼴 ──")
    for 라, _, _2 in _규모:
        if not 규모바탕[라]:
            continue
        print(f"\n   [{라}]  바탕 {규모바탕[라][0]:.1f}%")
        print(머)
        for 볼문, 낙문 in ((-1.0, -10), (-1.0, -5), (-1.0, -3),
                           (-1.5, -5), (-1.5, -3), (-0.5, -5), (-2.0, -3)):
            줄(f"볼{볼문:+.1f}σ · 낙{낙문}%", 라,
               lambda x, a=볼문, b=낙문: (x["볼20"] is not None and x["볼20"] <= a
                                          and x["낙20"] is not None
                                          and x["낙20"] <= b))

    # ── D 표준화 낙폭 ──
    print("\n  ── D ⭐⭐ **표준화 낙폭** — 그 종목 평소 등락폭 대비 몇 배 ──")
    print("     ⚠️ 규모마다 문턱을 따로 정할 필요가 없어진다 (자동으로 맞춰진다)")
    for 라, _, _2 in _규모:
        if not 규모바탕[라]:
            continue
        print(f"\n   [{라}]  바탕 {규모바탕[라][0]:.1f}%")
        print(머)
        for 문 in (-0.5, -1.0, -1.5, -2.0, -2.5):
            줄(f"평소 등락폭의 {문:+.1f}배↓", 라,
               lambda x, a=문: x["표준낙"] is not None and x["표준낙"] <= a)

    print("\n" + "=" * 104)
    print("  읽는 법")
    print("    - **바탕대비**는 「그 규모대 안에서」 얼마나 나은가다")
    print("    - 소형주 60.1% 와 직접 견주지 않는다 — 대형주는 원래 덜 오른다")
    print("    - **1년 10건 미만**이면 통과해도 못 쓴다 (기회가 없다)")
    print("    - D 가 되면 **규모별 문턱을 따로 안 정해도** 된다")
    print("=" * 104)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_226차_대형주문턱.txt")

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
