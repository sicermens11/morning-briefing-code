#!/usr/bin/env python3
r"""
strength_lab.py — **신호 강도의 연속값 · 중첩 · 통계적 유의성** (2026-09-02 · 14차)

⚠️⚠️⚠️ **내가 스스로 찾은 가장 큰 구멍 셋을 한 번에 메운다.**
   사용자: *"지금 추가로 테스트해야 할 거를 내가 말해주고 있는데, 네가 분석해서
   추가로 테스트해야 할 게 있는지 찾아봐"* → 투자 결정 흐름으로 훑어 셋을 골랐다.

## ① 신호 강도의 **연속값** — 가장 큰 구멍
지금까지 **전부 이분법**으로 쟀다: 「신고가다/아니다」 「RSI 30 이하다/아니다」.
⚠️ **「RSI 25 vs 29」 「신고가 99% vs 100%」의 차이를 통째로 버렸다.**
→ 각 지표를 **10분위**로 잘라 **단조성**을 본다.
   ⚠️⚠️ **단조로우면 진짜 신호다.** 한 칸만 튀면 우연이다.
   (이분법에선 이 구분이 아예 안 된다)

## ② 신호 **중첩(시너지)**
두세 신호가 동시에 뜨면 **1+1>2인가?** 몇 조합만 봤지 체계적으로 안 봤다.
→ 신호 개수(0~4개)별 성적을 본다. **개수가 늘수록 좋아지면 시너지가 있다.**

## ③ **통계적 유의성**
지금 판정 기준은 「학습·검증 둘 다 +」뿐이다. ⚠️ **너무 헐겁다.**
표본이 크면 +0.01%도 「둘 다 +」가 되고, 작으면 +2%도 우연이다.
→ **t값**을 같이 낸다. |t| ≥ 2 면 우연일 확률이 5% 미만이다.
   ⚠️ 다만 축이 많으면 t≥2도 우연히 나온다 → **본페로니 보정**(t 문턱을 높인다)도 같이 찍는다.

⚠️ 잣대 동일가중(자기 크기 구간 대비) · 매수 D+1 종가 · **D+20** · 오염 제외 · 16.7년.
"""
import glob
import io
import json
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = 20
_경계 = "20180101"
_MIN = 300

