#!/usr/bin/env python3
r"""
exclude_lab.py — **228차 · 「빼기」가 규칙이 될 수 있나** (2026-09-10 신설)

## 사용자 물음 (원문)
```
「만약에 PER를 넣었을 때 승율이 안 좋고 빼면 승율이 좋아진다면
 **이대로 규칙에 반영하냐**는 말이야!
 **뺀다고 승율이 높아진다면 빼는 것을 규칙에 반영하는게 맞냐**는 뜻이야!」
```

## ⚠️ 「나쁜 걸 빼면 남은 게 좋아진다」는 **거의 항상 참이다**
```
그건 **산수**이지 발견이 아니다. 그래서 세 가지를 봐야 한다

① **무작위 대조**  아무거나 같은 개수를 빼도 승률이 오른다. 그보다 나은가
② **기회**        빼면 후보가 준다. 하루 4개 사는데 살 게 없으면 소용없다
③ **자본 시뮬**    승률이 아니라 **돈**이 느는가
```

## 전례
```
✅ 220차 ⑥ 「S&P500이 오른 뒤엔 안 산다」(빼기)  -> **4관문 통과**
❌ 214차 D절 AND 둘 겹치기(빼기의 일종)         -> **열 쌍 전부 실패**
=> 빼기도 규칙이 될 수 있지만 **「빼면 승률 오름」만으로는 근거가 안 된다**
```

## 재는 것
```
A ⭐⭐⭐ **빼기 하나씩** — 승률·기회·무작위 대조를 **같이**
B ⭐⭐⭐ **무작위 대조** — 같은 개수를 아무렇게나 빼기 200번
C ⭐⭐  **빼기 여러 개** 겹치기
D ⭐⭐  밸류에이션을 **규모별로** (225차가 소형주만 쟀던 것 보완)
```

## 판정 기준 (먼저 밝힌다)
```
① 승률이 **+2%p 이상** 오르고
② 기회가 **70% 이상** 남고
③ **무작위로 같은 수를 뺀 200번 중 상위 5%** 안에 들어야 한다
   (③ 이 없으면 우연히 나쁜 게 빠진 것과 구별이 안 된다)
```

쓰는 법:
    python scripts\exclude_lab.py
"""
import glob
import io
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20160101"
_규모 = (("소형 300~2,000억", 300, 2000),
         ("중형 2,000억~1조", 2000, 10000),
         ("대형 1조↑", 10000, 9e9))


