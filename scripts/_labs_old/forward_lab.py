#!/usr/bin/env python3
r"""
forward_lab.py — **최근 기간을 격리해 실제로 맞았는지 본다** (2026-09-03 · 74차)

⚠️⚠️ **사용자 아이디어.**
   *"지금이 9월인데, 지금 학습한 신호로 예측 테스트를 해보는 거야.
     7/20날까지의 정보에 지금까지 학습한 신호로 7/21 등락을 예측해보고 얼마나 적중하는지!"*

## 이 시험이 다른 시험과 다른 점
```
지금까지  16.7년 전체를 보고 「평균 몇 %」를 냈다 — 숫자다
이번      **최근 기간을 완전히 격리**해서 「그날 이 종목을 샀으면 어떻게 됐나」를
          **종목 이름과 날짜로** 본다 — 현실이다
```

## 어떻게 격리하나 (look-ahead를 확실히 막는다)
```
① **학습 끝일**을 정한다 (기본 2025-12-31)
② 그 전 자료로만 재무 문턱(잉여금·부채비율 중앙값)을 정한다
③ 그 뒤 기간에 신호가 뜬 날·종목을 뽑아 **실제 결과**를 본다
④ D+1(다음날) · D+5 · D+20 각각의 적중률
```
⚠️⚠️ **완전한 out-of-sample은 아니다.** 신호의 **구조**(재무+갭+볼린저+20일)는
   전체 자료를 보며 만들었다. 다만 **문턱 숫자는 학습 기간에서만** 뽑았고,
   61차에서 **고정 숫자(잉여금30·부채80)로도 같은 결과**가 나왔으니
   구조가 그 기간에 맞춰진 것은 아니다.

⚠️ 사용자가 말한 「7/21 하루 등락 예측」도 낸다(D+1). 다만 우리 신호는
   **D+20 보유**가 전제라 D+1 적중률은 **참고**다.

쓰는 법:
    python scripts\forward_lab.py                    # 2026-01-01부터 검증
    python scripts\forward_lab.py --끝 20250630      # 학습 끝일을 바꾼다
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


def main():
    # >>> 2026-09-03 수정. 한 시점만 보면 **그 기간의 특수성**에 휘둘린다.
    #     첫 판(학습끝 20251231)에서 D+20 +24.90%가 나왔는데, 월별로 쪼개니
    #     2026-05는 -19.50%였고 **7월 급변장**이 평균을 끌어올린 것이었다.
    #     68차의 「날짜 편중」과 같은 문제다. => **여러 시점을 반복**해야 한다.
    끝들 = ["20191231", "20201231", "20211231", "20221231",
            "20231231", "20241231", "20251231"]
    if "--끝" in sys.argv:
        끝들 = [sys.argv[sys.argv.index("--끝") + 1]]
    for 학습끝 in 끝들:
        print("=" * 78)
        한판(학습끝)
    return 0


def 한판(학습끝):
    print(f"  학습 끝일 **{학습끝}** — 그 뒤는 신호를 만들 때 안 봤다고 친다\n",
          flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    갭표, 시장갭, 앞종 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d["기준일"]] = 하루
        if len(하루) >= 100:
            시장갭[d["기준일"]] = st.median(list(하루.values()))
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
        if not 앞2:
            continue
        p = spy[max(앞2)]
        if not p:
            continue
        try:
            if (dt.datetime.strptime(d, "%Y%m%d")
                    - dt.datetime.strptime(전, "%Y%m%d")).days > 4:
                continue
        except Exception:
            pass
        미맵[d] = (spy[전] / p - 1) * 100

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

    # ── ① 학습 기간에서 문턱을 뽑는다 ──
    학습값 = {"잉": [], "부": []}
    for i, d1 in enumerate(날):
        if i < 260 or 날[i + 1 if i + 1 < len(날) else i] > 학습끝:
            if 날[min(i + 1, len(날) - 1)] > 학습끝:
                continue
        if i + 1 >= len(날) or 날[i + 1] > 학습끝:
            continue
        for code in 주가[d1]:
            fm = 재무값(code, d1)
            if fm:
                if fm.get("잉여금비율") is not None:
                    학습값["잉"].append(fm["잉여금비율"])
                if fm.get("부채비율") is not None:
                    학습값["부"].append(fm["부채비율"])
        if i % 900 == 0 and 날[i] <= 학습끝:
            print(f"    학습 {날[i]} · 표본 {len(학습값['잉']):,}", flush=True)
    잉 = sorted(학습값["잉"])
    부 = sorted(학습값["부"])
    잉문, 부문 = (잉[len(잉) // 2], 부[len(부) // 2]) if 잉 and 부 else (30.0, 80.0)
    print(f"\n  학습 기간에서 뽑은 문턱: 잉여금비율 ≥{잉문:.1f}% · 부채비율 ≤{부문:.1f}%")
    print(f"  (참고: 고정 숫자는 잉여금 ≥30% · 부채 ≤80%였다)\n")

    # ── ② 검증 기간에서 신호를 뽑는다 ──
    보유들 = (1, 5, 20, 40)
    뽑 = []
    for i, d1 in enumerate(날):
        if i < 260:
            continue
        if i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 <= 학습끝:
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
            if not (fm and fm.get("잉여금비율", -9e9) >= 잉문
                    and fm.get("부채비율", 9e9) <= 부문 and fm.get("흑자") == 1.0):
                continue
            bb = 기본.get(code) or {}
            부명 = str(bb.get("업종") or "")
            if (("관리종목" in 부명) or ("SPAC" in 부명)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -1.0 or sq[k - 20] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            if r20 > -10:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            수익 = {}
            for h in 보유들:
                j = i + 1 + h
                if j < len(날):
                    끝 = 주가[날[j]].get(code)
                    if 끝:
                        수익[h] = (끝[0] / 매수 - 1) * 100 - _비용
            이름 = (bb.get("종목명") or bb.get("한글종목명")
                    or bb.get("표준코드명") or "")
            뽑.append((다음, code, 이름, 매수, 수익, 시총 / 1e8, 대금 / 1e8,
                       g - 시갭, 볼, r20, 미맵.get(다음), fm))

    if not 뽑:
        print("  검증 기간에 신호가 없다.")
        return 0
    뽑.sort()
    print(f"  ══ 검증 기간 신호: **{len(뽑)}건** "
          f"({뽑[0][0]} ~ {뽑[-1][0]}) · 신호일 {len({x[0] for x in 뽑})}일 ══\n")

    # ── ③ 종목별 표 ──
    # >>> 종목 표는 **마지막 판(가장 최근)**만 찍는다
    표찍기 = 학습끝 >= "20251231"
    if 표찍기:
        print(f"    {'매수일':<10}{'종목':<9}{'이름':<14}{'매수가':>9}"
              f"{'D+1':>8}{'D+5':>8}{'D+20':>9}{'D+40':>9}{'미국전날':>9}")
    for d, code, 이름, 매수, 수익, mc, am, rg, 볼, r20, 미, fm in (뽑 if 표찍기 else []):
        def f(h):
            return f"{수익[h]:+.1f}%" if h in 수익 else "  —"
        미표 = f"{미:+.2f}%" if 미 is not None else "  —"
        print(f"    {d:<10}{code:<9}{(이름 or '')[:12]:<14}{매수:>9,.0f}"
              f"{f(1):>8}{f(5):>8}{f(20):>9}{f(40):>9}{미표:>9}")

    # ── ④ 적중률 ──
    print(f"\n  ══ ⭐ **적중률** (검증 기간 {뽑[0][0]} ~ {뽑[-1][0]}) ══")
    print(f"    {'보유':<8}{'표본':>7}{'평균':>10}{'승률':>9}{'중앙값':>10}"
          f"{'최저':>9}{'최고':>9}")
    for h in 보유들:
        v = [x[4][h] for x in 뽑 if h in x[4]]
        if len(v) < 3:
            print(f"    D+{h:<6}{len(v):>7}  표본 부족 (아직 기간이 안 지났다)")
            continue
        승 = sum(1 for x in v if x > 0) / len(v) * 100
        print(f"    D+{h:<6}{len(v):>7}{st.mean(v):>+9.2f}%{승:>8.1f}%"
              f"{st.median(v):>+9.2f}%{min(v):>+8.1f}%{max(v):>+8.1f}%")

    월별 = {}
    for x in 뽑:
        if 20 in x[4]:
            월별.setdefault(x[0][:6], []).append(x[4][20])
    if len(월별) > 1:
        print("    ── 월별 (한 달에 몰려 있으면 평균을 믿으면 안 된다) ──")
        for m in sorted(월별):
            a = 월별[m]
            print(f"      {m}  {len(a):>3}건 · D+20 평균 {st.mean(a):>+7.2f}% · 중앙 {st.median(a):>+7.2f}%")
    print(f"\n  ══ 견줌 — **16.7년 전체 성적** ══")
    print("    D+20  +10.05% · 승률 72.2%   (61차 걷기검증 +9.98% · 8/8해)")
    print("    ⇒ 위 검증 기간 성적이 이와 비슷하면 **신호가 아직 살아 있다**")

    # ── ⑤ 미국 조건을 얹으면 ──
    미있 = [x for x in 뽑 if x[10] is not None]
    if len(미있) >= 5:
        print(f"\n  ══ 미국 조건(71차)을 얹으면 — 검증 기간에서도 듣나 ══")
        print(f"    {'조건':<24}{'표본':>7}{'D+20 평균':>12}{'승률':>9}")
        for 문, 라 in ((None, "전부"), (0.0, "어젯밤 미국 하락"),
                       (-0.5, "어젯밤 미국 −0.5%↓")):
            v = [x[4][20] for x in 미있
                 if 20 in x[4] and (문 is None or x[10] <= 문)]
            if len(v) < 3:
                print(f"    {라:<24}{len(v):>7}  표본 부족")
                continue
            승 = sum(1 for z in v if z > 0) / len(v) * 100
            print(f"    {라:<24}{len(v):>7}{st.mean(v):>+11.2f}%{승:>8.1f}%")

    print("\n  읽는 법")
    print("    - ⚠️ **완전한 out-of-sample은 아니다.** 신호의 **구조**는 전체를 보며 만들었다.")
    print("       다만 **문턱 숫자**는 학습 기간에서만 뽑았고, 61차에서")
    print("       **고정 숫자로도 같은 결과**가 나왔으니 구조가 기간에 맞춰진 건 아니다")
    print("    - D+1은 **참고**다. 우리 신호는 **D+20 보유**가 전제다")
    print("    - 표본이 적으면(검증 기간이 짧으면) **적중률을 그대로 믿으면 안 된다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
