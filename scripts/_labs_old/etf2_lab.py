#!/usr/bin/env python3
r"""
etf2_lab.py — **ETF도 브리핑 후보가 될 수 있나** (2026-09-03 · 69차)

⚠️⚠️ **사용자 지시.** *"브리핑 추천 종목에 개별종목도 ETF도 후보에 오를 수 있어!"*

## 자료 (오늘 새로 받았다)
```
국내 ETF  **4,103일 (2010-01-04 ~ 2026-09-02) · 1,167종목** · KRX etp/etf_bydd_trd
          시가·종가·NAV·거래대금·시가총액·추종지수명
```

⚠️⚠️ **ETF는 재무가 없다.** 우리 한국 신호의 핵심이 「잉여금↑·부채↓·흑자」였는데
   그게 없다. **가격 조건만으로 승부해야 한다.**
   ⇒ 60차에서 확인했다: 기술 조건만으로는 **+1.36% · 승률 50.5%**(동전던지기)였다.
      ETF에서도 그럴지, 아니면 다를지가 이 시험의 질문이다.

## 종류를 갈라 본다 — 성격이 전혀 다르다
```
국내지수   KODEX 200 · TIGER 200 …        레버리지  2배 · 인버스 · 곱버스
해외       미국S&P500 · 미국나스닥100 …     채권·금리  국고채 · CD금리 · 미국채
원자재     금 · 원유                       섹터·테마  반도체 · 2차전지 …
```
⚠️ **레버리지·인버스는 장기 보유에 부적합**하다(변동성 손실). 다만 D+20 단기엔 쓸 수 있다.
⚠️ **유동성이 결정적이다.** 1,167종목 중 대부분은 거래가 거의 없다 — 하한을 건다.

## 재는 것
```
A 그냥 들고 있기 (기준선)  — 종류별로 얼마?
B **빠졌을 때 산다**       갭 하락 + 볼린저 하단 + 20일 하락 → 다음날 시가 · D+20
C **올랐을 때 산다**       (한국 개별주에선 -1.54%로 실패했다)
D 종류별                  어느 종류에서 신호가 듣나
E ⭐ **한국 개별주 신호와 겹치나** — 안 겹치면 자금을 더 쓸 수 있다
```
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · 비용 0.26%
   (ETF는 **증권거래세가 면제**라 실제론 더 싸다 — 보수적으로 잡았다)
   · **날짜 단위** · 연도별 3분의 2.
"""
import glob
import io
import json
import os
import re
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_보유 = 20
_ETF = os.path.join(O._DATA, "etf-krx")
_최소대금 = 3e8       # ⚠️ 3억. 이보다 적으면 실제로 못 산다


def 종류(이름):
    n = 이름 or ""
    if re.search(r"레버리지|2X|인버스|곱버스|선물\s*2", n):
        return "레버리지·인버스"
    if re.search(r"채권|국고채|CD금리|금리|통안|회사채|국채|단기자금|머니마켓|MMF", n):
        return "채권·금리"
    if re.search(r"금\b|골드|은\b|실버|원유|WTI|천연가스|구리|농산물|원자재", n):
        return "원자재"
    if re.search(r"미국|나스닥|S&P|다우|중국|일본|인도|베트남|글로벌|선진국|신흥|유로|"
                 r"차이나|홍콩|대만|아시아|유럽|브라질", n):
        return "해외"
    if re.search(r"200|코스닥150|코스피|KRX\s*300|배당|고배당|가치|성장|중소형|대형", n):
        return "국내지수·스타일"
    return "국내섹터·테마"


def 재기(날별, 이름, 년수, 폭=32):
    if len(날별) < 8:
        print(f"    {이름:<{폭}}신호일 {len(날별)}일 — 부족")
        return None
    수 = [st.mean(v) for v in 날별.values()]
    승 = sum(1 for x in 수 if x > 0) / len(수) * 100
    해 = {}
    for d, v in 날별.items():
        해.setdefault(d[:4], []).append(st.mean(v))
    전 = 플 = 0
    for y, arr in 해.items():
        if len(arr) < 3:
            continue
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
    a = sorted(수)
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 8
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/max(0.1,년수):>7.1f}일{f'{플}/{전}':>8}{len(날별):>7}일{별}")
    return set(날별)


