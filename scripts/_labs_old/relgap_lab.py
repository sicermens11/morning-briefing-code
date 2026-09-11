#!/usr/bin/env python3
r"""
relgap_lab.py — **「시장보다 얼마나 더 빠지며 출발했나」를 16.7년으로** (2026-09-02 · 52차)

⚠️⚠️ **51차에서 나온 것을 전 기간으로 확장한다.**
```
51차(3년치 예비)
  미국 −0.5%↓ (시장이 같이 빠짐)   **+12.60%**  승률 **72.3%**
  시장보다 3%p 넘게 더 빠짐        **+13.96%**  승률 **73.4%**
⚠️ 미국 지수는 3년뿐이라 못 늘린다.
   **그런데 「한국 시장 전체 갭」은 16.7년 다 있다** → 그걸로 확장한다
```

## 왜 이게 미국장을 대신할 수 있나
```
51차: 미국장 → 한국 시장 갭 상관 **+0.551**
⇒ 「한국 시장 전체가 갭 하락한 날」은 대체로 **「미국이 빠진 날」**이다
⇒ 미국 지수 없이도 같은 것을 잴 수 있고, **16.7년치**를 쓸 수 있다
```

## 재는 것
```
① 시장 전체 갭(전 종목 중앙값) 구간별 → 신호 성적
② **상대 갭** = 그 종목 갭 − 시장 전체 갭. 구간별 성적
③ 둘을 겹쳤을 때 (시장도 빠지고 그 종목은 더 빠짐)
④ 연도별 — 16해 중 몇 해
```
⚠️ 신호: 볼하단 + 20일−10%↓ · 소형 (갭 조건은 여기서 쪼갠다)
⚠️ 판정: 절대 수익 · 승률 · 연도별. 다음날 시가 매수 · D+20 · 비용 0.26%.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_보유 = 20


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본 = O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # 원본에서 갭을 만든다 (시가/전일종가)
    갭표, 시장갭 = {}, {}
    앞종 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
    print(f"  거래일 {len(날):,} · 시장갭 있는 날 {len(시장갭):,}일", flush=True)

    # 사건: 볼하단 + 20일−10%↓ · 소형 (갭은 쪼갠다)
    사건 = []   # (해, 시장갭, 종목갭, 상대갭, 수익)
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0:
                continue
            if k < 20 or sq[k - 20] <= 0 or (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            g = 하루갭.get(code)
            if g is None:
                continue
            나 = 주가[다음].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            r = (끝[0] / 매수 - 1) * 100 - _비용
            사건.append((d1[:4], 시갭, g, g - 시갭, r))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len(날) / 245
    전 = [x[4] for x in 사건]
    print(f"  사건 {len(사건):,}건 · 연 {len(사건)/년수:.0f}건 · "
          f"전체 평균 {st.mean(전):+.2f}% · 승률 "
          f"{sum(1 for x in 전 if x > 0)/len(전)*100:.1f}%", flush=True)

    def 표찍(제목, 칸들, 뽑기):
        print(f"\n  ══ {제목} ══")
        print(f"    {'구간':<22}{'평균':>9}{'승률':>8}{'연간':>8}{'연도별':>9}{'표본':>9}")
        for 라, lo, hi in 칸들:
            a = [x for x in 사건 if lo <= 뽑기(x) < hi]
            if len(a) < 300:
                continue
            수 = [x[4] for x in a]
            승 = sum(1 for x in 수 if x > 0) / len(수) * 100
            해별 = {}
            for x in a:
                해별.setdefault(x[0], []).append(x[4])
            전c = 플 = 0
            for y, arr in 해별.items():
                if len(arr) < 15:
                    continue
                전c += 1
                플 += 1 if st.mean(arr) > 0 else 0
            통과 = 전c >= 10 and 플 / 전c >= 2 / 3
            별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 통과) else (
                "○" if st.mean(수) > 0 and 통과 else "  ")
            print(f"    {라:<22}{st.mean(수):>+8.2f}%{승:>7.1f}%"
                  f"{len(수)/년수:>7.0f}건{f'{플}/{전c}':>9}{len(수):>9,}{별}")

    표찍("① **시장 전체가** 얼마나 낮게 출발했나",
         [("시장 −1%↓", -99, -1), ("시장 −1~−0.3%", -1, -0.3),
          ("시장 −0.3~+0.3%", -0.3, 0.3), ("시장 +0.3~+1%", 0.3, 1),
          ("시장 +1%↑", 1, 99)],
         lambda x: x[1])

    표찍("② **상대 갭** = 그 종목 갭 − 시장 갭",
         [("상대 −7%p↓", -99, -7), ("상대 −7~−4%p", -7, -4),
          ("상대 −4~−2%p", -4, -2), ("상대 −2~0%p", -2, 0),
          ("상대 0~+2%p", 0, 2), ("상대 +2%p↑", 2, 99)],
         lambda x: x[3])

    표찍("③ 그 종목의 **절대 갭** (참고)",
         [("갭 −5%↓", -99, -5), ("갭 −5~−2%", -5, -2), ("갭 −2~0%", -2, 0),
          ("갭 0~+2%", 0, 2), ("갭 +2%↑", 2, 99)],
         lambda x: x[2])

    print(f"\n  ══ ④⭐ **둘을 겹쳤을 때** (시장도 빠지고 그 종목은 더 빠짐) ══")
    print(f"    {'조건':<34}{'평균':>9}{'승률':>8}{'연간':>8}{'연도별':>9}{'표본':>9}")
    조합 = [
        ("시장 −0.3%↓ + 상대 −4%p↓", lambda x: x[1] < -0.3 and x[3] < -4),
        ("시장 −0.3%↓ + 상대 −2%p↓", lambda x: x[1] < -0.3 and x[3] < -2),
        ("시장 −0.3%↓ + 상대 0%p↓", lambda x: x[1] < -0.3 and x[3] < 0),
        ("시장 −1%↓ + 상대 −2%p↓", lambda x: x[1] < -1 and x[3] < -2),
        ("시장 +0.3%↑ + 상대 −4%p↓ (시장은 좋은데)",
         lambda x: x[1] > 0.3 and x[3] < -4),
        ("시장 −0.3%↓ (상대 무관)", lambda x: x[1] < -0.3),
        ("상대 −4%p↓ (시장 무관)", lambda x: x[3] < -4),
    ]
    for 라, f in 조합:
        a = [x for x in 사건 if f(x)]
        if len(a) < 300:
            print(f"    {라:<34}{'표본 부족 (' + str(len(a)) + ')':>20}")
            continue
        수 = [x[4] for x in a]
        승 = sum(1 for x in 수 if x > 0) / len(수) * 100
        해별 = {}
        for x in a:
            해별.setdefault(x[0], []).append(x[4])
        전c = 플 = 0
        for y, arr in 해별.items():
            if len(arr) < 15:
                continue
            전c += 1
            플 += 1 if st.mean(arr) > 0 else 0
        통과 = 전c >= 10 and 플 / 전c >= 2 / 3
        별 = "⭐" if (st.mean(수) > 0 and 승 >= 65 and 통과) else (
            "○" if st.mean(수) > 0 and 통과 else "  ")
        print(f"    {라:<34}{st.mean(수):>+8.2f}%{승:>7.1f}%"
              f"{len(수)/년수:>7.0f}건{f'{플}/{전c}':>9}{len(수):>9,}{별}")

    # 최고 조합의 연도별
    print(f"\n  ══ ⑤ 연도별 — 「시장 −0.3%↓ + 상대 −4%p↓」 ══")
    a = [x for x in 사건 if x[1] < -0.3 and x[3] < -4]
    해별 = {}
    for x in a:
        해별.setdefault(x[0], []).append(x[4])
    print(f"    {'해':<7}{'건수':>7}{'평균':>10}{'승률':>8}")
    플, 전c = 0, 0
    for y in sorted(해별):
        arr = 해별[y]
        if len(arr) < 10:
            print(f"    {y:<7}{len(arr):>7}{'표본부족':>10}")
            continue
        승 = sum(1 for x in arr if x > 0) / len(arr) * 100
        전c += 1
        플 += 1 if st.mean(arr) > 0 else 0
        표 = "⭐" if st.mean(arr) > 0 else "❌"
        print(f"    {y:<7}{len(arr):>7}{st.mean(arr):>+9.2f}%{승:>7.1f}%{표}")
    if 전c:
        print(f"    ⇒ **{전c}해 중 {플}해 + ({플/전c*100:.0f}%)**")

    print("\n  읽는 법")
    print("    - ②의 '상대 갭'이 핵심이다 — **시장보다 얼마나 더 빠지며 출발했나**")
    print("    - ④에서 「시장은 좋은데 그 종목만 빠진 것」이 나쁘면 51차(3년)와 일치한다")
    print("    - ⚠️ 이건 **16.7년 전체**다. 51차의 미국장 결과(3년)를 전 기간으로 확장한 것이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
