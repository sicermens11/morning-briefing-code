#!/usr/bin/env python3
r"""
pool_lab.py — **여러 신호를 모아 매일 상위 N개를 뽑는다** (2026-09-02 · 45차)

⚠️⚠️ **사용자 지적.**
   *"당연히 종합적으로 여러 조건을 검토해서 채워야지! 아까 말한 조건만 가지고 종목을 채우면 안 되지"*
   ⚠️ 맞다. 44차는 볼린저 하나로 빈도를 채우려 했다 — 그건 **좋은 신호를 희석시키는 것**이다.

## 그래서 신호를 **각자 잘 통하는 조건에서만** 뽑아 한 통에 모은다
```
A 볼하단 + 갭 −5%↓          42차: 코스피대비 +10.14% 승률 74% 연 40건  ⭐
B 볼하단 + 갭 −5~−2%         +2.41% 56% 연 439건 ⭐
C 볼하단 + 시가 +2% 돌파       41차: +1.10% 51.2% 체결률 49%
D 신고가 **4~5일째** 이어짐    31차: 자기크기 대비 +1.83(중형)  ← 첫날이 아니다
E RSI 과매수 **11일↑** 이어짐  31차: 자기크기 대비 +1.47~4.24
F RSI 과매수 + **식는 중**     31차: 중형 +0.84 (오르는 중의 2배)
G 신고가 첫날                 (대조군 — 41차에서 코스피 못 넘었다)
```
⚠️⚠️ **D·E·F는 「자기 크기 구간 대비」로만 재봤다.** 여기서 **코스피 대비**로 다시 잰다 —
   잣대가 다르면 결과가 뒤집힐 수 있다(38차에서 RSI 과매수 진입이 그랬다).

## 재는 것
```
① 신호별 성적을 **같은 잣대**로 (코스피 대비 · D+20 · 다음날 시가 매수 · 연도별)
② 전부 한 통에 모아 **매일 상위 N개** (N=1·2·3·5)
③ **모으는 게 나은가, 가장 좋은 하나만 쓰는 게 나은가**  ← 이게 핵심 질문이다
```
⚠️ 왕복비용 0.26%. 연도별 문턱 **3분의 2**.
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
                고 = float(v.get("고가") or 0) or 종
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
            하루[c] = (종, 시, 고, 등, 시총, 대금)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 고, 등, 시총, 대금) in 원[d].items():
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
            하루[c] = (수, 시 * 배, 고 * 배, 시총, 대금)
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

    # 종목별 신호 계열 (연속일수를 세려면 매일 필요하다)
    print("  지표 계열 계산 중...", flush=True)
    신고연속, 과매연속, rsi표, 볼표 = {}, {}, {}, {}
    for code, sq in 종계.items():
        n = len(sq)
        if n < 260:
            continue
        신c, 과c = [0] * n, [0] * n
        rs, bl = [None] * n, [None] * n
        run신 = run과 = 0
        for k in range(250, n):
            고 = max(sq[k - 250:k + 1])
            신 = bool(고) and sq[k] >= 고 * 0.999
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            r = 100 - 100 / (1 + 상 / 하)
            rs[k] = r
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            bl[k] = (sq[k] - s20) / (2 * sd)
            run신 = run신 + 1 if 신 else 0
            run과 = run과 + 1 if r >= 70 else 0
            신c[k], 과c[k] = run신, run과
        신고연속[code], 과매연속[code] = 신c, 과c
        rsi표[code], 볼표[code] = rs, bl
    print(f"  지표 {len(rsi표):,}종목", flush=True)

    # 후보 모으기: 날 -> [(신호명, 점수, code, 크기, 수익, 초과, 대금)]
    후보 = {}
    앞볼 = {}
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            앞볼 = {}
            continue
        오늘볼, 묶 = {}, []
        for code, v in 주가[d1].items():
            c1, _시, _고, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250 or code not in rsi표:
                continue
            볼 = 볼표[code][k]
            rsi = rsi표[code][k]
            if 볼 is None or rsi is None:
                continue
            볼하 = 볼 <= -1.0
            오늘볼[code] = 볼하
            나 = 주가[날[i + 1]].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝 or 나[1] <= 0 or c1 <= 0:
                continue
            갭 = (나[1] / c1 - 1) * 100
            r = (끝[0] / 나[1] - 1) * 100 - _비용
            초 = r - ((ixv[i + 1 + _보유] / ixv[i + 1] - 1) * 100
                      if (ixv[i + 1] and ixv[i + 1 + _보유]) else 0)
            g = _크기(시총)
            앞 = 앞볼.get(code)
            첫볼 = 볼하 and (앞 is False)
            # ── 신호 판정 ──
            if 첫볼 and 갭 <= -5:
                묶.append(("A 볼하단+갭−5%↓", 10 - 갭, code, g, r, 초, 나[4]))
            elif 첫볼 and -5 < 갭 <= -2:
                묶.append(("B 볼하단+갭−5~−2%", 5 - 갭, code, g, r, 초, 나[4]))
            if 첫볼 and 나[2] >= 나[1] * 1.02:
                묶.append(("C 볼하단+시가2%돌파", 3.0, code, g, r, 초, 나[4]))
            런신 = 신고연속[code][k]
            if 4 <= 런신 <= 5:
                묶.append(("D 신고가 4~5일째", 2.5, code, g, r, 초, 나[4]))
            if 신고연속[code][k] == 1:
                묶.append(("G 신고가 첫날(대조)", 1.0, code, g, r, 초, 나[4]))
            런과 = 과매연속[code][k]
            if 런과 >= 11:
                묶.append(("E 과매수 11일↑", 2.0 + 런과 / 50, code, g, r, 초, 나[4]))
            if rsi >= 70 and k >= 5 and rsi표[code][k - 5] is not None \
                    and rsi < rsi표[code][k - 5]:
                묶.append(("F 과매수+식는중", 2.0, code, g, r, 초, 나[4]))
        앞볼 = 오늘볼
        if 묶:
            후보[i] = 묶
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    년수 = len(날) / 245
    이름들 = sorted({x[0] for v in 후보.values() for x in v})
    해들 = sorted({d[:4] for d in 날[260:]})

    print(f"\n  ══ ① 신호별 — **같은 잣대**로 (코스피 대비 · D+{_보유} · 다음날 시가 매수) ══")
    print("     ⚠️ D·E·F는 지금까지 「자기 크기 구간 대비」로만 봤다. 여기서 처음 코스피 대비로 잰다")
    print(f"    {'신호':<22}{'크기':<6}{'초과':>9}{'승률':>7}{'연간':>8}"
          f"{'연도별':>10}{'표본':>9}")
    좋은 = []
    for 이름 in 이름들:
        for g, _, _ in 크기표:
            a = [x for v in 후보.values() for x in v if x[0] == 이름 and x[3] == g]
            if len(a) < 400:
                continue
            초 = [x[5] for x in a]
            승 = sum(1 for x in a if x[4] > 0) / len(a) * 100
            해별 = {}
            for i, v in 후보.items():
                for x in v:
                    if x[0] == 이름 and x[3] == g:
                        해별.setdefault(날[i][:4], []).append(x[5])
            전 = 플 = 0
            for y, arr in 해별.items():
                if len(arr) < 15:
                    continue
                전 += 1
                플 += 1 if st.mean(arr) > 0 else 0
            연도 = f"{플}/{전}" if 전 else "-"
            통과 = 전 >= 8 and 플 / 전 >= 2 / 3
            별 = "⭐" if (st.mean(초) > 0 and 통과) else ("○" if st.mean(초) > 0 else "❌")
            if st.mean(초) > 0 and 통과:
                좋은.append((이름, g))
            print(f"    {이름:<22}{g:<6}{st.mean(초):>+8.2f}%{승:>6.0f}%"
                  f"{len(a)/년수:>7.0f}건{연도:>10}{len(a):>9,}{별}")

    print(f"\n  ⭐ 연도별 문턱(3분의 2)까지 통과한 조합 {len(좋은)}개: "
          + ", ".join(f"{a}·{b}" for a, b in 좋은[:12]))

    print(f"\n\n  ══ ②③ **모으는 게 나은가** — 매일 상위 N개 ══")
    print("     ⚠️ 「주 3개」 = 하루 0.6개. N=1이면 주 5개다")
    쓸 = set(좋은)
    묶음들 = [("전부(대조군 G 포함)", None),
              ("⭐통과한 것만", 쓸),
              ("A만 (가장 강한 하나)", {(a, b) for a, b in 좋은 if a.startswith("A")}),
              ("A+B만 (볼하단 계열)", {(a, b) for a, b in 좋은
                                     if a.startswith(("A", "B"))})]
    print(f"    {'묶음':<22}" + "".join(f"{'N='+str(n):>21}" for n in (1, 2, 3, 5)))
    for 라벨, 허용 in 묶음들:
        if 허용 is not None and not 허용:
            continue
        줄 = []
        for n in (1, 2, 3, 5):
            골 = []
            for i, v in 후보.items():
                쓸것 = [x for x in v
                        if 허용 is None or (x[0], x[3]) in 허용]
                if not 쓸것:
                    continue
                쓸것.sort(key=lambda x: (x[1], x[6]), reverse=True)
                골 += 쓸것[:n]
            if len(골) < 500:
                줄.append("-")
                continue
            초 = [x[5] for x in 골]
            승 = sum(1 for x in 골 if x[4] > 0) / len(골) * 100
            줄.append(f"{st.mean(초):+.2f}({승:.0f}%) {len(골)/년수:.0f}/년")
        print(f"    {라벨:<22}" + "".join(f"{x:>21}" for x in 줄))

    # 최종 후보의 연도별
    print(f"\n\n  ══ ⭐ 연도별 — 「⭐통과한 것만 · 상위 3개」 ══")
    if 쓸:
        해별 = {}
        for i, v in 후보.items():
            쓸것 = [x for x in v if (x[0], x[3]) in 쓸]
            if not 쓸것:
                continue
            쓸것.sort(key=lambda x: (x[1], x[6]), reverse=True)
            for x in 쓸것[:3]:
                해별.setdefault(날[i][:4], []).append(x[5])
        칸, 플, 전 = [], 0, 0
        for y in 해들:
            a = 해별.get(y) or []
            if len(a) < 20:
                칸.append((y, None, 0))
                continue
            m = st.mean(a)
            칸.append((y, m, len(a)))
            전 += 1
            플 += 1 if m > 0 else 0
        print(f"    {'해':<6}" + "".join(f"{y[2:]:>7}" for y, _, _ in 칸))
        print(f"    {'초과':<6}" + "".join(
            (f"{m:>+7.1f}" if m is not None else f"{'-':>7}") for _, m, _ in 칸))
        print(f"    {'건수':<6}" + "".join(f"{n:>7}" for _, _, n in 칸))
        if 전:
            판 = "⭐ 문턱 통과" if 플 / 전 >= 2 / 3 else "❌ 문턱 미달"
            print(f"    ⇒ **{전}해 중 {플}해 + ({플/전*100:.0f}%)**  {판}")

    print("\n  읽는 법")
    print("    - ①에서 D·E·F가 ❌면 **「자기 크기 구간 대비」로만 좋았던 것**이다")
    print("    - ③이 핵심이다: **「⭐통과한 것만」이 「A만」보다 나으면 모으는 게 맞다**")
    print("      나쁘면 **좋은 신호 하나만 쓰고 빈도는 포기**하는 게 맞다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
