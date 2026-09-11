#!/usr/bin/env python3
r"""
final2_lab.py — **상대갭 + 공시 + 수급(4,102일 완성)** (2026-09-03 · 56차)

⚠️⚠️ **어제 최고 발견에 오늘 확인된 공시를 붙인다.**
```
어제(52·53차)  시장 −0.3%↓ + 상대 −4%p↓ + 볼하단 + 20일−10%↓ · 소형
              D+20 +18.10% · 승률 82.5% · 15해 15해 + · **연 66건**
              ⚠️ 문제: **투입비 24%** — 자금의 4분의 1만 쓴다

오늘(공시 3,202일)  자사주취득 D+20 +1.00* (t=**6.8**)  ← 유일한 호재
                  악재 8종 t=−3.0 ~ **−7.7** (최대주주변경·유상증자·BW·CB·소송·합병·감자·자사주처분정정)
```

## 두 가지를 시험한다
```
① **악재 공시 제외**
   상대갭 신호는 「빠진 걸 사는」 것이다.
   ⚠️ 그런데 **빠진 이유가 유상증자·최대주주변경이면 계속 빠진다.**
   → 최근 20일 안에 악재 공시가 난 종목을 빼면 성적이 오르나?
② **자사주취득을 별도 신호로 추가**
   투입비 24% 문제를 푼다 — 신호가 늘어야 자금을 쓴다
```

## 재는 것
```
A 상대갭 신호 (기준선)
B A + 악재 공시 제외 (최근 20일)
C A + 악재 제외 + 자사주취득 가점
D 자사주취득 단독 (별도 신호로 쓸 만한가)
E B ∪ D  (둘을 합쳐 빈도를 늘림)
```
⚠️ 판정: 절대 수익 · 승률 · **연도별** · 다음날 시가 매수 · D+20 · 비용 0.26%.
⚠️ 공시는 3,202일(13년)뿐 — 2010~2012 일부가 빠진다. 연도별에서 그게 보인다.
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
_보유 = 20
_악재 = r"유상증자|최대주주\s*변경|신주인수권|전환사채|소송|합병|감자|자기주식\s*처분"
_호재 = r"자기주식\s*취득"


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    수급 = O._수급()      # ⚠️ 2026-09-03: **4,102일 완성**됐다 (어제는 2,751일)
    날인 = {d: i for i, d in enumerate(날)}
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # 공시: 코드 -> [(i, 악재여부, 호재여부)]
    악재일, 호재일 = {}, {}
    공시날 = set()
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            g = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = g.get("기준일")
        i = 날인.get(d8)
        if i is None:
            continue
        공시날.add(i)
        for x in (g.get("챙길공시") or []):
            code = x.get("종목코드")
            n = re.sub(r"\[[^\]]*\]", "", str(x.get("공시명") or ""))
            if not code:
                continue
            if re.search(_악재, n):
                악재일.setdefault(code, set()).add(i)
            if re.search(_호재, n):
                호재일.setdefault(code, set()).add(i)
    print(f"  공시 있는 날 {len(공시날):,}일 · 악재 종목 {len(악재일):,} "
          f"· 자사주취득 종목 {len(호재일):,}", flush=True)

    갭표, 시장갭 = {}, {}
    앞종 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
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
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
    print(f"  거래일 {len(날):,}", flush=True)

    def 악재있나(code, i, 며칠=20):
        s = 악재일.get(code)
        if not s:
            return False
        return any(i - 며칠 <= x <= i for x in s)

    def 호재있나(code, i, 며칠=20):
        s = 호재일.get(code)
        if not s:
            return False
        return any(i - 며칠 <= x <= i for x in s)

    # ── 사건 수집 ──
    A, D = [], []      # A: 상대갭 신호 · D: 자사주취득 단독
    # ⚠️ 수급 조건을 같이 담는다 — 50차에서 「외인+기관이면 승률 63%→71%」가
    #    나왔는데 그건 수급 2,751일 기준이었다. 이제 4,102일로 재확인한다
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
        시갭 = 시장갭.get(다음)
        하루갭 = 갭표.get(다음) or {}
        공시커버 = i in 공시날
        fl = 수급.get(d1) or {}
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
            나 = 주가[다음].get(code)
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 나 or not 끝:
                continue
            g = 하루갭.get(code)
            if g is None:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            r = (끝[0] / 매수 - 1) * 100 - _비용
            악 = 악재있나(code, i)
            호 = 호재있나(code, i)
            f = fl.get(code) or {}
            외, 기 = (f.get("외국인") or 0), (f.get("기관") or 0)
            수급켬 = (1 if 외 > 0 else 0) | (2 if 기 > 0 else 0)
            # A: 상대갭 신호
            if 시갭 is not None and 시갭 < -0.3:
                sq = 종계[code]
                s20 = st.mean(sq[k - 19:k + 1])
                sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
                if ((c1 - s20) / (2 * sd) <= -1.0 and k >= 20 and sq[k - 20] > 0
                        and (c1 / sq[k - 20] - 1) * 100 <= -10
                        and (g - 시갭) <= -4):
                    A.append((d1[:4], code, r, 악, 호, 공시커버, 수급켬))
            # D: 자사주취득 단독 (그날 공시)
            if 호 and (호재일.get(code) and i in 호재일[code]):
                D.append((d1[:4], code, r, 악, 호, 공시커버, 수급켬))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · A {len(A):,} · D {len(D):,}", flush=True)

    년수 = len(날) / 245

    def 요약(목록, 이름):
        if len(목록) < 100:
            print(f"    {이름:<34}표본 부족 ({len(목록)})")
            return None
        수 = [x[2] for x in 목록]
        승 = sum(1 for x in 수 if x > 0) / len(수) * 100
        해별 = {}
        for x in 목록:
            해별.setdefault(x[0], []).append(x[2])
        전 = 플 = 0
        for y, arr in 해별.items():
            if len(arr) < 10:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        a2 = sorted(수)
        별 = "⭐" if (st.mean(수) > 0 and 승 >= 65 and 전 >= 10
                     and 플 / 전 >= 2 / 3) else "  "
        print(f"    {이름:<34}{st.mean(수):>+8.2f}%{승:>7.1f}%"
              f"{st.median(수):>+8.2f}%{a2[len(a2)//4]:>+9.2f}%"
              f"{len(수)/년수:>7.0f}건{f'{플}/{전}':>8}{len(수):>8,}{별}")
        return st.mean(수), 승, len(수)

    print(f"\n  ══ 상대갭 신호 + 공시 결합 (D+{_보유} · 다음날 시가 매수) ══")
    print(f"    {'조합':<34}{'평균':>9}{'승률':>8}{'중앙값':>9}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'표본':>8}")
    요약(A, "A 상대갭 신호 (기준선)")
    A공 = [x for x in A if x[5]]
    요약(A공, "A' 공시 있는 날만 (비교용)")
    B = [x for x in A공 if not x[3]]
    요약(B, "B  A + **악재 공시 제외**")
    B악 = [x for x in A공 if x[3]]
    요약(B악, "   (참고) 악재 있는 것만")
    C = [x for x in B if x[4]]
    요약(C, "C  B + 자사주취득 있음")
    요약(D, "D  자사주취득 단독")
    D악 = [x for x in D if not x[3]]
    요약(D악, "D' 자사주취득 + 악재 없음")
    E = B + D악
    요약(E, "E  B ∪ D' (합쳐서 빈도↑)")

    print(f"\n  ══ 연도별 — 「B: 상대갭 + 악재 제외」 ══")
    해별 = {}
    for x in B:
        해별.setdefault(x[0], []).append(x[2])
    print(f"    {'해':<7}{'건수':>7}{'평균':>10}{'승률':>8}")
    플, 전 = 0, 0
    for y in sorted(해별):
        arr = 해별[y]
        if len(arr) < 8:
            print(f"    {y:<7}{len(arr):>7}{'표본부족':>10}")
            continue
        승 = sum(1 for x in arr if x > 0) / len(arr) * 100
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
        표 = "⭐" if st.mean(arr) > 0 else "❌"
        print(f"    {y:<7}{len(arr):>7}{st.mean(arr):>+9.2f}%{승:>7.1f}%{표}")
    if 전:
        print(f"    ⇒ **{전}해 중 {플}해 + ({플/전*100:.0f}%)**")

    print(f"\n  ══ 연도별 — 「D' 자사주취득 + 악재 없음」 ══")
    해별 = {}
    for x in D악:
        해별.setdefault(x[0], []).append(x[2])
    print(f"    {'해':<7}{'건수':>7}{'평균':>10}{'승률':>8}")
    플, 전 = 0, 0
    for y in sorted(해별):
        arr = 해별[y]
        if len(arr) < 20:
            continue
        승 = sum(1 for x in arr if x > 0) / len(arr) * 100
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
        표 = "⭐" if st.mean(arr) > 0 else "❌"
        print(f"    {y:<7}{len(arr):>7}{st.mean(arr):>+9.2f}%{승:>7.1f}%{표}")
    if 전:
        print(f"    ⇒ **{전}해 중 {플}해 + ({플/전*100:.0f}%)**")

    print(f"\n  ══ ⭐ **수급 조건** (수급 4,102일 완성 후 재확인) ══")
    print("     ⚠️ 50차에서 「외인+기관이면 승률 63%→71%」가 나왔는데 그건 **2,751일** 기준이었다")
    print(f"    {'조합':<34}{'평균':>9}{'승률':>8}{'중앙값':>9}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'표본':>8}")
    for 라, 조건 in (("A 전체 (수급 무관)", lambda x: True),
                     ("A + 외국인 순매수", lambda x: x[6] & 1),
                     ("A + 기관 순매수", lambda x: x[6] & 2),
                     ("A + **외인+기관 둘 다**", lambda x: x[6] == 3),
                     ("A + 둘 다 아님", lambda x: x[6] == 0)):
        요약([x for x in A if 조건(x)], 라)
    print("\n    ── 악재 제외까지 걸면 ──")
    for 라, 조건 in (("B (악재 제외)", lambda x: True),
                     ("B + 외인+기관 둘 다", lambda x: x[6] == 3),
                     ("B + 기관 순매수", lambda x: x[6] & 2),
                     ("B + 외국인 순매수", lambda x: x[6] & 1)):
        요약([x for x in B if 조건(x)], 라)

    print("\n  읽는 법")
    print("    - **B > A'면 악재 제외가 값어치 있다** (같은 날짜 범위끼리 견줘야 공정하다)")
    print("    - D가 좋으면 **자사주취득을 별도 신호로 쓸 수 있다** → 빈도가 늘어난다")
    print("    - E의 연간 건수가 A보다 크게 늘면 **투입비 24% 문제를 풀 수 있다**")
    print("    - ⚠️ 공시가 3,202일(13년)이라 2010~2012 일부가 빠진다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
