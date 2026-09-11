#!/usr/bin/env python3
r"""
hynix_lab.py — **93차. 보조 전략을 하이닉스 단독으로 다시 짠다** (2026-09-03)

## 92차가 알려준 것
```
해외 -2%↓ -> 다음날 매수         SK하이닉스        삼성전자
엔비디아                    **+1.13%** 9/11⭐   +0.27% 6/11
어플라이드                    +1.05% **10/11**⭐  ...
램리서치                     +0.99% **10/11**⭐
웨스턴디지털                   +0.83% **10/11**⭐
⇒ **삼성전자는 안 되고 SK하이닉스만 된다.**
   90차에서 둘을 반반 섞은 건 **손해였다**
```

## 재는 것
```
A 삼성 섞기 vs 하이닉스 단독      — 90차의 실수를 확인
B 어느 미국 종목·문턱이 최고인가
C ⭐ **여러 개가 동시에 빠졌을 때** — 신호가 겹치면 더 센가
D 보유일 3·5·10·15·20일
E 파는 법 — 정해진 날 vs **목표수익 도달 시**
F ⭐⭐ 자산 규모별 **주력 + 보조(하이닉스)** — 90차 다시
G ⚠️ 2025·26 제외
```
⚠️ 판정: **끝 자산**과 **낙폭**. 평균 수익은 참고다 (「평균 수익은 돈이 아니다」)
⚠️ 주수는 **원본 시가**로, 수익률은 **수정 비율**로 (53차 버그)
"""
import bisect
import datetime as dt
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_목표 = 20.0
_최대보유 = 40
_YH = os.path.join(O._DATA, "yahoo")
_하 = "000660"
_삼 = "005930"
미국 = (("NVDA", "엔비디아"), ("AMAT", "어플라이드"), ("LRCX", "램리서치"),
        ("SOXX", "반도체지수"), ("WDC", "웨스턴디지털"), ("MU", "마이크론"),
        ("ASML", "ASML"), ("KLAC", "KLA"))


