#!/usr/bin/env python3
r"""
timing_lab.py — **언제 팔까 · 얼마나 급하게 살까** (2026-09-02 · 18차)

⚠️⚠️ **아직 한 번도 안 재본 두 가지.**
   13차는 「며칠 들고 있나」를 **미리 정한 날수**로만 봤다. 실전은 그렇지 않다.

## ① 매도 규칙 — **날짜가 아니라 조건으로 판다면?**
```
고정 D+20 / D+60      ← 지금까지 쓴 것. 신호가 죽어도 계속 들고 있다
신호 소멸             대형=20일선 아래로 내려가면 / 소형=RSI 50 넘으면 판다
목표 도달             +10% 되면 판다 (이익 실현)
```
⚠️ **손절은 이미 독으로 판명났다(13·15차).** 여기서 보는 건 **이익 쪽 규칙**이다.

## ② 진입 지연 — **다음날 꼭 사야 하나?**
```
D+1 종가에 산다   ← 지금까지 쓴 것 (급하게)
D+2 / D+3 / D+5 종가에 산다
```
⚠️ 이게 중요한 이유 둘:
```
- 지연해서 성적이 안 죽으면 → **아침 브리핑이 굳이 09:00 전일 필요가 없다**
- 지연할수록 좋아지면 → 신호일 직후는 **비싸게 사는 것**이다 (되밀림을 기다려야)
```

⚠️ 잣대 동일가중(자기 크기 구간 대비) · 오염 제외 · 16.7년 · 학습/검증 분리 · t값.
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

_경계 = "20180101"
_MIN = 200
_최대일 = 60

크기표 = [("소형(3천억↓)", 0, 3e11), ("중형(3천억~1조)", 3e11, 1e12),
          ("대형(1조↑)", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def _t(a):
    n = len(a)
    if n < 30:
        return 0.0
    s = st.pstdev(a) or 1e-9
    return st.mean(a) / (s / math.sqrt(n))


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
                하루[c] = (종, float(v.get("시총") or 0), float(v.get("거래대금") or 0))
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    기본, 수급 = O._기본(), O._수급()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    매도 = {}      # (규칙, 크기, 기간) -> [초과%]
    보유일수 = {}  # (규칙, 크기) -> [일]
    진입 = {}      # (지연, 크기, 기간) -> [초과%]

    걸음 = 2
    for i in range(250, len(날) - _최대일 - 7, 걸음):
        d1 = 날[i]
        기간 = "학습" if d1 < _경계 else "검증"
        fl = 수급.get(d1) or {}

        # 크기별 후보와 기준선(D+20 · D+60)을 함께 만든다
        후보 = {}
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
            e20 = 주가[날[i + 21]].get(code)
            e60 = 주가[날[i + 1 + _최대일]].get(code)
            if not e20 or not e60:
                continue
            후보.setdefault(_크기(시총), []).append((code, v, k, m[0], e20[0], e60[0]))

        기준 = {}
        for g, a in 후보.items():
            if len(a) < 15:
                continue
            기준[g] = (st.mean([x[4] / x[3] - 1 for x in a]),
                       st.mean([x[5] / x[3] - 1 for x in a]))

        for g, a in 후보.items():
            if g not in 기준:
                continue
            b20, b60 = 기준[g]
            for code, v, k, 매수, p20, p60 in a:
                c1, 시총, 대금 = v
                sq = 종계[code]
                s20 = st.mean(sq[k - 19:k + 1])
                sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
                볼 = (c1 - s20) / (2 * sd)
                변14 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
                상 = st.mean([max(0, x) for x in 변14]) or 1e-9
                하 = st.mean([max(0, -x) for x in 변14]) or 1e-9
                rsi = 100 - 100 / (1 + 상 / 하)
                고 = max(sq[k - 250:k + 1])
                근접 = c1 / 고 if 고 else 0
                f = fl.get(code) or {}
                강 = (((f.get("외국인") or 0) + (f.get("기관") or 0)) * c1 / 시총 * 100
                      if 시총 > 0 else 0)

                # ⚠️ 크기별 신호는 12·13차 결과를 그대로 쓴다
                if g == "대형(1조↑)":
                    떴 = sum([근접 >= 0.999, rsi >= 70, 볼 >= 1.0, 강 >= 0.5]) >= 2
                    모멘텀 = True
                elif g == "중형(3천억~1조)":
                    떴 = sum([강 >= 0.5, 근접 >= 0.999, rsi >= 70, 볼 >= 1.0]) >= 2
                    모멘텀 = True
                else:
                    떴 = sum([볼 <= -1.0, rsi <= 30, c1 < s20, 강 >= 0.5]) >= 2
                    모멘텀 = False
                if not 떴:
                    continue

                # ── ① 매도 규칙 ──
                매도.setdefault(("고정 D+20", g, 기간), []).append((p20 / 매수 - 1 - b20) * 100)
                매도.setdefault(("고정 D+60", g, 기간), []).append((p60 / 매수 - 1 - b60) * 100)
                보유일수.setdefault(("고정 D+20", g), []).append(20)
                보유일수.setdefault(("고정 D+60", g), []).append(60)

                for 라벨, 조건 in (("신호 소멸", "소멸"), ("목표 +10%", "목표")):
                    팔, 든날 = None, _최대일
                    for j in range(i + 2, i + 1 + _최대일):
                        vv = 주가[날[j]].get(code)
                        if not vv:
                            continue
                        kk = (자리.get(code) or {}).get(날[j])
                        if kk is None or kk < 25:
                            continue
                        if 조건 == "목표":
                            if vv[0] >= 매수 * 1.10:
                                팔, 든날 = vv[0], j - i - 1
                                break
                        else:
                            m20 = st.mean(종계[code][kk - 19:kk + 1])
                            변 = [종계[code][z] - 종계[code][z - 1]
                                  for z in range(kk - 13, kk + 1)]
                            up = st.mean([max(0, x) for x in 변]) or 1e-9
                            dn = st.mean([max(0, -x) for x in 변]) or 1e-9
                            r2 = 100 - 100 / (1 + up / dn)
                            죽 = (vv[0] < m20) if 모멘텀 else (r2 >= 50)
                            if 죽:
                                팔, 든날 = vv[0], j - i - 1
                                break
                    if 팔 is None:
                        팔, 든날 = p60, _최대일
                    # ⚠️ 기준선도 실제 보유일에 맞춰야 공정하다 → 일수 비례로 섞는다
                    기 = (b20 * (든날 / 20) if 든날 <= 20
                          else b20 + (b60 - b20) * ((든날 - 20) / 40))
                    매도.setdefault((라벨, g, 기간), []).append((팔 / 매수 - 1 - 기) * 100)
                    보유일수.setdefault((라벨, g), []).append(든날)

                # ── ② 진입 지연 ──
                for 지연 in (1, 2, 3, 5):
                    b = 주가[날[i + 지연]].get(code)
                    끝 = 주가[날[i + 지연 + 20]].get(code)
                    if not b or not 끝:
                        continue
                    진입.setdefault((지연, g, 기간), []).append(
                        (끝[0] / b[0] - 1 - b20) * 100)
        if i % 400 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print("\n  ══ ① 매도 규칙 (신호 2개↑ 겹친 종목 · 자기 크기 구간 대비) ══")
    규칙들 = ["고정 D+20", "고정 D+60", "신호 소멸", "목표 +10%"]
    for g, _, _ in 크기표:
        print(f"\n  ── {g} ──")
        print(f"    {'규칙':<14}{'학습':>9}{'검증':>9}{'전체':>9}{'t값':>8}"
              f"{'평균보유':>9}{'표본':>9}")
        for r in 규칙들:
            ha = 매도.get((r, g, "학습")) or []
            va = 매도.get((r, g, "검증")) or []
            if len(ha) < _MIN or len(va) < _MIN:
                continue
            모 = ha + va
            일 = 보유일수.get((r, g)) or [0]
            표 = "*" if (st.mean(ha) > 0 and st.mean(va) > 0) else " "
            print(f"    {r:<14}{st.mean(ha):>+8.2f}%{st.mean(va):>+8.2f}%"
                  f"{st.mean(모):>+8.2f}{표}{_t(모):>8.1f}{st.mean(일):>8.1f}일"
                  f"{len(모):>9,}")

    print("\n  ══ ② 진입 지연 — 다음날 꼭 사야 하나 (D+20 보유) ══")
    for g, _, _ in 크기표:
        print(f"\n  ── {g} ──")
        print(f"    {'매수시점':<14}{'학습':>9}{'검증':>9}{'전체':>9}{'t값':>8}{'표본':>9}")
        for 지연 in (1, 2, 3, 5):
            ha = 진입.get((지연, g, "학습")) or []
            va = 진입.get((지연, g, "검증")) or []
            if len(ha) < _MIN or len(va) < _MIN:
                continue
            모 = ha + va
            표 = "*" if (st.mean(ha) > 0 and st.mean(va) > 0) else " "
            이름 = "신호+" + str(지연) + "일 종가"
            print(f"    {이름:<14}{st.mean(ha):>+8.2f}%"
                  f"{st.mean(va):>+8.2f}%{st.mean(모):>+8.2f}{표}{_t(모):>8.1f}"
                  f"{len(모):>9,}")

    print("\n  읽는 법")
    print("    - ①에서 '신호 소멸'이 '고정'보다 **평균보유가 짧으면서 성적이 같거나 낫다**면")
    print("      → 자본이 빨리 돌아 같은 돈으로 더 많이 거래할 수 있다 = 이득")
    print("    - ②가 지연해도 안 떨어지면 → **아침에 급할 필요가 없다**(브리핑 시각이 자유로워진다)")
    print("    - ②가 지연할수록 좋아지면 → 신호 직후는 **비싸게 사는 것**이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
