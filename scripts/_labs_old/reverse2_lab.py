#!/usr/bin/env python3
r"""
reverse2_lab.py — **크게 오른 종목을 먼저 찾고 거꾸로 본다** (2026-09-03 · 68차)

⚠️⚠️ **왜 다시 짜나.** 09-01 `reverse_lab`은 **원본 종가**를 썼다.
   수정주가 버그(09-02 발견: 평균 일간수익률을 **연 13.7%p** 부풀렸다)가 있던 상태다.
   ⇒ 그 결과는 못 쓴다. **설계는 그대로 두고 자료만 고쳐** 다시 돌린다.

⚠️⚠️ **63차에서 새 신호를 못 찾았다.** 모멘텀 -1.54% · 수급 +0.35% · 지분율 +0.00%.
   전부 「조건 → 수익」 방향으로 찾았다. **이번엔 반대로 간다.**
```
지금까지  조건을 정해놓고 → 그 조건일 때 성적이 어땠나      (가설 검정)
이번      **크게 오른 종목을 모아놓고 → 그 전날 뭐가 있었나**  (역추적)
```

## 답하려는 것
```
A 상위 5% vs 하위 5%의 **전날 특성**이 정말 다른가
B ⭐ **우리 신호가 상위 5%의 몇 %를 잡나** (포착률)
C ⭐⭐ **못 잡는 것들의 공통점은 뭔가**  ← 여기서 새 신호가 나온다
D 놓치는 것 중 살 만한 것이 있나 (유동성·크기)
```

⚠️⚠️⚠️ **사후편향에 주의한다.** 「오른 종목은 이랬다」는 사실이지만
   **「이러면 오른다」는 결론이 아니다.** 역추적은 **발견의 출발점**일 뿐이고,
   찾은 것은 반드시 **걷기검증(61차 방식)으로 다시 검증**해야 한다.

⚠️ 기간: 2016-04~ (연간재무가 있는 구간) · D+20 · 다음날 시가 매수 · 비용 0.26%.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_보유 = 20
_시작 = "20160401"
_꼬리 = 0.05


def 요약(vals):
    if not vals:
        return None
    a = sorted(vals)
    return (st.mean(a), a[len(a) // 4], st.median(a), a[len(a) * 3 // 4])


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무, 수급 = O._기본(), 연간재무(), O._수급()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    갭표, 시장갭, 앞종 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
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
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d["기준일"]] = 하루
        if len(하루) >= 100:
            시장갭[d["기준일"]] = st.median(list(하루.values()))

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

    def 숫(x):
        try:
            return float(str(x).replace(",", "").replace("%", ""))
        except (TypeError, ValueError):
            return None

    # ── 전 종목 · 전 날짜의 (수익, 특성) ──
    상, 하, 중 = [], [], []
    포착 = 놓침 = 0
    놓침특성 = []
    print("  훑는 중...", flush=True)
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        오늘 = []
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            g = 하루갭.get(code)
            if g is None:
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
            볼 = (c1 - s20) / (2 * sd)
            if sq[k - 20] <= 0 or sq[k - 60] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            r60 = (c1 / sq[k - 60] - 1) * 100
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            r = (끝[0] / 매수 - 1) * 100 - _비용
            fm = 재무값(code, d1)
            fr = (수급.get(d1) or {}).get(code) or {}
            오늘.append((r, {
                "상대갭": g - 시갭, "시장갭": 시갭, "볼린저": 볼,
                "20일수익": r20, "60일수익": r60,
                "시총(억)": 시총 / 1e8, "거래대금(억)": 대금 / 1e8,
                "잉여금비율": (fm or {}).get("잉여금비율"),
                "부채비율": (fm or {}).get("부채비율"),
                "ROE": (fm or {}).get("ROE"),
                "흑자": (fm or {}).get("흑자"),
                "외국인": 숫(fr.get("외국인")), "기관": 숫(fr.get("기관")),
            }, code, 다음))
        if len(오늘) < 100:
            continue
        오늘.sort(key=lambda x: -x[0])
        n = max(1, int(len(오늘) * _꼬리))
        상 += 오늘[:n]
        하 += 오늘[-n:]
        중 += 오늘[n:len(오늘) - n:37]      # 중간은 표본만
        # ⭐ 우리 신호가 상위 5%를 잡나
        for r, f, code, d in 오늘[:n]:
            잡 = (f["상대갭"] <= -3 and f["볼린저"] <= -1.0 and f["20일수익"] <= -10
                  and f["시총(억)"] < 3000
                  and (f["잉여금비율"] or -9e9) >= 30
                  and (f["부채비율"] or 9e9) <= 80 and f["흑자"] == 1.0)
            if 잡:
                포착 += 1
            else:
                놓침 += 1
                놓침특성.append(f)
        if i % 500 == 0:
            print(f"    {i}/{len(날)}일 · 상위 {len(상):,}", flush=True)

    print(f"\n  상위 5% {len(상):,}건 · 하위 5% {len(하):,}건 "
          f"· 중간표본 {len(중):,}건", flush=True)
    print(f"  상위 5%의 평균 수익 {st.mean([x[0] for x in 상]):+.2f}% "
          f"· 하위 5% {st.mean([x[0] for x in 하]):+.2f}% "
          f"· 중간 {st.mean([x[0] for x in 중]):+.2f}%")

    # ══ A 특성 비교 ══
    print("\n  ══ A **크게 오른 것 vs 크게 빠진 것**의 전날 특성 ══")
    print("     ⚠️ 「오른 종목은 이랬다」는 사실이지 **「이러면 오른다」가 아니다**")
    축 = list(상[0][1].keys())
    print(f"    {'특성':<14}{'상위5% 중앙':>13}{'하위5% 중앙':>13}"
          f"{'중간 중앙':>12}{'차이(상-하)':>13}{'방향':>8}")
    for a in 축:
        s = [x[1][a] for x in 상 if x[1].get(a) is not None]
        h = [x[1][a] for x in 하 if x[1].get(a) is not None]
        m = [x[1][a] for x in 중 if x[1].get(a) is not None]
        if len(s) < 200 or len(h) < 200:
            print(f"    {a:<14}표본 부족 ({len(s)}/{len(h)})")
            continue
        ss, hh, mm = st.median(s), st.median(h), st.median(m) if m else 0
        차 = ss - hh
        # 중간값 대비 어느 쪽으로 치우쳤나
        방 = "↑상승쪽" if (ss > mm and hh < mm) else (
            "↓하락쪽" if (ss < mm and hh > mm) else "  섞임")
        print(f"    {a:<14}{ss:>13,.2f}{hh:>13,.2f}{mm:>12,.2f}"
              f"{차:>13,.2f}{방:>8}")

    # ══ B 포착률 ══
    print("\n  ══ B ⭐ **우리 신호가 상위 5%를 몇 % 잡나** ══")
    총 = 포착 + 놓침
    print(f"    상위 5% {총:,}건 중")
    print(f"      우리 신호가 **잡은 것**   {포착:,}건 ({포착/max(1,총)*100:.2f}%)")
    print(f"      **놓친 것**             {놓침:,}건 ({놓침/max(1,총)*100:.2f}%)")
    print("    ⚠️ 포착률이 낮은 건 **당연하다** — 우리 신호는 연 14.5일뿐이다.")
    print("       중요한 건 **놓친 것들에 공통점이 있나**다. 아래를 본다")

    # ══ C 놓친 것들의 공통점 ══
    print("\n  ══ C ⭐⭐ **놓친 것들의 공통점** — 여기서 새 신호가 나온다 ══")
    print(f"    {'특성':<14}{'놓친 것 중앙':>14}{'전체상위 중앙':>14}"
          f"{'중간 중앙':>12}{'쏠림':>10}")
    for a in 축:
        n = [x[a] for x in 놓침특성 if x.get(a) is not None]
        s = [x[1][a] for x in 상 if x[1].get(a) is not None]
        m = [x[1][a] for x in 중 if x[1].get(a) is not None]
        if len(n) < 200 or len(m) < 100:
            continue
        nn, ss, mm = st.median(n), st.median(s), st.median(m)
        # 중간 대비 얼마나 치우쳤나 (사분위 폭으로 나눠 표준화)
        q = sorted(m)
        폭 = (q[len(q) * 3 // 4] - q[len(q) // 4]) or 1e-9
        z = (nn - mm) / 폭
        표 = ("⭐ 크게 위" if z > 0.5 else "⭐ 크게 아래" if z < -0.5
              else "  " if abs(z) < 0.2 else ("↑" if z > 0 else "↓"))
        print(f"    {a:<14}{nn:>14,.2f}{ss:>14,.2f}{mm:>12,.2f}{표:>10} (z={z:+.2f})")

    # ══ D 놓친 것 중 살 만한 것 ══
    print("\n  ══ D 놓친 것 중 **살 만한 것**이 있나 ══")
    살만 = [x for x in 놓침특성
            if x["거래대금(억)"] >= 1 and (x["시총(억)"] or 0) < 3000]
    print(f"    놓친 {len(놓침특성):,}건 중 소형·유동성 있는 것 {len(살만):,}건 "
          f"({len(살만)/max(1,len(놓침특성))*100:.1f}%)")
    if 살만:
        for a in ("상대갭", "볼린저", "20일수익", "60일수익", "잉여금비율", "부채비율"):
            v = [x[a] for x in 살만 if x.get(a) is not None]
            if len(v) < 100:
                continue
            r = 요약(v)
            print(f"      {a:<12}중앙 {r[2]:>9,.2f} · 25~75% "
                  f"{r[1]:>9,.2f} ~ {r[3]:>9,.2f}")

    print("\n  읽는 법")
    print("    - A에서 **↑상승쪽/↓하락쪽**이 뚜렷한 특성이 신호 후보다")
    print("    - **C가 핵심이다.** 놓친 것들이 한쪽으로 쏠려 있으면 그게 새 신호다")
    print("    - ⚠️⚠️ 여기서 찾은 건 **가설일 뿐이다.** 61차 걷기검증을 다시 해야 한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
