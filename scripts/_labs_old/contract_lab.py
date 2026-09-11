#!/usr/bin/env python3
r"""
contract_lab.py — **248차 · 계약 금액** (2026-09-11 신설)

## 오늘 처음 쓸 수 있게 된 재료
```
2026-09-10 까지: `data/contract` 를 읽는 곳이 **자기 자신뿐**이었다.
                시험에 **한 번도 안 썼다**
2026-09-11: 금액을 못 뽑던 원인을 찾았다 — **DART 공시 원문이 EUC-KR** 인데
            `decode("utf-8")` 로 읽어 **한글이 전부 깨졌다**
            -> 「계약금액」이라는 글자를 찾을 수가 없었다
고친 뒤: 금액 확보율 **26% -> 99%** (24,705건)
```

## 왜 값어치가 있나
```
「15억 계약」과 「1조 계약」은 **완전히 다른데** 지금은 둘 다 「호재 공시」 한 덩어리다.
`계약금액 ÷ 시가총액` 이 **진짜 신호 강도**다 —
시총 500억 회사의 300억 계약은 시총 2,000억 회사의 300억 계약과 다르다
```

## 재는 것
```
A ⭐⭐⭐ **계약금액 ÷ 시총** 구간별 (1% ~ 100%↑)
B ⭐⭐⭐ 지금 규칙·Ⓗ 와 **AND / OR**
C ⭐⭐  **며칠 안에** 공시됐나 (1·5·20·60일)
D ⭐⭐  **매출 대비 비중**(공시에 적힌 값)
```

## ⚠️ 이 시험이 보는 범위
```
크기   시총 300억 이상 — 상한 없음      방향   안 걸었다
기간   2016-01-01 ~                  견줌   전체 바탕
⚠️⚠️ 계약 자료는 **2022년부터만** 있다. 2016~2021 을 넣으면
   「계약 없음」 바탕에 **안 받아온 6년**이 섞여 숫자가 통째로 망가진다
```

쓰는 법:
    python scripts\contract_lab.py
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import lab_header as LH  # noqa: E402

# ⚠️⚠️ **2026-09-11 · 1차 결과를 버리고 다시 돌린다.**
#    머리말엔 「2016-01-01 ~」이라고 찍었는데 **계약 자료는 2022년부터만 있다**
#    (2016·2018·2019·2021 = **0건**, 2017 = 154건, 2020 = 38건).
#    그래서 「계약 없음 4,269,282건」 바탕에 **2016~2021 전체**가
#    「계약 없는 날」로 섞여 들어갔다 — 실제로는 **안 받아온 것**이다.
#    구간별 칸이 두 개만 찍힌 것도 2016~2019 에 표본이 없어서였다
_시작 = "20220101"
_비용 = 0.26


def 계약읽기():
    r"""{코드: [(공시일, 금액, 매출대비)]} — 금액이 **있는 것만**"""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "contract", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for rc, v in (d.get("건") or {}).items():
            금 = v.get("금액")
            if 금 is None:
                continue
            c = str(v.get("코드") or "")
            d8 = str(v.get("날짜") or "")
            if c and len(d8) == 8:
                out.setdefault(c, []).append((d8, float(금),
                                              v.get("매출대비pct")))
    # ⚠️ **날짜로만** 정렬한다. 그냥 sort() 하면 같은 날짜일 때
    #    둘째·셋째 칸을 비교하다 `매출대비`가 None 과 float 이 섮여 터졌다
    #    (2026-09-11 — 189차 컨센서스에서 **똑같은 일**을 겪었다)
    for c in out:
        out[c].sort(key=lambda z: z[0])
    return out


def main():
    LH.찍기(
        차수="248차", 이름="계약 금액 (오늘 처음 쓰는 재료)",
        크기="시총 300억 이상 — 상한 없음", 방향="안 걸었다",
        기간="2022-01-01 ~  (계약 자료가 실제로 있는 구간만)",
        재료=["계약 공시", "주가·시총·거래대금"],
        안본것=["자사주", "증자", "수급", "뉴스"],
        견줌="전체 바탕",
        판정="바탕 +5%p · 세 구간 같은 방향 · 1년 10건 이상",
    )

    계약 = 계약읽기()
    n = sum(len(v) for v in 계약.values())
    print(f"  계약 {len(계약):,}종목 · **{n:,}건** (금액 있는 것만)", flush=True)

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
        내계약 = 계약.get(c) or []
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
            d8 = 날[i]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            x = {"해": d8[:4], "_20": 뒤, "시억": 시억,
                 "볼20": 볼20, "낙20": 낙20,
                 "몫1": None, "몫5": None, "몫20": None, "몫60": None,
                 "매출대비": None}
            # 창마다 **가장 큰 계약**의 시총 대비 비율
            for 창, 키 in ((1, "몫1"), (5, "몫5"), (20, "몫20"), (60, "몫60")):
                앞 = 날[max(0, i - 창)]
                최 = None
                for zd, z금, z비 in 내계약:
                    if 앞 <= zd <= d8 and (최 is None or z금 > 최[0]):
                        최 = (z금, z비)
                if 최:
                    x[키] = 최[0] / 시원 * 100
                    if 키 == "몫60" and 최[1] is not None:
                        x["매출대비"] = 최[1]
            사건.append(x)
    print(f"  사건 **{len(사건):,}건**", flush=True)
    for 키 in ("몫1", "몫5", "몫20", "몫60"):
        붙 = sum(1 for x in 사건 if x[키] is not None)
        print(f"    {키} 붙은 것 {붙:>8,} ({붙/len(사건)*100:>5.2f}%)")

    해수 = len(날) / 245
    구간 = (("2022", "2022", "2022"), ("2023~2024", "2023", "2024"),
            ("2025~2026", "2025", "2026"))

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
            print(f"  {이름:<32}{nn:>9,}{'표본 부족':>17}")
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
        print(f"  {이름:<32}{r[2]:>9,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
              f"{r[1]:>+8.2f}{차:>+8.1f}p  [{방말}]{표}")

    머 = (f"  {'재료':<32}{'건수':>9}{'1년에':>7}{'이김':>8}{'평균':>8}"
          f"{'바탕대비':>9}  [구간별]")

    print("\n  ── A ⭐⭐⭐ **계약금액 ÷ 시총** (60일 안 가장 큰 계약) ──")
    print("     「15억 계약」과 「1조 계약」을 처음으로 **구분**한다")
    print(머)
    for a, b in ((0, 1), (1, 3), (3, 5), (5, 10), (10, 20), (20, 50),
                 (50, 100), (100, 99999)):
        재기(f"계약 ÷ 시총 {a}~{b}%",
             lambda x, p=a, q=b: (x["몫60"] is not None and p <= x["몫60"] < q))
    재기("계약 **없음** (60일 안)", lambda x: x["몫60"] is None)

    print("\n  ── B ⭐⭐ **며칠 안에 공시됐나** (계약 ÷ 시총 10%↑) ──")
    print(머)
    for 키, 라 in (("몫1", "1일"), ("몫5", "5일"), ("몫20", "20일"), ("몫60", "60일")):
        재기(f"{라} 안 · 10%↑ 계약",
             lambda x, k=키: x[k] is not None and x[k] >= 10)
        재기(f"{라} 안 · 30%↑ 계약",
             lambda x, k=키: x[k] is not None and x[k] >= 30)

    print("\n  ── C ⭐⭐⭐ **지금 규칙과 같이** ──")
    지금 = [x for x in 사건 if (x["볼20"] is not None and x["볼20"] <= -1.0
                                and x["낙20"] is not None and x["낙20"] <= -10)]
    기지금 = 점(지금)
    if 기지금:
        print(f"     [견줌] 지금 규칙 {기지금[2]:,}건 · 이김 {기지금[0]:.1f}%")
        print(머)
        for 문 in (3, 10, 30):
            재기(f"지금 AND 계약 {문}%↑ (60일)",
                 lambda x, a=문: x["몫60"] is not None and x["몫60"] >= a, 지금, 기지금)
        재기("지금 AND 계약 **있음**",
             lambda x: x["몫60"] is not None, 지금, 기지금)
        재기("지금 **빼기** 계약 있음",
             lambda x: x["몫60"] is None, 지금, 기지금)

    print("\n  ── D ⭐ **매출 대비 비중** (공시에 적힌 값) ──")
    print(머)
    for a, b in ((0, 10), (10, 30), (30, 50), (50, 100), (100, 99999)):
        재기(f"매출 대비 {a}~{b}%",
             lambda x, p=a, q=b: (x["매출대비"] is not None
                                  and p <= x["매출대비"] < q))

    LH.끝맺기(0, 0, ["A 계약÷시총", "B 며칠 안", "C 지금 규칙과", "D 매출 대비"])
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-11_248차_계약금액.txt")

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
