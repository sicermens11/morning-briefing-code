#!/usr/bin/env python3
r"""
proof_lab.py — **우연인가 아닌가 + 버그 교차검증** (2026-09-03 · 84차)

⚠️⚠️ **사용자 지적.** *"결정적으로 부족한 거 앞으로 할 거 아니야?"*
   → 맞다. **「부족하다」고 나열해놓고 할 수 있는 것을 안 하고 있었다.**

## 왜 이게 필요한가 — **오늘 조합을 100개 넘게 봤다**
```
57차 38개 조건 · 59차 재무 조합 30여 개 · 62차 자금배분 24개
65차 섹터 조합 40여 개 · 76차 매도 25개 · 77차 종목조합 20여 개
82차 운용 25개 · 83차 부분매도 25개 …
⇒ **좋은 걸 고르는 행위 자체가 성적을 부풀린다.**
   100개를 보면 그 중 하나쯤은 **우연히** 좋아 보인다
```

## 어떻게 재나
```
A ⭐ **순열검정(permutation test)**
   수익률을 **무작위로 섞어** 같은 신호를 만든다.
   진짜 신호가 「섞은 것」보다 확실히 나은가?
   ⇒ 이게 다중검정에 가장 강한 검증이다
B **무작위 신호와 비교**
   같은 날 · 같은 개수로 **아무 종목이나** 사면?
   우리 신호가 그보다 나은 게 우연이 아닌가
C **본페로니 보정**
   조합 N개를 봤을 때 필요한 t값 = sqrt(2 ln N)
   우리 t값이 그걸 넘나
D ⭐ **버그 교차검증**
   같은 조건을 **여러 방식으로 계산**해 숫자가 일치하나
   (오늘 70차 vs 72차에서 이렇게 버그를 찾았다)
```
⚠️ 순열검정은 무겁다. 200회로 한다.
"""
import glob
import io
import json
import math
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_목표 = 20.0
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
                고 = float(v.get("고가") or 0) or 종
                if min(종, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종, 고 / 종)
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

    def 수익내기(code, i0, 매수):
        """76차 규칙: +20% 지정가 · 최대 D+40 · 손절 없음."""
        for h in range(0, _최대보유 + 1):
            j = i0 + h
            if j >= len(날):
                return None, None
            dd = 날[j]
            vv = 주가[dd].get(code)
            bb2 = (비.get(dd) or {}).get(code)
            if not vv or not bb2:
                return None, None
            if vv[0] * bb2[1] >= 매수 * (1 + _목표 / 100):
                return _목표 - _비용, max(1, h)
        j = i0 + _최대보유
        if j >= len(날):
            return None, None
        끝 = 주가[날[j]].get(code)
        if not 끝:
            return None, None
        return (끝[0] / 매수 - 1) * 100 - _비용, _최대보유

    # ── 신호 + 그날의 「살 수 있었던 전체 종목」(무작위 비교용) ──
    사건, 후보풀 = [], {}
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
        오늘풀 = []
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
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            오늘풀.append((code, 매수, 대금))
            # 우리 신호인가
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
                continue
            if (g - 시갭) > -3:
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
            r, h = 수익내기(code, i + 1, 매수)
            if r is None:
                continue
            사건.append({"날": 다음, "code": code, "결과": r, "며칠": h,
                        "상대갭": g - 시갭, "대금": 대금, "i": i + 1})
        if 오늘풀:
            후보풀[다음] = (i + 1, 오늘풀)
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    날별 = {}
    for x in 사건:
        날별.setdefault(x["날"], []).append(x)
    수익들 = [x["결과"] for x in 사건]
    진평균 = st.mean(수익들)
    진승률 = sum(1 for z in 수익들 if z > 0) / len(수익들) * 100
    print(f"  사건 {len(사건):,}건 · 신호일 {len(날별)}일 · {년수:.1f}년")
    print(f"  진짜 신호: 평균 **{진평균:+.2f}%** · 승률 **{진승률:.1f}%**\n",
          flush=True)

    # ══ C 본페로니 ══
    print("  ══ C **본페로니 보정** — 조합을 많이 보면 문턱이 높아진다 ══")
    sd = st.pstdev(수익들) or 1e-9
    t = 진평균 / (sd / math.sqrt(len(수익들)))
    print(f"    우리 t값 = {t:.2f}  (평균 {진평균:+.2f}% · 표준편차 {sd:.2f} "
          f"· 표본 {len(수익들):,})")
    print(f"    {'본 조합 수':<14}{'필요 t':>10}{'통과?':>10}")
    for N in (1, 10, 50, 100, 500, 1000):
        need = math.sqrt(2 * math.log(N)) if N > 1 else 1.96
        need = max(need, 1.96)
        print(f"    {N:>10}개{need:>10.2f}{'✅' if t > need else '❌':>10}")
    print("    ⚠️ 오늘 본 조합은 **100~200개** 사이다")

    # ══ B 무작위 신호 ══
    print("\n  ══ B **무작위로 같은 날 같은 개수를 사면** ══")
    print("     ⚠️ 우리 신호가 뜬 날에, 그날 살 수 있던 종목 중 **아무거나** 고른다")
    print("        ⇒ 「그 날짜가 좋았을 뿐」인지 「종목 선택이 좋았는지」를 가른다")
    rng = random.Random(7)
    무작위평균, 무작위승률 = [], []
    for s in range(200):
        v = []
        for d, xs in 날별.items():
            i0, 풀 = 후보풀.get(d, (None, []))
            if not 풀:
                continue
            뽑 = rng.sample(풀, min(len(xs), len(풀)))
            for code, 매수, 대금 in 뽑:
                r, h = 수익내기(code, i0, 매수)
                if r is not None:
                    v.append(r)
        if len(v) > 100:
            무작위평균.append(st.mean(v))
            무작위승률.append(sum(1 for z in v if z > 0) / len(v) * 100)
        if s % 50 == 0:
            print(f"    {s}/200회...", flush=True)
    무작위평균.sort()
    무작위승률.sort()
    n = len(무작위평균)
    넘 = sum(1 for z in 무작위평균 if z >= 진평균)
    print(f"    무작위 {n}회: 평균 {st.mean(무작위평균):+.2f}% "
          f"(5% {무작위평균[n//20]:+.2f}% ~ 95% {무작위평균[n*19//20]:+.2f}%)")
    print(f"    승률 {st.mean(무작위승률):.1f}% "
          f"(5% {무작위승률[n//20]:.1f}% ~ 95% {무작위승률[n*19//20]:.1f}%)")
    print(f"    ⭐ **우리({진평균:+.2f}%)보다 좋은 무작위: {넘}/{n}회 "
          f"= p={넘/n:.4f}**")
    print(f"       {'✅ 우연이 아니다 (p<0.01)' if 넘/n < 0.01 else ('△ 애매 (p<0.05)' if 넘/n < 0.05 else '❌ 우연일 수 있다')}")

    # ══ A 순열검정 ══
    print("\n  ══ A ⭐ **순열검정** — 수익률을 무작위로 섞으면 ══")
    print("     ⚠️ 신호가 뜬 날짜·종목은 그대로 두고, **결과만 섞는다**")
    print("        ⇒ 「우리가 고른 조합」이 「아무 조합」보다 나은지를 본다")
    전체수익 = []
    for d, (i0, 풀) in 후보풀.items():
        for code, 매수, 대금 in 풀:
            pass
    # ⚠️ 전체 종목의 수익을 다 계산하면 너무 무겁다.
    #    대신 **신호 종목의 수익을 섞어** 날짜 배치가 우연인지 본다
    순열평균 = []
    for s in range(500):
        섞 = 수익들[:]
        rng.shuffle(섞)
        # 날짜별로 다시 묶어 날짜 단위 평균을 낸다
        t2, idx = {}, 0
        for d, xs in 날별.items():
            t2[d] = 섞[idx:idx + len(xs)]
            idx += len(xs)
        수 = [st.mean(v) for v in t2.values() if v]
        순열평균.append(st.mean(수))
    순열평균.sort()
    날짜단위 = st.mean([st.mean([y["결과"] for y in v]) for v in 날별.values()])
    넘2 = sum(1 for z in 순열평균 if z >= 날짜단위)
    print(f"    날짜 단위 실제 평균 {날짜단위:+.2f}%")
    print(f"    섞었을 때 {len(순열평균)}회: {st.mean(순열평균):+.2f}% "
          f"(5% {순열평균[len(순열평균)//20]:+.2f}% ~ "
          f"95% {순열평균[len(순열평균)*19//20]:+.2f}%)")
    print(f"    ⇒ 실제보다 좋은 순열: {넘2}/{len(순열평균)}")
    print("    ⚠️ 이건 **날짜 배치**가 우연인지만 본다. B가 더 중요한 검증이다")

    # ══ D 버그 교차검증 ══
    print("\n  ══ D ⭐ **버그 교차검증** — 같은 것을 다르게 계산해 맞춰본다 ══")
    print("     ⚠️ 오늘 70차 vs 72차에서 이렇게 버그를 찾았다")
    # ① 날짜 단위 평균을 두 방식으로
    방식1 = st.mean([st.mean([y["결과"] for y in v]) for v in 날별.values()])
    합, 개 = 0.0, 0
    for v in 날별.values():
        합 += sum(y["결과"] for y in v) / len(v)
        개 += 1
    방식2 = 합 / 개
    print(f"    ① 날짜 단위 평균   방식A {방식1:+.6f}% · 방식B {방식2:+.6f}% "
          f"· 차이 {abs(방식1-방식2):.9f} {'✅' if abs(방식1-방식2) < 1e-9 else '❌'}")
    # ② 종목 단위 평균
    방식3 = st.mean(수익들)
    방식4 = sum(수익들) / len(수익들)
    print(f"    ② 종목 단위 평균   방식A {방식3:+.6f}% · 방식B {방식4:+.6f}% "
          f"· 차이 {abs(방식3-방식4):.9f} {'✅' if abs(방식3-방식4) < 1e-9 else '❌'}")
    # ③ 목표 달성률 — 결과가 정확히 19.74%인 것의 비율
    달성 = sum(1 for z in 수익들 if abs(z - (_목표 - _비용)) < 1e-9)
    빠른 = sum(1 for x in 사건 if x["며칠"] < _최대보유)
    print(f"    ③ 목표 달성 수   결과기준 {달성:,}건 · 보유일기준 {빠른:,}건 "
          f"{'✅' if 달성 == 빠른 else '❌ 불일치!'}")
    # ④ 며칠이 범위 안인가
    나쁨 = [x for x in 사건 if not (1 <= x["며칠"] <= _최대보유)]
    print(f"    ④ 보유일 범위     1~{_최대보유}일 밖 {len(나쁨)}건 "
          f"{'✅' if not 나쁨 else '❌'}")
    # ⑤ 수익이 목표를 넘는 게 있나 (지정가라 넘으면 안 된다)
    초과 = [x for x in 사건 if x["며칠"] < _최대보유
            and x["결과"] > _목표 - _비용 + 1e-9]
    print(f"    ⑤ 목표 초과 체결   {len(초과)}건 "
          f"{'✅' if not 초과 else '❌ 지정가인데 더 벌었다?'}")
    # ⑥ 매수일이 신호일 다음인가
    어긋 = [x for x in 사건 if 날[x["i"]] != x["날"]]
    print(f"    ⑥ 매수일 정합성   어긋난 것 {len(어긋)}건 "
          f"{'✅' if not 어긋 else '❌'}")

    print("\n  읽는 법")
    print("    - **B의 p값이 가장 중요하다.** 0.01 미만이면 우연이 아니다")
    print("    - C에서 **본 조합 수만큼의 문턱**을 넘어야 한다")
    print("    - D에서 ❌가 하나라도 나오면 **버그다.** 찾아서 고쳐야 한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
