#!/usr/bin/env python3
r"""
prob2_lab.py — **96차. 브리핑에 쓸 확률표를 만든다** (2026-09-04 새벽)

## 왜
```
사용자: *"꼭 등급제 아니어도 돼! 점수제나 확률제여도 좋고,
        우리가 테스트 결과로 얻는 정보를 잘 보여줄 수 있는 형태면"*

지금 브리핑은 종목만 보여준다. **얼마나 믿을 만한지**를 안 보여준다.
91차가 알려준 것: 같은 신호라도 **금리 국면에 따라 도달률이 65.2% vs 87.8%**다.
⇒ 그 정보를 브리핑에 넣어야 한다
```

## 재는 것
```
A 신호 자체의 깊이별      상대갭 · 볼린저 · 20일 낙폭이 깊을수록 다른가
B 시장 상황별            코스피 20일 · 코스닥 20일
C ⭐ **미국 금리 국면**    인상 · 동결 · 인하 (91차 다시)
D ⭐⭐ **한국 금리 방향**  국고채10년 ETF 20일 등락으로 역산 (FRED 없이)
                       ⚠️ 채권 ETF는 **가격이 오르면 금리가 내린 것**이다
E 재무 깊이별            잉여금비율 · 부채비율
F ⭐⭐ **확률 계산식**     위 조각들을 더해 확률을 낸다
G ⭐⭐⭐ **보정 확인**     내가 「70%」라 한 것이 실제로 70%였나 (calibration)
                       ⚠️ 이게 없으면 확률을 보여줄 자격이 없다
```
⚠️ 확률은 **그 해 이전 자료로만** 만들어야 한다. G에서 그렇게 잰다
"""
import bisect
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
_FR = os.path.join(O._DATA, "fred")
_ETF = os.path.join(O._DATA, "etf-krx")
# 국고채 ETF 후보 (있는 것을 쓴다)
국채ETF = ("365780", "148070", "114460", "114260", "302190")


