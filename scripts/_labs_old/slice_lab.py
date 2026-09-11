#!/usr/bin/env python3
r"""
slice_lab.py — **모든 축으로 쪼개서 본다** (2026-09-02 · 9차)

⚠️⚠️ **사용자 요청.**
   *"종목별, 일별, 월별, 분기별, 계절별, 연별, 장기, 섹터별, 다양한 측면으로 쪼개서
   분석하는 것도 필요한 것 같아."*
   → **맞다.** 7차에서 「전 종목으로 뭉쳐 보다가 대형주로 쪼개니 답이 달라진」 일이 있었다.
      뭉치면 놓친다.

**쪼개는 축**
```
시간   요일 · 월 · 분기 · 계절 · 연도 · 상반기/하반기
크기   시총 4구간 · 거래대금 3구간
시장   코스피 / 코스닥
상태   52주 신고가 여부 · 20일선 위/아래 · 최근 20일 변동성 3구간
```
**그리고 「신고가+대형주」 신호를 이 축들로 다시 쪼갠다** — 어느 조건에서 사는지 본다.

⚠️⚠️ **다중검정 위험을 반드시 안고 읽는다.**
   축이 많을수록 **우연히 좋아 보이는 칸**이 나온다. 그래서 **학습/검증을 갈라** 찍는다.
   **학습·검증 둘 다 좋은 칸만** 의미가 있다.

⚠️ 잣대는 **동일가중 초과수익**(시총가중은 착시를 만든다 — 2차에서 확인).
⚠️ 매수 D+1 종가 · D+20 보유 · 오염 제외 · 16.7년.
"""
import datetime as dt
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = 20
_경계 = "20180101"
_MIN = 500          # 칸마다 이 표본 미만이면 "-"


