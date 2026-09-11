#!/usr/bin/env python3
r"""
volprofile_lab.py — **매물대(Volume Profile) 검증** (2026-09-02 · 11차)

⚠️⚠️ **사용자가 NH 앱 차트 지표 150여 개를 보여주며 물었다: 데이터가 더 필요한가.**
   → 대부분은 **OHLCV의 변형**이라 추가 데이터가 필요 없고, **이미 잰 것과 겹친다.**
   ⚠️ **매물대만 성격이 다르다** — 「과거 가격의 변형」이 아니라
      **「어느 가격대에 물량이 얼마나 쌓였나」**다. 한 번도 안 재봤다.

**어떻게 계산하나** (일봉으로 근사)
```
최근 120거래일을 40개 가격 구간으로 나눈다
각 날의 거래량을 그날 저가~고가 구간에 **고르게 배분**한다
⚠️ 정확히 하려면 분봉·틱이 필요하다. 우리는 없다.
   다만 많은 차트 도구도 일봉으로 근사한다 — 실용상 충분하다
```

**재는 것**
```
① 현재가 위 매물 비중    위에 쌓인 물량이 많으면 오르기 어렵다는 통념
② 현재가가 매물대 안/밖   최대 매물 구간(POC) 대비 위치
③ 매물대 돌파           최대 매물 구간을 막 위로 뚫었나
④ 매물 공백             위쪽에 물량이 거의 없나 (「매물 빈 공간」)
⑤ 매물 집중도           물량이 한 구간에 몰렸나 흩어졌나
```

⚠️ 잣대 **동일가중** · 매수 D+1 종가 · D+20 보유 · 오염 제외 · 16.7년.
⚠️ 학습/검증 분리 + **다중검정 계산**(축 N개면 N×25%가 우연히 「둘 다 +」).
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = 20
_창 = 120            # 매물대를 볼 기간
_구간수 = 40
_경계 = "20180101"
_MIN = 400


def _주가():
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"]); 고 = float(v["고가"]); 저 = float(v["저가"])
                if 종 <= 0 or 고 <= 0 or 저 <= 0:
                    continue
                하루[c] = (종, 고, 저, float(v.get("시총") or 0),
                           float(v.get("거래대금") or 0), float(v.get("거래량") or 0))
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    기본 = O._기본()
    종계, 고계, 저계, 량계, 자리 = {}, {}, {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            고계.setdefault(c, []).append(v[1])
            저계.setdefault(c, []).append(v[2])
            량계.setdefault(c, []).append(v[5])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    통 = {}

    def 담(축, 구간, v):
        통.setdefault((축, 구간), []).append(v)

    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + _H >= len(날):
            continue
        구간 = "학습" if d1 < _경계 else "검증"
        s1 = 주가[d1]
        후보, 수익 = [], []
        for code, v in s1.items():
            if v[3] < O._MIN_MC or v[4] < O._MIN_AMT:
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
            후보.append((code, v, e[0] / m[0] - 1))
            수익.append(e[0] / m[0] - 1)
        if len(후보) < 100:
            continue
        기준 = st.mean(수익)

        for code, v, r in 후보:
            c1, 고, 저, 시총, 대금, 량 = v
            k = (자리.get(code) or {}).get(d1)
            초 = (r - 기준) * 100

            # ── 매물대 계산 ──
            a, b = k - _창 + 1, k + 1
            hs, ls, vs = 고계[code][a:b], 저계[code][a:b], 량계[code][a:b]
            바닥, 천장 = min(ls), max(hs)
            if 천장 <= 바닥:
                continue
            폭 = (천장 - 바닥) / _구간수
            버킷 = [0.0] * _구간수
            for h2, l2, q in zip(hs, ls, vs):
                if q <= 0:
                    continue
                s = max(0, min(_구간수 - 1, int((l2 - 바닥) / 폭)))
                t = max(0, min(_구간수 - 1, int((h2 - 바닥) / 폭)))
                n = t - s + 1
                for j in range(s, t + 1):
                    버킷[j] += q / n
            총량 = sum(버킷) or 1e-9
            현구간 = max(0, min(_구간수 - 1, int((c1 - 바닥) / 폭)))
            위 = sum(버킷[현구간 + 1:]) / 총량 * 100          # 현재가 위 매물 비중
            poc = max(range(_구간수), key=lambda j: 버킷[j])   # 최대 매물 구간
            # 최대 매물 구간을 방금 뚫었나 (어제는 아래, 오늘은 위)
            전종 = 종계[code][k - 1]
            전구간 = max(0, min(_구간수 - 1, int((전종 - 바닥) / 폭)))
            돌파 = 전구간 <= poc < 현구간
            # 집중도: 상위 5구간이 전체의 몇 %
            집중 = sum(sorted(버킷, reverse=True)[:5]) / 총량 * 100

            축들 = [
                ("A 위 매물 20%↓ (가볍다)", 위 <= 20),
                ("A 위 매물 20~50%", 20 < 위 <= 50),
                ("A 위 매물 50~80%", 50 < 위 <= 80),
                ("A 위 매물 80%↑ (무겁다)", 위 > 80),
                ("B POC 위", 현구간 > poc),
                ("B POC 아래", 현구간 < poc),
                ("B POC 구간 안", 현구간 == poc),
                ("C POC 돌파(막 뚫음)", 돌파),
                ("D 집중도 높음(상위5구간 60%↑)", 집중 >= 60),
                ("D 집중도 낮음(40%↓)", 집중 < 40),
                ("E 위매물 가볍고 + 대형주", 위 <= 20 and 시총 >= 1e12),
                ("E 위매물 무겁고 + 대형주", 위 > 80 and 시총 >= 1e12),
                ("F POC돌파 + 거래량3배",
                 돌파 and 량 >= (st.mean(량계[code][k - 20:k]) or 1) * 3),
            ]
            for 이름, 참 in 축들:
                if 참:
                    담(이름, 구간, 초)
            담("0 전 종목(기준선)", 구간, 초)
        if i % 400 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    축이름 = sorted({a for (a, _) in 통})
    print(f"\n  매물대: 최근 {_창}일 · {_구간수}구간 · D+{_H} · 동일가중 대비\n")
    print(f"  {'축':<32}{'전체':>17}{'학습':>17}{'검증':>17}  판정")
    둘다 = 잰것 = 0
    for a in 축이름:
        ha = 통.get((a, "학습")) or []
        va = 통.get((a, "검증")) or []
        모 = ha + va
        if len(모) < _MIN:
            continue
        def f(x):
            return f"{st.mean(x):+.3f}% ({len(x)//1000}k)" if len(x) >= _MIN // 2 else "-"
        판 = ""
        if len(ha) >= _MIN // 2 and len(va) >= _MIN // 2:
            잰것 += 1
            h, v = st.mean(ha), st.mean(va)
            if h > 0 and v > 0:
                판 = "⭐ 둘 다 +"
                둘다 += 1
            elif h < 0 and v < 0:
                판 = "❌ 둘 다 −"
            else:
                판 = "· 뒤집힘"
        print(f"  {a:<32}{f(모):>17}{f(ha):>17}{f(va):>17}  {판}")
    print(f"\n  ══ 다중검정 ══  잰 축 {잰것}개 · 우연 기대 {잰것*0.25:.1f}개 · **실제 {둘다}개**")
    print("    → " + ("⚠️ 우연 수준이거나 그 이하" if 둘다 <= 잰것 * 0.25
                      else "우연보다 많다. 살펴볼 값어치가 있다"))
    print("\n  읽는 법")
    print("    - 통념: '위에 매물이 많으면 오르기 어렵다' → A축이 그걸 검증한다")
    print("    - ⚠️ 일봉 근사다. 분봉/틱이 있으면 더 정확하지만 우리는 없다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
