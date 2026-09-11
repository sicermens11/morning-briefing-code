#!/usr/bin/env python3
r"""
intraday_lab.py — **종목마다 아침에 오르나 오후에 오르나** (2026-09-02 · 39차)

⚠️⚠️ **사용자 아이디어.**
   *"종목마다 일별 시가 종가 패턴 분석하면 종목의 특징 같은 것도 알 수 있을 것 같은데?"*

## 일봉만으로도 하루를 둘로 쪼갤 수 있다
```
갭 수익률    시가 / **전일종가** − 1    ← 밤사이(장 마감~다음날 개장) 움직임
장중 수익률   종가 / **시가** − 1        ← 장 열린 뒤 움직임
⇒ 둘을 더하면 일간 수익률이 된다. **어디서 벌고 어디서 잃는지**가 갈린다
```

## 종목마다 성향이 다르면 매매 시점을 종목별로 정할 수 있다
```
갭 +  장중 −    아침에 오르고 오후에 빠진다  → **종가에 사서 다음날 아침에 판다**
갭 −  장중 +    아침에 빠지고 오후에 오른다  → **아침에 사서 종가에 판다**
```

## ⚠️⚠️ 하지만 **성향이 이어지는지**가 먼저다
```
과거 1년 성향이 다음 1년에도 유지되나? 안 되면 **그냥 우연이고 쓸모없다.**
→ ②에서 **전반기 성향 vs 후반기 성향의 상관**을 잰다. 이게 이 시험의 핵심이다
```

## 재는 것
```
① 시장 전체    해마다 갭 수익률 합계 vs 장중 수익률 합계 — **한국 시장은 어디서 오르나**
② **성향의 지속성**  종목별 전반기(2010~2017) 성향 → 후반기(2018~2026) 성향 상관
                  ⚠️ 상관이 낮으면 종목별 성향은 못 쓴다
③ 크기별       소형/중형/대형이 다른가
④ 신호가 뜬 날   신고가·과매수 난 날은 일중 패턴이 다른가
⑤ 요일         요일마다 다른가 (월요일 갭, 금요일 장중 등)
```
⚠️ 수정 배율을 시가에도 똑같이 먹인다. 비용은 안 뺀다(패턴을 보는 것이지 매매가 아니다).
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
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


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


def _주가():
    """{날: {코드: (수정종가, 수정시가, 수정고가, 수정저가, 시총, 대금)}}"""
    원 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                if 종 <= 0:
                    continue
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                저 = float(v.get("저가") or 0) or 종
            except (TypeError, ValueError, KeyError):
                continue
            등 = v.get("등락률")
            try:
                등 = float(등) if 등 not in (None, "") else None
            except (TypeError, ValueError):
                등 = None
            if 등 is not None and abs(등) > 31.0:
                등 = None
            try:
                시총 = float(v.get("시총") or 0)
                대금 = float(v.get("거래대금") or 0)
            except (TypeError, ValueError):
                시총 = 대금 = 0.0
            하루[c] = (종, 시, 고, 저, 등, 시총, 대금)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 고, 저, 등, 시총, 대금) in 원[d].items():
            p, s = 앞원.get(c), 앞수.get(c)
            if p is None or s is None:
                수 = 종
            elif 등 is not None:
                수 = s * (1 + 등 / 100.0)
            else:
                r = 종 / p - 1 if p > 0 else 0.0
                수 = s * (1 + (0.0 if abs(r) > 0.32 else r))
            if 수 <= 0:
                수 = s if s and s > 0 else 종
            배 = 수 / 종 if 종 else 1.0
            앞원[c], 앞수[c] = 종, 수
            하루[c] = (수, 시 * 배, 고 * 배, 저 * 배, 시총, 대금)
        out[d] = 하루
    return out


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    기본 = O._기본()
    print(f"  거래일 {len(날):,}", flush=True)

    # 종목별 갭/장중 수익률 모으기
    갭모음 = {}     # 코드 -> {"전": [갭], "후": [갭]}
    장모음 = {}
    해갭, 해장 = {}, {}
    크갭, 크장 = {}, {}
    요갭, 요장 = {}, {}
    import datetime as dt
    앞종 = {}
    for d in 날:
        해 = d[:4]
        기간 = "전" if d < _경계 else "후"
        try:
            요일 = "월화수목금토일"[dt.date(int(d[:4]), int(d[4:6]), int(d[6:8])).weekday()]
        except ValueError:
            요일 = "?"
        for c, v in 주가[d].items():
            종, 시, 고, 저, 시총, 대금 = v
            p = 앞종.get(c)
            앞종[c] = 종
            if p is None or p <= 0 or 시 <= 0:
                continue
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(c) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            갭 = (시 / p - 1) * 100
            장 = (종 / 시 - 1) * 100
            if abs(갭) > 32 or abs(장) > 32:
                continue
            갭모음.setdefault(c, {"전": [], "후": []})[기간].append(갭)
            장모음.setdefault(c, {"전": [], "후": []})[기간].append(장)
            해갭.setdefault(해, []).append(갭)
            해장.setdefault(해, []).append(장)
            g = _크기(시총)
            크갭.setdefault(g, []).append(갭)
            크장.setdefault(g, []).append(장)
            요갭.setdefault(요일, []).append(갭)
            요장.setdefault(요일, []).append(장)

    print(f"  종목 {len(갭모음):,}개", flush=True)

    print(f"\n  ══ ① 한국 시장은 **어디서 오르나** (연도별 평균, 하루당 %) ══")
    print("     ⚠️ 갭 = 밤사이(전일종가→시가) · 장중 = 장 열린 뒤(시가→종가)")
    print(f"    {'해':<7}{'갭':>10}{'장중':>10}{'합계':>10}{'관측치':>12}")
    for 해 in sorted(해갭):
        a, b = 해갭[해], 해장[해]
        if len(a) < 1000:
            continue
        print(f"    {해:<7}{st.mean(a):>+9.4f}%{st.mean(b):>+9.4f}%"
              f"{st.mean(a)+st.mean(b):>+9.4f}%{len(a):>12,}")
    전갭 = [x for a in 해갭.values() for x in a]
    전장 = [x for a in 해장.values() for x in a]
    print(f"    {'전체':<7}{st.mean(전갭):>+9.4f}%{st.mean(전장):>+9.4f}%"
          f"{st.mean(전갭)+st.mean(전장):>+9.4f}%{len(전갭):>12,}")
    print(f"    ⇒ 연환산: 갭 {st.mean(전갭)*245:+.1f}% · 장중 {st.mean(전장)*245:+.1f}%")

    print(f"\n  ══ ②⭐ **성향이 이어지나** — 이게 핵심이다 ══")
    print("     전반기(2010~2017) 종목별 평균 → 후반기(2018~2026) 종목별 평균의 상관")
    for 이름, 모음 in (("갭 성향", 갭모음), ("장중 성향", 장모음)):
        A, B = [], []
        for c, v in 모음.items():
            if len(v["전"]) >= 500 and len(v["후"]) >= 500:
                A.append(st.mean(v["전"]))
                B.append(st.mean(v["후"]))
        if len(A) < 50:
            print(f"    {이름}: 표본 부족")
            continue
        r, t = _상관(A, B)
        판 = ("⭐ 이어진다 — 종목별로 매매 시점을 정할 수 있다" if r >= 0.3 else
              "○ 약하게 이어진다" if r >= 0.15 else
              "❌ **안 이어진다 — 종목별 성향은 못 쓴다**")
        print(f"    {이름:<10} 상관 {r:>+.3f} (t={t:.1f}) · 종목 {len(A):,}개   {판}")

    print(f"\n  ══ ③ 크기별 ══")
    print(f"    {'크기':<8}{'갭':>10}{'장중':>10}{'합계':>10}{'관측치':>12}")
    for g, _, _ in 크기표:
        a, b = 크갭.get(g) or [], 크장.get(g) or []
        if len(a) < 1000:
            continue
        print(f"    {g:<8}{st.mean(a):>+9.4f}%{st.mean(b):>+9.4f}%"
              f"{st.mean(a)+st.mean(b):>+9.4f}%{len(a):>12,}")

    print(f"\n  ══ ⑤ 요일별 ══")
    print(f"    {'요일':<8}{'갭':>10}{'장중':>10}{'합계':>10}{'관측치':>12}")
    for 요 in "월화수목금":
        a, b = 요갭.get(요) or [], 요장.get(요) or []
        if len(a) < 1000:
            continue
        print(f"    {요:<8}{st.mean(a):>+9.4f}%{st.mean(b):>+9.4f}%"
              f"{st.mean(a)+st.mean(b):>+9.4f}%{len(a):>12,}")

    print(f"\n  ══ ④ 성향이 가장 뚜렷한 종목 (후반기 기준, 관측 500일↑) ══")
    후 = []
    for c, v in 갭모음.items():
        if len(v["후"]) >= 500 and c in 장모음 and len(장모음[c]["후"]) >= 500:
            후.append((st.mean(v["후"]), st.mean(장모음[c]["후"]), c, len(v["후"])))
    이름표 = {c: (기본.get(c) or {}).get("이름") or c for _, _, c, _ in 후}
    print("    ── 갭에서 벌고 장중에 잃는 종목 (아침에 오르고 오후에 빠진다) ──")
    for 갭, 장, c, n in sorted(후, key=lambda x: -(x[0] - x[1]))[:8]:
        print(f"      {이름표[c][:14]:<16}({c})  갭 {갭:>+7.4f}%  장중 {장:>+7.4f}%  {n}일")
    print("    ── 장중에 벌고 갭에서 잃는 종목 (아침에 빠지고 오후에 오른다) ──")
    for 갭, 장, c, n in sorted(후, key=lambda x: (x[0] - x[1]))[:8]:
        print(f"      {이름표[c][:14]:<16}({c})  갭 {갭:>+7.4f}%  장중 {장:>+7.4f}%  {n}일")

    print("\n  읽는 법")
    print("    - ①에서 갭과 장중의 부호가 다르면 **어디서 사고 어디서 팔지**가 갈린다")
    print("    - ②가 **가장 중요하다.** 상관이 0.3을 넘어야 종목별 성향을 실전에 쓸 수 있다")
    print("      ⚠️ 낮으면 ④의 종목 목록은 **과거를 설명할 뿐 미래에 못 쓴다**")
    print("    - ⑤ 요일 효과는 표본이 커서 작은 차이도 t가 크게 나온다. 크기를 보고 판단한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
