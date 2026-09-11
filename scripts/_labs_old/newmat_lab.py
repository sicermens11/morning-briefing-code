#!/usr/bin/env python3
r"""
newmat_lab.py — **236차 · 안 써본 재료** (2026-09-10 신설)

## 「다음 순서」에 적어놓고 **안 만들었던 것**
```
233차 안 써본 재료 5개  -> 적어만 두고 넘어갔다. 여기서 만든다
```

## ⚠️ 두 번 잘못 말했다 — 정정한다
```
① 「분기 재무 값이 비어 있다」 -> **틀렸다.** 한 종목 매출액만 보고 말했다.
   표본 400개 중 **389개(97%)** 에 값이 있다
② 「분기 재무를 못 쓴다」    -> **반만 맞다.**
   `naver-quarter/` 는 **종목당 파일 하나 · 받은날 없음 · 최근 5분기뿐** 이라
   과거 시점에 무엇을 알 수 있었는지 모른다 -> **못 쓴다** (미리보기)
   `quarter-fin/` 은 **해x분기별 파일 48개 · 1,571~1,877종목** 이라
   **쓸 수 있다.** 이쪽을 쓴다
```

## 재는 것
```
A ⭐⭐⭐ **분기 실적 성장률** (전년 동기 대비 매출·영업이익)
B ⭐⭐  **유상증자 · 무상증자** (dart-capital)
C ⭐⭐  **공시 시각** — 장중(9~15:30) vs 장후 vs 밤 (kind-time)
D ⭐   **ETF** — 그 종목이 든 섹터 ETF 가 빠진 날 (etf-krx)
```

## ⚠️ 미리보기 막기 (분기 재무)
```
1분기(3월말) -> **5월 20일**부터 쓴다   반기(6월말) -> **8월 20일**
3분기(9월말) -> **11월 20일**          사업(12월말) -> **다음해 4월 1일**
(공시 기한 + 여유. 기한은 분기 45일 · 사업 90일이다)
```

## ⚠️ 이 시험이 보는 범위
```
크기   시총 300억 이상 — 상한 없음      방향   안 걸었다
기간   2016-01-01 ~                  견줌   전체 바탕
판정   바탕 +5%p · 세 구간 같은 방향 · 1년 10건 이상
```

쓰는 법:
    python scripts\newmat_lab.py
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

# 분기 -> (그 분기가 끝난 달, 쓸 수 있게 되는 날짜의 월일)
_적용 = {"1분기": ("03", "0520"), "반기": ("06", "0820"),
         "3분기": ("09", "1120"), "사업": ("12", None)}   # 사업은 다음해 0401


def 분기재무():
    r"""{코드: [(쓸수있는날, {항목}), ...]} — ⚠️ 공시 기한 뒤부터 쓴다."""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "quarter-fin", "*.json"))):
        base = os.path.basename(f)[:-5]
        if "_" not in base:
            continue
        해, 분 = base.split("_", 1)
        if not 해.isdigit() or 분 not in _적용:
            continue
        _, 월일 = _적용[분]
        쓸날 = f"{int(해) + 1}0401" if 월일 is None else f"{해}{월일}"
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for c, v in (j.get("종목") or {}).items():
            if not isinstance(v, dict) or not v:
                continue

            def g(k):
                x = v.get(k)
                return float(x) if isinstance(x, (int, float)) else None
            out.setdefault(c, []).append((쓸날, 해, 분, {
                "매출": g("매출액"), "영익": g("영업이익"),
                "순익": g("당기순이익(손실)")}))
    for c in out:
        out[c].sort()
    return out


def 증자읽기():
    r"""{코드: [(받은날, 유상, 무상)]}"""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-capital", "*.json"))):
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        c = str(j.get("종목") or "")
        받 = str(j.get("받은날") or "")
        if not c or not 받:
            continue
        out.setdefault(c, []).append(
            (받, bool(j.get("유상증자")), bool(j.get("무상증자"))))
    for c in out:
        out[c].sort()
    return out


def main():
    LH.찍기(
        차수="236차", 이름="안 써본 재료 (분기실적·증자·공시시각)",
        크기="시총 300억 이상 — 상한 없음", 방향="안 걸었다",
        기간="2016-01-01 ~",
        재료=["분기 재무 (DART)", "유상증자·무상증자", "공시 시각",
              "주가·시총·거래대금"],
        안본것=["ETF (연결이 애매해 이번엔 뺐다)", "수급(235차)", "뉴스", "해외"],
        견줌="전체 바탕",
        판정="바탕 +5%p · 세 구간 같은 방향 · 1년 10건 이상",
    )

    주가 = O.수정주가(("시총", "거래대금"))
    날 = [d for d in sorted(주가) if d >= _시작]
    분재 = 분기재무()
    증자 = 증자읽기()
    print(f"  거래일 {len(날):,}일 · 분기재무 {len(분재):,}종목 · "
          f"증자 {len(증자):,}종목", flush=True)

    # 공시 시각 — 그날 밤(15:30 뒤) 공시가 있었나
    밤공시 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "kind-time", "*.json"))):
        d8 = os.path.basename(f)[:8]
        if d8 < _시작:
            continue
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        시 = j.get("시각") or {}
        n밤 = sum(1 for v in 시.values()
                  if isinstance(v, str) and len(v) >= 5 and v[:2].isdigit()
                  and int(v[:2]) >= 16)
        밤공시[d8] = (len(시), n밤)
    print(f"  공시 시각 {len(밤공시):,}일", flush=True)

    종계, 있는날 = {}, {}
    자리 = {d: i for i, d in enumerate(날)}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(자리[d])

    def 분재값(code, d8):
        r"""그날 쓸 수 있는 **가장 최근 분기**와 **1년 전 같은 분기**."""
        벌 = 분재.get(code)
        if not 벌:
            return None, None
        지금, 작년 = None, None
        for 쓸날, 해, 분, m in 벌:
            if 쓸날 <= d8:
                지금 = (해, 분, m)
        if not 지금:
            return None, None
        해0, 분0, _ = 지금
        for 쓸날, 해, 분, m in 벌:
            if 분 == 분0 and int(해) == int(해0) - 1:
                작년 = (해, 분, m)
        return 지금, 작년

    print("  사건 만드는 중...", flush=True)
    사건 = []
    for c, vs in 종계.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        증 = 증자.get(c) or []
        for k in range(120, len(vs)):
            시억 = vs[k][1] / 1e8
            if 시억 < 300 or vs[k][2] / 1e8 < 1.0:
                continue
            i = ii[k]
            j2 = i + 20
            if j2 >= len(날):
                continue
            c1 = 종[k]
            끝 = 주가[날[j2]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            d8 = 날[i]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100 if 종[k - 20] > 0 else None
            지금, 작년 = 분재값(c, d8)
            매성, 영성 = None, None
            영흑 = None
            if 지금 and 작년:
                a, b = 지금[2], 작년[2]
                if a["매출"] and b["매출"] and b["매출"] > 0:
                    매성 = (a["매출"] / b["매출"] - 1) * 100
                if a["영익"] is not None and b["영익"] is not None and b["영익"] > 0:
                    영성 = (a["영익"] / b["영익"] - 1) * 100
            if 지금:
                영흑 = (1.0 if (지금[2]["영익"] or 0) > 0 else 0.0)
            # 최근 60일 안에 증자 공시가 있었나
            유상, 무상 = False, False
            for 받, u, m in 증:
                if 받 <= d8 and 받 >= 날[max(0, i - 60)]:
                    유상 = 유상 or u
                    무상 = 무상 or m
            전체, 밤 = 밤공시.get(d8, (0, 0))
            사건.append({
                "해": d8[:4], "_20": 뒤, "시억": 시억,
                "볼20": 볼20, "낙20": 낙20,
                "매성": 매성, "영성": 영성, "영흑": 영흑,
                "유상": 유상, "무상": 무상,
                "밤공시비": (밤 / 전체 * 100) if 전체 else None,
            })
    print(f"  사건 **{len(사건):,}건**", flush=True)
    for 라, 키 in (("분기 성장률", "매성"), ("영업이익 성장률", "영성"),
                   ("증자(유상)", "유상"), ("밤공시", "밤공시비")):
        n = sum(1 for x in 사건 if x[키] is not None and x[키] is not False)
        print(f"    {라:<14}붙은 것 {n:>9,} ({n/len(사건)*100:>4.0f}%)")

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
            n = len([x for x in 칸 if x.get("_20") is not None])
            print(f"  {이름:<34}{n:>9,}{'표본 부족':>18}")
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
              f"{차:>+8.1f}p  [{방말}]{표}")

    머 = (f"  {'재료':<34}{'건수':>9}{'1년에':>7}{'이김':>8}"
          f"{'바탕대비':>9}  [구간별]")

    print("\n  ── A ⭐⭐⭐ **분기 실적 성장률** (전년 동기 대비) ──")
    print(머)
    for a, b in ((-999, -30), (-30, -10), (-10, 0), (0, 10), (10, 30),
                 (30, 50), (50, 100), (100, 99999)):
        재기(f"매출 성장 {a:+.0f}% ~ {b:+.0f}%",
             lambda x, p=a, q=b: x["매성"] is not None and p <= x["매성"] < q)
    print()
    for a, b in ((-999, -50), (-50, 0), (0, 50), (50, 100), (100, 99999)):
        재기(f"영업이익 성장 {a:+.0f}% ~ {b:+.0f}%",
             lambda x, p=a, q=b: x["영성"] is not None and p <= x["영성"] < q)
    재기("영업 **적자**", lambda x: x["영흑"] == 0.0)
    재기("영업 **흑자**", lambda x: x["영흑"] == 1.0)

    print("\n  ── A-2 ⭐⭐ **성장 × 지금 규칙** (같이 쓰면) ──")
    print(머)
    지금 = [x for x in 사건 if (x["볼20"] is not None and x["볼20"] <= -1.0
                                and x["낙20"] is not None and x["낙20"] <= -10)]
    기지금 = 점(지금)
    if 기지금:
        print(f"     [견줌] 지금 규칙 {기지금[2]:,}건 · 이김 {기지금[0]:.1f}%")
        for 라, fn in (("매출 성장 +10%↑",
                        lambda x: x["매성"] is not None and x["매성"] >= 10),
                       ("매출 성장 +30%↑",
                        lambda x: x["매성"] is not None and x["매성"] >= 30),
                       ("영업이익 성장 +50%↑",
                        lambda x: x["영성"] is not None and x["영성"] >= 50),
                       ("영업 흑자", lambda x: x["영흑"] == 1.0)):
            재기(f"지금 규칙 AND {라}", fn, 지금, 기지금)

    print("\n  ── B ⭐⭐ **증자** (60일 안 공시) ──")
    print(머)
    재기("**유상증자** 있었다", lambda x: x["유상"])
    재기("**무상증자** 있었다", lambda x: x["무상"])
    재기("유상증자 **없었다**", lambda x: not x["유상"])

    print("\n  ── C ⭐⭐ **공시 시각** (그날 밤 16시 뒤 공시 비율) ──")
    print(머)
    for a, b in ((0, 20), (20, 40), (40, 60), (60, 101)):
        재기(f"밤 공시 비율 {a}~{b}%",
             lambda x, p=a, q=b: (x["밤공시비"] is not None
                                  and p <= x["밤공시비"] < q))

    LH.끝맺기(0, 0, ["A 분기 성장", "A-2 성장×지금규칙", "B 증자", "C 공시 시각"])
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_236차_안써본재료.txt")

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
