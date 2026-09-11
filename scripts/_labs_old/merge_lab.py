#!/usr/bin/env python3
r"""
merge_lab.py — **한국 개별주 신호 + 해외 ETF 신호를 합치면?** (2026-09-03 · 70차)

⚠️⚠️ **오늘 세 번 실패한 뒤 처음 나온 실마리다.**
```
62차 자금배분 넷      ❌ 지수 갈아타기·비중↑·조건완화·새신호 섞기 — 전부 실패
63차 모멘텀·수급·지분율 ❌ -1.54% · +0.35% · +0.00%
68차 역추적           ❌ 놓친 것들의 쏠림이 전부 z=-0.20~+0.21 — 단서 없음
──────────────────────────────────────────────
69차 ETF            ⭐ **해외 ETF에서 「빠진 걸 산다」가 듣는다**
                      +4.73% · 승률 66.1% · 하위25% -1.35% · **5/5해** · 연 3.7일
```

## 왜 합칠 값어치가 있나
```
한국 개별주 신호   **한국이 빠진 날**에 뜬다   연 14.5일
해외 ETF 신호     **미국이 빠진 날**에 뜬다   연  3.7일
⇒ 두 시장이 항상 같이 빠지지는 않는다. **겹치지 않으면 자금을 더 쓴다.**
```

## 재는 것
```
A 겹침       두 신호가 같은 날 뜨나 · 합치면 연 며칠인가
B 빈도 확장   해외 ETF 문턱을 풀면 몇 일까지 늘고 성적이 얼마나 떨어지나
C 자본 시뮬   ⭐ **둘을 합쳐 돌리면 실제로 돈이 더 느나** (62차에서 넷 다 실패했다)
D 국내 ETF도  국내섹터·테마(+2.22% · 8/10해)를 셋째로 넣으면?
```
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · 비용 0.26% · 날짜 단위 · 연도별 3분의 2.
⚠️ ETF 유동성: 거래대금 3억 미만인 날은 뺀다. 시뮬에선 **거래대금의 1%**를 상한으로 건다.
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
from day_lab import 연간재무  # noqa: E402
from etf2_lab import 종류  # noqa: E402

_비용 = 0.26
_보유 = 20
_ETF = os.path.join(O._DATA, "etf-krx")
_최소대금 = 3e8


def 재기(날별, 이름, 년수, 폭=34):
    if len(날별) < 6:
        print(f"    {이름:<{폭}}신호일 {len(날별)}일 — 부족")
        return set(날별)
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
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 6
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/max(0.1,년수):>7.1f}일{f'{플}/{전}':>8}{len(날별):>7}일{별}")
    return set(날별)


def main():
    print("  자료 읽는 중...", flush=True)
    # ── ETF ──
    시세, 이름표 = {}, {}
    날짜 = []
    for f in sorted(glob.glob(os.path.join(_ETF, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        날짜.append(d["기준일"])
        for c, v in (d.get("종목") or {}).items():
            종, 시 = v.get("종가"), v.get("시가")
            if not 종 or 종 <= 0:
                continue
            시세.setdefault(c, {})[d["기준일"]] = (
                시 if (시 and 시 > 0) else 종, 종, v.get("거래대금") or 0)
            이름표[c] = v.get("이름") or 이름표.get(c, "")
    날짜.sort()
    무리 = {}
    for c in 시세:
        무리.setdefault(종류(이름표.get(c, "")), []).append(c)

    def ETF후보(codes):
        out = []
        for code in codes:
            k = sorted(시세[code])
            if len(k) < 300:
                continue
            종 = [시세[code][d][1] for d in k]
            for i in range(60, len(k) - 1 - _보유):
                대 = 시세[code][k[i]][2]
                if 대 < _최소대금:
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
                out.append((k[i + 1], code, (종[i + 1 + _보유] / 시 - 1) * 100 - _비용,
                            갭, 볼, r20, 대, 시))
        return out

    해외 = ETF후보(무리.get("해외") or [])
    테마 = ETF후보(무리.get("국내섹터·테마") or [])
    print(f"  해외 ETF 후보 {len(해외):,}건 · 국내섹터 {len(테마):,}건", flush=True)

    # ── 한국 개별주 ──
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    갭표, 시장갭, 앞종 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
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
        갭표[d["기준일"]] = 하루
        if len(하루) >= 100:
            시장갭[d["기준일"]] = st.median(list(하루.values()))

    def 재무값(code, d8):
        줄 = 재무.get(code)
        if not 줄:
            return None
        m = None
        for 적용, v in 줄:
            if 적용 <= d8:
                m = v
            else:
                break
        return m

    한국 = []
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
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -3:
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
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
            if (c1 - s20) / (2 * sd) > -1.0 or sq[k - 20] <= 0:
                continue
            if (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            한국.append((다음, code, (끝[0] / 매수 - 1) * 100 - _비용,
                        대금, 매수, i + 1))
    print(f"  한국 개별주 신호 {len(한국):,}건\n", flush=True)

    # ⚠️ 재무가 2016-04부터라 공통 창을 그때로 맞춘다
    _시작 = "20160401"
    쓸날 = [d for d in 날짜 if d >= _시작]
    년수 = len(쓸날) / 245
    머 = (f"    {'신호':<34}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'신호일':>8}")

    def ETF모으기(후보, 갭문, 볼문, r문):
        t = {}
        for d, c, r, g, b, rr, 대, 시 in 후보:
            if d >= _시작 and g <= 갭문 and b <= 볼문 and rr <= r문:
                t.setdefault(d, []).append(r)
        return t

    한국날 = {}
    for d, c, r, 대, 매, i in 한국:
        if d >= _시작:
            한국날.setdefault(d, []).append(r)

    print(f"  ══ A 두 신호를 나란히 ({_시작}부터 {년수:.1f}년) ══")
    print(머)
    K = 재기(한국날, "**한국 개별주** (재무+빠짐)", 년수)
    H = 재기(ETF모으기(해외, -1.5, -1.0, -10), "**해외 ETF** (갭−1.5·볼−1·20일−10)", 년수)
    T = 재기(ETF모으기(테마, -1.5, -1.0, -10), "국내섹터·테마 ETF", 년수)

    print(f"\n  ══ ⭐ 겹침 ══")
    print(f"    한국 {len(K)}일 · 해외ETF {len(H)}일 · 국내섹터 {len(T)}일")
    print(f"    한국 ∩ 해외ETF   **{len(K & H)}일**  "
          f"(해외의 {len(K & H)/max(1,len(H))*100:.1f}%)")
    print(f"    한국 ∪ 해외ETF   **{len(K | H)}일**  "
          f"→ 연 {len(K | H)/년수:.1f}일 (한국 단독 {len(K)/년수:.1f}일)")
    print(f"    셋 다 합치면      {len(K | H | T)}일 → 연 {len(K|H|T)/년수:.1f}일")

    print(f"\n  ══ B 해외 ETF 문턱을 풀면 ══")
    print(머)
    for 갭, 볼, r in ((-1.5, -1.0, -10), (-1, -1.0, -10), (-1, -1.0, -5),
                      (-0.5, -1.0, -5), (-1, -0.5, -5), (-0.5, -0.5, 0)):
        s = 재기(ETF모으기(해외, 갭, 볼, r), f"갭≤{갭} · 볼≤{볼} · 20일≤{r}", 년수)
        if s:
            print(f"        └ 한국과 겹침 {len(K & s)}일 "
                  f"({len(K & s)/max(1,len(s))*100:.0f}%) · 합치면 "
                  f"{len(K | s)}일 (연 {len(K|s)/년수:.1f}일)")

    # ── C 자본 시뮬 ──
    print(f"\n  ══ C ⭐ **자본 시뮬** — 합치면 실제로 돈이 더 느나 ══")
    print("     ⚠️ 62차에서 자금을 더 쓰려는 시도 넷이 **전부 실패**했다. 이번엔 다를까")
    날인 = {d: i for i, d in enumerate(날)}
    etf날인 = {d: i for i, d in enumerate(날짜)}

    def 시뮬(한국쓰나, ETF조건, 이름, 비중=0.10, 초기=5_000_000.0, 끝날='20260902'):
        살것 = {}
        if 한국쓰나:
            for d, code, r, 대금, 매수, i in 한국:
                if d >= _시작:
                    살것.setdefault(d, []).append(("K", code, 대금, 매수, i))
        if ETF조건:
            갭문, 볼문, r문 = ETF조건
            for d, c, r, g, b, rr, 대, 시 in 해외:
                if d >= _시작 and g <= 갭문 and b <= 볼문 and rr <= r문:
                    살것.setdefault(d, []).append(("E", c, 대, 시, etf날인[d]))
        현금, 보유 = 초기, []
        기록, 투입 = [], []
        # ⚠️⚠️ **2025~2026을 뺀 판**을 따로 내야 공정하다.
        #   62차에서 그 두 해를 빼니 결론이 뒤집힌 전례가 있다
        for d in [z for z in 쓸날 if z <= 끝날]:
            # 청산
            남 = []
            for 종류_, 청산i, 금, 단가, code in 보유:
                끝났나 = (청산i <= 날인.get(d, -1)) if 종류_ == "K" \
                    else (청산i <= etf날인.get(d, -1))
                if 끝났나:
                    if 종류_ == "K":
                        v = 주가[날[min(청산i, len(날) - 1)]].get(code)
                        현금 += (금 * (v[0] / 단가) if v else 금) * (1 - _비용 / 100)
                    else:
                        dd = 날짜[min(청산i, len(날짜) - 1)]
                        v = (시세.get(code) or {}).get(dd)
                        현금 += (금 * (v[1] / 단가) if v else 금) * (1 - _비용 / 100)
                else:
                    남.append((종류_, 청산i, 금, 단가, code))
            보유 = 남
            평가 = 현금
            for 종류_, 청산i, 금, 단가, code in 보유:
                if 종류_ == "K":
                    v = 주가.get(d, {}).get(code)
                    평가 += 금 * (v[0] / 단가) if v else 금
                else:
                    v = (시세.get(code) or {}).get(d)
                    평가 += 금 * (v[1] / 단가) if v else 금
            for 종류_, code, 대금, 단가, i in 살것.get(d) or []:
                쓸 = min(평가 * 비중, 대금 * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                끝i = (min(i + _보유, len(날) - 1) if 종류_ == "K"
                       else min(i + _보유, len(날짜) - 1))
                보유.append((종류_, 끝i, 쓸, 단가, code))
            기록.append((d, 평가))
            투입.append(sum(금 for _, _, 금, _, _ in 보유) / 평가 if 평가 > 0 else 0)
        마지막 = 기록[-1][1] if 기록 else 초기
        해 = len(기록) / 245
        연 = ((마지막 / 초기) ** (1 / 해) - 1) * 100 if 마지막 > 0 else -100
        최고, 낙폭 = 초기, 0.0
        for _, v in 기록:
            최고 = max(최고, v)
            낙폭 = min(낙폭, v / 최고 - 1)
        해별 = {}
        for d, v in 기록:
            해별.setdefault(d[:4], []).append(v)
        플 = 전 = 0
        for y in sorted(해별):
            a = 해별[y]
            if len(a) < 60:
                continue
            전 += 1
            플 += 1 if a[-1] > a[0] else 0
        print(f"    {이름:<38}{마지막:>13,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{sum(투입)/max(1,len(투입))*100:>8.1f}%{f'{플}/{전}':>8}")

    print(f"    {'전략':<38}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
          f"{'투입비':>8}{'연도별':>8}")
    # ⚠️⚠️ **공정 비교가 핵심이다.** 「둘 합침 20%」가 좋아 보이는 게
    #   합쳐서인지 **비중을 키워서인지** 갈라야 한다. 같은 비중끼리 나란히 놓는다
    for 끝날, 라벨 in (("20260902", "2016-04 ~ 2026-09 (10.4년)"),
                       ("20241230", "2016-04 ~ 2024-12 (8.8년) — **2025·26 뺀 판**")):
        print("\n    ══════ " + 라벨 + " ══════")
        print(f"    {'전략':<38}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
              f"{'투입비':>8}{'연도별':>8}")
        for 비 in (0.10, 0.20, 0.34):
            print(f"    ── 종목당 {비*100:.0f}% ──")
            시뮬(True, None, f"한국만 · {비*100:.0f}%", 비중=비, 끝날=끝날)
            시뮬(False, (-1, -1.0, -5), f"해외ETF만 · {비*100:.0f}%", 비중=비, 끝날=끝날)
            시뮬(True, (-1.5, -1.0, -10), f"**둘 합침**(갭−1.5) · {비*100:.0f}%",
                 비중=비, 끝날=끝날)
            시뮬(True, (-1, -1.0, -5), f"**둘 합침**(넓게) · {비*100:.0f}%",
                 비중=비, 끝날=끝날)

    print("\n  읽는 법")
    print("    - **겹침률이 낮고 합친 시뮬이 한국 단독보다 나아야** 값어치가 있다")
    print("    - ⚠️ 62차에서 자금을 더 쓰려는 시도 넷이 전부 실패했다. 여기가 다섯 번째다")
    print("    - ⚠️ 해외 ETF는 연도가 적다(최근에 늘었다). 연도별 칸을 꼭 본다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
