#!/usr/bin/env python3
r"""
boll_lab.py — **볼린저 하단 계열을 끝까지 검증한다** (2026-09-02 · 42차)

⚠️⚠️ **오늘 가장 강한 후보다.** 41차에서 나왔다:
```
볼린저 하단 이탈 · 소형 · 다음날 **갭 −2% 이하**로 출발
  D+20 코스피 대비 **+4.55%** · 승률 **61%** · 표본 9,000건 · 16.7년
```
방금 무너진 수주계약(2025년 사이클)과 달리 **기간 편중이 없고 공시와 무관**하다.
하지만 오늘 네 번 당했다 — **검증 안 하면 또 무너진다.**

## 오늘 무너진 넷과 그 이유
```
신호 3개 중첩(14차)      t=4.2~9.2였는데 **자본 시뮬에서 코스피에 짐**
중형 신고가 워크포워드(30차) 승률 93%였는데 **자본 시뮬 검증구간 −5.5%p**
수주계약 대형(37·38·40차) 표본 99.4%가 2024~2026 · **2025년 한 해가 만든 것**
계약금액 규모(40차)       시장 대비 +9.1%p인데 **2.6년 강세장 구간뿐**
```

## 그래서 이번엔 **세 관문을 한 번에** 통과시킨다
```
① **연도별** — 17해 중 몇 해가 +인가. 문턱 **3분의 2(12해)**
   ⚠️ 오늘 두 번 당한 함정이다 (20차 2020년 · 방금 2025년)
② **유동성** — 갭 −2% 하락한 날 실제로 살 수 있었나
   매수일 거래대금 분포를 찍는다. 소형주라 이게 중요하다
③ **자본 시뮬** — 21차 교훈. 개별 거래가 좋아도 돈이 안 늘 수 있다
```
⚠️ 판정은 **코스피 뺀 값 + 승률 + 연도별**. 왕복비용 0.26%.
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
갭칸 = [("갭 −5%↓", -99, -5), ("갭 −5~−2%", -5, -2), ("갭 −2~0%", -2, 0),
        ("갭 0~2%", 0, 2), ("갭 2%↑", 2, 99)]


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
                고 = float(v.get("고가") or 0) or 종
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
            하루[c] = (종, 시, 고, 저, 등, 시총, 대금)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 고, 저, 등, 시총, 대금) in 원[d].items():
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
            하루[c] = (수, 시 * 배, 고 * 배, 저 * 배, 시총, 대금)
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

    # 사건: 볼린저 하단 **이탈 첫날**
    사건 = []       # (i, code, 크기, 갭%, 매수일 거래대금)
    앞상태 = {}
    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + 60 >= len(날):
            앞상태 = {}
            continue
        오늘 = {}
        for code, v in 주가[d1].items():
            c1, _시, _고, _저, 시총, 대금 = v
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
            볼하 = (c1 - s20) / (2 * sd) <= -1.0
            오늘[code] = 볼하
            앞 = 앞상태.get(code)
            if 앞 is None or not (볼하 and not 앞):
                continue
            나 = 주가[날[i + 1]].get(code)
            if not 나 or 나[1] <= 0 or c1 <= 0:
                continue
            갭 = (나[1] / c1 - 1) * 100
            사건.append((i, code, _크기(시총), 갭, 나[5]))
        앞상태 = 오늘
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일", flush=True)
    print(f"  볼린저 하단 이탈 첫날 {len(사건):,}건", flush=True)

    def 성과(목록, 보유, 진입="시가"):
        절, 대 = [], []
        for (i, code, g, 갭, 대금) in 목록:
            나 = 주가[날[i + 1]].get(code)
            끝 = 주가[날[i + 1 + 보유]].get(code)
            if not 나 or not 끝:
                continue
            매수 = 나[1] if 진입 == "시가" else 나[0]
            if 매수 <= 0:
                continue
            r = (끝[0] / 매수 - 1) * 100 - _비용
            절.append(r)
            if ixv[i + 1] and ixv[i + 1 + 보유]:
                대.append(r - (ixv[i + 1 + 보유] / ixv[i + 1] - 1) * 100)
        return 절, 대

    print(f"\n  ══ ① 갭 × 크기 (다음날 시가 매수 · D+20) ══")
    print(f"    {'갭 구간':<12}" + "".join(f"{g:>24}" for g, _, _ in 크기표))
    최고들 = []
    for 라벨, lo, hi in 갭칸:
        줄 = []
        for g, _, _ in 크기표:
            목록 = [x for x in 사건 if x[2] == g and lo <= x[3] < hi]
            if len(목록) < 500:
                줄.append("-")
                continue
            절, 대 = 성과(목록, 20)
            if len(절) < 400:
                줄.append("-")
                continue
            승 = sum(1 for x in 절 if x > 0) / len(절) * 100
            md = st.mean(대) if 대 else 0
            줄.append(f"{md:+.2f}({승:.0f}%) {len(절):,}")
            if md > 0.5 and 승 >= 52:
                최고들.append((라벨, lo, hi, g, md, 승, len(절)))
        print(f"    {라벨:<12}" + "".join(f"{x:>24}" for x in 줄))

    if not 최고들:
        print("\n  ❌ 문턱(코스피 대비 +0.5%p · 승률 52%)을 넘는 칸이 없다")
        최고들 = [("갭 −5~−2%", -5, -2, "소형", 0, 0, 0)]

    print(f"\n\n  ══ ②⭐ **연도별** — 오늘 두 번 당한 함정이다 ══")
    print("     ⚠️ 문턱: 17해 중 **3분의 2(12해)** 이상이 +여야 한다")
    해들 = sorted({날[x[0]][:4] for x in 사건})
    for 라벨, lo, hi, g, md, 승, n in 최고들[:4]:
        목록전 = [x for x in 사건 if x[2] == g and lo <= x[3] < hi]
        print(f"\n  ── {라벨} · {g} (전체 {len(목록전):,}건 · 코스피 대비 {md:+.2f}% 승률 {승:.0f}%) ──")
        칸, 플, 전 = [], 0, 0
        for y in 해들:
            목록 = [x for x in 목록전 if 날[x[0]][:4] == y]
            if len(목록) < 30:
                칸.append((y, None, None, len(목록)))
                continue
            절, 대 = 성과(목록, 20)
            if len(대) < 30:
                칸.append((y, None, None, len(목록)))
                continue
            m = st.mean(대)
            w = sum(1 for x in 절 if x > 0) / len(절) * 100
            칸.append((y, m, w, len(목록)))
            전 += 1
            플 += 1 if m > 0 else 0
        print(f"    {'해':<7}" + "".join(f"{y[2:]:>8}" for y, _, _, _ in 칸))
        print(f"    {'초과':<7}" + "".join(
            (f"{m:>+8.1f}" if m is not None else f"{'-':>8}") for _, m, _, _ in 칸))
        print(f"    {'승률':<7}" + "".join(
            (f"{w:>7.0f}%" if w is not None else f"{'-':>8}") for _, _, w, _ in 칸))
        print(f"    {'건수':<7}" + "".join(f"{n2:>8}" for _, _, _, n2 in 칸))
        if 전:
            판 = "⭐ 문턱 통과" if 플 / 전 >= 2 / 3 else "❌ 문턱 미달 — **채택 못 한다**"
            print(f"    ⇒ **{전}해 중 {플}해 + ({플/전*100:.0f}%)**  {판}")

    print(f"\n\n  ══ ③ 유동성 — 갭 하락한 날 실제로 살 수 있었나 ══")
    print("     ⚠️ 소형주라 이게 중요하다. 거래대금이 작으면 원하는 만큼 못 산다")
    print(f"    {'구간':<20}{'중앙값 거래대금':>16}{'하위25%':>14}{'1억 미만':>10}{'표본':>9}")
    for 라벨, lo, hi, g, md, 승, n in 최고들[:4]:
        목록 = [x for x in 사건 if x[2] == g and lo <= x[3] < hi]
        대금들 = sorted(x[4] for x in 목록 if x[4] > 0)
        if len(대금들) < 100:
            continue
        작 = sum(1 for x in 대금들 if x < 1e8) / len(대금들) * 100
        print(f"    {(라벨 + ' ' + g):<20}{대금들[len(대금들)//2]/1e8:>14.1f}억"
              f"{대금들[len(대금들)//4]/1e8:>12.1f}억{작:>9.1f}%{len(대금들):>9,}")

    print(f"\n\n  ══ ④ 자본 시뮬 — 개별 거래가 좋아도 돈이 안 늘 수 있다 (21차) ══")
    최 = 최고들[0]
    라벨, lo, hi, g = 최[0], 최[1], 최[2], 최[3]
    뽑날 = {}
    for (i, code, gg, 갭, 대금) in 사건:
        if gg == g and lo <= 갭 < hi:
            뽑날.setdefault(i, []).append((대금, code))
    for v in 뽑날.values():
        v.sort(reverse=True)
    경계i = next(i for i, d in enumerate(날) if d >= "20180101")

    def 굴리기(자리수, 보유, a, b):
        현금 = 1.0
        보유목록 = []
        곡선, 이긴, 진 = [], 0, 0
        for i in range(a, len(날)):
            s1 = 주가[날[i]]
            남 = []
            for (끝i, code, 매수가, 주수) in 보유목록:
                if i >= 끝i:
                    v = s1.get(code)
                    팔 = v[0] if v else 매수가
                    현금 += 주수 * 팔 * (1 - _비용 / 200)
                    이긴 += 1 if 팔 > 매수가 else 0
                    진 += 1 if 팔 <= 매수가 else 0
                else:
                    남.append((끝i, code, 매수가, 주수))
            보유목록 = 남
            평가 = sum(주수 * ((s1.get(code) or (매수가,))[0])
                       for (_, code, 매수가, 주수) in 보유목록)
            총 = 현금 + 평가
            if i < b and 총 > 0 and i in 뽑날:
                든 = {c for (_, c, _, _) in 보유목록}
                빈 = 자리수 - len(든)
                for _대금, code in 뽑날[i][:max(0, 빈)]:
                    if code in 든:
                        continue
                    나 = 주가[날[i + 1]].get(code) if i + 1 < len(날) else None
                    if not 나 or 나[1] <= 0:
                        continue
                    몫 = min(총 / 자리수, 현금)
                    if 몫 <= 1e-9:
                        break
                    보유목록.append((i + 1 + 보유, code, 나[1],
                                    몫 * (1 - _비용 / 200) / 나[1]))
                    현금 -= 몫
                    든.add(code)
            곡선.append(max(총, 0.0))
            if i >= b and not 보유목록:
                break
        마 = min(b, len(날)) - 1
        s1 = 주가[날[마]]
        for (_, code, 매수가, 주수) in 보유목록:
            v = s1.get(code)
            현금 += 주수 * ((v[0] if v else 매수가)) * (1 - _비용 / 200)
        최고, 낙 = 1.0, 0.0
        for x in 곡선:
            최고 = max(최고, x)
            낙 = min(낙, x / 최고 - 1)
        거 = 이긴 + 진
        return 현금, 낙 * 100, 거, (이긴 / 거 * 100 if 거 else 0)

    print(f"    대상: {라벨} · {g} · 거래대금 큰 것부터")
    for 이름, a, b in (("학습 2010~2017", 250, 경계i),
                       ("검증 2018~2026", 경계i, len(날))):
        있 = [d for d in 날[a:b] if 지수.get(d)]
        배 = 지수[있[-1]]["KOSPI"] / 지수[있[0]]["KOSPI"]
        년 = (b - a) / 245
        지연 = (배 ** (1 / 년) - 1) * 100
        print(f"\n    ── {이름} (코스피 연 {지연:+.1f}%) ──")
        print(f"      {'자리':<8}{'보유':<8}{'배수':>9}{'연환산':>9}{'낙폭':>8}"
              f"{'거래':>7}{'승률':>7}{'코스피대비':>11}")
        for 자리수 in (10, 20):
            for 보유 in (20, 60):
                자산, 낙, 거, 승 = 굴리기(자리수, 보유, a, b)
                연 = (자산 ** (1 / 년) - 1) * 100 if 자산 > 0 else -100
                표 = "⭐" if 연 > 지연 else "  "
                print(f"      {자리수:<8}{str(보유)+'일':<8}{자산:>9.3f}{연:>8.1f}%"
                      f"{낙:>7.1f}%{거:>7}{승:>6.0f}%{연-지연:>+10.1f}%{표}")

    print("\n  읽는 법")
    print("    - ②에서 **17해 중 12해 이상**이 +여야 채택한다. 아니면 기간 편중이다")
    print("    - ③에서 거래대금 하위 25%가 1억 근처면 **실전에서 못 산다**")
    print("    - ④에서 학습·검증 **둘 다** 코스피를 넘어야 한다")
    print("    - ⚠️ 셋 중 하나라도 못 넘으면 **오늘 무너진 넷과 같은 운명**이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
