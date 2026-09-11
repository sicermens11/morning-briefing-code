#!/usr/bin/env python3
r"""
stock_score_lab.py — **238차 · 「종목 성적」 잣대로 다시** (2026-09-10 신설)

## ⚠️ 사용자 지적으로 **판정 잣대를 바꾼다**
```
「자본 시뮬에서 기각됐다고 했는데, **내 자본을 상정해서** 시뮬레이션 돌린거 아니야?
 내가 아까 **내 자산에 맞춰 매수할테니까 매수 기회 포착만** 해달라고 했는데,
 자본 시뮬에서 기각됐다는 건 **나한테 의미 없는 거** 아니야?」
```

### 자본 시뮬이 가정했던 것 — **사용자와 무관한 부분**
```
❌ 시드 500만원          자기 자산에서 알아서 산다
❌ 비중 20% x 4종목      몇 개 살지 직접 정한다
❌ 거래대금 1% 한도       50~100만원이면 안 걸린다
❌ 「현금이 없어 못 샀다」  사용자 판단이다
❌ 끝 자산 금액          8,369만원 같은 숫자
```

### 그래서 **「하루 3종목 기각」은 철회**했다
```
순전히 자본 배분 문제였다. 사용자 방식에서는 판정 대상이 아니다
```

## 새 잣대 — **종목 성적**
```
① **이기는 비율**   20일 뒤 오른 비율
② **평균 수익**
③ **최악 5%**      하위 5% 평균 — 크게 물릴 위험
④ ⭐ **며칠 만에 +15% / +40% 에 닿나**
     사용자가 **직접 팔 수 있으므로** 「목표 도달까지 걸리는 날」이 핵심이다.
     자본 시뮬은 이걸 「자금이 묶인다」로만 봤는데, 사용자는 충분히 올랐다 싶으면
     직접 판다
⑤ ⭐ **기회**      1년에 몇 번 걸리나
     ⚠️ 승률만 보면 「적게 사서 승률 오른 것」을 통과시킨다.
        사용자 원문: 「매도 타이밍도 중요하지만 **그것 때문에 상승 기회를
        놓쳐서는 안돼**」
⑥ **세 구간** 다 같은 방향 (2016~19 / 2020~22 / 2023~26)
```

## 다시 재는 것 (자본 시뮬로 기각·보류됐던 것)
```
A ⭐⭐⭐ **대형주 / 시총 상한**   승률 64.5% 로 최고였는데 자본 시뮬로 기각됐다
B ⭐⭐⭐ **볼60 대체**          세 규모대 전부 볼20보다 나았는데 자본 시뮬로 기각
C ⭐⭐  **표준화 낙폭**         네 규모대 전부 ⭐ · 자본 시뮬을 **안 했다**
D ⭐⭐  **PBR 0.5배↓ AND**    승률 56%->63% · 자본 시뮬을 **안 했다**
E ⭐⭐⭐ **대형주 단타**         사용자 물음: 「대형주는 단타 매도를 기준으로?」
```

## ⚠️ 이 시험이 보는 범위
```
크기   시총 300억 이상 — **상한 없음**      방향   안 걸었다
기간   2016-01-01 ~                     견줌   그 칸의 바탕
비용   왕복 0.26% 를 **뺀다** (단타는 비용에 민감하다)
```

쓰는 법:
    python scripts\stock_score_lab.py
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import lab_header as LH  # noqa: E402

_시작 = "20160101"
_비용 = 0.26
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
            out.setdefault(code, []).append((적용, {"자본": g("자본총계")}))
    for c in out:
        out[c].sort()
    return out


def main():
    LH.찍기(
        차수="238차", 이름="「종목 성적」 잣대로 다시",
        크기="시총 300억 이상 — **상한 없음**", 방향="안 걸었다",
        기간="2016-01-01 ~",
        재료=["주가·시총·거래대금", "지수 71개", "연간 재무"],
        안본것=["수급", "공시", "뉴스", "분기 재무"],
        견줌="그 칸의 바탕",
        판정="이김·평균·최악5%·**목표 도달일**·기회·세 구간",
    )

    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    재무 = 연간재무원본()
    print(f"  거래일 {len(날):,}일 · 재무 {len(재무):,}종목", flush=True)

    # 지수 (때 조건)
    지수 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        하루 = {}
        for 이름2 in ("코스피", "코스닥"):
            v2 = (d2.get("지수") or {}).get(이름2) or {}
            try:
                하루[이름2] = float(str(v2.get("종가")).replace(",", ""))
            except (TypeError, ValueError, AttributeError):
                pass
        if 하루:
            지수[d2.get("기준일") or os.path.basename(f)[:8]] = 하루
    계열 = {n: [(지수.get(d) or {}).get(n) for d in 날]
            for n in ("코스피", "코스닥")}

    def 지낙(n, i, w):
        sq = 계열[n]
        if i < w or i >= len(sq):
            return None
        a, b = sq[i - w], sq[i]
        return ((b / a - 1) * 100) if (a and b) else None

    시장표 = {}
    _sb = json.load(io.open(os.path.join(O._DATA, "stock-base.json"),
                            encoding="utf-8-sig")).get("종목") or {}
    for c2, v2 in _sb.items():
        시장표[c2] = "코스닥" if "KOSDAQ" in str(v2.get("시장") or "") else "코스피"

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

    print("  사건 만드는 중... (⭐ **목표 도달일**을 같이 잰다)", flush=True)
    사건 = []
    _목표들 = (3, 5, 10, 15, 20, 40)
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        이름2 = 시장표.get(c, "코스피")
        for k in range(120, len(vs)):
            시원 = vs[k][1]
            시억 = 시원 / 1e8
            if 시억 < 300 or vs[k][2] / 1e8 < 1.0:
                continue
            i = ii[k]
            if i + 20 >= len(날):
                continue
            c1 = 종[k]
            끝 = 주가[날[i + 20]].get(c)
            뒤20 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100 - _비용)
            # ⭐ **목표마다 며칠 만에 닿나** (최대 120일)
            닿 = {}
            for h in range(1, 121):
                j = i + h
                if j >= len(날):
                    break
                v2 = 주가[날[j]].get(c)
                if not v2:
                    continue
                올 = (v2[0] / c1 - 1) * 100 - _비용
                for 목 in _목표들:
                    if 목 not in 닿 and 올 >= 목:
                        닿[목] = h
                if len(닿) == len(_목표들):
                    break
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            m60, sd60 = O.창평균표준(종, k, 60)
            볼60 = ((c1 - m60) / (2 * sd60)) if sd60 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            낙60 = (c1 / 종[k - 60] - 1) * 100 if 종[k - 60] > 0 else None
            일간 = [(종[q] / 종[q - 1] - 1) * 100
                    for q in range(k - 59, k + 1) if 종[q - 1] > 0]
            평 = sum(일간) / len(일간) if 일간 else 0
            평소 = ((sum((z - 평) ** 2 for z in 일간) / len(일간)) ** 0.5
                    if len(일간) > 30 else None)
            fm = 재무값(c, 날[i]) or {}
            자본 = fm.get("자본")
            사건.append({
                "해": 날[i][:4], "시억": 시억, "_20": 뒤20, "닿": 닿,
                "볼20": 볼20, "볼60": 볼60, "낙20": 낙20, "낙60": 낙60,
                "표준낙": ((낙20 / (평소 * (20 ** 0.5)))
                           if (평소 and 평소 > 0 and 낙20 is not None) else None),
                "지낙20": 지낙(이름2, i, 20), "지낙60": 지낙(이름2, i, 60),
                "PBR": (시원 / 자본) if (자본 and 자본 > 0) else None,
            })
    print(f"  사건 **{len(사건):,}건**", flush=True)

    해수 = len(날) / 245
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"))

    def 점(칸, 최소=150):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        v2 = sorted(v)
        n최악 = max(1, len(v2) // 20)
        return {"이김": sum(1 for z in v if z > 0) / len(v) * 100,
                "평균": sum(v) / len(v),
                "최악": sum(v2[:n최악]) / n최악,
                "건수": len(v)}

    def 도달(칸, 목, 안에):
        r"""그 목표에 **안에** 안에 닿은 비율과, 닿은 것들의 **중간 날수**"""
        벌 = [x["닿"].get(목) for x in 칸]
        닿것 = [h for h in 벌 if h is not None and h <= 안에]
        if not 벌:
            return None, None
        비 = len(닿것) / len(벌) * 100
        중 = sorted(닿것)[len(닿것) // 2] if 닿것 else None
        return 비, 중

    def 재기(칸0, 이름, fn, 바, 최소=150):
        칸 = [x for x in 칸0 if fn(x)]
        r = 점(칸, 최소)
        if not r or not 바:
            n = len([x for x in 칸 if x.get("_20") is not None])
            print(f"  {이름:<30}{n:>8,}{'표본 부족':>16}")
            return
        방 = []
        for _, a, b in 구간:
            c1 = 점([x for x in 칸 if a <= x["해"] <= b], 50)
            b1 = 점([x for x in 칸0 if a <= x["해"] <= b], 50)
            if c1 and b1:
                방.append(c1["이김"] - b1["이김"])
        고름 = len(방) == 3 and all(v > 0 for v in 방)
        차 = r["이김"] - 바["이김"]
        기회 = r["건수"] / 해수
        d15, n15 = 도달(칸, 15, 40)
        d40, n40 = 도달(칸, 40, 90)
        표 = ("  ⭐" if (고름 and 차 >= 5 and 기회 >= 10) else
              "  ~" if 차 >= 3 else "")
        방말 = " ".join(f"{v:+.0f}" for v in 방)
        print(f"  {이름:<30}{기회:>7.0f}{r['이김']:>7.1f}%{r['평균']:>+7.2f}"
              f"{r['최악']:>+8.2f}{차:>+7.1f}p"
              f"{(d15 or 0):>7.0f}%{(n15 or 0):>5.0f}일"
              f"{(d40 or 0):>7.0f}%  [{방말}]{표}")

    머 = (f"  {'재료':<30}{'1년에':>7}{'이김':>7}{'평균':>7}{'최악5%':>8}"
          f"{'바탕대비':>7}{'+15%':>7}{'며칠':>5}{'+40%':>7}  [구간별]")

    def _H(x):
        return ((x["지낙20"] is not None and x["지낙20"] <= -7)
                or (x["지낙60"] is not None and x["지낙60"] <= -10))

    def _빠짐(x):
        return ((x["볼20"] is not None and x["볼20"] <= -0.5)
                or (x["낙20"] is not None and x["낙20"] <= -5)
                or (x["낙60"] is not None and x["낙60"] <= -15))

    def _지금(x):
        return (x["볼20"] is not None and x["볼20"] <= -1.0
                and x["낙20"] is not None and x["낙20"] <= -10)

    print("\n" + "=" * 118)
    print("  238차 · ⭐⭐⭐ **「종목 성적」 잣대로 다시**")
    print("     사용자: 「자본 시뮬에서 기각됐다는 건 **나한테 의미 없는 거** 아니야?」")
    print("     ⇒ 자본 배분(몇 개·얼마)은 **판정에서 뺀다**.")
    print("        「이 종목을 사면 오르나」와 **「며칠 만에 목표에 닿나」**를 본다")
    print("=" * 118)

    # ── A 규모별 ──
    print("\n  ── A ⭐⭐⭐ **규모별** — 대형주가 정말 나쁜가 ──")
    for 라, lo, hi in _규모:
        칸0 = [x for x in 사건 if lo <= x["시억"] < hi]
        바 = 점(칸0)
        if not 바:
            continue
        d15, n15 = 도달(칸0, 15, 40)
        d40, _ = 도달(칸0, 40, 90)
        print(f"\n   [{라}]  바탕 이김 {바['이김']:.1f}% · 평균 {바['평균']:+.2f}% ·"
              f" 40일 안 +15% 도달 {d15:.0f}% · 90일 안 +40% {d40:.0f}%")
        print(머)
        재기(칸0, "Ⓗ AND 빠짐", lambda x: _H(x) and _빠짐(x), 바)
        재기(칸0, "지금 규칙 (볼20·낙20)", _지금, 바)
        재기(칸0, "볼60 ≤-1.0σ AND 낙20≤-10",
             lambda x: (x["볼60"] is not None and x["볼60"] <= -1.0
                        and x["낙20"] is not None and x["낙20"] <= -10), 바)
        재기(칸0, "평소 등락폭의 -2.0배↓",
             lambda x: x["표준낙"] is not None and x["표준낙"] <= -2.0, 바)
        재기(칸0, "PBR 0.5배↓ AND 지금 규칙",
             lambda x: (x["PBR"] is not None and x["PBR"] < 0.5 and _지금(x)), 바)
        재기(칸0, "PBR 0.8배↓ AND 지금 규칙",
             lambda x: (x["PBR"] is not None and x["PBR"] < 0.8 and _지금(x)), 바)

    # ── B 대형주 단타 ──
    print("\n" + "=" * 118)
    print("  B ⭐⭐⭐ **대형주 단타** — 사용자 물음")
    print("     「대형주는 **단타 매도를 기준으로** 잡으면 되지 않아?」")
    print("     ⚠️ 왕복 비용 0.26% 를 뺐다. +3% 목표면 비용이 **수익의 9%** 다")
    print("=" * 118)
    for 라, lo, hi in _규모:
        칸0 = [x for x in 사건 if lo <= x["시억"] < hi]
        if not 점(칸0):
            continue
        칸 = [x for x in 칸0 if _H(x) and _빠짐(x)]
        if len(칸) < 150:
            continue
        print(f"\n   [{라}]  Ⓗ AND 빠짐 {len(칸):,}건")
        print(f"  {'목표':<10}{'5일 안':>9}{'10일 안':>9}{'20일 안':>9}"
              f"{'40일 안':>9}{'90일 안':>9}{'닿은 것 중간':>12}")
        for 목 in _목표들:
            줄 = []
            for 안 in (5, 10, 20, 40, 90):
                비, _ = 도달(칸, 목, 안)
                줄.append(f"{비:>8.0f}%" if 비 is not None else f"{'—':>9}")
            _, 중 = 도달(칸, 목, 120)
            print(f"  +{목}%{'':<6}" + "".join(줄)
                  + (f"{중:>10.0f}일" if 중 else f"{'—':>12}"))

    LH.끝맺기(0, 0, ["A 규모별", "B 대형주 단타"])
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_238차_종목성적잣대.txt")

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
