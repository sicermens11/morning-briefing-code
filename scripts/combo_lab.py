#!/usr/bin/env python3
r"""
combo_lab.py — **230~232차 · 조합 빈 칸을 메운다** (2026-09-10 신설)

## 사용자 지시
```
「조합 격자 — 빈 칸이 열두 개, 나중에 결정돼서 조합을 못 한 것,
 제대로 안 된 것 · 끝까지 안 된 것, 다음 순서 **일단 다 해!**」
```

## 메우는 빈 칸 (COMBO-AUDIT-2026-09-10.md)
```
230차 ⭐⭐⭐ **때 조건 × 규모 × 섹터**   반영 1순위(Ⓗ)의 빈 칸. 가장 급했다
231차 ⭐⭐  **표준화 낙폭 × 섹터**       226·227차의 빈 칸
232차 ⭐⭐  **밸류(PER·PBR) × 섹터**    225차의 빈 칸
234차 ⭐⭐  **볼60 vs 볼20**            227차에서 볼60이 상위였다 (지금은 볼20)
```

## ⚠️ 이 시험이 보는 범위 (여기 없는 것은 안 본 것이다)
```
크기   시총 300억 이상 — **상한 없음** (대형주 포함)
방향   **안 걸었다** — 오르는 종목도 담는다
기간   2016-01-01 ~
견줌   그 칸(규모·섹터)의 **바탕**. 소형주 성적과 직접 대지 않는다
```

## 판정 기준 (먼저 밝힌다)
```
① 그 칸의 바탕보다 **+5%p** 이상
② **세 구간 다** 같은 방향 (2016~19 / 2020~22 / 2023~26)
③ 1년에 **10건 이상**
```

쓰는 법:
    python scripts\combo_lab.py
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import chain_map as CM  # noqa: E402
import lab_header as LH  # noqa: E402

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
                "자본": g("자본총계"), "순익": g("당기순이익(손실)")}))
    for c in out:
        out[c].sort()
    return out


def main():
    LH.찍기(
        차수="230~232·234차", 이름="조합 빈 칸 메우기",
        크기="시총 300억 이상 — **상한 없음** (대형주 포함)",
        방향="**안 걸었다** — 오르는 종목도 담는다",
        기간="2016-01-01 ~",
        재료=["주가·시총·거래대금", "지수 71개", "연간 재무", "표준화 낙폭"],
        안본것=["수급", "공시", "뉴스", "무리", "모멘텀(224·227·229차에서 이미 실패)"],
        견줌="그 칸(규모·섹터)의 **바탕**",
        판정="바탕 +5%p · 세 구간 같은 방향 · 1년 10건 이상",
    )

    섹터맵 = CM.섹터표()
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    재무 = 연간재무원본()
    print(f"  거래일 {len(날):,}일 · 섹터맵 {len(섹터맵):,}종목 "
          f"· 재무 {len(재무):,}종목", flush=True)

    # ── 지수 계열 (때 조건) ──
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
    계열 = {이름2: [(지수.get(d) or {}).get(이름2) for d in 날]
            for 이름2 in ("코스피", "코스닥")}
    print(f"  지수 {len(지수):,}일", flush=True)

    def 지낙(이름2, i, n):
        sq = 계열[이름2]
        if i < n or i >= len(sq):
            return None
        a, b = sq[i - n], sq[i]
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

    print("  사건 만드는 중...", flush=True)
    사건 = []
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        섹 = 섹터맵.get(c)
        이름2 = 시장표.get(c, "코스피")
        for k in range(120, len(vs)):
            시원 = vs[k][1]
            시억 = 시원 / 1e8
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
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            낙60v = (c1 / 종[k - 60] - 1) * 100 if 종[k - 60] > 0 else None
            일간 = [(종[q] / 종[q - 1] - 1) * 100
                    for q in range(k - 59, k + 1) if 종[q - 1] > 0]
            평 = sum(일간) / len(일간) if 일간 else 0
            평소 = ((sum((z - 평) ** 2 for z in 일간) / len(일간)) ** 0.5
                    if len(일간) > 30 else None)
            fm = 재무값(c, 날[i]) or {}
            자본, 순익 = fm.get("자본"), fm.get("순익")
            사건.append({
                "섹": 섹, "시억": 시억, "해": 날[i][:4], "_20": 뒤,
                "볼20": 볼20, "볼60": 볼60, "낙20": 낙20, "낙60": 낙60v,
                "표준낙": ((낙20 / (평소 * (20 ** 0.5)))
                           if (평소 and 평소 > 0 and 낙20 is not None) else None),
                "지낙20": 지낙(이름2, i, 20), "지낙60": 지낙(이름2, i, 60),
                "PBR": (시원 / 자본) if (자본 and 자본 > 0) else None,
                "PER": (시원 / 순익) if (순익 and 순익 > 0) else None,
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

    def 재기(칸0, 이름, fn, 바, 최소=120):
        칸 = [x for x in 칸0 if fn(x)]
        r = 점(칸, 최소)
        if not r or not 바:
            return None
        방 = []
        for _, a, b in 구간:
            c1 = 점([x for x in 칸 if a <= x["해"] <= b], 40)
            b1 = 점([x for x in 칸0 if a <= x["해"] <= b], 40)
            if c1 and b1:
                방.append(c1[0] - b1[0])
        고름 = len(방) == 3 and all(v > 0 for v in 방)
        차 = r[0] - 바[0]
        쓸 = r[2] / 해수 >= 10
        표 = ("  ⭐ **된다**" if (고름 and 차 >= 5 and 쓸)
              else "  (1년 10건 미만)" if (고름 and 차 >= 5)
              else "  ~" if 차 >= 3 else "")
        방말 = " ".join(f"{v:+.0f}" for v in 방)
        print(f"  {이름:<30}{r[2]:>9,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
              f"{차:>+8.1f}p  [{방말}]{표}")
        return (차, 고름, 쓸)

    머 = (f"  {'재료':<30}{'건수':>9}{'1년에':>7}{'이김':>8}"
          f"{'바탕대비':>9}  [구간별]")

    # ══ 230차 — 때 조건 × 규모 × 섹터 ══
    print("\n" + "=" * 104)
    print("  230차 · ⭐⭐⭐ **때 조건 × 규모 × 섹터**")
    print("     반영 1순위 Ⓗ(시장낙폭)를 **규모별·섹터별로 한 번도 안 봤다**")
    print("=" * 104)
    때들 = (("지수20일 ≤-7%", lambda x: x["지낙20"] is not None and x["지낙20"] <= -7),
            ("지수60일 ≤-10%", lambda x: x["지낙60"] is not None and x["지낙60"] <= -10),
            ("Ⓗ (둘 중 하나)",
             lambda x: ((x["지낙20"] is not None and x["지낙20"] <= -7)
                        or (x["지낙60"] is not None and x["지낙60"] <= -10))))

    print("\n  ── 230-A **때 × 규모** ──")
    for 라, lo, hi in _규모:
        칸0 = [x for x in 사건 if lo <= x["시억"] < hi]
        바 = 점(칸0)
        if not 바:
            print(f"\n   [{라}] 표본 부족")
            continue
        print(f"\n   [{라}]  {len(칸0):,}건 · 바탕 {바[0]:.1f}%")
        print(머)
        for 이름, fn in 때들:
            재기(칸0, 이름, fn, 바)
            재기(칸0, f"   └ {이름} **AND 빠짐**",
                 lambda x, f=fn: (f(x) and ((x["볼20"] is not None and x["볼20"] <= -0.5)
                                            or (x["낙20"] is not None and x["낙20"] <= -5)
                                            or (x["낙60"] is not None and x["낙60"] <= -15))),
                 바)

    print("\n  ── 230-B **때 × 섹터** ──")
    섹들 = sorted({x["섹"] for x in 사건 if x["섹"]})
    for 섹 in 섹들:
        칸0 = [x for x in 사건 if x["섹"] == 섹]
        바 = 점(칸0)
        if not 바:
            continue
        print(f"\n   [{섹}]  {len(칸0):,}건 · 바탕 {바[0]:.1f}%")
        print(머)
        for 이름, fn in 때들[2:]:
            재기(칸0, 이름, fn, 바)
            재기(칸0, "   └ Ⓗ **AND 빠짐**",
                 lambda x, f=fn: (f(x) and ((x["볼20"] is not None and x["볼20"] <= -0.5)
                                            or (x["낙20"] is not None and x["낙20"] <= -5)
                                            or (x["낙60"] is not None and x["낙60"] <= -15))),
                 바)

    # ══ 231차 — 표준화 낙폭 × 섹터 ══
    print("\n" + "=" * 104)
    print("  231차 · ⭐⭐ **표준화 낙폭 × 섹터** (226·227차의 빈 칸)")
    print("=" * 104)
    for 섹 in 섹들:
        칸0 = [x for x in 사건 if x["섹"] == 섹]
        바 = 점(칸0)
        if not 바:
            continue
        print(f"\n   [{섹}]  바탕 {바[0]:.1f}%")
        print(머)
        for 문 in (-1.0, -1.5, -2.0, -2.5):
            재기(칸0, f"평소 등락폭의 {문:+.1f}배↓",
                 lambda x, a=문: x["표준낙"] is not None and x["표준낙"] <= a, 바)

    # ══ 232차 — 밸류 × 섹터 ══
    print("\n" + "=" * 104)
    print("  232차 · ⭐⭐ **밸류(PER·PBR) × 섹터** (225차의 빈 칸)")
    print("     ⚠️ 조선·건설은 원래 PBR 이 낮다 — 섹터마다 문턱이 달라야 할 수 있다")
    print("=" * 104)
    for 섹 in 섹들:
        칸0 = [x for x in 사건 if x["섹"] == 섹]
        바 = 점(칸0)
        if not 바:
            continue
        pb = sorted(x["PBR"] for x in 칸0 if x["PBR"] is not None)
        가운데 = pb[len(pb) // 2] if pb else None
        print(f"\n   [{섹}]  바탕 {바[0]:.1f}%"
              + (f" · 이 섹터 PBR 가운데 **{가운데:.2f}배**" if 가운데 else ""))
        print(머)
        for 문 in (0.5, 0.8, 1.0):
            재기(칸0, f"PBR {문}배↓",
                 lambda x, a=문: x["PBR"] is not None and x["PBR"] < a, 바)
        if 가운데:
            재기(칸0, f"PBR **이 섹터 가운데**({가운데:.2f})↓",
                 lambda x, a=가운데: x["PBR"] is not None and x["PBR"] < a, 바)
        재기(칸0, "PER 8배↓",
             lambda x: x["PER"] is not None and x["PER"] < 8, 바)

    # ══ 234차 — 볼60 vs 볼20 ══
    print("\n" + "=" * 104)
    print("  234차 · ⭐⭐ **볼60 vs 볼20** — 지금 규칙은 볼20 인데 227차에서 볼60 이 상위였다")
    print("=" * 104)
    for 라, lo, hi in _규모:
        칸0 = [x for x in 사건 if lo <= x["시억"] < hi]
        바 = 점(칸0)
        if not 바:
            continue
        print(f"\n   [{라}]  바탕 {바[0]:.1f}%")
        print(머)
        for w in (20, 60):
            for 문 in (-1.0, -1.5, -2.0):
                재기(칸0, f"볼{w} ≤{문:+.1f}σ",
                     lambda x, a=w, b=문: (x[f"볼{a}"] is not None
                                           and x[f"볼{a}"] <= b), 바)
        재기(칸0, "볼20≤-1.0 **AND** 낙20≤-10 (지금)",
             lambda x: (x["볼20"] is not None and x["볼20"] <= -1.0
                        and x["낙20"] is not None and x["낙20"] <= -10), 바)
        재기(칸0, "볼60≤-1.0 **AND** 낙20≤-10",
             lambda x: (x["볼60"] is not None and x["볼60"] <= -1.0
                        and x["낙20"] is not None and x["낙20"] <= -10), 바)

    LH.끝맺기(0, 0, ["230-A 때×규모", "230-B 때×섹터", "231 표준화×섹터",
                     "232 밸류×섹터", "234 볼60vs볼20"])
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_230-234차_조합빈칸.txt")

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
