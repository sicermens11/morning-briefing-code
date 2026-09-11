#!/usr/bin/env python3
r"""market_wide_test.py — **전 종목 소급 검증** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 브리핑 픽은 하루 3.2건뿐이라 무엇을 물어도 표본이 모자랐다
   (2026-09-01 기준 19건). 그런데 **주가에서 나오는 지표는 전 종목에 소급할 수 있다** —
   `data\krx-daily\`에 하루치 전 종목(2,766개)이 통째로 쌓이기 때문이다.
   18거래일만으로 **24,016건**이 나왔다. 표본 문제의 상당 부분이 여기서 풀린다.

⚠️⚠️ **반드시 초과수익률로 잰다. 절대 수익률은 거짓말을 한다.**
   2026-09-01 실측이 그 증거다 — 같은 데이터인데 재는 방법에 따라 결론이 뒤집혔다:
```
                절대 수익률        초과수익률(시장 대비)
   급등(+5%↑)    +0.674%p 좋음  →   +0.018%p  사실상 0
   무반응(<1%)    +0.234%p 좋음  →   -0.014%p  사실상 0
   급락(-5%↓)    -2.446%p 나쁨  →   -0.649%p  여전히 나쁨
```
   이 기간(07-28~08-31) 전 종목 평균이 **하루 +0.579%**였다. 오른 날이 많으니
   **아무 규칙이나 다 좋아 보인다.** 갭①에서 당한 「기간 효과」와 같은 함정이다.

⚠️ **못 재는 것이 있다.** 갭①(시간)·갭②(정보)는 **뉴스가 있어야** 판정되는데
   과거 전 종목 뉴스가 없다. ⇒ 이 스크립트는 **주가 기반 지표 검증**에는 강력하고
   **갭 전략 자체의 검증**에는 쓸 수 없다. 갭④도 우리 정의는 "재료가 났는데도 무반응"이라
   여기서 재는 "그냥 무반응"과 다르다 — **같은 것으로 취급하지 않는다.**

⚠️ **중간에 빠진 날은 뺀다.** `krx-daily`에 없는 거래일이 있어(08-07·08-14~19·08-25~26)
   이어지지 않은 쌍으로 D+1을 계산하면 틀린다. 달력 간격 3일 이하만 쓴다.

⚠️ 걸러내는 것: 시총 500억 미만·거래대금 1억 미만. 호가가 얇아 수익률이 튄다.

쓰는 법:
    python scripts\market_wide_test.py
"""
import io, json, glob, datetime as dt, statistics as st
fs = sorted(glob.glob('data/krx-daily/*.json'))
일 = []
for f in fs:
    d = json.load(io.open(f, encoding='utf-8-sig'))
    일.append((d['기준일'], d['종목']))
def 날(s): return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))

행 = []
for i in range(len(일) - 1):
    (d1, s1), (d2, s2) = 일[i], 일[i + 1]
    if (날(d2) - 날(d1)).days > 3: continue
    # 그 다음날 시장 전체 등락 (기간 통제용)
    시장 = st.mean([float(v['등락률']) for v in s2.values()
                    if v.get('등락률') is not None and float(v.get('시총') or 0) >= 5e10])
    for code, v1 in s1.items():
        v2 = s2.get(code)
        if not v2: continue
        try:
            c1, c2 = float(v1['종가']), float(v2['종가'])
            r1 = float(v1['등락률']); 시총 = float(v1['시총']); 대금 = float(v1['거래대금'])
        except (TypeError, ValueError, KeyError): continue
        if c1 <= 0 or 시총 < 5e10 or 대금 < 1e8: continue
        수익 = (c2 / c1 - 1) * 100
        행.append({"초과": 수익 - 시장, "등락": r1, "시장": 시장})

print(f"  관측 {len(행):,}건 — **초과수익률**(종목 − 그날 시장 평균)으로 다시 잰다\n")
def 비교(이름, 조건):
    a = [x["초과"] for x in 행 if 조건(x)]
    b = [x["초과"] for x in 행 if not 조건(x)]
    if not a or not b: return
    print(f"  {이름:20s} n={len(a):6,d} {st.mean(a):+6.3f}%p  |  n={len(b):6,d} {st.mean(b):+6.3f}%p"
          f"  →  차이 {st.mean(a)-st.mean(b):+6.3f}%p")
비교("갭④ 무반응(<1%)", lambda x: abs(x["등락"]) < 1)
비교("전날 급등(+5%↑)", lambda x: x["등락"] >= 5)
비교("전날 급락(−5%↓)", lambda x: x["등락"] <= -5)
print()
print("  ── 시장이 오른 날 / 내린 날로 갈라서 (기간 효과 통제)")
for 라벨, 필터 in [("시장 상승일", lambda x: x["시장"] > 0), ("시장 하락일", lambda x: x["시장"] <= 0)]:
    부분 = [x for x in 행 if 필터(x)]
    print(f"\n  [{라벨}] {len(부분):,}건")
    for 이름, cond in [("무반응", lambda x: abs(x["등락"]) < 1),
                       ("급등(+5%↑)", lambda x: x["등락"] >= 5),
                       ("급락(−5%↓)", lambda x: x["등락"] <= -5)]:
        a = [x["초과"] for x in 부분 if cond(x)]
        b = [x["초과"] for x in 부분 if not cond(x)]
        if not a or not b: continue
        print(f"    {이름:12s} n={len(a):5,d} {st.mean(a):+6.3f}%p  vs  {st.mean(b):+6.3f}%p"
              f"  →  {st.mean(a)-st.mean(b):+6.3f}%p")
