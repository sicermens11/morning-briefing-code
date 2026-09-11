#!/usr/bin/env python3
r"""
link_lab.py — **미국이 한국에 미치는 영향** (2026-09-03 · 71차)

⚠️⚠️ **사용자 요청.**
   *"미국의 종목, ETF가 한국 개별종목, ETF에 어떤 영향을 미치는지 연관관계가 있는지도 보면 좋을 것 같아."*

## ⭐ 왜 이게 쓸모 있나 — **시차**
```
미국장은 한국 시간 **새벽 05:00~06:00에 끝난다**
⇒ 「어젯밤 미국」은 **오늘 아침 08:00 브리핑에 이미 알 수 있다**
⇒ **look-ahead가 아니다.** 실제로 쓸 수 있는 정보다
```
```
미국 T일 종가(한국시간 T+1 새벽)  →  한국 T+1일 09:00 시가
```

## 자료
```
SPY        5,000일 (2006-10-17 ~ 2026-09-02) · FMP
한국 주가   4,103일 (2010-01-04 ~ 2026-09-02) · 수정주가
국내 ETF   4,103일 · 1,167종목
```
⚠️ SPY만 있다. QQQ·SOXX는 FMP·Alpha Vantage 무료에서 다 막혔다.
   ⇒ **국내 상장 미국 ETF**(TIGER 미국나스닥100 등)를 대리로 쓴다.

## 재는 것
```
A 전이율      미국 전일 등락 → 한국 다음날 **갭**에 얼마나 반영되나 (회귀 기울기)
B 남는 게 있나 갭에 반영되고 **남은 부분**이 그날 종가까지 이어지나
              ⇒ 다 반영됐으면 **아침에 알아도 쓸모가 없다**
C 크기별      미국이 크게 빠진 날(-1%·-2%·-3%) 한국은 얼마나 빠지나
D ⭐ **결합**  미국이 크게 빠진 다음날 우리 신호를 쓰면 더 좋나
E 종목 민감도  어떤 한국 종목이 미국에 민감한가 (시총·업종별)
```
⚠️ 판정: 상관계수 + **95% 신뢰구간** · 회귀 기울기 · 연도별.
"""
import glob
import io
import json
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_보유 = 20


def 상관(a, b):
    n = len(a)
    if n < 20:
        return None
    ma, mb = st.mean(a), st.mean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    if sa == 0 or sb == 0:
        return None
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (sa * sb)


def z신뢰(r, n):
    if n < 4 or r is None or abs(r) >= 1:
        return None, None
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    return math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)


def 기울기(x, y):
    """y = a + b·x 의 b (미국 1% 움직일 때 한국이 몇 % 움직이나)."""
    n = len(x)
    if n < 20:
        return None
    mx, my = st.mean(x), st.mean(y)
    분모 = sum((v - mx) ** 2 for v in x)
    if 분모 == 0:
        return None
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / 분모


