#!/usr/bin/env python3
r"""
nv_lab.py — **89b차. 89차에서 살아남은 하나를 끝까지 캔다** (2026-09-03)

## 89차에서 살아남은 것
```
엔비디아 −2%↓ → 다음날 삼성·하이닉스 시가 매수
   5일 **+0.78%** · 승률 **55.9%** · 연도별 **9/11해**
   (기준선: 5일 +0.19% · 승률 47.3%)
```
나머지는 다 떨어졌다. 특히 **「미국이 오르면 따라 산다」는 완전히 실패**했다
(반도체지수 +3%↑ 다음날은 5일 **−0.72%**, 기준선보다 나쁘다).

## ⚠️ 그런데 이게 진짜인지 세 가지를 확인해야 한다
```
① **다른 이름일 뿐인가**
   「엔비디아가 빠진 날」 = 「한국이 갭하락한 날」일 수 있다.
   그렇다면 엔비디아는 필요 없고 **갭만 보면 된다**.
   ⇒ 갭을 통제하고 엔비디아가 **추가로** 설명하는 게 있는지 본다

② **돈이 되는가** (88b에서 똑같이 좋아 보이던 게 자본 시뮬에서 전멸했다)
   ⇒ 실제로 사고 파는 자본 시뮬

③ **몇 해가 다 한 건가**
   ⇒ 2025·26 제외 · 연도별 표
```
⚠️ 그리고 **무작위 신호**와 견준다 (같은 날 수를 아무렇게나 골라 1,000번)
"""
import datetime as dt
import glob
import io
import json
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_YH = os.path.join(O._DATA, "yahoo")
대상 = (("005930", "삼성전자"), ("000660", "SK하이닉스"))
후보 = (("NVDA", "엔비디아"), ("MU", "마이크론"), ("SOXX", "반도체지수"),
        ("TSM", "TSMC"), ("AMAT", "어플라이드"))


