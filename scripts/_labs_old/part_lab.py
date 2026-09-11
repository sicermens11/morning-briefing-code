#!/usr/bin/env python3
r"""
part_lab.py — **나눠서 팔면 어떤가 (부분 매도)** (2026-09-03 · 83차)

⚠️⚠️ **81차에서 이게 나왔다.**
```
진 것 104건 중
  **+10% 넘게 갔다가 꺾인 것: 52건 = 50%**
  한 번도 +5% 못 간 것: 14건 (13%)
⇒ **진 것의 절반은 한 번 이겼던 것**이다. +20%를 기다리다 놓쳤다
```

## 76차에서 이미 보였던 실마리
```
목표 +10%  평균 +5.04% · **승률 82.1%** · 하위25% **+3.45%** · 11/11 · 보유 6.4일
목표 +20%  평균 +7.30% · 승률 76.6% · 하위25% +0.88% · 10/11 · 보유 13.4일
자본 시뮬  +10% -> 연 +22.79% / **+20% -> 연 +26.66%**
⇒ **+10%는 자주 이기고 적게 벌고, +20%는 덜 이기고 크게 번다**
⇒ 둘을 **섞으면** 어떨까? 그게 이 시험이다
```

## 재는 것
```
A 반반        절반은 +10%에, 나머지 절반은 +20%에
B 3분할       3분의 1씩 +10% · +20% · D+40
C 비율 조정    +10%에 30% / 50% / 70%를 팔면
D 문턱 조정    +8/+12 · +10/+25 · +15/+30 같은 조합
E 트레일링 결합 절반은 +10%에 팔고, 나머지는 고점 대비 -10%에
F ⭐ 자본 시뮬  실제로 돈이 더 느나 (최종 판정)
```
⚠️ 매수는 80차 확인대로 **다음날 시가**. 하루 최대 2종목 · 자산의 20%씩.
⚠️ 판정: 자본 시뮬 · 낙폭 · 연도별 · **2025·26 뺀 판**까지.
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
_최대보유 = 40


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    날인 = {d: i for i, d in enumerate(날)}
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}
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
                if min(종, 시, 저, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종, 저 / 종, 고 / 종)
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

    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _최대보유 >= len(날):
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
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            # 경로: (종가, 저가, 고가) — 매수일부터 D+40까지
            길 = []
            ok = True
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    ok = False
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    ok = False
                    break
                길.append((vv[0], vv[0] * bb2[1], vv[0] * bb2[2]))
            if not ok:
                continue
            사건.append({"날": 다음, "code": code, "매수": 매수, "길": 길,
                        "상대갭": g - 시갭, "대금": 대금, "i": i + 1})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    날별 = {}
    for x in 사건:
        날별.setdefault(x["날"], []).append(x)
    print(f"  사건 {len(사건):,}건 · 신호일 {len(날별)}일 · {년수:.1f}년\n", flush=True)

    def 팔기(x, 단계):
        """단계 = [(목표%, 비율), ...] · 나머지는 D+40 종가.
        돌려주는 값: (가중 수익%, 마지막 청산일수)"""
        매수 = x["매수"]
        남은 = 1.0
        수익 = 0.0
        끝일 = _최대보유
        미달 = list(단계)
        for h, (종2, 저2, 고2) in enumerate(x["길"], 0):
            새 = []
            for 목표, 비율 in 미달:
                if 고2 >= 매수 * (1 + 목표 / 100) and 남은 >= 비율 - 1e-9:
                    수익 += 비율 * (목표 - _비용)
                    남은 -= 비율
                    끝일 = max(1, h)
                else:
                    새.append((목표, 비율))
            미달 = 새
            if 남은 <= 1e-9:
                return 수익, 끝일
        if 남은 > 0:
            끝 = x["길"][min(_최대보유, len(x["길"])) - 1][0]
            수익 += 남은 * ((끝 / 매수 - 1) * 100 - _비용)
            끝일 = _최대보유
        return 수익, 끝일

    def 트레일팔기(x, 첫목표, 첫비율, 트레일):
        """첫 목표에 일부 팔고, 나머지는 고점 대비 트레일%에서 판다."""
        매수 = x["매수"]
        남은, 수익, 끝일 = 1.0, 0.0, _최대보유
        판첫 = False
        고점 = 매수
        for h, (종2, 저2, 고2) in enumerate(x["길"], 0):
            고점 = max(고점, 고2)
            if not 판첫 and 고2 >= 매수 * (1 + 첫목표 / 100):
                수익 += 첫비율 * (첫목표 - _비용)
                남은 -= 첫비율
                판첫 = True
                끝일 = max(1, h)
            if 판첫 and 남은 > 0 and 저2 <= 고점 * (1 + 트레일 / 100):
                수익 += 남은 * ((고점 * (1 + 트레일 / 100) / 매수 - 1) * 100 - _비용)
                return 수익, max(1, h)
        if 남은 > 0:
            끝 = x["길"][min(_최대보유, len(x["길"])) - 1][0]
            수익 += 남은 * ((끝 / 매수 - 1) * 100 - _비용)
        return 수익, 끝일

    def 재기(팔기함수, 라):
        t, 보유 = {}, []
        for x in 사건:
            r, h = 팔기함수(x)
            t.setdefault(x["날"], []).append(r)
            보유.append(h)
        수 = [st.mean(v) for v in t.values()]
        승 = sum(1 for z in 수 if z > 0) / len(수) * 100
        해 = {}
        for d, v in t.items():
            해.setdefault(d[:4], []).append(st.mean(v))
        전 = 플 = 0
        for y, arr in 해.items():
            if len(arr) < 3:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        a = sorted(수)
        print(f"    {라:<34}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
              f"{f'{플}/{전}':>8}{st.mean(보유):>7.1f}일")

    머 = (f"    {'매도 방법':<34}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연도별':>8}{'보유':>8}")
    print("  ══ 기준선 — 한 번에 파는 방법 (76차) ══")
    print(머)
    재기(lambda x: 팔기(x, [(10, 1.0)]), "목표 +10% 전량")
    재기(lambda x: 팔기(x, [(15, 1.0)]), "목표 +15% 전량")
    재기(lambda x: 팔기(x, [(20, 1.0)]), "**목표 +20% 전량** (지금)")
    재기(lambda x: 팔기(x, [(30, 1.0)]), "목표 +30% 전량")
    재기(lambda x: 팔기(x, []), "목표 없음 · D+40만")

    print("\n  ══ A **반반** — 절반은 낮게, 절반은 높게 ══")
    print(머)
    for a, b in ((10, 20), (10, 30), (12, 25), (15, 30), (8, 20)):
        재기(lambda x, p=a, q=b: 팔기(x, [(p, 0.5), (q, 0.5)]),
             f"절반 +{a}% · 절반 +{b}%")

    print("\n  ══ B **3분할** ══")
    print(머)
    재기(lambda x: 팔기(x, [(10, 1 / 3), (20, 1 / 3)]),
         "1/3 +10% · 1/3 +20% · 1/3 D+40")
    재기(lambda x: 팔기(x, [(10, 1 / 3), (20, 1 / 3), (35, 1 / 3)]),
         "1/3 +10% · 1/3 +20% · 1/3 +35%")
    재기(lambda x: 팔기(x, [(8, 1 / 3), (15, 1 / 3), (25, 1 / 3)]),
         "1/3 +8% · 1/3 +15% · 1/3 +25%")

    print("\n  ══ C **비율 조정** (+10%에 얼마나 팔까) ══")
    print(머)
    # >>> 오타 수정. f-string의 q는 lambda 밖이라 정의되지 않는다. p를 쓴다
    for p in (0.3, 0.5, 0.7):
        재기(lambda x, q=p: 팔기(x, [(10, q), (20, 1 - q)]),
             f"+10%에 {p*100:.0f}% · +20%에 {(1-p)*100:.0f}%")

    print("\n  ══ E **트레일링 결합** — 절반 익절 후 나머지는 고점 추적 ══")
    print(머)
    for 첫, 비, tr in ((10, 0.5, -10), (10, 0.5, -15), (15, 0.5, -10),
                       (10, 0.3, -10)):
        재기(lambda x, a=첫, b=비, c=tr: 트레일팔기(x, a, b, c),
             f"+{첫}%에 {비*100:.0f}% · 나머지 트레일 {tr}%")

    # ══ F 자본 시뮬 ══
    print("\n  ══ F ⭐ **자본 시뮬** — 실제로 돈이 더 느나 ══")
    print("     초기 500만 · 종목당 20% · 하루 최대 2종목")

    def 자본(팔기함수, 이름, 끝날="20260902"):
        현금, 보유, 기록, 투입 = 5_000_000.0, [], [], []
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            남 = []
            for 청산i, 금, r in 보유:
                if 청산i <= i:
                    현금 += 금 * (1 + r / 100)
                else:
                    남.append((청산i, 금, r))
            보유 = 남
            평가 = 현금 + sum(금 for _, 금, _ in 보유)
            for x in sorted(날별.get(d) or [], key=lambda z: z["상대갭"])[:2]:
                r, h = 팔기함수(x)
                쓸 = min(평가 * 0.20, x["대금"] * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                보유.append((min(x["i"] + h, len(날) - 1), 쓸, r))
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
        print(f"    {이름:<34}{마지막:>14,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{sum(투입)/max(1,len(투입))*100:>8.1f}%{f'{플}/{전}':>8}")

    for 끝날, 라벨 in (("20260902", "10.4년"),
                       ("20241230", "8.8년 — **2025·26 뺀 판**")):
        print(f"\n    ══ {라벨} ══")
        print(f"    {'매도 방법':<34}{'끝 자산':>15}{'연평균':>8}{'최대낙폭':>9}"
              f"{'투입비':>8}{'연도별':>8}")
        자본(lambda x: 팔기(x, [(10, 1.0)]), "목표 +10% 전량", 끝날)
        자본(lambda x: 팔기(x, [(20, 1.0)]), "**목표 +20% 전량** (지금)", 끝날)
        자본(lambda x: 팔기(x, [(10, 0.5), (20, 0.5)]), "절반 +10% · 절반 +20%", 끝날)
        자본(lambda x: 팔기(x, [(10, 0.5), (30, 0.5)]), "절반 +10% · 절반 +30%", 끝날)
        자본(lambda x: 팔기(x, [(10, 1 / 3), (20, 1 / 3), (35, 1 / 3)]),
             "1/3씩 +10 · +20 · +35", 끝날)
        자본(lambda x: 트레일팔기(x, 10, 0.5, -10),
             "+10%에 절반 · 나머지 트레일 -10%", 끝날)

    print("\n  읽는 법")
    print("    - **F가 최종 판정이다.** 평균만 보면 안 된다 (오늘 여러 번 겪었다)")
    print("    - ⚠️ 2025·26 뺀 판에서도 나아야 한다")
    print("    - **보유일**이 짧으면 자금 회전이 빨라져 자본 시뮬에서 유리하다")
    print("    - ⚠️ 부분 매도는 **수수료가 두 번** 든다. 비용에 이미 반영했다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