def _주가():
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                if 종 <= 0:
                    continue
                하루[c] = (종, float(v.get("시총") or 0), float(v.get("거래대금") or 0),
                           float(v.get("등락률") or 0),
                           1 if "KOSDAQ" in str(v.get("시장", "")).upper() else 0)
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    종가계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종가계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종가계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종가계):,}", flush=True)

    # (축, 칸, 구간, 신호여부) -> [초과수익…]
    통 = {}

    def 담(축, 칸, 구간, 신호, v):
        통.setdefault((축, 칸, 구간, 신호), []).append(v)

    계절 = {12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄",
            6: "여름", 7: "여름", 8: "여름", 9: "가을", 10: "가을", 11: "가을"}

    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + _H >= len(날):
            continue
        구간 = "학습" if d1 < _경계 else "검증"
        y, m, dd = int(d1[:4]), int(d1[4:6]), int(d1[6:])
        요일 = "월화수목금토일"[dt.date(y, m, dd).weekday()]
        분기 = f"{(m - 1) // 3 + 1}분기"
        반기 = "상반기" if m <= 6 else "하반기"

        s1 = 주가[d1]
        후보, 수익 = [], []
        for code, v in s1.items():
            c1, 시총, 대금, 등락, 코스닥 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            mm = 주가[날[i + 1]].get(code)
            ee = 주가[날[i + 1 + _H]].get(code)
            if not mm or not ee:
                continue
            # ⚠️⚠️ 기준선 불일치 버그(2026-09-02 발견).
            #    기준선은 「모든 후보」로 계산하는데 집계는 「상장 250일 넘은 것」만 했다.
            #    → 신규상장 종목이 기준에만 들어가 **모든 축이 +0.05% 정도 밀렸다.**
            #    여기서 미리 걸러 기준선과 집계 대상을 **같게** 맞춘다.
            if ((자리.get(code) or {}).get(d1) or 0) < 250:
                continue
            후보.append((code, v, ee[0] / mm[0] - 1))
            수익.append(ee[0] / mm[0] - 1)
        if len(후보) < 100:
            continue
        기준 = st.mean(수익)

        for code, v, r in 후보:
            c1, 시총, 대금, 등락, 코스닥 = v
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            seq = 종가계[code]
            신고 = c1 >= max(seq[k - 250:k + 1]) * 0.999
            큼 = 시총 >= 1e12
            신호 = 신고 and 큼          # ← 8차에서 남은 후보의 뼈대
            초 = (r - 기준) * 100

            s20 = st.mean(seq[k - 20:k + 1])
            변 = st.pstdev([seq[j] / seq[j - 1] - 1 for j in range(k - 19, k + 1)]) * 100

            칸들 = [
                ("요일", 요일), ("월", f"{m:02d}월"), ("분기", 분기),
                ("계절", 계절[m]), ("반기", 반기), ("연도", str(y)),
                ("시총", "1조↑" if 시총 >= 1e12 else
                 ("3천억~1조" if 시총 >= 3e11 else
                  ("1천억~3천억" if 시총 >= 1e11 else "1천억↓"))),
                ("거래대금", "100억↑" if 대금 >= 1e10 else
                 ("10억~100억" if 대금 >= 1e9 else "10억↓")),
                ("시장", "코스닥" if 코스닥 else "코스피"),
                ("신고가", "신고가" if 신고 else "아님"),
                ("20일선", "위" if c1 > s20 else "아래"),
                ("변동성", "높음(3%↑)" if 변 >= 3 else ("낮음(1.5%↓)" if 변 < 1.5 else "보통")),
            ]
            for 축, 칸 in 칸들:
                담(축, 칸, 구간, False, 초)
                if 신호:
                    담(축, 칸, 구간, True, 초)
        if i % 400 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    def 찍기(신호여부, 제목):
        print(f"\n{'='*96}\n{제목}\n{'='*96}")
        축순 = ["요일", "월", "분기", "계절", "반기", "연도", "시총", "거래대금",
                "시장", "신고가", "20일선", "변동성"]
        for 축 in 축순:
            칸들 = sorted({c for (a, c, _, s) in 통 if a == 축 and s == 신호여부})
            if not 칸들:
                continue
            print(f"\n  ── {축} ──")
            print(f"    {'칸':<14}{'전체':>18}{'학습':>18}{'검증':>18}  판정")
            for 칸 in 칸들:
                줄 = {}
                모 = []
                for g in ("학습", "검증"):
                    a = 통.get((축, 칸, g, 신호여부)) or []
                    모 += a
                    줄[g] = (st.mean(a), len(a)) if len(a) >= _MIN else None
                전 = (st.mean(모), len(모)) if len(모) >= _MIN else None
                if not 전:
                    continue
                def f(x):
                    return f"{x[0]:+.3f}% ({x[1]//1000}k)" if x else "-"
                판 = ""
                if 줄["학습"] and 줄["검증"]:
                    if 줄["학습"][0] > 0 and 줄["검증"][0] > 0:
                        판 = "⭐ 둘 다 +"
                    elif 줄["학습"][0] < 0 and 줄["검증"][0] < 0:
                        판 = "❌ 둘 다 −"
                    else:
                        판 = "· 뒤집힘"
                print(f"    {칸:<14}{f(전):>18}{f(줄['학습']):>18}{f(줄['검증']):>18}  {판}")

    찍기(False, "① 전 종목 — 축별 초과수익 (동일가중 대비 · D+20)")
    찍기(True, "② 「52주 신고가 + 시총 1조↑」 신호 — 같은 축으로 쪼갬")
    print("\n  읽는 법")
    print("    - ⚠️ 축이 많아 **우연히 좋아 보이는 칸**이 반드시 나온다")
    print("    - **학습·검증 둘 다 +**인 칸만 의미가 있다 (⭐)")
    print("    - '뒤집힘'은 한쪽만 좋다는 뜻 = 우연일 가능성이 높다")
    print("    - ①과 ②를 비교해야 한다. ①이 이미 좋은 칸이면 신호 덕이 아니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
