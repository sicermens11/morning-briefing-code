#!/usr/bin/env python3
r"""
reverse_lab.py — **크게 오른 종목의 공통점은 뭐였나** (2026-09-01 신설)

⚠️⚠️ **다른 13개와 방향이 반대다.**
```
나머지    조건을 정해놓고 → 그 조건일 때 성적이 어땠나       (가설 검정)
이것      크게 오른 종목을 모아놓고 → 그것들의 공통점은?     (역추적)
```

⚠️⚠️⚠️ **그리고 이 스크립트가 답하는 가장 중요한 질문:**
```
「우리 방식(공시 기반)이 상승 종목의 몇 %를 잡아내나」
→ 우리는 **공시가 난 종목**에서만 출발한다.
→ 공시 없이 오르는 종목은 아예 안 본다.
→ 잡아내는 비율이 낮으면, 규칙을 아무리 다듬어도 **대부분을 놓친다.**
```

**어떻게 재나**: 각 날짜에서 D+5 초과수익 **상위 5% / 하위 5%** 종목을 모아,
**그 전날의 특성 분포**를 비교한다.

⚠️⚠️ **사후편향(hindsight bias)에 주의한다.** "오른 종목은 이랬다"는 사실이지만
   "이러면 오른다"는 결론이 아니다. **역추적은 발견의 출발점일 뿐** —
   찾은 것은 `combo_lab`처럼 학습/검증을 갈라 다시 검증해야 한다.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = 5
_꼬리 = 0.05          # 상·하위 5%


def main():
    print("  자료 읽는 중…", flush=True)
    주가 = O._주가()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)
    재무 = O._분기재무()
    임원 = O._이벤트("dart-exec")
    컨센 = O._컨센()

    특성 = {"상위": [], "하위": [], "전체": []}
    for i, d1 in enumerate(날):
        j = i + _H
        if j >= len(날):
            break
        a, b = 지수.get(d1), 지수.get(날[j])
        if not a or not b:
            continue
        s1, s2 = 주가[d1], 주가[날[j]]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}
        구 = set(날[max(0, i - 20):i + 1])
        오늘 = []
        for code, v1 in s1.items():
            c1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            v2 = s2.get(code)
            if not v2:
                continue
            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            초 = ((v2[0] / c1 - 1) - (b[장] / a[장] - 1)) * 100
            오늘.append((초, code, v1))
        if len(오늘) < 100:
            continue
        오늘.sort()
        n = max(1, int(len(오늘) * _꼬리))
        묶음 = [("하위", 오늘[:n]), ("상위", 오늘[-n:]), ("전체", 오늘)]
        for 이름, 목록 in 묶음:
            for 초, code, v1 in 목록:
                c1, 시총, 대금, 등락, 코스닥 = v1
                r = ds.get(code) or {}
                f = fl.get(code) or {}
                fin = {}
                for 적용, 값 in (재무.get(code) or []):
                    if 적용 <= d1:
                        fin = 값
                    else:
                        break
                bb = 기본.get(code) or {}
                부 = str(bb.get("업종") or "")
                특성[이름].append({
                    "공시": bool(r),
                    "호재": "호재" in r.get("성격", set()),
                    "장후": r.get("분") is not None and r["분"] >= 930,
                    "무반응": abs(등락) < 1,
                    "급등5": 등락 >= 5, "급락5": 등락 <= -5,
                    "수급": (f.get("외국인") or 0) > 0 and (f.get("기관") or 0) > 0,
                    "외인매수": (f.get("외국인") or 0) > 0,
                    "코스닥": bool(코스닥),
                    "대형주": 시총 >= 1e12, "소형주": 시총 < 3e11,
                    "거래활발": 대금 >= 1e10,
                    "적자": (fin.get("순이익률") is not None and fin["순이익률"] < 0),
                    "부채높음": (fin.get("부채비율") is not None and fin["부채비율"] >= 200),
                    "임원신고": bool((임원.get(code) or set()) & 구),
                    "컨센있음": bool((컨센.get(code) or {}).get(d1)),
                    "더럽": (("관리종목" in 부) or ("SPAC" in 부)
                             or (str(bb.get("상장일") or "") > "20240101")
                             or (bb.get("증권구분") not in (None, "주권"))),
                })
        if i % 150 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    키 = list(특성["전체"][0]) if 특성["전체"] else []
    print(f"\n  표본: 상위 {len(특성['상위']):,} · 하위 {len(특성['하위']):,} "
          f"· 전체 {len(특성['전체']):,}  (D+{_H} 초과수익 상·하위 {_꼬리*100:.0f}%)\n")
    print(f"  {'특성':<12}{'상위5%':>9}{'하위5%':>9}{'전체':>9}{'상위-전체':>11}  판정")
    줄 = []
    for k in 키:
        v = {n: sum(1 for x in 특성[n] if x[k]) / max(1, len(특성[n])) * 100
             for n in ("상위", "하위", "전체")}
        줄.append((v["상위"] - v["전체"], k, v))
    줄.sort(reverse=True)
    for 차, k, v in 줄:
        판 = ("↑ 상승과 함께 나타남" if 차 >= 2 else
              ("↓ 하락과 함께" if 차 <= -2 else "· 차이 없음"))
        print(f"  {k:<12}{v['상위']:>8.1f}%{v['하위']:>8.1f}%{v['전체']:>8.1f}%"
              f"{차:>+10.1f}%p  {판}")

    # ⚠️ 가장 중요한 숫자
    상 = 특성["상위"]
    if 상:
        공 = sum(1 for x in 상 if x["공시"]) / len(상) * 100
        호 = sum(1 for x in 상 if x["호재"]) / len(상) * 100
        갭 = sum(1 for x in 상 if x["호재"] and x["장후"] and x["무반응"]) / len(상) * 100
        print(f"\n  ══════ ⚠️⚠️ 우리 방식의 커버리지 ══════")
        print(f"    크게 오른 종목(상위 5%) 중")
        print(f"      공시가 있던 것          {공:>5.1f}%")
        print(f"      호재 공시였던 것         {호:>5.1f}%")
        print(f"      갭①④(호재+장후+무반응)   {갭:>5.1f}%   ← **우리가 잡아내는 비율**")
        print(f"\n    ⚠️ 이 비율이 낮으면 규칙을 아무리 다듬어도 **대부분을 놓친다.**")
        print(f"       그건 규칙이 나쁜 게 아니라 **출발점(공시)이 좁다**는 뜻이다.")
    print("\n  ⚠️⚠️ **사후편향 주의.** 「오른 종목은 이랬다」는 사실이지만")
    print("     「이러면 오른다」는 결론이 아니다. 찾은 것은 학습/검증을 갈라 다시 재야 한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
