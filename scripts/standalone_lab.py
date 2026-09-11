#!/usr/bin/env python3
r"""
standalone_lab.py — **신호 하나만으로 규칙을 새로 짠다** (2026-09-07 신설)

## ⚠️⚠️ 왜 만들었나 — 사용자 지적
```
「하루 이틀이라도 상승해서 수익을 거둘 수 있다면 성공이라고 생각한다.
  우리 규칙이 그걸 못 잡는 게 너무 우리 규칙에 얽매여 있는 거 아니야?
  목표는 매수기회 포착해서 수익을 얻는 거지, 우리 규칙을 입증하는 게 아니야」

**맞다. 오늘 시험이 전부 규칙 중심이었다:**
  「⑪ 리포트 난 것만」 = 우리 규칙(재무+낙폭+볼린저+갭) **위에** 리포트를 얹음
  -> 산 것 0건. 당연하다. **신호가 아니라 교집합을 시험한 것**이다
  그리고 「우리 규칙을 못 이기면 기각」이라는 잣대 자체가 규칙 중심이었다
```

## 그래서 여기서는
```
· 우리 조건(재무·20일낙폭·볼린저·상대갭)을 **전부 뺀다**
· 신호 하나만으로 산다
· **짧게 판다** — D+1 / D+2 / D+3 / D+5 (우리 규칙은 평균 17일이다)
· 목표도 낮게 — +3% / +5% / +10%
· 견줄 대상은 **「아무 날이나 아무거나」**다 (우리 규칙이 아니다)
```
⚠️ 지도(평균 수익)에서 D+1 에도 값이 있었다:
   소형 갭 -2%↓ D+1 +0.71% · 리포트 D+1 +0.42% (기준선 -0.03%)
⚠️ **거래비용이 크게 걸린다.** 짧게 사고팔수록 0.26%가 무겁다

쓰는 법:
    python scripts\standalone_lab.py
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_시드 = 5_000_000.0


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    _사라짐 = O.사라진종목(주가, 날)   # ⚠️ 상장폐지를 손실로 센다
    print(f"  중간에 사라진 종목 {len(_사라짐):,}개 — 상장폐지는 {O.폐지손실:.0f}% 손실로 센다", flush=True)
    기본 = O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 앞종, 원시 = {}, {}, {}, {}
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
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루

    # ── 신호 자료 ──
    print("  신호 자료 읽는 중...", flush=True)
    공시, 리포트 = {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            dd = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = dd.get("기준일")
        if not d8:
            continue
        났 = set()
        for k in ("챙길공시", "그밖의공시"):
            for x in (dd.get(k) or []):
                c2 = x.get("종목코드")
                if c2:
                    났.add(str(c2).zfill(6))
        공시[d8] = 났
    for f in sorted(glob.glob(os.path.join(O._DATA, "consensus", "*.json"))):
        try:
            dd = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        for x in (dd.get("리포트") or []):
            c2 = x.get("코드")
            날짜2 = str(x.get("날짜") or "").replace("-", "")
            if c2 and len(날짜2) == 8:
                리포트.setdefault(날짜2, set()).add(str(c2).zfill(6))

    assert isinstance(날, list) and len(날) > 1000, "거래일 목록이 망가졌다"
    print("  후보 모으는 중 (**우리 조건을 전부 뺀다**)...", flush=True)

    사건 = []
    for i, d1 in enumerate(날):
        if i < 30 or i + 7 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        하루갭 = 갭표.get(다음) or {}
        오늘공시 = 공시.get(d1) or set()
        오늘리포 = 리포트.get(d1) or set()
        # 거래대금 급증을 재려면 그날 순위가 필요하다
        대금들 = sorted((v[2] for v in 주가[d1].values()), reverse=True)
        상위 = 대금들[int(len(대금들) * 0.05)] if len(대금들) > 40 else None
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 대금 < O._MIN_AMT or 시총 < 5e10:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            g = 하루갭.get(code)
            if not b0 or not v0 or not o0 or g is None:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            kk = (자리.get(code) or {}).get(d1)
            낙20 = None
            if kk is not None and kk >= 21 and 종계[code][kk - 20] > 0:
                낙20 = (c1 / 종계[code][kk - 20] - 1) * 100
            사건.append({
                "인": i + 1, "code": code, "원시": o0, "대금": b0[2],
                "매수": 매수, "갭": g, "시총억": 시총 / 1e8, "낙20": 낙20,
                "공시": code in 오늘공시, "리포트": code in 오늘리포,
                "대금급증": (상위 is not None and 대금 >= 상위)})
    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  후보 {len(사건):,}건 · {len(묶):,}일\n", flush=True)

    캐시 = {}

    def 결과(x, 목표, 보유):
        키 = (x["인"], x["code"], 목표, 보유)
        if 키 in 캐시:
            return 캐시[키]
        i = x["인"] - 1
        r, 청 = None, None
        for h in range(0, 보유 + 1):
            j = i + 1 + h
            if j >= len(날):
                break
            vv = 주가[날[j]].get(x["code"])
            b2 = (비.get(날[j]) or {}).get(x["code"])
            if not vv or not b2:
                break
            if vv[0] * b2[1] >= x["매수"] * (1 + 목표 / 100):
                r, 청 = 목표 - _비용, j
                break
        if r is None:
            j = i + 1 + 보유
            끝 = 주가[날[j]].get(x["code"]) if j < len(날) else None
            # ⚠️⚠️ **상장폐지를 손실로 센다** (2026-09-08 고침).
            #    전에는 자료가 없으면 그 거래를 **지웠다** —
            #    913종목(25%)이 중간에 사라졌고 성적이 부풀려졌다
            if not 끝 and x["code"] in _사라짐:
                캐시[키] = (O.폐지손실 - _비용, min(j, len(날) - 1))
                return 캐시[키]
            if not 끝:
                캐시[키] = (None, None)
                return 캐시[키]
            r, 청 = (끝[0] / x["매수"] - 1) * 100 - _비용, j
        캐시[키] = (r, 청)
        return 캐시[키]

    def 시뮬(고름, 정렬, 목표, 보유, 종목수=4, 비중=0.20, 끝년=None):
        현금, 보유중, 곡, 산 = _시드, [], [], 0
        for i in range(시i, len(날)):
            if 끝년 and 날[i][:4] > 끝년:
                break
            남 = []
            for q in 보유중:
                if q["청산"] <= i:
                    현금 += q["주수"] * q["원시"] * (1 + q["결과"] / 100)
                else:
                    남.append(q)
            보유중 = 남
            현금 *= (1 + 0.025 / 245)
            평 = 현금 + sum(q["주수"] * q["원시"] for q in 보유중)
            골 = sorted([x for x in (묶.get(i) or []) if 고름(x)], key=정렬)
            # ⚠️⚠️ **동시 보유 상한** (2026-09-07 고침).
            #    처음엔 상한이 없어서 매일 4종목씩 사고 3일 보유하면
            #    **항상 12포지션 = 비중 20%x12 = 240% 노출**이 됐다.
            #    그래서 499억(연 +141%) 같은 비현실적 값이 나왔다.
            #    우리 규칙은 후보가 드물어 실제 동시 보유가 적다 — 견줄 수 없었다
            자리남 = max(0, 종목수 - len(보유중))
            for x in 골[:자리남]:
                r, 청 = 결과(x, 목표, 보유)
                if r is None:
                    continue
                쓸 = min(평 * 비중, 현금, x["대금"] * 0.01)
                주수 = int(쓸 // x["원시"])
                if 주수 < 1 or 주수 * x["원시"] > 현금:
                    continue
                현금 -= 주수 * x["원시"]
                보유중.append({"주수": 주수, "원시": x["원시"],
                               "결과": r, "청산": 청})
                산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유중)
        해 = max(len(곡) / 245, 0.1)
        연 = ((끝 / _시드) ** (1 / 해) - 1) * 100 if 끝 > 0 else -100
        최고, 낙 = _시드, 0.0
        for v in 곡:
            최고 = max(최고, v)
            낙 = min(낙, v / 최고 - 1)
        return {"끝": 끝, "연": 연, "낙": 낙 * 100, "산": 산}

    머 = (f"    {'':<38}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}"
          f"{'산 것':>7}{'돈÷낙폭':>9}")

    def 표(r, 라):
        점 = r["연"] / max(abs(r["낙"]), 3.0)
        print(f"    {라:<38}{r['끝']:>15,.0f}원{r['연']:>+8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}{점:>9.2f}", flush=True)

    print("=" * 100)
    print("  신호 하나만으로 — **우리 조건을 전부 뺐다**")
    print("=" * 100)
    print("  ⚠️ 견줄 대상은 「아무 날이나 아무거나」다 (우리 규칙이 아니다)")
    print(머)
    표(시뮬(lambda x: True, lambda z: -z["대금"], 5, 3),
      "아무거나 (거래대금 큰 순) 목표5% 3일")

    신호들 = (
        ("갭 상승 +3%↑ (로보티즈 꼴)", lambda x: x["갭"] >= 3,
         lambda z: -z["갭"]),
        ("갭 상승 +5%↑", lambda x: x["갭"] >= 5, lambda z: -z["갭"]),
        ("공시 + 갭 상승 +3%↑", lambda x: x["공시"] and x["갭"] >= 3,
         lambda z: -z["갭"]),
        ("공시 난 것", lambda x: x["공시"], lambda z: -z["대금"]),
        ("리포트 난 것", lambda x: x["리포트"], lambda z: -z["대금"]),
        ("거래대금 상위 5%", lambda x: x["대금급증"], lambda z: -z["대금"]),
        ("갭 하락 -3%↓ (우리 뿌리)", lambda x: x["갭"] <= -3,
         lambda z: z["갭"]),
        ("갭 하락 -5%↓", lambda x: x["갭"] <= -5, lambda z: z["갭"]),
    )
    for 라, 고, 정 in 신호들:
        print("")
        print(f"    ── {라} ──")
        for 목표, 보유 in ((3, 1), (3, 2), (5, 3), (5, 5), (10, 5)):
            표(시뮬(고, 정, 목표, 보유),
              f"목표 {목표}% · {보유}일 보유")

    print("")
    # ── ⭐ 거래비용을 올리면 무너지나 (슬리피지 대신) ──
    #    ⚠️ 「아무거나」가 연 +74%라는 건 시뮬이 낙관적이라는 뜻이다.
    #       안 넣은 것은 **슬리피지**다 — 소형주 호가 차이는 0.5~1%도 흔하다.
    #       목표 +20%인 우리 규칙엔 작지만 **목표 5%면 수익의 10%**다
    global _비용
    print("")
    assert isinstance(비, dict), "(시가/종가 딕셔너리)가 덮어써졌다"
    print("=" * 100)
    print("  == 거래비용을 올리면 (슬리피지를 넣으면) ==")
    print("=" * 100)
    # ⚠️⚠️ ** 를 쓰지 마라.** 시가/종가 비율 딕셔너리 이름이다.
    #    2026-09-07 에 이걸로 **다섯 번** 당했다 (비·묶·날·비).
    #    아침에 문서화까지 해놓고 또 했다 — 한 글자 한글 이름을 아예 안 쓴다
    for 비용값 in (0.26, 0.5, 1.0, 1.5):
        _비용 = 비용값
        캐시.clear()
        print("")
        print("    -- 왕복 " + format(비용값, ".2f") + "% --")
        print(머)
        표(시뮬(lambda x: True, lambda z: -z["대금"], 5, 3),
          "아무거나 · 목표5% 3일")
        표(시뮬(lambda x: x["대금급증"], lambda z: -z["대금"], 3, 1),
          "거래대금 상위5% · 목표3% 1일")
        표(시뮬(lambda x: x["공시"], lambda z: -z["대금"], 10, 5),
          "공시 난 것 · 목표10% 5일")
    _비용 = 0.26
    print("")

    print("=" * 100)
    print("  읽는 법")
    print("    · **「아무거나」보다 나아야** 신호다")
    print("    · 짧게 사고팔수록 **거래비용 0.26%**가 무겁다")
    print("    · 여기서 이겨도 앞뒤 분할·무작위 대비를 통과해야 규칙이 된다")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
