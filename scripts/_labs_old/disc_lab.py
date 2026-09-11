#!/usr/bin/env python3
r"""
disc_lab.py — **133차 · 공시를 축으로 규칙을 처음부터 짠다** (2026-09-07 신설)

## 사용자 지적
```
「공시 자체는 테스트 충분히 했나? 뉴스랑 중복인지 말고, 공시 자체가 유효한지!」
「하나의 자료로도 충분한 매수 기회를 잡을 수 있다는 결과가 나오면
  그것도 브리핑에 반영할 수 있어」
```
⇒ **우리 규칙에 얹을 필요가 없다.** 공시만으로 독립 규칙을 만들어도 된다

## 지금까지 공시를 어떻게 봤나 — 충분하지 않았다
```
97d 증자감자      기각 — 공시 **종류 하나**만 봤다
121차 정보신호     기각 — 우리 규칙에 **얹었다**
132차 공시 시각    표본 부족 — 우리 후보 703건 중 실제 매수 **1건**
122차 단독신호     ⭐ 여기서 딱 한 줄 나왔다:
      「공시 난 것 · 목표10% 5일」 = 6,760만 · 연 +28.33% · **낙폭 -80.0%** · 2,643건
      끝 자산은 우리 규칙(6,432만)보다 **크다.** 그런데 낙폭이 -80%다
```
**낙폭 -80%를 잡을 수 있으면 쓸 수 있다.** 122차는 재무·시총상한을 안 걸었다.
공시를 축으로 두고 **조건을 하나씩 얹어가며** 낙폭이 잡히는지 본다

## 짜임새
```
축     그날 공시가 난 종목 -> 다음날 시가에 산다
       ⚠️ 볼린저·낙폭은 **안 건다.** 그건 우리 규칙이고 여기선 공시가 축이다
층     ① 공시만  ② +시총 상한  ③ +재무  ④ +거래대금  ⑤ 전부
갈래   공시 종류(챙길공시/그밖) · 시각(장중/장후/새벽/장전) · 건수
매도   124차에서 채택한 **나눠팔기** (반 +15%/40일 · 반 +40%/90일)
```
⚠️ 잣대는 **끝 자산과 낙폭 둘 다**다. 낙폭 -80%면 끝 자산이 커도 못 쓴다

쓰는 법:
    python scripts\disc_lab.py
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
    기본틀["상대갭"] = 99.0        # ⚠️ 갭 문턱을 **끈다** — 공시가 축이다
    기본틀["시총하한"] = 500
    기본틀["시총상한"] = 9e9       # 사실상 상한 없음
    기본틀["대금하한"] = 0.0

    def 있(x, k):
        return x.get(k) is not None

    def 층(이름, **바꿀):
        c = dict(기본틀)
        c.update(바꿀)
        return 이름, c

    층들 = [
        층("① 공시만 (조건 없음)"),
        층("② + 시총 2,000억 이하", 시총상한=2000),
        층("③ + 재무(잉여금30·부채80·흑자)",
           거름=lambda x: x.get("재무통과") == 1.0),
        층("④ + 거래대금 1억↑", 대금하한=1.0),
        층("⑤ + 시총 2,000억 + 재무 + 거래대금", 시총상한=2000, 대금하한=1.0,
           거름=lambda x: x.get("재무통과") == 1.0),
        층("⑥ ⑤ + 「챙길공시」만", 시총상한=2000, 대금하한=1.0,
           거름=lambda x: x.get("재무통과") == 1.0 and (x.get("챙길수") or 0) > 0),
        층("⑦ ⑤ + 장후·새벽 공시만", 시총상한=2000, 대금하한=1.0,
           거름=lambda x: x.get("재무통과") == 1.0
           and ((x.get("장후") or 0) + (x.get("새벽") or 0)) > 0),
        층("⑧ ⑤ + 장중 공시만 (견줌)", 시총상한=2000, 대금하한=1.0,
           거름=lambda x: x.get("재무통과") == 1.0 and (x.get("장중") or 0) > 0),
        층("⑨ ⑤ + 갭 하락 -3.5%p", 시총상한=2000, 대금하한=1.0, 상대갭=-3.5,
           거름=lambda x: x.get("재무통과") == 1.0),
        층("⑩ ⑤ + 20일 낙폭 -10% 이하", 시총상한=2000, 대금하한=1.0,
           거름=lambda x: x.get("재무통과") == 1.0
           and 있(x, "낙폭20") and x["낙폭20"] <= -10),
    ]

    for 끝년, 라 in ((None, "전체 기간"), ("2024", "2025·26 제외")):
        print("=" * 96)
        print("  == " + 라 + " ==  (공시를 축으로 · 매도는 124차 나눠팔기)")
        print("=" * 96)
        print(머)
        첫 = None
        for 이름, c in 층들:
            n2 = len(사건) if not c.get("거름") else sum(
                1 for x in 사건 if c["거름"](x))
            r = 시뮬(c, 끝년=끝년)
            if 첫 is None:
                첫 = r
            표(r, f"{이름} [{n2:,}건]", 첫 if 이름[0] != "①" else None)
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
