#!/usr/bin/env python3
r"""
sweep2_lab.py — **97차. 새로 받은 자료로 다시 훑는다** (2026-09-04 새벽)

## 새벽에 받는 것
```
00:05  DartOldBackfill   공시 **900일치** 더  -> data/dart-daily/
00:35  IndustryCollect   업종                -> data/industry.json
01:00  CapitalCollect    증자·감자            -> data/dart-capital/
```
⇒ 이 셋을 **주력 전략에 조건으로 붙여** 도움이 되는지 본다

## ⚠️⚠️ 미리 밝혀두는 것
```
88b·88c·91에서 **조건을 더하는 시도가 세 번 다 자본 시뮬에서 무너졌다.**
이유: 원판 도달률이 이미 75%라, 조건으로 얻는 것보다 **살 기회를 잃는 손해가 크다.**
⇒ 여기서도 **도달률만 보고 좋아하면 안 된다.** 반드시 **자본 시뮬**까지 본다
⇒ 그리고 「거르는 조건」보다 **「제외하는 조건」**(나쁜 걸 빼는 쪽)을 눈여겨본다
   — 나쁜 걸 빼는 건 살 기회를 거의 안 줄인다
```

## 재는 것
```
0 자료 점검      뭐가 얼마나 들어왔나 (없으면 그 절은 건너뛴다)
A 공시 종류별    그 종목에 **어떤 공시가 있었나** (전날·3일·7일 안)
B ⭐ 증자·감자    유상증자·무상증자·감자가 있었으면 (**나쁜 걸 빼는** 쪽)
C 업종별        어느 업종에서 잘 되나
D ⭐⭐ 자본 시뮬  살아남은 조건을 실제로 붙여본다
```
⚠️ 판정: 도달률 + **연도별 3분의 2** + **자본 시뮬 끝 자산** + 2025·26 제외
"""
import collections
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
    # ══ 0 자료 점검 ══
    print("  ══ 0 **자료 점검** ══")
    공시들 = sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json")))
    증자들 = sorted(glob.glob(os.path.join(O._DATA, "dart-capital", "*.json")))
    업종p = os.path.join(O._DATA, "industry.json")
    print(f"    공시   {len(공시들):>6}일  "
          f"{os.path.basename(공시들[0])[:8] if 공시들 else '-'} ~ "
          f"{os.path.basename(공시들[-1])[:8] if 공시들 else '-'}")
    print(f"    증자감자 {len(증자들):>6}건")
    print(f"    업종   {'있음' if os.path.exists(업종p) else '**없음**'}"
          f"  {업종p}")

    # 공시: 종목 -> 날짜 -> 종류 집합
    공시 = collections.defaultdict(dict)
    종류수 = collections.Counter()
    for f in 공시들:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = d.get("기준일") or os.path.basename(f)[:8]
        # ⚠️ 실제 구조는 "챙길공시"·"그밖의공시" 두 목록이고
        #    필드는 "종목코드"·"공시명"이다 (stock_code/report_nm 아님)
        목 = []
        for 키 in ("챙길공시", "그밖의공시", "공시", "목록", "자료"):
            v = d.get(키)
            if isinstance(v, list):
                목.extend(v)
            elif isinstance(v, dict):
                목.extend(v.values())
        for it in 목:
            if not isinstance(it, dict):
                continue
            c = str(it.get("종목코드") or it.get("stock_code") or "").zfill(6)
            나 = str(it.get("공시명") or it.get("report_nm")
                     or it.get("보고서명") or "")
            if not c or c == "000000" or not 나:
                continue
            공시[c].setdefault(d8, set()).add(나)
            종류수[나[:14]] += 1
    print(f"    공시가 있는 종목 {len(공시):,}개 · 보고서명 갈래 {len(종류수):,}가지")
    print(f"    많은 것: " + " · ".join(
        f"{k}({v:,})" for k, v in 종류수.most_common(6)))
    # ⚠️⚠️ **파일은 있는데 파싱이 0건이면 그냥 넘어가지 않는다** (2026-09-04)
    #    97b가 4,104일을 읽고 **0개**를 파싱하고도 그대로 진행해
    #    「공시는 값을 못 한다」는 **틀린 결론**을 낼 뻔했다
    if 공시들 and not 공시:
        print("    ⚠️⚠️ **공시 파일이 4,104일 있는데 파싱 결과가 0개다.**")
        print("       필드명이 바뀌었을 가능성이 크다. 여기서 멈춘다.")
        print("       확인: python scripts/peek.py data/dart-daily --전부")
        return 2

    # ⚠️ 실제 구조: 종목별 파일 하나에
    #    유상증자·무상증자·유무상증자·감자·자사주취득 목록이 따로 들어 있다
    # ⭐ 날짜(bddd)가 있으므로 **「최근에 있었나」**로 잰다 (이력 유무보다 쓸모 있다)
    # ⚠️ peek.py가 잡아준 것: **자사주처분**도 있다 (2026-09-04)
    갈래들 = ("유상증자", "무상증자", "유무상증자", "감자",
              "자사주취득", "자사주처분")
    증자 = collections.defaultdict(list)   # 종목 -> [(YYYYMMDD, 갈래), ...]
    갈래수 = collections.Counter()
    for f in 증자들:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        c = str(d.get("종목") or d.get("종목코드") or "").zfill(6)
        if not c or c == "000000":
            continue
        for 갈 in 갈래들:
            for it in (d.get(갈) or []):
                if not isinstance(it, dict):
                    continue
                # ⚠️⚠️ 갈래마다 날짜 필드 이름이 다르다
                #    무상증자·감자 bddd(이사회결의일) · 자사주취득 aq_dd(취득결정일)
                #    유상증자는 또 다르다 -> 처음엔 bddd만 봐서 **유상증자 5,050건을
                #    통째로 놓쳤다** (2026-09-04)
                # ⇒ **rcept_no 앞 8자리 = 공시 접수일**을 쓴다.
                #    모든 DART 기록에 있고, **시장이 알게 된 날**이라 우리에게 맞다
                날 = str(it.get("rcept_no") or "")[:8]
                if not (len(날) == 8 and 날.isdigit()):
                    for 키 in ("bddd", "aq_dd", "dcd_dd"):
                        v2 = "".join(ch for ch in str(it.get(키) or "")
                                     if ch.isdigit())
                        if len(v2) == 8:
                            날 = v2
                            break
                if len(날) == 8 and 날.isdigit():
                    증자[c].append((날, 갈))
                    갈래수[갈] += 1
    print(f"    증자·감자가 있는 종목 {len(증자):,}개 · "
          f"건수 {sum(갈래수.values()):,}건")
    if 갈래수:
        print("    갈래별: " + " · ".join(f"{k} {v:,}" for k, v in
                                        갈래수.most_common()))
    # ⚠️ 같은 이유로 여기서도 멈춘다
    if 증자들 and not 증자:
        print("    ⚠️⚠️ **증자감자 파일이 있는데 파싱 결과가 0개다.** 멈춘다.")
        print("       확인: python scripts/peek.py data/dart-capital --전부")
        return 2
    # ⚠️ 갈래 하나가 통째로 0건이어도 알린다 (유상증자를 이렇게 놓쳤다)
    for 갈 in 갈래들:
        if 갈래수.get(갈, 0) == 0:
            print(f"    ⚠️ **{갈}이 0건이다.** 날짜 필드를 못 찾았을 수 있다")

    업종 = {}
    if os.path.exists(업종p):
        try:
            j = json.load(io.open(업종p, encoding="utf-8-sig"))
            업종 = j.get("업종") or j
        except Exception:
            업종 = {}
    print(f"    업종이 있는 종목 {len(업종):,}개\n")

    # ══ 사건 모으기 (94b 개선안 기준) ══
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종, 원시 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            p = 앞종.get(c)
            앞종[c] = 종c
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
            if (c1 - s20) / (2 * sd) > -1.0 or sq[kk - 20] <= 0:
                continue
            if (c1 / sq[kk - 20] - 1) * 100 > -10:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결과, 청산 = None, None
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 청산 = _목표 - _비용, j
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            # ── 그 종목의 최근 공시 (⚠️ **전날까지**만 본다) ──
            창 = {}
            표 = 공시.get(code) or {}
            for 며칠, 라 in ((1, "1일"), (3, "3일"), (7, "7일")):
                모 = set()
                for o in range(1, 며칠 + 1):
                    j2 = i - o + 1
                    if 0 <= j2 < len(날):
                        모 |= 표.get(날[j2], set())
                창[라] = 모
            사건.append({"인": i + 1, "날": 다음, "code": code, "결과": 결과,
                         "청산": 청산, "원시": o0, "대금": b0[2],
                         "상대갭": g - 시갭, "시총": 시총,
                         "도달": 결과 > _목표 - _비용 - 1e-9, "공시": 창})
    n = len(사건)
    if n == 0:
        print("  ⚠️ 사건이 없다. 끝낸다")
        return 1
    바닥 = sum(1 for x in 사건 if x["도달"]) / n * 100
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"  사건 {n:,}건 · 기본 도달률 {바닥:.1f}% · {년수:.1f}년\n", flush=True)

    def 재기(a, 라, 폭=30):
        if len(a) < 25:
            return None
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        묶 = {}
        for x in a:
            묶.setdefault(x["날"][:4], []).append(x["결과"])
        전 = 플 = 0
        for y, arr in 묶.items():
            if len(arr) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        별 = "⭐" if (abs(d2 - 바닥) > 5 and 전 >= 8
                     and 플 / 전 >= 2 / 3) else "  "
        print(f"    {라:<{폭}}{len(a):>7}건{d2:>8.1f}%{d2-바닥:>+8.1f}%p"
              f"{st.mean([x['결과'] for x in a]):>+9.2f}%{f'{플}/{전}':>7}{별}")
        return d2 - 바닥

    머 = (f"    {'조건':<30}{'표본':>9}{'도달률':>8}{'기본대비':>8}"
          f"{'평균':>9}{'연도별':>7}")

    # ══ A 공시 종류별 ══
    if 공시:
        print("  ══ A **최근 공시 종류별** (⚠️ 전날까지만 본다) ══")
        print(머)
        재기([x for x in 사건 if not x["공시"]["7일"]], "7일 안 공시 **없음**")
        재기([x for x in 사건 if x["공시"]["7일"]], "7일 안 공시 있음")
        재기([x for x in 사건 if x["공시"]["1일"]], "**전날** 공시 있음")
        흔 = [k for k, _ in 종류수.most_common(30)]
        print(f"\n    ── 보고서명별 (7일 안) ──")
        점 = []
        for 나 in 흔:
            a = [x for x in 사건
                 if any(나 in s for s in x["공시"]["7일"])]
            r = 재기(a, f"「{나}」")
            if r is not None:
                점.append((r, 나, len(a)))
        점.sort()
        if 점:
            print(f"\n    ⭐ **가장 나쁜 공시** (빼야 할 것):")
            for r, 나, ln in 점[:5]:
                print(f"      「{나}」 {r:+.1f}%p ({ln}건)")
            print(f"    ⭐ **가장 좋은 공시**:")
            for r, 나, ln in 점[-5:][::-1]:
                print(f"      「{나}」 {r:+.1f}%p ({ln}건)")

    # ══ B 증자·감자 ══
    if 증자:
        print("")
        print("  ══ B ⭐ **증자·감자** (나쁜 걸 빼는 쪽) ══")
        print("     ⚠️ 신호 **전날까지**의 것만 본다 (미리보기 금지)")
        print(머)

        def 최근(x, 일수, 갈래=None):
            """신호 전 일수 안에 그 갈래 사건이 있었나"""
            앞 = 증자.get(x["code"]) or []
            끝 = x["날"]
            시 = str(int(끝) - 일수 * 10000 // 365 * 100)   # 대략
            for 날, 갈 in 앞:
                if 갈래 and 갈 != 갈래:
                    continue
                if 날 < 끝 and 날 >= 시:
                    return True
            return False

        있 = set(증자)
        재기([x for x in 사건 if x["code"] in 있], "증자·감자 이력 **있음**")
        재기([x for x in 사건 if x["code"] not in 있], "이력 없음")
        print("    ── 최근 1년 안에 ──")
        for 갈 in ("유상증자", "무상증자", "감자", "자사주취득"):
            재기([x for x in 사건 if 최근(x, 365, 갈)], f"{갈} 있었음")
        재기([x for x in 사건 if 최근(x, 365)], "아무거나 있었음")
        재기([x for x in 사건 if not 최근(x, 365)], "**아무것도 없었음**")
    else:
        print("")
        print("  ══ B 증자·감자 — 자료가 없다")

    # ══ C 업종 ══
    if 업종:
        print(f"\n  ══ C **업종별** ══")
        print(머)
        묶 = collections.Counter()
        for x in 사건:
            u = 업종.get(x["code"])
            if isinstance(u, dict):
                u = u.get("업종명") or u.get("이름")
            묶[str(u)] += 1
        for u, cnt in 묶.most_common(14):
            if cnt < 25:
                continue
            a = []
            for x in 사건:
                v = 업종.get(x["code"])
                if isinstance(v, dict):
                    v = v.get("업종명") or v.get("이름")
                if str(v) == u:
                    a.append(x)
            재기(a, u[:28])
    else:
        print(f"\n  ══ C 업종 — 자료가 없다 (00:35 수집이 아직 안 끝났나)")

    # ══ D 자본 시뮬 ══
    print(f"\n  ══ D ⭐⭐ **자본 시뮬** — 살아남은 조건을 실제로 붙이면 ══")
    print("     ⚠️ 88b·88c·91에서 조건 추가가 세 번 다 여기서 무너졌다")
    묶날 = {}
    for x in 사건:
        묶날.setdefault(x["인"], []).append(x)

    def 시뮬(거름, 라, 끝년=None):
        현금, 보유, 곡, 산 = 5_000_000.0, [], [], 0
        시작i = [j for j, d in enumerate(날) if d >= _시작][0]
        for i in range(시작i, len(날)):
            if 끝년 and 날[i][:4] > 끝년:
                break
            남 = []
            for q in 보유:
                if q["청산"] <= i:
                    현금 += q["주수"] * q["원시"] * (1 + q["결과"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
            골 = [x for x in 묶날.get(i, []) if 거름(x)]
            for x in sorted(골, key=lambda z: z["상대갭"])[:4]:
                쓸 = min(평 * 0.20, 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({**x, "주수": 주수})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        c = ((끝 / 5_000_000) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        print(f"    {라:<30}{끝:>15,.0f}원{c:>+9.2f}%{낙:>8.1f}%{산:>7}건")

    print(f"    {'전략':<30}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")
    시뮬(lambda x: True, "원판 (조건 없음)")
    if 공시:
        시뮬(lambda x: not x["공시"]["7일"], "+ 7일 안 공시 없는 것만")
        시뮬(lambda x: not x["공시"]["1일"], "+ 전날 공시 없는 것만")
    if 증자:
        def 최근있(x, 일수=365, 갈래=None):
            앞 = 증자.get(x["code"]) or []
            끝 = x["날"]
            시 = str(int(끝) - 일수 * 10000 // 365 * 100)
            for 날, 갈 in 앞:
                if 갈래 and 갈 != 갈래:
                    continue
                if 날 < 끝 and 날 >= 시:
                    return True
            return False
        시뮬(lambda x: not 최근있(x), "+ 최근 1년 증자·감자 없는 것만")
        시뮬(lambda x: not 최근있(x, 365, "유상증자"), "+ 최근 1년 유상증자 없는 것만")
    print(f"\n    ⚠️ 2025·26 제외")
    시뮬(lambda x: True, "원판", 끝년="2024")
    if 공시:
        시뮬(lambda x: not x["공시"]["7일"], "+ 7일 안 공시 없는 것만",
             끝년="2024")
    if 증자:
        시뮬(lambda x: not 최근있(x), "+ 최근 1년 증자·감자 없는 것만",
             끝년="2024")

    print("\n  읽는 법")
    print("    - D에서 원판을 못 이기면 그 조건은 **안 쓴다** (세 번 겪었다)")
    print("    - 「나쁜 걸 빼는」 조건이 「좋은 걸 고르는」 조건보다 유리하다")
    print("      (살 기회를 거의 안 줄이기 때문이다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
