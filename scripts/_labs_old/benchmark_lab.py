#!/usr/bin/env python3
r"""
benchmark_lab.py — **「전부 음수」가 신호 탓인가 벤치마크 탓인가** (2026-09-02 · 2차)

⚠️⚠️⚠️ **1차 실험의 가장 큰 미해결 문제.**
   `origin_lab`에서 여덟 출발점이 **전부 음수**로 나왔다. 그런데 사실상 전 종목인
   「강한 시장 소속」(하루 735종목)조차 D+20 **−1.50**이었다.
   → **개별 종목 평균이 시총가중 지수를 못 따라간 것**일 수 있다.
      코스피가 2.6년에 **+155%**였고 **대형주가 그걸 끌어올렸다.**
   → 그렇다면 「음수」는 **신호가 나쁜 게 아니라 잣대가 가혹한 것**이다.

**세 가지 잣대로 같은 신호를 나란히 잰다**
```
① 시총가중 지수    실제 코스피/코스닥      ← 지금 쓰는 것. 대형주가 지배한다
② 동일가중 평균    그날 거래된 전 종목 평균  ← 「보통 종목」이 기준
③ 크기군 평균     같은 시총 구간 평균      ← 대형주는 대형주끼리 비교
```
⚠️ **③이 가장 공정하다** — 소형주 신호를 대형주 지수와 비교하는 건 애초에 불공평하다.

**읽는 법**
```
①에서 음수인데 ②③에서 양수  →  **잣대 문제였다.** 신호는 살아 있다
①②③ 모두 음수             →  **신호가 진짜 나쁘다**
```
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = (1, 5, 20)
_MIN = 100
_구간 = [("소형(3천억↓)", 0, 3e11), ("중형(3천억~1조)", 3e11, 1e12),
         ("대형(1조↑)", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in _구간:
        if a <= 시총 < b:
            return 이름
    return _구간[-1][0]


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O._주가()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)
    fsc = O._fscore()

    종가계, 대금계, 자리 = {}, {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종가계.setdefault(c, []).append(v[0])
            대금계.setdefault(c, []).append(v[2])
            자리.setdefault(c, {})[d] = len(종가계[c]) - 1
    print(f"  준비 완료 · 종목 {len(종가계):,}", flush=True)

    통 = {}

    def 담(k, v):
        s = 통.setdefault(k, [0.0, 0])
        s[0] += v
        s[1] += 1

    for i, d1 in enumerate(날):
        if i + 1 >= len(날) or i < 21:
            continue
        a0 = 지수.get(날[i + 1])
        if not a0:
            continue
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}
        창 = [지수[d]["KOSPI"] for d in 날[i - 20:i + 1] if 지수.get(d)]
        조정 = len(창) >= 15 and 지수[d1]["KOSPI"] < st.mean(창)

        # 그날 거래 가능한 종목 목록(오염 제외)
        후보 = []
        for code, v1 in s1.items():
            c1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (str(bb.get("상장일") or "") > "20240101")
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            if 주가[날[i + 1]].get(code):
                후보.append((code, v1))
        if len(후보) < 100:
            continue

        for h in _H:
            j = i + 1 + h
            if j >= len(날) or not 지수.get(날[j]):
                continue
            sJ = 주가[날[j]]
            b = 지수[날[j]]
            # ── 잣대 ② 동일가중 · ③ 크기군 평균 ──
            수익들, 크기별 = [], {}
            for code, v1 in 후보:
                매수 = 주가[날[i + 1]].get(code)
                vv = sJ.get(code)
                if not 매수 or not vv:
                    continue
                r = vv[0] / 매수[0] - 1
                수익들.append(r)
                크기별.setdefault(_크기(v1[1]), []).append(r)
            if len(수익들) < 50:
                continue
            동일 = st.mean(수익들)
            군평 = {k: st.mean(v) for k, v in 크기별.items() if len(v) >= 20}

            for code, v1 in 후보:
                c1, 시총, 대금, 등락, 코스닥 = v1
                매수 = 주가[날[i + 1]].get(code)
                vv = sJ.get(code)
                if not 매수 or not vv:
                    continue
                r = vv[0] / 매수[0] - 1
                장 = "KOSDAQ" if 코스닥 else "KOSPI"
                시총가중 = b[장] / a0[장] - 1
                군 = 군평.get(_크기(시총))

                # ── 신호 판정 ──
                rr = ds.get(code) or {}
                f = fl.get(code) or {}
                외 = f.get("외국인") or 0
                기 = f.get("기관") or 0
                k = (자리.get(code) or {}).get(d1)
                신고 = 거3 = False
                if k is not None and k >= 240:
                    신고 = c1 >= max(종가계[code][k - 240:k + 1]) * 0.999
                if k is not None and k >= 20:
                    평 = st.mean(대금계[code][k - 20:k]) or 1
                    거3 = 대금 >= 평 * 3
                F = max([v for 적, v in (fsc.get(code) or {}).items() if 적 <= d1],
                        default=None)
                강도 = ((외 + 기) * c1 / 시총 * 100) if 시총 > 0 else 0
                호재 = "호재" in rr.get("성격", set())
                장후 = rr.get("분") is not None and rr["분"] >= 930

                신호 = ["0 전 종목(기준선)"]
                if 호재:
                    신호.append("1 호재 공시")
                    if 장후:
                        신호.append("2 갭1 호재+장후")
                        if abs(등락) < 1:
                            신호.append("3 갭1+4 +무반응")
                if 강도 >= 0.5:
                    신호.append("4 수급강도 0.5%+")
                if 신고:
                    신호.append("5 52주 신고가")
                if 거3:
                    신호.append("6 거래량 3배+")
                if F is not None and F >= 6:
                    신호.append("7 F-Score 6점+")
                if 조정 and 호재:
                    신호.append("8 호재 + 20일선아래")

                for s in 신호:
                    담((s, "1 시총가중", h), (r - 시총가중) * 100)
                    담((s, "2 동일가중", h), (r - 동일) * 100)
                    if 군 is not None:
                        담((s, "3 크기군평균", h), (r - 군) * 100)
        if i % 100 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    신호들 = ["0 전 종목(기준선)", "1 호재 공시", "2 갭1 호재+장후", "3 갭1+4 +무반응",
              "4 수급강도 0.5%+", "5 52주 신고가", "6 거래량 3배+", "7 F-Score 6점+",
              "8 호재 + 20일선아래"]
    잣대들 = ["1 시총가중", "2 동일가중", "3 크기군평균"]
    print("\n  매수 D+1 종가 · 오염 종목 제외 · 세 잣대 비교\n")
    print(f"  {'신호':<22}{'잣대':<14}{'D+1':>16}{'D+5':>16}{'D+20':>16}")
    for s in 신호들:
        for 잣 in 잣대들:
            칸 = []
            for h in _H:
                t = 통.get((s, 잣, h))
                칸.append(f"{t[0] / t[1]:+.3f}({t[1] // 1000}k)"
                          if t and t[1] >= _MIN else "-")
            if all(c == "-" for c in 칸):
                continue
            print(f"  {s if 잣 == 잣대들[0] else '':<22}{잣:<14}"
                  + "".join(f"{c:>16}" for c in 칸))
        print()
    print("  읽는 법")
    print("    - 시총가중에서 음수인데 동일가중·크기군에서 양수면 '잣대 문제'였다")
    print("    - 셋 다 음수면 신호가 진짜 나쁘다")
    print("    - '0 전 종목'이 각 잣대의 기준선이다. 동일가중/크기군은 정의상 0에 가까워야 한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
