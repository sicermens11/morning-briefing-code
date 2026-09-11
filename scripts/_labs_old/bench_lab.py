#!/usr/bin/env python3
r"""
bench_lab.py — **코스피는 대체 누가 올린 건가** (2026-09-02 · 24차)

⚠️⚠️⚠️ **23차에서 결정적 모순이 나왔다.**
```
22차 regime_lab   2026년 대형주 「52주 신고가」 초과수익 **+3.23%** (대형주 중에서 잘 골랐다)
23차 final_sim5   2026년 대형주만 담은 시뮬 **−23.7%**, 코스피는 **+62.2%**
```
⚠️ **둘 다 맞을 수 있다.** 잣대가 다르기 때문이다.
```
22차 = 「대형주들 **중에서**」 잘 골랐나   (자기 크기 구간 평균 대비)
23차 = 「**코스피 지수**를 이겼나」        (시총가중 지수 대비)
```
⇒ **코스피가 초대형주 몇 개로 급등했다면 둘이 갈린다.** 그걸 여기서 확인한다.

## 재는 것 — 연도별로 다섯 줄을 나란히 놓는다
```
① 코스피 (시총가중)
② 전 종목 **동일가중** 평균        ← 아무거나 똑같이 사면
③ 대형(1조↑) 동일가중 평균
④ **시총 상위 10** 동일가중 평균    ← 초대형주만
⑤ 시총 상위 30 동일가중 평균
```
⚠️ ①이 ②③보다 훨씬 높은 해가 있으면 **「종목을 고르는 것」으로는 지수를 못 이긴다.**
   그 해에는 **지수를 사는 것이 정답**이고, 선별은 초과분에만 쓸 수 있다.

⚠️ 상장폐지 편향을 피하려고 **그 해 시작 시점에 있던 종목**만 쓰고, 중간에 사라지면
   마지막 가격으로 평가한다(0으로 처리하지 않는다 — 거래정지·합병이 대부분이다).
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402


def _주가():
    """⚠️⚠️ **2026-09-02: 수정주가로 바꿨다.**
    KRX 종가는 액면분할·병합·권리락이 반영 안 된 값이다. 그대로 쓰면
    평균 일간수익률이 **연 13.7%p 부풀려진다**(오염은 0.052%뿐인데도).
    → `omni_lab.수정주가()`가 등락률을 누적해 만든 계열을 쓴다."""
    return O.수정주가(("시총", "거래대금"))


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    print(f"  거래일 {len(날):,}", flush=True)

    해들 = sorted({d[:4] for d in 날})
    print(f"\n  ══ 연도별: 코스피는 누가 올렸나 ══")
    print("     ⚠️ 코스피(시총가중)가 동일가중보다 훨씬 높은 해 = **종목 선별로는 못 이기는 해**")
    print(f"\n    {'해':<6}{'코스피':>9}{'전종목중앙':>10}{'전종목평균':>11}{'대형':>9}"
          f"{'상위10':>9}{'상위30':>9}{'코스피−중앙':>13}")
    쌓 = []
    for y in 해들:
        일 = [d for d in 날 if d[:4] == y]
        if len(일) < 30:
            continue
        시, 끝 = 일[0], 일[-1]
        ix0 = (지수.get(시) or {}).get("KOSPI")
        ix1 = (지수.get(끝) or {}).get("KOSPI")
        지 = (ix1 / ix0 - 1) * 100 if (ix0 and ix1) else None

        s0 = 주가[시]
        후 = []
        for code, v in s0.items():
            c0, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            # 마지막 가격을 찾는다 (중간에 사라지면 직전 값)
            끝값 = None
            for d in reversed(일):
                v2 = 주가[d].get(code)
                if v2:
                    끝값 = v2[0]
                    break
            if not 끝값:
                continue
            후.append((시총, code, (끝값 / c0 - 1) * 100))
        if len(후) < 100:
            continue
        후.sort(reverse=True)
        전 = st.mean([r for _, _, r in 후])
        대 = [r for 시총, _, r in 후 if 시총 >= 1e12]
        대평 = st.mean(대) if len(대) >= 5 else None
        상10 = st.mean([r for _, _, r in 후[:10]])
        상30 = st.mean([r for _, _, r in 후[:30]])
        상100 = st.mean([r for _, _, r in 후[:100]])
        갭 = (지 - 전) if 지 is not None else None
        쌓.append((y, 지, 전, 갭))
        print(f"    {y:<6}{(f'{지:+.1f}%' if 지 is not None else '-'):>9}"
              f"{전:>+8.1f}%{(f'{대평:+.1f}%' if 대평 is not None else '-'):>9}"
              f"{상10:>+8.1f}%{상30:>+8.1f}%{상100:>+8.1f}%"
              f"{(f'{갭:+.1f}%p' if 갭 is not None else '-'):>12}")

    좋 = [x for x in 쌓 if x[3] is not None and x[3] > 5]
    나 = [x for x in 쌓 if x[3] is not None and x[3] < -5]
    print(f"\n  ══ 판정 ══")
    print(f"    코스피가 전종목 평균보다 **5%p 넘게 높은 해**: {len(좋)}개 "
          + (", ".join(f"{y}({g:+.0f}%p)" for y, _, _, g in 좋) if 좋 else "없음"))
    print(f"    코스피가 전종목 평균보다 **5%p 넘게 낮은 해**: {len(나)}개 "
          + (", ".join(f"{y}({g:+.0f}%p)" for y, _, _, g in 나) if 나 else "없음"))
    if 쌓:
        평 = st.mean([x[3] for x in 쌓 if x[3] is not None])
        print(f"    평균 격차 {평:+.1f}%p")
        print("\n  읽는 법")
        print("    - '코스피−전종목'이 크게 +인 해 = **소수 초대형주가 지수를 끌어올린 해**")
        print("      그 해에는 아무리 잘 골라도 지수를 못 이긴다 → **지수를 사는 게 정답**")
        print("    - 크게 −인 해 = 개별 종목이 지수보다 나은 해 → **선별이 값어치 있다**")
        print("    - ⚠️ 이 격차가 해마다 뒤집히면 **미리 알 수 없다** = 지수+선별 섞는 게 답")
    return 0


if __name__ == "__main__":
    sys.exit(main())
