#!/usr/bin/env python3
r"""
noreact_lab.py — **135차 · 「재료는 났는데 안 움직였다」를 숫자로 잰다** (2026-09-07)

## 사용자 질문에서 나왔다
```
「기존 브리핑은 갭 위주였는데, 퀀트 추천에도 갭이 반영될 가능성 있나?」
```
⚠️ **두 「갭」은 이름만 같고 다른 것이다.**
```
퀀트의 갭      **가격 갭**. 08:50 예상체결가가 후보중앙갭보다 -3.5%p 낮게 열림
              -> 이미 우리 규칙의 핵심이고, 134차에서 격자 64칸 중 **1등**으로 확인됐다
기존 브리핑의 갭  **정보 갭**(갭①~④). 「재료는 나왔는데 주가가 아직 안 움직인 정도」
              갭④ = 강화-P 로 **실제 무반응**을 확인하는 것
```
정보 갭 전체는 백테스트가 안 된다 — 재료 판정에 뉴스 텍스트가 필요한데 **1년치뿐**이다.
**그런데 갭④(무반응)만은 숫자로 옮길 수 있다.** 그게 이 시험이다

## 재는 것
```
축   그날 「챙길공시」가 난 종목 (133차 ⑥과 같은 자리)
     + 시총 2,000억 이하 · 재무 · 거래대금 1억
무반응을 세 가지로 잰다
  A 거래량이 20일 평균보다 **적다**       (아무도 안 샀다)
  B 그날 등락률의 **절댓값이 작다**        (가격이 안 움직였다)
  C 둘 다
견줌  반대쪽(거래량 급증 · 크게 움직임)도 같이 잰다
```
⚠️ 133차에서 공시 축은 우리 규칙의 1/3이었다. 여기서 이겨도
   **우리 규칙을 대체하는 게 아니라 「따로 돌릴 값어치가 있나」**를 보는 것이다

쓰는 법:
    python scripts\noreact_lab.py
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

_비용 = 0.26
_시작 = "20160401"
_시드 = 5_000_000.0
_후보수 = 40
확정 = {"잉여금": 30, "부채": 80, "흑자필수": True, "상대갭": -3.5,
        "볼린저": -1.0, "낙폭20": -10, "목표": 20, "최대보유": 40,
        "비중": 0.20, "하루상한": 4,
        "시총하한": 500, "시총상한": 2000, "대금하한": 1.0, "거래량하한": 0,
        "회전율하한": 0.0}


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    _사라짐 = O.사라진종목(주가, 날)   # ⚠️ 상장폐지를 손실로 센다
    print(f"  중간에 사라진 종목 {len(_사라짐):,}개 — 상장폐지는 {O.폐지손실:.0f}% 손실로 센다", flush=True)
    # ⚠️ 짧은 한글 이름 덮어쓰기로 하루에 다섯 번 당했다 — 훑기 전에 못 박는다
    assert isinstance(날, list) and len(날) > 1000, ('거래일 목록이 깨졌다', len(날))
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 앞종, 원시, 거량 = {}, {}, {}, {}, {}
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
                량 = float(v.get("거래량") or 0)
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            거량.setdefault(d8, {})[c] = 량
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루

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

    # ── 공시 읽기 (종목 · 종류 · 시각) ──
    print("  공시 읽는 중...", flush=True)

    def _분(시문자):
        s = str(시문자 or "").strip()
        if ":" in s:
            a, _, b = s.partition(":")
        elif len(s) == 4 and s.isdigit():
            a, b = s[:2], s[2:]
        else:
            return None
        try:
            return int(a) * 60 + int(b)
        except ValueError:
            return None

    공시 = {}      # 날짜 -> {코드: {"수":n, "챙길":n, "분": [분,...]}}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            dj = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        d8 = dj.get("기준일") or os.path.basename(f)[:8]
        kp = os.path.join(O._DATA, "kind-time", d8 + ".json")
        뒤5 = {}
        if os.path.exists(kp):
            try:
                for 번, 시 in (json.load(io.open(kp, encoding="utf-8-sig"))
                               .get("시각") or {}).items():
                    if len(str(번)) >= 5:
                        뒤5[str(번)[-5:]] = _분(시)
            except ValueError:
                pass
        하루 = {}
        for 챙길, 목록 in ((True, dj.get("챙길공시") or []),
                           (False, dj.get("그밖의공시") or [])):
            for x3 in 목록:
                c3 = str(x3.get("종목코드") or "").zfill(6)
                if not c3 or c3 == "000000":
                    continue
                칸 = 하루.setdefault(c3, {"수": 0, "챙길": 0, "분": []})
                칸["수"] += 1
                if 챙길:
                    칸["챙길"] += 1
                분 = 뒤5.get(str(x3.get("접수번호", ""))[-5:])
                if 분 is not None:
                    칸["분"].append(분)
        if 하루:
            공시[d8] = 하루
    print(f"    공시 있는 날 {len(공시):,}일", flush=True)

    assert isinstance(날, list) and len(날) > 1000, "거래일 목록이 망가졌다"
    print("  후보 모으는 중 (**공시가 축이다 — 볼린저·낙폭은 안 건다**)...",
          flush=True)
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        오늘공시 = 공시.get(d1) or {}
        if not 오늘공시:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, 칸 in 오늘공시.items():
            v = 주가[d1].get(code)
            if not v:
                continue
            c1, 시총, 대금 = v
            if 시총 < 5e10 or 시총 >= 5e12:
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
            fm = 재무값(code, d1) or {}
            kk = (자리.get(code) or {}).get(d1)
            볼, 낙 = None, None
            if kk is not None and kk >= 250:
                sq = 종계[code]
                s20 = st.mean(sq[kk - 19:kk + 1])
                sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
                볼 = (c1 - s20) / (2 * sd)
                if sq[kk - 20] > 0:
                    낙 = (c1 / sq[kk - 20] - 1) * 100
            # ── 「반응했나」를 잰다 (갭④를 숫자로) ──
            거20, 등락 = None, None
            if kk is not None and kk >= 21:
                최근 = []
                for j2 in range(kk - 20, kk):
                    dd = 날[j2] if j2 < len(날) else None
                    vv2 = 주가.get(dd, {}).get(code) if dd else None
                    if vv2:
                        최근.append(vv2[2])       # 거래대금
                if len(최근) >= 10:
                    평 = sum(최근) / len(최근)
                    거20 = (대금 / 평) if 평 > 0 else None
                if 종계[code][kk - 1] > 0:
                    등락 = (c1 / 종계[code][kk - 1] - 1) * 100
            분들 = 칸["분"]
            사건.append({
                "인": i + 1, "code": code, "원시": o0, "대금": b0[2],
                "매수": 매수, "갭": g,
                "시총억": 시총 / 1e8, "대금억": 대금 / 1e8,
                "볼린저": 볼, "낙폭20": 낙,
                "거래량": 0, "회전율": (대금 / 시총 * 100) if 시총 else 0,
                "공시수": 칸["수"], "챙길수": 칸["챙길"],
                "장중": sum(1 for m in 분들 if 9 * 60 <= m < 16 * 60),
                "장후": sum(1 for m in 분들 if m >= 16 * 60),
                "새벽": sum(1 for m in 분들 if m < 8 * 60),
                "거래배수": 거20, "등락": 등락,
                "재무통과": 1.0 if (
                    fm.get("잉여금비율", -9e9) >= 확정["잉여금"]
                    and fm.get("부채비율", 9e9) <= 확정["부채"]
                    and fm.get("흑자") == 1.0) else 0.0,
            })

    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  후보 {len(사건):,}건 · {len(묶):,}일\n", flush=True)

    캐시 = {}

    def 결과(x, 목표, 보유, 상태=None):
        """상태: None(기한) · "20일선"(종가가 20일선 위) · "볼0"(볼린저 0 위)

        ⚠️ 목표가에 먼저 닿으면 그걸로 판다. 상태는 **기한 대신** 쓰는 것이다
        """
        키 = (x["인"], x["code"], 목표, 보유, 상태)
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
            # ⭐ 상태 청산 — 날짜가 아니라 **회복됐을 때** 판다
            if 상태 and h >= 1:
                kk2 = (자리.get(x["code"]) or {}).get(날[j])
                if kk2 is not None and kk2 >= 20:
                    sq2 = 종계[x["code"]]
                    m20 = st.mean(sq2[kk2 - 19:kk2 + 1])
                    회복 = False
                    if 상태 == "20일선":
                        회복 = sq2[kk2] > m20
                    else:
                        sd2 = st.pstdev(sq2[kk2 - 19:kk2 + 1]) or 1e-9
                        회복 = (sq2[kk2] - m20) / (2 * sd2) > 0
                    if 회복:
                        r, 청 = (vv[0] / x["매수"] - 1) * 100 - _비용, j
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

    def 시뮬(c, 끝년=None, 시드=None, 시작년=None, 오차=0.0):
        import random as _r2
        _rng = _r2.Random(20260907)
        시드 = 시드 or _시드
        시작i = 시i
        if 시작년:
            _a = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = _a[0] if _a else 시i
        현금, 보유, 곡, 산 = 시드, [], [], 0
        for i in range(시작i, len(날)):
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
            칸 = [x for x in (묶.get(i) or [])
                  if c["시총하한"] <= x["시총억"] < c["시총상한"]
                  and x["대금억"] >= c["대금하한"]
                  and x["거래량"] >= c["거래량하한"]
                  and x["회전율"] >= c["회전율하한"]]
            # ⚠️ 수급 거름은 **40개로 좁히기 전**에 건다.
            #    수급은 전날 자료라 08:00에 이미 알 수 있기 때문이다
            거름 = c.get("거름")
            if 거름:
                칸 = [x for x in 칸 if 거름(x)]
            # 공시 축에서는 낙폭20 이 None 일 수 있다 (상장 초기 등)
            칸 = sorted(칸, key=lambda z: (z["낙폭20"] is None,
                                          z["낙폭20"] or 0.0))[:_후보수]
            if len(칸) < 3:
                곡.append(평)
                continue
            중 = st.median([x["갭"] for x in 칸])
            잰 = []
            for x in 칸:
                v3 = x["갭"] - 중
                if 오차:
                    v3 += _rng.gauss(0, 오차)
                if v3 <= c["상대갭"]:
                    잰.append((v3, x))
            # ⚠️ 기본은 **갭이 큰 순**이다. 고르기가 있으면 그 순서로 바꾼다.
            #    문턱(상대갭 -3.5%p)은 그대로라 **후보 수는 안 변한다**
            고르기 = c.get("고르기")
            if 고르기:
                골 = sorted([z[1] for z in 잰], key=고르기)
            else:
                골 = [z[1] for z in sorted(잰, key=lambda z: z[0])]
            for x in 골[:c["하루상한"]]:
                # ⚠️ 나눔이 있으면 **주수를 쪼개** 두 몫으로 만든다.
                #    한 종목에 들어가는 총액은 같다 (자산 20%)
                몫들 = c.get("나눔") or ((1.0, c["목표"], c["최대보유"]),)
                쓸 = min(평 * c["비중"], 현금, x["대금"] * 0.01)
                총주수 = int(쓸 // x["원시"])
                if 총주수 < len(몫들) or 총주수 * x["원시"] > 현금:
                    continue
                넣음 = False
                for 몫 in 몫들:
                    비율, 목표b, 보유b = 몫[0], 몫[1], 몫[2]
                    상태b = 몫[3] if len(몫) > 3 else None
                    r, 청 = 결과(x, 목표b, 보유b, 상태b)
                    if r is None:
                        continue
                    주수 = int(총주수 * 비율)
                    if 주수 < 1 or 주수 * x["원시"] > 현금:
                        continue
                    현금 -= 주수 * x["원시"]
                    보유.append({"주수": 주수, "원시": x["원시"],
                                 "결과": r, "청산": 청})
                    넣음 = True
                if 넣음:
                    산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        해 = max(len(곡) / 245, 0.1)
        연 = ((끝 / 시드) ** (1 / 해) - 1) * 100 if 끝 > 0 else -100
        최고, 낙 = 시드, 0.0
        for v in 곡:
            최고 = max(최고, v)
            낙 = min(낙, v / 최고 - 1)
        return {"끝": 끝, "연": 연, "낙": 낙 * 100, "산": 산}

    머 = f"    {'':<28}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}"

    def 표(r, 라, 기=None):
        점 = r["연"] / max(abs(r["낙"]), 3.0)
        꼬 = ""
        if 기:
            늘 = (r["끝"] / 기["끝"] - 1) * 100
            꼬 = f"  ({늘:+.0f}%)"
        print(f"    {라:<28}{r['끝']:>15,.0f}원{r['연']:>+8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}{점:>9.2f}{꼬}", flush=True)

    기본틀 = dict(확정)
    기본틀["나눔"] = ((0.5, 15, 40), (0.5, 40, 90))
    기본틀["상대갭"] = 99.0
    기본틀["시총하한"] = 500
    기본틀["시총상한"] = 2000
    기본틀["대금하한"] = 1.0

    def 있(x, k):
        return x.get(k) is not None

    def 바탕(x):
        """133차 ⑥ 자리 — 재무 + 「챙길공시」"""
        return x.get("재무통과") == 1.0 and (x.get("챙길수") or 0) > 0

    갈래 = [
        ("바탕 (재무 + 챙길공시)", 바탕),
        ("── A 거래량이 안 늘었나 (20일 평균 대비) ──", None),
        ("거래 0.5배 아래 — **아무도 안 샀다**",
         lambda x: 바탕(x) and 있(x, "거래배수") and x["거래배수"] < 0.5),
        ("거래 1.0배 아래", lambda x: 바탕(x) and 있(x, "거래배수")
         and x["거래배수"] < 1.0),
        ("(반대) 거래 2배 넘음 — 크게 반응",
         lambda x: 바탕(x) and 있(x, "거래배수") and x["거래배수"] > 2.0),
        ("(반대) 거래 5배 넘음", lambda x: 바탕(x) and 있(x, "거래배수")
         and x["거래배수"] > 5.0),
        ("── B 가격이 안 움직였나 (그날 등락률) ──", None),
        ("|등락| 1% 아래 — **가격이 안 움직였다**",
         lambda x: 바탕(x) and 있(x, "등락") and abs(x["등락"]) < 1.0),
        ("|등락| 2% 아래", lambda x: 바탕(x) and 있(x, "등락")
         and abs(x["등락"]) < 2.0),
        ("(반대) +3% 넘게 올랐다", lambda x: 바탕(x) and 있(x, "등락")
         and x["등락"] > 3.0),
        ("(반대) -3% 넘게 내렸다", lambda x: 바탕(x) and 있(x, "등락")
         and x["등락"] < -3.0),
        ("── C 둘 다 (진짜 무반응) ──", None),
        ("거래 1.0배 아래 + |등락| 2% 아래",
         lambda x: 바탕(x) and 있(x, "거래배수") and 있(x, "등락")
         and x["거래배수"] < 1.0 and abs(x["등락"]) < 2.0),
        ("거래 0.7배 아래 + |등락| 1.5% 아래",
         lambda x: 바탕(x) and 있(x, "거래배수") and 있(x, "등락")
         and x["거래배수"] < 0.7 and abs(x["등락"]) < 1.5),
        ("── D 무반응 + 우리 규칙의 낙폭 조건 ──", None),
        ("무반응 + 20일 낙폭 -10% 이하",
         lambda x: 바탕(x) and 있(x, "거래배수") and 있(x, "등락")
         and x["거래배수"] < 1.0 and abs(x["등락"]) < 2.0
         and 있(x, "낙폭20") and x["낙폭20"] <= -10),
    ]

    for 끝년, 라 in ((None, "전체 기간"), ("2024", "2025·26 제외")):
        print("=" * 96)
        print("  == " + 라 + " ==  (공시 축 · 매도는 124차 나눠팔기)")
        print("=" * 96)
        print(머)
        기 = None
        for 이름, fn in 갈래:
            if fn is None:
                print("")
                print("    " + 이름)
                continue
            n2 = sum(1 for x in 사건 if fn(x))
            if n2 < 200:
                print(f"    {이름:<42}후보 {n2:>6,}건 — **표본 부족**")
                continue
            c2 = dict(기본틀)
            c2["거름"] = fn
            r = 시뮬(c2, 끝년=끝년)
            if 기 is None:
                기 = r
                표(r, f"{이름} [{n2:,}건]")
            else:
                표(r, f"{이름} [{n2:,}건]", 기)
        print("")
    print("  ⚠️ 견줄 것: 우리 규칙 = 6,432만 · 낙폭 -3.3% · 103건")
    print("")

    print("=" * 96)
    print("  읽는 법")
    print("    - 기준보다 끝 자산이 크고 낙폭이 안 나빠져야 바꾼다")
    print("    - 전체 기간과 2025·26 제외에서 **같은 방향**이어야 믿을 만하다")
    print("    - 기준보다 **끝 자산이 크고 낙폭이 안 나빠져야** 쓸 값어치가 있다")
    print("    - **산 것 수가 기준과 비슷해야** 제대로 견준 것이다")
    print("      (거르기가 아니라 고르기라 후보 수는 안 변한다)")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
