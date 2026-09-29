#!/usr/bin/env python3
r"""
insider_screen.py — **임원 매수 · 대량보유 증가가 쓸 만한 신호인가** 1차 선별 (2026-09-29)

사용자: 「임원 매매·대량보유 자료가 우리한테 유의미하다면 수집해야하고, 무의미하면 생략해도 되지!」

## 왜 「1차 선별」인가
자료가 **2024-09 ~ 2026-09 (약 2년)** 뿐이다. 우리 판정(11년 자본 시뮬 + 앞/뒤 걷기)은
앞 기간(2010~2020)에 자료가 없어 **못 한다.** 그래서 먼저 싸게 묻는다:
  「그 공시가 난 종목이, 같은 날 산 **시장 평균보다** 그 뒤 20·40거래일에 더 올랐나」
  · 2년 동안에도 **아무 차이가 없으면** → 2010~2023 을 모을 까닭이 없다 → **생략**
  · 차이가 **뚜렷하고 해마다 같은 쪽**이면 → 모아서 11년 판으로 제대로 잰다 → **수집**
⚠️ 1차 선별을 통과해도 「우리 규칙에 보탬이 된다」는 뜻은 **아니다** — 그건 11년 판에서 가린다.

## 사건
  A 임원 순매수 — 한 종목·한 접수일의 `증감`(주식 수) 합이 + 인 날 (등기임원만 따로도)
  B 대량보유 증가 — `증감지분율` ≥ +1.0%p 인 보고
## 수익
  접수일 **다음 거래일 종가**에 샀다고 친다 (접수가 장 뒤일 수 있어 그날 종가는 미래를 본다).
  20·40거래일 뒤 종가까지. **초과 = 그 종목 − 같은 날 전 종목 평균.**
## 판정 (미리 정한 선 · 사용자 확인 필요 [[judge-criteria-need-user-check]])
  n ≥ 200 · 20일 초과 평균 ≥ +1.0%p · **해마다(2024·2025·2026) 모두 +** → 「수집 권함」
  아니면 「생략 권함」

쓰기: python scripts/insider_screen.py [--out 결과.txt]
"""
import bisect
import glob
import io
import json
import os
import statistics as st
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
_DATA = os.path.join(os.path.dirname(_HERE), "data")

import omni_lab as O  # noqa: E402


def _수(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def 사건들():
    임원, 임원등기, 대량 = defaultdict(float), defaultdict(float), set()
    for f in glob.glob(os.path.join(_DATA, "dart-exec", "*.json")):
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        c = str(j.get("종목") or os.path.basename(f)[:6]).zfill(6)
        for r in j.get("이력") or []:
            d, g = str(r.get("접수일") or "").replace("-", ""), _수(r.get("증감"))
            if len(d) != 8 or g is None:
                continue
            임원[(c, d)] += g
            if "등기임원" == str(r.get("등기") or "").strip():
                임원등기[(c, d)] += g
    for f in glob.glob(os.path.join(_DATA, "dart-major", "*.json")):
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        c = str(j.get("종목") or os.path.basename(f)[:6]).zfill(6)
        for r in j.get("이력") or []:
            d, p = str(r.get("접수일") or "").replace("-", ""), _수(r.get("증감지분율"))
            if len(d) == 8 and p is not None and p >= 1.0:
                대량.add((c, d))
    return ({k for k, v in 임원.items() if v > 0},
            {k for k, v in 임원등기.items() if v > 0},
            대량)


def main():
    _out = None
    if "--out" in sys.argv:
        _out = sys.argv[sys.argv.index("--out") + 1]
    줄 = []

    def 찍(s=""):
        print(s)
        줄.append(s)

    찍("=" * 100)
    찍("  임원 매수 · 대량보유 증가 — 1차 선별 (2024-09 ~ 2026-09 · 약 2년)")
    찍("=" * 100)
    A, A등, B = 사건들()
    찍(f"  사건 — 임원 순매수 {len(A):,} · 그중 등기임원 {len(A등):,} · 대량보유 +1%p↑ {len(B):,}")

    주가 = O.krx한번읽기()[0]              # {날: {코드: (수정종가, 시총, 거래대금)}}
    날 = sorted(주가)
    자리 = {d: i for i, d in enumerate(날)}
    찍(f"  주가 {날[0]} ~ {날[-1]} · {len(날):,}거래일")

    평균 = {}

    def 시장(i, n):
        k = (i, n)
        if k not in 평균:
            a, b = 주가.get(날[i]) or {}, 주가.get(날[i + n]) or {}
            rs = [(b[c][0] / a[c][0] - 1) * 100 for c in a
                  if c in b and a[c][0] and a[c][0] > 0 and b[c][0]]
            평균[k] = st.mean(rs) if rs else None
        return 평균[k]

    def 재기(이름, 사건):
        for n in (20, 40):
            초 = defaultdict(list)
            for c, d in 사건:
                # 접수일 **다음 거래일** — 그날 종가는 장 뒤 공시면 미래다
                i = bisect.bisect_right(날, d)
                if i + n >= len(날):
                    continue
                a, b = (주가.get(날[i]) or {}).get(c), (주가.get(날[i + n]) or {}).get(c)
                m = 시장(i, n)
                if not a or not b or not a[0] or a[0] <= 0 or m is None:
                    continue
                초[날[i][:4]].append((b[0] / a[0] - 1) * 100 - m)
            모두 = [x for v in 초.values() for x in v]
            if not 모두:
                찍(f"  {이름:<22} {n}일 — 자료 없음")
                continue
            해 = " · ".join(f"{y} {st.mean(v):+.2f}%p(n{len(v)})" for y, v in sorted(초.items()))
            찍(f"  {이름:<22} {n}일  n={len(모두):>5,}  초과 평균 {st.mean(모두):+.2f}%p · "
              f"중앙 {st.median(모두):+.2f}%p · 시장보다 나은 비율 "
              f"{sum(1 for x in 모두 if x > 0) / len(모두) * 100:.1f}%")
            찍(f"  {'':<22}      해마다  {해}")
            if n == 20:
                ok = (len(모두) >= 200 and st.mean(모두) >= 1.0
                      and all(st.mean(v) > 0 for v in 초.values() if len(v) >= 20))
                찍(f"  {'':<22}      ⇒ " + ("⭐ **수집 권함** (2년에도 뚜렷 · 해마다 같은 쪽)" if ok
                                          else "생략 권함 (2년에 뚜렷한 차이가 없다)"))

    찍("")
    재기("임원 순매수", A)
    재기("임원 순매수 (등기임원)", A등)
    재기("대량보유 +1%p↑", B)
    찍("")
    찍("  ⚠️ 1차 선별이다 — 통과해도 「우리 규칙에 보탬」인지는 11년 판에서 가린다")
    찍("  ⚠️ 판정 선(n≥200 · +1.0%p · 해마다 +)은 내가 정했다 — 사용자 확인이 필요하다")
    if _out:
        io.open(_out, "w", encoding="utf-8").write("\n".join(줄) + "\n")


if __name__ == "__main__":
    main()
