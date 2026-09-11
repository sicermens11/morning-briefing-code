#!/usr/bin/env python3
r"""
cross3_lab.py — **240차 · 3중 교차 (규모 × 섹터 × 재료)** (2026-09-10 신설)

## 왜 다시 하나
```
235-D 에서 3중 교차를 했지만 **재료를 셋만** 넣었다:
   볼20≤-1.0 AND 낙20≤-10  ·  외국인 20일 순매도  ·  재무 셋 다
=> **표준화 낙폭 · 모멘텀 · 밸류 · 때 조건 · 무리**가 빠졌다
=> 「17칸 중 13칸 완료」라고 했지만 3중 칸은 **사실상 미완**이었다
```

## ⚠️ 이 시험이 보는 범위
```
크기   시총 300억 이상 — 상한 없음        방향   **안 걸었다** (오르는 것도 담는다)
기간   2016-01-01 ~                    견줌   **그 칸(규모×섹터)의 바탕**
비용   왕복 0.26% 뺌
```

## 판정
```
① 그 칸 바탕보다 **+5%p** · ② 세 구간 다 같은 방향 · ③ 1년 **10건** 이상
⚠️ 231차에서 섹터만 쪼개도 1년 11~28건이었다. 규모까지 쪼개면 더 적다.
   **표본 부족이 많이 나올 것**이다 — 그것도 결과다
```

쓰는 법:
    python scripts\cross3_lab.py
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
_비용 = 0.26
_규모 = (("소형", 300, 2000), ("중형", 2000, 10000), ("대형", 10000, 9e9))


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


def 무리읽기():
    p = os.path.join(O._DATA, "_무리_60.json")
    if not os.path.exists(p):
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8-sig"))
    except ValueError:
        return {}
    속 = {}
    for 해, 무리들 in (d.get("해마다") or {}).items():
        for 대, 들 in (무리들 or {}).items():
            for c in 들:
                속[(해, c)] = 대
    return 속


def main():
    LH.찍기(
        차수="240차", 이름="3중 교차 (규모 × 섹터 × 재료)",
        크기="시총 300억 이상 — 상한 없음", 방향="**안 걸었다**",
        기간="2016-01-01 ~",
        재료=["주가·시총·거래대금", "지수 71개", "연간 재무"],
        안본것=["수급(235-D에서 함)", "공시", "뉴스", "분기 재무", "계약", "자사주"],
        견줌="그 칸(규모×섹터)의 바탕",
        판정="바탕 +5%p · 세 구간 같은 방향 · 1년 10건 이상",
    )

    섹터맵 = CM.섹터표()
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    재무 = 연간재무원본()
    속 = 무리읽기()
    print(f"  거래일 {len(날):,}일 · 섹터 {len(섹터맵):,}종목 · 무리 {len(속):,}",
          flush=True)

    지수 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        하루 = {}
        for n in ("코스피", "코스닥"):
            v2 = (d2.get("지수") or {}).get(n) or {}
            try:
                하루[n] = float(str(v2.get("종가")).replace(",", ""))
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
            if c in 섹터맵:
                종계.setdefault(c, []).append(v)
                있는날.setdefault(c, []).append(자리[d])
    print(f"  섹터에 든 종목 {len(종계):,}개", flush=True)

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
        섹 = 섹터맵[c]
        n2 = 시장표.get(c, "코스피")
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
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100 - _비용)
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
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
                "섹": 섹, "시억": 시억, "해": 날[i][:4], "_20": 뒤,
                "볼20": 볼20, "낙20": 낙20, "낙60": 낙60,
                "표준낙": ((낙20 / (평소 * (20 ** 0.5)))
                           if (평소 and 평소 > 0 and 낙20 is not None) else None),
                "지낙20": 지낙(n2, i, 20), "지낙60": 지낙(n2, i, 60),
                "PBR": (시원 / 자본) if (자본 and 자본 > 0) else None,
                "무리": 속.get((날[i][:4], c)),
            })
    print(f"  사건 **{len(사건):,}건**", flush=True)

    해수 = len(날) / 245
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"))

    def 점(칸, 최소=100):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(v))

    def _H(x):
        return ((x["지낙20"] is not None and x["지낙20"] <= -7)
                or (x["지낙60"] is not None and x["지낙60"] <= -10))

    def _빠짐(x):
        return ((x["볼20"] is not None and x["볼20"] <= -0.5)
                or (x["낙20"] is not None and x["낙20"] <= -5)
                or (x["낙60"] is not None and x["낙60"] <= -15))

    # ⭐ 235-D 에 **없던** 재료들을 넣는다
    재료들 = [
        ("[견줌] 지금 규칙",
         lambda x: (x["볼20"] is not None and x["볼20"] <= -1.0
                    and x["낙20"] is not None and x["낙20"] <= -10)),
        ("⭐ Ⓗ AND 빠짐 (때 조건)", lambda x: _H(x) and _빠짐(x)),
        ("⭐ 평소 등락폭 -1.5배↓",
         lambda x: x["표준낙"] is not None and x["표준낙"] <= -1.5),
        ("⭐ 평소 등락폭 -2.0배↓",
         lambda x: x["표준낙"] is not None and x["표준낙"] <= -2.0),
        ("⭐ PBR 0.8배↓ (밸류)",
         lambda x: x["PBR"] is not None and x["PBR"] < 0.8),
        ("⭐ 오름 20일 +10%↑ (모멘텀)",
         lambda x: x["낙20"] is not None and x["낙20"] >= 10),
        ("⭐ 무리에 들어 있다", lambda x: bool(x["무리"])),
    ]

    섹들 = sorted({x["섹"] for x in 사건 if x["섹"]})
    print("\n" + "=" * 110)
    print("  240차 · ⭐⭐⭐ **3중 교차 (규모 × 섹터 × 재료)**")
    print("     235-D 는 **재료 셋만** 넣었다 (볼20·낙20 / 외국인 / 재무).")
    print("     여기서 **표준화 낙폭 · 모멘텀 · 밸류 · 때 조건 · 무리**를 넣는다")
    print("=" * 110)

    머 = (f"  {'재료':<26}{'건수':>8}{'1년에':>7}{'이김':>8}"
          f"{'바탕대비':>9}  [구간별]")
    된것 = []
    칸수 = 표본된칸 = 0
    for 섹 in 섹들:
        for 라, lo, hi in _규모:
            칸수 += 1
            칸0 = [x for x in 사건 if x["섹"] == 섹 and lo <= x["시억"] < hi]
            바 = 점(칸0)
            if not 바:
                continue
            표본된칸 += 1
            print(f"\n   [{섹} · {라}]  {len(칸0):,}건 · "
                  f"1년 {len(칸0)/해수:,.0f}건 · 바탕 {바[0]:.1f}%")
            print(머)
            for 이름, fn in 재료들:
                칸 = [x for x in 칸0 if fn(x)]
                r = 점(칸, 60)
                if not r:
                    continue
                방 = []
                for _, a, b in 구간:
                    c1 = 점([x for x in 칸 if a <= x["해"] <= b], 25)
                    b1 = 점([x for x in 칸0 if a <= x["해"] <= b], 25)
                    if c1 and b1:
                        방.append(c1[0] - b1[0])
                고름 = len(방) == 3 and all(v > 0 for v in 방)
                차 = r[0] - 바[0]
                쓸 = r[2] / 해수 >= 10
                표 = ("  ⭐ **된다**" if (고름 and 차 >= 5 and 쓸)
                      else "  (1년 10건 미만)" if (고름 and 차 >= 5)
                      else "  ~" if 차 >= 3 else "")
                if 고름 and 차 >= 5 and 쓸:
                    된것.append((섹, 라, 이름, 차, r[2] / 해수))
                방말 = " ".join(f"{v:+.0f}" for v in 방)
                print(f"  {이름:<26}{r[2]:>8,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
                      f"{차:>+8.1f}p  [{방말}]{표}")

    print("\n" + "=" * 110)
    print(f"  ⇒ 3중 칸 **{칸수}개** 중 **{표본된칸}개**가 표본이 됐다")
    if 된것:
        print(f"  ⇒ ⭐ **된 칸 {len(된것)}개**")
        for 섹, 라, 이름, 차, 해건 in sorted(된것, key=lambda z: -z[3])[:20]:
            print(f"       {섹:<18}{라:<5}{이름:<26}{차:+.1f}p · 1년 {해건:.0f}건")
        print("\n     ⚠️ 3중으로 쪼개면 **한 칸이 1년 10~30건**이다.")
        print("        혼자서는 못 쓴다 — 여러 칸을 **합쳐야** 한다")
    else:
        print("  ⇒ ❌ **된 칸이 없다** (바탕 +5%p · 세 구간 · 1년 10건)")
    print("=" * 110)
    LH.끝맺기(len(된것), 칸수, ["3중 교차 전부"])
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_240차_3중교차.txt")

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
