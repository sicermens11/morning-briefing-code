#!/usr/bin/env python3
r"""
delist_lab.py — **158차 · 상장폐지가 우리 성적을 얼마나 부풀렸나** (2026-09-08)

## 왜 만들었나
```
시뮬:  끝 = 주가[날[j]].get(code)
      if not 끝: return (None, None)     <- 그 거래를 **없던 것으로** 친다
```
산 뒤에 종목이 사라지면 손실이 아니라 **무효**가 됐다.
실측: 3,678종목 중 **904개(25%)가 중간에 사라졌다**

## ⚠️ 그런데 규칙 사례를 다시 내보니 숫자가 **하나도 안 변했다**
```
              고치기 전     고친 뒤
전체 97건 · 승률 85.6% · 평균 +17.83% · 가장 나쁨 -19.41%   ← 똑같다
```
**재무 관문(잉여금 30%↑ · 부채 80%↓ · 흑자)이 상장폐지를 막고 있었던 것이다.**

## 그래서 이 시험이 답할 것
```
① 재무를 **뺀** 후보는 상장폐지를 얼마나 밟나
② 조건별로 (볼린저만 · 낙폭만 · 크기만) 얼마나 밟나
③ 그 거래들을 -50% 로 세면 이길 확률·평균 수익이 얼마나 내려가나
   -> **어떤 옛 시험이 오염됐는지** 이걸로 가른다
```
⚠️ 자본 시뮬을 쓰지 않는다. 155차 잣대(1년에 몇 개 · 이길 확률 · 평균)만 쓴다

쓰는 법:
    python scripts\delist_lab.py
"""
import io
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_잉여금, _부채 = 30.0, 80.0


