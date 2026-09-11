#!/usr/bin/env python3
r"""
world_lab.py — **192차 · 해외 신호와 수주 공시** (2026-09-09 신설)

## 사용자 말 (그대로)
```
「한국은 **수출 위주 국가**라 **해외 수주나 해외 소식**에 영향을 받을 것 같아」
```

## 자료가 이미 다 있었다 (2026-09-09에 확인)
```
data/yahoo/ 에 96개가 매일 쌓이고 있고 **기간이 20~30년**이다:
  반도체   SOXX 6,325일 · TSMC 7,269일 · ASML 7,923일 · 엔비디아 6,949일
           도쿄일렉트론 6,655일 · 어드반테스트 6,655일 · TSMC(대만상장) 6,632일
  환율     **원달러 5,903일** · 달러인덱스 8,039일
  원자재   **구리 6,532일** · WTI 6,536일
  아시아   대만 7,149일 · 일본 7,766일
  형편     공포지수(VIX) 7,971일 · 미국10년물 7,952일 · S&P500 7,973일
⚠️ 「필라반도체」는 751일(3년)뿐이라 안 쓴다. **SOXX 6,325일**로 대신한다
수주   dart-daily 4,108일(2010~) 에 「단일판매ㆍ공급계약체결」이 있다
```

## ⚠️⚠️ 미리보기(look-ahead) 막기 — 이게 제일 중요하다
```
한국 D일 **09:00 시가**에 산다. 그때 알 수 있는 것만 써야 한다.
  · 미국 D-1 종가  -> 한국 D일 **새벽 5~6시**에 나온다        ✅ 쓴다
  · 대만·일본 D일 종가 -> 한국 D일 **장중**에 나온다            ❌ 못 쓴다
=> 그래서 나라를 가리지 않고 **D보다 앞선 마지막 값**만 쓴다.
   대만·일본을 D일로 쓰면 「오늘 대만이 오른 걸 알고 오늘 아침에 산다」가 된다
```

## ⚠️ 램 — 189차에서 배운 것
```
189차는 사건 5,437,354개 dict 마다 필드를 더하다 **램이 터져 죽었다.**
그래서 이 시험은:
  ① 후보를 **볼린저 -0.5σ 또는 20일 -5%** 로 미리 좁힌다
  ② 해외 값은 **날짜에만 달렸다** — 사건마다 넣지 않고 날짜 표에서 찾아 쓴다
```

## 재는 것
```
A  견줄 자리 (지금 규칙)
B  해외 재료마다 **단독으로** — 전날 그게 빠진 날 / 오른 날
C  ⭐ **원달러** — 「수출 위주라 환율이 오르면 유리하다」를 곧바로 잰다
D  ⭐ **섹터 짝짓기** — 반도체 후보에 SOXX·TSMC, 조선에 구리·유가
E  ⭐ **수주 공시** (단일판매ㆍ공급계약체결)
F  조합 — 지금 규칙 + 해외
```
⚠️ E 는 공시명만 봐서는 **국내 수주인지 해외 수주인지 모른다.** 「공급계약」으로만 읽는다

쓰는 법:
    python scripts\world_lab.py
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from chain_map import 읽기 as 맵읽기  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_시작 = "20100104"          # ⚠️ 공시가 2010-01-04부터라 거기 맞춘다
_최소 = 200

# (파일이름, 보여줄 이름) — 전부 20년 넘는 것만 골랐다
_해외 = (("SOXX", "반도체 ETF"), ("TSM", "TSMC"), ("ASML", "ASML"),
         ("NVDA", "엔비디아"), ("2330_TW", "TSMC(대만)"),
         ("8035_T", "도쿄일렉트론"), ("6857_T", "어드반테스트"),
         ("KRW=X", "**원달러**"), ("DX-Y.NYB", "달러인덱스"),
         ("HG=F", "**구리**"), ("CL=F", "WTI 유가"),
         ("IDX_TWII", "대만지수"), ("IDX_N225", "일본지수"),
         ("IDX_VIX", "공포지수"), ("IDX_TNX", "미국10년물"),
         ("SPY", "S&P500"), ("QQQ", "나스닥100"))


def 해외읽기():
    r"""{이름: {날짜: 종가}}. 없는 파일은 조용히 건너뛴다"""
    난것 = {}
    for 파, 라 in _해외:
        p = os.path.join(_BASE, "data", "yahoo", f"{파}.json")
        if not os.path.exists(p):
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        z = {k: float(v) for k, v in (d.get("종가") or {}).items()
             if v not in (None, "")}
        if len(z) > 1000:
            난것[라] = z
    return 난것


def 앞값표(계열, 한국날):
    r"""⚠️ 한국 날짜마다 **그보다 앞선 마지막 해외 값**을 짝지어 둔다.

    {한국날짜: (앞값, 1일변화%, 5일변화%, 20일변화%)}
    같은 날 값을 쓰면 **미리보기**가 된다 — 대만·일본은 한국 장중에 끝난다
    """
    해날 = sorted(계열)
    표, j = {}, 0
    for d in 한국날:
        while j < len(해날) and 해날[j] < d:
            j += 1
        k = j - 1                       # ⚠️ **앞선** 마지막 것
        if k < 20:
            표[d] = None
            continue
        v = 계열[해날[k]]
        표[d] = (v,
                 (v / 계열[해날[k - 1]] - 1) * 100,
                 (v / 계열[해날[k - 5]] - 1) * 100,
                 (v / 계열[해날[k - 20]] - 1) * 100)
    return 표


def 수주읽기():
    r"""{종목코드: {날짜들}} — 「단일판매ㆍ공급계약체결」이 난 날"""
    난것 = {}
    for f in sorted(glob.glob(os.path.join(_BASE, "data", "dart-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = d.get("기준일") or os.path.basename(f)[:8]
        for r in (d.get("챙길공시") or []):
            나 = str(r.get("공시명") or "")
            c = str(r.get("종목코드") or "")
            if c and ("공급계약" in 나 or "수주" in 나):
                난것.setdefault(c, set()).add(d8)
    return 난것


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일 · {날[0]} ~ {날[-1]}", flush=True)

    해 = 해외읽기()
    print(f"  해외 {len(해)}가지 읽음", flush=True)
    표들 = {라: 앞값표(z, 날) for 라, z in 해.items()}

    수주 = 수주읽기()
    print(f"  수주·공급계약 공시 {len(수주):,}종목", flush=True)

    맵 = 맵읽기()
    섹터표 = {}
    for s, 들 in 맵.items():
        for _, c in 들:
            if c and c not in 섹터표:
                섹터표[c] = s

    # ── 사건 (⚠️ 189차처럼 죽지 않게 **미리 좁힌다**) ──
    print("  후보 모으는 중 (볼린저 -0.5σ 또는 20일 -5% 만)...", flush=True)
    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            계열.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(i)
    사건 = []
    for c, vs in 계열.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(20, len(vs)):
            시총억 = vs[k][1] / 1e8
            대금억 = vs[k][2] / 1e8
            if 시총억 < 100 or 대금억 < 1.0:
                continue
            c1 = 종[k]
            m, sd = O.창평균표준(종, k, 20)
            볼 = ((c1 - m) / (2 * sd)) if sd else None
            낙 = (c1 / 종[k - 20] - 1) * 100
            if not ((볼 is not None and 볼 <= -0.5) or 낙 <= -5):
                continue                # ⚠️ 여기서 좁혀야 램이 산다
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            사건.append({"code": c, "_날짜": 날[i], "시총억": 시총억,
                         "볼20": 볼, "낙20": 낙, "_20": 뒤,
                         "섹터": 섹터표.get(c)})
    print(f"  사건 {len(사건):,}건", flush=True)

    해수 = max((int(날[-1][:4]) - int(날[0][:4])) + 1, 1)

    def 세기(칸, 최소=None):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < (최소 or _최소):
            return None
        return (len(칸), len(칸) / 해수,
                sum(1 for z in v if z > 0) / len(v) * 100, sum(v) / len(v))

    def 줄찍기(라, r, 폭=38):
        if r is None:
            print(f"  {라:<{폭}}{'표본 부족':>30}")
        else:
            n, 년, 이, 평 = r
            print(f"  {라:<{폭}}{n:>9,}{년:>8.0f}{이:>9.1f}%{평:>+9.2f}")

    머 = f"  {'':<38}{'건수':>9}{'1년에':>8}{'20일 이김':>10}{'평균':>9}"

    def 지금규칙(x):
        return (x["볼20"] is not None and x["볼20"] <= -1.0
                and x["낙20"] <= -10.0 and 300 <= x["시총억"] < 2000)

    후보 = [x for x in 사건 if 지금규칙(x)]

    print("\n" + "=" * 104)
    print("  192차 · **해외 신호와 수주 공시**")
    print("  사용자: 「한국은 수출 위주 국가라 **해외 수주나 해외 소식**에 영향을 받을 것 같아」")
    print(f"  {날[0]} ~ {날[-1]} · {해수}년 · 상장폐지 {O.폐지손실:.0f}%")
    print("  ⚠️ 해외 값은 **그날보다 앞선 마지막 값**만 쓴다 (미리보기 막기)")
    print("=" * 104)

    # ══ A ══
    print("\n  ── A 견줄 자리 ──")
    print(머)
    줄찍기("느슨한 후보 전체 (볼-0.5σ 또는 -5%)", 세기(사건))
    줄찍기("**지금 규칙** (볼-1.0σ · -10% · 300~2,000억)", 세기(후보))

    # ══ B ══
    print("\n  ── B **해외 재료마다 단독으로** ──")
    print("     전날까지 그게 얼마나 움직였나로 나눈다 (5일 변화)")
    for 라 in 표들:
        표 = 표들[라]
        칸들 = []
        for 이름, lo, hi in (("많이 빠짐 (-5%↓)", -9e9, -5),
                             ("빠짐 (-2~-5%)", -5, -2),
                             ("제자리 (-2~+2%)", -2, 2),
                             ("오름 (+2%↑)", 2, 9e9)):
            추 = [x for x in 후보
                  if 표.get(x["_날짜"]) and lo <= 표[x["_날짜"]][2] < hi]
            칸들.append((이름, 세기(추)))
        if all(r is None for _, r in 칸들):
            continue
        print(f"\n   [{라} · 5일 변화]")
        print(머)
        for 이름, r in 칸들:
            줄찍기(f"  {이름}", r)

    # ══ C ══
    print("\n  ── C ⭐ **원달러** — 「수출 위주라 환율이 오르면 유리하다」 ──")
    표 = 표들.get("**원달러**")
    if 표:
        for 창, 자리 in (("1일", 1), ("5일", 2), ("20일", 3)):
            print(f"\n   [원달러 {창} 변화]")
            print(머)
            for 이름, lo, hi in (("원화 **강세** (-2%↓)", -9e9, -2),
                                 ("조금 강세 (-2~-0.5%)", -2, -0.5),
                                 ("제자리 (-0.5~+0.5%)", -0.5, 0.5),
                                 ("조금 약세 (+0.5~+2%)", 0.5, 2),
                                 ("원화 **약세** (+2%↑)", 2, 9e9)):
                추 = [x for x in 후보
                      if 표.get(x["_날짜"]) and lo <= 표[x["_날짜"]][자리] < hi]
                줄찍기(f"  {이름}", 추 and 세기(추))
    else:
        print("     ⚠️ 원달러 자료를 못 읽었다")

    # ══ D ══
    print("\n  ── D ⭐ **섹터 짝짓기** — 그 섹터에 맞는 해외 재료를 붙인다 ──")
    짝 = (("반도체/HBM 소부장", ("반도체 ETF", "TSMC", "ASML", "TSMC(대만)")),
          ("조선 기자재", ("**구리**", "WTI 유가")),
          ("조선 본선", ("**구리**", "WTI 유가")),
          ("2차전지 소부장", ("**구리**", "나스닥100")),
          ("방산", ("WTI 유가", "S&P500")),
          ("전력 인프라/변압기", ("**구리**", "S&P500")),
          ("AI 소프트웨어", ("나스닥100", "엔비디아")))
    for 섹, 재료들 in 짝:
        칸 = [x for x in 사건 if x["섹터"] == 섹]
        if not 칸:
            continue
        print(f"\n   [{섹}]  (느슨한 후보 {len(칸):,}건)")
        print(머)
        줄찍기("  [견줌] 그 섹터 전체", 세기(칸, 100))
        for 라 in 재료들:
            표2 = 표들.get(라)
            if not 표2:
                continue
            for 이름, lo, hi in (("5일 -3%↓ 빠진 뒤", -9e9, -3),
                                 ("5일 +3%↑ 오른 뒤", 3, 9e9)):
                추 = [x for x in 칸
                      if 표2.get(x["_날짜"]) and lo <= 표2[x["_날짜"]][2] < hi]
                줄찍기(f"  {라} {이름}", 세기(추, 100))

    # ══ E ══
    print("\n  ── E ⭐ **수주·공급계약 공시** ──")
    print("     ⚠️ 공시명만으로는 **국내 수주인지 해외 수주인지 모른다**. 「공급계약」으로 읽는다")
    print(머)
    자리 = {d: i for i, d in enumerate(날)}
    for 일 in (5, 20, 60):
        추 = []
        for x in 후보:
            들 = 수주.get(x["code"])
            if not 들:
                continue
            i = 자리[x["_날짜"]]
            앞 = set(날[max(0, i - 일 + 1):i + 1])
            if 들 & 앞:
                추.append(x)
        줄찍기(f"{일}일 안에 공급계약 공시 **있음**", 세기(추))
    없 = [x for x in 후보 if not (수주.get(x["code"]) or set())]
    줄찍기("공급계약 공시가 한 번도 없는 회사", 세기(없))

    # ══ F ══
    print("\n  ── F **지금 규칙 + 해외** 조합 ──")
    print(머)
    줄찍기("[견줌] 지금 규칙", 세기(후보))
    for 라 in ("반도체 ETF", "S&P500", "**원달러**", "공포지수", "**구리**"):
        표2 = 표들.get(라)
        if not 표2:
            continue
        for 이름, lo, hi in (("이 5일 -3%↓ 일 때", -9e9, -3),
                             ("이 5일 +3%↑ 일 때", 3, 9e9)):
            추 = [x for x in 후보
                  if 표2.get(x["_날짜"]) and lo <= 표2[x["_날짜"]][2] < hi]
            줄찍기(f"+ {라} {이름}", 세기(추))

    print("\n" + "=" * 104)
    print("  읽는 법")
    print("    - A 의 **지금 규칙** 값과 견준다. 전체와 견주면 틀린다")
    print("    - ⚠️ 해외 값은 다 **하루 앞선 것**이다. 그날 것을 쓰면 미리보기가 된다")
    print("    - D 에서 섹터별로 갈리면 **섹터마다 다른 해외 재료**를 쓸 값어치가 있다")
    print("    - E 는 국내·해외 수주를 못 가른다. 갈라야 하면 공시 본문을 받아야 한다")
    print("=" * 104)
    return 0


if __name__ == "__main__":
    _p = os.path.join(_BASE, "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-09_192차_해외신호.txt")

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
