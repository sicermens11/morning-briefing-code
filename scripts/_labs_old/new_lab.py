#!/usr/bin/env python3
r"""
new_lab.py — **지금 신호와 겹치지 않는 새 신호를 찾는다** (2026-09-03 · 63차)

⚠️⚠️ **사용자가 넷 다 하라고 했다. 이게 넷째다.**
```
지금 신호  「재무 우량 소형주가 **빠졌을 때** 산다」  연 14.5일 · 투입비 17%
문제       자금의 83%가 논다. 강세장에서 지수에 크게 진다(2025년 -67.6%p)
⇒ **빈도를 늘리려면 겹치지 않는 신호가 필요하다.**
```

## 찾는 곳 — **아직 안 판 데이터**
```
수급      16.7년 완비 · 외국인 · 기관 · 개인 · 외국인지분율   ← 깊이 안 봤다
지수 71개  16.7년 완비                                    ← 57차에서 겉만 봤다
재무      11년 (2015~2025)                               ← 「빠진 것」에만 붙여 봤다
```

## 재는 것 — **지금 신호와 반대 방향도 본다**
```
A 모멘텀   20일 **+10%↑** · 볼린저 **상단** 돌파 + 재무 좋음
           ⚠️ 지금까지 「빠진 걸 산다」만 봤다. 오르는 걸 사는 건 안 봤다
B 수급     외국인/기관 20일 순매수 상위 + 재무 좋음
C 지분율   외국인지분율 20일 급증
D 재무만   기술 조건 **없이** 재무 좋은 것 (시장 하락일에만)
E 겹침     A~D가 **지금 신호와 같은 날**에 나오나 — 겹치면 자금이 안 는다
```
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · D+20 · 비용 0.26% · **날짜 단위** · 연도별 3분의 2.
⚠️ 재무 조건은 **고정 숫자**(잉여금 ≥30% · 부채비율 ≤80% · 흑자) — 61차에서 확인한 값.
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


def 재기(날별, 이름, 년수, 폭=36):
    if len(날별) < 8:
        print(f"    {이름:<{폭}}신호일 {len(날별)}일 — 부족")
        return None
    수 = [st.mean(v) for v in 날별.values()]
    승 = sum(1 for x in 수 if x > 0) / len(수) * 100
    해 = {}
    for d, v in 날별.items():
        해.setdefault(d[:4], []).append(st.mean(v))
    전 = 플 = 0
    for y, arr in 해.items():
        if len(arr) < 3:
            continue
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
    a = sorted(수)
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 8
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/년수:>7.1f}일{f'{플}/{전}':>8}{len(날별):>7}일{별}")
    return set(날별)


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

    def 좋재무(fm):
        return bool(fm) and fm.get("잉여금비율", -9e9) >= 30 \
            and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0

    def 숫(x):
        try:
            return float(str(x).replace(",", "").replace("%", ""))
        except (TypeError, ValueError):
            return None

    # ── 후보: 조건 없이 넓게 모은다 (시장갭·상대갭·볼·20일·수급·재무) ──
    후보 = []
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
        # 수급 20일 누적
        창 = 날[max(0, i - 19):i + 1]
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
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
            if sq[k - 20] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            외 = 기 = 0.0
            지분0 = 지분1 = None
            for j, dd in enumerate(창):
                fr = (수급.get(dd) or {}).get(code)
                if not fr:
                    continue
                외 += 숫(fr.get("외국인")) or 0
                기 += 숫(fr.get("기관")) or 0
                z = 숫(fr.get("외국인지분율"))
                if z is not None:
                    if 지분0 is None:
                        지분0 = z
                    지분1 = z
            지분변 = (지분1 - 지분0) if (지분0 is not None and 지분1 is not None) else None
            후보.append((다음, code, (끝[0] / 매수 - 1) * 100 - _비용,
                         g - 시갭, 시갭, 볼, r20,
                         재무값(code, d1), 외, 기, 지분변, 시총))
        if i % 800 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  후보 {len(후보):,}건 · {년수:.1f}년\n", flush=True)

    def 모으기(cond):
        t = {}
        for x in 후보:
            if cond(x):
                t.setdefault(x[0], []).append(x[2])
        return t

    머 = (f"    {'조합':<36}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'신호일':>8}")

    print("  ══ 기준: 지금 신호 (재무 우량 + 빠진 것) ══")
    print(머)
    지금 = 재기(모으기(lambda x: x[3] <= -3 and x[5] <= -1.0 and x[6] <= -10
                       and 좋재무(x[7])), "**지금 신호**", 년수)

    print("\n  ══ A 모멘텀 — **오르는 걸 산다** (지금까지 안 본 방향) ══")
    print(머)
    모 = {}
    for 볼문, r문, 라 in ((1.0, 10, "볼상단+1.0 · 20일 +10%↑"),
                          (1.0, 20, "볼상단+1.0 · 20일 +20%↑"),
                          (0.5, 10, "볼+0.5 · 20일 +10%↑"),
                          (1.5, 30, "볼상단+1.5 · 20일 +30%↑")):
        s = 재기(모으기(lambda x, b=볼문, r=r문: x[5] >= b and x[6] >= r
                       and 좋재무(x[7])), f"모멘텀 {라} + 재무", 년수)
        if s and 라.startswith("볼상단+1.0 · 20일 +10"):
            모 = s
    재기(모으기(lambda x: x[5] >= 1.0 and x[6] >= 10 and not 좋재무(x[7])),
         "  (견줌) 모멘텀 · 재무 나쁨", 년수)

    print("\n  ══ B 수급 — 외국인·기관 20일 순매수 ══")
    print(머)
    외값 = sorted(x[8] for x in 후보 if x[8])
    기값 = sorted(x[9] for x in 후보 if x[9])
    if len(외값) > 1000:
        외상 = 외값[len(외값) * 9 // 10]
        기상 = 기값[len(기값) * 9 // 10]
        print(f"    (문턱: 외국인 상위10% ≥{외상:,.0f} · 기관 상위10% ≥{기상:,.0f})")
        재기(모으기(lambda x: x[8] >= 외상 and 좋재무(x[7])),
             "외국인 순매수 상위10% + 재무", 년수)
        재기(모으기(lambda x: x[9] >= 기상 and 좋재무(x[7])),
             "기관 순매수 상위10% + 재무", 년수)
        재기(모으기(lambda x: x[8] >= 외상 and x[9] >= 기상 and 좋재무(x[7])),
             "**외국인+기관 둘 다** + 재무", 년수)
        재기(모으기(lambda x: x[8] >= 외상 and x[9] >= 기상 and 좋재무(x[7])
                   and x[5] <= -0.5), "  위 + 볼린저 하단쪽(−0.5)", 년수)

    print("\n  ══ C 외국인지분율 20일 변화 ══")
    print(머)
    지값 = sorted(x[10] for x in 후보 if x[10] is not None)
    if len(지값) > 1000:
        상 = 지값[len(지값) * 95 // 100]
        하 = 지값[len(지값) * 5 // 100]
        print(f"    (문턱: 상위5% ≥{상:+.2f}%p · 하위5% ≤{하:+.2f}%p)")
        재기(모으기(lambda x: x[10] is not None and x[10] >= 상 and 좋재무(x[7])),
             f"지분율 급증(≥{상:+.2f}%p) + 재무", 년수)
        재기(모으기(lambda x: x[10] is not None and x[10] <= 하 and 좋재무(x[7])),
             f"지분율 급감(≤{하:+.2f}%p) + 재무", 년수)

    print("\n  ══ D 재무만 — **기술 조건 없이** ══")
    print(머)
    재기(모으기(lambda x: 좋재무(x[7])), "재무 좋은 것 전부 (기술 무관)", 년수)
    재기(모으기(lambda x: 좋재무(x[7]) and x[4] < -0.6),
         "재무 좋은 것 · 시장 −0.6%↓ 인 날", 년수)
    재기(모으기(lambda x: 좋재무(x[7]) and x[3] <= -3),
         "재무 좋은 것 · 상대갭 −3%p↓", 년수)

    print("\n  ══ E 겹침 — **지금 신호와 같은 날에 나오나** ══")
    print("     ⚠️ 겹치면 합쳐도 자금이 안 는다")
    if 지금:
        후보들 = {
            "모멘텀(볼+1.0·20일+10%)":
                모으기(lambda x: x[5] >= 1.0 and x[6] >= 10 and 좋재무(x[7])),
            "재무+시장−0.6":
                모으기(lambda x: 좋재무(x[7]) and x[4] < -0.6),
        }
        if len(외값) > 1000:
            후보들["외국인+기관 상위10%"] = 모으기(
                lambda x: x[8] >= 외상 and x[9] >= 기상 and 좋재무(x[7]))
        print(f"    {'신호':<36}{'그 신호 날':>10}{'겹치는 날':>10}{'겹침률':>9}"
              f"{'합치면':>9}")
        for 라, t in 후보들.items():
            s = set(t)
            겹 = len(s & 지금)
            합 = len(s | 지금)
            print(f"    {라:<36}{len(s):>10}{겹:>10}{겹/max(1,len(s))*100:>8.1f}%"
                  f"{합:>9}일")
        print(f"    {'(지금 신호 단독)':<36}{len(지금):>10}")

    print("\n  읽는 법")
    print("    - **겹침률이 낮고 성적이 좋은 것**이 찾던 것이다 — 자금을 더 쓴다")
    print("    - A의 모멘텀이 되면 「빠진 걸 산다」와 **반대 국면**을 덮는다")
    print("    - ⚠️ 조합을 많이 봤다. 좋은 게 나오면 **걷기검증을 다시 해야 한다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
