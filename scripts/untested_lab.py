#!/usr/bin/env python3
r"""
untested_lab.py — **한 번도 안 써본 자료를 훑는다** (2026-09-05 주말)

## ⚠️ 사용자 질문에서 나왔다
```
*"우리 100여가지 정보 중에 다 한번이라도 테스트 해본거야?"*
-> field_audit.py로 세어보니 **아니었다**
   가진 필드 927개 · 시험에 나온 것 311개(34%) · **안 써본 것 616개**
```

## ⚠️ 안 써본 것 중 **쓸 수 있는 것만** 고른다
```
❌ 못 쓴다
   dart-snap (배당·소액주주·자기주식)  **2024·2025 두 해뿐**
                                     백테스트가 10.4년인데 2년으론 못 쓴다
   card-copy · portfolio · secrets    분석 대상이 아니다 (브리핑 문구·열쇠)
   orderbook-today                    **오늘 것만** 있다 (과거 호가 기록 없음)
   us-symbols · sec-tickers           종목 목록일 뿐

✅ 쓸 수 있다
   A dart-capital **세부** (93개 미사용)
      지금은 「증자가 있었나 없었나」만 봤다.
      실제로는 **발행가·주식수·목적**이 다 들어 있다 -> **크기**를 재본다
   B index-daily **업종 지수** (49개 미사용) — 4,104일치가 있다
      그 종목이 속한 업종이 그날 어땠나 · 20일간 어땠나
   C dart-fin 세부 (18개 미사용) — 유동자산·자본금·영업비용 등
   D flow-daily **외국인지분율** — 지금은 순매수만 봤다
```
⚠️ 판정: 도달률 + 연도별 + **자본 시뮬** (여덟 번 다 자본 시뮬에서 졌다)
"""
import collections
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
확정 = {"갭": -3.5, "볼": -1.0, "낙": -10.0, "시총": 2e11,
        "비중": 0.20, "종목수": 4}


