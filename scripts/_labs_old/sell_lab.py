#!/usr/bin/env python3
r"""
sell_lab.py — **언제 팔 것인가** (2026-09-03 · 76차)

⚠️⚠️ **한 번도 검증한 적 없는 가정을 검증한다.**
   지금까지 모든 시험이 **「D+20에 무조건 판다, 손절 없다」**를 전제로 했다.
   그게 최적인지 **한 번도 안 재봤다.** 실제 매매에 직결되는 부분이다.

## 우리 신호 (61·72차에서 확정)
```
잉여금비율 >=30% · 부채비율 <=80% · 흑자 · 소형주
+ 상대갭 -3%p 이하 + 볼린저 -1.0σ + 20일 -10% 이하
→ 다음날 **시가** 매수
```

## 재는 것 — **파는 방법 8가지**
```
A 정해진 날     D+5 · 10 · 20 · 30 · 40 · 60
B 손절         -5% · -8% · -10% · -15%  (그날 **저가**가 닿으면 판다)
C 목표가        +10% · +15% · +20% · +30% 닿으면 판다
D 손절+목표      둘을 같이
E 트레일링      고점 대비 -5% · -8% · -10% 빠지면 판다
F 조건 청산     볼린저 중심선 회복 / 20일선 회복
```
⚠️⚠️ **look-ahead 주의.** 손절·목표가는 **그날 저가/고가**로 판정한다.
   장중에 닿았는지는 **장이 끝나야** 알지만, 실제 매매에서는 **지정가 주문**으로
   장중에 체결된다. 그래서 저가/고가 사용이 맞다.
   ⚠️ 다만 **같은 날 저가와 고가를 둘 다 쓰면** 어느 쪽이 먼저인지 모른다.
      ⇒ **손절을 먼저** 본다(보수적). 실제로는 더 나을 수 있다.
⚠️ 판정: 절대 수익 · 비용 0.26% · **날짜 단위**와 **자본 시뮬** 둘 다.
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
_시작 = "20160401"
_최대 = 60      # 최대 보유일


def 재기(날별, 이름, 년수, 폭=30):
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
    종 = sum(len(v) for v in 날별.values())
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{f'{플}/{전}':>8}{len(날별):>7}일{종:>7}건{별}")
    return st.mean(수)


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # ⚠️ 손절·목표가에 쓸 **수정 저가·고가**가 필요하다.
    #    원본 저가/고가를 그날 종가 대비 비율로 바꿔 수정종가에 곱한다
    저비, 고비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                저 = float(v.get("저가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                if 종 <= 0 or 시 <= 0 or 저 <= 0 or 고 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            저비.setdefault(d8, {})[c] = 저 / 종
            고비.setdefault(d8, {})[c] = 고 / 종
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

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

    # ── 신호 + 이후 60일 경로 ──
    # ⚠️ 걷기검증을 하려면 **재무값을 같이 담아야** 해마다 문턱을 다시 걸 수 있다
    사건, 사건상세, 재무값들 = [], [], []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _최대 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
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
            # ⚠️⚠️ 여기서 재무 문턱(30/80)을 걸면 **걷기검증이 무의미해진다** —
            #   문턱을 뽑을 모집단이 이미 그 문턱을 통과한 것만 남기 때문이다.
            #   ⇒ **흑자만 걸어 담고**, 30/80은 아래에서 `사건`에만 건다
            fm = 재무값(code, d1)
            if not (fm and fm.get("흑자") == 1.0):
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
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            # 이후 60일 경로: (종가, 저가, 고가) — 전부 수정 기준
            길 = []
            ok = True
            for h in range(1, _최대 + 1):
                j = i + 1 + h
                if j >= len(날):
                    ok = False
                    break
                dd = 날[j]
                v2 = 주가[dd].get(code)
                if not v2:
                    ok = False
                    break
                종2 = v2[0]
                lo = (저비.get(dd) or {}).get(code, 1.0) * 종2
                hi = (고비.get(dd) or {}).get(code, 1.0) * 종2
                길.append((종2, lo, hi))
            if not ok or len(길) < _최대:
                continue
            # 매수 당일(다음)의 저가·고가도 필요하다 — 시가에 샀으니 그날부터 위험
            v0 = 주가[다음].get(code)
            if v0:
                종0 = v0[0]
                길.insert(0, (종0,
                              (저비.get(다음) or {}).get(code, 1.0) * 종0,
                              (고비.get(다음) or {}).get(code, 1.0) * 종0))
            # `사건`= 고정 문턱(30/80) 통과분 · `사건상세`= 흑자만 통과한 전부(걷기용)
            사건상세.append((다음, code, 매수, 길, fm))
            재무값들.append((다음, fm.get("잉여금비율"), fm.get("부채비율")))
            if (fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80):
                사건.append((다음, code, 매수, 길))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  사건 {len(사건):,}건 · {년수:.1f}년\n", flush=True)

    def 팔기(길, 매수, 최대일, 손절=None, 목표=None, 트레일=None,
             중심회복=False):
        """길: [(종가, 저가, 고가)] · 돌려주는 값: (수익%, 보유일)"""
        고점 = 매수
        for h, (종2, lo, hi) in enumerate(길[:최대일], 1):
            # ⚠️ 손절을 먼저 본다 (같은 날 저가·고가 순서를 모르므로 보수적으로)
            if 손절 is not None and lo <= 매수 * (1 + 손절 / 100):
                return 손절 - _비용, h
            if 트레일 is not None:
                고점 = max(고점, hi)
                if lo <= 고점 * (1 + 트레일 / 100):
                    return (고점 * (1 + 트레일 / 100) / 매수 - 1) * 100 - _비용, h
            if 목표 is not None and hi >= 매수 * (1 + 목표 / 100):
                return 목표 - _비용, h
        끝 = 길[min(최대일, len(길)) - 1][0]
        return (끝 / 매수 - 1) * 100 - _비용, min(최대일, len(길))

    def 모으기(**kw):
        t, 보유 = {}, []
        for d, code, 매수, 길 in 사건:
            r, h = 팔기(길, 매수, **kw)
            t.setdefault(d, []).append(r)
            보유.append(h)
        return t, st.mean(보유)

    머 = (f"    {'방법':<30}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연도별':>8}{'신호일':>8}{'건수':>7}")
    print("  ══ A **정해진 날에 판다** (지금 방식) ══")
    print(머)
    for h in (5, 10, 20, 30, 40, 60):
        t, 평보 = 모으기(최대일=h)
        재기(t, f"D+{h}", 년수)

    print("\n  ══ B **손절** (그날 저가가 닿으면) · 최대 D+20 ══")
    print(머)
    for s in (-5, -8, -10, -15):
        t, 평보 = 모으기(최대일=20, 손절=s)
        재기(t, f"손절 {s}% (평균보유 {평보:.1f}일)", 년수)

    print("\n  ══ C **목표가** (그날 고가가 닿으면) · 최대 D+20 ══")
    print(머)
    for g in (10, 15, 20, 30):
        t, 평보 = 모으기(최대일=20, 목표=g)
        재기(t, f"목표 +{g}% (평균보유 {평보:.1f}일)", 년수)

    print("\n  ══ D **손절 + 목표** 같이 · 최대 D+20 ══")
    print(머)
    for s, g in ((-8, 15), (-8, 20), (-10, 20), (-10, 30), (-15, 30)):
        t, 평보 = 모으기(최대일=20, 손절=s, 목표=g)
        재기(t, f"손절{s}% + 목표+{g}% ({평보:.1f}일)", 년수)

    print("\n  ══ E **트레일링** (고점 대비) · 최대 D+40 ══")
    print(머)
    for tr in (-5, -8, -10, -15):
        t, 평보 = 모으기(최대일=40, 트레일=tr)
        재기(t, f"트레일 {tr}% ({평보:.1f}일)", 년수)
    for tr in (-8, -10):
        t, 평보 = 모으기(최대일=60, 트레일=tr)
        재기(t, f"트레일 {tr}% · 최대D+60 ({평보:.1f}일)", 년수)

    # ⚠️⚠️ **평균 수익만 보면 안 된다.** 목표 +10%는 평균이 +5.04%로 D+20(+9.75%)의
    #   절반이지만 **평균 보유가 6.4일**로 3분의 1이다. 자금이 3배 빨리 돌아온다.
    #   ⇒ 「투입비 17%」 문제와 직결된다. **자본 시뮬로 판정한다.**
    print("\n  ══ ⭐ **자본 시뮬** — 자금 회전까지 넣으면 뭐가 이기나 ══")
    print("     초기 500만원 · 종목당 자산의 20% · 거래대금 1% 상한")
    날인 = {d: i for i, d in enumerate(날)}

    def 자본(이름, 최대일, 끝날="20260902", **kw):
        살것 = {}
        for d, code, 매수, 길 in 사건:
            r, h = 팔기(길, 매수, 최대일=최대일, **kw)
            살것.setdefault(d, []).append((code, 매수, r, h))
        현금, 보유, 기록, 투입 = 5_000_000.0, [], [], []
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            남 = []
            for 청산i, 금, 수익률 in 보유:
                if 청산i <= i:
                    현금 += 금 * (1 + 수익률 / 100)
                else:
                    남.append((청산i, 금, 수익률))
            보유 = 남
            평가 = 현금 + sum(금 for _, 금, _ in 보유)
            for code, 매수, r, h in 살것.get(d) or []:
                v = 주가[d].get(code)
                쓸 = min(평가 * 0.20, (v[2] if v else 0) * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                보유.append((min(i + h, len(날) - 1), 쓸, r))
            기록.append((d, 평가))
            투입.append(sum(금 for _, 금, _ in 보유) / 평가 if 평가 > 0 else 0)
        마지막 = 기록[-1][1] if 기록 else 5_000_000.0
        해 = len(기록) / 245
        연 = ((마지막 / 5_000_000.0) ** (1 / 해) - 1) * 100 if 마지막 > 0 else -100
        최고, 낙폭 = 5_000_000.0, 0.0
        for _, v in 기록:
            최고 = max(최고, v)
            낙폭 = min(낙폭, v / 최고 - 1)
        해별 = {}
        for d, v in 기록:
            해별.setdefault(d[:4], []).append(v)
        플 = 전 = 0
        for y in sorted(해별):
            a = 해별[y]
            if len(a) < 60:
                continue
            전 += 1
            플 += 1 if a[-1] > a[0] else 0
        print(f"    {이름:<30}{마지막:>13,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{sum(투입)/max(1,len(투입))*100:>8.1f}%{f'{플}/{전}':>8}")

    print(f"    {'방법':<30}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
          f"{'투입비':>8}{'연도별':>8}")
    자본("D+20 (지금 방식)", 20)
    자본("D+30", 30)
    자본("D+40", 40)
    자본("**목표 +10%** (최대D+20)", 20, 목표=10)
    자본("**목표 +10%** (최대D+40)", 40, 목표=10)
    자본("목표 +15% (최대D+40)", 40, 목표=15)
    자본("목표 +20% (최대D+40)", 40, 목표=20)
    자본("손절-10% + 목표+20%", 20, 손절=-10, 목표=20)

    # ⚠️⚠️ **오늘 62·64·72차에서 이 두 검증에 걸려 결론이 세 번 뒤집혔다.**
    #   낙폭 -6~9%는 너무 좋다 — 반드시 확인한다
    print("\n  ══ ⚠️ **2025·26을 뺀 판** (2016-04 ~ 2024-12) ══")
    print(f"    {'방법':<30}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
          f"{'투입비':>8}{'연도별':>8}")
    for 이름, 최대, kw in (("D+20 (지금 방식)", 20, {}), ("D+40", 40, {}),
                            ("목표 +10% (최대D+40)", 40, {"목표": 10}),
                            ("목표 +15% (최대D+40)", 40, {"목표": 15}),
                            ("목표 +20% (최대D+40)", 40, {"목표": 20})):
        자본(이름, 최대, 끝날="20241230", **kw)

    # ── 걷기검증: 그 해 이전만 보고 재무 문턱을 정한다 ──
    print("\n  ══ ⭐ **걷기검증** — 그 해 이전만 보고 문턱을 정한다 ══")
    print("     ⚠️ 매도 규칙(목표가)은 문턱이 아니라 **규칙**이라 걷기 대상이 아니다.")
    print("        재무 문턱만 해마다 다시 뽑는다")
    해들 = sorted({x[0][:4] for x in 사건})
    문턱 = {}
    for y in 해들:
        앞 = [x for x in 재무값들 if x[0][:4] < y]
        잉 = sorted(a for _, a, b in 앞 if a is not None)
        부 = sorted(b for _, a, b in 앞 if b is not None)
        if len(잉) >= 200 and len(부) >= 200:
            문턱[y] = (잉[len(잉) // 2], 부[len(부) // 2])

    def 자본걷기(이름, 최대일, 끝날="20260902", **kw):
        살것 = {}
        for d, code, 매수, 길, fm in 사건상세:
            t = 문턱.get(d[:4])
            if not t:
                continue
            if not (fm.get("잉여금비율", -9e9) >= t[0]
                    and fm.get("부채비율", 9e9) <= t[1]):
                continue
            r, h = 팔기(길, 매수, 최대일=최대일, **kw)
            살것.setdefault(d, []).append((code, 매수, r, h))
        현금, 보유, 기록, 투입 = 5_000_000.0, [], [], []
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            남 = []
            for 청산i, 금, 수익률 in 보유:
                if 청산i <= i:
                    현금 += 금 * (1 + 수익률 / 100)
                else:
                    남.append((청산i, 금, 수익률))
            보유 = 남
            평가 = 현금 + sum(금 for _, 금, _ in 보유)
            for code, 매수, r, h in 살것.get(d) or []:
                v = 주가[d].get(code)
                쓸 = min(평가 * 0.20, (v[2] if v else 0) * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                보유.append((min(i + h, len(날) - 1), 쓸, r))
            기록.append((d, 평가))
            투입.append(sum(금 for _, 금, _ in 보유) / 평가 if 평가 > 0 else 0)
        마지막 = 기록[-1][1] if 기록 else 5_000_000.0
        해 = len(기록) / 245
        연 = ((마지막 / 5_000_000.0) ** (1 / 해) - 1) * 100 if 마지막 > 0 else -100
        최고, 낙폭 = 5_000_000.0, 0.0
        for _, v in 기록:
            최고 = max(최고, v)
            낙폭 = min(낙폭, v / 최고 - 1)
        해별 = {}
        for d, v in 기록:
            해별.setdefault(d[:4], []).append(v)
        플 = 전 = 0
        for y in sorted(해별):
            a = 해별[y]
            if len(a) < 60:
                continue
            전 += 1
            플 += 1 if a[-1] > a[0] else 0
        print(f"    {이름:<30}{마지막:>13,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{sum(투입)/max(1,len(투입))*100:>8.1f}%{f'{플}/{전}':>8}")

    print(f"    {'방법':<30}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
          f"{'투입비':>8}{'연도별':>8}")
    for 끝날, 라 in (("20260902", "10.4년"), ("20241230", "8.8년")):
        print(f"    ── {라} ──")
        자본걷기("D+20 · 걷기", 20, 끝날=끝날)
        자본걷기("D+40 · 걷기", 40, 끝날=끝날)
        자본걷기("**목표+20%(D+40) · 걷기**", 40, 끝날=끝날, 목표=20)

    print("\n  ══ 견줌 — 지금 방식(D+20)과 나란히 ══")
    t20, _ = 모으기(최대일=20)
    기준 = st.mean([st.mean(v) for v in t20.values()])
    print(f"    지금 방식 D+20 = {기준:+.2f}% (날짜 단위)")
    print("    위 표에서 **이보다 높고 연도별이 통과**하는 것만 쓸 값어치가 있다")

    print("\n  읽는 법")
    print("    - ⚠️ 손절·목표가는 **그날 저가/고가**로 판정했다. 지정가 주문을 전제한다")
    print("    - ⚠️ 같은 날 저가와 고가 중 **어느 쪽이 먼저인지 모른다** →")
    print("       **손절을 먼저** 봤다(보수적). 실제로는 더 나을 수 있다")
    print("    - **평균보유일**이 짧으면 자금 회전이 빨라진다 — 자본 시뮬에서 유리하다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
