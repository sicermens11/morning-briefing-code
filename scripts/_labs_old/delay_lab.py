#!/usr/bin/env python3
r"""
delay_lab.py — **사건 후 며칠째에 사야 하나 · 며칠 들고 있나** (2026-09-02 · 37차)

⚠️⚠️ **사용자 취지 — 브리핑 구조를 바꾸는 발상.**
   *"공시 후 3일 뒤 통상적으로 상승 반응이 왔다는 데이터가 많았다면, 공시 후 3일 아침 브리핑에
   「공시 후 3일 뒤 해당 종목, 상승 가능성 높음」 이런 식으로 쓴다든가"*
   *"매수와 매도를 어느 타이밍에 하면 좋은지 브리핑에 기재되어 있으면 좋다는 뜻"*

## 브리핑 구조가 달라진다
```
지금    「**오늘** 공시 난 종목」을 보여준다
제안    「**오늘이 매수 적기인** 종목」을 보여준다
        → 그 이유는 3일 전 공시일 수도, 5일 전 신고가일 수도 있다
```
⚠️ 31차 `flow_lab`이 이미 그쪽을 가리켰다:
```
신고가 1일차 +1.06  <  4~5일차 **+1.83**   (중형)
⇒ 「오늘 신고가 났다」보다 **「4일 전부터 신고가인데 아직 이어지는 중」**이 낫다
```

## 재는 것 — **사건 후 N일째 종가에 사서 M일 들고 있으면 얼마 버나**
```
사건    ① 52주 신고가 **처음** 난 날
        ② RSI 과매수 **처음** 진입한 날
        ③ 볼린저 하단 **처음** 이탈한 날
        ④ 공시 (호재/악재 유형별) — ⚠️ 909일뿐이라 예비
진입    사건 후 **1·2·3·5·7·10·15·20일째** 종가
보유    **10 · 20 · 60일**
```
⚠️ **판정은 절대 수익**이다 (사용자 지적, 35차). 왕복비용 0.26% 차감.
   평균 · 승률 · 중앙값 · 하위25%(최악)를 같이 낸다.
⚠️ 「사건 후 N일째」를 쓰려면 그날까지 살아 있어야 한다 — 거래정지·상폐는 제외된다(생존편향).
   그래서 **표본 수를 같이 찍어** 얼마나 빠졌는지 보이게 한다.
"""
import glob
import io
import json
import os
import re
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_지연들 = (1, 2, 3, 5, 7, 10, 15, 20)
_보유들 = (10, 20, 60)
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]

유형규칙 = [
    ("계약해지", r"공급계약해지|계약해지"), ("수주계약", r"단일판매|공급계약"),
    ("유상증자", r"유상증자"), ("무상증자", r"무상증자"),
    ("전환사채CB", r"전환사채"), ("신주인수권BW", r"신주인수권"),
    ("자사주취득", r"자기주식\s*취득"), ("자사주처분", r"자기주식\s*처분"),
    ("배당", r"배당"), ("실적", r"영업실적|손익구조|매출액또는손익"),
    ("최대주주변경", r"최대주주\s*변경"), ("합병", r"합병"), ("분할", r"분할"),
    ("소송", r"소송"), ("감자", r"감자"), ("횡령배임", r"횡령|배임"),
    ("시설투자", r"신규시설투자|시설투자"), ("특허", r"특허"),
]


