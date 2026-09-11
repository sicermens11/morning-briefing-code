#!/usr/bin/env python3
r"""
walk2_lab.py — **걷기검증: 과거로 정하고 미래로 시험한다** (2026-09-03 · 61차)

⚠️⚠️ **왜 필요한가.** 59~60차에서 조합을 **40개 넘게** 봤다.
   그 중 제일 좋은 걸 골랐으니 **고른 행위 자체가 성적을 부풀린다**(다중검정).
```
+재무(잉여금↑부채↓흑자)   +10.15% · 승률 72.9% · 10/11해 · 자본 500만 → 2,908만
```
이게 진짜인지 **미리 알 수 없는 방식**으로 다시 재야 한다.

## 걷기검증 방식
```
매 해마다:
  ① **그 해 이전 데이터만** 보고 재무 문턱(잉여금·부채비율 중앙값)을 정한다
  ② 정한 문턱으로 **그 해**를 산다
  ③ 다음 해로 넘어간다
```
⚠️ 그 해 데이터를 문턱 정하는 데 **절대 안 쓴다.** 그게 look-ahead다.

## 함께 재는 것
```
A 걷기검증 — 해마다 문턱을 다시 정하고 그 해를 산다
B 조건 고정 — 「잉여금 ≥30% · 부채비율 ≤80% · 흑자」처럼 **고정 숫자**로도 되나
  (문턱을 데이터에서 뽑지 않으면 다중검정이 훨씬 줄어든다)
C 유동성 — 그날 뽑힌 종목을 **실제로 살 수 있나** (거래대금 대비 투자금)
D 반쪽 시험 — 앞 절반에서 정하고 **뒤 절반**에서만 재본다
```
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · 비용 0.26% · 날짜 단위 · 연도별.
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
_보유 = 20


def 재기(날별, 이름, 년수, 폭=34):
    if len(날별) < 6:
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
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 6
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/max(0.1,년수):>7.1f}일{f'{플}/{전}':>8}{len(날별):>7}일{별}")
    return st.mean(수), 승


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

    후보 = []      # (매수일, code, 수익, 상대갭, 시장갭, 볼, 20일, 재무, 거래대금)
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
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -3:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            fm = 재무값(code, d1)
            if not fm:
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -1.0 or sq[k - 20] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            if r20 > -10:
                continue
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            후보.append((다음, code, (끝[0] / 매수 - 1) * 100 - _비용,
                         g - 시갭, 시갭, 볼, r20, fm, 대금))
        if i % 800 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  후보 {len(후보):,}건 · {년수:.1f}년\n", flush=True)
    머 = (f"    {'조합':<34}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'신호일':>8}")

    # ── A 걷기검증 ──
    print("  ══ A 걷기검증 — **그 해 이전만 보고 문턱을 정해 그 해를 산다** ══")
    print("     ⚠️ 그 해 데이터는 문턱 정하는 데 **절대 안 쓴다**")
    해들 = sorted({x[0][:4] for x in 후보})
    걷기 = {}
    print(f"    {'해':<7}{'잉여금문턱':>11}{'부채문턱':>10}{'신호일':>7}"
          f"{'평균':>10}{'승률':>8}")
    for y in 해들:
        앞 = [x for x in 후보 if x[0][:4] < y]
        if len(앞) < 300:
            continue
        잉 = sorted(x[7]["잉여금비율"] for x in 앞 if "잉여금비율" in x[7])
        부 = sorted(x[7]["부채비율"] for x in 앞 if "부채비율" in x[7])
        if len(잉) < 200 or len(부) < 200:
            continue
        잉문, 부문 = 잉[len(잉) // 2], 부[len(부) // 2]
        올 = {}
        for x in 후보:
            if x[0][:4] != y:
                continue
            m = x[7]
            if (m.get("잉여금비율", -9e9) >= 잉문
                    and m.get("부채비율", 9e9) <= 부문
                    and m.get("흑자") == 1.0):
                올.setdefault(x[0], []).append(x[2])
        if not 올:
            continue
        걷기.update(올)
        수 = [st.mean(v) for v in 올.values()]
        승 = sum(1 for z in 수 if z > 0) / len(수) * 100
        표 = "⭐" if st.mean(수) > 0 else "❌"
        print(f"    {y:<7}{잉문:>10.1f}%{부문:>9.1f}%{len(올):>7}"
              f"{st.mean(수):>+9.2f}%{승:>7.1f}%{표}")
    print()
    print(머)
    재기(걷기, "**걷기검증 전체**", 년수)

    # 견줄 것: 전 기간으로 정한 문턱 (60차 방식)
    잉값 = sorted(x[7]["잉여금비율"] for x in 후보 if "잉여금비율" in x[7])
    부값 = sorted(x[7]["부채비율"] for x in 후보 if "부채비율" in x[7])
    잉A, 부A = 잉값[len(잉값) // 2], 부값[len(부값) // 2]
    전기간 = {}
    for x in 후보:
        m = x[7]
        if (m.get("잉여금비율", -9e9) >= 잉A and m.get("부채비율", 9e9) <= 부A
                and m.get("흑자") == 1.0):
            전기간.setdefault(x[0], []).append(x[2])
    재기(전기간, f"(견줌) 전 기간 문턱 잉{잉A:.0f}·부{부A:.0f}", 년수)

    # ── B 고정 숫자 ──
    print("\n  ══ B **고정 숫자**로도 되나 (데이터에서 문턱을 안 뽑는다) ══")
    print("     ⚠️ 고정이면 다중검정이 훨씬 줄어든다 — 「상식적인 값」을 그냥 쓴다")
    print(머)
    for 잉, 부 in ((0, 100), (20, 100), (30, 80), (50, 80), (50, 50), (100, 50)):
        t = {}
        for x in 후보:
            m = x[7]
            if (m.get("잉여금비율", -9e9) >= 잉 and m.get("부채비율", 9e9) <= 부
                    and m.get("흑자") == 1.0):
                t.setdefault(x[0], []).append(x[2])
        재기(t, f"잉여금 ≥{잉}% · 부채비율 ≤{부}% · 흑자", 년수)

    # ── C 유동성 ──
    print("\n  ══ C 유동성 — **실제로 살 수 있나** ══")
    고정 = [x for x in 후보 if x[7].get("잉여금비율", -9e9) >= 30
            and x[7].get("부채비율", 9e9) <= 80 and x[7].get("흑자") == 1.0]
    if 고정:
        대금 = sorted(x[8] for x in 고정)
        print(f"    뽑힌 종목의 전날 거래대금")
        for q, 라 in ((0, "최소"), (10, "하위10%"), (25, "하위25%"),
                      (50, "중앙"), (75, "상위25%")):
            v = 대금[min(len(대금) - 1, len(대금) * q // 100)]
            print(f"      {라:<8}{v/1e8:>10,.1f}억원")
        for 투자 in (500_000, 2_000_000, 10_000_000):
            막 = sum(1 for v in 대금 if 투자 > v * 0.01)
            print(f"    한 종목에 {투자/10000:>5,.0f}만원 넣으면 "
                  f"**거래대금의 1%를 넘는 것** {막:,}건 / {len(대금):,} "
                  f"({막/len(대금)*100:.1f}%)")

    # ── D 반쪽 시험 ──
    print("\n  ══ D 반쪽 시험 — 앞에서 정하고 **뒤에서만** 재본다 ══")
    print(머)
    가운데 = 해들[len(해들) // 2]
    앞 = [x for x in 후보 if x[0][:4] < 가운데]
    잉2 = sorted(x[7]["잉여금비율"] for x in 앞 if "잉여금비율" in x[7])
    부2 = sorted(x[7]["부채비율"] for x in 앞 if "부채비율" in x[7])
    if 잉2 and 부2:
        잉B, 부B = 잉2[len(잉2) // 2], 부2[len(부2) // 2]
        for 라, 골 in ((f"앞 절반 (~{가운데}) 문턱 정함", lambda x: x[0][:4] < 가운데),
                       (f"**뒤 절반 ({가운데}~) — 진짜 시험**",
                        lambda x: x[0][:4] >= 가운데)):
            t = {}
            for x in 후보:
                if not 골(x):
                    continue
                m = x[7]
                if (m.get("잉여금비율", -9e9) >= 잉B
                        and m.get("부채비율", 9e9) <= 부B
                        and m.get("흑자") == 1.0):
                    t.setdefault(x[0], []).append(x[2])
            재기(t, 라, 년수 / 2)
        print(f"    (앞 절반에서 뽑은 문턱: 잉여금 ≥{잉B:.1f}% · 부채비율 ≤{부B:.1f}%)")

    print("\n  읽는 법")
    print("    - **A의 걷기검증이 60차와 비슷하면 진짜다.** 크게 떨어지면 다중검정 탓이다")
    print("    - **B가 A와 비슷하면 고정 숫자를 쓰면 된다** — 훨씬 단단하다")
    print("    - D의 **뒤 절반**이 진짜 시험이다. 앞 절반은 참고일 뿐이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
