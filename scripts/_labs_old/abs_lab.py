#!/usr/bin/env python3
r"""
abs_lab.py — **절대 수익률: 이 신호로 사면 실제로 얼마 버나** (2026-09-02 · 35차)

⚠️⚠️⚠️ **사용자 지적으로 판정 기준을 바로잡는다.**
   *"꼭 지수를 이길 필요 없어. 절대값으로 종목이 상승하면 돼. 왜 자꾸 지수에 못 이겼다고
   잘못된 것처럼 얘기하는 거야?"*
   *"돈이 되는 것은 아니라는 게 수익성이 없다는 뜻 같은데, 오히려 지금 브리핑 시스템에
   대입해서 그런 거 아니야? 매수 기회 포착이라는 목표에 맞게 새로 설계한다고 해도 답이 안 나와?"*

## 내가 틀린 틀을 쓰고 있었다
```
지금까지 낸 숫자   **「같은 크기 구간 평균 대비 초과」**
⚠️ 초과가 +1.29%라고 그 종목이 올랐다는 뜻이 아니다. 구간 평균이 −5%면 그 종목은 −3.7%다
지금까지 시뮬     **포트폴리오 운용** — 자산 100%를 굴리고 자리를 다 채우고 무조건 산다
⚠️ 실제 브리핑은 「오늘 이거 봐라」를 주고 **사용자가 골라서 산다.** 다 사는 게 아니다
```

## 그래서 **가장 기본적인 숫자**를 낸다
```
이 신호가 뜬 종목을 **D+1 종가에 사서 N일 뒤에 팔면**
  ① 평균 몇 % 버나 (비용 차감 후)
  ② **몇 %가 플러스로 끝나나** (승률)
  ③ 중앙값은 몇 %인가 (극단값에 안 흔들리는 값)
  ④ 잘 되면 얼마, 못 되면 얼마 (상위 25% · 하위 25%)
  ⑤ **1년에 그런 기회가 몇 번 오나**
  ⑥ 연도별로는 어땠나 — **손실 난 해가 몇 해인가**
```
⚠️ 왕복비용 0.26% 차감. 수정주가 적용. 16.7년.
⚠️ **비교 기준을 같이 둔다**: 「아무 종목이나 무작위로 샀을 때」의 같은 숫자.
   그래야 신호가 값어치가 있는지 안다. **하지만 판정은 절대 수익으로 한다.**
"""
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_지평 = (5, 20, 60)
_비용 = 0.26          # 왕복 %
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    지수, 기본, 수급 = O._지수(), O._기본(), O._수급()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    신호이름 = ["A 52주 신고가", "B RSI 과매수", "C 볼린저 상단", "D 수급강도",
                "F 볼린저 하단", "G RSI 과매도", "J 모멘텀 2개↑", "K 반전 2개↑",
                "Z 무작위(비교용)"]
    통 = {}       # (신호, 크기, 지평) -> [절대수익%]
    해통 = {}     # (신호, 크기, 지평, 해) -> [절대수익%]
    rnd = random.Random(7)

    최대 = max(_지평)
    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + 최대 >= len(날):
            continue
        해 = d1[:4]
        fl = 수급.get(d1) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            m = 주가[날[i + 1]].get(code)
            if not m:
                continue
            수 = {}
            for h in _지평:
                e = 주가[날[i + 1 + h]].get(code)
                if e:
                    수[h] = (e[0] / m[0] - 1) * 100 - _비용     # ⚠️ 비용 차감
            if len(수) < len(_지평):
                continue
            g = _크기(시총)
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            고 = max(sq[k - 250:k + 1])
            f = fl.get(code) or {}
            강 = (((f.get("외국인") or 0) + (f.get("기관") or 0)) * c1 / 시총 * 100
                  if 시총 > 0 else 0)
            A = bool(고) and c1 >= 고 * 0.999
            B, C = rsi >= 70, 볼 >= 1.0
            D = 강 >= 0.5
            F, G = 볼 <= -1.0, rsi <= 30
            J = sum([A, B, C]) >= 2
            K = sum([F, G, c1 < s20]) >= 2
            Z = rnd.random() < 0.01          # 무작위 1% 표본
            for 이름, 켜 in zip(신호이름, [A, B, C, D, F, G, J, K, Z]):
                if not 켜:
                    continue
                for h in _지평:
                    통.setdefault((이름, g, h), []).append(수[h])
                    해통.setdefault((이름, g, h, 해), []).append(수[h])
        if i % 500 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    해수 = len({d[:4] for d in 날[250:]})
    print(f"\n  ══ 이 신호로 사면 실제로 얼마 버나 (비용 {_비용}% 차감 · 절대 수익) ══")
    print("     ⚠️ **판정은 절대 수익으로 한다.** 「Z 무작위」는 견주기 위한 기준선이다")
    for g, _, _ in 크기표:
        print(f"\n  ══════ {g} ══════")
        for h in _지평:
            print(f"\n  ── D+{h} 보유 ──")
            print(f"    {'신호':<16}{'평균':>9}{'중앙값':>9}{'승률':>8}"
                  f"{'상위25%':>9}{'하위25%':>9}{'연간기회':>10}{'표본':>10}")
            for s in 신호이름:
                a = 통.get((s, g, h)) or []
                if len(a) < 300:
                    continue
                a2 = sorted(a)
                n = len(a2)
                승 = sum(1 for x in a2 if x > 0) / n * 100
                상25 = a2[int(n * 0.75)]
                하25 = a2[int(n * 0.25)]
                기회 = n / 해수
                별 = "⭐" if st.mean(a2) > 0 and 승 >= 50 else ("  " if st.mean(a2) > 0 else "❌")
                print(f"    {s:<16}{st.mean(a2):>+8.2f}%{st.median(a2):>+8.2f}%"
                      f"{승:>7.1f}%{상25:>+8.2f}%{하25:>+8.2f}%{기회:>9.0f}회{n:>10,}{별}")

    # 연도별 — 손실 난 해가 몇 해인가
    해들 = sorted({k[3] for k in 해통})
    print(f"\n\n  ══ 연도별 절대 수익 (D+60 보유 · 비용 차감) ══")
    print("     ⚠️ **손실 난 해가 몇 해인지**가 중요하다. 평균이 +여도 자주 잃으면 못 쓴다")
    for g, _, _ in 크기표:
        print(f"\n  ── {g} ──")
        print(f"    {'신호':<16}" + "".join(f"{y[2:]:>7}" for y in 해들) + f"{'+인해':>8}")
        for s in 신호이름:
            줄, 플, 전 = [], 0, 0
            있 = False
            for y in 해들:
                a = 해통.get((s, g, 60, y)) or []
                if len(a) < 30:
                    줄.append("-")
                    continue
                있 = True
                m = st.mean(a)
                전 += 1
                플 += 1 if m > 0 else 0
                줄.append(f"{m:+.1f}")
            if 있:
                print(f"    {s:<16}" + "".join(f"{x:>7}" for x in 줄)
                      + f"{플:>5}/{전}")

    print("\n  읽는 법")
    print("    - **평균이 +이고 승률이 50%를 넘으면 그 신호로 사면 돈을 번다** (⭐)")
    print("    - 「Z 무작위」와 견줘 얼마나 나은지 본다. 하지만 **판정은 절대 수익으로 한다**")
    print("    - '연간 기회'는 1년에 그 신호가 몇 번 뜨는지다. 적으면 실전에서 쓰기 어렵다")
    print("    - '하위 25%'는 **못 될 때 얼마나 잃는지**다. 이게 크면 마음이 못 버틴다")
    print("    - ⚠️ 절대 수익은 **시장이 오르면 같이 오른다**. 신호의 힘과 시장의 힘이 섞여 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