def _유형(이름):
    n = re.sub(r"\[[^\]]*\]", "", str(이름 or ""))
    for 라벨, 패턴 in 유형규칙:
        if re.search(패턴, n):
            return 라벨
    return None


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본 = O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    # ── 사건 목록 만들기 ──
    print("  사건 찾는 중...", flush=True)
    사건 = {}          # 사건이름 -> [(i, code, 크기)]
    앞상태 = {}
    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + max(_지연들) + max(_보유들) >= len(날):
            앞상태 = {}
            continue
        오늘 = {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
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
            고 = max(sq[k - 250:k + 1])
            신 = bool(고) and c1 >= 고 * 0.999
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            상태 = (신, rsi >= 70, 볼 <= -1.0)
            오늘[code] = 상태
            앞 = 앞상태.get(code)
            if 앞 is None:
                continue
            g = _크기(시총)
            if 상태[0] and not 앞[0]:
                사건.setdefault("① 신고가 첫날", []).append((i, code, g))
            if 상태[1] and not 앞[1]:
                사건.setdefault("② RSI 과매수 진입", []).append((i, code, g))
            if 상태[2] and not 앞[2]:
                사건.setdefault("③ 볼린저 하단 이탈", []).append((i, code, g))
        앞상태 = 오늘
        if i % 500 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    # ── 공시 사건 ──
    날인덱스 = {d: i for i, d in enumerate(날)}
    공시수 = 0
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            g = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = g.get("기준일")
        i = 날인덱스.get(d8)
        if i is None or i < 250 or i + 1 + max(_지연들) + max(_보유들) >= len(날):
            continue
        for x in (g.get("챙길공시") or []):
            code = x.get("종목코드")
            if not code or code not in 주가[d8]:
                continue
            v = 주가[d8][code]
            if v[1] < O._MIN_MC or v[2] < O._MIN_AMT:
                continue
            라벨 = _유형(x.get("공시명"))
            if not 라벨:
                continue
            사건.setdefault(f"공 {라벨}", []).append((i, code, _크기(v[1])))
            공시수 += 1
    print(f"  사건: " + " · ".join(f"{k} {len(v):,}" for k, v in sorted(사건.items()))
          [:400], flush=True)

    def 성과(목록, 지연, 보유):
        a = []
        for (i, code, g) in 목록:
            j = i + 지연
            e = j + 보유
            if e >= len(날):
                continue
            m = 주가[날[j]].get(code)
            x = 주가[날[e]].get(code)
            if not m or not x:
                continue
            a.append((x[0] / m[0] - 1) * 100 - _비용)
        return a

    이름들 = sorted(사건)
    print(f"\n  ══ 사건 후 **며칠째에 사면** 얼마 버나 (절대 수익 · 비용 {_비용}% 차감) ══")
    print("     ⚠️ 판정은 절대 수익이다. 평균과 **승률**을 같이 본다")
    for 이름 in 이름들:
        목록 = 사건[이름]
        if len(목록) < 500:
            continue
        for 보유 in _보유들:
            줄 = []
            보 = False
            for 지연 in _지연들:
                a = 성과(목록, 지연, 보유)
                if len(a) < 300:
                    줄.append("-")
                    continue
                보 = True
                승 = sum(1 for x in a if x > 0) / len(a) * 100
                줄.append(f"{st.mean(a):+.2f}({승:.0f}%)")
            if 보:
                if 보유 == _보유들[0]:
                    print(f"\n  ── {이름} (표본 {len(목록):,}) ──")
                    print(f"    {'보유':<8}" + "".join(f"{'D+'+str(x):>14}" for x in _지연들))
                print(f"    {str(보유)+'일':<8}" + "".join(f"{x:>14}" for x in 줄))

    # 크기별로 가장 좋은 조합
    print(f"\n\n  ══ 크기별 최적 (평균 수익이 가장 큰 진입·보유 조합) ══")
    print(f"    {'사건':<20}{'크기':<6}{'최적 진입':>10}{'보유':>7}"
          f"{'평균':>9}{'승률':>7}{'중앙값':>9}{'하위25%':>9}{'표본':>9}")
    for 이름 in 이름들:
        for g, _, _ in 크기표:
            목록 = [x for x in 사건[이름] if x[2] == g]
            if len(목록) < 500:
                continue
            최고 = None
            for 지연 in _지연들:
                for 보유 in _보유들:
                    a = 성과(목록, 지연, 보유)
                    if len(a) < 300:
                        continue
                    m = st.mean(a)
                    if 최고 is None or m > 최고[0]:
                        최고 = (m, 지연, 보유, a)
            if not 최고:
                continue
            m, 지연, 보유, a = 최고
            a2 = sorted(a)
            승 = sum(1 for x in a2 if x > 0) / len(a2) * 100
            별 = "⭐" if (m > 0 and 승 >= 50) else ("  " if m > 0 else "❌")
            print(f"    {이름:<20}{g:<6}{'D+'+str(지연):>10}{str(보유)+'일':>7}"
                  f"{m:>+8.2f}%{승:>6.0f}%{st.median(a2):>+8.2f}%"
                  f"{a2[len(a2)//4]:>+8.2f}%{len(a2):>9,}{별}")

    print("\n  읽는 법")
    print("    - 표의 값은 **평균 수익(승률)**이다. 둘 다 봐야 한다")
    print("    - **D+1이 가장 좋지 않으면 「오늘 사라」가 아니라 「N일 뒤 사라」가 맞다**")
    print("      → 브리핑에 「3일 전 공시 난 종목, 오늘이 적기」 같은 걸 쓸 근거가 된다")
    print("    - ⚠️ 공시는 909일(2.6년)뿐이라 예비다. 09-04에 4,102일로 다시 돌린다")
    print("    - ⚠️ 사건 후 N일째까지 살아 있어야 세어진다 → 상폐·거래정지가 빠진 생존편향이 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
