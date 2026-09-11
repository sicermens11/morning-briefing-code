#!/usr/bin/env python3
r"""
trend_lab.py — **한국 시장은 어디서 어디로 가고 있나** (2026-09-02 · 32차)

⚠️⚠️ **사용자 취지.**
   *"한국이 과거에서 현재까지 어떤 흐름으로 왔고, 미래로 어떤 흐름으로 가는지의 흐름이었어.
   그러면 현상황과 미래 상승 가치를 조금이라도 파악할 수 있으니까"*

## 왜 필요한가
```
지금까지 나는 16.7년 **평균**을 내서 「이 신호는 t=4.2다」라고 말해왔다.
⚠️ 시장 구조가 바뀌었다면 그 평균은 **지금과 상관없는 숫자**다.
⇒ 먼저 **무엇이 어떻게 변해왔는지**를 봐야 한다. 그래야 지금이 어떤 국면인지 안다.
```

## 재는 것 — 연도별 궤적 + **지금이 역사적으로 어디쯤인가**
```
① 시장 규모      상장 종목 수 · 총 시총 · 하루 거래대금
② 쏠림          상위 10 / 30 / 100의 시총 비중
                ⚠️ 2026년이 극단적인데 **추세인가 일시적인가**가 핵심이다
③ 산업 구성      업종별 시총 비중 2010 vs 2026 — **어떤 산업이 커지고 줄었나**
④ 변동성        코스피 연간 변동성
⑤ 종목 간 상관   종목들이 **점점 같이 움직이는가** (= 분산이 안 되는가)
⑥ 수급 구조      외국인·기관 순매수 비중 (⚠️ 수급 자료가 쌓이는 중이라 부분만)
⑦ 시장 회전      새로 들어온 종목 · 사라진 종목
```
⚠️ **미래는 「추세가 이어진다면」이라는 조건부로만 말한다.** 외삽은 예측이 아니다.
⚠️ 수정주가 적용 · 시총·거래대금은 원본(그날의 실제 값이 맞다).
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402


def _기울기(xs, ys):
    """단순 선형 추세 기울기 (연당 변화량)."""
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = st.mean(xs), st.mean(ys)
    분모 = sum((x - mx) ** 2 for x in xs) or 1e-9
    return sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / 분모


def _백분위(값들, 지금):
    """지금 값이 역사적으로 몇 백분위인가."""
    a = sorted(값들)
    if not a:
        return 0.0
    아래 = sum(1 for x in a if x < 지금)
    return 아래 / len(a) * 100


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._수급() and O._기본()
    수급 = O._수급()
    print(f"  거래일 {len(날):,}", flush=True)

    해들 = sorted({d[:4] for d in 날})
    해들 = [y for y in 해들 if sum(1 for d in 날 if d[:4] == y) >= 30]

    행 = []
    for y in 해들:
        일 = [d for d in 날 if d[:4] == y]
        끝 = 일[-1]
        s = 주가[끝]
        시총들 = sorted((v[1] for v in s.values() if v[1] > 0), reverse=True)
        합 = sum(시총들) or 1
        대금 = st.mean([sum(v[2] for v in 주가[d].values()) for d in 일[::5]])
        # 변동성
        ix = [(지수.get(d) or {}).get("KOSPI") for d in 일]
        ix = [x for x in ix if x]
        변 = (st.pstdev([ix[k] / ix[k - 1] - 1 for k in range(1, len(ix))]) * 100 * (245 ** .5)
              if len(ix) > 30 else 0)
        행.append({
            "해": y, "종목수": len(시총들), "총시총": 합 / 1e12, "거래대금": 대금 / 1e12,
            "상위10": sum(시총들[:10]) / 합 * 100,
            "상위30": sum(시총들[:30]) / 합 * 100,
            "상위100": sum(시총들[:100]) / 합 * 100,
            "변동성": 변,
        })

    # ⑤ 종목 간 상관 (해마다 표본 60종목으로 평균 쌍 상관)
    print("  종목 간 상관 계산 중...", flush=True)
    for r in 행:
        y = r["해"]
        일 = [d for d in 날 if d[:4] == y]
        if len(일) < 100:
            r["상관"] = None
            continue
        s0 = 주가[일[0]]
        후 = sorted(((v[1], c) for c, v in s0.items()
                     if v[1] >= O._MIN_MC and v[2] >= O._MIN_AMT), reverse=True)
        뽑 = [c for _, c in 후[::max(1, len(후) // 60)]][:60]
        수 = {}
        for c in 뽑:
            a = []
            for k in range(1, len(일)):
                x, p = 주가[일[k]].get(c), 주가[일[k - 1]].get(c)
                if x and p and p[0] > 0:
                    a.append(x[0] / p[0] - 1)
            if len(a) > 150:
                수[c] = a
        cs = list(수)
        쌍 = []
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                A, B = 수[cs[i]], 수[cs[j]]
                n = min(len(A), len(B))
                if n < 150:
                    continue
                A, B = A[:n], B[:n]
                ma, mb = st.mean(A), st.mean(B)
                sa = st.pstdev(A) or 1e-9
                sb = st.pstdev(B) or 1e-9
                쌍.append(sum((A[z] - ma) * (B[z] - mb) for z in range(n)) / n / (sa * sb))
        r["상관"] = st.mean(쌍) if 쌍 else None

    # ⑦ 시장 회전 (종목 등장·소멸)
    for k, r in enumerate(행):
        y = r["해"]
        일 = [d for d in 날 if d[:4] == y]
        올 = set(주가[일[-1]])
        앞해 = 행[k - 1]["해"] if k > 0 else None
        if 앞해:
            앞일 = [d for d in 날 if d[:4] == 앞해]
            전 = set(주가[앞일[-1]])
            r["신규"] = len(올 - 전)
            r["소멸"] = len(전 - 올)
        else:
            r["신규"] = r["소멸"] = 0

    print(f"\n  ══ ①②④⑤⑦ 한국 시장의 궤적 ══")
    print(f"    {'해':<6}{'종목수':>7}{'총시총(조)':>11}{'거래대금(조)':>12}"
          f"{'상위10%':>9}{'상위30%':>9}{'상위100%':>10}{'변동성':>8}{'상관':>8}"
          f"{'신규':>6}{'소멸':>6}")
    for r in 행:
        상 = f"{r['상관']:+.3f}" if r["상관"] is not None else "-"
        print(f"    {r['해']:<6}{r['종목수']:>7,}{r['총시총']:>11,.0f}{r['거래대금']:>12.1f}"
              f"{r['상위10']:>8.1f}%{r['상위30']:>8.1f}%{r['상위100']:>9.1f}%"
              f"{r['변동성']:>7.1f}%{상:>8}{r['신규']:>6}{r['소멸']:>6}")

    print(f"\n  ══ 추세와 「지금 어디쯤인가」 ══")
    print("     ⚠️ 백분위 100%면 **17년 중 지금이 가장 높다**는 뜻이다")
    xs = list(range(len(행)))
    print(f"    {'지표':<14}{'2010':>10}{'2018':>10}{'지금(2026)':>12}"
          f"{'연당 변화':>11}{'백분위':>9}")
    for 키, 라벨, 단위 in (("종목수", "상장 종목 수", "개"), ("총시총", "총 시총(조)", "조"),
                           ("거래대금", "하루 거래대금(조)", "조"),
                           ("상위10", "상위10 비중", "%"), ("상위30", "상위30 비중", "%"),
                           ("상위100", "상위100 비중", "%"),
                           ("변동성", "시장 변동성", "%"), ("상관", "종목 간 상관", "")):
        ys = [r[키] for r in 행 if r.get(키) is not None]
        xs2 = [i for i, r in enumerate(행) if r.get(키) is not None]
        if len(ys) < 5:
            continue
        기 = _기울기(xs2, ys)
        첫 = next((r[키] for r in 행 if r["해"] == "2010" and r.get(키) is not None), ys[0])
        중 = next((r[키] for r in 행 if r["해"] == "2018" and r.get(키) is not None), None)
        끝 = ys[-1]
        백 = _백분위(ys, 끝)
        화 = "↗" if 기 > 0 else ("↘" if 기 < 0 else "→")
        print(f"    {라벨:<14}{첫:>10,.2f}"
              f"{(f'{중:,.2f}' if 중 is not None else '-'):>10}{끝:>12,.2f}"
              f"{기:>+10.3f}{화}{백:>8.0f}%")

    # ③ 산업 구성 변화
    print(f"\n  ══ ③ 산업 구성 — 어떤 산업이 커지고 줄었나 ══")
    def 업종비중(d):
        s = 주가[d]
        합계 = {}
        전 = 0.0
        for c, v in s.items():
            if v[1] <= 0:
                continue
            부 = str((기본.get(c) or {}).get("업종") or "미상")
            합계[부] = 합계.get(부, 0) + v[1]
            전 += v[1]
        return {k: x / (전 or 1) * 100 for k, x in 합계.items()}, 전

    처음 = [d for d in 날 if d[:4] == 해들[0]][-1]
    중간 = [d for d in 날 if d[:4] == "2018"]
    중간 = 중간[-1] if 중간 else 처음
    지금 = 날[-1]
    a, _ = 업종비중(처음)
    b, _ = 업종비중(중간)
    c, _ = 업종비중(지금)
    변화 = sorted(((c.get(k, 0) - a.get(k, 0), k) for k in set(a) | set(c)), reverse=True)
    print(f"    {'업종':<24}{해들[0]:>9}{'2018':>9}{'2026':>9}{'변화':>10}")
    print("    ── 커진 업종 상위 10 ──")
    for d_, k in 변화[:10]:
        if abs(d_) < 0.05:
            continue
        print(f"    {k[:22]:<24}{a.get(k,0):>8.2f}%{b.get(k,0):>8.2f}%"
              f"{c.get(k,0):>8.2f}%{d_:>+9.2f}%p")
    print("    ── 줄어든 업종 상위 10 ──")
    for d_, k in 변화[-10:]:
        if abs(d_) < 0.05:
            continue
        print(f"    {k[:22]:<24}{a.get(k,0):>8.2f}%{b.get(k,0):>8.2f}%"
              f"{c.get(k,0):>8.2f}%{d_:>+9.2f}%p")

    # ⑥ 수급 구조
    if 수급:
        print(f"\n  ══ ⑥ 수급 구조 (⚠️ 자료가 쌓이는 중이라 부분만) ══")
        해수 = {}
        for d, fl in 수급.items():
            y = d[:4]
            외 = sum((v.get("외국인") or 0) for v in fl.values())
            기 = sum((v.get("기관") or 0) for v in fl.values())
            개 = sum((v.get("개인") or 0) for v in fl.values())
            해수.setdefault(y, []).append((외, 기, 개))
        print(f"    {'해':<6}{'외국인 순매수(억)':>18}{'기관(억)':>14}{'개인(억)':>14}{'일수':>7}")
        for y in sorted(해수):
            a2 = 해수[y]
            if len(a2) < 20:
                continue
            print(f"    {y:<6}{sum(x[0] for x in a2)/1e8:>17,.0f}"
                  f"{sum(x[1] for x in a2)/1e8:>14,.0f}"
                  f"{sum(x[2] for x in a2)/1e8:>14,.0f}{len(a2):>7}")

    print("\n  읽는 법")
    print("    - **백분위 100%면 17년 중 지금이 가장 높다**는 뜻이다. 그게 '지금이 특이한가'의 답이다")
    print("    - '연당 변화'가 꾸준히 한 방향이면 **구조 변화**, 왔다갔다면 **주기**다")
    print("    - 종목 간 상관이 오르는 추세면 **분산이 점점 안 된다** = 종목 수를 늘려도 소용없어진다")
    print("    - ⚠️ 미래는 「추세가 이어진다면」이라는 조건부로만 말할 수 있다. 외삽은 예측이 아니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
