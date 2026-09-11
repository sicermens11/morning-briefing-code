#!/usr/bin/env python3
r"""
wide_lab2.py — **209차 · 재료 넓힌 격자** (2026-09-10 신설)

## 왜
```
볼린저·낙폭 **둘만** 격자로 조합해봤다 (191·198·207차).
나머지 재료는 **세분화만 하고 조합은 안 했다**:
  재무 · 시장상태 · 수급 · 거래 · 종목성격 · 해외 · 컨센서스
185차가 재료 40여개를 쟀지만 **단계적으로 3개 고르기**라 과적합됐고
잣대(기회 수)도 틀렸다
```

## 판정 기준 (먼저 밝힌다 — [[judge-criteria-need-user-check]])
```
**AND 로 붙일 때**   ① 승률 **+3%p 이상** ② 기회 **절반 이상** 남음
**OR 로 더할 때**    ① 기회 늘고 ② 승률 **-0.5%p 이내**
둘 다              ③ **최근 3년(2023~)에도** 같은 방향
                   ④ **바탕 대비**로 잰다 (207차: 바탕이 47.4%->44.4%로 빠졌다)
```

## 뼈대를 셋으로 나눈다
```
뼈대 1  **볼20 -1.5σ**   (207차 최고 · 최근 3년에 강하다)
뼈대 2  **기존 규칙**     (지금 쓰는 것)
뼈대 3  **없음**         (재료 단독 — 뼈대 때문에 나온 결과인지 가린다)
```

쓰는 법:
    python scripts\wide_lab2.py
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_시작 = "20100104"
_최소 = 300


def _해외표(한국날):
    r"""{이름: {한국날짜: 5일 변화%}} — ⚠️ **그날보다 앞선 마지막 값**만 쓴다"""
    볼것 = (("SOXX", "반도체ETF"), ("SPY", "S&P500"),
            ("HG=F", "구리"), ("KRW=X", "원달러"))
    난것 = {}
    for 파, 라 in 볼것:
        p = os.path.join(_BASE, "data", "yahoo", f"{파}.json")
        if not os.path.exists(p):
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        z = {k: float(v) for k, v in (d.get("종가") or {}).items()
             if v not in (None, "")}
        if len(z) < 1000:
            continue
        해날 = sorted(z)
        표, j = {}, 0
        for d8 in 한국날:
            while j < len(해날) and 해날[j] < d8:
                j += 1
            k = j - 1
            if k < 5:
                continue
            표[d8] = (z[해날[k]] / z[해날[k - 5]] - 1) * 100
        난것[라] = 표
    return 난것


def _컨센서스():
    r"""{종목: [날짜…]} — 리포트가 나온 날 (189차에서 가장 셌다)"""
    난것 = {}
    for f in sorted(glob.glob(os.path.join(_BASE, "data", "consensus", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        줄 = d.get("목록") or d.get("리포트") or []
        if isinstance(줄, dict):
            줄 = list(줄.values())
        for r in 줄:
            if not isinstance(r, dict):
                continue
            c = str(r.get("종목코드") or r.get("code") or "")
            d8 = str(r.get("날짜") or r.get("date") or "")[:10].replace("-", "")
            if len(c) == 6 and len(d8) == 8:
                난것.setdefault(c, []).append(d8)
    for c in 난것:
        난것[c].sort()
    return 난것


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    자리 = {d: i for i, d in enumerate(날)}
    print(f"  거래일 {len(날):,}일", flush=True)

    해 = _해외표(날)
    print(f"  해외 {len(해)}가지", flush=True)
    컨 = _컨센서스()
    print(f"  컨센서스 {len(컨):,}종목", flush=True)
    재무 = 연간재무()
    기본 = O._기본()

    # 시장 지수(코스피)로 시장낙폭·상대강도
    시장 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        v = (d2.get("지수") or {}).get("코스피")
        if isinstance(v, dict):
            try:
                시장[d2.get("기준일") or os.path.basename(f)[:8]] = \
                    float(str(v.get("종가")).replace(",", ""))
            except (TypeError, ValueError):
                pass
    시장날 = sorted(시장)
    시장낙 = {}
    for i2, d in enumerate(시장날):
        if i2 >= 20 and 시장[시장날[i2 - 20]] > 0:
            시장낙[d] = (시장[d] / 시장[시장날[i2 - 20]] - 1) * 100
    print(f"  시장 지수 {len(시장낙):,}일", flush=True)

    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            계열.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(i)

    print("  사건 만드는 중...", flush=True)
    사건 = []
    for c, vs in 계열.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        bb = 기본.get(c) or {}
        for k in range(120, len(vs)):
            시총억 = vs[k][1] / 1e8
            대금억 = vs[k][2] / 1e8
            if 시총억 < 100 or 대금억 < 1.0:
                continue
            c1 = 종[k]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100
            # ⚠️ 램 — 만들 때부터 좁힌다
            if not ((볼20 is not None and 볼20 <= -0.5) or 낙20 <= -5):
                continue
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            d8 = 날[i]
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            m60, _ = O.창평균표준(종, k, 60)
            # 그 종목 20일 변동성
            일 = []
            for z in range(k - 19, k + 1):
                앞 = 종[z - 1]
                if 앞 > 0:
                    일.append(종[z] / 앞 - 1)
            _, 일sd = O.빠른평균표준(일) if len(일) >= 15 else (0, 0)
            시낙 = 시장낙.get(d8)
            # 재무 (적용일이 지난 것 중 최근)
            fm = {}
            for 적용, 값 in (재무.get(c) or []):
                if 적용 <= d8:
                    fm = 값
                else:
                    break
            # 컨센서스 — 90일 안에 리포트가 있나
            줄c = 컨.get(c) or []
            k0 = 자리.get(d8, 0)
            앞90 = 날[max(0, k0 - 90)]
            리포트90 = any(앞90 <= z <= d8 for z in 줄c)
            사건.append({
                "해": d8[:4], "_날짜": d8,
                "볼20": 볼20, "낙20": 낙20,
                "시총억": 시총억, "대금억": 대금억,
                "회전율": (대금억 / 시총억 * 100) if 시총억 > 0 else 0,
                "주가": c1,
                "변동": 일sd * (252 ** 0.5) * 100 if 일sd else None,
                "60일선대비": ((c1 / m60 - 1) * 100) if m60 else None,
                "시장낙폭": 시낙,
                "상대강도": (낙20 - 시낙) if 시낙 is not None else None,
                "잉여금": fm.get("잉여금비율"), "부채": fm.get("부채비율"),
                "ROE": fm.get("ROE"), "영업이익률": fm.get("영업이익률"),
                "순이익률": fm.get("순이익률"), "유동비율": fm.get("유동비율"),
                "리포트90": 리포트90,
                "외SOXX": (해.get("반도체ETF") or {}).get(d8),
                "외SP": (해.get("S&P500") or {}).get(d8),
                "외구리": (해.get("구리") or {}).get(d8),
                "외원달러": (해.get("원달러") or {}).get(d8),
                "_20": 뒤,
            })
    print(f"  사건 {len(사건):,}건", flush=True)

    해수 = max(len({x["해"] for x in 사건}), 1)

    def 셈(칸, 최소=None):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < (최소 or _최소):
            return None
        return (len(v), len(v) / 해수,
                sum(1 for z in v if z > 0) / len(v) * 100, sum(v) / len(v))

    바탕 = 셈(사건)
    최근 = [x for x in 사건 if x["해"] >= "2023"]
    바탕최 = 셈(최근)

    # ── 뼈대 셋 ──
    def 뼈볼(x):
        return x["볼20"] is not None and x["볼20"] <= -1.5

    def 뼈기존(x):
        return (x["볼20"] is not None and x["볼20"] <= -1.0
                and x["낙20"] <= -10.0 and 300 <= x["시총억"] < 2000)

    뼈대들 = (("볼20 -1.5σ", 뼈볼), ("기존 규칙", 뼈기존), ("없음", lambda x: True))

    # ── 재료 (이름, 함수) ──
    def 위(k, 문):
        return lambda x, a=k, b=문: (x.get(a) is not None and x[a] >= b)

    def 아래(k, 문):
        return lambda x, a=k, b=문: (x.get(a) is not None and x[a] <= b)

    재료들 = []
    for k, 문들 in (("잉여금", (30, 80, 200)), ("ROE", (0, 5, 12)),
                    ("영업이익률", (0, 5, 12)), ("순이익률", (0, 3, 8)),
                    ("유동비율", (100, 150, 250))):
        for 문 in 문들:
            재료들.append((f"{k}≥{문}", 위(k, 문)))
    for k, 문들 in (("부채", (40, 60, 80)),):
        for 문 in 문들:
            재료들.append((f"{k}≤{문}", 아래(k, 문)))
    for 문 in (-3, -7, -12):
        재료들.append((f"시장낙폭≤{문}%", 아래("시장낙폭", 문)))
    for 문 in (-12, -5, 3):
        재료들.append((f"상대강도≥{문}", 위("상대강도", 문)))
    for 문 in (1, 3, 10):
        재료들.append((f"대금≥{문}억", 위("대금억", 문)))
    for 문 in (0.5, 1.5, 4):
        재료들.append((f"회전율≥{문}%", 위("회전율", 문)))
    for 문 in (300, 800, 2000):
        재료들.append((f"시총≥{문}억", 위("시총억", 문)))
    for 문 in (800, 2000):
        재료들.append((f"시총<{문}억", 아래("시총억", 문 - 0.01)))
    for 문 in (30, 50, 70):
        재료들.append((f"변동성≥{문}%", 위("변동", 문)))
    for 문 in (-10, -25):
        재료들.append((f"60일선≤{문}%", 아래("60일선대비", 문)))
    재료들.append(("⭐리포트90일", lambda x: bool(x.get("리포트90"))))
    재료들.append(("리포트 없음", lambda x: not x.get("리포트90")))
    for k, 라 in (("외SOXX", "SOXX"), ("외SP", "S&P"), ("외구리", "구리")):
        재료들.append((f"{라} 5일≤-3%", 아래(k, -3)))
        재료들.append((f"{라} 5일≥+3%", 위(k, 3)))
    재료들.append(("원달러 5일≥+3%", 위("외원달러", 3)))
    재료들.append(("원달러 5일≤-3%", 아래("외원달러", -3)))

    print("\n" + "=" * 112)
    print("  209차 · **재료 넓힌 격자** — 뼈대 셋 × 재료 " + str(len(재료들)) + "개 × AND·OR")
    print("  ⚠️ 판정: AND는 **승률+3%p·기회 절반↑** · OR는 **기회 늘고 승률-0.5%p 이내**")
    print("     ③ 최근 3년에도 같은 방향 ④ **바탕 대비**로 잰다")
    print("=" * 112)
    if 바탕 and 바탕최:
        print(f"\n  바탕  전체 **{바탕[2]:.1f}%** ({바탕[0]:,}건)"
              f" · 최근 **{바탕최[2]:.1f}%** ({바탕최[0]:,}건)")

    for 뼈라, 뼈fn in 뼈대들:
        뼈칸 = [x for x in 사건 if 뼈fn(x)]
        r뼈 = 셈(뼈칸)
        뼈최 = [x for x in 뼈칸 if x["해"] >= "2023"]
        r뼈최 = 셈(뼈최)
        if not r뼈:
            continue
        print(f"\n  ══ 뼈대: **{뼈라}** — 1년 {r뼈[1]:.0f}개 · {r뼈[2]:.1f}%"
              f" (최근 {r뼈최[2] if r뼈최 else 0:.1f}%) ══")
        print(f"  {'재료':<18}{'AND 이김':>9}{'AND 기회':>9}{'AND 최근':>9}"
              f"{'  |':<3}{'OR 이김':>8}{'OR 기회':>8}{'OR 최근':>8}   판정")
        됨A, 됨O = [], []
        for 라, fn in 재료들:
            A칸 = [x for x in 뼈칸 if fn(x)]
            rA = 셈(A칸)
            O칸 = [x for x in 사건 if 뼈fn(x) or fn(x)]
            rO = 셈(O칸)
            if not rA or not rO:
                continue
            rA최 = 셈([x for x in A칸 if x["해"] >= "2023"], 100)
            rO최 = 셈([x for x in O칸 if x["해"] >= "2023"], 100)
            기A = rA[0] / r뼈[0] * 100
            차A = rA[2] - r뼈[2]
            기O = rO[0] / r뼈[0] * 100
            차O = rO[2] - r뼈[2]
            좋A = (차A >= 3 and 기A >= 50
                   and (rA최 and r뼈최 and rA최[2] - r뼈최[2] >= 0))
            좋O = (기O > 100 and 차O >= -0.5
                   and (rO최 and r뼈최 and rO최[2] - r뼈최[2] >= -0.5))
            if not (좋A or 좋O or 차A >= 5):
                continue
            if 좋A:
                됨A.append((라, 차A, 기A))
            if 좋O:
                됨O.append((라, 차O, 기O))
            표 = ("  ⭐AND" if 좋A else "") + ("  ⭐OR" if 좋O else "")
            print(f"  {라:<18}{rA[2]:>8.1f}%{기A:>8.0f}%"
                  f"{(rA최[2] if rA최 else 0):>8.1f}%   |"
                  f"{rO[2]:>7.1f}%{기O:>7.0f}%"
                  f"{(rO최[2] if rO최 else 0):>7.1f}%{표}")
        print(f"     ⇒ AND 로 된 것 **{len(됨A)}개** · OR 로 된 것 **{len(됨O)}개**")
        if 됨A:
            print("       AND: " + " · ".join(f"{라}({차:+.1f}%p/{기:.0f}%)"
                                              for 라, 차, 기 in 됨A[:6]))
        if 됨O:
            print("       OR : " + " · ".join(f"{라}({차:+.1f}%p/{기:.0f}%)"
                                              for 라, 차, 기 in 됨O[:6]))

    print("\n" + "=" * 112)
    print("  읽는 법")
    print("    - **AND 는 기회를 깎는다.** 기회가 절반 밑이면 아무리 승률이 올라도 안 쓴다")
    print("    - **OR 는 기회를 늘린다.** 승률이 조금 떨어져도 기회가 늘면 값어치가 있다")
    print("    - 뼈대 **「없음」**은 재료 단독이다 — 뼈대 때문에 나온 결과인지 가린다")
    print("=" * 112)
    return 0


if __name__ == "__main__":
    _p = os.path.join(_BASE, "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_209차_재료넓힌격자.txt")

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
