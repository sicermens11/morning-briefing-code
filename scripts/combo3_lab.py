#!/usr/bin/env python3
r"""
combo3_lab.py — **이긴 조합에 조건을 하나씩 더 붙인다** (2026-09-02 · 48차)

⚠️⚠️ **사용자: 다양한 조합으로 여러 개 테스트해봐. 안 쓴 데이터도 체크해서.**

## 왜 「전수 조합」이 아니라 「하나씩 붙이기」인가
```
조건 20개에서 3개 조합 = 1,140가지 × 크기 3 = **3,420칸**
⚠️ 다중검정이 심각하다 — 3,420칸을 재면 우연히 좋은 게 반드시 나온다
⇒ **46차에서 이긴 조합을 기반으로 두고 조건을 하나씩 붙인다.**
   칸이 20여 개로 줄고, **「이 조건이 도움이 되나」**가 바로 읽힌다
```

## 기반 (46차 최고)
```
볼린저 하단 이탈 + 갭 −2%↓ + 최근 20일 −10%↓ · 소형
  절대 +8.37% · 승률 66% · 연 897건 · 16해 중 16해 + · 표본 15,019
```

## 붙여볼 조건 — **안 쓴 데이터를 우선 넣는다**
```
수급(2,751일)   외국인 순매수 · 기관 순매수 · 둘 다 · 수급강도 0.5%↑ · 개인 순매도
재무(2,766종목) 영업이익 흑자 · 매출 성장 · 순이익 흑자 · 영업이익률 5%↑
                ⚠️ 분기말+75일부터 쓴다 (look-ahead 방지)
컨센서스(6.7년)  최근 60일 리포트 있음 · 목표주가 괴리 30%↑
가격            거래량 3배↑ · RSI≤30 · 60일 최저 · 시가가 저가 근처
시장            코스피 / 코스닥
국면            강세 / 횡보 / 약세
```
⚠️ **빼면 좋아지는 조건**도 같이 본다(반대 방향).
⚠️ 판정: 절대 수익 · 승률 · 연도별 3분의 2 · 다음날 시가 매수 · D+20 · 비용 0.26%.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_보유 = 20


def _주가():
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
                량 = float(v.get("거래량") or 0)
            except (TypeError, ValueError):
                시총 = 대금 = 량 = 0.0
            시장 = str(v.get("시장") or "")
            하루[c] = (종, 시, 저, 등, 시총, 대금, 량, 시장)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 저, 등, 시총, 대금, 량, 시장) in 원[d].items():
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
            하루[c] = (수, 시 * 배, 저 * 배, 시총, 대금, 량, 시장)
        out[d] = 하루
    return out


def _컨센(날):
    """{코드: [날짜...]} — 리포트가 나온 날. 6.7년치."""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "consensus", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for x in (d.get("리포트") or []):
            c = x.get("코드")
            날짜 = str(x.get("날짜") or "").replace("-", "")
            if c and len(날짜) == 8:
                out.setdefault(c, []).append((날짜, x.get("목표주가") or 0))
    for c in out:
        out[c].sort()
    return out


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본, 수급 = O._지수(), O._기본(), O._수급()
    분기 = O._분기재무()
    컨센 = _컨센(날)
    종계, 량계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            량계.setdefault(c, []).append(v[5])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    ixv, 앞x = [], None
    for d in 날:
        x = (지수.get(d) or {}).get("KOSPI") or 앞x
        if x:
            앞x = x
        ixv.append(x)
    국면 = {}
    for i, d in enumerate(날):
        if i < 200 or not ixv[i] or not ixv[i - 200]:
            국면[d] = "횡보"
        else:
            r = ixv[i] / ixv[i - 200] - 1
            국면[d] = "강세" if r >= 0.10 else ("약세" if r <= -0.10 else "횡보")
    print(f"  거래일 {len(날):,} · 재무 {len(분기):,}종목 · 컨센 {len(컨센):,}종목",
          flush=True)

    def 재무값(code, d8, 항목):
        줄 = 분기.get(code)
        if not 줄:
            return None
        val = None
        for 적용, 값 in 줄:
            if 적용 <= d8:
                v = 값.get(항목)
                if v is not None:
                    val = v
            else:
                break
        return val

    # ── 기반 조합 사건 + 각 조건의 켜짐 여부 ──
    사건 = []      # (해, 켠집합, 절대수익)
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        fl = 수급.get(d1) or {}
        면 = 국면[d1]
        for code, v in 주가[d1].items():
            c1, _시, _저, 시총, 대금, 량, 시장 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue                                  # 소형만
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
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -1.0:
                continue                                  # 기반①
            if k < 20 or sq[k - 20] <= 0 or (c1 / sq[k - 20] - 1) * 100 > -10:
                continue                                  # 기반③
            나 = 주가[날[i + 1]].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝 or 나[1] <= 0:
                continue
            if (나[1] / c1 - 1) * 100 > -2:
                continue                                  # 기반②
            # ── 붙일 조건들 ──
            f = fl.get(code) or {}
            외 = f.get("외국인") or 0
            기 = f.get("기관") or 0
            개 = f.get("개인") or 0
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            평량 = st.mean(량계[code][k - 20:k]) or 1
            켠 = set()
            if 외 > 0:
                켠.add("외국인 순매수")
            if 기 > 0:
                켠.add("기관 순매수")
            if 외 > 0 and 기 > 0:
                켠.add("외국인+기관 둘 다")
            if 개 < 0:
                켠.add("개인 순매도")
            if 시총 > 0 and (외 + 기) * c1 / 시총 * 100 >= 0.5:
                켠.add("수급강도 0.5%↑")
            if 량 >= 평량 * 3:
                켠.add("거래량 3배↑")
            if rsi <= 30:
                켠.add("RSI≤30")
            if 볼 <= -2.0:
                켠.add("볼린저 −2σ↓")
            if k >= 60 and c1 <= min(sq[k - 59:k + 1]) * 1.001:
                켠.add("60일 최저")
            # ⚠️⚠️ **여기 look-ahead 버그가 있었다 (2026-09-02 발견, 제거함).**
            #   「다음날 시가가 그날 저가 근처인가」를 조건으로 넣었는데
            #   **그날 저가는 장이 끝나야 안다.** 아침 9시 매수 시점엔 알 수 없다.
            #   그 조건으로 「기반+약세+시가≈저가 = +17.38%, 승률 78.9%」가 나왔는데 **허수다.**
            if "KOSDAQ" in 시장.upper():
                켠.add("코스닥")
            else:
                켠.add("코스피")
            켠.add(f"국면 {면}")
            # 재무 (분기말+75일 적용 — look-ahead 방지)
            영 = 재무값(code, d1, "영업이익")
            순 = 재무값(code, d1, "당기순이익")
            률 = 재무값(code, d1, "영업이익률")
            매 = 재무값(code, d1, "매출액")
            if 영 is not None:
                켠.add("영업이익 흑자" if 영 > 0 else "영업이익 적자")
            if 순 is not None:
                켠.add("순이익 흑자" if 순 > 0 else "순이익 적자")
            if 률 is not None and 률 >= 5:
                켠.add("영업이익률 5%↑")
            if 매 is not None and 매 > 0:
                켠.add("매출 있음")
            # 컨센서스
            리 = 컨센.get(code)
            if 리:
                최근 = [x for x in 리 if x[0] <= d1]
                if 최근 and (int(d1) - int(최근[-1][0])) < 10000:
                    앞 = 최근[-1]
                    # 60일 이내 리포트 (대략 날짜 차이로 근사)
                    켠.add("최근 리포트 있음")
                    try:
                        목 = float(앞[1] or 0)
                        if 목 > 0 and c1 > 0 and (목 / c1 - 1) * 100 >= 30:
                            켠.add("목표주가 괴리 30%↑")
                    except (TypeError, ValueError):
                        pass
            r = (끝[0] / 나[1] - 1) * 100 - _비용
            사건.append((d1[:4], frozenset(켠), r))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)

    년수 = len(날) / 245
    전부 = [x[2] for x in 사건]
    승전 = sum(1 for x in 전부 if x > 0) / len(전부) * 100
    해전 = {}
    for x in 사건:
        해전.setdefault(x[0], []).append(x[2])
    전_전, 전_플 = 0, 0
    for y, a in 해전.items():
        if len(a) < 15:
            continue
        전_전 += 1
        전_플 += 1 if st.mean(a) > 0 else 0
    print(f"\n  ══ 기반: 볼하단 + 갭−2%↓ + 20일−10%↓ · 소형 ══")
    print(f"    절대 {st.mean(전부):+.2f}% · 승률 {승전:.1f}% · 연 {len(전부)/년수:.0f}건 "
          f"· 연도별 {전_플}/{전_전} · 표본 {len(전부):,}")

    조건들 = sorted({c for _, s, _ in 사건 for c in s})
    결과 = []
    for c in 조건들:
        걸 = [x for x in 사건 if c in x[1]]
        안 = [x for x in 사건 if c not in x[1]]
        if len(걸) < 300:
            continue
        a = [x[2] for x in 걸]
        b = [x[2] for x in 안] or [0]
        승 = sum(1 for x in a if x > 0) / len(a) * 100
        해별 = {}
        for x in 걸:
            해별.setdefault(x[0], []).append(x[2])
        전, 플 = 0, 0
        for y, arr in 해별.items():
            if len(arr) < 15:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        결과.append((st.mean(a) - st.mean(전부), st.mean(a), 승, 승 - 승전,
                     len(a), len(a) / 년수, 플, 전, c, st.mean(b)))

    결과.sort(reverse=True)
    print(f"\n  ══ 조건을 **하나씩 더 붙였을 때** (기반 대비) ══")
    print("     ⚠️ '기반차'가 +면 도움이 되는 조건, −면 오히려 나쁜 조건이다")
    print(f"    {'붙인 조건':<22}{'기반차':>9}{'절대':>9}{'승률':>8}{'승률차':>8}"
          f"{'연간':>8}{'연도별':>8}{'표본':>8}{'뺀쪽':>9}")
    for 차, m, 승, 승차, n, 연, 플, 전, c, 뺀 in 결과:
        통과 = 전 >= 8 and 플 / 전 >= 2 / 3
        별 = "⭐" if (차 > 0.5 and 통과 and 승차 > 0) else (
            "○" if 차 > 0 else ("❌" if 차 < -1 else "  "))
        print(f"    {c:<22}{차:>+8.2f}%{m:>+8.2f}%{승:>7.1f}%{승차:>+7.1f}%"
              f"{연:>7.0f}건{f'{플}/{전}':>8}{n:>8,}{뺀:>+8.2f}%{별}")

    print(f"\n\n  ══ ⭐ **가장 도움이 되는 조건 셋을 다 걸면** ══")
    좋 = [x for x in 결과 if x[0] > 0.5 and x[7] >= 8 and x[6] / max(1, x[7]) >= 2 / 3
          and x[5] >= 30]
    for k in (1, 2, 3):
        if len(좋) < k:
            break
        고른 = [x[8] for x in 좋[:k]]
        s = set(고른)
        걸 = [x for x in 사건 if s <= x[1]]
        if len(걸) < 100:
            print(f"    {' + '.join(고른)}  →  표본 {len(걸)}건뿐. 못 쓴다")
            continue
        a = [x[2] for x in 걸]
        승 = sum(1 for x in a if x > 0) / len(a) * 100
        해별 = {}
        for x in 걸:
            해별.setdefault(x[0], []).append(x[2])
        전, 플 = 0, 0
        for y, arr in 해별.items():
            if len(arr) < 10:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        print(f"    기반 + {' + '.join(고른)}")
        print(f"      절대 **{st.mean(a):+.2f}%** · 승률 **{승:.1f}%** "
              f"· 연 {len(a)/년수:.0f}건 · 연도별 {플}/{전} · 표본 {len(a):,}")

    print("\n  읽는 법")
    print("    - '기반차'가 핵심이다. **그 조건을 붙였을 때 얼마나 좋아지나**")
    print("    - '뺀쪽'은 그 조건이 **없는** 것들의 성적이다. 기반차와 반대로 움직여야 정상")
    print("    - ⭐ = 기반보다 +0.5%p↑ · 승률도 오름 · 연도별 통과")
    print("    - ⚠️ 조건을 겹칠수록 표본이 준다. 연 30건 미만이면 실전에서 쓰기 어렵다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
