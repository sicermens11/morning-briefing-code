#!/usr/bin/env python3
r"""
macro_lab.py — **밤사이 미국장이 다음날 한국 갭을 설명하나** (2026-09-02 · 51차)

⚠️⚠️ **아직 한 번도 안 쓴 축이다.**
```
us-index.json   S&P500 · 나스닥 · 다우 · 필라반도체  751일 (2023-09-05 ~ 2026-09-01, **3년**)
fx-daily.json   USDKRW · JPYKRW                680일 (2023-11-20 ~, **2.7년**)
```

## 왜 이걸 재나
```
39차: 한국 주식 상승의 **대부분이 밤사이(갭)에 일어난다**
      갭 +0.1356%/일 → 연 **+33.2%**  ·  장중 −0.0537%/일 → 연 −13.2%
⇒ 그 갭을 **미국장이 설명하는가**가 자연스러운 다음 질문이다
```
⚠️ 시차: 미국장은 한국 시간 밤 11:30~새벽 6:00에 열린다.
   **미국 D−1 종가가 한국 D 아침에 반영된다** — 그 순서로 맞춘다.

## 재는 것
```
① 미국 지수 등락률 → **다음날 한국 갭** 상관 (지수 4종)
② 환율 변동 → 한국 갭
③ 미국 등락률 구간별 한국 갭 평균 (−2%↓ / −2~0 / 0~2 / +2%↑)
④ **우리 신호가 미국장 상태에 따라 다른가**  ← 이게 핵심이다
   「미국이 빠져서 한국 소형주가 같이 갭 하락」 vs 「미국은 멀쩡한데 그 종목만 갭 하락」
   → 후자가 개별 종목 이슈라 반등이 다를 수 있다
```
⚠️⚠️ **3년치뿐이라 연도별이 3~4개다. 전부 예비 결과다.**
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

_비용 = 0.26
_보유 = 20


def _상관(A, B):
    n = min(len(A), len(B))
    if n < 30:
        return 0.0, 0.0
    A, B = A[:n], B[:n]
    ma, mb = st.mean(A), st.mean(B)
    sa = st.pstdev(A) or 1e-9
    sb = st.pstdev(B) or 1e-9
    r = sum((A[i] - ma) * (B[i] - mb) for i in range(n)) / n / (sa * sb)
    t = r * math.sqrt(max(1, n - 2)) / math.sqrt(max(1e-9, 1 - r * r))
    return r, t


def main():
    print("  자료 읽는 중...", flush=True)
    미 = json.load(io.open(os.path.join(O._DATA, "us-index.json"), encoding="utf-8-sig"))
    환 = json.load(io.open(os.path.join(O._DATA, "fx-daily.json"), encoding="utf-8-sig"))
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 미국지수 {list(미)} · 환율 {list(환)}", flush=True)

    # 시가가 필요해 원본을 따로 읽는다 (수정 배율 적용)
    갭표 = {}      # 날 -> {코드: 갭%}
    코스피갭 = {}
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
    # 시장 전체 갭 (동일가중 중앙값)
    for d8, h in 갭표.items():
        if len(h) >= 100:
            코스피갭[d8] = st.median(list(h.values()))

    def 미등락(이름, d8):
        """한국 d8 아침에 반영되는 **미국 D−1 등락률**."""
        a = 미.get(이름) or {}
        후 = [x for x in a if x < d8]
        if not 후:
            return None
        키 = max(후)
        v = a[키]
        try:
            return float(v.get("등락률"))
        except (TypeError, ValueError, AttributeError):
            return None

    def 환변동(이름, d8):
        a = 환.get(이름) or {}
        키들 = sorted(x for x in a if x < d8)
        if len(키들) < 2:
            return None
        try:
            x1 = float((a[키들[-1]] or {}).get("종가") or a[키들[-1]])
            x0 = float((a[키들[-2]] or {}).get("종가") or a[키들[-2]])
            return (x1 / x0 - 1) * 100 if x0 else None
        except (TypeError, ValueError, AttributeError):
            return None

    공통 = [d for d in sorted(코스피갭) if 미등락("S&P500", d) is not None]
    print(f"  미국 지수와 겹치는 날 {len(공통):,}일 "
          f"({공통[0] if 공통 else '-'} ~ {공통[-1] if 공통 else '-'})", flush=True)

    print(f"\n  ══ ① 밤사이 미국장 → **다음날 한국 갭** (시장 전체 중앙값) ══")
    print("     ⚠️ 미국 D−1 종가가 한국 D 아침에 반영된다")
    print(f"    {'지수':<14}{'상관':>9}{'t값':>8}{'표본':>8}")
    한 = [코스피갭[d] for d in 공통]
    for 이름 in ("S&P500", "나스닥", "다우", "필라반도체"):
        미값 = [미등락(이름, d) for d in 공통]
        쌍 = [(a, b) for a, b in zip(미값, 한) if a is not None]
        if len(쌍) < 100:
            continue
        r, t = _상관([x[0] for x in 쌍], [x[1] for x in 쌍])
        판 = "⭐ 강하다" if abs(r) >= 0.5 else ("○ 있다" if abs(r) >= 0.3 else "약하다")
        print(f"    {이름:<14}{r:>+9.3f}{t:>8.1f}{len(쌍):>8}  {판}")
    for 이름 in ("USDKRW", "JPYKRW"):
        환값 = [환변동(이름, d) for d in 공통]
        쌍 = [(a, b) for a, b in zip(환값, 한) if a is not None]
        if len(쌍) < 100:
            continue
        r, t = _상관([x[0] for x in 쌍], [x[1] for x in 쌍])
        print(f"    {이름:<14}{r:>+9.3f}{t:>8.1f}{len(쌍):>8}")

    print(f"\n  ══ ② 미국 등락률 구간별 → 한국 갭 평균 ══")
    칸 = [("−2%↓", -99, -2), ("−2~−0.5%", -2, -0.5), ("−0.5~+0.5%", -0.5, 0.5),
          ("+0.5~+2%", 0.5, 2), ("+2%↑", 2, 99)]
    print(f"    {'미국 S&P500':<14}" + "".join(f"{'한국갭':>12}" for _ in (1,))
          + f"{'표본':>8}   나스닥 기준")
    for 라, lo, hi in 칸:
        a = [코스피갭[d] for d in 공통
             if 미등락("S&P500", d) is not None and lo <= 미등락("S&P500", d) < hi]
        b = [코스피갭[d] for d in 공통
             if 미등락("나스닥", d) is not None and lo <= 미등락("나스닥", d) < hi]
        if len(a) < 20:
            continue
        print(f"    {라:<14}{st.mean(a):>+11.3f}%{len(a):>8}   "
              f"{(st.mean(b) if len(b) >= 20 else 0):>+8.3f}% ({len(b)})")

    # ── ④ 우리 신호가 미국장 상태에 따라 다른가 ──
    print(f"\n  ══ ④⭐ **우리 신호가 미국장에 따라 다른가** ══")
    print("     신호: 볼하단 + 갭−2%↓ + 20일−10%↓ · 소형 (D+20 · 다음날 시가 매수)")
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
        미v = 미등락("S&P500", 다음)
        if 미v is None:
            continue
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
            g = (갭표.get(다음) or {}).get(code)
            if g is None or g > -2:
                continue
            나 = 주가[다음].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝:
                continue
            # ⚠️ 시가는 갭으로 되돌린다 (수정 배율 일관성)
            매수 = c1 * (1 + g / 100)
            r = (끝[0] / 매수 - 1) * 100 - _비용
            시장갭 = 코스피갭.get(다음, 0)
            사건.append((다음[:4], 미v, 시장갭, g, r))
    print(f"    표본 {len(사건):,}건 ({공통[0][:4] if 공통 else '-'}~2026, **3년뿐 — 예비**)")
    if 사건:
        전 = [x[4] for x in 사건]
        print(f"    전체 평균 {st.mean(전):+.2f}% · 승률 "
              f"{sum(1 for x in 전 if x > 0)/len(전)*100:.1f}%")
        print(f"\n    {'미국 전날':<16}{'평균':>9}{'승률':>8}{'표본':>8}")
        for 라, lo, hi in 칸:
            a = [x[4] for x in 사건 if lo <= x[1] < hi]
            if len(a) < 100:
                continue
            승 = sum(1 for x in a if x > 0) / len(a) * 100
            print(f"    {라:<16}{st.mean(a):>+8.2f}%{승:>7.1f}%{len(a):>8}")
        print(f"\n    ── **미국은 멀쩡한데 그 종목만 빠진 경우** ──")
        for 라, 조건 in (("미국 +0.5%↑ 인데 종목은 갭−2%↓", lambda x: x[1] >= 0.5),
                         ("미국 −0.5~+0.5% (보합)", lambda x: -0.5 <= x[1] < 0.5),
                         ("미국 −0.5%↓ (같이 빠짐)", lambda x: x[1] < -0.5)):
            a = [x[4] for x in 사건 if 조건(x)]
            if len(a) < 100:
                continue
            승 = sum(1 for x in a if x > 0) / len(a) * 100
            print(f"    {라:<32}{st.mean(a):>+8.2f}%  승률 {승:>5.1f}%  표본 {len(a):>6,}")
        print(f"\n    ── **시장 전체 갭 대비 그 종목의 갭** ──")
        for 라, 조건 in (("시장보다 3%p 넘게 더 빠짐", lambda x: x[3] - x[2] <= -3),
                         ("시장보다 1~3%p 더 빠짐", lambda x: -3 < x[3] - x[2] <= -1),
                         ("시장과 비슷하게 빠짐", lambda x: x[3] - x[2] > -1)):
            a = [x[4] for x in 사건 if 조건(x)]
            if len(a) < 100:
                continue
            승 = sum(1 for x in a if x > 0) / len(a) * 100
            print(f"    {라:<32}{st.mean(a):>+8.2f}%  승률 {승:>5.1f}%  표본 {len(a):>6,}")

    print("\n  읽는 법")
    print("    - ①의 상관이 0.5를 넘으면 **미국장이 한국 갭을 크게 좌우한다**")
    print("    - ④에서 「미국은 멀쩡한데 그 종목만 빠진 경우」가 좋으면")
    print("      **개별 종목 이슈로 빠진 것이 시장 따라 빠진 것보다 낫다**는 뜻이다")
    print("    - ⚠️⚠️ 미국·환율 자료가 **3년치뿐이다. 전부 예비 결과다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