def main():
    print("  주가 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    사라짐 = O.사라진종목(주가, 날)
    자리 = {d: i for i, d in enumerate(날)}
    print(f"  거래일 {len(날):,} · 중간에 사라진 종목 **{len(사라짐):,}개**",
          flush=True)

    기본, 재무 = O._기본(), 연간재무()

    def 재무값(code, d8):
        줄 = 재무.get(code)
        if not 줄:
            return None
        m = None
        for 적용, v in 줄:
            if 적용 <= d8:
                m = v
            else:
                break
        return m

    # ── 종목별 종가 계열 ──
    print("  종가 계열 만드는 중...", flush=True)
    종계, 종날 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            종날.setdefault(c, []).append(d)

    # ── 후보 모으기 (조건을 안 걸고 값만 붙인다) ──
    print("  후보 모으는 중 (조건 안 검)...", flush=True)
    사건 = []
    for c, sq in 종계.items():
        ds = 종날[c]
        폐 = 사라짐.get(c)
        for k in range(260, len(sq) - 1):
            d1 = ds[k]
            if d1 < _시작:
                continue
            c1 = sq[k]
            if c1 <= 0 or sq[k - 20] <= 0:
                continue
            v = 주가[d1].get(c)
            if not v:
                continue
            시총억, 대금억 = v[1] / 1e8, v[2] / 1e8
            m = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            fm = 재무값(c, d1) or {}
            사건.append({
                "code": c, "i": 자리[d1], "종가": c1,
                "볼": (c1 - m) / (2 * sd),
                "낙": (c1 / sq[k - 20] - 1) * 100,
                "시총억": 시총억, "대금억": 대금억,
                "재통과": 1.0 if (fm.get("잉여금비율", -9e9) >= _잉여금
                                and fm.get("부채비율", 9e9) <= _부채
                                and fm.get("흑자") == 1.0) else 0.0,
                "폐지": 자리.get(폐) if 폐 else None,
            })
    print(f"  후보 {len(사건):,}건\n", flush=True)

    끝i = len(날) - 1

    def 수익(x, n):
        r"""n일 뒤 수익. 사라졌으면 **-50% 로 센다** / 옛 방식은 None"""
        i, j = x["i"], x["i"] + n
        if j > 끝i:
            return None, None
        a = 주가[날[i]].get(x["code"])
        b = 주가[날[j]].get(x["code"])
        if not a or a[0] <= 0:
            return None, None
        if b:
            r = (b[0] / a[0] - 1) * 100 - _비용
            return r, r
        # 자료가 없다 — 사라진 종목인가?
        if x["폐지"] is not None and x["폐지"] >= i:
            return None, O.폐지손실 - _비용   # 옛=지움 / 새=-50%
        return None, None

    기간들 = (5, 20, 40, 90)
    print("  수익률 붙이는 중...", flush=True)
    for x in 사건:
        for n in 기간들:
            옛, 새 = 수익(x, n)
            x[f"옛{n}"], x[f"새{n}"] = 옛, 새

    해수 = 10.4
    줄1 = (f"  {'설정':<30}{'건수':>9}{'1년에':>7}"
           f"{'폐지밟음':>9}{'비율':>7}"
           f"{'옛 이김':>9}{'옛 평균':>9}{'새 이김':>9}{'새 평균':>9}{'차이':>8}")

    def 재기(라, fn, 기=20):
        칸 = [x for x in 사건 if fn(x)]
        n = len(칸)
        if n < 200:
            print(f"  {라:<30}{n:>9,}{'  표본 부족':>26}")
            return
        밟 = sum(1 for x in 칸 if x["폐지"] is not None and x["폐지"] >= x["i"])
        옛v = [x[f"옛{기}"] for x in 칸 if x[f"옛{기}"] is not None]
        새v = [x[f"새{기}"] for x in 칸 if x[f"새{기}"] is not None]
        if len(옛v) < 100 or len(새v) < 100:
            print(f"  {라:<30}{n:>9,}{'  표본 부족':>26}")
            return
        옛이 = sum(1 for z in 옛v if z > 0) / len(옛v) * 100
        새이 = sum(1 for z in 새v if z > 0) / len(새v) * 100
        옛평 = sum(옛v) / len(옛v)
        새평 = sum(새v) / len(새v)
        print(f"  {라:<30}{n:>9,}{n/해수:>7.0f}{밟:>9,}{밟/n*100:>6.2f}%"
              f"{옛이:>8.1f}%{옛평:>+9.2f}{새이:>8.1f}%{새평:>+9.2f}"
              f"{새평-옛평:>+8.2f}")

    # ⚠️ 한 글자 이름은 쓰지 않는다 — 위의 `재무` 딕셔너리를 덮어쓴다
    #    (메모리 no-one-letter-korean-names · 오늘만 여섯 번 당했다)
    def 재무통과(x): return x["재통과"] == 1.0
    def 크기통과(x): return 500 <= x["시총억"] < 2000
    def 대금통과(x): return x["대금억"] >= 1.0
    def 볼통과(x): return x["볼"] <= -1.0
    def 낙통과(x): return x["낙"] <= -10.0

    print("=" * 118)
    print("  158차 · 상장폐지를 손실로 세면 성적이 얼마나 내려가나")
    print("  옛 = 그 거래를 지움 (지금까지의 모든 시험)  ·  "
          f"새 = **{O.폐지손실:.0f}% 손실로 팜**")
    print("  ※ 20일 뒤 수익 기준")
    print("=" * 118)
    print(줄1)

    print("\n  ── A 조건을 하나씩 쌓으면 ──")
    재기("아무 종목·아무 날", lambda x: True)
    재기("볼린저 -1.0 만", 볼통과)
    재기("낙폭 -10% 만", 낙통과)
    재기("볼린저 + 낙폭", lambda x: 볼통과(x) and 낙통과(x))
    재기("+ 크기 500~2,000억", lambda x: 볼통과(x) and 낙통과(x) and 크기통과(x))
    재기("+ 거래대금 1억", lambda x: 볼통과(x) and 낙통과(x) and 크기통과(x) and 대금통과(x))
    재기("**+ 재무 (지금 규칙)**",
         lambda x: 볼통과(x) and 낙통과(x) and 크기통과(x) and 대금통과(x) and 재무통과(x))

    print("\n  ── B ⭐ 재무를 **빼면** 얼마나 달라지나 ──")
    재기("재무 있음 (지금 규칙)",
         lambda x: 볼통과(x) and 낙통과(x) and 크기통과(x) and 대금통과(x) and 재무통과(x))
    재기("재무 **없음**",
         lambda x: 볼통과(x) and 낙통과(x) and 크기통과(x) and 대금통과(x))
    재기("재무 못 지난 것만",
         lambda x: 볼통과(x) and 낙통과(x) and 크기통과(x) and 대금통과(x) and not 재무통과(x))

    print("\n  ── C 크기별 (재무 없이) ──")
    for 라, lo, hi in (("300억 미만", 0, 300), ("300~500억", 300, 500),
                       ("500~2,000억", 500, 2000),
                       ("2,000~1조", 2000, 10000), ("1조 이상", 10000, 9e9)):
        재기(f"시총 {라}",
             lambda x, a=lo, b=hi: 볼통과(x) and 낙통과(x) and a <= x["시총억"] < b)

    print("\n  ── D 낙폭이 깊을수록 위험한가 (재무 없이) ──")
    for 라, 문 in (("-10%", -10), ("-20%", -20), ("-30%", -30),
                   ("-40%", -40), ("-50%", -50)):
        재기(f"20일 낙폭 {라} 이하",
             lambda x, m=문: x["낙"] <= m and 크기통과(x) and 대금통과(x))

    print("\n  ── E 기간을 늘리면 (재무 없는 후보) ──")
    for 기 in 기간들:
        print(f"\n   [{기}일 뒤]")
        재기("재무 없음", lambda x: 볼통과(x) and 낙통과(x) and 크기통과(x) and 대금통과(x), 기)
        재기("재무 있음",
             lambda x: 볼통과(x) and 낙통과(x) and 크기통과(x) and 대금통과(x) and 재무통과(x), 기)

    print("\n" + "=" * 118)
    print("  읽는 법")
    print("    - **폐지 비율**이 0.0%에 가까우면 그 조건으로 한 시험은 **안전하다**")
    print("    - 「차이」가 -0.5%p 보다 크면 그 시험은 **다시 돌려야 한다**")
    print("    - 재무 관문이 상장폐지를 막는지 B 에서 갈린다")
    print("=" * 118)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      # ⚠ 다른 값으로 다시 돌릴 때 결과를 덮어쓰지 않는다
                      os.environ.get("LAB_OUT") or "2026-09-08_158차_상장폐지영향.txt")

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
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
