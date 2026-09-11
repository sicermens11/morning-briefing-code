#!/usr/bin/env python3
r"""
slip_lab.py — **시가에 정말 살 수 있나 (슬리피지)** (2026-09-03 · 80차)

⚠️⚠️⚠️ **이걸 1순위로 두는 이유.**
   지금까지 **모든 시험**이 「다음날 **시가**에 산다」를 전제로 했다.
   그런데 그게 실제로 되는지 **한 번도 안 재봤다.**
   ⇒ 나쁘게 나오면 **오늘 결과 전부를 다시 봐야 한다.** 나중에 아는 것보다 지금 아는 게 낫다.

## 왜 시가에 못 살 수 있나
```
① 시가는 **동시호가로 정해지는 한 점**이다. 그 가격에 내 주문이 체결된다는 보장이 없다
② **소형주는 호가 스프레드가 크다.** 우리 신호 종목은 시총 3천억 미만 소형주다
③ 갭 하락으로 시작하는 날은 **팔려는 사람이 몰려** 체결이 어긋날 수 있다
④ 시장가로 넣으면 **시가보다 불리하게** 체결되기 쉽다
```

## 어떻게 재나 — **VWAP(거래대금÷거래량)**을 쓴다
```
krx-daily에 **거래량**과 **거래대금**이 둘 다 있다.
  거래대금 ÷ 거래량 = **그날 평균 체결가**
⇒ 이게 「그날 아무 때나 시장가로 샀을 때의 대략적인 값」이다
⇒ 시가와 VWAP의 차이가 **슬리피지의 현실적인 상한**이다
```

## 재는 것
```
A 시가 vs VWAP  우리 신호 종목에서 둘이 얼마나 다른가
B 시가 vs 저가·고가  시가가 그날 어디쯤이었나 (최저였나 중간이었나)
C ⭐ **불리하게 사면** 성적이 얼마나 떨어지나
   시가 / 시가+0.3% / +0.5% / +1.0% / VWAP / 고가(최악)
D 매도 쪽도 — +20% 지정가는 안전하지만 **D+40 시장가 매도**는 슬리피지가 있다
E 자본 시뮬로 최종 판정
```
⚠️ **호가 데이터는 없다.** VWAP은 대용이지 정확한 체결가가 아니다. 그 한계를 명시한다.
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

_비용 = 0.26
_시작 = "20160401"
_목표 = 20.0
_최대보유 = 40


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # ⚠️ 원본 시가·저가·고가·VWAP을 **종가 대비 비율**로 담는다.
    #   수정주가에 곱해야 액면분할이 있어도 맞는다
    비 = {}      # 날 -> code -> (시가비, 저가비, 고가비, VWAP비)
    갭표, 시장갭, 앞종 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                저 = float(v.get("저가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                량 = float(v.get("거래량") or 0)
                대 = float(v.get("거래대금") or 0)
                if min(종, 시, 저, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            # ⚠️ 거래량이 0이면 VWAP을 못 낸다 → 종가로 대신한다
            vw = (대 / 량) if 량 > 0 else 종
            # ⚠️ VWAP이 저가~고가 밖이면 자료가 이상한 것이다. 가둔다
            vw = min(max(vw, 저), 고)
            비.setdefault(d8, {})[c] = (시 / 종, 저 / 종, 고 / 종, vw / 종)
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

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

    # ── 신호 + 매수일의 가격 구조 ──
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _최대보유 >= len(날):
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
            b = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b or not v0:
                continue
            종0 = v0[0]                     # 매수일 수정종가
            시가 = 종0 * b[0]
            저가 = 종0 * b[1]
            고가 = 종0 * b[2]
            vwap = 종0 * b[3]
            if min(시가, 저가, 고가, vwap) <= 0:
                continue
            # 이후 경로 (매도용)
            길 = []
            ok = True
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    ok = False
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    ok = False
                    break
                길.append((vv[0], vv[0] * bb2[2], vv[0] * bb2[3]))  # 종가·고가·VWAP
            if not ok:
                continue
            사건.append({"날": 다음, "code": code, "시가": 시가, "저가": 저가,
                        "고가": 고가, "vwap": vwap, "종가": 종0, "길": 길,
                        "i": i + 1, "대금": 대금, "상대갭": g - 시갭})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  사건 {len(사건):,}건 · {년수:.1f}년\n", flush=True)

    # ══ A·B 가격 구조 ══
    print("  ══ A·B **매수일의 가격 구조** — 시가가 어디쯤이었나 ══")
    print("     ⚠️ 우리 신호는 「크게 갭 하락한 날」을 산다. 그날 시가가 최저였나?")
    vw차 = [(x["vwap"] / x["시가"] - 1) * 100 for x in 사건]
    저차 = [(x["저가"] / x["시가"] - 1) * 100 for x in 사건]
    고차 = [(x["고가"] / x["시가"] - 1) * 100 for x in 사건]
    종차 = [(x["종가"] / x["시가"] - 1) * 100 for x in 사건]
    print(f"    {'항목':<24}{'평균':>10}{'중앙':>10}{'하위25%':>10}{'상위25%':>10}")
    for 라, v in (("VWAP − 시가", vw차), ("저가 − 시가", 저차),
                  ("고가 − 시가", 고차), ("종가 − 시가", 종차)):
        a = sorted(v)
        print(f"    {라:<24}{st.mean(v):>+9.2f}%{st.median(v):>+9.2f}%"
              f"{a[len(a)//4]:>+9.2f}%{a[len(a)*3//4]:>+9.2f}%")
    낮 = sum(1 for x in 사건 if abs(x["저가"] / x["시가"] - 1) < 0.002)
    print(f"    ⇒ **시가가 그날 저가와 거의 같았던 것**: {낮:,}건 "
          f"({낮/len(사건)*100:.1f}%)")
    print("       (많으면 「시가가 그날 바닥이었다」는 뜻 — 사기 좋았다)")

    # ══ C 불리하게 사면 ══
    def 팔기(x, 매수):
        for h, (종2, 고2, vw2) in enumerate(x["길"], 0):
            if 고2 >= 매수 * (1 + _목표 / 100):
                return _목표 - _비용, max(1, h)
        끝 = x["길"][min(_최대보유, len(x["길"])) - 1][0]
        return (끝 / 매수 - 1) * 100 - _비용, _최대보유

    def 재기(매수뽑기, 라):
        t = {}
        for x in 사건:
            매수 = 매수뽑기(x)
            if 매수 <= 0:
                continue
            r, h = 팔기(x, 매수)
            t.setdefault(x["날"], []).append(r)
        if len(t) < 8:
            print(f"    {라:<30}부족")
            return
        수 = [st.mean(v) for v in t.values()]
        승 = sum(1 for z in 수 if z > 0) / len(수) * 100
        해 = {}
        for d, v in t.items():
            해.setdefault(d[:4], []).append(st.mean(v))
        전 = 플 = 0
        for y, arr in 해.items():
            if len(arr) < 3:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        print(f"    {라:<30}{st.mean(수):>+8.2f}%{승:>7.1f}%{f'{플}/{전}':>8}"
              f"{len(t):>7}일")

    print("\n  ══ C ⭐ **불리하게 사면 성적이 얼마나 떨어지나** ══")
    print(f"    {'매수 가격':<30}{'평균':>9}{'승률':>8}{'연도별':>8}{'신호일':>8}")
    재기(lambda x: x["시가"], "**시가** (지금 가정)")
    for p in (0.3, 0.5, 1.0, 2.0):
        재기(lambda x, q=p: x["시가"] * (1 + q / 100), f"시가 +{p}% 불리하게")
    재기(lambda x: x["vwap"], "**VWAP** (그날 평균 체결가)")
    재기(lambda x: (x["시가"] + x["고가"]) / 2, "시가와 고가의 중간")
    재기(lambda x: x["고가"], "고가 (최악의 경우)")

    # ══ E 자본 시뮬 ══
    print("\n  ══ E ⭐ **자본 시뮬** — 슬리피지를 넣으면 얼마나 남나 ══")
    print("     초기 500만 · 종목당 20% · 하루 최대 2종목 (77차 규칙)")
    날인 = {d: i for i, d in enumerate(날)}
    날별 = {}
    for x in 사건:
        날별.setdefault(x["날"], []).append(x)

    def 자본(매수뽑기, 이름, 끝날="20260902"):
        현금, 보유, 기록, 투입 = 5_000_000.0, [], [], []
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            남 = []
            for 청산i, 금, r in 보유:
                if 청산i <= i:
                    현금 += 금 * (1 + r / 100)
                else:
                    남.append((청산i, 금, r))
            보유 = 남
            평가 = 현금 + sum(금 for _, 금, _ in 보유)
            오늘 = sorted(날별.get(d) or [], key=lambda z: z["상대갭"])[:2]
            for x in 오늘:
                매수 = 매수뽑기(x)
                if 매수 <= 0:
                    continue
                r, h = 팔기(x, 매수)
                쓸 = min(평가 * 0.20, x["대금"] * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                보유.append((min(x["i"] + h, len(날) - 1), 쓸, r))
            기록.append((d, 평가))
            투입.append(sum(금 for _, 금, _ in 보유) / 평가 if 평가 > 0 else 0)
        마지막 = 기록[-1][1] if 기록 else 5_000_000.0
        해 = len(기록) / 245
        연 = ((마지막 / 5_000_000.0) ** (1 / 해) - 1) * 100 if 마지막 > 0 else -100
        최고, 낙폭 = 5_000_000.0, 0.0
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
        print(f"    {이름:<30}{마지막:>13,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{f'{플}/{전}':>8}")

    print(f"    {'매수 가격':<30}{'끝 자산':>14}{'연평균':>8}{'최대낙폭':>9}{'연도별':>8}")
    자본(lambda x: x["시가"], "**시가** (지금 가정)")
    자본(lambda x: x["시가"] * 1.003, "시가 +0.3%")
    자본(lambda x: x["시가"] * 1.005, "시가 +0.5%")
    자본(lambda x: x["시가"] * 1.01, "시가 +1.0%")
    자본(lambda x: x["vwap"], "**VWAP** (현실적 하한)")

    print("\n  읽는 법")
    print("    - ⚠️⚠️ **호가 데이터가 없다.** VWAP은 대용이지 정확한 체결가가 아니다")
    print("    - **VWAP 판이 「그날 아무 때나 시장가로 샀을 때」**의 대략적인 값이다")
    print("    - 시가 판과 VWAP 판의 차이가 **슬리피지의 현실적인 폭**이다")
    print("    - ⚠️ 매도 쪽 +20%는 **지정가**라 슬리피지가 없다.")
    print("       D+40 매도만 시장가인데, 그건 40일 중 하루라 영향이 작다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
