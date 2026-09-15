#!/usr/bin/env python3
r"""
rebound_lab.py — **「반등이 시작된 뒤 산다」가 나은가** (2026-09-15 신설)

## 왜
사용자가 세 AI(클로드·제미나이·챗지피티)에게 우리 규칙을 물었더니 **셋 다** 같은 말을 했다:
```
「떨어지는 종목을 산다」에서 **「떨어진 뒤 반등하기 시작한 종목을 산다」**로
한 단계만 수정하면 훨씬 안정적이다
  · 볼린저 하단 이탈 후 **양봉 전환**(바닥 확인) 시 매수
  · 조건 충족 후 **첫 번째 거래량 터진 양봉**에 분할 매수
  · **5일선 회복 / 전일 고가 돌파 / 볼린저 밴드 재진입** 중 하나 -> 매수
```

## 우리가 이미 아는 것 — 방향은 **반대**다
```
161차 C절 「언제 사나」   그날 시가 60.1%  ->  다음날 58.7%  ->  사흘 뒤 55.1%
buy-dips-not-rallies    「오른 걸 산다」 41.1% (바탕 43.5% 보다도 나쁘다 · 여섯 시험)
sell-at-target-...      매도도 「회복 신호로 팔면 돈이 반 난다」
```
⚠️ **그런데 우리가 잰 것은 「무조건 늦추기」다.** 셋이 말한 것은 **조건부**다 —
   반등 신호가 뜨면 사고, **안 뜨면 아예 안 산다.** 기회를 버리는 대신 칼날을 피한다.
   성격이 달라서 **직접 재야 한다.** [[evidence-before-rules]]

## 재는 법 — 161차 C절과 **나란히 놓이게**
같은 사건에 매수 시점만 바꾼다. 잣대도 같다(건수 · 1년에 · 이김% · 평균).
```
지금        신호일 다음 날 **시가**에 산다
㉮ 볼린저 재진입   종가가 볼린저 -1σ 위로 올라온 날 -> **그 다음 날 시가**
㉯ 5일선 회복     종가가 5일 평균 위로 -> 다음 날 시가
㉰ 전일 고가 돌파  그날 고가가 전날 고가보다 높음 -> 다음 날 시가
㉱ 양봉          종가 > 시가 -> 다음 날 시가
㉲ 양봉 + 거래량   양봉이면서 거래량이 20일 평균의 1.5배 이상
```
⚠️ **반등을 확인하려면 종가를 봐야 한다.** 그래서 산 날은 **확인한 날의 다음 날**이다 —
   최소 하루가 더 늦는다. 그 대가를 치르고도 나은지가 이 시험의 질문이다.
⚠️ `최대` 일 안에 신호가 안 오면 **그 사건은 버린다**(안 산다). 기회가 얼마나 주는지가
   결과의 절반이다 — 사용자 1순위는 **기회**다.

쓰는 법:
    python scripts\rebound_lab.py
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import rule_def as R  # noqa: E402
# ⭐ 공시·컨센서스·뉴스 표는 `newmat` 이 이미 읽는다 — 다시 안 쓴다
import newmat  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_시작 = "20160401"
_비용 = 0.26
_최대 = 10          # 신호를 며칠까지 기다리나
_기간들 = (5, 20, 40)


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    print(f"  거래일 {len(날):,}일", flush=True)
    기본, 재무 = O._기본(), 연간재무()

    # ── 종목별 종가·시가·고가·거래량을 날 순서로 ────────────────
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    시계, 고계, 량계 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                량 = float(v.get("거래량") or 0)
            except (TypeError, ValueError, KeyError):
                continue
            if 종c <= 0:
                continue
            시계.setdefault(c, {})[d["기준일"]] = 시
            고계.setdefault(c, {})[d["기준일"]] = 고
            량계.setdefault(c, {})[d["기준일"]] = 량

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

    # ── 사건 = **지금 규칙(기존 갈래)** 을 통과한 것 ─────────────
    #    ⚠️ 섹터·시장 갈래는 안 건다 — 여기서 묻는 것은 **진입 시점**이지
    #       어느 종목을 고르냐가 아니다. 161차 C절과 같은 바탕이어야 견준다
    print("  사건 모으는 중...", flush=True)
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        if 날[i + 1] < _시작:
            continue
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            _시억, _대억 = 시총 / 1e8, 대금 / 1e8
            if (_시억 < R.시총하한억 or _시억 >= R.시총상한억
                    or _대억 < R.대금하한억):
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= R.잉여금하한
                    and fm.get("부채비율", 9e9) <= R.부채상한
                    and (fm.get("흑자") == 1.0 or not R.흑자필수)):
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250:
                continue
            sq = 종계[code]
            if sq[kk - 20] <= 0:
                continue
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if not (볼 <= R.볼린저문턱 and 낙 <= R.낙폭20문턱):
                continue
            사건.append({"i": i, "code": code, "kk": kk})
    print(f"  사건 {len(사건):,}건", flush=True)

    # ── 사건 재료 (공시·컨센서스·뉴스) ──────────────────────────
    #    ⚠️ 어젯밤 재료는 **신호일까지** 봤다. 여기는 **빠진 뒤**를 본다
    print("  공시·컨센서스·뉴스 읽는 중...", flush=True)
    _공시 = newmat._공시시각표(날)
    _컨 = newmat._컨센서스표()
    _뉴 = newmat._뉴스표()
    print(f"    공시 {len(_공시):,}일 · 컨센서스 {len(_컨):,}종목 · "
          f"뉴스 {len(_뉴):,}종목", flush=True)
    해수 = max(len([d for d in 날 if d >= _시작]) / 245, 0.1)

    # ── 반등 신호 ───────────────────────────────────────────────
    def _볼린저(code, k):
        sq = 종계[code]
        if k < 20 or k >= len(sq):
            return None
        s20 = st.mean(sq[k - 19:k + 1])
        sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
        return (sq[k] - s20) / (2 * sd)

    def 신호(방식, code, k, d8, 앞d8):
        """그날 **종가까지 보고** 반등이 시작됐나"""
        sq = 종계[code]
        if k >= len(sq):
            return False
        if 방식 == "볼린저재진입":
            v = _볼린저(code, k)
            return v is not None and v > R.볼린저문턱
        if 방식 == "5일선회복":
            if k < 5:
                return False
            return sq[k] > st.mean(sq[k - 4:k + 1])
        if 방식 == "전일고가돌파":
            a = (고계.get(code) or {}).get(d8)
            b = (고계.get(code) or {}).get(앞d8)
            return bool(a and b and a > b)
        if 방식 == "양봉":
            o = (시계.get(code) or {}).get(d8)
            return bool(o and sq[k] > o)
        # ── 여기부터 **사건 신호** (사용자 지적) ──────────────
        if 방식 == "공시":
            중, 후, 챙 = (_공시.get(d8) or {}).get(code, (0, 0, 0))
            return (중 + 후) >= 1
        if 방식 == "챙길공시":
            중, 후, 챙 = (_공시.get(d8) or {}).get(code, (0, 0, 0))
            return 챙 >= 1
        if 방식 == "장중공시":
            중, 후, 챙 = (_공시.get(d8) or {}).get(code, (0, 0, 0))
            return 중 >= 1
        if 방식 in ("새리포트", "목표주가올림"):
            # ⚠️⚠️ `_컨센서스표` 는 종목 -> **[(날짜8, 목표주가, 의견점수), …] 리스트**다.
            #    `_뉴스표`(3벌 묶음)와 **모양이 다르다** — 2026-09-15 에
            #    `ds, 목, 의 = t` 로 풀다 `ValueError: too many values to unpack` 로
            #    판이 죽었다. 같은 파일에서 온 표라도 **모양을 확인하고 쓴다**
            벌 = _컨.get(code)
            if not 벌:
                return False
            _자 = [q for q, z in enumerate(벌) if z[0] == d8]
            if not _자:
                return False
            if 방식 == "새리포트":
                return True
            # 목표주가올림 — 그 전 리포트보다 높은 목표가
            q = _자[-1]
            이번 = 벌[q][1]
            앞 = [벌[w][1] for w in range(q) if 벌[w][1]]
            return bool(이번 and 앞 and 이번 > 앞[-1])
        if 방식 in ("뉴스", "호재뉴스"):
            t = _뉴.get(code)
            if not t:
                return False
            ds, 호, 악 = t
            _자 = [q for q, z in enumerate(ds) if z == d8]
            if not _자:
                return False
            return True if 방식 == "뉴스" else any(호[w] > 0 for w in _자)
        if 방식 == "양봉+거래량":
            o = (시계.get(code) or {}).get(d8)
            if not (o and sq[k] > o) or k < 20:
                return False
            벌 = [(량계.get(code) or {}).get(날[j]) for j in range(k - 20, k)]
            벌 = [z for z in 벌 if z]
            이 = (량계.get(code) or {}).get(d8)
            return bool(벌 and 이 and 이 >= (sum(벌) / len(벌)) * 1.5)
        return False

    def 수익(code, 산자리, n):
        """산자리 **시가**에 사서 n 거래일 뒤 종가에 판다"""
        sq = 종계[code]
        k = (자리.get(code) or {}).get(날[산자리])
        if k is None:
            return None
        o = (시계.get(code) or {}).get(날[산자리])
        if not o or o <= 0:
            return None
        j = 산자리 + n
        if j >= len(날):
            return None
        k2 = (자리.get(code) or {}).get(날[j])
        if k2 is None:
            return None
        return (sq[k2] / o - 1) * 100 - _비용

    def 재기(라, 사는자리, 시작="00000000"):
        """사는자리(x) -> 산 날 자리 또는 None. `시작` 부터의 사건만 센다"""
        벌 = {n: [] for n in _기간들}
        산것 = 0
        늦음 = []
        _대상 = [x for x in 사건 if 날[x["i"]] >= 시작]
        _해 = max(len([d for d in 날 if d >= max(시작, _시작)]) / 245, 0.1)
        for x in _대상:
            j = 사는자리(x)
            if j is None:
                continue
            산것 += 1
            늦음.append(j - (x["i"] + 1))
            for n in _기간들:
                v = 수익(x["code"], j, n)
                if v is not None:
                    벌[n].append(v)
        줄 = f"  {라:<26}{산것:>9,}{산것 / _해:>8,.0f}"
        for n in _기간들:
            a = 벌[n]
            if len(a) < 80:
                줄 += f"{'-':>9}{'-':>9}"
            else:
                줄 += (f"{sum(1 for z in a if z > 0) / len(a) * 100:>8.1f}%"
                       f"{sum(a) / len(a):>+9.2f}")
        줄 += f"{(st.mean(늦음) if 늦음 else 0):>8.1f}일"
        print(줄, flush=True)
        return 산것

    print("\n" + "=" * 112)
    print("  **반등이 시작된 뒤 사면 나은가** — 세 AI 가 공통으로 말한 한 가지")
    print(f"  사건 {len(사건):,}건 · {해수:.1f}년 · 신호를 **최대 {_최대}일** 기다린다")
    print("  ⚠️ 신호가 안 오면 **안 산다** — 기회가 얼마나 주는지가 결과의 절반이다")
    print("=" * 112)
    머 = (f"  {'설정':<26}{'산 것':>9}{'1년에':>8}"
          f"{'5일 이김':>9}{'평균':>9}{'20일 이김':>9}{'평균':>9}"
          f"{'40일 이김':>9}{'평균':>9}{'늦음':>9}")
    print(머)

    def _사는자리만들기(방식):
        def _f(x):
            for h in range(0, _최대):
                k = x["kk"] + h
                j = x["i"] + h
                if j + 1 >= len(날) or k >= len(종계[x["code"]]):
                    return None
                if 신호(방식, x["code"], k, 날[j], 날[j - 1] if j else 날[0]):
                    return j + 1
            return None
        return _f

    # ⚠️⚠️ **기간을 맞춰 견딘다** — 자료가 있는 기간이 제각각이다.
    #    공시 2010~ · 컨센서스 2020~ · 뉴스 **2025-09~ (1년뿐)**.
    #    그냥 한 표에 놓으면 **기간 차이를 신호 차이로 읽는다.**
    #    묶음마다 「지금」을 **같은 기간으로 잘라** 맨 위에 다시 찍는다
    묶음들 = (("기술적 신호 (전 기간)", "00000000",
               ("볼린저재진입", "5일선회복", "전일고가돌파", "양봉", "양봉+거래량")),
              ("⭐ 공시 (2010~ · 전 기간)", "00000000",
               ("공시", "챙길공시", "장중공시")),
              ("⭐ 컨센서스 (2020~ 만)", "20200101",
               ("새리포트", "목표주가올림")),
              ("⭐ 뉴스 (2025-09~ · 1년뿐)", "20250903",
               ("뉴스", "호재뉴스")))
    for 제목, 시작, 방식들 in 묶음들:
        print(f"\n  ── {제목} ──")
        if 시작 > "00000000":
            print(머)
        재기(f"[견줌] 지금", lambda x: x["i"] + 1, 시작)
        for 방식 in 방식들:
            재기(방식, _사는자리만들기(방식), 시작)

    print("\n  읽는 법")
    print("    - **산 것**이 줄면 그만큼 **기회를 버린 것**이다 (사용자 1순위)")
    print("    - 「늦음」은 신호일 다음 날 대비 **며칠 늦게 샀나**")
    print("    - 161차 C절(무조건 늦추기): 그날 시가 60.1% → 다음날 58.7% → 사흘 뒤 55.1%")
    print("      ⇒ 조건부가 그보다 나으면 **기다린 값어치가 있다**는 뜻이다")
    print("    - ⚠️ 여기는 **이길 확률**이다. 이걸 지나면 **자본 시뮬 + 4관문**으로 넘긴다")
    print("=" * 112)
    return 0


if __name__ == "__main__":
    sys.exit(main())
