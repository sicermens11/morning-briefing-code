#!/usr/bin/env python3
r"""
value_lab.py — **225차 · 밸류에이션** (2026-09-10 신설)

## 사용자 물음
```
「보통 **컨센서스, 모멘텀, 밸류에이션, 펀더멘탈**을 본다고 하는데,
 이제야 모멘텀을 보는거네? **펀더멘탈도 보는 건가?**
 컨센서스랑 밸류에이션은 보고 있고!」
```

## ⚠️ 확인해 보니 **말씀과 실제가 달랐다**
```
펀더멘탈   ✅ 보고 있음 — 잉여금>=30% · 부채<=80% · 흑자 (후보 조건)
모멘텀     ⚠️ 224차가 처음
컨센서스   ⚠️ 자료는 있는데 **소형주라 못 씀**
           189차: 목표주가 올랐다 **51건** · 조금 올랐다 **115건** (표본 부족)
           209차: **컨센서스 0종목**
밸류에이션  ❌ **아예 안 봄** — PER·PBR·PSR 이 코드 어디에도 없다
           209·215차의 재료 22가지에도 없었다
```

## 자료는 있다 (dart-fin)
```
자산총계 · 자본총계 · 부채총계 · 매출액 · 영업이익 · 당기순이익
=> PBR = 시총/자본총계 · PER = 시총/순이익 · PSR = 시총/매출액
   그리고 **자산 대비**(시총/자산총계) 도 볼 수 있다
```

## 재는 것
```
A ⭐⭐⭐ **PBR** 구간별 (0.3배 ~ 5배)
B ⭐⭐⭐ **PER** 구간별 (적자 · 3배 ~ 50배)
C ⭐⭐  **PSR** 구간별
D ⭐⭐  밸류에이션 **x 낙폭** — 싼데 빠진 것이 더 좋은가
E ⭐⭐⭐ 기존 규칙과 **겹치는가 · OR 로 합치면**
```

## 판정 기준 (먼저 밝힌다)
```
① 바탕(아무 종목 아무 날)보다 나아야 한다
② **세 구간 다** 같은 방향 (2016~19 / 2020~22 / 2023~26)
③ 겹침이 낮아야 **새 기회**다
⚠️ Y년치 재무는 **Y+1년 4월 1일부터** 쓴다 (미리보기 금지)
```

쓰는 법:
    python scripts\value_lab.py
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20160101"


def 연간재무원본():
    r"""{코드: [(적용시작일, {항목: 값})]} — ⚠️ Y년치는 **Y+1년 4월 1일부터**."""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-fin", "*.json"))):
        y = os.path.basename(f)[:-5]
        if not y.isdigit():
            continue
        적용 = f"{int(y) + 1}0401"
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for code, v in d.items():
            def g(k):
                x = v.get(k)
                return float(x) if isinstance(x, (int, float)) else None
            out.setdefault(code, []).append((적용, {
                "자본": g("자본총계"), "자산": g("자산총계"),
                "매출": g("매출액"), "순익": g("당기순이익(손실)"),
                "영익": g("영업이익"),
            }))
    for c in out:
        out[c].sort()
    return out


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일", flush=True)
    재무 = 연간재무원본()
    print(f"  재무 {len(재무):,}종목", flush=True)

    종계, 있는날 = {}, {}
    자리 = {d: i for i, d in enumerate(날)}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(자리[d])

    def 재무값(code, d8):
        벌 = 재무.get(code)
        if not 벌:
            return None
        좋 = None
        for 적용, m in 벌:
            if 적용 <= d8:
                좋 = m
            else:
                break
        return 좋

    print("  사건 만드는 중...", flush=True)
    사건 = []
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(120, len(vs)):
            시원 = vs[k][1]
            시억 = 시원 / 1e8
            if not (300 <= 시억 < 2000) or vs[k][2] / 1e8 < 1.0:
                continue
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            fm = 재무값(c, 날[i])
            if not fm:
                continue
            c1 = 종[k]
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            자본, 매출, 순익, 자산 = (fm["자본"], fm["매출"], fm["순익"],
                                     fm["자산"])
            사건.append({
                "해": 날[i][:4], "_20": 뒤, "볼20": 볼20, "낙20": 낙20,
                "PBR": (시원 / 자본) if (자본 and 자본 > 0) else None,
                "PER": (시원 / 순익) if (순익 and 순익 > 0) else None,
                "적자": (순익 is not None and 순익 <= 0),
                "PSR": (시원 / 매출) if (매출 and 매출 > 0) else None,
                "자산대비": (시원 / 자산) if (자산 and 자산 > 0) else None,
            })
    print(f"  사건 **{len(사건):,}건**", flush=True)

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
    print(f"\n  ⭐ **바탕** (재무 있는 종목 아무 날) — 20일 이김 "
          f"**{바탕[0]:.1f}%** · 평균 {바탕[1]:+.2f}%")

    def 지금(x):
        return (x["볼20"] is not None and x["볼20"] <= -1.0
                and x["낙20"] is not None and x["낙20"] <= -10)

    머 = (f"  {'구간':<32}{'건수':>10}{'1년에':>7}{'이김':>8}"
          f"{'평균':>8}{'바탕대비':>9}  [구간별]")

    def 줄(라, fn):
        칸 = [x for x in 사건 if fn(x)]
        r = 점(칸)
        if not r:
            print(f"  {라:<32}{'표본 부족':>10}")
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
        print(f"  {라:<32}{r[2]:>10,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
              f"{r[1]:>+8.2f}{차:>+8.1f}p  [{방말}]{표}")
        return r

    print("\n" + "=" * 100)
    print("  225차 · ⭐⭐⭐ **밸류에이션** (PER·PBR·PSR)")
    print("     ⚠️ 209·215차의 재료 22가지에 **밸류에이션이 없었다**")
    print("        코드 어디에도 PER·PBR 이 없다 — 한 번도 안 재봤다")
    print("=" * 100)

    print("\n  ── A ⭐⭐⭐ **PBR** (시총 / 자본총계) ──")
    print(머)
    줄("[견줌] 지금 규칙", 지금)
    for a, b in ((0, 0.3), (0.3, 0.5), (0.5, 0.8), (0.8, 1.0), (1.0, 1.5),
                 (1.5, 2.0), (2.0, 3.0), (3.0, 5.0), (5.0, 9999)):
        줄(f"PBR {a} ~ {b}배",
           lambda x, p=a, q=b: (x["PBR"] is not None and p <= x["PBR"] < q))

    print("\n  ── B ⭐⭐⭐ **PER** (시총 / 당기순이익) ──")
    print(머)
    줄("**적자** 회사", lambda x: x["적자"])
    for a, b in ((0, 3), (3, 5), (5, 8), (8, 12), (12, 20), (20, 30),
                 (30, 50), (50, 99999)):
        줄(f"PER {a} ~ {b}배",
           lambda x, p=a, q=b: (x["PER"] is not None and p <= x["PER"] < q))

    print("\n  ── C ⭐⭐ **PSR** (시총 / 매출액) ──")
    print(머)
    for a, b in ((0, 0.3), (0.3, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 5.0),
                 (5.0, 99999)):
        줄(f"PSR {a} ~ {b}배",
           lambda x, p=a, q=b: (x["PSR"] is not None and p <= x["PSR"] < q))

    print("\n  ── D ⭐⭐ **싼데 빠진 것** (밸류 x 낙폭) ──")
    print("     ⚠️ 싼 것이 그냥 좋은 게 아니라 **싼데 빠진 것**이 좋은가")
    print(머)
    for 라, fn in (("PBR 0.8배↓", lambda x: x["PBR"] is not None and x["PBR"] < 0.8),
                   ("PBR 0.5배↓", lambda x: x["PBR"] is not None and x["PBR"] < 0.5),
                   ("PER 8배↓", lambda x: x["PER"] is not None and x["PER"] < 8),
                   ("PSR 0.5배↓", lambda x: x["PSR"] is not None and x["PSR"] < 0.5)):
        줄(f"{라} (그냥)", fn)
        줄(f"   └ **AND 지금 규칙**", lambda x, f=fn: f(x) and 지금(x))

    print("\n  ── E ⭐⭐⭐ **기존 규칙과 겹치는가 · OR** ──")
    print("     ⚠️ 겹침이 낮아야 **새 기회**다")
    print(머)
    for 라, fn in (("PBR 0.5배↓", lambda x: x["PBR"] is not None and x["PBR"] < 0.5),
                   ("PBR 0.8배↓", lambda x: x["PBR"] is not None and x["PBR"] < 0.8),
                   ("PER 8배↓", lambda x: x["PER"] is not None and x["PER"] < 8),
                   ("PER 5배↓", lambda x: x["PER"] is not None and x["PER"] < 5)):
        내 = len([x for x in 사건 if fn(x)])
        겹 = len([x for x in 사건 if fn(x) and 지금(x)])
        줄(f"{라} (겹침 {겹/max(1,내)*100:.0f}%)", fn)
        줄("   └ 기존 **OR** 이것", lambda x, f=fn: 지금(x) or f(x))

    print("\n" + "=" * 100)
    print("  읽는 법")
    print("    - **바탕대비**가 답이다 · **[구간별] 세 칸 다 +** 여야 믿는다")
    print("    - D 에서 「그냥」보다 「AND 지금 규칙」이 훨씬 좋으면")
    print("      밸류는 **혼자서는 못 쓰고 같이 써야** 한다는 뜻이다")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_225차_밸류에이션.txt")

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
