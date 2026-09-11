#!/usr/bin/env python3
r"""
verify_lab.py — **46차 최고 조합을 끝까지 검증한다** (2026-09-02 · 47차)

⚠️⚠️ **46차에서 오늘 최고의 결과가 나왔다.**
```
볼하단 + 갭−2%↓ + 20일−10%↓ · 소형
  절대 **+8.37%** · 승률 **66%** · 연 897건 · **16해 중 16해 +** · 표본 15,019
```

## 하지만 오늘 다섯 번 무너졌다. 이번엔 **처음부터 다 확인한다**
```
무너진 것          무너진 이유
신호 3개 중첩       자본 시뮬 (→ 이제 기각 관문 아님)
중형 신고가 93%     자본 시뮬 (→ 이제 기각 관문 아님)
**수주계약 대형**   **특정 업종 편중** — 조선·건설·방산이 58% · 2025년 한 해가 만듦
계약금액 규모       기간 편중 (2.6년 강세장)
매일 상위 1개       조건 미달인 걸 억지로 뽑음
```

## 그래서 여섯 가지를 잰다
```
① **종목·업종 편중**  상위 몇 종목이 몇 %인가 — 수주계약 때 이걸 놓쳤다
② 유동성            매수일 거래대금 분포. 소형주라 중요하다
③ **최악**          하위25% · 최악5% → 손절이 필요한가
④ 매도 시점         D+5 · 10 · 20 · 40 · 60 중 어디가 좋은가
⑤ 시가 vs 종가 매수  브리핑 사용자는 아침에 산다
⑥ 연도별 상세       16/16이 정말인지 건수까지 본다
```
⚠️ 판정: 절대 수익 · 승률 · 연도별. 코스피 대비는 참고. 왕복비용 0.26%.
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
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


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
            except (TypeError, ValueError):
                시총 = 대금 = 0.0
            하루[c] = (종, 시, 저, 등, 시총, 대금)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 저, 등, 시총, 대금) in 원[d].items():
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
            하루[c] = (수, 시 * 배, 저 * 배, 시총, 대금)
        out[d] = 하루
    return out


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    ixv, 앞x = [], None
    for d in 날:
        x = (지수.get(d) or {}).get("KOSPI") or 앞x
        if x:
            앞x = x
        ixv.append(x)
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    # 46차 최고 조합: 볼하단 + 갭−2%↓ + 20일−10%↓
    최대보유 = 60
    사건 = []      # (i, code, 크기, 대금, 갭)
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + 최대보유 >= len(날):
            continue
        for code, v in 주가[d1].items():
            c1, _시, _저, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
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
            if (c1 - s20) / (2 * sd) > -1.0:           # 볼린저 하단
                continue
            if k < 20 or sq[k - 20] <= 0 or (c1 / sq[k - 20] - 1) * 100 > -10:
                continue                                # 최근 20일 −10%↓
            나 = 주가[날[i + 1]].get(code)
            if not 나 or 나[1] <= 0:
                continue
            갭 = (나[1] / c1 - 1) * 100
            if 갭 > -2:                                 # 갭 −2%↓
                continue
            사건.append((i, code, _크기(시총), 나[4], 갭))
    print(f"  조합 사건 {len(사건):,}건 · 연 {len(사건)/(len(날)/245):.0f}건", flush=True)

    def 성과(목록, 보유, 진입="시가", 손절=None):
        out, 하 = [], []
        for (i, code, g, 대금, 갭) in 목록:
            나 = 주가[날[i + 1]].get(code)
            끝 = 주가[날[i + 1 + 보유]].get(code)
            if not 나 or not 끝:
                continue
            매수 = 나[1] if 진입 == "시가" else 나[0]
            if 매수 <= 0:
                continue
            팔 = None
            if 손절 is not None:
                선 = 매수 * (1 + 손절 / 100)
                for j in range(i + 1, i + 1 + 보유):
                    v = 주가[날[j]].get(code)
                    if not v:
                        continue
                    if j > i + 1 and v[1] <= 선:
                        팔 = v[1]
                        break
                    if v[2] <= 선:
                        팔 = 선
                        break
            if 팔 is None:
                팔 = 끝[0]
            r = (팔 / 매수 - 1) * 100 - _비용
            out.append(r)
            하.append(r - ((ixv[i + 1 + 보유] / ixv[i + 1] - 1) * 100
                           if (ixv[i + 1] and ixv[i + 1 + 보유]) else 0))
        return out, 하

    소형 = [x for x in 사건 if x[2] == "소형"]

    # ── ① 종목·업종 편중 ──
    print(f"\n  ══ ①⚠️ **종목 편중** — 수주계약 때 이걸 놓쳤다 ══")
    종 = {}
    for (i, code, g, 대금, 갭) in 소형:
        종.setdefault(code, []).append(i)
    이름표 = {c: (기본.get(c) or {}).get("이름") or c for c in 종}
    전체 = len(소형)
    상위 = sorted(종.items(), key=lambda x: -len(x[1]))
    print(f"    서로 다른 종목 **{len(종):,}개** / 사건 {전체:,}건")
    for k in (3, 5, 10, 20, 50):
        s = sum(len(v) for _, v in 상위[:k])
        print(f"      상위 {k:>2}종목이 전체의 {s/전체*100:>5.1f}%")
    print("    건수 상위 10종목:")
    for c, v in 상위[:10]:
        a, _ = 성과([x for x in 소형 if x[1] == c], 20)
        승 = (sum(1 for x in a if x > 0) / len(a) * 100) if a else 0
        print(f"      {이름표[c][:16]:<18}{len(v):>5}건 {len(v)/전체*100:>5.1f}%"
              f"  평균 {(st.mean(a) if a else 0):>+7.2f}%  승률 {승:>3.0f}%")

    # ── ② 유동성 ──
    print(f"\n  ══ ② 유동성 — 실제로 살 수 있나 (매수일 거래대금) ══")
    대금들 = sorted(x[3] for x in 소형 if x[3] > 0)
    if 대금들:
        n = len(대금들)
        작1 = sum(1 for x in 대금들 if x < 1e8) / n * 100
        작5 = sum(1 for x in 대금들 if x < 5e8) / n * 100
        print(f"    중앙값 {대금들[n//2]/1e8:.1f}억 · 하위25% {대금들[n//4]/1e8:.1f}억 "
              f"· 하위10% {대금들[n//10]/1e8:.1f}억")
        print(f"    1억 미만 {작1:.1f}% · 5억 미만 {작5:.1f}%  "
              + ("⭐ 살 수 있다" if 작1 < 5 else "⚠️ 못 사는 게 섞인다"))

    # ── ③ 최악 · 손절 ──
    print(f"\n  ══ ③ **최악** — 손절이 필요한가 (D+20) ══")
    print(f"    {'손절':<10}{'평균':>9}{'승률':>8}{'중앙값':>9}{'하위25%':>10}"
          f"{'최악5%':>10}{'표본':>9}")
    for 손 in (None, -5, -8, -12, -15):
        a, _ = 성과(소형, 20, 손절=손)
        if len(a) < 500:
            continue
        a2 = sorted(a)
        n = len(a2)
        승 = sum(1 for x in a2 if x > 0) / n * 100
        라 = "없음" if 손 is None else f"{손}%"
        print(f"    {라:<10}{st.mean(a2):>+8.2f}%{승:>7.1f}%{st.median(a2):>+8.2f}%"
              f"{a2[n//4]:>+9.2f}%{a2[n//20]:>+9.2f}%{n:>9,}")

    # ── ④ 매도 시점 ──
    print(f"\n  ══ ④ 매도 시점 — 며칠 들고 있나 ══")
    print(f"    {'보유':<10}{'절대':>9}{'승률':>8}{'코스피대비':>11}{'표본':>9}")
    for 보유 in (5, 10, 20, 40, 60):
        a, 대 = 성과(소형, 보유)
        if len(a) < 500:
            continue
        승 = sum(1 for x in a if x > 0) / len(a) * 100
        print(f"    {str(보유)+'일':<10}{st.mean(a):>+8.2f}%{승:>7.1f}%"
              f"{st.mean(대):>+10.2f}%{len(a):>9,}")

    # ── ⑤ 시가 vs 종가 ──
    print(f"\n  ══ ⑤ 매수 시점 — 아침(시가) vs 장 마감(종가) · D+20 ══")
    for 진입 in ("시가", "종가"):
        a, 대 = 성과(소형, 20, 진입=진입)
        승 = sum(1 for x in a if x > 0) / len(a) * 100
        라 = "다음날 시가(아침)" if 진입 == "시가" else "다음날 종가"
        print(f"    {라:<18}{st.mean(a):>+8.2f}%  승률 {승:>4.1f}%  "
              f"코스피대비 {st.mean(대):>+6.2f}%  표본 {len(a):,}")

    # ── ⑥ 연도별 상세 ──
    print(f"\n  ══ ⑥ 연도별 상세 (D+20 · 시가 매수) ══")
    해별 = {}
    for x in 소형:
        해별.setdefault(날[x[0]][:4], []).append(x)
    print(f"    {'해':<7}{'건수':>7}{'절대':>10}{'승률':>8}{'코스피대비':>11}")
    플, 전 = 0, 0
    for y in sorted(해별):
        a, 대 = 성과(해별[y], 20)
        if len(a) < 15:
            print(f"    {y:<7}{len(해별[y]):>7}{'표본부족':>10}")
            continue
        승 = sum(1 for x in a if x > 0) / len(a) * 100
        전 += 1
        플 += 1 if st.mean(a) > 0 else 0
        표 = "⭐" if st.mean(a) > 0 else "❌"
        print(f"    {y:<7}{len(a):>7}{st.mean(a):>+9.2f}%{승:>7.1f}%"
              f"{st.mean(대):>+10.2f}%{표}")
    if 전:
        print(f"    ⇒ **{전}해 중 {플}해 + ({플/전*100:.0f}%)**")

    print("\n  읽는 법")
    print("    - ①에서 상위 10종목이 30%를 넘으면 **특정 종목에 몰린 것**이다(수주계약이 58%였다)")
    print("    - ②에서 1억 미만이 5%를 넘으면 **못 사는 게 섞인다**")
    print("    - ③에서 손절이 최악을 크게 줄이면서 평균을 조금만 깎으면 **쓸 값어치가 있다**")
    print("    - ⑤에서 시가가 종가보다 나쁘면 **아침에 사는 게 불리하다**(39차와 반대 방향)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
