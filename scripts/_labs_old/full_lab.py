#!/usr/bin/env python3
r"""
full_lab.py — **세 층을 합친 판 + 걷기검증** (2026-09-03 · 72차)

## 오늘 선 신호 세 층
```
① 한국 개별주 (주 신호)   재무 우량 + 크게 빠짐        +10.05% · 72.2% · 11/11해
② 해외 ETF (자금 확대)    국내 상장 해외추종 · 겹침 26%  +5.56% · 67.7% · 5/5해
③ 미국 하락 (등급 조정)   어젯밤 미국 -0.5%↓          ①이 +13.98% · 78.5%로 강해짐
```
**셋이 서로 다른 문제를 푼다**: ① 무엇을 살까 · ② 자금이 노는 문제(양) · ③ 언제가 좋은가(질)
⚠️ **②와 ③은 방향이 반대다.** ③은 빈도를 줄이고(14.5->6.2일) ②는 늘린다(14.5->18.9일).
   **같이 써야 균형이 맞는다.** 아직 같이 안 돌려봤다 — 그게 이 시험이다.

## 재는 것
```
A 세 층 조합      ①만 / ①+② / ①+③ / ①+②+③ 을 자본 시뮬로
B ⭐ **걷기검증**  해마다 **그 해 이전만** 보고 문턱을 정해 그 해를 산다
C 기간 분할       2025·26 뺀 8.8년 판을 같이 낸다
```
⚠️⚠️ **③의 유효성이 시기를 탈 수 있다.** 71차에서 미국->한국 전이율이
   2011년 0.580 -> 2025년 **0.160**으로 약해졌다(2026년 0.456으로 회복).
   ⇒ 걷기검증에서 **연도별로 갈리는지** 봐야 한다.
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · 비용 0.26% · 연도별 3분의 2.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402
from etf2_lab import 종류  # noqa: E402

_비용 = 0.26
_보유 = 20
_시작 = "20160401"
_ETF = os.path.join(O._DATA, "etf-krx")
_최소대금 = 3e8


def main():
    print("  자료 읽는 중...", flush=True)
    # ── 미국 ──
    try:
        spy = json.load(io.open(os.path.join(O._DATA, "us-daily", "SPY.json"),
                                encoding="utf-8-sig"))["종가"]
    except Exception:
        spy = {}
    sk = sorted(spy)
    미등락 = {}
    for j in range(1, len(sk)):
        p = spy[sk[j - 1]]
        if p:
            미등락[sk[j]] = (spy[sk[j]] / p - 1) * 100

    # ── ETF ──
    시세, 이름표, 날짜 = {}, {}, []
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
    해외코드 = [c for c in 시세 if 종류(이름표.get(c, "")) == "해외"]

    # ── 한국 ──
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

    # 미국 전일 등락을 한국 날짜에 붙인다 (연휴 4일 초과는 제외)
    import datetime as dt
    미맵 = {}
    for d in 날:
        앞 = [x for x in sk if x < d]
        if not 앞:
            continue
        전 = max(앞)
        if 전 not in 미등락:
            continue
        try:
            if (dt.datetime.strptime(d, "%Y%m%d")
                    - dt.datetime.strptime(전, "%Y%m%d")).days > 4:
                continue
        except Exception:
            pass
        미맵[d] = 미등락[전]

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

    # ── 한국 후보 (문턱을 나중에 걸 수 있게 재무값을 담아둔다) ──
    한국 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
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
            if not fm:
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
                        대금, 매수, i + 1, fm))
    print(f"  한국 후보 {len(한국):,}건 (재무 문턱 걸기 전)", flush=True)

    해외 = []
    for code in 해외코드:
        k = sorted(시세[code])
        if len(k) < 300:
            continue
        종 = [시세[code][d][1] for d in k]
        for i in range(60, len(k) - 1 - _보유):
            대 = 시세[code][k[i]][2]
            if 대 < _최소대금 or k[i + 1] < _시작:
                continue
            c1 = 종[i]
            s20 = st.mean(종[i - 19:i + 1])
            sd = st.pstdev(종[i - 19:i + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -1.0 or 종[i - 20] <= 0:
                continue
            if (c1 / 종[i - 20] - 1) * 100 > -10:
                continue
            시 = 시세[code][k[i + 1]][0]
            if 시 <= 0:
                continue
            갭 = (시 / c1 - 1) * 100
            if 갭 > -1.5 or abs(갭) > 20:
                continue
            # >>> 2026-09-03 버그 수정. **i는 그 종목만의 날짜 목록 k에서의 위치**인데
            #     시뮬에서는 전체 날짜 목록(날짜)의 위치로 썼다. 늦게 상장한 ETF일수록
            #     k가 짧아 인덱스가 작아지고, 청산일이 엉뚱한 날(심하면 과거)이 됐다.
            #     70차 merge_lab은 etf날인[d]를 써서 맞았다. 여기도 그렇게 고친다.
            해외.append((k[i + 1], code, (종[i + 1 + _보유] / 시 - 1) * 100 - _비용,
                        대, 시, None))
    print(f"  해외 ETF 후보 {len(해외):,}건\n", flush=True)

    날인 = {d: i for i, d in enumerate(날)}
    etf날인 = {d: i for i, d in enumerate(날짜)}

    def 시뮬(쓸한국, 쓸ETF, 미문턱, 이름, 비중=0.20, 끝날="20260902",
             초기=5_000_000.0, 걷기=False):
        """미문턱: None이면 미국 조건 없음. 숫자면 그 이하일 때만 산다.
        걷기=True면 **그 해 이전 자료로만** 재무 문턱을 정한다."""
        # 재무 문턱
        고정 = (30.0, 80.0)
        해별문턱 = {}
        if 걷기:
            해들 = sorted({x[0][:4] for x in 한국})
            for y in 해들:
                앞 = [x for x in 한국 if x[0][:4] < y]
                잉 = sorted(x[6].get("잉여금비율") for x in 앞
                            if x[6].get("잉여금비율") is not None)
                부 = sorted(x[6].get("부채비율") for x in 앞
                            if x[6].get("부채비율") is not None)
                if len(잉) < 200 or len(부) < 200:
                    continue
                해별문턱[y] = (잉[len(잉) // 2], 부[len(부) // 2])

        def 통과(x):
            fm = x[6]
            if fm.get("흑자") != 1.0:
                return False
            잉문, 부문 = (해별문턱.get(x[0][:4]) if 걷기 else 고정) or (None, None)
            if 잉문 is None:
                return False
            return (fm.get("잉여금비율", -9e9) >= 잉문
                    and fm.get("부채비율", 9e9) <= 부문)

        살것 = {}
        if 쓸한국:
            for x in 한국:
                if not 통과(x):
                    continue
                if 미문턱 is not None:
                    m = 미맵.get(x[0])
                    if m is None or m > 미문턱:
                        continue
                살것.setdefault(x[0], []).append(("K", x[1], x[3], x[4], x[5]))
        if 쓸ETF:
            for d, c, r, 대, 시, _ in 해외:
                # >>> 전체 ETF 날짜 목록의 위치를 쓴다 (위 버그 수정)
                살것.setdefault(d, []).append(("E", c, 대, 시, etf날인[d]))
        현금, 보유 = 초기, []
        기록, 투입 = [], []
        for d in [z for z in 날짜 if _시작 <= z <= 끝날]:
            남 = []
            for 종_, 청산i, 금, 단가, code in 보유:
                끝났나 = (청산i <= 날인.get(d, -1)) if 종_ == "K" \
                    else (청산i <= etf날인.get(d, -1))
                if 끝났나:
                    if 종_ == "K":
                        v = 주가[날[min(청산i, len(날) - 1)]].get(code)
                        현금 += (금 * (v[0] / 단가) if v else 금) * (1 - _비용 / 100)
                    else:
                        dd = 날짜[min(청산i, len(날짜) - 1)]
                        v = (시세.get(code) or {}).get(dd)
                        현금 += (금 * (v[1] / 단가) if v else 금) * (1 - _비용 / 100)
                else:
                    남.append((종_, 청산i, 금, 단가, code))
            보유 = 남
            평가 = 현금
            for 종_, 청산i, 금, 단가, code in 보유:
                v = (주가.get(d, {}).get(code) if 종_ == "K"
                     else (시세.get(code) or {}).get(d))
                if v:
                    평가 += 금 * ((v[0] if 종_ == "K" else v[1]) / 단가)
                else:
                    평가 += 금
            for 종_, code, 대금, 단가, i in 살것.get(d) or []:
                쓸 = min(평가 * 비중, 대금 * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                끝i = (min(i + _보유, len(날) - 1) if 종_ == "K"
                       else min(i + _보유, len(날짜) - 1))
                보유.append((종_, 끝i, 쓸, 단가, code))
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
        print(f"    {이름:<44}{마지막:>13,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{sum(투입)/max(1,len(투입))*100:>8.1f}%{f'{플}/{전}':>8}")
        return 연

    for 끝날, 라벨 in (("20260902", "2016-04 ~ 2026-09 (10.4년)"),
                       ("20241230", "2016-04 ~ 2024-12 (8.8년) — 2025·26 뺀 판")):
        print("\n  ══════ " + 라벨 + " ══════")
        print(f"    {'전략':<44}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
              f"{'투입비':>8}{'연도별':>8}")
        for 비 in (0.10, 0.20):
            print(f"    ── 종목당 {비*100:.0f}% ──")
            시뮬(True, False, None, f"① 한국만", 비중=비, 끝날=끝날)
            시뮬(True, True, None, f"①+② 한국+해외ETF", 비중=비, 끝날=끝날)
            시뮬(True, False, -0.5, f"①+③ 한국+미국-0.5%↓", 비중=비, 끝날=끝날)
            시뮬(True, False, 0.0, f"①+③ 한국+미국 하락", 비중=비, 끝날=끝날)
            시뮬(True, True, -0.5, f"**①+②+③ 셋 다**", 비중=비, 끝날=끝날)
            시뮬(True, True, 0.0, f"**①+②+③ (미국 하락만)**", 비중=비, 끝날=끝날)

    print("\n  ══════ ⭐ B 걷기검증 — 그 해 이전만 보고 문턱을 정한다 ══════")
    print(f"    {'전략':<44}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}"
          f"{'투입비':>8}{'연도별':>8}")
    for 끝날, 라벨 in (("20260902", "10.4년"), ("20241230", "8.8년")):
        print(f"    ── {라벨} ──")
        시뮬(True, False, None, "① 한국만 · 걷기", 비중=0.20, 끝날=끝날, 걷기=True)
        시뮬(True, True, None, "①+② · 걷기", 비중=0.20, 끝날=끝날, 걷기=True)
        시뮬(True, True, -0.5, "**①+②+③ · 걷기**", 비중=0.20, 끝날=끝날, 걷기=True)

    print("\n  읽는 법")
    print("    - **걷기검증이 고정 문턱과 비슷하면** 과최적화가 아니다")
    print("    - ②는 자금을 늘리고 ③은 줄인다. **셋 다 쓴 판이 균형점인지**가 핵심")
    print("    - ⚠️ 71차에서 미국→한국 전이율이 2011년 0.580 → 2025년 0.160으로")
    print("       약해졌다(2026년 0.456 회복). ③이 시기를 탈 수 있다 — 연도별을 본다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
