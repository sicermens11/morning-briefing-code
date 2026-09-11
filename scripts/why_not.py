#!/usr/bin/env python3
r"""
why_not.py — **이 종목을 왜 안 뽑았나 / 왜 뽑았나** (2026-09-04 신설)

기존 브리핑이 고른 종목과 우리 규칙이 고른 종목이 다를 때
**어느 조건에서 갈렸는지**를 한 줄씩 보여준다.

쓰는 법:
    python scripts\why_not.py 010960 065450 052460
    python scripts\why_not.py 삼호개발 빅텍
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

확정 = {"갭": -3.5, "볼": -1.0, "낙": -10.0, "시총": 2e11}


def main():
    찾 = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not 찾:
        print("쓰는 법: python scripts/why_not.py 010960 065450 ...")
        return 1

    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기준일 = 날[-1]
    기본, 재무 = O._기본(), 연간재무()
    # 이름으로도 찾을 수 있게
    이름코드 = {}
    for c, v in 기본.items():
        이름코드[str(v.get("이름") or "")] = c
    코드들 = []
    for a in 찾:
        if a.isdigit() and len(a) == 6:
            코드들.append(a)
        elif a in 이름코드:
            코드들.append(이름코드[a])
        else:
            비슷 = [n for n in 이름코드 if a in n]
            if 비슷:
                코드들.append(이름코드[비슷[0]])
                print(f"  ('{a}' → {비슷[0]} {이름코드[비슷[0]]})")
            else:
                print(f"  ⚠️ 못 찾음: {a}")

    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

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

    print(f"\n  신호 기준일 **{기준일}** 종가")
    print(f"  ⚠️ 상대갭은 **다음 거래일 시가**로 정해진다 — 여기선 못 잰다\n")
    for code in 코드들:
        bb = 기본.get(code) or {}
        이름 = bb.get("이름", code)
        v = 주가[기준일].get(code)
        print(f"  ══ {이름} ({code}) ══")
        if not v:
            print(f"     ⚠️ {기준일} 주가 자료가 없다\n")
            continue
        c1, 시총, 대금 = v
        줄 = []

        def 재(라, ok, 값글):
            줄.append((라, ok, 값글))

        재("시총 2,000억 아래", 시총 < 확정["시총"], f"{시총/1e8:,.0f}억")
        재("거래대금 문턱", 대금 >= O._MIN_AMT, f"{대금/1e8:,.0f}억")
        부 = str(bb.get("업종") or "")
        재("관리종목·SPAC 아님",
           not (("관리종목" in 부) or ("SPAC" in 부))
           and bb.get("증권구분") in (None, "주권"),
           str(bb.get("증권구분") or "주권"))
        fm = 재무값(code, 기준일)
        if fm:
            재("잉여금비율 ≥30%", fm.get("잉여금비율", -9e9) >= 30,
               f"{fm.get('잉여금비율', 0):,.0f}%")
            재("부채비율 ≤80%", fm.get("부채비율", 9e9) <= 80,
               f"{fm.get('부채비율', 0):,.0f}%")
            재("흑자", fm.get("흑자") == 1.0,
               "흑자" if fm.get("흑자") == 1.0 else "적자")
        else:
            재("연간 재무 자료", False, "없음")
        kk = (자리.get(code) or {}).get(기준일)
        if kk is not None and kk >= 250:
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            재("볼린저 −1.0σ 아래", 볼 <= 확정["볼"], f"{볼:+.2f}σ")
            if sq[kk - 20] > 0:
                낙 = (c1 / sq[kk - 20] - 1) * 100
                재("20일 낙폭 −10% 아래", 낙 <= 확정["낙"], f"{낙:+.1f}%")
            else:
                재("20일 낙폭", False, "계산 불가")
        else:
            재("상장 250일 이상", False, f"{kk}일")
        떨 = [x for x in 줄 if not x[1]]
        for 라, ok, 값글 in 줄:
            print(f"     {'✅' if ok else '❌'} {라:<22}{값글}")
        if 떨:
            print(f"     ⇒ **{len(떨)}개 조건에서 탈락**: "
                  f"{' · '.join(x[0] for x in 떨)}")
        else:
            print(f"     ⇒ ⭐ **08:00 조건 전부 통과** — "
                  f"다음날 시가에서 상대갭만 보면 된다")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
