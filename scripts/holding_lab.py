#!/usr/bin/env python3
r"""
holding_lab.py — **얼마나 들고 있어야 하나 (단타 vs 장기)** (2026-09-02 · 13차)

⚠️⚠️ **사용자 요청.**
   *"종목 추천할 때 해당 종목을 장기적으로 갖고 있는 게 좋을지, 단타를 치는 게 좋을지도
   분석해서 알려줄 수 있을 것 같은데?"*
   → **맞다. 그리고 그게 실전에 가장 직접 쓰인다.** 지금까지 단편적으로만 봤다:
```
momentum_lab   신고가는 D+20~60이 좋았다
entry_lab      갭①④는 D+1이 가장 좋고 D+20에 죽었다
→ ⚠️ **신호마다 최적 보유기간이 다르다.** 체계적으로 안 쟀다
```

**재는 것**
```
신호 10종 × 보유기간 8구간(1·3·5·10·20·40·60·120일) × 크기 3구간
```

**두 가지를 같이 낸다 — 이게 핵심이다**
```
① 원값        보유기간별 초과수익 (동일가중, 자기 크기 구간 대비)
② **비용 후 연환산**   ⚠️ **단타는 회전율이 높아 비용을 훨씬 많이 낸다**
                 D+1을 1년 내내 하면 245번 사고판다 → 비용 245 × 0.26% = **연 63.7%**
                 D+120이면 2번 → 연 0.5%
                 **그래서 원값이 같아도 단타가 훨씬 불리하다**
```
⚠️ 이 비교를 안 하면 「D+1이 제일 좋다」는 착각을 한다.

⚠️ 잣대 동일가중(자기 크기 구간) · 매수 D+1 종가 · 오염 제외 · 16.7년 · 학습/검증 분리.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_보유들 = (1, 3, 5, 10, 20, 40, 60, 120)
_경계 = "20180101"
_MIN = 300
_비용 = 0.26          # 왕복 %
_거래일 = 245

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


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    기본, 수급 = O._기본(), O._수급()
    공시 = O._공시(날)
    종계, 량계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            량계.setdefault(c, []).append(v[3])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    통 = {}

    def 담(신호, 크기, h, 기간, v):
        통.setdefault((신호, 크기, h, 기간), []).append(v)

    최대 = max(_보유들)
    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + 최대 >= len(날):
            continue
        기간 = "학습" if d1 < _경계 else "검증"
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}

        # 크기 구간별 후보 + 보유기간별 기준선
        후보 = {}
        for code, v in s1.items():
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
            if not m:
                continue
            수 = {}
            for h in _보유들:
                e = 주가[날[i + 1 + h]].get(code)
                if e:
                    수[h] = e[0] / m[0] - 1
            if len(수) < len(_보유들):
                continue
            후보.setdefault(_크기(시총), []).append((code, v, 수))
        기준 = {}
        for g, a in 후보.items():
            if len(a) < 15:
                continue
            기준[g] = {h: st.mean([수[h] for _, _, 수 in a]) for h in _보유들}

        for g, a in 후보.items():
            if g not in 기준:
                continue
            for code, v, 수 in a:
                c1, 시총, 대금, 량 = v
                k = (자리.get(code) or {}).get(d1)
                sq = 종계[code]
                s20 = st.mean(sq[k - 19:k + 1])
                sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
                볼하 = s20 - 2 * sd
                변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
                상 = st.mean([max(0, x) for x in 변]) or 1e-9
                하 = st.mean([max(0, -x) for x in 변]) or 1e-9
                rsi = 100 - 100 / (1 + 상 / 하)
                신고 = c1 >= max(sq[k - 250:k + 1]) * 0.999
                평량 = st.mean(량계[code][k - 20:k]) or 1
                f = fl.get(code) or {}
                강도 = (((f.get("외국인") or 0) + (f.get("기관") or 0)) * c1 / 시총 * 100
                        if 시총 > 0 else 0)
                rr = ds.get(code) or {}
                호재 = "호재" in rr.get("성격", set())
                장후 = rr.get("분") is not None and rr["분"] >= 930

                신호들 = ["0 기준선"]
                if 신고:
                    신호들.append("A 52주 신고가")
                if c1 < 볼하:
                    신호들.append("B 볼린저 하단 이탈")
                if c1 < 볼하 and rsi <= 30:
                    신호들.append("C 반전(볼하단+RSI과매도)")
                if rsi >= 70:
                    신호들.append("D RSI 과매수")
                if 량 >= 평량 * 3:
                    신호들.append("E 거래량 3배↑")
                if 강도 >= 0.5:
                    신호들.append("F 수급강도 0.5%↑")
                if 호재:
                    신호들.append("G 호재 공시")
                    if 장후:
                        신호들.append("H 호재+장 마감 후")
                if c1 > s20:
                    신호들.append("I 20일선 위")
                else:
                    신호들.append("J 20일선 아래")

                for s in 신호들:
                    for h in _보유들:
                        담(s, g, h, 기간, (수[h] - 기준[g][h]) * 100)
        if i % 400 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    신호들 = sorted({s for (s, _, _, _) in 통})
    print(f"\n  ══ ① 원값: 보유기간별 초과수익 (자기 크기 구간 대비) ══")
    for g, _, _ in 크기표:
        print(f"\n  ── {g} ──")
        print(f"    {'신호':<24}" + "".join(f"{'D+'+str(h):>9}" for h in _보유들))
        for s in 신호들:
            줄 = []
            for h in _보유들:
                ha = 통.get((s, g, h, "학습")) or []
                va = 통.get((s, g, h, "검증")) or []
                if len(ha) < _MIN or len(va) < _MIN:
                    줄.append("-")
                    continue
                hv, vv = st.mean(ha), st.mean(va)
                표 = "*" if (hv > 0 and vv > 0) else ("x" if (hv < 0 and vv < 0) else " ")
                줄.append(f"{(hv+vv)/2:+.2f}{표}")
            if all(x == "-" for x in 줄):
                continue
            print(f"    {s:<24}" + "".join(f"{x:>9}" for x in 줄))

    print(f"\n  ══ ② **비용 후 연환산** — 단타의 진짜 값 ══")
    print(f"     ⚠️ D+1을 1년 내내 하면 245번 사고판다 → 비용만 연 {245*_비용:.0f}%")
    for g, _, _ in 크기표:
        print(f"\n  ── {g} ──")
        print(f"    {'신호':<24}" + "".join(f"{'D+'+str(h):>9}" for h in _보유들) + "   최적")
        for s in 신호들:
            if s.startswith("0"):
                continue
            줄, 값 = [], []
            for h in _보유들:
                ha = 통.get((s, g, h, "학습")) or []
                va = 통.get((s, g, h, "검증")) or []
                if len(ha) < _MIN or len(va) < _MIN:
                    줄.append("-")
                    값.append(None)
                    continue
                hv, vv = st.mean(ha), st.mean(va)
                평 = (hv + vv) / 2
                순 = 평 - _비용                      # 왕복 비용 한 번
                연 = 순 * (_거래일 / h)              # 1년에 몇 번 굴리나
                둘다 = (hv > 0 and vv > 0)
                줄.append(f"{연:+.1f}{'*' if 둘다 else ' '}")
                값.append(연 if 둘다 else None)
            if all(x == "-" for x in 줄):
                continue
            좋 = [(v, _보유들[j]) for j, v in enumerate(값) if v is not None]
            최적 = f"D+{max(좋)[1]} ({max(좋)[0]:+.1f}%)" if 좋 else "없음"
            print(f"    {s:<24}" + "".join(f"{x:>9}" for x in 줄) + f"   {최적}")

    print("\n  읽는 법")
    print("    - '*'는 학습·검증 둘 다 +인 칸이다. 그것만 믿는다")
    print("    - ①은 한 번 거래의 초과수익, ②는 그걸 **1년 내내 반복**했을 때 비용 후 값")
    print(f"    - ⚠️ 왕복비용 {_비용}%를 매 거래마다 뺐다. 단타일수록 이게 커진다")
    print("    - '최적'은 비용 후 연환산이 가장 큰 보유기간이다 = **며칠 들고 있어야 하나**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
