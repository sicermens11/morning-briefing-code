#!/usr/bin/env python3
r"""
prob_lab.py — **무엇이 「도달 확률」을 가장 잘 나누나** (2026-09-03 · 86차)

⚠️⚠️ **사용자 지시로 방향이 바뀌었다.**
   *"꼭 등급제 아니어도 돼! 점수제나 확률제여도 좋고,
     우리가 테스트 결과로 얻는 정보를 잘 보여줄 수 있는 형태면"*
```
원래 질문   「지금 브리핑 등급제(🔴🟡🟢)가 작동하나」
바뀐 질문   **「무엇이 +20% 도달 확률을 가장 잘 나누나」**
```

⚠️ **등급제가 우리 결과와 안 맞는 이유**
```
등급은 「사람의 판단」을 담는 형식이다.
우리가 가진 건 **숫자**다 — 도달률 86% · 평균 20일 · 최악 -36%
⇒ 등급으로 바꾸면 **정보가 줄어든다**
```

⚠️ **점수제도 안 맞을 수 있다**
```
81차에서 확인했다: 재무를 더 조여도(잉여금 50%↑·부채 50%↓·ROE 5%↑)
성적이 **안 올랐다**. 점수를 더 주면 오히려 왜곡된다.
⇒ 「조건을 많이 만족할수록 좋다」가 **사실인지** 이 시험에서 확인한다
```

## 재는 것
```
A ⭐ **조건 개수와 도달률의 관계** — 많이 만족할수록 정말 좋나 (점수제의 전제)
B 각 지표별 **도달률 곡선** — 어느 지표가 확률을 가장 잘 가르나
C 구간을 몇 개로 나눠야 의미 있나 (2단계? 3단계? 연속?)
D ⭐ **브리핑에 쓸 표현** — 실제로 보여줄 숫자를 뽑는다
   「과거 N건 중 M%가 +20% 도달 · 평균 K일 · 최악 -X%」
```
⚠️ 매도는 76차 확정 규칙(목표 +20% · 최대 D+40 · 손절 없음).
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
    # 공시 (조용한지 판정용)
    날인 = {d: i for i, d in enumerate(날)}
    공시일 = {}
    공시커버 = set()
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            g = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        i = 날인.get(g.get("기준일"))
        if i is None:
            continue
        공시커버.add(i)
        for x in (g.get("챙길공시") or []):
            if x.get("종목코드"):
                공시일.setdefault(x["종목코드"], set()).add(i)

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
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -1.0 or sq[k - 20] <= 0 or sq[k - 60] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            if r20 > -10:
                continue
            r60 = (c1 / sq[k - 60] - 1) * 100
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            # 거래대금 배수 (조용한가) — 최근 20일 중앙값 대비
            앞대금 = []
            for j2 in range(max(0, i - 20), i):
                vv = 주가[날[j2]].get(code)
                if vv:
                    앞대금.append(vv[2])
            중앙대 = st.median(앞대금) if 앞대금 else 0
            배수 = (대금 / 중앙대) if 중앙대 > 0 else 1.0
            공시있나 = (i in (공시일.get(code) or set())) if i in 공시커버 else None
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
            사건.append({
                "날": 다음, "code": code, "이름": bb.get("이름") or "",
                "결과": 결과, "며칠": 며칠, "도달": 결과 > _목표 - _비용 - 1e-9,
                "상대갭": g - 시갭, "시장갭": 시갭, "볼린저": 볼,
                "낙폭20": r20, "낙폭60": r60, "시총": 시총 / 1e8,
                "배수": 배수, "미국": 미맵.get(다음), "공시": 공시있나,
                "잉여금": fm.get("잉여금비율"), "부채": fm.get("부채비율")})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    n = len(사건)
    도달 = sum(1 for x in 사건 if x["도달"])
    print(f"\n  사건 {n:,}건 · {년수:.1f}년")
    print(f"  **+20% 도달 {도달:,}건 = {도달/n*100:.1f}%** · "
          f"평균 {st.mean([x['결과'] for x in 사건]):+.2f}% · "
          f"평균보유 {st.mean([x['며칠'] for x in 사건]):.1f}일 · "
          f"최악 {min(x['결과'] for x in 사건):+.1f}%\n", flush=True)

    def 재기(a, 라, 폭=30):
        if len(a) < 20:
            print(f"    {라:<{폭}}{len(a):>6}건  — 표본 부족")
            return
        d2 = sum(1 for x in a if x["도달"])
        v = [x["결과"] for x in a]
        print(f"    {라:<{폭}}{len(a):>6}건{d2/len(a)*100:>9.1f}%"
              f"{st.mean(v):>+9.2f}%{st.mean([x['며칠'] for x in a]):>7.1f}일"
              f"{min(v):>+8.1f}%")

    머 = (f"    {'구분':<30}{'표본':>8}{'도달률':>9}{'평균':>9}{'보유':>8}{'최악':>8}")

    # ══ A 조건 개수 ══
    print("  ══ A ⭐ **조건을 많이 만족할수록 좋나** (점수제의 전제) ══")
    print("     ⚠️ 81차에서 재무를 더 조여도 성적이 안 올랐다. 정말 그런지 본다")
    조건들 = (
        ("미국 하락", lambda x: (x["미국"] or 9) <= -0.5),
        ("시장도 빠짐", lambda x: x["시장갭"] < -0.3),
        ("상대갭 −4%p↓", lambda x: x["상대갭"] <= -4),
        ("60일도 −20%↓", lambda x: x["낙폭60"] <= -20),
        ("시총 1000억↓", lambda x: x["시총"] < 1000),
        ("조용함(배수 1.5↓)", lambda x: x["배수"] < 1.5),
        ("공시 없음", lambda x: x["공시"] is False),
    )
    for x in 사건:
        x["점수"] = sum(1 for _, f in 조건들 if f(x))
    print(머)
    for s in range(0, len(조건들) + 1):
        재기([x for x in 사건 if x["점수"] == s], f"조건 {s}개 만족")
    print()
    for s in range(0, len(조건들) + 1):
        a = [x for x in 사건 if x["점수"] >= s]
        if len(a) >= 20:
            재기(a, f"조건 {s}개 **이상**")

    # ══ B 지표별 곡선 ══
    print("\n  ══ B **각 지표가 도달률을 얼마나 가르나** ══")
    print(머)
    for 라, f in 조건들:
        재기([x for x in 사건 if f(x)], f"✅ {라}")
        재기([x for x in 사건 if not f(x)], f"❌ {라} 아님")
        print()

    # ══ C 구간 나누기 ══
    print("  ══ C **몇 구간으로 나눠야 의미 있나** ══")
    for 축, 라 in (("상대갭", "상대갭"), ("낙폭60", "60일 낙폭"),
                    ("시총", "시총(억)"), ("배수", "거래대금 배수")):
        v = sorted(x[축] for x in 사건 if x.get(축) is not None)
        if len(v) < 100:
            continue
        print(f"\n    ── {라} ──")
        print(머)
        for i2, (a, b) in enumerate([(0, 25), (25, 50), (50, 75), (75, 100)]):
            lo = v[max(0, len(v) * a // 100 - 1)]
            hi = v[min(len(v) - 1, len(v) * b // 100)]
            재기([x for x in 사건
                  if x.get(축) is not None and lo <= x[축] <= hi],
                 f"{a}~{b}% ({lo:,.1f} ~ {hi:,.1f})")

    # ══ D 브리핑 표현 ══
    print("\n  ══ D ⭐ **브리핑에 실제로 쓸 숫자** ══")
    print("     ⚠️ 확률만 주면 과신을 부른다. **표본·평균일·최악**을 같이 준다")
    print()
    기본군 = 사건
    d2 = sum(1 for x in 기본군 if x["도달"])
    v = [x["결과"] for x in 기본군]
    print(f"    ┌ 기본 문구 ─────────────────────────────────────")
    print(f"    │ 과거 같은 조건 **{len(기본군):,}건** ({_시작[:4]}-{_시작[4:6]} ~ 2026-09)")
    print(f"    │   +20% 도달   **{d2/len(기본군)*100:.0f}%**  "
          f"(평균 {st.mean([x['며칠'] for x in 기본군]):.0f}거래일)")
    print(f"    │   손실 마감    {sum(1 for z in v if z<=0)/len(v)*100:.0f}%  "
          f"(최악 {min(v):+.1f}%)")
    print(f"    └────────────────────────────────────────────────")
    print()
    for 라, f in (("어젯밤 미국 −0.5%↓", lambda x: (x["미국"] or 9) <= -0.5),
                   ("시장도 같이 빠진 날", lambda x: x["시장갭"] < -0.3),
                   ("둘 다", lambda x: (x["미국"] or 9) <= -0.5
                    and x["시장갭"] < -0.3)):
        a = [x for x in 기본군 if f(x)]
        if len(a) < 20:
            continue
        d3 = sum(1 for x in a if x["도달"])
        print(f"    「{라}」이면 → 도달률 **{d3/len(a)*100:.0f}%** "
              f"(표본 {len(a):,}건 · 평균 {st.mean([x['며칠'] for x in a]):.0f}일)")

    print("\n  읽는 법")
    print("    - **A가 점수제의 전제를 검증한다.** 조건 개수와 도달률이 비례하지 않으면")
    print("       점수를 합산하는 방식은 **쓰면 안 된다**")
    print("    - B에서 ✅와 ❌의 도달률 차이가 큰 지표만 브리핑에 표시할 값어치가 있다")
    print("    - D가 실제 브리핑 문구다. **확률·표본·평균일·최악을 항상 같이** 준다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
