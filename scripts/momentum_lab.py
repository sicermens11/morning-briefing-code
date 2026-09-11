#!/usr/bin/env python3
r"""
momentum_lab.py — **224차 · 오르는 걸 사면?** (2026-09-10 신설)

## 사용자 물음
```
「동부건설 오늘 성적 좋은데, 이건 왜 퀀트 후보에서는 못 나오는 걸까?」
「퀀트 규칙은 **「빠진 걸 산다」에 매몰**되지 않았나 물어보려고 했는데」
```

## ⚠️⚠️ 지금까지 220번 넘는 시험이 **오르는 종목을 데이터에서부터 뺐다**
```
gate7 의 사건 만들기:
    if not (볼20 <= -0.5  or  낙20 <= -5  or  낙60 <= -15):
        continue          # <- **오르는 종목은 사건에 아예 안 들어옴**

=> 「모멘텀이 나쁘다」는 결과가 나온 적이 **없다**.
   잴 **기회조차 없었다.** 그래서 새 파일로 만든다
```

## 동부건설이 안 나온 이유 (실측)
```
볼린저 **+0.46σ** · 20일 낙폭 **+8.44%** · 60일 낙폭 **+19.71%**
=> 두 달간 20% 오르는 중이었다. 「빠진 걸 산다」 규칙에 걸릴 수가 없다
```

## 재는 것 — **양쪽을 다 본다**
```
A ⭐⭐⭐ **오른 만큼**으로 나눠 본다 (-30% ~ +50%) — 어디가 제일 좋은가
B ⭐⭐⭐ **볼린저 전 구간** (-2σ ~ +2σ) — 아래만 좋은 게 맞나
C ⭐⭐  **신고가 근처** (250일 최고 대비)
D ⭐⭐  **조정 후 재상승** — 오르는 중(60일 +20%) 짧게 눌림(5일 -3%)
E ⭐⭐  **거래량 터지며** 오른 것
F ⭐⭐⭐ **기존 규칙과 OR** — 합치면 기회가 느는가
```

## 판정 기준 (먼저 밝힌다)
```
① 바탕(아무 종목 아무 날)보다 나아야 한다
② **세 구간 다** 같은 방향 (2016~19 / 2020~22 / 2023~26)
③ 기존 규칙과 **겹치지 않아야** 값어치가 있다 (겹치면 새 기회가 아니다)
```

쓰는 법:
    python scripts\momentum_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20160101"


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일", flush=True)
    _사라짐 = O.사라진종목(주가, 날)
    print(f"  사라진 종목 {len(_사라짐):,}개 — 폐지는 {O.폐지손실:.0f}% 손실",
          flush=True)

    종계, 거량 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v)

    print("  사건 만드는 중... ⚠️ **좁히지 않는다** (오르는 것도 다 담는다)",
          flush=True)
    사건 = []
    자리 = {d: i for i, d in enumerate(날)}
    있는날 = {}
    for d in 날:
        for c in 주가[d]:
            있는날.setdefault(c, []).append(자리[d])

    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        거 = [z[2] for z in vs]
        for k in range(250, len(vs)):
            시억 = vs[k][1] / 1e8
            대억 = vs[k][2] / 1e8
            # ⚠️ 크기·거래대금만 건다. **방향은 안 건다**
            if not (300 <= 시억 < 2000) or 대억 < 1.0:
                continue
            c1 = 종[k]
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            m60, sd60 = O.창평균표준(종, k, 60)
            볼60 = ((c1 - m60) / (2 * sd60)) if sd60 else None
            낙5 = (c1 / 종[k - 5] - 1) * 100 if 종[k - 5] > 0 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            낙60 = (c1 / 종[k - 60] - 1) * 100 if 종[k - 60] > 0 else None
            최고250 = max(종[k - 250:k + 1])
            고대비 = (c1 / 최고250 - 1) * 100 if 최고250 > 0 else None
            평거 = sum(거[k - 20:k]) / 20 if k >= 20 else None
            거배 = (거[k] / 평거) if (평거 and 평거 > 0) else None
            사건.append({
                "해": 날[i][:4], "_20": 뒤,
                "볼20": 볼20, "볼60": 볼60,
                "낙5": 낙5, "낙20": 낙20, "낙60": 낙60,
                "고대비": 고대비, "거배": 거배,
            })
    print(f"  사건 **{len(사건):,}건** (좁히기 없음)", flush=True)

    해수 = len(날) / 245
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"))

    def 점(칸):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 200:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(v))

    바탕 = 점(사건)
    print(f"\n  ⭐ **바탕** (아무 종목 아무 날) — 20일 이김 "
          f"**{바탕[0]:.1f}%** · 평균 {바탕[1]:+.2f}%")

    # 지금 규칙(기술 부분만) — 견줌
    def 지금(x):
        return (x["볼20"] is not None and x["볼20"] <= -1.0
                and x["낙20"] is not None and x["낙20"] <= -10)

    기 = 점([x for x in 사건 if 지금(x)])

    머 = (f"  {'구간':<34}{'건수':>10}{'1년에':>7}{'이김':>8}"
          f"{'평균':>8}{'바탕대비':>9}  [구간별]")

    def 줄(라, fn, 견=None):
        칸 = [x for x in 사건 if fn(x)]
        r = 점(칸)
        if not r:
            print(f"  {라:<34}{'표본 부족':>10}")
            return None
        방 = []
        for _, a, b in 구간:
            c1 = 점([x for x in 칸 if a <= x["해"] <= b])
            b1 = 점([x for x in 사건 if a <= x["해"] <= b])
            if c1 and b1:
                방.append(c1[0] - b1[0])
        고름 = len(방) == 3 and all(v > 0 for v in 방)
        차 = r[0] - 바탕[0]
        표 = "  ⭐ **된다**" if (고름 and 차 >= 5) else ("  ~" if 차 >= 3 else "")
        방말 = " ".join(f"{v:+.0f}" for v in 방)
        print(f"  {라:<34}{r[2]:>10,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
              f"{r[1]:>+8.2f}{차:>+8.1f}p  [{방말}]{표}")
        return r

    print("\n" + "=" * 104)
    print("  224차 · ⭐⭐⭐ **오르는 걸 사면?**")
    print("     ⚠️ 지금까지 220번 넘는 시험이 **오르는 종목을 데이터에서부터 뺐다**")
    print("        「모멘텀이 나쁘다」는 결과가 나온 적이 **없다** — 잴 기회가 없었다")
    print("=" * 104)
    print("\n  ── A ⭐⭐⭐ **20일 오른 만큼**으로 나눠 본다 ──")
    print(머)
    줄("[견줌] 지금 규칙 (볼-1σ·낙-10%)", 지금)
    칸들 = ((-99, -30), (-30, -20), (-20, -10), (-10, -5), (-5, 0),
            (0, 5), (5, 10), (10, 20), (20, 30), (30, 50), (50, 999))
    for a, b in 칸들:
        줄(f"20일 {a:+.0f}% ~ {b:+.0f}%",
           lambda x, p=a, q=b: (x["낙20"] is not None and p <= x["낙20"] < q))

    print("\n  ── A-2 ⭐⭐ **60일 오른 만큼** ──")
    print(머)
    for a, b in 칸들:
        줄(f"60일 {a:+.0f}% ~ {b:+.0f}%",
           lambda x, p=a, q=b: (x["낙60"] is not None and p <= x["낙60"] < q))

    print("\n  ── B ⭐⭐⭐ **볼린저 전 구간** — 아래만 좋은 게 맞나 ──")
    print(머)
    볼칸 = ((-99, -2.0), (-2.0, -1.5), (-1.5, -1.0), (-1.0, -0.5),
            (-0.5, 0), (0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0),
            (2.0, 99))
    for a, b in 볼칸:
        줄(f"볼20 {a:+.1f}σ ~ {b:+.1f}σ",
           lambda x, p=a, q=b: (x["볼20"] is not None and p <= x["볼20"] < q))

    print("\n  ── C ⭐⭐ **신고가 근처** (250일 최고 대비) ──")
    print(머)
    for a, b in ((-3, 0), (-10, -3), (-20, -10), (-40, -20), (-99, -40)):
        줄(f"250일 최고 대비 {a}% ~ {b}%",
           lambda x, p=a, q=b: (x["고대비"] is not None and p <= x["고대비"] < q))

    print("\n  ── D ⭐⭐ **조정 후 재상승** (오르는 중 짧게 눌림) ──")
    print(머)
    for n60 in (10, 20, 30):
        for n5 in (-3, -5, -8):
            줄(f"60일 +{n60}%↑ **이면서** 5일 {n5}%↓",
               lambda x, a=n60, b=n5: (x["낙60"] is not None and x["낙60"] >= a
                                       and x["낙5"] is not None and x["낙5"] <= b))

    print("\n  ── E ⭐⭐ **거래량 터지며 오른 것** ──")
    print(머)
    for 배 in (2, 3, 5):
        for n20 in (5, 10, 20):
            줄(f"거래량 {배}배↑ **이면서** 20일 +{n20}%↑",
               lambda x, a=배, b=n20: (x["거배"] is not None and x["거배"] >= a
                                       and x["낙20"] is not None
                                       and x["낙20"] >= b))

    print("\n  ── F ⭐⭐⭐ **기존 규칙과 겹치는가** ──")
    print("     ⚠️ 겹치면 새 기회가 아니다. **안 겹쳐야** 값어치가 있다")
    print(머)
    후보들 = [
        ("오름: 20일 +10~30%",
         lambda x: x["낙20"] is not None and 10 <= x["낙20"] < 30),
        ("오름: 볼20 +1.0~2.0σ",
         lambda x: x["볼20"] is not None and 1.0 <= x["볼20"] < 2.0),
        ("오름: 신고가 -3% 이내",
         lambda x: x["고대비"] is not None and x["고대비"] >= -3),
        ("조정후: 60일+20% & 5일-5%",
         lambda x: (x["낙60"] is not None and x["낙60"] >= 20
                    and x["낙5"] is not None and x["낙5"] <= -5)),
    ]
    for 라, fn in 후보들:
        겹 = len([x for x in 사건 if fn(x) and 지금(x)])
        내 = len([x for x in 사건 if fn(x)])
        줄(라 + f" (겹침 {겹/max(1,내)*100:.0f}%)", fn)
        줄("   └ 기존 **OR** 이것", lambda x, f=fn: 지금(x) or f(x))

    print("\n" + "=" * 104)
    print("  읽는 법")
    print("    - **바탕대비**가 답이다. 바탕은 아무 종목 아무 날의 20일 이김률")
    print("    - **[구간별] 세 칸이 다 +** 여야 믿을 수 있다")
    print("    - 겹침이 낮은데 좋으면 **새 기회**다 — 기존 규칙이 못 잡던 것")
    print("=" * 104)
    if 기:
        print(f"\n  [견줌] 지금 규칙 {기[0]:.1f}% · 바탕 {바탕[0]:.1f}%")
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_224차_오르는걸사면.txt")

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
