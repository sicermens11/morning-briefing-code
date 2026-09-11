#!/usr/bin/env python3
r"""
funnel_lab.py — **1년 16.4번밖에 못 사는 이유를 단계별로 센다** (2026-09-09 신설)

## 사용자 말
```
「1년에 16.4번 주식을 사는 거면 **안 사는 게 나아.**
  그거 그냥 **주식 안 하는 게 낫다**는 소리야」
```
맞다. 나는 여태 문턱만 만지작거리면서 이 숫자를 못 올렸다.
**어디서 막히는지를 한 번도 단계별로 안 세어봤다.**

## 세는 것 — 깔때기
```
① 우주            시총 300~2,000억 · 거래대금 1억↑ 인 종목·날
② + 재무          잉여금 30%↑ · 부채 80%↓ · 흑자
③ + 볼린저 -1.0σ
④ + 20일 낙폭 -10%    <- 여기까지가 「후보」
⑤ + 후보가 3개 이상인 날만    <- 상대갭을 낼 수 있는 날
⑥ + 상대갭 -3.5%p 아래
⑦ + 하루 4종목 상한
⑧ + 돈이 있어야 산다 (자산 20%씩 · 최대 5종목)   <- 실제 매수
```
**단계마다 몇 배로 줄어드는지**를 보면 어디를 풀어야 할지 알 수 있다

쓰는 법:
    python scripts\funnel_lab.py
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

_시작 = "20160401"
_시총하한, _시총상한 = 3e10, 2e11
_갭문턱, _하루상한, _비중 = -3.5, 4, 0.20


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    갭표, 앞종 = {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c, 시 = float(v["종가"]), float(v.get("시가") or 0)
            except (TypeError, ValueError, KeyError):
                continue
            시 = 시 or 종c
            if min(종c, 시) <= 0:
                continue
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d["기준일"]] = 하루

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

    print("  세는 중...", flush=True)
    칸 = {k: 0 for k in ("①우주", "②재무", "③볼린저", "④낙폭",
                         "⑤3개이상날", "⑥갭", "⑦하루상한")}
    날수 = {"전체": 0, "후보1개↑": 0, "후보3개↑": 0, "갭통과날": 0}
    묶 = {}
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        날수["전체"] += 1
        하루갭 = 갭표.get(다음) or {}
        오늘후보 = []
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < _시총하한 or 대금 < O._MIN_AMT or 시총 >= _시총상한:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250 or 종계[code][kk - 20] <= 0:
                continue
            g = 하루갭.get(code)
            if g is None:
                continue
            칸["①우주"] += 1
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
                continue
            칸["②재무"] += 1
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0:
                continue
            칸["③볼린저"] += 1
            if (c1 / sq[kk - 20] - 1) * 100 > -10.0:
                continue
            칸["④낙폭"] += 1
            오늘후보.append((code, g))
        if 오늘후보:
            날수["후보1개↑"] += 1
        if len(오늘후보) >= 3:
            날수["후보3개↑"] += 1
            칸["⑤3개이상날"] += len(오늘후보)
            중 = st.median([z[1] for z in 오늘후보])
            골 = [z for z in 오늘후보 if z[1] - 중 <= _갭문턱]
            칸["⑥갭"] += len(골)
            if 골:
                날수["갭통과날"] += 1
            칸["⑦하루상한"] += min(len(골), _하루상한)
            묶[다음] = len(골)

    해수 = 날수["전체"] / 245 or 1
    print("\n" + "=" * 92)
    print("  181차 · **1년 16.4번밖에 못 사는 이유** — 단계마다 몇 배로 줄어드나")
    print(f"  2016-04 ~ · 거래일 {날수['전체']:,}일 (약 {해수:.1f}해)")
    print("=" * 92)
    print(f"\n  {'단계':<26}{'남은 것':>14}{'1년에':>12}{'앞 단계 대비':>14}")
    앞 = None
    이름 = (("① 우주 (크기·거래대금)", "①우주"),
            ("② + 재무 우량", "②재무"),
            ("③ + 볼린저 -1.0σ", "③볼린저"),
            ("④ + 20일 낙폭 -10%  = **후보**", "④낙폭"),
            ("⑤ + 후보 3개 이상인 날만", "⑤3개이상날"),
            ("⑥ + 상대갭 -3.5%p", "⑥갭"),
            ("⑦ + 하루 4종목 상한  = **살 수 있는 것**", "⑦하루상한"))
    for 라, k in 이름:
        n = 칸[k]
        비 = f"{n/앞*100:>12.1f}%" if 앞 else f"{'—':>13}"
        print(f"  {라:<26}{n:>14,}{n/해수:>11.0f}개{비}")
        앞 = n or 1
    print(f"\n  {'실제 매수 (돈 있을 때만)':<26}{'':>14}{16.4:>11.1f}번"
          f"   <- 여기서 또 절반 넘게 준다 (현금 소진)")

    print("\n  ── 날짜로 보면 ──")
    n = 날수["전체"]
    for 라, k in (("전체 거래일", "전체"), ("후보가 1개라도 있는 날", "후보1개↑"),
                  ("후보가 3개 이상인 날", "후보3개↑"),
                  ("갭까지 통과한 게 있는 날", "갭통과날")):
        print(f"  {라:<26}{날수[k]:>8,}일{날수[k]/n*100:>8.1f}%"
              f"{날수[k]/해수:>10.0f}일/년")

    print("\n" + "=" * 92)
    print("  읽는 법")
    print("    - **앞 단계 대비**가 가장 작은 곳이 **가장 세게 막는 곳**이다")
    print("    - 「후보 3개 이상인 날만」과 「상대갭」 둘이 크면")
    print("      **문턱이 아니라 08:50 절차가 문제**다 (173·174차)")
    print("    - 「하루 4종목」과 「현금」이 크면 **자산 배분이 문제**다")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT") or "2026-09-09_181차_깔때기.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
