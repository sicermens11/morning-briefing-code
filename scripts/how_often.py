#!/usr/bin/env python3
r"""
how_often.py — **후보가 며칠에 한 번 나오나** (2026-09-07 신설)

## 왜
```
2026-09-07 오늘 후보가 **0개**였다. 그런데 그게 흔한 일인지 드문 일인지 몰랐다.
08:50 예상체결가 오차를 20건 모아야 상대갭 문턱(-3.5 vs -3.0)을 정할 수 있는데,
후보가 안 나오는 날이 많으면 **몇 달**이 걸린다. 계획을 세우려면 이 숫자가 필요하다
```

## 재는 것
```
A 08:00 후보가 **몇 개** 나오는 날이 며칠인가   (기록할 수 있는 날)
B 그중 실제로 **사게 되는** 날은 며칠인가        (상대갭 -3.5 를 넘는 것이 있는 날)
C 최근 1년만 보면                              (요즘 장에서도 그런가)
```
⚠️ 08:00 조건만 건다 — 갭은 09:00에 정해지므로 A 에는 안 들어간다.

쓰는 법:
    python scripts\how_often.py
"""
import collections
import datetime as dt
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import rule_def as R  # noqa: E402
from day_lab import 연간재무  # noqa: E402
# ⚠️ `record_pick` 은 `__main__` 가드가 있어 읽어도 아무것도 안 돈다.
#    실전이 쓰는 **그 함수 그대로**를 써야 숫자가 어긋나지 않는다
from record_pick import _섹터표, 섹터규칙맞나  # noqa: E402

