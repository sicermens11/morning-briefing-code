#!/usr/bin/env python3
r"""
capital_lab.py — **244차 · 증자·감자·자사주** (2026-09-10 밤 신설)

## 236차가 왜 0건이었나
```
`dart-capital/{종목}.json` 의 **「받은날」을 공시일로 착각**했다.
그건 **수집한 날**이다. 실제 공시일은 각 항목 안의 **`rcept_no` 앞 8자리**다

실제 짜임새:
  {"종목":"000020", "받은날":..., "유상증자":[], "무상증자":[],
   "감자":[], "자사주취득":[{"rcept_no":"20170720000271", ...}], "자사주처분":[]}
  -> 내용 있는 파일 **2,449 / 3,988**
```

## 재는 것 (전부 **단독**부터 — 한 번도 안 쟀다)
```
A ⭐⭐⭐ **유상증자** — 흔히 악재라고 한다. 정말인가
B ⭐⭐⭐ **무상증자** — 흔히 호재라고 한다
C ⭐⭐⭐ **자사주 취득** — 오늘 계약에서 분리한 것과 같은 재료
D ⭐⭐  **감자** · **자사주 처분**
E ⭐⭐  지금 규칙 **AND / 빼기** — 같이 쓰면
```

## ⚠️ 이 시험이 보는 범위
```
크기   시총 300억 이상 — 상한 없음      방향   안 걸었다
기간   2016-01-01 ~                  견줌   전체 바탕
창     공시 뒤 **60일 안**이면 「있었다」로 본다
```

쓰는 법:
    python scripts\capital_lab.py
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
_창 = 60          # 공시 뒤 며칠까지 「있었다」로 볼까
_종류 = ("유상증자", "무상증자", "유무상증자", "감자", "자사주취득", "자사주처분")


def 자본이력():
    r"""{코드: {종류: [공시일…]}} — ⚠️ 공시일은 **rcept_no 앞 8자리**"""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-capital", "*.json"))):
        code = os.path.basename(f)[:-5]
        if not code.isdigit():
            continue
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for k in _종류:
            for x in (j.get(k) or []):
                rc = str(x.get("rcept_no") or "")
                if len(rc) >= 8 and rc[:8].isdigit():
                    out.setdefault(code, {}).setdefault(k, []).append(rc[:8])
    for c in out:
        for k in out[c]:
            out[c][k].sort()
    return out


def main():
    LH.찍기(
        차수="244차", 이름="증자·감자·자사주",
        크기="시총 300억 이상 — 상한 없음", 방향="안 걸었다",
        기간="2016-01-01 ~",
        재료=["유상증자·무상증자", "주가·시총·거래대금"],
        안본것=["수급", "뉴스", "계약 금액(정규식 고친 뒤)"],
        견줌="전체 바탕",
        판정="바탕 +5%p · 세 구간 같은 방향 · 1년 10건 이상",
    )

    이력 = 자본이력()
    n = sum(len(v) for d in 이력.values() for v in d.values())
    print(f"  자본 이력 {len(이력):,}종목 · **{n:,}건**", flush=True)
    셈 = {}
    for d in 이력.values():
        for k, v in d.items():
            셈[k] = 셈.get(k, 0) + len(v)
    for k in _종류:
        print(f"    {k:<10}{셈.get(k, 0):>8,}건")

    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일", flush=True)

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
        내이력 = 이력.get(c) or {}
        for k in range(120, len(vs)):
            시억 = vs[k][1] / 1e8
            if 시억 < 300 or vs[k][2] / 1e8 < 1.0:
                continue
            i = ii[k]
            if i + 20 >= len(날):
                continue
            c1 = 종[k]
            끝 = 주가[날[i + 20]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100 - _비용)
            d8 = 날[i]
            앞d8 = 날[max(0, i - _창)]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            x = {"해": d8[:4], "_20": 뒤, "시억": 시억,
                 "볼20": 볼20, "낙20": 낙20}
            for kk in _종류:
                벌 = 내이력.get(kk) or []
                x[kk] = any(앞d8 <= z <= d8 for z in 벌)
            사건.append(x)
    print(f"  사건 **{len(사건):,}건**", flush=True)
    for kk in _종류:
        붙 = sum(1 for x in 사건 if x[kk])
        print(f"    {kk:<10}붙은 것 {붙:>8,} ({붙/len(사건)*100:>5.2f}%)")

    해수 = len(날) / 245
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"))

    def 점(칸, 최소=120):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(v))

    바 = 점(사건)
    print(f"\n  ⭐ **바탕** {바[2]:,}건 · 이김 **{바[0]:.1f}%** · 평균 {바[1]:+.2f}%")

    def 재기(이름, fn, 칸0=None, 기=None):
        칸0 = 칸0 if 칸0 is not None else 사건
        기 = 기 or 바
        칸 = [x for x in 칸0 if fn(x)]
        r = 점(칸)
        if not r:
            nn = len([x for x in 칸 if x.get("_20") is not None])
            print(f"  {이름:<34}{nn:>9,}{'표본 부족':>17}")
            return
        방 = []
        for _, a, b in 구간:
            c1 = 점([x for x in 칸 if a <= x["해"] <= b], 40)
            b1 = 점([x for x in 칸0 if a <= x["해"] <= b], 40)
            if c1 and b1:
                방.append(c1[0] - b1[0])
        고름 = len(방) == 3 and all(v > 0 for v in 방)
        차 = r[0] - 기[0]
        쓸 = r[2] / 해수 >= 10
        표 = ("  ⭐ **된다**" if (고름 and 차 >= 5 and 쓸)
              else "  (1년 10건 미만)" if (고름 and 차 >= 5)
              else "  ~" if 차 >= 3 else "")
        방말 = " ".join(f"{v:+.0f}" for v in 방)
        print(f"  {이름:<34}{r[2]:>9,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
              f"{r[1]:>+8.2f}{차:>+8.1f}p  [{방말}]{표}")

    머 = (f"  {'재료':<34}{'건수':>9}{'1년에':>7}{'이김':>8}{'평균':>8}"
          f"{'바탕대비':>9}  [구간별]")

    print("\n  ── A~D ⭐⭐⭐ **종류마다 단독** (60일 안에 있었나) ──")
    print(머)
    for kk in _종류:
        재기(f"**{kk}** 있었다", lambda x, a=kk: x[a])
        재기(f"   └ {kk} **없었다**", lambda x, a=kk: not x[a])

    print("\n  ── E ⭐⭐ **지금 규칙과 같이** ──")
    지금 = [x for x in 사건 if (x["볼20"] is not None and x["볼20"] <= -1.0
                                and x["낙20"] is not None and x["낙20"] <= -10)]
    기지금 = 점(지금)
    if 기지금:
        print(f"     [견줌] 지금 규칙 {기지금[2]:,}건 · 이김 {기지금[0]:.1f}%")
        print(머)
        for kk in _종류:
            재기(f"지금 AND {kk}", lambda x, a=kk: x[a], 지금, 기지금)
            재기(f"지금 **빼기** {kk}", lambda x, a=kk: not x[a], 지금, 기지금)

    LH.끝맺기(0, 0, ["A~D 종류별 단독", "E 지금 규칙과 같이"])
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_244차_증자감자자사주.txt")

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