def main():
    print("  ETF 자료 읽는 중...", flush=True)
    파일 = sorted(glob.glob(os.path.join(_ETF, "*.json")))
    if len(파일) < 1000:
        print(f"  ⚠️ etf-krx가 {len(파일)}일뿐이다. collect_krx_etf.py를 먼저 돌려야 한다")
        return 1
    시세, 이름표 = {}, {}
    날짜 = []
    for f in 파일:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = d["기준일"]
        날짜.append(d8)
        for c, v in (d.get("종목") or {}).items():
            종, 시 = v.get("종가"), v.get("시가")
            if not 종 or 종 <= 0:
                continue
            시세.setdefault(c, {})[d8] = (시 if (시 and 시 > 0) else 종, 종,
                                          v.get("거래대금") or 0)
            이름표[c] = v.get("이름") or 이름표.get(c, "")
    날짜.sort()
    년수 = len(날짜) / 245
    print(f"  {len(날짜):,}일 ({날짜[0]} ~ {날짜[-1]}) · 종목 {len(시세):,}개 "
          f"· {년수:.1f}년", flush=True)

    # ── 종류별 현황 ──
    분류 = {}
    for c in 시세:
        분류.setdefault(종류(이름표.get(c, "")), []).append(c)
    print(f"\n  ══ 종류별 (거래대금 3억 이상인 날이 250일 넘는 것만 쓴다) ══")
    쓸것 = {}
    for k in sorted(분류, key=lambda x: -len(분류[x])):
        살 = []
        for c in 분류[k]:
            n = sum(1 for d in 시세[c] if 시세[c][d][2] >= _최소대금)
            if n >= 250:
                살.append(c)
        쓸것[k] = 살
        print(f"    {k:<18}전체 {len(분류[k]):>5}개 · **쓸 수 있는 것 {len(살):>4}개**")

    # ── 후보 ──
    def 후보(code):
        k = sorted(시세[code])
        if len(k) < 300:
            return []
        종 = [시세[code][d][1] for d in k]
        out = []
        for i in range(60, len(k) - 1 - _보유):
            if 시세[code][k[i]][2] < _최소대금:
                continue
            c1 = 종[i]
            s20 = st.mean(종[i - 19:i + 1])
            sd = st.pstdev(종[i - 19:i + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 종[i - 20] <= 0:
                continue
            r20 = (c1 / 종[i - 20] - 1) * 100
            시 = 시세[code][k[i + 1]][0]
            if 시 <= 0:
                continue
            갭 = (시 / c1 - 1) * 100
            if abs(갭) > 20:
                continue
            out.append((k[i + 1], (종[i + 1 + _보유] / 시 - 1) * 100 - _비용,
                        갭, 볼, r20))
        return out

    전체 = {}
    for k, codes in 쓸것.items():
        for c in codes:
            a = 후보(c)
            if a:
                전체[c] = a
    print(f"\n  후보를 모은 ETF {len(전체):,}개 · "
          f"총 {sum(len(v) for v in 전체.values()):,}건", flush=True)

    def 모으기(codes, 갭문, 볼문, r문, 위=False):
        t = {}
        for c in codes:
            for d, r, g, b, rr in 전체.get(c) or []:
                if 위:
                    if g >= 갭문 and b >= 볼문 and rr >= r문:
                        t.setdefault(d, []).append(r)
                else:
                    if g <= 갭문 and b <= 볼문 and rr <= r문:
                        t.setdefault(d, []).append(r)
        return t

    모두 = list(전체)
    머 = (f"    {'조합':<32}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'신호일':>8}")

    print(f"\n  ══ A·B 전체 ETF — 기준선과 「빠졌을 때」 ══")
    print(머)
    재기(모으기(모두, 99, 99, 99), "기준선 (조건 없음)", 년수)
    for 갭, 볼, r in ((-1, -1.0, -5), (-1.5, -1.0, -10), (-2, -1.0, -10),
                      (-1, -1.5, -10), (-2, -1.5, -15), (-3, -1.5, -15)):
        재기(모으기(모두, 갭, 볼, r), f"갭≤{갭}% · 볼≤{볼} · 20일≤{r}%", 년수)

    print(f"\n  ══ C **올랐을 때 산다** (한국 개별주에선 −1.54%로 실패) ══")
    print(머)
    for 갭, 볼, r in ((1, 1.0, 5), (1.5, 1.0, 10), (2, 1.5, 10)):
        재기(모으기(모두, 갭, 볼, r, 위=True),
             f"갭≥{갭}% · 볼≥{볼} · 20일≥{r}%", 년수)

    print(f"\n  ══ D **종류별** — 어디서 듣나 ══")
    for k in sorted(쓸것, key=lambda x: -len(쓸것[x])):
        codes = [c for c in 쓸것[k] if c in 전체]
        if len(codes) < 3:
            continue
        print(f"\n    ── {k} ({len(codes)}개) ──")
        print(머)
        재기(모으기(codes, 99, 99, 99), "기준선", 년수)
        재기(모으기(codes, -1.5, -1.0, -10), "빠졌을 때 (갭−1.5·볼−1·20일−10)", 년수)
        재기(모으기(codes, -1, -1.5, -10), "더 깊이 (갭−1·볼−1.5·20일−10)", 년수)
        재기(모으기(codes, 1.5, 1.0, 10, 위=True), "올랐을 때 (갭+1.5·볼+1·20일+10)", 년수)

    print("\n  읽는 법")
    print("    - **B가 A(기준선)보다 나아야** ETF 신호로 쓸 값어치가 있다")
    print("    - ⚠️ ETF는 **재무가 없다.** 60차에서 기술 조건만으로는")
    print("       +1.36%·승률 50.5%(동전던지기)였다 — ETF도 그런지가 핵심이다")
    print("    - ⚠️ 레버리지·인버스는 **장기 보유에 부적합**하다(변동성 손실)")
    print(f"    - ⚠️ 거래대금 {_최소대금/1e8:.0f}억 미만인 날은 뺐다 (실제로 못 산다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
