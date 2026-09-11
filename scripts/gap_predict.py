#!/usr/bin/env python3
r"""
gap_predict.py — **「선별이 통할 시기」를 미리 알 수 있나** (2026-09-02 · 25차)

⚠️⚠️ **24차에서 나온 것.**
```
코스피(시총가중) − 전종목 동일가중 평균 = 「격차」
격차가 + 인 해  → 초대형주가 지수를 끌어올린 해. **선별로는 못 이긴다** (8해)
격차가 − 인 해  → 개별 종목이 지수보다 나은 해. **선별이 값어치 있다** (5해)
17해 평균 +4.9%p — 구조적으로 지수가 유리하다
```

## 그래서 이걸 재야 한다
```
격차를 **미리 알 수 있나?**
  알 수 있다 → 그 시기엔 선별 비중을 높인다 (동적 배분)
  알 수 없다 → **지수 기본 + 선별 고정 비중**이 답이다 (그게 최종 구조)
```
⚠️ 연도로 재면 표본이 17개뿐이다. **월 단위**로 잰다 (표본 ~190개).

## 미리 아는 것으로 뒤를 맞힐 수 있나 — 후보 넷
```
① 지속성      지난 3개월 격차 → 다음 1·3개월 격차       (추세가 이어지나)
② 시장 국면    코스피 200일 수익률 → 다음 격차           (강세장이 초대형주 장세인가)
③ 집중도      상위 10종목 시총 비중 → 다음 격차          (쏠림이 더 쏠리나)
④ 변동성      코스피 60일 변동성 → 다음 격차
```
⚠️ 전부 **그 시점까지의 정보만** 쓴다. 상관계수와 구간별 평균을 같이 낸다.
"""
import glob
import io
import json
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402


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
                하루[c] = (종, float(v.get("시총") or 0), float(v.get("거래대금") or 0))
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def _상관(A, B):
    n = min(len(A), len(B))
    if n < 20:
        return 0.0, 0.0
    A, B = A[:n], B[:n]
    ma, mb = st.mean(A), st.mean(B)
    sa = st.pstdev(A) or 1e-9
    sb = st.pstdev(B) or 1e-9
    r = sum((A[i] - ma) * (B[i] - mb) for i in range(n)) / n / (sa * sb)
    t = r * math.sqrt(max(1, n - 2)) / math.sqrt(max(1e-9, 1 - r * r))
    return r, t


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    print(f"  거래일 {len(날):,}", flush=True)

    # 월 경계
    달 = []
    앞 = None
    for i, d in enumerate(날):
        if d[:6] != 앞:
            달.append((d[:6], i))
            앞 = d[:6]
    print(f"  달 {len(달)}개", flush=True)

    # 달마다: 그 달의 격차 · 그 시점의 예측 후보들
    행 = []
    ixv, 앞x = [], None
    for d in 날:
        x = (지수.get(d) or {}).get("KOSPI") or 앞x
        if x:
            앞x = x
        ixv.append(x)

    for j in range(len(달) - 1):
        ym, i0 = 달[j]
        i1 = 달[j + 1][1] - 1
        if i0 < 250 or i1 <= i0:
            continue
        s0 = 주가[날[i0]]
        후 = []
        for code, v in s0.items():
            c0, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            끝값 = None
            for k in range(i1, i0, -1):
                v2 = 주가[날[k]].get(code)
                if v2:
                    끝값 = v2[0]
                    break
            if not 끝값:
                continue
            후.append((시총, (끝값 / c0 - 1) * 100))
        if len(후) < 100 or not ixv[i0] or not ixv[i1]:
            continue
        지 = (ixv[i1] / ixv[i0] - 1) * 100
        동 = st.mean([r for _, r in 후])
        격 = 지 - 동
        # 예측 후보 (i0 시점까지의 정보)
        국 = (ixv[i0] / ixv[i0 - 200] - 1) * 100 if ixv[i0 - 200] else 0
        창 = [ixv[k] for k in range(i0 - 60, i0) if ixv[k]]
        변 = (st.pstdev([창[k] / 창[k - 1] - 1 for k in range(1, len(창))]) * 100
              if len(창) > 30 else 0)
        후.sort(reverse=True)
        전시총 = sum(x[0] for x in 후) or 1
        집중 = sum(x[0] for x in 후[:10]) / 전시총 * 100
        행.append({"달": ym, "격차": 격, "국면": 국, "변동성": 변, "집중도": 집중})
        if j % 50 == 0:
            print(f"    {ym}", flush=True)

    print(f"\n  달 표본 {len(행)}개 · 격차 평균 {st.mean([x['격차'] for x in 행]):+.2f}%p "
          f"· 표준편차 {st.pstdev([x['격차'] for x in 행]):.2f}")

    # 집중도 변화율을 만든다
    for k in range(len(행)):
        행[k]["집중변화"] = (행[k]["집중도"] - 행[k - 3]["집중도"]) if k >= 3 else 0.0
        행[k]["과거격차3"] = st.mean([행[z]["격차"] for z in range(k - 3, k)]) if k >= 3 else 0.0

    print(f"\n  ══ ① 미리 아는 값 → 다음 1개월 격차 (상관계수) ══")
    print("     ⚠️ |t|≥2 라야 우연이 아니다. 상관이 0.2를 넘어야 실용성이 있다")
    print(f"    {'예측 후보':<20}{'상관':>9}{'t값':>8}{'표본':>8}")
    앞들 = [("지난 3개월 격차", "과거격차3"), ("코스피 200일 수익률", "국면"),
            ("코스피 60일 변동성", "변동성"), ("상위10 시총 비중", "집중도"),
            ("상위10 비중 3개월 변화", "집중변화")]
    나중 = [x["격차"] for x in 행[1:]]
    for 이름, 키 in 앞들:
        앞값 = [x[키] for x in 행[:-1]]
        r, t = _상관(앞값, 나중)
        print(f"    {이름:<20}{r:>+9.3f}{t:>8.1f}{len(나중):>8}")

    print(f"\n  ══ ② 미리 아는 값 → 다음 3개월 격차 (상관계수) ══")
    나중3 = []
    for k in range(len(행) - 3):
        나중3.append(sum(행[z]["격차"] for z in range(k + 1, k + 4)))
    print(f"    {'예측 후보':<20}{'상관':>9}{'t값':>8}{'표본':>8}")
    for 이름, 키 in 앞들:
        앞값 = [x[키] for x in 행[:len(나중3)]]
        r, t = _상관(앞값, 나중3)
        print(f"    {이름:<20}{r:>+9.3f}{t:>8.1f}{len(나중3):>8}")

    print(f"\n  ══ ③ 국면별 격차 평균 — **가장 실용적인 형태** ══")
    구간 = [("강세 (200일 +10%↑)", lambda x: x >= 10),
            ("횡보 (−10~+10%)", lambda x: -10 < x < 10),
            ("약세 (−10%↓)", lambda x: x <= -10)]
    print(f"    {'국면':<22}{'다음달 격차':>12}{'+비율':>8}{'표본':>8}")
    for 이름, f in 구간:
        a = [행[k + 1]["격차"] for k in range(len(행) - 1) if f(행[k]["국면"])]
        if len(a) < 10:
            continue
        플 = sum(1 for x in a if x > 0) / len(a) * 100
        print(f"    {이름:<22}{st.mean(a):>+11.2f}%p{플:>7.0f}%{len(a):>8}")

    print(f"\n  ══ ④ 집중도 구간별 격차 평균 ══")
    집 = sorted(x["집중도"] for x in 행)
    삼 = [집[len(집) // 3], 집[2 * len(집) // 3]]
    구간2 = [(f"집중도 낮음 (<{삼[0]:.0f}%)", lambda x: x < 삼[0]),
             (f"중간 ({삼[0]:.0f}~{삼[1]:.0f}%)", lambda x: 삼[0] <= x < 삼[1]),
             (f"집중도 높음 (≥{삼[1]:.0f}%)", lambda x: x >= 삼[1])]
    print(f"    {'구간':<22}{'다음달 격차':>12}{'+비율':>8}{'표본':>8}")
    for 이름, f in 구간2:
        a = [행[k + 1]["격차"] for k in range(len(행) - 1) if f(행[k]["집중도"])]
        if len(a) < 10:
            continue
        플 = sum(1 for x in a if x > 0) / len(a) * 100
        print(f"    {이름:<22}{st.mean(a):>+11.2f}%p{플:>7.0f}%{len(a):>8}")

    print("\n  읽는 법")
    print("    - 상관이 전부 0.2 미만이면 → **미리 알 수 없다**")
    print("      ⇒ 동적 배분은 포기하고 **지수 기본 + 선별 고정 비중**으로 간다")
    print("    - 하나라도 |t|≥2에 상관 0.2↑면 → 그걸로 비중을 조절해볼 값어치가 있다")
    print("    - ③④의 '+비율'은 그 구간에서 코스피가 동일가중을 이긴 달의 비율이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