def main():
    미등 = {}
    for 심, 이름 in 미국:
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
        미등[심] = (이름, e, sorted(e))

    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종, 원시 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

    쓸 = {}
    for 심, (이름, e, ks) in 미등.items():
        t = {}
        for d in 날:
            j = bisect.bisect_left(ks, d)
            if j == 0:
                continue
            전 = ks[j - 1]
            try:
                if (dt.datetime.strptime(d, "%Y%m%d")
                        - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                    continue
            except Exception:
                pass
            t[d] = e[전]
        쓸[심] = t

    선 = {}
    for c in (_하, _삼):
        선[c] = {d: 주가[d][c][0] for d in 날 if 주가[d].get(c)}
    쓸날 = [d for d in 날 if d >= _시작]
    년수 = len(쓸날) / 245
    날인 = {d: i for i, d in enumerate(날)}
    print(f"  {len(쓸날):,}일 · {년수:.1f}년 · 미국 {len(미등)}종목\n", flush=True)

    def 사기(날들, 종목들, 보유일=5, 목표=None):
        """목표를 주면 그 수익률에 닿을 때 판다 (최대 보유일까지)"""
        결, 해 = [], {}
        for d in 날들:
            i = 날인[d]
            for c in 종목들:
                s = 선[c]
                b = (비.get(d) or {}).get(c)
                v0 = s.get(d)
                if not b or not v0:
                    continue
                매수 = v0 * b[0]
                r = None
                if 목표 is not None:
                    for h in range(0, 보유일):
                        j = i + h
                        if j >= len(날):
                            break
                        b2 = (비.get(날[j]) or {}).get(c)
                        v2 = s.get(날[j])
                        if not b2 or not v2:
                            continue
                        # 고가가 목표에 닿으면 그날 판다
                        if v2 * b2[1] >= 매수 * (1 + 목표 / 100):
                            r = 목표 - _비용
                            break
                if r is None:
                    j = i + 보유일 - 1
                    if j >= len(날) or not s.get(날[j]):
                        continue
                    r = (s[날[j]] / 매수 - 1) * 100 - _비용
                결.append(r)
                해.setdefault(d[:4], []).append(r)
        return 결, 해

    def 보고(결, 해, 라, 날수, 폭=30):
        if len(결) < 40:
            print(f"    {라:<{폭}}표본 부족")
            return
        전 = 플 = 0
        for y, a in 해.items():
            if len(a) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(a) > 0 else 0
        승 = sum(1 for r in 결 if r > 0) / len(결) * 100
        별 = "⭐" if (전 >= 9 and 플 / 전 >= 2 / 3 and st.mean(결) > 0.5) else "  "
        print(f"    {라:<{폭}}{날수:>6}일{len(결):>7}건{st.mean(결):>+9.2f}%"
              f"{st.median(결):>+9.2f}%{승:>8.1f}%{f'{플}/{전}':>8}{별}")

    머 = (f"    {'조건':<30}{'날':>7}{'표본':>7}{'평균':>10}{'중앙':>9}"
          f"{'승률':>8}{'연도별':>8}")

    def 날뽑(심, 문):
        t = 쓸.get(심) or {}
        return [d for d in 쓸날 if t.get(d) is not None and t[d] <= 문]

    # ══ A 삼성 섞기 vs 하이닉스 단독 ══
    print("  ══ A ⚠️ **90차의 실수 확인** — 삼성을 섞으면 ══")
    print(머)
    엔 = 날뽑("NVDA", -2)
    for 종, 라 in (((_하,), "하이닉스만"), ((_삼,), "삼성만"),
                   ((_하, _삼), "둘 다 (90차가 한 것)")):
        결, 해 = 사기(엔, 종)
        보고(결, 해, f"엔비디아 −2%↓ → {라}", len(엔))

    # ══ B 어느 미국 종목·문턱 ══
    print(f"\n  ══ B **어느 미국 종목·문턱이 최고인가** (하이닉스만) ══")
    print(머)
    표 = []
    for 심, (이름, _, _) in 미등.items():
        for 문 in (-1.5, -2.0, -3.0):
            날들 = 날뽑(심, 문)
            if len(날들) < 60:
                continue
            결, 해 = 사기(날들, (_하,))
            보고(결, 해, f"{이름} {문}%↓", len(날들))
            if 결:
                전 = 플 = 0
                for y, a in 해.items():
                    if len(a) >= 5:
                        전 += 1
                        플 += 1 if st.mean(a) > 0 else 0
                표.append((st.mean(결), 심, 문, 전, 플))

    # ══ C 여러 개가 동시에 ══
    print(f"\n  ══ C ⭐ **여러 개가 동시에 빠졌을 때** ══")
    print("     8개 미국 종목 중 몇 개가 −2% 넘게 빠졌나")
    점 = {}
    for d in 쓸날:
        s = 0
        for 심 in 미등:
            v = (쓸.get(심) or {}).get(d)
            if v is not None and v <= -2:
                s += 1
        점[d] = s
    print(f"    {'점수':<12}{'날':>7}{'표본':>7}{'평균':>10}{'중앙':>9}"
          f"{'승률':>8}{'연도별':>8}")
    for lo, hi, 라 in ((0, 0, "0개 (아무도 안 빠짐)"), (1, 2, "1~2개"),
                       (3, 5, "3~5개"), (6, 9, "6개↑ (다 빠짐)")):
        날들 = [d for d in 쓸날 if lo <= 점[d] <= hi]
        if len(날들) < 40:
            continue
        결, 해 = 사기(날들, (_하,))
        보고(결, 해, 라, len(날들), 폭=12)

    # ══ D 보유일 ══
    print(f"\n  ══ D **며칠 들고 있나** (엔비디아 −2%↓ · 하이닉스) ══")
    print(머)
    for h in (1, 3, 5, 10, 15, 20):
        결, 해 = 사기(엔, (_하,), 보유일=h)
        보고(결, 해, f"{h}일 보유", len(엔))

    # ══ E 파는 법 ══
    print(f"\n  ══ E **목표수익에 닿으면 판다** (최대 10일) ══")
    print(머)
    결, 해 = 사기(엔, (_하,), 보유일=10)
    보고(결, 해, "목표 없음 (10일 뒤 종가)", len(엔))
    for 목 in (2, 3, 5, 8):
        결, 해 = 사기(엔, (_하,), 보유일=10, 목표=목)
        보고(결, 해, f"+{목}% 닿으면 판다", len(엔))

    # ══ F 자산 규모별 주력 + 보조 ══
    print(f"\n  ══ F ⭐⭐ **주력 + 보조(하이닉스)** — 90차 다시 ══")

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

    주력 = {}
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
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
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0 or sq[kk - 20] <= 0:
                continue
            if (c1 / sq[kk - 20] - 1) * 100 > -10:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결과, 청산 = None, None
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                bb2 = (비.get(날[j]) or {}).get(code)
                if not vv or not bb2:
                    break
                if vv[0] * bb2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 청산 = _목표 - _비용, j
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            주력.setdefault(i + 1, []).append(
                {"청산": 청산, "결과": 결과, "원시": o0, "대금": b0[2],
                 "상대갭": g - 시갭})

    보조 = {}
    엔셋 = set(엔)
    for i, d in enumerate(날):
        if d not in 엔셋:
            continue
        j = i + 9          # 10일 보유
        if j >= len(날):
            continue
        s = 선[_하]
        b = (비.get(d) or {}).get(_하)
        v0, v1 = s.get(d), s.get(날[j])
        o0 = (원시.get(d) or {}).get(_하)
        if not b or not v0 or not v1 or not o0:
            continue
        보조[i] = [{"청산": j, "결과": (v1 / (v0 * b[0]) - 1) * 100 - _비용,
                    "원시": o0, "대금": 9e15}]
    print(f"     주력 신호일 {len(주력)}일 · 보조 신호일 {len(보조)}일 "
          f"(하이닉스 단독 · 10일 보유)")

    def 시뮬(시드, 주on, 보몫, 라, 끝년=None):
        현금, 보유, 곡 = float(시드), [], []
        주n = 보n = 0
        for i, d in enumerate(날):
            if d < _시작:
                continue
            if 끝년 and d[:4] > 끝년:
                break
            남 = []
            for p in 보유:
                if p["청산"] <= i:
                    현금 += p["주수"] * p["원시"] * (1 + p["결과"] / 100)
                else:
                    남.append(p)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(p["주수"] * p["원시"] for p in 보유)
            보중 = sum(p["주수"] * p["원시"] for p in 보유 if p.get("보"))
            if 주on:
                for x in sorted(주력.get(i, []), key=lambda z: z["상대갭"])[:2]:
                    쓸2 = min(평 * 0.20, 현금, x["대금"] * 0.01)
                    주수 = int(쓸2 // x["원시"])
                    if 주수 < 1:
                        continue
                    실 = 주수 * x["원시"]
                    if 실 > 현금:
                        continue
                    현금 -= 실
                    보유.append({**x, "주수": 주수, "보": False})
                    주n += 1
            if 보몫 > 0 and i in 보조 and 보중 <= 0:
                x = 보조[i][0]
                주수 = int(min(현금, 평 * 보몫) // x["원시"])
                if 주수 >= 1 and 주수 * x["원시"] <= 현금:
                    현금 -= 주수 * x["원시"]
                    보유.append({**x, "주수": 주수, "보": True})
                    보n += 1
            곡.append(평)
        끝 = 현금 + sum(p["주수"] * p["원시"] for p in 보유)
        yr = len(곡) / 245
        cagr = ((끝 / 시드) ** (1 / max(yr, 0.1)) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        print(f"    {라:<24}{끝:>17,.0f}원{cagr:>+9.2f}%{낙:>8.1f}%"
              f"{주n:>7}{보n:>6}")

    머2 = (f"    {'전략':<24}{'끝 자산':>18}{'연평균':>9}{'낙폭':>8}"
           f"{'주력':>7}{'보조':>6}")
    for 시드 in (5_000_000, 30_000_000, 100_000_000, 300_000_000):
        print(f"\n     자산 {시드:,}원")
        print(머2)
        시뮬(시드, True, 0, "A 주력만")
        시뮬(시드, False, 0.5, "B 보조만 (50%)")
        시뮬(시드, True, 0.3, "C 주력 + 보조 30%")
        시뮬(시드, True, 0.5, "C2 주력 + 보조 50%")

    print(f"\n  ══ G ⚠️ **2025·26 제외** ══")
    for 시드 in (30_000_000, 100_000_000):
        print(f"     자산 {시드:,}원")
        print(머2)
        시뮬(시드, True, 0, "A 주력만", 끝년="2024")
        시뮬(시드, False, 0.5, "B 보조만", 끝년="2024")
        시뮬(시드, True, 0.3, "C 주력 + 보조 30%", 끝년="2024")

    print("\n  읽는 법")
    print("    - A에서 「둘 다」가 「하이닉스만」보다 나쁘면 90차가 틀린 것이다")
    print("    - F·G에서 C가 A를 이겨야 보조를 붙일 값어치가 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