_시작 = "20160401"
# ⚠️⚠️ **숫자를 여기 적지 않는다** (2026-09-11 전수조사 ⑦).
#    전에는 `확정 = {...}` 에 손으로 적어 두어, 섹터·시장 규칙이 붙은 뒤에도
#    이 파일만 **옛 규칙(잉30부80흑 볼-1.0 낙-10)** 으로 세고 있었다.
#    시총 하한도 `O._MIN_MC`(**500억**)를 써서 실전(300억)과 달랐다
_갭문턱 = R.상대갭문턱
_후보수 = R.후보수
_BASE2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    갭표, 앞종 = {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                if min(종c, 시) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루

    # ⭐⭐⭐ **시장 규칙**에 쓸 지수 낙폭 (2026-09-11).
    #    실전 `record_pick` 은 **그날 하루치**만 내지만, 여기는 전 기간을
    #    훑으므로 **날짜마다** 20일·60일 낙폭을 미리 만들어 둔다
    _지수계 = {}
    for _f in sorted(glob.glob(os.path.join(O._DATA, "index-daily",
                                            "*.json"))):
        try:
            _d2 = json.load(io.open(_f, encoding="utf-8-sig"))
        except ValueError:
            continue
        _날2 = _d2.get("기준일") or os.path.basename(_f)[:8]
        for _이름2 in ("코스피", "코스닥"):
            _v2 = (_d2.get("지수") or {}).get(_이름2) or {}
            try:
                _c2 = float(str(_v2.get("종가")).replace(",", ""))
            except (TypeError, ValueError, AttributeError):
                continue
            if _c2 > 0:
                _지수계.setdefault(
                    "KOSDAQ" if _이름2 == "코스닥" else "KOSPI",
                    []).append((_날2, _c2))
    지수낙 = {}          # {날짜: {"KOSPI": (20일, 60일), ...}}
    for _키2, _벌2 in _지수계.items():
        _벌2.sort()
        for _j, (_날3, _c3) in enumerate(_벌2):
            _n20 = ((_c3 / _벌2[_j - 20][1] - 1) * 100) if _j >= 20 else None
            _n60 = ((_c3 / _벌2[_j - 60][1] - 1) * 100) if _j >= 60 else None
            지수낙.setdefault(_날3, {})[_키2] = (_n20, _n60)
    print(f"  지수 {len(지수낙):,}일 · 섹터 규칙 {len(R.섹터규칙)}업종")
    섹터맵 = _섹터표()

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

    셈 = []          # (날짜, 후보수, 살것수)
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        하루갭 = 갭표.get(다음) or {}
        _지낙 = 지수낙.get(d1) or {}
        칸 = []
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            _시억 = 시총 / 1e8
            # ⚠️ 하한은 **rule_def(300억)** 다. `O._MIN_MC` 는 500억이라
            #    실전이 사는 종목의 10% 가 표본에서 빠졌었다 (전수조사 ②)
            if (_시억 < R.시총하한억 or _시억 >= R.시총상한억
                    or 대금 / 1e8 < R.대금하한억):
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= R.잉여금하한
                    and fm.get("부채비율", 9e9) <= R.부채상한
                    and (fm.get("흑자") == 1.0 or not R.흑자필수)):
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
            if sq[kk - 20] <= 0:
                continue
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            낙 = (c1 / sq[kk - 20] - 1) * 100
            낙60 = ((c1 / sq[kk - 60] - 1) * 100
                    if kk >= 60 and sq[kk - 60] > 0 else None)
            # ⭐⭐⭐ **Ⓗ — 기존 OR 섹터 OR 시장** (2026-09-11 전수조사 ⑦).
            #    전에는 **기존 하나뿐**이라 이 파일이 세는 「며칠에 한 번」이
            #    실제보다 **적게** 나왔다
            _기존 = (볼 <= R.볼린저문턱 and 낙 <= R.낙폭20문턱)
            _섹, _ = 섹터규칙맞나(code, sq, kk, c1, 섹터맵)
            _키2 = ("KOSDAQ" if ("닥" in str(bb.get("시장") or "")
                                 or "KOSDAQ" in str(bb.get("시장") or ""))
                    else "KOSPI")
            _z20, _z60 = _지낙.get(_키2, (None, None))
            _시장 = (((_z20 is not None and _z20 <= R.지수낙20문턱)
                      or (_z60 is not None and _z60 <= R.지수낙60문턱))
                     and (볼 <= R.시장볼문턱 or 낙 <= R.시장낙20문턱
                          or (낙60 is not None and 낙60 <= R.시장낙60문턱)))
            if not (_기존 or _섹 or _시장):
                continue
            g = 하루갭.get(code)
            칸.append((_기존 + _섹 + _시장, 낙, g))
        # ⚠️ 자르는 순서도 **실전과 같게** — 걸린 규칙 수가 많은 것 먼저,
        #    같은 층에서 깊게 빠진 순 (record_pick · 206차 P-2)
        칸.sort(key=lambda z: (-z[0], z[1]))
        앞 = 칸[:_후보수]
        살 = 0
        벌 = [g for _, _, g in 앞 if g is not None]
        if len(벌) >= 3:
            중 = st.median(벌)
            살 = sum(1 for _, _, g in 앞
                     if g is not None and (g - 중) <= _갭문턱)
        셈.append((다음, len(앞), min(살, R.하루최대종목)))

    print("=" * 74)
    print("  후보가 며칠에 한 번 나오나")
    print("=" * 74)

    def 요약(a, 라):
        if not a:
            print(f"  {라}: 자료 없음")
            return
        n = len(a)
        있 = sum(1 for _, c, _ in a if c > 0)
        셋 = sum(1 for _, c, _ in a if c >= 3)
        삼 = sum(1 for _, c, _ in a if c >= 10)
        삼십 = sum(1 for _, c, _ in a if c >= 30)
        산날 = sum(1 for _, _, b in a if b > 0)
        산것 = sum(b for _, _, b in a)
        평 = st.mean([c for _, c, _ in a])
        print(f"\n  ── {라} ({n:,} 거래일) ──")
        print(f"    후보가 **1개 이상** 있는 날   {있:,}일  ({있/n*100:.0f}%)")
        print(f"    후보가 3개 이상 (기록 가능)   {셋:,}일  ({셋/n*100:.0f}%)")
        print(f"    후보가 10개 이상             {삼:,}일  ({삼/n*100:.0f}%)")
        print(f"    후보가 30개 이상             {삼십:,}일  ({삼십/n*100:.0f}%)")
        print(f"    하루 평균 후보              {평:.1f}개")
        print(f"    **실제로 사게 되는 날**       {산날:,}일  ({산날/n*100:.0f}%)"
              f"  = {n/max(산날,1):.0f}일에 한 번")
        print(f"    산 종목 수                  {산것:,}건")

    # ⚠️ **숫자를 코드에 박지 않는다.** 브리핑이 이 파일을 읽는다 (2026-09-07)
    def 몫(a):
        n = max(len(a), 1)
        있 = sum(1 for _, c, _ in a if c > 0)
        셋 = sum(1 for _, c, _ in a if c >= 3)
        산날 = sum(1 for _, _, b in a if b > 0)
        return {"거래일": len(a),
                "후보있는날비율": round(있 / n * 100),
                "후보3개이상비율": round(셋 / n * 100),
                "하루평균후보": round(st.mean([c for _, c, _ in a]), 1),
                "사는날비율": round(산날 / n * 100),
                "며칠에한번": round(n / max(산날, 1)),
                "산것": sum(b for _, _, b in a)}
    몫들 = {"만든날": dt.date.today().strftime("%Y-%m-%d"),
            "출처": "scripts/how_often.py",
            # ⚠️ **손으로 적지 않는다** — rule_def 하나에서 (전수조사 ⑦)
            "규칙": R.한줄(),
            "전체": 몫(셈),
            "최근1년": 몫([x for x in 셈 if x[0] >= "20250901"]),
            "최근3개월": 몫([x for x in 셈 if x[0] >= "20260601"])}
    _p = os.path.join(_BASE2, "data", "rule-frequency.json")
    io.open(_p, "w", encoding="utf-8").write(
        json.dumps(몫들, ensure_ascii=False, indent=1))
    print("  -> " + os.path.basename(_p) + " 에 남겼다")


    요약(셈, "전체 기간")
    요약([x for x in 셈 if x[0] >= "20250901"], "최근 1년")
    요약([x for x in 셈 if x[0] >= "20260601"], "최근 3개월")

    print("\n" + "=" * 74)
    print("  ══ 08:50 오차를 20건 모으려면 ══")
    최근 = [x for x in 셈 if x[0] >= "20250901"]
    if 최근:
        셋 = [c for _, c, _ in 최근 if c >= 3]
        비 = len(셋) / len(최근)
        하루평 = st.mean([min(c, 8) for c in 셋]) if 셋 else 0
        if 하루평 > 0:
            필요 = 20 / (비 * 하루평)
            print(f"    후보 3개 이상인 날이 {비*100:.0f}% · "
                  f"그런 날 평균 {하루평:.1f}개를 적는다면")
            print(f"    ⇒ **약 {필요:.0f} 거래일** (약 {필요/5*7:.0f}일)이면 20건이 된다")
        print(f"    ⚠️ 전부 적으면 더 빠르다 — 후보 40개를 다 적으면 하루면 된다")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