def 연간재무원본():
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
                "자본": g("자본총계"), "매출": g("매출액"),
                "순익": g("당기순이익(손실)"), "부채": g("부채총계"),
            }))
    for c in out:
        out[c].sort()
    return out


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    재무 = 연간재무원본()
    print(f"  거래일 {len(날):,}일 · 재무 {len(재무):,}종목", flush=True)

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

    print("  사건 만드는 중... (지금 규칙에 걸리는 것 = **빼기의 대상**)",
          flush=True)
    사건 = []
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(120, len(vs)):
            시원 = vs[k][1]
            시억 = 시원 / 1e8
            if 시억 < 300 or vs[k][2] / 1e8 < 1.0:
                continue
            c1 = 종[k]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            # ⚠️ **지금 규칙에 걸린 것만** 담는다 — 여기서 무엇을 뺄지 본다
            if not (볼20 is not None and 볼20 <= -1.0
                    and 낙20 is not None and 낙20 <= -10):
                continue
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            fm = 재무값(c, 날[i]) or {}
            자본, 매출, 순익, 부채 = (fm.get("자본"), fm.get("매출"),
                                     fm.get("순익"), fm.get("부채"))
            사건.append({
                "해": 날[i][:4], "_20": 뒤, "시억": 시억,
                "PBR": (시원 / 자본) if (자본 and 자본 > 0) else None,
                "PER": (시원 / 순익) if (순익 and 순익 > 0) else None,
                "PSR": (시원 / 매출) if (매출 and 매출 > 0) else None,
                "적자": (순익 is not None and 순익 <= 0),
                "부채비": (부채 / 자본 * 100) if (자본 and 자본 > 0
                                                and 부채 is not None) else None,
            })
    print(f"  사건 **{len(사건):,}건** (지금 규칙 통과분)", flush=True)

    해수 = len(날) / 245
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"))

    def 점(칸, 최소=150):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(v))

    기 = 점(사건)
    print(f"\n  ⭐ **빼기 전** — {기[2]:,}건 · 1년 {기[2]/해수:,.0f}건"
          f" · 이김 **{기[0]:.1f}%** · 평균 {기[1]:+.2f}%")

    빼기들 = [
        ("PER 50배↑ 를 뺀다", lambda x: x["PER"] is not None and x["PER"] >= 50),
        ("PER 30배↑ 를 뺀다", lambda x: x["PER"] is not None and x["PER"] >= 30),
        ("PER 20배↑ 를 뺀다", lambda x: x["PER"] is not None and x["PER"] >= 20),
        ("PBR 3배↑ 를 뺀다", lambda x: x["PBR"] is not None and x["PBR"] >= 3),
        ("PBR 2배↑ 를 뺀다", lambda x: x["PBR"] is not None and x["PBR"] >= 2),
        ("PBR 1.5배↑ 를 뺀다", lambda x: x["PBR"] is not None and x["PBR"] >= 1.5),
        ("PSR 3배↑ 를 뺀다", lambda x: x["PSR"] is not None and x["PSR"] >= 3),
        ("**적자**를 뺀다", lambda x: x["적자"]),
        ("부채비율 150%↑ 를 뺀다",
         lambda x: x["부채비"] is not None and x["부채비"] >= 150),
        ("PER 자료 **없는 것**을 뺀다", lambda x: x["PER"] is None),
        ("PBR 자료 **없는 것**을 뺀다", lambda x: x["PBR"] is None),
    ]

    print("\n" + "=" * 108)
    print("  228차 · ⭐⭐⭐ **「빼기」가 규칙이 될 수 있나**")
    print("     사용자: 「**뺀다고 승율이 높아진다면 빼는 것을 규칙에 반영하는게"
          " 맞냐**는 뜻이야!」")
    print("     ⚠️ 「나쁜 걸 빼면 남은 게 좋아진다」는 **거의 항상 참**이다 —"
          " 산수이지 발견이 아니다")
    print("     ⚠️ 판정: 승률 +2%p · 기회 70%↑ · **무작위 200번 중 상위 5%**")
    print("=" * 108)

    print(f"\n  {'빼기':<28}{'뺀 수':>9}{'남은 수':>9}{'기회':>7}"
          f"{'남은 이김':>10}{'차이':>8}{'무작위 대조':>26}")
    쓸만 = []
    for 라, fn in 빼기들:
        뺀 = [x for x in 사건 if fn(x)]
        남 = [x for x in 사건 if not fn(x)]
        r남 = 점(남)
        if not r남 or not 뺀:
            print(f"  {라:<28}{len(뺀):>9,}{'표본 부족':>19}")
            continue
        차 = r남[0] - 기[0]
        기회 = r남[2] / 기[2] * 100
        # ── ⭐ 무작위 대조: **같은 개수**를 아무렇게나 빼기 200번 ──
        rr = random.Random(20260910)
        n뺄 = len(뺀)
        무 = []
        for _ in range(200):
            뽑 = set(rr.sample(range(len(사건)), min(n뺄, len(사건) - 200)))
            v = [사건[q]["_20"] for q in range(len(사건))
                 if q not in 뽑 and 사건[q].get("_20") is not None]
            if len(v) >= 150:
                무.append(sum(1 for z in v if z > 0) / len(v) * 100)
        무.sort()
        상위 = (sum(1 for v in 무 if v < r남[0]) / len(무) * 100) if 무 else 0
        낫나 = 상위 >= 95
        표 = (f"중앙 {무[len(무)//2]:.1f}% → **상위 {100-상위:.0f}%**"
              if 무 else "—")
        되나 = (차 >= 2 and 기회 >= 70 and 낫나)
        if 되나:
            표 += "  ⭐ **된다**"
            쓸만.append((라, 차, 기회))
        elif 차 >= 2 and 기회 >= 70:
            표 += "  ❌ 우연"
        print(f"  {라:<28}{len(뺀):>9,}{r남[2]:>9,}{기회:>6.0f}%"
              f"{r남[0]:>9.1f}%{차:>+7.1f}p{표:>26}")

    # ── 구간별 ──
    print("\n  ── 위에서 **차이 +2%p 이상**인 것만 구간별로 ──")
    print(f"  {'빼기':<28}{'2016~19':>10}{'2020~22':>10}{'2023~26':>10}")
    for 라, fn in 빼기들:
        남 = [x for x in 사건 if not fn(x)]
        r남 = 점(남)
        if not r남 or r남[0] - 기[0] < 2:
            continue
        칸 = []
        for _, a, b in 구간:
            c1 = 점([x for x in 남 if a <= x["해"] <= b], 60)
            b1 = 점([x for x in 사건 if a <= x["해"] <= b], 60)
            칸.append(f"{c1[0]-b1[0]:+.1f}p" if (c1 and b1) else "—")
        print(f"  {라:<28}" + "".join(f"{z:>10}" for z in 칸))

    # ── D 밸류에이션을 규모별로 ──
    print("\n  ── D ⭐⭐ **밸류에이션을 규모별로** (225차는 소형주만 쟀다) ──")
    for 라, lo, hi in _규모:
        칸0 = [x for x in 사건 if lo <= x["시억"] < hi]
        바 = 점(칸0)
        if not 바:
            print(f"\n   [{라}]  표본 부족 ({len(칸0):,}건)")
            continue
        print(f"\n   [{라}]  {len(칸0):,}건 · 지금 규칙 이김 {바[0]:.1f}%")
        print(f"  {'재료':<28}{'건수':>9}{'1년에':>7}{'이김':>8}{'차이':>8}")
        for 이름, fn in (("PBR 0.5배↓", lambda x: x["PBR"] is not None and x["PBR"] < 0.5),
                         ("PBR 0.8배↓", lambda x: x["PBR"] is not None and x["PBR"] < 0.8),
                         ("PER 8배↓", lambda x: x["PER"] is not None and x["PER"] < 8),
                         ("PSR 0.5배↓", lambda x: x["PSR"] is not None and x["PSR"] < 0.5)):
            칸 = [x for x in 칸0 if fn(x)]
            r = 점(칸, 80)
            if not r:
                print(f"  {이름:<28}{len(칸):>9,}{'표본 부족':>15}")
                continue
            print(f"  {이름:<28}{r[2]:>9,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
                  f"{r[0]-바[0]:>+7.1f}p")

    print("\n" + "=" * 108)
    if 쓸만:
        print(f"  ⇒ ⭐ **무작위 대조까지 이긴 빼기 {len(쓸만)}개**")
        for 라, 차, 기회 in 쓸만:
            print(f"       {라:<30}{차:+.1f}%p · 기회 {기회:.0f}%")
        print("\n     ⚠️ 아직 **자본 시뮬**이 남았다. 승률이 아니라 **돈**으로 확인해야 한다")
    else:
        print("  ⇒ ❌ **무작위 대조를 이긴 빼기가 없다**")
        print("     = 「빼면 승률 오름」이 **우연히 나쁜 게 빠진 것**과 구별이 안 된다")
        print("     => 사용자 물음에 대한 답: **이대로 반영하면 안 된다**")
    print("=" * 108)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_228차_빼기가규칙이되나.txt")

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
