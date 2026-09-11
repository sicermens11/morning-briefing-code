#!/usr/bin/env python3
r"""
pick_now.py — **확정 규칙으로 실제 종목을 뽑아본다** (2026-09-03 · 78차)

⚠️⚠️ **사용자 목표는 「수익 실현」이다.** 지금까지는 평균·승률·낙폭 같은 숫자만 봤다.
   이번엔 **실제로 어떤 종목이 언제 뽑혔고 결과가 어땠는지**를 종목명과 함께 본다.

## 2026-09-03 기준 확정 규칙 (57~77차)
```
무엇      잉여금비율 >=30% · 부채비율 <=80% · 흑자 · 소형주(시총 3천억 미만)
          + 상대갭 -3%p 이하 + 볼린저 -1.0σ + 최근 20일 -10% 이하
          + 관리종목·SPAC 제외 · 거래대금 하한
언제      다음날 **시가** 매수
          ⭐ 어젯밤 미국(SPY)이 -0.5% 넘게 빠졌으면 더 좋다 (71차)
얼마      자산의 **20%씩** · 하루 **최대 2종목** (77차: 3개 이상은 역효과)
          여러 개 뜨면 **상대갭이 가장 크게 벌어진 둘**
언제 팔아  **+20% 지정가 매도** · 안 오르면 **최대 D+40** · **손절 없음** (76차)
피할 것   거래대금 급증 · 공시 있는 것 (73차: 조용한 게 낫다)
```

## 내는 것
```
A 최근 N개월 신호 — 날짜 · 종목 · 이름 · 매수가 · **실제 결과**(+20% 닿았나 · 며칠 걸렸나)
B 하루 2종목 규칙을 적용했을 때 실제로 뽑힌 것
C 아직 안 끝난 것 (보유 중) — 지금 어떻게 되고 있나
D 요약 — 이 기간에 실제로 얼마를 벌었나
```
⚠️ **과거를 보는 것이지 미래를 맞히는 게 아니다.** 이 기간 성적이 전체와 비슷한지 본다.

쓰는 법:
    python scripts\pick_now.py               # 최근 12개월
    python scripts\pick_now.py --부터 20260101
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
_목표 = 20.0
_최대보유 = 40
# ⚠️ 79차 뉴스 시험에서 **표본을 넓히려면** 상한을 풀어야 한다.
#   신호 자체는 더 있는데 77차 규칙(하루 2개)으로 잘랐기 때문이다.
_하루상한 = int(sys.argv[sys.argv.index("--상한") + 1]) if "--상한" in sys.argv else 2


def main():
    부터 = "20250901"
    if "--부터" in sys.argv:
        부터 = sys.argv[sys.argv.index("--부터") + 1]
    print(f"  {부터}부터 · 확정 규칙(57~77차)으로 실제 종목을 뽑는다\n", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    고비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}
    원시 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                if min(종, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            고비.setdefault(d8, {})[c] = 고 / 종
            원시.setdefault(d8, {})[c] = 시
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
    # 미국
    try:
        spy = json.load(io.open(os.path.join(O._DATA, "us-daily", "SPY.json"),
                                encoding="utf-8-sig"))["종가"]
    except Exception:
        spy = {}
    sk = sorted(spy)
    미맵 = {}
    import datetime as dt
    for d in 날:
        앞 = [x for x in sk if x < d]
        if len(앞) < 2:
            continue
        전 = max(앞)
        앞2 = [x for x in sk if x < 전]
        if not 앞2 or not spy[max(앞2)]:
            continue
        try:
            if (dt.datetime.strptime(d, "%Y%m%d")
                    - dt.datetime.strptime(전, "%Y%m%d")).days > 4:
                continue
        except Exception:
            pass
        미맵[d] = (spy[전] / spy[max(앞2)] - 1) * 100

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

    뽑 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < 부터:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        오늘 = []
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
            r20 = (c1 / sq[k - 20] - 1) * 100
            if r20 > -10:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            # ⚠️ `기본()`의 종목명 필드는 **「이름」**이다 (2026-09-03 확인).
            #   「종목명」으로 찾으면 빈 값이 나온다
            이름 = bb.get("이름") or ""
            오늘.append({
                "날": 다음, "code": code, "이름": 이름, "매수": 매수,
                "원시가": (원시.get(다음) or {}).get(code),
                "상대갭": g - 시갭, "낙폭20": r20, "시총": 시총 / 1e8,
                "대금": 대금 / 1e8, "잉여금": fm.get("잉여금비율"),
                "부채": fm.get("부채비율"), "ROE": fm.get("ROE"),
                "미국": 미맵.get(다음), "i": i + 1})
        # ⚠️ 77차 규칙: 하루 최대 2종목 · 상대갭이 가장 크게 벌어진 순
        오늘.sort(key=lambda x: x["상대갭"])
        뽑 += 오늘[:_하루상한]

    # 결과 계산 (76차 매도 규칙)
    for x in 뽑:
        i, code, 매수 = x["i"], x["code"], x["매수"]
        결과, 며칠, 상태 = None, None, "보유중"
        for h in range(0, _최대보유):
            j = i + h
            if j >= len(날):
                break
            dd = 날[j]
            v = 주가[dd].get(code)
            if not v:
                break
            hi = (고비.get(dd) or {}).get(code, 1.0) * v[0]
            if hi >= 매수 * (1 + _목표 / 100):
                결과, 며칠, 상태 = _목표 - _비용, max(1, h), "목표달성"
                break
        if 결과 is None:
            j = i + _최대보유
            if j < len(날):
                끝 = 주가[날[j]].get(code)
                if 끝:
                    결과, 며칠, 상태 = ((끝[0] / 매수 - 1) * 100 - _비용,
                                        _최대보유, "D+40매도")
            if 결과 is None:
                끝 = 주가[날[-1]].get(code)
                if 끝:
                    결과, 며칠, 상태 = ((끝[0] / 매수 - 1) * 100 - _비용,
                                        len(날) - 1 - i, "보유중")
        x["결과"], x["며칠"], x["상태"] = 결과, 며칠, 상태

    print(f"  ══ 뽑힌 종목 {len(뽑)}건 · 신호일 {len({x['날'] for x in 뽑})}일 ══\n")
    print(f"    {'매수일':<10}{'종목':<8}{'이름':<13}{'매수가':>9}{'상대갭':>8}"
          f"{'20일':>8}{'시총':>8}{'미국':>8}{'결과':>9}{'며칠':>6}  상태")
    for x in 뽑:
        미 = f"{x['미국']:+.2f}%" if x["미국"] is not None else "  —"
        r = f"{x['결과']:+.1f}%" if x["결과"] is not None else "  —"
        print(f"    {x['날']:<10}{x['code']:<8}{(x['이름'] or '')[:11]:<13}"
              f"{x['원시가'] or x['매수']:>9,.0f}{x['상대갭']:>+7.1f}%"
              f"{x['낙폭20']:>+7.1f}%{x['시총']:>7,.0f}억{미:>8}{r:>9}"
              f"{x['며칠'] if x['며칠'] is not None else '-':>6}  {x['상태']}")

    끝난 = [x for x in 뽑 if x["상태"] != "보유중" and x["결과"] is not None]
    if 끝난:
        v = [x["결과"] for x in 끝난]
        승 = sum(1 for z in v if z > 0) / len(v) * 100
        목표 = sum(1 for x in 끝난 if x["상태"] == "목표달성")
        print(f"\n  ══ 요약 (끝난 것 {len(끝난)}건) ══")
        print(f"    평균 {st.mean(v):+.2f}% · 승률 {승:.1f}% · 중앙 {st.median(v):+.2f}%")
        print(f"    **목표(+20%) 달성 {목표}건 ({목표/len(끝난)*100:.0f}%)** · "
              f"D+40 매도 {len(끝난)-목표}건")
        print(f"    평균 보유 {st.mean([x['며칠'] for x in 끝난]):.1f}일 "
              f"· 최고 {max(v):+.1f}% · 최저 {min(v):+.1f}%")
        # 자본으로 환산
        자산 = 5_000_000.0
        for x in sorted(끝난, key=lambda z: z["날"]):
            자산 *= (1 + 0.20 * x["결과"] / 100)
        print(f"    ⚠️ **거칠게** 자산의 20%씩 순서대로 넣었다고 치면 "
              f"500만 → {자산:,.0f}원")
        print("       (동시 보유·현금 제약을 무시한 계산이라 **참고용**이다)")
    남 = [x for x in 뽑 if x["상태"] == "보유중"]
    if 남:
        print(f"\n  ══ 아직 안 끝난 것 {len(남)}건 ══")
        for x in 남:
            print(f"    {x['날']} {x['code']} {(x['이름'] or '')[:12]:<13}"
                  f"현재 {x['결과']:+.1f}% ({x['며칠']}일째)")
    print("\n  읽는 법")
    print("    - ⚠️ **과거를 보는 것이지 미래를 맞히는 게 아니다**")
    print("    - 전체 성적(10.4년 연 +30.01% · 낙폭 -8.7%)과 비슷하면 신호가 살아 있다")
    print("    - **목표 달성률**이 높으면 +20% 지정가가 실제로 잘 걸린다는 뜻이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
