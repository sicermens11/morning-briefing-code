#!/usr/bin/env python3
r"""
bigcap_check_lab.py — **238-2차 · 대형주 결과가 반도체 호황 탓인가** (2026-09-10)

## 사용자 물음
```
「"40일 안에 +15% 도달률이 소형 45%, 대형 **44%**로 거의 같고," 이건
 **최근 반도체 호황이라 삼성전자 SK하이닉스가 급등해서** 그런 결과 아니야?」
```

## 확인하는 것
```
A ⭐⭐⭐ **+15%·+40% 도달률을 구간별로** (2016~19 / 2020~22 / 2023~26)
        238차는 **승률만** 구간별로 찍었다. 도달률은 통짜였다
B ⭐⭐⭐ **삼성전자·SK하이닉스를 빼고** 다시
C ⭐⭐  **반도체 섹터를 통째로 빼고** 다시
D ⭐   대형주 안에서 **어떤 종목이 도달률을 끌고 가나** (상위 10개)
```

## ⚠️ 이 시험이 보는 범위
```
크기   시총 300억 이상 — 상한 없음     방향   안 걸었다
기간   2016-01-01 ~                 조건   Ⓗ AND 빠짐 (238차와 같게)
비용   왕복 0.26% 뺌
```

쓰는 법:
    python scripts\bigcap_check_lab.py
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import chain_map as CM  # noqa: E402

_시작 = "20160101"
_비용 = 0.26
_삼전 = {"005930", "000660"}          # 삼성전자 · SK하이닉스
_규모 = (("소형 300~2,000억", 300, 2000),
         ("중형 2,000억~1조", 2000, 10000),
         ("대형 1조↑", 10000, 9e9))
_구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
         ("2023~2026", "2023", "2026"))


def main():
    섹터맵 = CM.섹터표()
    반도체 = {c for c, s in 섹터맵.items() if "반도체" in s}
    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일 · 반도체 섹터 {len(반도체)}종목", flush=True)

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
    이름표 = {}
    _sb = json.load(io.open(os.path.join(O._DATA, "stock-base.json"),
                            encoding="utf-8-sig")).get("종목") or {}
    for c2, v2 in _sb.items():
        시장표[c2] = "코스닥" if "KOSDAQ" in str(v2.get("시장") or "") else "코스피"
        이름표[c2] = v2.get("이름") or c2

    종계, 있는날 = {}, {}
    자리 = {d: i for i, d in enumerate(날)}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(자리[d])

    print("  사건 만드는 중...", flush=True)
    사건 = []
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        n2 = 시장표.get(c, "코스피")
        for k in range(120, len(vs)):
            시억 = vs[k][1] / 1e8
            if 시억 < 300 or vs[k][2] / 1e8 < 1.0:
                continue
            i = ii[k]
            if i + 20 >= len(날):
                continue
            c1 = 종[k]
            g20, g60 = 지낙(n2, i, 20), 지낙(n2, i, 60)
            H = ((g20 is not None and g20 <= -7) or (g60 is not None and g60 <= -10))
            if not H:
                continue
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            낙60 = (c1 / 종[k - 60] - 1) * 100 if 종[k - 60] > 0 else None
            빠 = ((볼20 is not None and 볼20 <= -0.5)
                  or (낙20 is not None and 낙20 <= -5)
                  or (낙60 is not None and 낙60 <= -15))
            if not 빠:
                continue
            끝 = 주가[날[i + 20]].get(c)
            뒤20 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100 - _비용)
            닿 = {}
            for h in range(1, 91):
                j = i + h
                if j >= len(날):
                    break
                v2 = 주가[날[j]].get(c)
                if not v2:
                    continue
                올 = (v2[0] / c1 - 1) * 100 - _비용
                for 목 in (15, 40):
                    if 목 not in 닿 and 올 >= 목:
                        닿[목] = h
                if len(닿) == 2:
                    break
            사건.append({"code": c, "해": 날[i][:4], "시억": 시억,
                         "_20": 뒤20, "닿": 닿})
    print(f"  사건 **{len(사건):,}건** (Ⓗ AND 빠짐)", flush=True)

    def 재기(칸, 라, 들여=0):
        v = [x["_20"] for x in 칸 if x["_20"] is not None]
        if len(v) < 100:
            print(f"  {' ' * 들여}{라:<34}{len(v):>8,}{'표본 부족':>14}")
            return
        d15 = sum(1 for x in 칸 if (x["닿"].get(15) or 999) <= 40) / len(칸) * 100
        d40 = sum(1 for x in 칸 if (x["닿"].get(40) or 999) <= 90) / len(칸) * 100
        이 = sum(1 for z in v if z > 0) / len(v) * 100
        print(f"  {' ' * 들여}{라:<34}{len(v):>8,}{이:>8.1f}%"
              f"{sum(v)/len(v):>+8.2f}{d15:>9.0f}%{d40:>8.0f}%")

    머 = (f"  {'칸':<34}{'건수':>8}{'이김':>8}{'평균':>8}"
          f"{'40일 +15%':>10}{'90일 +40%':>9}")

    print("\n" + "=" * 96)
    print("  238-2차 · ⭐⭐⭐ **대형주 결과가 반도체 호황 탓인가**")
    print("     사용자: 「최근 반도체 호황이라 삼성전자 SK하이닉스가 급등해서")
    print("              그런 결과 아니야?」")
    print("=" * 96)

    print("\n  ── A ⭐⭐⭐ **도달률을 구간별로** (238차는 통짜였다) ──")
    for 라, lo, hi in _규모:
        칸0 = [x for x in 사건 if lo <= x["시억"] < hi]
        if len(칸0) < 200:
            continue
        print(f"\n   [{라}]")
        print(머)
        재기(칸0, "전 기간")
        for 라2, a, b in _구간:
            재기([x for x in 칸0 if a <= x["해"] <= b], 라2, 들여=2)

    print("\n  ── B ⭐⭐⭐ **삼성전자·SK하이닉스를 빼고** ──")
    대형 = [x for x in 사건 if x["시억"] >= 10000]
    삼전건 = [x for x in 대형 if x["code"] in _삼전]
    print(f"     대형주 {len(대형):,}건 중 삼성전자·SK하이닉스 "
          f"**{len(삼전건):,}건 ({len(삼전건)/max(1,len(대형))*100:.1f}%)**")
    print(머)
    재기(대형, "대형주 전부")
    재기([x for x in 대형 if x["code"] not in _삼전], "**둘을 빼고**")
    재기(삼전건, "삼성전자·SK하이닉스만")
    print()
    for 라2, a, b in _구간:
        재기([x for x in 대형 if x["code"] not in _삼전 and a <= x["해"] <= b],
             f"둘 빼고 · {라2}", 들여=2)

    print("\n  ── C ⭐⭐ **반도체 섹터를 통째로 빼고** ──")
    반건 = [x for x in 대형 if x["code"] in 반도체]
    print(f"     대형주 {len(대형):,}건 중 반도체 섹터 "
          f"**{len(반건):,}건 ({len(반건)/max(1,len(대형))*100:.1f}%)**")
    print(머)
    재기([x for x in 대형 if x["code"] not in 반도체], "**반도체 빼고**")
    재기(반건, "반도체만")
    print()
    for 라2, a, b in _구간:
        재기([x for x in 대형 if x["code"] not in 반도체 and a <= x["해"] <= b],
             f"반도체 빼고 · {라2}", 들여=2)

    print("\n  ── D ⭐ **대형주 안에서 어느 종목이 많이 걸렸나** (상위 12개) ──")
    셈 = {}
    for x in 대형:
        셈[x["code"]] = 셈.get(x["code"], 0) + 1
    print(f"  {'종목':<24}{'건수':>8}{'몫':>7}{'이김':>8}{'40일 +15%':>10}")
    for c, n in sorted(셈.items(), key=lambda z: -z[1])[:12]:
        칸 = [x for x in 대형 if x["code"] == c]
        v = [x["_20"] for x in 칸 if x["_20"] is not None]
        if not v:
            continue
        d15 = sum(1 for x in 칸 if (x["닿"].get(15) or 999) <= 40) / len(칸) * 100
        이 = sum(1 for z in v if z > 0) / len(v) * 100
        print(f"  {이름표.get(c, c)[:22]:<24}{n:>8,}"
              f"{n/len(대형)*100:>6.1f}%{이:>7.1f}%{d15:>9.0f}%")

    print("\n" + "=" * 96)
    print("  읽는 법")
    print("    - B·C 에서 **빼고도 도달률이 비슷하면** 반도체 탓이 아니다")
    print("    - 구간별로 **2023~26 만 높으면** 최근 호황 탓이다")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_238-2차_대형주반도체확인.txt")

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
