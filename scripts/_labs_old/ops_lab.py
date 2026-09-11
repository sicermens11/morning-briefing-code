#!/usr/bin/env python3
r"""
ops_lab.py — **매매 운용을 여러 각도로** (2026-09-03 · 82차)

⚠️⚠️ **사용자 지시.** *"계속 테스트해야 해! 할 수 있는 모든 걸 해! 다양한 각도로."*
   ⇒ 계획표 v2의 86~93차를 **한 스크립트에 묶는다.**
      수정주가 계산이 무거워 따로 돌리면 로딩만 몇 분씩 낭비된다.

## 지금까지 확정 (57~80차)
```
무엇   잉여금>=30% · 부채<=80% · 흑자 · 소형주 + 상대갭-3%p · 볼린저-1σ · 20일-10%
언제   다음날 시가 (80차: 시가가 그날 저가인 경우가 61.2% — 사기 좋다)
얼마   자산의 20%씩 · 하루 최대 2종목
매도   +20% 지정가 · 최대 D+40 · 손절 없음
자본   10.4년 500만 -> 7,642만원 (연 +29.87% · 낙폭 -9.0% · 11/11해)
       VWAP로 보수적으로 잡아도 연 +25.27%
```

## 재는 것 — **한 번도 안 잰 것들**
```
A 재진입      같은 종목이 또 뜨면? (78차에서 위메이드플레이가 3번 나왔다)
              중복 보유를 막으면 나아지나
B 신호 강도    상대갭 -25%와 -3%를 **같은 비중**으로 샀다. 강도에 따라 나눠야 하나
C 분할        한 번에 사고 한 번에 판다. 나눠 사면?
D 자금 규모    500만·3천만·1억·3억이면 어디서 막히나
              ⚠️ 「1억부터 유동성에 막힌다」고 했는데 **실제 시뮬은 안 했다**
E 노는 자금    82%를 **무이자**로 뒀다. 예금·MMF면 연 2~3%가 더해진다
F 요일·월      계절성이 있나
G 외국인       68차에서 **유일하게 방향이 갈린** 지표다
              「많이 사는 것 고르기」가 아니라 **「파는 것 피하기」**
```
⚠️ 판정: 자본 시뮬 · 낙폭 · 연도별 · 2025·26 뺀 판.
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
    기본, 재무, 수급 = O._기본(), 연간재무(), O._수급()
    날인 = {d: i for i, d in enumerate(날)}
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}
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
            비.setdefault(d8, {})[c] = (시 / 종, 고 / 종)
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
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

    def 숫(x):
        try:
            return float(str(x).replace(",", "").replace("%", ""))
        except (TypeError, ValueError):
            return None

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
        창 = 날[max(0, i - 19):i + 1]
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
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            외 = 0.0
            for dd in 창:
                fr = (수급.get(dd) or {}).get(code)
                if fr:
                    외 += 숫(fr.get("외국인")) or 0
            결과, 며칠 = None, _최대보유
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    break
                if vv[0] * bb2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 며칠 = _목표 - _비용, max(1, h)
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과 = (끝[0] / 매수 - 1) * 100 - _비용
            사건.append({"날": 다음, "code": code, "결과": 결과, "며칠": 며칠,
                        "상대갭": g - 시갭, "대금": 대금, "시총": 시총,
                        "미국": 미맵.get(다음), "외국인": 외, "i": i + 1})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    날별 = {}
    for x in 사건:
        날별.setdefault(x["날"], []).append(x)
    print(f"  사건 {len(사건):,}건 · 신호일 {len(날별)}일 · {년수:.1f}년\n", flush=True)

    def 시뮬(이름, 비중=0.20, 상한=2, 끝날="20260902", 초기=5_000_000.0,
             중복금지=False, 강도비중=False, 이자=0.0, 고르기=None,
             유동=0.01, 분할=1):
        현금, 보유, 기록, 투입 = 초기, [], [], []
        보유코드 = {}
        하루이자 = (1 + 이자 / 100) ** (1 / 245) - 1
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            # ⚠️ 노는 현금에 이자를 붙인다 (E)
            if 하루이자:
                현금 *= (1 + 하루이자)
            남 = []
            for 청산i, 금, r, code in 보유:
                if 청산i <= i:
                    현금 += 금 * (1 + r / 100)
                    보유코드[code] = 보유코드.get(code, 0) - 1
                else:
                    남.append((청산i, 금, r, code))
            보유 = 남
            평가 = 현금 + sum(금 for _, 금, _, _ in 보유)
            오늘 = 날별.get(d) or []
            if 고르기:
                오늘 = [x for x in 오늘 if 고르기(x)]
            오늘 = sorted(오늘, key=lambda z: z["상대갭"])
            산것 = 0
            for x in 오늘:
                if 산것 >= 상한:
                    break
                # ⚠️ A 재진입 금지
                if 중복금지 and 보유코드.get(x["code"], 0) > 0:
                    continue
                # ⚠️ B 신호 강도별 비중 — 상대갭이 클수록 크게
                비 = 비중
                if 강도비중:
                    강 = min(3.0, max(1.0, abs(x["상대갭"]) / 3.0))
                    비 = min(0.34, 비중 * 강)
                쓸 = min(평가 * 비, x["대금"] * 유동)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                # ⚠️ C 분할 — 같은 금액을 나눠서 여러 날에 (여기선 첫날에 1/n만)
                쓸 = 쓸 / 분할
                현금 -= 쓸
                보유.append((min(x["i"] + x["며칠"], len(날) - 1), 쓸,
                            x["결과"], x["code"]))
                보유코드[x["code"]] = 보유코드.get(x["code"], 0) + 1
                산것 += 1
            기록.append((d, 평가))
            투입.append(sum(금 for _, 금, _, _ in 보유) / 평가 if 평가 > 0 else 0)
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
        print(f"    {이름:<34}{마지막:>14,.0f}원{연:>+8.2f}%{낙폭*100:>9.1f}%"
              f"{sum(투입)/max(1,len(투입))*100:>8.1f}%{f'{플}/{전}':>8}")
        return 연

    머 = (f"    {'전략':<34}{'끝 자산':>15}{'연평균':>8}{'최대낙폭':>9}"
          f"{'투입비':>8}{'연도별':>8}")

    print("  ══ 기준선 ══")
    print(머)
    시뮬("지금 규칙 (77·76·80차)")

    print("\n  ══ A **재진입** — 같은 종목 중복 보유를 막으면 ══")
    print("     ⚠️ 78차에서 위메이드플레이가 3번 나왔다 (6/08 · 6/24 · 6/29)")
    print(머)
    시뮬("중복 허용 (지금)")
    시뮬("**같은 종목 중복 금지**", 중복금지=True)
    중복 = {}
    for x in 사건:
        중복[x["code"]] = 중복.get(x["code"], 0) + 1
    많 = sorted(중복.items(), key=lambda z: -z[1])[:5]
    print(f"    (가장 자주 뜬 종목: "
          + " · ".join(f"{c}({n}회)" for c, n in 많) + ")")

    print("\n  ══ B **신호 강도별 비중** — 상대갭이 클수록 크게 사면 ══")
    print(머)
    시뮬("같은 비중 20% (지금)")
    시뮬("**강도별 비중** (상대갭 클수록↑)", 강도비중=True)
    시뮬("강도별 · 기본 15%", 비중=0.15, 강도비중=True)

    print("\n  ══ C **분할 매수** — 한 번에 vs 나눠서 ══")
    print("     ⚠️ 여기선 「같은 신호에 절반만 넣는다」로 단순화했다")
    print(머)
    시뮬("한 번에 (지금)")
    시뮬("절반만 (분할 2)", 분할=2)

    print("\n  ══ D **자금 규모별 한계** — 어디서 막히나 ══")
    print("     ⚠️ 「1억부터 막힌다」고 했는데 실제 시뮬은 안 했다")
    print(머)
    for 초 in (5_000_000, 30_000_000, 100_000_000, 300_000_000, 1_000_000_000):
        시뮬(f"초기 {초/10000:,.0f}만원", 초기=초)

    print("\n  ══ E **노는 자금에 이자를 붙이면** ══")
    print("     ⚠️ 지금까지 82%를 **무이자 현금**으로 뒀다")
    print(머)
    for r in (0.0, 2.0, 3.0, 3.5):
        시뮬(f"현금 이자 연 {r:.1f}%", 이자=r)

    print("\n  ══ G **외국인 순매도 회피** (68차 단서) ══")
    print("     ⚠️ 68차에서 크게 오른 것 +51 vs 크게 빠진 것 -300으로 유일하게 갈렸다")
    print(머)
    시뮬("전부 (지금)")
    시뮬("**외국인 순매도 종목 제외**", 고르기=lambda x: x["외국인"] >= 0)
    외값 = sorted(x["외국인"] for x in 사건)
    하위 = 외값[len(외값) // 4]
    시뮬(f"외국인 하위25%({하위:,.0f}) 제외",
         고르기=lambda x: x["외국인"] > 하위)
    시뮬("외국인 순매수만", 고르기=lambda x: x["외국인"] > 0)

    print("\n  ══ F **요일·월** — 계절성이 있나 ══")
    import datetime as dt2
    요일별, 월별 = {}, {}
    for x in 사건:
        try:
            w = dt2.datetime.strptime(x["날"], "%Y%m%d").weekday()
        except Exception:
            continue
        요일별.setdefault(w, []).append(x["결과"])
        월별.setdefault(x["날"][4:6], []).append(x["결과"])
    print(f"    {'요일':<10}{'건수':>7}{'평균':>10}{'승률':>8}")
    for w, 라 in enumerate(("월", "화", "수", "목", "금")):
        a = 요일별.get(w) or []
        if len(a) < 20:
            continue
        print(f"    {라:<10}{len(a):>7}{st.mean(a):>+9.2f}%"
              f"{sum(1 for z in a if z>0)/len(a)*100:>7.1f}%")
    print(f"\n    {'월':<10}{'건수':>7}{'평균':>10}{'승률':>8}")
    for m in sorted(월별):
        a = 월별[m]
        if len(a) < 15:
            continue
        print(f"    {m}월{'':<7}{len(a):>7}{st.mean(a):>+9.2f}%"
              f"{sum(1 for z in a if z>0)/len(a)*100:>7.1f}%")

    print("\n  ══ ⚠️ 2025·26 뺀 판으로 핵심만 다시 ══")
    print(머)
    시뮬("지금 규칙", 끝날="20241230")
    시뮬("+ 중복 금지", 중복금지=True, 끝날="20241230")
    시뮬("+ 강도별 비중", 강도비중=True, 끝날="20241230")
    시뮬("+ 외국인 순매도 제외", 고르기=lambda x: x["외국인"] >= 0,
         끝날="20241230")
    시뮬("+ 현금 이자 3%", 이자=3.0, 끝날="20241230")

    print("\n  읽는 법")
    print("    - 각 항목에서 **기준선보다 나은 것**만 채택한다")
    print("    - ⚠️ 2025·26 뺀 판에서도 나아야 한다 (오늘 세 번 뒤집혔다)")
    print("    - D에서 **자금이 커질수록 연평균이 떨어지는 지점**이 유동성 한계다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