def main():
    print("  자료 읽는 중...", flush=True)
    try:
        spy = json.load(io.open(os.path.join(O._DATA, "us-daily", "SPY.json"),
                                encoding="utf-8-sig"))["종가"]
    except Exception as e:
        print(f"  ⚠️ SPY를 못 읽는다: {e}. collect_us.py를 먼저 돌려야 한다")
        return 1
    sk = sorted(spy)
    미등락 = {}
    for j in range(1, len(sk)):
        p = spy[sk[j - 1]]
        if p:
            미등락[sk[j]] = (spy[sk[j]] / p - 1) * 100
    print(f"  SPY {sk[0]} ~ {sk[-1]} · {len(spy):,}일", flush=True)

    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # 한국 시장 갭·종가등락
    갭표, 시장갭, 시장종, 앞종 = {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루, 종등 = {}, []
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                x = (종 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
                if abs(x) <= 32:
                    종등.append(x)
        갭표[d["기준일"]] = 하루
        if len(하루) >= 100:
            시장갭[d["기준일"]] = st.median(list(하루.values()))
        if len(종등) >= 100:
            시장종[d["기준일"]] = st.median(종등)

    # ⚠️ 미국 T일 → 한국 T+1일. 한국 거래일 중 「그 앞의 가장 가까운 미국 거래일」을 짝짓는다
    짝 = []
    미키 = sk
    for d in 날:
        앞 = [x for x in 미키 if x < d]
        if not 앞:
            continue
        전 = max(앞)
        if 전 not in 미등락 or d not in 시장갭 or d not in 시장종:
            continue
        # ⚠️ 3일 넘게 벌어지면(연휴) 짝짓지 않는다
        try:
            import datetime as dt
            d1 = dt.datetime.strptime(d, "%Y%m%d")
            d0 = dt.datetime.strptime(전, "%Y%m%d")
            if (d1 - d0).days > 4:
                continue
        except Exception:
            pass
        짝.append((d, 미등락[전], 시장갭[d], 시장종[d]))
    print(f"  짝지은 날 {len(짝):,}일 ({짝[0][0]} ~ {짝[-1][0]})\n", flush=True)

    미 = [x[1] for x in 짝]
    갭 = [x[2] for x in 짝]
    종 = [x[3] for x in 짝]
    장중 = [x[3] - x[2] for x in 짝]      # 종가등락 − 갭 = 장중 움직임

    # ══ A 전이율 ══
    print("  ══ A **미국 전일 등락 → 한국 다음날 갭** ══")
    r = 상관(미, 갭)
    lo, hi = z신뢰(r, len(짝))
    b = 기울기(미, 갭)
    print(f"    상관 **{r:.3f}** (95% CI {lo:.3f} ~ {hi:.3f}) · 표본 {len(짝):,}일")
    print(f"    기울기 **{b:.3f}** — 미국이 1% 움직이면 한국 갭이 {b:.2f}% 움직인다")

    print("\n  ══ B **갭에 다 반영되고 남는 게 있나** (장중 = 종가 − 갭) ══")
    print("     ⚠️ 다 반영됐으면 **아침에 알아도 쓸모가 없다**")
    r2 = 상관(미, 장중)
    lo2, hi2 = z신뢰(r2, len(짝))
    b2 = 기울기(미, 장중)
    print(f"    미국 → 한국 **장중** 상관 {r2:.3f} (CI {lo2:.3f} ~ {hi2:.3f}) "
          f"· 기울기 {b2:.3f}")
    r3 = 상관(미, 종)
    b3 = 기울기(미, 종)
    print(f"    미국 → 한국 **종가** 상관 {r3:.3f} · 기울기 {b3:.3f}")
    if b and b3:
        print(f"    ⇒ 종가 기울기 {b3:.3f} 중 **갭이 {b:.3f}** ({b/b3*100:.0f}%), "
              f"장중이 {b2:.3f} ({b2/b3*100:.0f}%)")

    print("\n  ══ 연도별 전이율 (시간이 지나며 세졌나) ══")
    print(f"    {'해':<7}{'표본':>7}{'상관':>9}{'기울기':>9}")
    해별 = {}
    for d, m, g, c in 짝:
        해별.setdefault(d[:4], []).append((m, g))
    for y in sorted(해별):
        a = 해별[y]
        if len(a) < 100:
            continue
        rr = 상관([x[0] for x in a], [x[1] for x in a])
        bb = 기울기([x[0] for x in a], [x[1] for x in a])
        print(f"    {y:<7}{len(a):>7}{rr:>9.3f}{bb:>9.3f}")

    # ══ C 크기별 ══
    print("\n  ══ C **미국이 크게 빠진 날** 한국은? ══")
    print(f"    {'미국 등락':<18}{'날수':>7}{'한국 갭 중앙':>13}"
          f"{'한국 종가 중앙':>14}{'갭 후 장중':>12}")
    for 하, 상, 라 in ((-99, -3, "≤ −3%"), (-3, -2, "−3 ~ −2%"),
                       (-2, -1, "−2 ~ −1%"), (-1, 0, "−1 ~ 0%"),
                       (0, 1, "0 ~ +1%"), (1, 2, "+1 ~ +2%"), (2, 99, "≥ +2%")):
        a = [x for x in 짝 if 하 < x[1] <= 상]
        if len(a) < 20:
            continue
        print(f"    {라:<18}{len(a):>7}{st.median([x[2] for x in a]):>+12.3f}%"
              f"{st.median([x[3] for x in a]):>+13.3f}%"
              f"{st.median([x[3]-x[2] for x in a]):>+11.3f}%")

    # ══ D 결합 ══
    print("\n  ══ D ⭐ **미국이 빠진 다음날 우리 신호를 쓰면 더 좋나** ══")

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

    미맵 = {d: m for d, m, g, c in 짝}
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < "20160401" or 다음 not in 미맵:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -3:
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0 or sq[k - 20] <= 0:
                continue
            if (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            사건.append((다음, (끝[0] / 매수 - 1) * 100 - _비용, 미맵[다음]))
    년수 = len([d for d in 날 if d >= "20160401"]) / 245
    print(f"    {'조건':<28}{'평균':>9}{'승률':>8}{'연간':>8}{'연도별':>8}{'신호일':>8}")

    def 재기(고르기, 라):
        t = {}
        for d, r, m in 사건:
            if 고르기(m):
                t.setdefault(d, []).append(r)
        if len(t) < 6:
            print(f"    {라:<28}신호일 {len(t)}일 — 부족")
            return
        수 = [st.mean(v) for v in t.values()]
        승 = sum(1 for x in 수 if x > 0) / len(수) * 100
        해 = {}
        for d, v in t.items():
            해.setdefault(d[:4], []).append(st.mean(v))
        전 = 플 = 0
        for y, arr in 해.items():
            if len(arr) < 3:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        print(f"    {라:<28}{st.mean(수):>+8.2f}%{승:>7.1f}%"
              f"{len(t)/년수:>7.1f}일{f'{플}/{전}':>8}{len(t):>7}일")

    재기(lambda m: True, "우리 신호 전부 (기준선)")
    재기(lambda m: m <= -1.5, "+ 어젯밤 미국 −1.5%↓")
    재기(lambda m: m <= -1.0, "+ 어젯밤 미국 −1.0%↓")
    재기(lambda m: m <= -0.5, "+ 어젯밤 미국 −0.5%↓")
    재기(lambda m: m <= 0, "+ 어젯밤 미국 하락")
    재기(lambda m: m > 0, "+ 어젯밤 미국 상승")
    재기(lambda m: m >= 0.5, "+ 어젯밤 미국 +0.5%↑")

    print("\n  읽는 법")
    print("    - **A의 기울기**가 전이율이다. 1에 가까우면 한국이 미국을 그대로 따라간다")
    print("    - **B가 핵심이다.** 갭에 다 반영됐으면(장중 상관≈0) 아침에 알아도 못 쓴다")
    print("    - D에서 「미국 하락」 쪽이 기준선보다 나으면 **브리핑에 붙일 수 있다**")
    print("    - ⚠️ SPY만 있다. QQQ·SOXX는 무료 API에서 다 막혔다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