크기표 = [("소형(3천억↓)", 0, 3e11), ("중형(3천억~1조)", 3e11, 1e12),
          ("대형(1조↑)", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def _주가():
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                if 종 <= 0:
                    continue
                하루[c] = (종, float(v.get("시총") or 0), float(v.get("거래대금") or 0),
                           float(v.get("거래량") or 0))
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def _t(a):
    """t값. |t|≥2 면 우연일 확률 5% 미만."""
    n = len(a)
    if n < 30:
        return 0.0
    s = st.pstdev(a) or 1e-9
    return st.mean(a) / (s / math.sqrt(n))


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    기본, 수급 = O._기본(), O._수급()
    종계, 량계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            량계.setdefault(c, []).append(v[3])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    # 지표별 값을 모아 10분위 경계를 정한다 (표본 추출로 빠르게)
    표본 = {"RSI": [], "신고가근접": [], "볼린저위치": [], "수급강도": [], "거래량배수": []}
    걸음 = max(1, len(날) // 200)
    for i in range(250, len(날) - _H - 1, 걸음):
        d1 = 날[i]
        fl = 수급.get(d1) or {}
        for code, v in list(주가[d1].items())[::7]:
            c1, 시총, 대금, 량 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            표본["RSI"].append(100 - 100 / (1 + 상 / 하))
            고 = max(sq[k - 250:k + 1])
            표본["신고가근접"].append(c1 / 고 * 100 if 고 else 0)
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            표본["볼린저위치"].append((c1 - s20) / (2 * sd))
            f = fl.get(code) or {}
            표본["수급강도"].append(
                (((f.get("외국인") or 0) + (f.get("기관") or 0)) * c1 / 시총 * 100)
                if 시총 > 0 else 0)
            평량 = st.mean(량계[code][k - 20:k]) or 1
            표본["거래량배수"].append(량 / 평량)
    경계 = {}
    for k2, a in 표본.items():
        if len(a) < 1000:
            continue
        a = sorted(a)
        경계[k2] = [a[int(len(a) * p / 10)] for p in range(1, 10)]
    print(f"  10분위 경계 계산 완료 ({', '.join(경계)})", flush=True)

    def 분위(이름, v):
        b = 경계.get(이름)
        if not b:
            return None
        for j, x in enumerate(b):
            if v < x:
                return j
        return 9

    통 = {}          # (축, 칸, 크기, 기간) -> [값]

    def 담(축, 칸, g, 기간, v):
        통.setdefault((축, 칸, g, 기간), []).append(v)

    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + _H >= len(날):
            continue
        기간 = "학습" if d1 < _경계 else "검증"
        fl = 수급.get(d1) or {}
        후보 = {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금, 량 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            if ((자리.get(code) or {}).get(d1) or 0) < 250:
                continue
            m = 주가[날[i + 1]].get(code)
            e = 주가[날[i + 1 + _H]].get(code)
            if not m or not e:
                continue
            후보.setdefault(_크기(시총), []).append((code, v, e[0] / m[0] - 1))
        기준 = {g: st.mean([r for _, _, r in a]) for g, a in 후보.items() if len(a) >= 15}

        for g, a in 후보.items():
            if g not in 기준:
                continue
            for code, v, r in a:
                c1, 시총, 대금, 량 = v
                k = (자리.get(code) or {}).get(d1)
                sq = 종계[code]
                초 = (r - 기준[g]) * 100
                변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
                상 = st.mean([max(0, x) for x in 변]) or 1e-9
                하 = st.mean([max(0, -x) for x in 변]) or 1e-9
                rsi = 100 - 100 / (1 + 상 / 하)
                고 = max(sq[k - 250:k + 1])
                근접 = c1 / 고 * 100 if 고 else 0
                s20 = st.mean(sq[k - 19:k + 1])
                sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
                볼 = (c1 - s20) / (2 * sd)
                f = fl.get(code) or {}
                강도 = (((f.get("외국인") or 0) + (f.get("기관") or 0)) * c1 / 시총 * 100
                        if 시총 > 0 else 0)
                평량 = st.mean(량계[code][k - 20:k]) or 1
                배수 = 량 / 평량

                # ① 연속값 10분위
                for 이름, 값 in (("RSI", rsi), ("신고가근접", 근접), ("볼린저위치", 볼),
                                 ("수급강도", 강도), ("거래량배수", 배수)):
                    q = 분위(이름, 값)
                    if q is not None:
                        담(이름, f"{q}분위", g, 기간, 초)

                # ② 신호 중첩 (그 크기에서 좋다고 나온 것들로만 센다)
                if g == "대형(1조↑)":
                    개 = sum([근접 >= 99.9, rsi >= 70, 볼 >= 1.0, 강도 >= 0.5])
                elif g == "중형(3천억~1조)":
                    개 = sum([강도 >= 0.5, 근접 >= 99.9, rsi >= 70, 볼 >= 1.0])
                else:
                    개 = sum([볼 <= -1.0, rsi <= 30, c1 < s20, 강도 >= 0.5])
                담("신호개수", f"{개}개", g, 기간, 초)
        if i % 400 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    축들 = ["RSI", "신고가근접", "볼린저위치", "수급강도", "거래량배수", "신호개수"]
    잰칸 = 0
    print(f"\n  ══ ① 연속값 10분위 · ③ t값 (D+{_H} · 자기 크기 구간 대비) ══")
    print("     ⚠️ **단조로우면 진짜 신호다.** 한 칸만 튀면 우연이다")
    for 축 in 축들:
        for g, _, _ in 크기표:
            칸들 = sorted({c for (a, c, gg, _) in 통 if a == 축 and gg == g},
                          key=lambda x: int(x[0]))
            if not 칸들:
                continue
            줄 = []
            for 칸 in 칸들:
                ha = 통.get((축, 칸, g, "학습")) or []
                va = 통.get((축, 칸, g, "검증")) or []
                모 = ha + va
                if len(모) < _MIN or len(ha) < 100 or len(va) < 100:
                    줄.append(("-", None))
                    continue
                잰칸 += 1
                t = _t(모)
                h, v = st.mean(ha), st.mean(va)
                표 = "*" if (h > 0 and v > 0) else ("x" if (h < 0 and v < 0) else " ")
                줄.append((f"{st.mean(모):+.2f}{표}", t))
            if all(x[0] == "-" for x in 줄):
                continue
            print(f"\n  ── {축} · {g} ──")
            print(f"    {'칸':<8}" + "".join(f"{c:>9}" for c in 칸들))
            print(f"    {'값':<8}" + "".join(f"{x[0]:>9}" for x in 줄))
            print(f"    {'t값':<8}" + "".join(
                (f"{x[1]:>9.1f}" if x[1] is not None else f"{'-':>9}") for x in 줄))
    문턱 = 2.0
    본 = math.sqrt(2 * math.log(max(2, 잰칸)))     # 대략적 본페로니 문턱
    print(f"\n  ══ ③ 통계 문턱 ══")
    print(f"    잰 칸 {잰칸}개 · 보통 문턱 |t|≥{문턱:.1f} · **본페로니 보정 문턱 |t|≥{본:.1f}**")
    print(f"    ⚠️ 칸이 많으므로 **|t|≥{본:.1f}** 를 넘어야 우연이 아니라고 말할 수 있다")
    print("\n  읽는 법")
    print("    - ①은 값이 분위를 따라 **단조롭게** 움직이는지 본다. 그게 진짜 신호의 모습이다")
    print("    - '신호개수'가 늘수록 값이 커지면 **중첩 시너지가 있다**")
    print("    - '*'는 학습·검증 둘 다 +. t값과 **같이** 봐야 한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