def main():
    미등 = {}
    for 심, 이름 in 후보:
        p = os.path.join(_YH, 심 + ".json")
        if not os.path.exists(p):
            continue
        종 = json.load(io.open(p, encoding="utf-8-sig")).get("종가") or {}
        k = sorted(종)
        e = {}
        for j in range(1, len(k)):
            pv = 종[k[j - 1]]
            if pv:
                e[k[j]] = (종[k[j]] / pv - 1) * 100
        미등[심] = (이름, e)

    주가 = O.수정주가(())
    날 = sorted(주가)
    날인 = {d: i for i, d in enumerate(날)}
    비 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        for c, v in d["종목"].items():
            if c not in ("005930", "000660"):
                continue
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = 시 / 종

    쓸값 = {}
    for 심, (이름, e) in 미등.items():
        ek = sorted(e)
        t = {}
        for d in 날:
            앞 = [x for x in ek if x < d]
            if not 앞:
                continue
            전 = max(앞)
            try:
                if (dt.datetime.strptime(d, "%Y%m%d")
                        - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                    continue
            except Exception:
                pass
            t[d] = e[전]
        쓸값[심] = t

    # 각 대상의 (날 -> 수정종가) · 갭
    선 = {}
    for c, n in 대상:
        s, 갭 = {}, {}
        앞 = None
        for d in 날:
            v = 주가[d].get(c)
            if not v:
                continue
            s[d] = v[0]
            b = (비.get(d) or {}).get(c)
            if 앞 and b:
                갭[d] = (v[0] * b / 앞 - 1) * 100    # 수정 기준 갭
            앞 = v[0]
        선[c] = (s, 갭)

    쓸날 = [d for d in 날 if d >= _시작]
    년수 = len(쓸날) / 245
    print(f"  {len(쓸날):,}일 · {년수:.1f}년\n", flush=True)

    def 사기(날들, 보유일=5):
        """그 날들에 삼성·하이닉스를 시가 매수 → 보유일 뒤 종가"""
        결, 해 = [], {}
        for d in 날들:
            i = 날인[d]
            j = i + 보유일 - 1
            if j >= len(날):
                continue
            for c, n in 대상:
                s, _ = 선[c]
                b = (비.get(d) or {}).get(c)
                v0, v1 = s.get(d), s.get(날[j])
                if not b or not v0 or not v1:
                    continue
                r = (v1 / (v0 * b) - 1) * 100 - _비용
                결.append(r)
                해.setdefault(d[:4], []).append(r)
        return 결, 해

    def 보고(날들, 라, 폭=30):
        결, 해 = 사기(날들)
        if len(결) < 40:
            print(f"    {라:<{폭}}표본 부족 ({len(결)}건)")
            return None
        전 = 플 = 0
        for y, a in 해.items():
            if len(a) < 10:
                continue
            전 += 1
            플 += 1 if st.mean(a) > 0 else 0
        승 = sum(1 for r in 결 if r > 0) / len(결) * 100
        별 = "⭐" if (전 >= 9 and 플 / 전 >= 2 / 3 and st.mean(결) > 0.4) else "  "
        print(f"    {라:<{폭}}{len(날들):>6}일{len(결):>7}건"
              f"{st.mean(결):>+9.2f}%{st.median(결):>+9.2f}%{승:>8.1f}%"
              f"{f'{플}/{전}':>8}{별}")
        return st.mean(결)

    머 = (f"    {'조건':<30}{'날':>8}{'표본':>7}{'5일평균':>9}"
          f"{'중앙':>9}{'승률':>8}{'연도별':>8}")

    # ══ 기준선 ══
    print("  ══ 기준선 ══")
    print(머)
    기준 = 보고(쓸날, "아무 날이나")

    # ══ ① 갭을 통제하면 ══
    print(f"\n  ══ ① ⚠️⚠️ **엔비디아는 「갭하락」의 다른 이름인가** ══")
    print("     「엔비디아가 빠진 날」과 「한국이 갭하락한 날」이 같은 것이라면")
    print("     엔비디아는 **필요 없다**. 갭만 보면 된다")
    t = 쓸값.get("NVDA") or {}
    엔하 = [d for d in 쓸날 if t.get(d) is not None and t[d] <= -2]
    # 두 종목의 평균 갭
    평갭 = {}
    for d in 쓸날:
        g = [선[c][1].get(d) for c, n in 대상 if 선[c][1].get(d) is not None]
        if g:
            평갭[d] = st.mean(g)
    갭하 = [d for d in 쓸날 if 평갭.get(d) is not None and 평갭[d] <= -1.0]
    겹 = set(엔하) & set(갭하)
    print(f"\n     엔비디아 −2%↓ 난 날      {len(엔하):>5}일")
    print(f"     한국이 −1% 갭하락한 날    {len(갭하):>5}일")
    print(f"     **둘 다**              {len(겹):>5}일  "
          f"(엔비디아 날의 {len(겹)/max(1,len(엔하))*100:.0f}%)")
    if 엔하:
        print(f"     엔비디아 −2%↓ 날의 평균 갭  {st.mean([평갭[d] for d in 엔하 if d in 평갭]):+.2f}%")
        print(f"     그 외 날의 평균 갭         {st.mean([평갭[d] for d in 쓸날 if d in 평갭 and d not in set(엔하)]):+.2f}%")
    print(f"\n{머}")
    보고(엔하, "엔비디아 −2%↓ (원래 결과)")
    보고(갭하, "한국 −1% 갭하락만 봐도")
    보고(sorted(겹), "둘 다")
    보고([d for d in 엔하 if d not in set(갭하)],
         "⭐ 엔비디아만 (갭은 안 빠짐)")
    보고([d for d in 갭하 if d not in set(엔하)],
         "⭐ 갭만 (엔비디아는 안 빠짐)")

    # ══ ② 다른 미국 종목도 ══
    print(f"\n  ══ ② **다른 미국 반도체도 같은가** ══")
    print(머)
    for 심, (이름, _) in 미등.items():
        tt = 쓸값[심]
        for 문 in (-2.0, -3.0):
            보고([d for d in 쓸날 if tt.get(d) is not None and tt[d] <= 문],
                 f"{이름} {문}%↓")

    # ══ ③ 무작위 ══
    print(f"\n  ══ ③ **무작위 신호와 견준다** (같은 날 수로 1,000번) ══")
    random.seed(20260903)
    실제 = st.mean(사기(엔하)[0])
    이김 = 0
    분포 = []
    for _ in range(1000):
        표 = random.sample(쓸날, len(엔하))
        m = 사기(표)[0]
        if m:
            v = st.mean(m)
            분포.append(v)
            if v >= 실제:
                이김 += 1
    분포.sort()
    p = 이김 / max(1, len(분포))
    print(f"     실제(엔비디아 −2%↓)   {실제:+.3f}%")
    print(f"     무작위 평균          {st.mean(분포):+.3f}%")
    print(f"     무작위 상위 5%       {분포[int(len(분포)*0.95)]:+.3f}%")
    print(f"     무작위가 이긴 횟수     {이김}/1000  →  **p = {p:.3f}**")
    print(f"     {'⚠️ p가 0.05를 넘는다. 우연과 구별이 안 된다' if p > 0.05 else '⭐ p < 0.05'}")

    # ══ ④ 연도별 · 2025·26 제외 ══
    print(f"\n  ══ ④ **연도별로 펴 본다** ══")
    결, 해 = 사기(엔하)
    print(f"    {'해':<8}{'표본':>8}{'평균':>10}{'승률':>9}")
    for y in sorted(해):
        a = 해[y]
        print(f"    {y:<8}{len(a):>7}건{st.mean(a):>+9.2f}%"
              f"{sum(1 for r in a if r>0)/len(a)*100:>8.1f}%")
    빼 = [r for y in 해 if y < "2025" for r in 해[y]]
    print(f"\n    ⚠️ 2025·26 빼면  {len(빼)}건  {st.mean(빼):+.2f}%  "
          f"승률 {sum(1 for r in 빼 if r>0)/len(빼)*100:.1f}%")
    기결, 기해 = 사기(쓸날)
    기빼 = [r for y in 기해 if y < "2025" for r in 기해[y]]
    print(f"       같은 판 기준선  {len(기빼)}건  {st.mean(기빼):+.2f}%  "
          f"승률 {sum(1 for r in 기빼 if r>0)/len(기빼)*100:.1f}%")

    # ══ ⑤ 자본 시뮬 ══
    print(f"\n  ══ ⑤ ⭐⭐ **자본 시뮬** — 진짜 돈이 느나 ══")
    print("     500만원 · 신호 나면 반씩 두 종목 · 5일 뒤 판다 · 노는 돈 연 2.5%")

    def 시뮬(날들, 라, 끝년=None, 보유일=5):
        골 = set(날들)
        현금, 보유, 곡 = 5_000_000.0, [], []
        n = 0
        for i, d in enumerate(날):
            if d < _시작:
                continue
            if 끝년 and d[:4] > 끝년:
                break
            남 = []
            for p in 보유:
                if p["끝"] <= i:
                    현금 += p["금액"] * (1 + p["r"] / 100)
                else:
                    남.append(p)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(p["금액"] for p in 보유)
            if d in 골 and not 보유:
                j = i + 보유일 - 1
                if j < len(날):
                    for c, nm in 대상:
                        s, _ = 선[c]
                        b = (비.get(d) or {}).get(c)
                        v0, v1 = s.get(d), s.get(날[j])
                        if not b or not v0 or not v1:
                            continue
                        금 = min(현금 * 0.5, 평 * 0.5)
                        if 금 < 1000:
                            continue
                        현금 -= 금
                        보유.append({"금액": 금, "끝": j,
                                     "r": (v1 / (v0 * b) - 1) * 100 - _비용})
                        n += 1
            곡.append(평)
        끝 = 현금 + sum(p["금액"] for p in 보유)
        yr = len(곡) / 245
        cagr = ((끝 / 5_000_000) ** (1 / max(yr, 0.1)) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        print(f"    {라:<30}{끝:>14,.0f}원{cagr:>+9.2f}%{낙:>8.1f}%{n:>7}건")
        return cagr

    print(f"    {'전략':<30}{'끝 자산':>15}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")
    시뮬(엔하, "엔비디아 −2%↓ 때만")
    시뮬(갭하, "한국 −1% 갭하락 때만")
    시뮬(쓸날, "⚠️ 늘 들고 있기 (사서 묻기)")
    print()
    시뮬(엔하, "엔비디아 −2%↓ · 2025·26 제외", 끝년="2024")
    시뮬(쓸날, "늘 들고 있기 · 2025·26 제외", 끝년="2024")

    print("\n  읽는 법")
    print("    - ①에서 **「엔비디아만」**이 기준선을 못 이기면 갭의 다른 이름이다")
    print("    - ③의 p가 0.05를 넘으면 우연과 구별이 안 된다")
    print("    - ⑤에서 **늘 들고 있기**를 못 이기면 신호를 볼 이유가 없다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