def main():
    print("  ══ 0 자료 점검 ══", flush=True)
    # ── A 증자·감자 세부 ──
    증자 = collections.defaultdict(list)
    갈래들 = ("유상증자", "무상증자", "유무상증자", "감자",
              "자사주취득", "자사주처분")
    필드수 = collections.Counter()
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-capital",
                                           "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        c = str(d.get("종목") or "").zfill(6)
        if not c or c == "000000":
            continue
        for 갈 in 갈래들:
            for it in (d.get(갈) or []):
                if not isinstance(it, dict):
                    continue
                날 = str(it.get("rcept_no") or "")[:8]
                if not (len(날) == 8 and 날.isdigit()):
                    continue
                증자[c].append((날, 갈, it))
                for k in it:
                    필드수[k] += 1
    print(f"    증자·감자 {len(증자):,}종목 · "
          f"{sum(len(v) for v in 증자.values()):,}건 · "
          f"세부 필드 {len(필드수)}개")

    # ── B 업종 지수 ──
    업종지수 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily",
                                           "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = d.get("기준일") or os.path.basename(f)[:8]
        항 = d.get("지수") or {}
        하 = {}
        for 이름, v in 항.items():
            if not isinstance(v, dict):
                continue
            try:
                종 = float(v.get("종가") or 0)
            except (TypeError, ValueError):
                continue
            if 종 > 0:
                하[이름] = 종
        if 하:
            업종지수[d8] = 하
    이름목 = collections.Counter()
    for v in 업종지수.values():
        이름목.update(v)
    print(f"    업종·지수 {len(업종지수):,}일 · 종류 {len(이름목)}개")
    print(f"      {', '.join(list(이름목)[:12])} …")

    # ── C 업종 매핑 ──
    업종표 = {}
    p = os.path.join(O._DATA, "industry.json")
    if os.path.exists(p):
        try:
            j = json.load(io.open(p, encoding="utf-8-sig"))
            j = j.get("업종") or j
            for c, v in j.items():
                if isinstance(v, dict):
                    업종표[c] = str(v.get("업종명") or "")
                else:
                    업종표[c] = str(v)
        except Exception:
            pass
    print(f"    종목→업종 {len(업종표):,}개")

    # ── D 외국인 지분율 ──
    외인율 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "flow-daily",
                                           "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = d.get("기준일") or os.path.basename(f)[:8]
        하 = {}
        for c, v in (d.get("종목") or {}).items():
            if not isinstance(v, dict):
                continue
            r = v.get("외국인지분율")
            if r is not None:
                try:
                    하[c] = float(r)
                except (TypeError, ValueError):
                    pass
        if 하:
            외인율[d8] = 하
    print(f"    외국인지분율 {len(외인율):,}일\n", flush=True)

    # ══ 사건 모으기 ══
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종, 원시 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            pv = 앞종.get(c)
            앞종[c] = 종c
            if pv and pv > 0:
                g = (시 / pv - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

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

    지수날 = sorted(업종지수)
    import bisect

    def 지수값(이름, d8, 앞=0):
        i = bisect.bisect_left(지수날, d8) - 앞
        while i >= 0:
            v = 업종지수.get(지수날[i], {}).get(이름)
            if v:
                return v
            i -= 1
        return None

    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
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
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 확정["시총"]:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > 확정["갭"]:
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
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > 확정["볼"] or sq[kk - 20] <= 0:
                continue
            if (c1 / sq[kk - 20] - 1) * 100 > 확정["낙"]:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결과, 청산 = None, None
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                vv = 주가[날[j]].get(code)
                b2 = (비.get(날[j]) or {}).get(code)
                if not vv or not b2:
                    break
                if vv[0] * b2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 청산 = _목표 - _비용, j
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과, 청산 = (끝[0] / 매수 - 1) * 100 - _비용, j
            # ── A 증자 세부 (⚠️ 신호 전날까지) ──
            최근증자, 증자크기 = None, None
            for 날2, 갈, it in (증자.get(code) or []):
                if 날2 >= d1:
                    continue
                if 최근증자 is None or 날2 > 최근증자[0]:
                    최근증자 = (날2, 갈, it)
            if 최근증자:
                it = 최근증자[2]
                # 새로 발행하는 주식수 / 이미 있는 주식수 = **희석 비율**
                for a, b in (("nstk_ostk_cnt", "bfic_tisstk_ostk"),
                             ("nstk_ostk_cnt", None)):
                    try:
                        새 = float(str(it.get(a) or "").replace(",", "") or 0)
                        옛 = float(str(it.get(b) or "").replace(",", "")
                                   or 0) if b else 0
                        if 새 > 0 and 옛 > 0:
                            증자크기 = 새 / 옛 * 100
                            break
                    except ValueError:
                        pass
            # ── B 업종 지수 ──
            업 = 업종표.get(code) or ""
            업20 = None
            if 업 and 업 in 이름목:
                a1 = 지수값(업, d1)
                a0 = 지수값(업, 날[max(0, i - 20)])
                if a1 and a0 and a0 > 0:
                    업20 = (a1 / a0 - 1) * 100
            # ── D 외국인 지분율 ──
            외 = (외인율.get(d1) or {}).get(code)
            사건.append({"인": i + 1, "날": 다음, "code": code, "결과": 결과,
                         "청산": 청산, "원시": o0, "대금": b0[2],
                         "상갭": g - 시갭,
                         "증자갈래": (최근증자[1] if 최근증자 else None),
                         "증자날": (최근증자[0] if 최근증자 else None),
                         "증자크기": 증자크기,
                         "업종": 업, "업종20일": 업20, "외인율": 외,
                         "도달": 결과 > _목표 - _비용 - 1e-9})
    n = len(사건)
    if n == 0:
        print("  ⚠️ 사건이 없다")
        return 1
    바닥 = sum(1 for x in 사건 if x["도달"]) / n * 100
    print(f"  사건 {n:,}건 · 기본 도달률 {바닥:.1f}%")
    for k, 라 in (("증자크기", "증자 크기를 아는 것"),
                  ("업종20일", "업종 지수를 아는 것"),
                  ("외인율", "외국인 지분율을 아는 것")):
        있 = sum(1 for x in 사건 if x.get(k) is not None)
        print(f"    {라:<22}{있:>5}건 ({있/n*100:>5.1f}%)")
    print()

    def 재기(a, 라, 폭=28):
        if len(a) < 20:
            print(f"    {라:<{폭}}{len(a):>6}건  표본 부족")
            return
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        묶 = {}
        for x in a:
            묶.setdefault(x["날"][:4], []).append(x["결과"])
        전 = 플 = 0
        for y, arr in 묶.items():
            if len(arr) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        별 = "⭐" if (abs(d2 - 바닥) > 5 and 전 >= 7
                     and 플 / 전 >= 2 / 3) else "  "
        print(f"    {라:<{폭}}{len(a):>6}건{d2:>8.1f}%{d2-바닥:>+8.1f}%p"
              f"{st.mean([x['결과'] for x in a]):>+9.2f}%{f'{플}/{전}':>7}{별}")

    머 = (f"    {'조건':<28}{'표본':>8}{'도달률':>8}{'기본대비':>8}"
          f"{'평균':>9}{'연도별':>7}")

    print("  ══ A **증자·감자 세부** (지금은 있음/없음만 봤다) ══")
    print(머)
    for 갈 in 갈래들:
        재기([x for x in 사건 if x["증자갈래"] == 갈], f"마지막이 {갈}")
    재기([x for x in 사건 if x["증자갈래"] is None], "증자·감자 이력 없음")
    print("\n    ── ⭐ 증자 **크기**(희석 비율)별 ──")
    print(머)
    for lo, hi, 라 in ((0, 5, "5% 미만 희석"), (5, 15, "5~15%"),
                       (15, 40, "15~40%"), (40, 9e9, "40% 넘는 희석")):
        재기([x for x in 사건 if x["증자크기"] is not None
              and lo <= x["증자크기"] < hi], 라)

    print(f"\n  ══ B **업종 지수** (4,104일치를 한 번도 안 썼다) ══")
    print(머)
    for lo, hi, 라 in ((-9e9, -10, "업종이 20일 −10%↓"),
                       (-10, -3, "−3~−10%"), (-3, 3, "−3~+3%"),
                       (3, 9e9, "+3%↑")):
        재기([x for x in 사건 if x["업종20일"] is not None
              and lo <= x["업종20일"] < hi], 라)

    print(f"\n  ══ D **외국인 지분율** (지금은 순매수만 봤다) ══")
    print(머)
    for lo, hi, 라 in ((0, 1, "1% 미만"), (1, 5, "1~5%"),
                       (5, 15, "5~15%"), (15, 9e9, "15%↑")):
        재기([x for x in 사건 if x["외인율"] is not None
              and lo <= x["외인율"] < hi], 라)

    # ══ 자본 시뮬 ══
    print(f"\n  ══ ⭐⭐ **자본 시뮬** — 여덟 번 다 여기서 졌다 ══")
    묶날 = {}
    for x in 사건:
        묶날.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]

    def 시뮬(거름, 라, 끝년=None, 폭=32):
        현금, 보유, 곡, 산 = 5_000_000.0, [], [], 0
        for i in range(시i, len(날)):
            if 끝년 and 날[i][:4] > 끝년:
                break
            남 = []
            for q in 보유:
                if q["청산"] <= i:
                    현금 += q["주수"] * q["원시"] * (1 + q["결과"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
            골 = [x for x in 묶날.get(i, []) if 거름(x)]
            for x in sorted(골, key=lambda z: z["상갭"])[:확정["종목수"]]:
                쓸 = min(평 * 확정["비중"], 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유.append({**x, "주수": 주수})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        yr = max(len(곡) / 245, 0.1)
        c = ((끝 / 5_000_000) ** (1 / yr) - 1) * 100
        피 = 낙 = 0.0
        for v in 곡:
            피 = max(피, v)
            낙 = min(낙, (v / 피 - 1) * 100)
        print(f"    {라:<{폭}}{끝:>15,.0f}원{c:>+9.2f}%{낙:>8.1f}%{산:>7}건")

    print(f"    {'전략':<32}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")
    for 끝년, 라2 in ((None, ""), ("2024", " (2025·26 제외)")):
        if 끝년:
            print(f"\n    ⚠️ 2025·26 제외")
        시뮬(lambda x: True, "원판", 끝년=끝년)
        시뮬(lambda x: not (x["증자크기"] is not None and x["증자크기"] >= 15),
             "+ 15%↑ 희석 증자 **제외**", 끝년=끝년)
        시뮬(lambda x: x["업종20일"] is None or x["업종20일"] < -3,
             "+ 업종도 20일 −3%↓만", 끝년=끝년)
        시뮬(lambda x: x["외인율"] is None or x["외인율"] >= 1,
             "+ 외국인 지분 1%↑만", 끝년=끝년)

    print("\n  읽는 법")
    print("    - 자본 시뮬에서 원판을 못 이기면 **안 쓴다** (여덟 번 겪었다)")
    print("    - ⚠️ dart-snap(배당·소액주주·자기주식)은 **2024·2025 두 해뿐**이라")
    print("      10.4년 백테스트에 못 쓴다. 여기서 안 뺐다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
