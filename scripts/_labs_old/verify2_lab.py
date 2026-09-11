#!/usr/bin/env python3
r"""
verify2_lab.py — **52차 최고 조합을 끝까지 검증 + 시뮬레이션** (2026-09-02 · 53차)

⚠️⚠️ **52차에서 오늘 최대 발견이 나왔다.**
```
시장 −0.3%↓ + 상대 −4%p↓ (볼하단 + 20일−10%↓ · 소형 기반)
  평균 **+21.09%** · 승률 **84.0%** · 연 76건 · **15해 중 15해 +** · 표본 1,271
  ⭐ 2026년(강세장)에도 **+37.18%, 승률 91.8%** — 국면을 안 탄다
```

## 오늘 다섯 번 무너졌다. 관문을 전부 건다
```
무너진 것          무너진 이유            여기서 거는 관문
수주계약 대형       업종 편중(조선·건설 58%)  → ① 종목 편중
계약금액 규모       기간 편중(2.6년)        → ② 연도별(52차에서 15/15 확인)
신호 3개 중첩      자본 시뮬              → ③ **사용자 규칙 시뮬레이션**
중형 신고가 93%    자본 시뮬              → ③
매일 상위 1개      조건 미달을 억지로 뽑음    → 조건 유지
                유동성 미확인            → ④ 유동성
```

## 재는 것
```
① 종목·업종 편중  상위 몇 종목이 몇 %인가
② 유동성        매수일 거래대금 분포
③ **시뮬레이션**  사용자 규칙(10만원씩 · 최소 1주) · 초기자금별 · 매도 시점별
④ 매도 시점      D+5·10·20·40·60
⑤ 손절          걸면 좋아지나 나빠지나
⑥ 두 등급 비교   최우선(상대−4%p) vs 매수권고(상대−2%p)
```
⚠️ 매수 다음날 시가 · 비용 0.26% · 수정주가.
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


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # 갭 + 원본가(주문용)
    갭표, 시장갭, 원가 = {}, {}, {}
    앞종 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루, 원 = {}, {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                저 = float(v.get("저가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            원[c] = (종, 시, 저)      # ⚠️ 원본. 수정 배율은 아래에서 따로 붙인다
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        원가[d8] = 원
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
    print(f"  거래일 {len(날):,}", flush=True)

    # 사건 수집
    사건 = []   # (i, 해, code, 상대갭, 시장갭, 거래대금)
    for i, d1 in enumerate(날):
        if i < 260 or i + 61 >= len(날):
            continue
        다음 = 날[i + 1]
        시갭 = 시장갭.get(다음)
        if 시갭 is None or 시갭 >= -0.3:
            continue                       # ⚠️ 시장이 −0.3% 넘게 낮게 출발한 날만
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
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
            if (c1 - s20) / (2 * sd) > -1.0:
                continue
            if k < 20 or sq[k - 20] <= 0 or (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -2:
                continue                   # 상대 −2%p 이하만 (등급은 아래서 나눔)
            사건.append((i, d1[:4], code, g - 시갭, 시갭, 대금))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len(날) / 245
    최우선 = [x for x in 사건 if x[3] <= -4]
    권고 = [x for x in 사건 if -4 < x[3] <= -2]
    print(f"  사건 {len(사건):,}건 · 최우선(상대−4%p↓) {len(최우선):,} "
          f"· 권고(−4~−2%p) {len(권고):,}", flush=True)

    def 성과(목록, 보유, 손절=None):
        """⚠️⚠️ **버그 수정(2026-09-02).** 처음에 **원본 가격**으로 계산했다.
        액면분할이 일어나면 원본 가격이 반토막 나는데 그걸 실제 손실로 셌다.
        → **수정주가**로 바꾼다. 손절 판정의 저가도 배율을 먹여 맞춘다."""
        out = []
        for (i, y, code, 상대, 시갭, 대금) in 목록:
            b = 원가.get(날[i + 1], {}).get(code)
            e = 주가.get(날[i + 1 + 보유], {}).get(code)
            수b = 주가.get(날[i + 1], {}).get(code)
            if not b or not e or not 수b or b[0] <= 0:
                continue
            배 = 수b[0] / b[0]              # 그날의 수정 배율
            매수 = b[1] * 배                 # 수정 시가
            if 매수 <= 0:
                continue
            팔 = None
            if 손절 is not None:
                선 = 매수 * (1 + 손절 / 100)
                for j in range(i + 1, i + 1 + 보유):
                    v = 원가.get(날[j], {}).get(code)
                    수v = 주가.get(날[j], {}).get(code)
                    if not v or not 수v or v[0] <= 0:
                        continue
                    배j = 수v[0] / v[0]
                    if j > i + 1 and v[1] * 배j <= 선:
                        팔 = v[1] * 배j
                        break
                    if v[2] * 배j <= 선:
                        팔 = 선
                        break
            if 팔 is None:
                팔 = e[0]                   # 수정 종가
            out.append((y, (팔 / 매수 - 1) * 100 - _비용))
        return out

    def 요약(목록, 이름, 보유=20, 손절=None):
        a = 성과(목록, 보유, 손절)
        if len(a) < 100:
            return None
        수 = [r for _, r in a]
        승 = sum(1 for x in 수 if x > 0) / len(수) * 100
        해별 = {}
        for y, r in a:
            해별.setdefault(y, []).append(r)
        전 = 플 = 0
        for y, arr in 해별.items():
            if len(arr) < 10:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        return (st.mean(수), 승, st.median(수), sorted(수)[len(수) // 4],
                len(수), len(수) / 년수, 플, 전)

    # ── ① 종목 편중 ──
    print(f"\n  ══ ①⚠️ 종목 편중 (최우선 등급) ══")
    종 = {}
    for (i, y, code, 상대, 시갭, 대금) in 최우선:
        종.setdefault(code, 0)
        종[code] += 1
    이름표 = {c: (기본.get(c) or {}).get("이름") or c for c in 종}
    전체 = len(최우선)
    상위 = sorted(종.items(), key=lambda x: -x[1])
    print(f"    서로 다른 종목 **{len(종):,}개** / 사건 {전체:,}건")
    for kk in (3, 5, 10, 20, 50):
        s = sum(v for _, v in 상위[:kk])
        print(f"      상위 {kk:>2}종목이 전체의 {s/전체*100:>5.1f}%")
    print("    건수 상위 8종목: " + " · ".join(
        f"{이름표[c][:10]}({v})" for c, v in 상위[:8]))

    # ── ② 유동성 ──
    print(f"\n  ══ ② 유동성 ══")
    for 라, 목록 in (("최우선", 최우선), ("권고", 권고)):
        대금들 = sorted(x[5] for x in 목록 if x[5] > 0)
        if len(대금들) < 50:
            continue
        n = len(대금들)
        작 = sum(1 for x in 대금들 if x < 1e8) / n * 100
        print(f"    {라:<8} 중앙값 {대금들[n//2]/1e8:>6.1f}억 · 하위25% "
              f"{대금들[n//4]/1e8:>5.1f}억 · 1억 미만 {작:>4.1f}%")

    # ── ⑥ 두 등급 × ④ 매도 시점 ──
    print(f"\n  ══ ④⑥ 등급 × 매도 시점 ══")
    print(f"    {'등급':<8}{'매도':<8}{'평균':>9}{'승률':>8}{'중앙값':>9}"
          f"{'하위25%':>10}{'연간':>8}{'연도별':>8}{'표본':>8}")
    for 라, 목록 in (("최우선", 최우선), ("권고", 권고), ("합계", 사건)):
        for 보유 in (5, 10, 20, 40, 60):
            r = 요약(목록, 라, 보유)
            if not r:
                continue
            m, 승, 중, 하25, n, 연, 플, 전 = r
            별 = "⭐" if (m > 0 and 승 >= 70 and 전 >= 10 and 플 / 전 >= 2 / 3) else "  "
            print(f"    {라:<8}{'D+'+str(보유):<8}{m:>+8.2f}%{승:>7.1f}%{중:>+8.2f}%"
                  f"{하25:>+9.2f}%{연:>7.0f}건{f'{플}/{전}':>8}{n:>8,}{별}")

    # ── ⑤ 손절 ──
    print(f"\n  ══ ⑤ 손절 (최우선 · D+20) ══")
    print(f"    {'손절':<10}{'평균':>9}{'승률':>8}{'중앙값':>9}{'하위25%':>10}")
    for 손 in (None, -5, -8, -12):
        r = 요약(최우선, "", 20, 손)
        if not r:
            continue
        m, 승, 중, 하25, n, 연, 플, 전 = r
        라 = "없음" if 손 is None else f"{손}%"
        print(f"    {라:<10}{m:>+8.2f}%{승:>7.1f}%{중:>+8.2f}%{하25:>+9.2f}%")

    # ── ③ 사용자 규칙 시뮬레이션 ──
    print(f"\n  ══ ③⭐ **사용자 규칙 시뮬레이션** (10만원씩 · 최소 1주 · 손절 없음) ══")
    뽑날 = {}
    for (i, y, code, 상대, 시갭, 대금) in 사건:
        뽑날.setdefault(i + 1, []).append((상대, 대금, code))
    for v in 뽑날.values():
        v.sort()          # 상대갭 낮은 것부터 (더 많이 빠진 것 우선)

    def 시뮬(초기, 하루최대, 보유일, 등급문턱):
        """⚠️⚠️⚠️ **버그 두 번 고쳤다 (2026-09-02).**
        1차: 원본 가격으로 평가 → 액면분할을 손실로 셌다 (초기 500만 → 26만원)
        2차: **주수는 원본 시가로, 금액은 수정 시가로** 계산했다 →
             원본 1,000원·수정 100,000원인 종목은 100주 × 10만 = **1,000만원**을 썼다.
             10만원어치 사려다 1,000만원을 쓴 것이다. 현금이 바닥나 매수가 298건뿐이었다.
        ⇒ **주수를 아예 쓰지 않는다.** 포지션을 (청산일, code, 투자금, 매수시_수정단가)로 담고
           매도금 = 투자금 × (수정단가_매도 / 수정단가_매수)로 굴린다.
           **수익률만으로 계산하니 배율 문제가 원천적으로 없다.**
        ⚠️ 「10만원씩」은 **원본 가격 기준 최소 1주**를 지키도록 투자금을 정한다."""
        현금 = float(초기)
        보유, 곡선 = [], []
        이긴 = 진 = 산 = 못 = 0
        for j2 in range(261, len(날)):
            원 = 원가.get(날[j2], {})
            수 = 주가.get(날[j2], {})
            남 = []
            for (끝j, code, 투자금, 수매수) in 보유:
                if j2 >= 끝j:
                    o, sv = 원.get(code), 수.get(code)
                    if o and sv and o[0] > 0:
                        수팔 = o[1] * (sv[0] / o[0])        # 수정 시가
                    else:
                        수팔 = 수매수
                    받 = 투자금 * (수팔 / 수매수) * (1 - _비용 / 2)
                    현금 += 받
                    이긴 += 1 if 수팔 > 수매수 else 0
                    진 += 1 if 수팔 <= 수매수 else 0
                else:
                    남.append((끝j, code, 투자금, 수매수))
            보유 = 남
            if j2 in 뽑날:
                든 = {c for (_, c, _, _) in 보유}
                오늘 = 0
                for 상대, 대금, code in 뽑날[j2]:
                    if 상대 > 등급문턱:
                        continue
                    if 오늘 >= 하루최대 or code in 든:
                        continue
                    o, sv = 원.get(code), 수.get(code)
                    if not o or not sv or o[1] <= 0 or o[0] <= 0:
                        continue
                    배 = sv[0] / o[0]
                    수매수 = o[1] * 배
                    # ⚠️ 「10만원씩, 최소 1주」 — **원본 가격**으로 주수를 정하고
                    #    그 주수 × 원본 시가를 투자금으로 본다 (실제로 나가는 돈)
                    주수 = max(1, int(100_000 // o[1]))
                    투자금 = 주수 * o[1] * (1 + _비용 / 2)
                    if 투자금 > 현금:
                        못 += 1
                        continue
                    현금 -= 투자금
                    보유.append((j2 + 보유일, code, 투자금, 수매수))
                    든.add(code)
                    산 += 1
                    오늘 += 1
            평가 = 0.0
            for (_, code, 투자금, 수매수) in 보유:
                o, sv = 원.get(code), 수.get(code)
                수now = (o[0] * (sv[0] / o[0])) if (o and sv and o[0] > 0) else 수매수
                평가 += 투자금 * (수now / 수매수)
            곡선.append(현금 + 평가)
        수끝, 원끝 = 주가.get(날[-1], {}), 원가.get(날[-1], {})
        for (_, code, 투자금, 수매수) in 보유:
            o, sv = 원끝.get(code), 수끝.get(code)
            수팔 = (o[0] * (sv[0] / o[0])) if (o and sv and o[0] > 0) else 수매수
            현금 += 투자금 * (수팔 / 수매수) * (1 - _비용 / 2)
        최고, 낙 = 곡선[0] if 곡선 else 1, 0.0
        for x in 곡선:
            최고 = max(최고, x)
            낙 = min(낙, x / 최고 - 1)
        거 = 이긴 + 진
        return 현금, 낙 * 100, (이긴 / 거 * 100 if 거 else 0), 산, 못, 곡선

    년 = (len(날) - 261) / 245
    있 = [d for d in 날[261:] if 지수.get(d)]
    지연 = ((지수[있[-1]]["KOSPI"] / 지수[있[0]]["KOSPI"]) ** (1 / 년) - 1) * 100
    print(f"     기간 {날[261][:4]}~{날[-1][:4]} ({년:.1f}년) · 코스피 연 {지연:+.1f}%")
    print(f"    {'등급':<8}{'초기자금':<11}{'하루':<6}{'매도':<7}{'최종자산':>14}"
          f"{'배수':>7}{'연환산':>9}{'낙폭':>8}{'매수':>7}{'승률':>7}{'못산':>7}")
    최선 = None
    for 라, 문턱 in (("최우선", -4), ("최우선+권고", -2)):
        for 초기 in (5_000_000, 10_000_000, 30_000_000):
            for 보유일 in (20, 40):
                자산, 낙, 승, 산, 못, 곡선 = 시뮬(초기, 5, 보유일, 문턱)
                배수 = 자산 / 초기
                연 = (배수 ** (1 / 년) - 1) * 100 if 배수 > 0 else -100
                표 = "⭐" if 연 > 지연 else "  "
                print(f"    {라:<8}{초기//10000:>8,}만{5:>4}개{'D+'+str(보유일):<7}"
                      f"{자산:>13,.0f}원{배수:>7.2f}{연:>8.1f}%{낙:>7.1f}%"
                      f"{산:>7,}{승:>6.0f}%{못:>7,}{표}")
                if 최선 is None or 연 > 최선[0]:
                    최선 = (연, 라, 초기, 보유일, 곡선)

    if 최선:
        print(f"\n  ══ 연도별 (「{최선[1]}」 · 초기 {최선[2]//10000:,}만 · D+{최선[3]}) ══")
        곡선 = 최선[4]
        해별, 앞v = {}, None
        for j, d in enumerate(날[261:261 + len(곡선)]):
            y = d[:4]
            if y not in 해별:
                해별[y] = [앞v if 앞v is not None else 곡선[j], 곡선[j]]
            해별[y][1] = 곡선[j]
            앞v = 곡선[j]
        지해, 앞x = {}, None
        for d in 날[261:]:
            x = (지수.get(d) or {}).get("KOSPI")
            if not x:
                continue
            y = d[:4]
            if y not in 지해:
                지해[y] = [앞x if 앞x else x, x]
            지해[y][1] = x
            앞x = x
        print(f"    {'해':<7}{'자산':>14}{'수익률':>10}{'코스피':>10}{'차이':>10}")
        플, 전 = 0, 0
        for y in sorted(해별):
            a0, a1 = 해별[y]
            수 = (a1 / a0 - 1) * 100 if a0 else 0
            지 = ((지해[y][1] / 지해[y][0] - 1) * 100) if y in 지해 and 지해[y][0] else 0
            전 += 1
            플 += 1 if 수 > 0 else 0
            표 = "⭐" if 수 > 지 else ("  " if 수 > 0 else "❌")
            print(f"    {y:<7}{a1:>13,.0f}원{수:>+9.1f}%{지:>+9.1f}%{수-지:>+9.1f}%{표}")
        print(f"    ⇒ **{전}해 중 {플}해 수익 ({플/전*100:.0f}%)**")

    print("\n  읽는 법")
    print("    - ①에서 상위 10종목이 30%를 넘으면 특정 종목에 몰린 것이다")
    print("    - ③이 최종 관문이다 — **브리핑 대로 샀을 때 실제로 돈이 되나**")
    print("    - '못산'이 많으면 자금이 모자라 기회를 놓친 것이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