def main():
    # ── 미국 기준금리 ──
    기준 = {}
    p = os.path.join(_FR, "AV_FEDFUNDS.json")
    if os.path.exists(p):
        기준 = json.load(io.open(p, encoding="utf-8-sig")).get("값") or {}
    k기 = sorted(기준)

    # ── 한국 국고채 ETF (금리 방향 역산) ──
    #   ⚠️ 채권 ETF는 **가격이 오르면 금리가 내린 것**이다
    채권 = {}
    쓴코드 = None
    파일들 = sorted(glob.glob(os.path.join(_ETF, "*.json")))
    if 파일들:
        # 어느 코드가 가장 오래 있나
        표 = {}
        for f in 파일들[::10]:      # 10일 간격으로 훑어 후보를 고른다
            try:
                d = json.load(io.open(f, encoding="utf-8-sig"))
            except Exception:
                continue
            종 = d.get("종목") or {}
            for c in 국채ETF:
                if c in 종:
                    표[c] = 표.get(c, 0) + 1
        if 표:
            쓴코드 = max(표, key=표.get)
            for f in 파일들:
                try:
                    d = json.load(io.open(f, encoding="utf-8-sig"))
                except Exception:
                    continue
                v = (d.get("종목") or {}).get(쓴코드)
                if not v:
                    continue
                try:
                    c2 = float(v.get("종가") or 0)
                except (TypeError, ValueError):
                    continue
                if c2 > 0:
                    채권[d.get("기준일") or os.path.basename(f)[:8]] = c2
    print(f"  미국 기준금리 {len(기준):,}일 · 국고채 ETF {쓴코드} {len(채권):,}일",
          flush=True)

    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
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
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c)
            pv = 앞종.get(c)
            앞종[c] = 종c
            if pv and pv > 0:
                g = (시 / pv - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

    # 시장 지수 대용 — 그날 전체 중앙 등락
    시장 = {}
    앞2 = {}
    for d in 날:
        벌 = []
        for c, v in 주가[d].items():
            pv = 앞2.get(c)
            앞2[c] = v[0]
            if pv and pv > 0:
                벌.append((v[0] / pv - 1) * 100)
        if len(벌) >= 100:
            시장[d] = st.median(벌)
    시누 = {}
    누 = 100.0
    for d in 날:
        누 *= (1 + 시장.get(d, 0) / 100)
        시누[d] = 누

    def 앞값(표, ks, d):
        i = bisect.bisect_left(ks, d)
        return 표[ks[i - 1]] if i > 0 else None

    k채 = sorted(채권)

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
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        # 그날 쓸 수 있는 국면 값
        r = 앞값(기준, k기, 다음)
        r0 = 앞값(기준, k기, 날[max(0, i - 62)])
        국면 = "모름"
        if r is not None and r0 is not None:
            차 = r - r0
            국면 = "인상" if 차 >= 0.20 else ("인하" if 차 <= -0.20 else "동결")
        # 한국 금리 방향 (채권 ETF 20일 등락 — **오르면 금리 하락**)
        b1 = 앞값(채권, k채, 다음)
        b0 = 앞값(채권, k채, 날[max(0, i - 20)])
        한금 = None
        if b1 and b0 and b0 > 0:
            한금 = (b1 / b0 - 1) * 100      # 양수 = 채권값 상승 = **금리 하락**
        # 시장 20일
        시20 = None
        if i >= 21 and 시누.get(날[i - 20]):
            시20 = (시누[d1] / 시누[날[i - 20]] - 1) * 100
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 2e11:
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
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -1.0 or sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            if 낙 > -10:
                continue
            bb0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not bb0 or not v0:
                continue
            매수 = v0[0] * bb0[0]
            if 매수 <= 0:
                continue
            결과 = None
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + _목표 / 100):
                    결과 = _목표 - _비용
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과 = (끝[0] / 매수 - 1) * 100 - _비용
            사건.append({"날": 다음, "code": code, "결과": 결과,
                         "도달": 결과 > _목표 - _비용 - 1e-9,
                         "갭": g - 시갭, "볼": 볼, "낙": 낙, "시총": 시총,
                         "국면": 국면, "한금": 한금, "시20": 시20,
                         "잉여": fm.get("잉여금비율"), "부채": fm.get("부채비율")})
    n = len(사건)
    바닥 = sum(1 for x in 사건 if x["도달"]) / n * 100
    print(f"  사건 {n:,}건 · **기본 도달률 {바닥:.1f}%**\n", flush=True)

    def 쪼개(키, 칸들, 라, 꼴="{}"):
        print(f"\n  ══ {라} ══")
        print(f"    {'구간':<22}{'표본':>8}{'도달률':>9}{'기본대비':>10}"
              f"{'평균':>9}   {'걸친 해'}")
        for lo, hi, 이름 in 칸들:
            a = [x for x in 사건 if x.get(키) is not None
                 and lo <= x[키] < hi]
            if len(a) < 20:
                print(f"    {이름:<22}{len(a):>7}건   표본 부족")
                continue
            d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
            해 = sorted({x["날"][:4] for x in a})
            경 = "⚠️" if len(해) <= 2 else "  "
            print(f"    {이름:<22}{len(a):>7}건{d2:>8.1f}%{d2-바닥:>+9.1f}%p"
                  f"{st.mean([x['결과'] for x in a]):>+8.2f}%   "
                  f"{경}{len(해)}해")

    쪼개("갭", ((-99, -8, "상대갭 −8%p 아래"), (-8, -6, "−6~−8%p"),
               (-6, -4.5, "−4.5~−6%p"), (-4.5, -3, "−3~−4.5%p")),
         "A-1 **상대갭이 깊을수록**")
    쪼개("볼", ((-99, -1.6, "볼린저 −1.6σ 아래"), (-1.6, -1.3, "−1.3~−1.6σ"),
               (-1.3, -1.15, "−1.15~−1.3σ"), (-1.15, -1.0, "−1.0~−1.15σ")),
         "A-2 **볼린저가 깊을수록**")
    쪼개("낙", ((-99, -30, "20일 −30% 아래"), (-30, -20, "−20~−30%"),
               (-20, -15, "−15~−20%"), (-15, -10, "−10~−15%")),
         "A-3 **20일 낙폭이 깊을수록**")
    쪼개("시20", ((-99, -8, "시장 20일 −8%↓"), (-8, -3, "−3~−8%"),
                 (-3, 2, "−3~+2%"), (2, 99, "+2%↑")),
         "B **시장이 어떤 상태였나**")

    print(f"\n  ══ C ⭐ **미국 금리 국면** (91차 다시) ══")
    print(f"    {'구간':<22}{'표본':>8}{'도달률':>9}{'기본대비':>10}{'평균':>9}"
          f"   {'걸친 해'}")
    for g in ("인상", "동결", "인하"):
        a = [x for x in 사건 if x["국면"] == g]
        if len(a) < 20:
            continue
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        해 = sorted({x["날"][:4] for x in a})
        print(f"    {g + '기':<22}{len(a):>7}건{d2:>8.1f}%{d2-바닥:>+9.1f}%p"
              f"{st.mean([x['결과'] for x in a]):>+8.2f}%   {len(해)}해")

    쪼개("한금", ((-99, -1.5, "채권 −1.5%↓ (금리 급등)"),
                 (-1.5, -0.3, "−0.3~−1.5% (금리 상승)"),
                 (-0.3, 0.3, "제자리"),
                 (0.3, 99, "+0.3%↑ (금리 하락)")),
         "D ⭐⭐ **한국 금리 방향** (국고채 ETF 20일 · FRED 없이)")
    쪼개("잉여", ((30, 100, "잉여금비율 30~100%"), (100, 300, "100~300%"),
                 (300, 800, "300~800%"), (800, 9e9, "800%↑")),
         "E-1 **잉여금비율**")
    쪼개("부채", ((0, 20, "부채비율 20%↓"), (20, 40, "20~40%"),
                 (40, 60, "40~60%"), (60, 80, "60~80%")),
         "E-2 **부채비율**")

    # ══ F 확률 계산식 ══
    print(f"\n  ══ F ⭐⭐ **확률 계산식** ══")
    print("     기본 도달률에 조각들을 더해 확률을 낸다")
    조각 = []

    def 조각재기(이름, 조건):
        a = [x for x in 사건 if 조건(x)]
        b = [x for x in 사건 if not 조건(x)]
        if len(a) < 40 or len(b) < 40:
            return
        da = sum(1 for x in a if x["도달"]) / len(a) * 100
        db = sum(1 for x in b if x["도달"]) / len(b) * 100
        조각.append((da - db, 이름, 조건))

    조각재기("상대갭 −6%p 아래", lambda x: x["갭"] < -6)
    조각재기("볼린저 −1.3σ 아래", lambda x: x["볼"] < -1.3)
    조각재기("20일 −20% 아래", lambda x: x["낙"] < -20)
    조각재기("시총 1,000억 아래", lambda x: x["시총"] < 1e11)
    조각재기("금리 인하기", lambda x: x["국면"] == "인하")
    조각재기("금리 인상기 아님", lambda x: x["국면"] != "인상")
    조각재기("한국 금리 하락 중",
             lambda x: x["한금"] is not None and x["한금"] > 0.3)
    조각재기("시장도 20일 −3%↓",
             lambda x: x["시20"] is not None and x["시20"] < -3)
    조각재기("잉여금비율 300%↑", lambda x: (x["잉여"] or 0) >= 300)
    조각재기("부채비율 40%↓", lambda x: (x["부채"] or 99) <= 40)
    조각.sort(reverse=True)
    print(f"    {'조각':<26}{'있을 때 − 없을 때'}")
    for 값, 이름, _ in 조각:
        표 = "⭐" if 값 >= 5 else ("  " if 값 > -3 else "❌")
        print(f"    {이름:<26}{값:>+8.1f}%p  {표}")

    # ══ G 보정 확인 ══
    print("")
    print("  ══ G ⭐⭐⭐ **보정 확인** — 「70%」라 한 게 실제로 70%였나 ══")
    print("     ⚠️ 확률은 **그 해 이전 자료로만** 만든다 (미리보기 금지)")
    print("     ⚠️⚠️ **조각을 더하는 방식은 버렸다.** 2026-09-03 첫 판에서")
    print("        70~79%라 한 게 실제 51.1%(−23.9%p)로 크게 과대추정했다.")
    print("        원인: 조각 다섯 중 셋이 사실상 같은 것이었다")
    print("        (금리 인하기 · 금리 인상기 아님 · 한국 금리 하락)")
    print("     ⇒ 대신 **「조건 몇 개를 만족했나」별 실제 도달률**을 그대로 쓴다")

    # ⚠️ 겹치지 않게 **갈래마다 하나씩**만 고른다
    갈래 = (
        ("신호 깊이", lambda x: x["낙"] < -20),
        ("상대갭 깊이", lambda x: x["갭"] < -6),
        ("금리 국면", lambda x: x["국면"] == "인하"),
        ("한국 금리", lambda x: x["한금"] is not None and x["한금"] > 0.3),
        ("시장 상황", lambda x: x["시20"] is not None and x["시20"] < -3),
        ("크기", lambda x: x["시총"] < 1e11),
    )
    print("")
    print(f"     쓰는 갈래 ({len(갈래)}개, 서로 안 겹치게 하나씩):")
    for 라, 조건 in 갈래:
        a = [x for x in 사건 if 조건(x)]
        if not a:
            continue
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        print(f"       {라:<12}{len(a):>6}건  도달률 {d2:>5.1f}%  "
              f"({d2 - 바닥:+.1f}%p)")

    for x in 사건:
        x["점"] = sum(1 for _, 조건 in 갈래 if 조건(x))

    print("")
    print("    ── 조건 개수별 **실제** 도달률 (전 기간) ──")
    print(f"    {'만족한 조건':<16}{'표본':>8}{'도달률':>10}{'평균':>10}"
          f"{'걸친 해':>9}")
    for s2 in range(0, len(갈래) + 1):
        a = [x for x in 사건 if x["점"] == s2]
        if len(a) < 15:
            continue
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        해 = sorted({x["날"][:4] for x in a})
        print(f"    {str(s2) + '개':<16}{len(a):>7}건{d2:>9.1f}%"
              f"{st.mean([x['결과'] for x in a]):>+9.2f}%{len(해):>8}해")

    print("")
    print("    ── ⭐⭐ **보정 확인** (그 해 이전 자료로만 확률을 만든다) ──")
    묶 = {}
    for y in sorted({x["날"][:4] for x in 사건}):
        앞 = [z for z in 사건 if z["날"][:4] < y]
        올 = [z for z in 사건 if z["날"][:4] == y]
        if len(앞) < 120:
            continue
        # 그 해 **이전** 자료로만 조건 개수별 도달률을 만든다
        표2 = {}
        for s2 in range(0, len(갈래) + 1):
            b = [z for z in 앞 if z["점"] == s2]
            if len(b) >= 12:
                표2[s2] = sum(1 for z in b if z["도달"]) / len(b) * 100
        if not 표2:
            continue
        for x in 올:
            p2 = 표2.get(x["점"])
            if p2 is None:
                # 그 개수의 표본이 없으면 가장 가까운 개수를 쓴다
                가 = min(표2, key=lambda k: abs(k - x["점"]))
                p2 = 표2[가]
            묶.setdefault(int(p2 // 10) * 10, []).append(x["도달"])
    print(f"    {'내가 말한 확률':<18}{'표본':>8}{'실제 도달률':>12}{'차이':>10}"
          f"   {'판정'}")
    벗 = 잰 = 0
    for 칸 in sorted(묶):
        a = 묶[칸]
        if len(a) < 20:
            continue
        실 = sum(a) / len(a) * 100
        가 = 칸 + 5
        잰 += 1
        ok = abs(실 - 가) <= 10
        벗 += 0 if ok else 1
        print(f"    {f'{칸}~{칸+9}%':<18}{len(a):>7}건{실:>11.1f}%"
              f"{실-가:>+9.1f}%p   {'좋음' if ok else '**벗어남**'}")
    print("")
    print(f"     ⇒ {잰}칸 중 **{잰-벗}칸이 ±10%p 안**")
    if 잰 == 0:
        print("     ⚠️ 잴 표본이 없다")
    elif 벗 == 0:
        print("     ⭐⭐ **확률을 브리핑에 써도 된다**")
    elif 벗 <= 1:
        print("     ⚠️ 한 칸이 벗어난다. **「높음·보통·낮음」 세 등급**이 안전하다")
    else:
        print("     ⚠️⚠️ 여러 칸이 벗어난다. **확률을 쓰면 안 된다.**")
        print("        조건 개수(0~6개)를 **그대로 보여주고** 과거 도달률을")
        print("        붙이는 게 낫다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
