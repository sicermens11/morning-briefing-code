#!/usr/bin/env python3
r"""
rest_combo_lab.py — **235차 · 남은 조합 13칸 + 안 써본 재료** (2026-09-10 신설)

## ⚠️ 앞서 「다 했다」고 말했는데 **틀렸다**
```
조합 격자 **17칸** 중 오늘 메운 것은 **4칸**뿐이었다
  ✅ 때×규모(230-A) · 때×섹터(230-B) · 표준화×섹터(231) · 밸류×섹터(232)
  ❌ 남은 **13칸** — 특히 **「× 규모 × 섹터」 3중 교차는 한 칸도 안 했다**
그리고 「빈 칸 12개」라고 했던 숫자도 틀렸다 (실제 17개)
```

## 이 시험이 메우는 것
```
A ⭐⭐⭐ **수급**(외국인·기관) × 규모 · × 섹터
B ⭐⭐⭐ **재무**(잉여금·부채·ROE) × 규모 · × 섹터
C ⭐⭐⭐ **상관 무리** × 규모 · × 섹터
D ⭐⭐⭐ **3중 교차** (규모 × 섹터) — 한 칸도 안 했다
       ⚠️ 231차에서 섹터만 쪼개도 1년 11~28건이었다.
          규모까지 쪼개면 **표본이 무너질 것**이다. 재보고 말한다
```

## ⚠️ 이 시험이 보는 범위
```
크기   시총 300억 이상 — **상한 없음**
방향   **안 걸었다**
기간   2016-01-01 ~
견줌   그 칸의 **바탕**
판정   바탕 +5%p · 세 구간 같은 방향 · 1년 10건 이상
```

쓰는 법:
    python scripts\rest_combo_lab.py
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


def 수급읽기(날집합):
    r"""{날짜: {코드: (외국인, 기관, 외국인지분율)}} — flow-daily"""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "flow-daily", "*.json"))):
        d8 = os.path.basename(f)[:8]
        if d8 not in 날집합:
            continue
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        하루 = {}
        for c, v in (d.get("종목") or {}).items():
            if not isinstance(v, dict):
                continue

            def _수(k):
                x = v.get(k)
                try:
                    return float(str(x).replace(",", ""))
                except (TypeError, ValueError):
                    return None
            하루[c] = (_수("외국인"), _수("기관"), _수("외국인지분율"))
        if 하루:
            out[d8] = 하루
    return out


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
            자본, 부채, 순익 = g("자본총계"), g("부채총계"), g("당기순이익(손실)")
            잉여 = g("이익잉여금")
            자산 = g("자산총계")
            out.setdefault(code, []).append((적용, {
                "부채비": (부채 / 자본 * 100) if (자본 and 자본 > 0
                                                and 부채 is not None) else None,
                "잉여비": (잉여 / 자산 * 100) if (자산 and 자산 > 0
                                                and 잉여 is not None) else None,
                "ROE": (순익 / 자본 * 100) if (자본 and 자본 > 0
                                              and 순익 is not None) else None,
                "흑자": (1.0 if (순익 is not None and 순익 > 0) else 0.0),
            }))
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
        차수="235차", 이름="남은 조합 13칸 + 3중 교차",
        크기="시총 300억 이상 — **상한 없음**",
        방향="**안 걸었다**",
        기간="2016-01-01 ~",
        재료=["외국인·기관·개인 순매수 · 외국인지분율", "연간 재무", "주가·시총·거래대금"],
        안본것=["공시", "뉴스", "해외", "금리", "분기 재무", "ETF", "증자", "공시 시각"],
        견줌="그 칸의 **바탕**",
        판정="바탕 +5%p · 세 구간 같은 방향 · 1년 10건 이상",
    )

    섹터맵 = CM.섹터표()
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    재무 = 연간재무원본()
    속 = 무리읽기()
    수급 = 수급읽기(set(날))
    print(f"  거래일 {len(날):,}일 · 재무 {len(재무):,}종목 · "
          f"수급 {len(수급):,}일 · 무리 {len(속):,}개", flush=True)

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
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            # 수급 20일 누적
            외누, 기누 = 0.0, 0.0
            지분 = None
            본날 = 0
            for q in range(max(0, i - 19), i + 1):
                h = (수급.get(날[q]) or {}).get(c)
                if not h:
                    continue
                본날 += 1
                if h[0] is not None:
                    외누 += h[0]
                if h[1] is not None:
                    기누 += h[1]
                if h[2] is not None:
                    지분 = h[2]
            fm = 재무값(c, 날[i]) or {}
            사건.append({
                "섹": 섹, "시억": 시억, "해": 날[i][:4], "_20": 뒤,
                "볼20": 볼20, "낙20": 낙20,
                "외20": (외누 if 본날 >= 10 else None),
                "기20": (기누 if 본날 >= 10 else None),
                "지분": 지분,
                "부채비": fm.get("부채비"), "잉여비": fm.get("잉여비"),
                "ROE": fm.get("ROE"), "흑자": fm.get("흑자"),
                "무리": 속.get((날[i][:4], c)),
            })
    print(f"  사건 **{len(사건):,}건**", flush=True)
    _수급붙 = sum(1 for x in 사건 if x["외20"] is not None)
    _재무붙 = sum(1 for x in 사건 if x["부채비"] is not None)
    _무리붙 = sum(1 for x in 사건 if x["무리"])
    print(f"    수급 붙은 것 {_수급붙:,} ({_수급붙/len(사건)*100:.0f}%) · "
          f"재무 {_재무붙:,} ({_재무붙/len(사건)*100:.0f}%) · "
          f"무리 {_무리붙:,} ({_무리붙/len(사건)*100:.0f}%)", flush=True)

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
            n = len([x for x in 칸 if x.get("_20") is not None])
            print(f"  {이름:<30}{n:>9,}{'표본 부족':>18}")
            return
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

    머 = (f"  {'재료':<30}{'건수':>9}{'1년에':>7}{'이김':>8}"
          f"{'바탕대비':>9}  [구간별]")

    수급재료 = (("외국인 20일 **순매수**", lambda x: (x["외20"] or 0) > 0),
                ("외국인 20일 **순매도**", lambda x: (x["외20"] or 0) < 0),
                ("기관 20일 **순매수**", lambda x: (x["기20"] or 0) > 0),
                ("기관 20일 **순매도**", lambda x: (x["기20"] or 0) < 0),
                ("외국인·기관 **둘 다 순매수**",
                 lambda x: (x["외20"] or 0) > 0 and (x["기20"] or 0) > 0),
                ("외국인·기관 **둘 다 순매도**",
                 lambda x: (x["외20"] or 0) < 0 and (x["기20"] or 0) < 0),
                ("외국인 지분율 **10%↑**",
                 lambda x: x["지분"] is not None and x["지분"] >= 10),
                ("외국인 지분율 **3%↓**",
                 lambda x: x["지분"] is not None and x["지분"] <= 3))
    재무재료 = (("잉여금비율 30%↑", lambda x: (x["잉여비"] or -999) >= 30),
                ("부채비율 80%↓", lambda x: x["부채비"] is not None and x["부채비"] <= 80),
                ("ROE 5%↑", lambda x: (x["ROE"] or -999) >= 5),
                ("**흑자**", lambda x: x["흑자"] == 1.0),
                ("셋 다 (지금 규칙 재무)",
                 lambda x: ((x["잉여비"] or -999) >= 30
                            and x["부채비"] is not None and x["부채비"] <= 80
                            and x["흑자"] == 1.0)))
    무리재료 = (("무리에 **들어 있다**", lambda x: bool(x["무리"])),
                ("무리에 **없다**", lambda x: not x["무리"]))

    # ── A·B·C: 수급 · 재무 · 무리 × 규모 ──
    for 절, 재료들 in (("A ⭐⭐⭐ **수급** × 규모", 수급재료),
                       ("B ⭐⭐⭐ **재무** × 규모", 재무재료),
                       ("C ⭐⭐⭐ **상관 무리** × 규모", 무리재료)):
        print("\n" + "=" * 104)
        print(f"  {절}")
        print("=" * 104)
        for 라, lo, hi in _규모:
            칸0 = [x for x in 사건 if lo <= x["시억"] < hi]
            바 = 점(칸0)
            if not 바:
                continue
            print(f"\n   [{라}]  {len(칸0):,}건 · 바탕 {바[0]:.1f}%")
            print(머)
            for 이름, fn in 재료들:
                재기(칸0, 이름, fn, 바)

    # ── 수급 · 재무 · 무리 × 섹터 ──
    섹들 = sorted({x["섹"] for x in 사건 if x["섹"]})
    for 절, 재료들 in (("A-2 ⭐⭐ **수급** × 섹터", 수급재료),
                       ("B-2 ⭐⭐ **재무** × 섹터", 재무재료),
                       ("C-2 ⭐⭐ **상관 무리** × 섹터", 무리재료)):
        print("\n" + "=" * 104)
        print(f"  {절}")
        print("=" * 104)
        for 섹 in 섹들:
            칸0 = [x for x in 사건 if x["섹"] == 섹]
            바 = 점(칸0)
            if not 바:
                continue
            print(f"\n   [{섹}]  바탕 {바[0]:.1f}%")
            print(머)
            for 이름, fn in 재료들:
                재기(칸0, 이름, fn, 바)

    # ── D: 3중 교차 (규모 × 섹터) ──
    print("\n" + "=" * 104)
    print("  D ⭐⭐⭐ **3중 교차 (규모 × 섹터)** — 한 칸도 안 했던 것")
    print("     ⚠️ 231차에서 섹터만 쪼개도 1년 11~28건이었다.")
    print("        규모까지 쪼개면 **표본이 무너질 것**이다 — 재보고 말한다")
    print("=" * 104)
    쓸수있는칸, 못쓰는칸 = 0, 0
    for 섹 in 섹들:
        for 라, lo, hi in _규모:
            칸0 = [x for x in 사건 if x["섹"] == 섹 and lo <= x["시억"] < hi]
            바 = 점(칸0)
            if not 바:
                못쓰는칸 += 1
                continue
            쓸수있는칸 += 1
            print(f"\n   [{섹} · {라}]  {len(칸0):,}건 · "
                  f"1년 {len(칸0)/해수:,.0f}건 · 바탕 {바[0]:.1f}%")
            print(머)
            재기(칸0, "볼20≤-1.0 AND 낙20≤-10 (지금)",
                 lambda x: (x["볼20"] is not None and x["볼20"] <= -1.0
                            and x["낙20"] is not None and x["낙20"] <= -10), 바)
            재기(칸0, "외국인 20일 순매도",
                 lambda x: (x["외20"] or 0) < 0, 바)
            재기(칸0, "셋 다 (지금 규칙 재무)",
                 lambda x: ((x["잉여비"] or -999) >= 30
                            and x["부채비"] is not None and x["부채비"] <= 80
                            and x["흑자"] == 1.0), 바)
    print(f"\n     ⇒ 3중 칸 **{쓸수있는칸 + 못쓰는칸}개** 중 "
          f"**{쓸수있는칸}개**만 표본이 되고 **{못쓰는칸}개**는 표본 부족")

    LH.끝맺기(0, 0, ["A 수급×규모", "A-2 수급×섹터", "B 재무×규모",
                     "B-2 재무×섹터", "C 무리×규모", "C-2 무리×섹터",
                     "D 3중 교차"])
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_235차_남은조합13칸.txt")

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
