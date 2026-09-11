#!/usr/bin/env python3
r"""
sector_rule_lab.py — **169차 · 섹터·크기마다 다른 규칙** (2026-09-08 신설)

## 사용자가 계속 말해온 것
```
「종목/섹터마다 규칙 적용 —
  **꼭 한 가지 규칙으로 모든 종목을 선별하려고 하지 않아도 돼**」
```
맞는 말인데 **한 번도 안 재봤다.** 지금까지 시험은 전부
「모든 종목에 같은 문턱 하나」였다

## 왜 값어치가 있나
```
반도체가 -10% 빠진 것과 음식료가 -10% 빠진 것은 **같은 일이 아니다**
반도체는 원래 많이 움직이고 음식료는 덜 움직인다
=> 섹터마다 「많이 빠졌다」의 뜻이 달라야 한다
```

## ⚠️⚠️ 가장 큰 위험 — **과적합**
```
섹터가 20개면 섹터마다 문턱을 고르는 순간 **고를 것이 20배**가 된다.
과거에 맞추기는 쉽고 앞으로 맞기는 어렵다
=> 그래서 **E절(걷기 검증)이 이 시험의 핵심**이다.
   앞 기간에서 고른 문턱을 **뒤 기간에 그대로 써서** 재본다.
   거기서 안 되면 아무리 A~D가 좋아도 못 쓴다
```

## 잣대 — 155차와 같다 (매수 기회를 깎지 않는 잣대)
```
① 1년에 몇 개  ② 20일 뒤 **오른 비율**  ③ 평균 몇 %
⚠️ 자본 시뮬을 안 쓴다. 그건 적게 살수록 점수가 올라 **기회를 깎는다**
```

## 재는 것
```
A 섹터마다 지금 규칙이 얼마나 다른가
B 섹터마다 **낙폭 문턱**을 따로 고르면 (그 섹터의 평소 움직임에 맞춰)
C 크기대마다 따로
D 시장(코스피/코스닥)마다 따로
E ⭐ **걷기 검증** — 앞에서 고른 문턱을 뒤에 써보면 (과적합 검사)
F 「그 섹터 기준으로 몇 시그마 빠졌나」 — 문턱을 안 고르고 **표준화**한다
```
F 가 제일 안전하다. 고르는 게 없으니 과적합이 안 생긴다

쓰는 법:
    python scripts\sector_rule_lab.py
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

    print("  후보 모으는 중 (크기 조건도 느슨하게)...", flush=True)
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            # ⚠️ **크기 조건을 여기서 걸지 않는다** — 훑을 대상이기 때문이다.
            #    아주 작은 것(100억)과 아주 큰 것(50조)만 잘라 낸다
            if 시총 < 1e10 or 시총 >= 5e13:
                continue
            fm = 재무값(code, d1) or {}
            재통과 = 1.0 if (
                fm.get("잉여금비율", -9e9) >= 확정["잉여금"]
                and fm.get("부채비율", 9e9) <= 확정["부채"]
                and fm.get("흑자") == 1.0) else 0.0
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
            볼 = (c1 - s20) / (2 * sd)
            if sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            낙60 = ((c1 / sq[kk - 60] - 1) * 100
                    if kk >= 60 and sq[kk - 60] > 0 else None)
            s60 = st.mean(sq[kk - 59:kk + 1]) if kk >= 59 else None
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            g = 하루갭.get(code)
            if not b0 or not v0 or not o0 or g is None:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            량 = (거량.get(d1) or {}).get(code) or 0
            사건.append({
                "인": i + 1, "code": code, "원시": o0, "대금": b0[2],
                "볼린저": 볼, "낙폭20": 낙,
                "시총억": 시총 / 1e8, "대금억": 대금 / 1e8, "거래량": 량,
                "회전율": (대금 / 시총 * 100) if 시총 > 0 else 0,
                "갭": g, "매수": 매수, "재통과": 재통과, "낙폭60": 낙60,
                "해": d1[:4],
                "60일선대비": ((c1 / s60 - 1) * 100) if s60 else None,
                "주가": o0,
                "잉여금": (재무값(code, d1) or {}).get("잉여금비율"),
                "부채": (재무값(code, d1) or {}).get("부채비율"),
                "ROE": (재무값(code, d1) or {}).get("ROE"),
                "영업이익률": (재무값(code, d1) or {}).get("영업이익률"),
                "순이익률": (재무값(code, d1) or {}).get("순이익률"),
                "유동비율": (재무값(code, d1) or {}).get("유동비율")})
    # ══ 지수 붙이기 ══ (2026-09-07 신설)
    print("  지수 읽는 중...", flush=True)
    지수 = {}          # 날짜 -> {지수이름: 종가}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        하루 = {}
        for 이름2, v2 in (d2.get("지수") or {}).items():
            try:
                하루[이름2] = float(str(v2.get("종가")).replace(",", ""))
            except (TypeError, ValueError, AttributeError):
                pass
        if 하루:
            지수[d2.get("기준일") or os.path.basename(f)[:8]] = 하루
    print(f"    지수 {len(지수):,}일", flush=True)

    def 지수계열(이름2):
        """날 순서대로 늘어놓은 종가 (없는 날은 None)"""
        return [(지수.get(d) or {}).get(이름2) for d in 날]

    _계열캐시 = {}

    def 낙폭(이름2, i2, n=20):
        """i2 자리에서 n일 전 대비 몇 % 인가"""
        sq = _계열캐시.get(이름2)
        if sq is None:
            sq = 지수계열(이름2)
            _계열캐시[이름2] = sq
        if i2 < n or i2 >= len(sq):
            return None
        a, b = sq[i2 - n], sq[i2]
        if not a or not b:
            return None
        return (b / a - 1) * 100

    def 변동성(이름2, i2, n=20):
        sq = _계열캐시.get(이름2)
        if sq is None:
            sq = 지수계열(이름2)
            _계열캐시[이름2] = sq
        if i2 < n or i2 >= len(sq):
            return None
        칸 = [x for x in sq[i2 - n:i2 + 1] if x]
        if len(칸) < n * 0.8:
            return None
        일간 = [(칸[j] / 칸[j - 1] - 1) * 100 for j in range(1, len(칸))
                if 칸[j - 1]]
        return st.pstdev(일간) if len(일간) > 3 else None

    # ── 업종 매핑 (표준산업분류 63종 -> 코스닥 업종지수 20종) ──
    # ⚠️ 손으로 이은 표다. 매핑률을 아래에서 찍는다
    _업종map = {
        "식료품": "음식료·담배", "음료": "음식료·담배", "담배": "음식료·담배",
        "섬유제품": "섬유·의류", "의복": "섬유·의류", "가죽·가방·신발": "섬유·의류",
        "펄프·종이": "종이·목재", "목재": "종이·목재", "가구": "종이·목재",
        "화학": "화학", "고무·플라스틱": "화학", "코크스·석유정제": "화학",
        "의약품": "제약",
        "비금속광물": "비금속",
        "1차금속": "금속", "금속가공": "금속",
        "기계·장비": "기계·장비",
        "전자부품·통신장비": "전기전자", "전기장비": "전기전자",
        "반도체": "전기전자",
        "의료·정밀·광학": "의료·정밀기기",
        "자동차": "운송장비·부품", "자동차부품": "운송장비·부품",
        "기타운송장비": "운송장비·부품", "선박": "운송장비·부품",
        "도매": "유통", "소매": "유통", "상품중개": "유통",
        "종합건설": "건설", "전문건설": "건설", "건설": "건설",
        "육상운송": "운송·창고", "수상운송": "운송·창고",
        "항공운송": "운송·창고", "창고·운송서비스": "운송·창고",
        "통신": "통신", "우편·통신": "통신",
        "금융": "금융", "금융지원": "금융", "보험": "금융",
        "연구개발": "일반서비스", "전문서비스": "일반서비스",
        "사업지원": "일반서비스", "교육": "일반서비스",
        "출판": "출판·매체복제", "영상·오디오": "오락·문화",
        "컴퓨터프로그래밍": "IT 서비스", "정보서비스": "IT 서비스",
        "기타제조": "기타제조",
    }
    _산업 = {}
    _ip = os.path.join(O._DATA, "industry.json")
    if os.path.exists(_ip):
        for c2, v2 in json.load(io.open(_ip, encoding="utf-8-sig")).items():
            if isinstance(v2, dict):
                _산업[c2] = str(v2.get("업종명") or "")

    def 업종지수(code):
        나 = _산업.get(code) or ""
        if 나 in _업종map:
            return _업종map[나]
        for k, v in _업종map.items():
            if k and (k in 나 or 나 in k):
                return v
        return None

    시장표 = {}
    _sp = os.path.join(O._DATA, "stock-base.json")
    if os.path.exists(_sp):
        _sb = json.load(io.open(_sp, encoding="utf-8-sig"))
        for c2, v2 in _sb.items():
            if isinstance(v2, dict) and v2.get("시장"):
                시장표[c2] = str(v2["시장"])

    붙음, 섹붙음 = 0, 0
    for x in 사건:
        i2 = x["인"] - 1
        시장 = 시장표.get(x["code"]) or ""
        지수이름 = "코스닥" if "닥" in 시장 else "코스피"
        시낙 = 낙폭(지수이름, i2)
        x["시장낙폭"] = 시낙
        x["상대강도"] = (x["낙폭20"] - 시낙) if 시낙 is not None else None
        x["시장변동성"] = 변동성(지수이름, i2)
        큰 = 낙폭("코스닥 대형주", i2)
        작 = 낙폭("코스닥 소형주", i2)
        x["소형우위"] = (작 - 큰) if (큰 is not None and 작 is not None) else None
        if 시낙 is not None:
            붙음 += 1
        섹 = 업종지수(x["code"])
        섹낙 = 낙폭(섹, i2) if 섹 else None
        x["섹터"] = 섹
        x["섹터낙폭"] = 섹낙
        x["섹터대비"] = (x["낙폭20"] - 섹낙) if 섹낙 is not None else None
        if 섹낙 is not None:
            섹붙음 += 1
    print(f"  시장 지수 붙은 것 {붙음:,}/{len(사건):,} "
          f"· 섹터 지수 붙은 것 {섹붙음:,}/{len(사건):,} "
          f"({섹붙음/max(len(사건),1)*100:.0f}%)", flush=True)

    # ── 수급 붙이기 (flow-daily) ──
    import collections as _co
    print("  수급 붙이는 중...", flush=True)

    def _수(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).replace(",", "").replace("%", "").strip()
        try:
            return float(s)
        except ValueError:
            return None

    쓸코드 = {x["code"] for x in 사건}
    사건별 = {}
    for x in 사건:
        사건별.setdefault(x["인"] - 1, []).append(x)
    창 = {}
    지분창 = {}
    for i2, d2 in enumerate(날):
        p2 = os.path.join(O._DATA, "flow-daily", d2 + ".json")
        하루수급 = {}
        if os.path.exists(p2):
            try:
                하루수급 = (json.load(io.open(p2, encoding="utf-8-sig"))
                             .get("종목") or {})
            except ValueError:
                하루수급 = {}
        for code in 쓸코드:
            r2 = 하루수급.get(code)
            if not r2:
                continue
            종2 = _수(r2.get("종가"))
            if not 종2:
                continue
            창.setdefault(code, _co.deque(maxlen=20)).append(
                ((_수(r2.get("외국인")) or 0) * 종2,
                 (_수(r2.get("기관")) or 0) * 종2,
                 (_수(r2.get("개인")) or 0) * 종2))
            지2 = _수(r2.get("외국인지분율"))
            if 지2 is not None:
                지분창.setdefault(code, _co.deque(maxlen=21)).append(지2)
        for x in 사건별.get(i2, []):
            q2 = 창.get(x["code"])
            시총원 = x["시총억"] * 1e8
            if not q2 or 시총원 <= 0:
                continue

            def _몫(n, 자리, q2=q2, 시총원=시총원):
                return sum(z[자리] for z in list(q2)[-n:]) / 시총원 * 100
            x["외인1"] = _몫(1, 0)
            x["외인5"] = _몫(5, 0)
            x["외인20"] = _몫(20, 0)
            x["기관5"] = _몫(5, 1)
            x["기관20"] = _몫(20, 1)
            x["개인5"] = _몫(5, 2)
            z2 = 지분창.get(x["code"])
            if z2:
                x["지분율"] = z2[-1]
                x["지분20변화"] = z2[-1] - z2[0] if len(z2) >= 21 else None

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
            칸 = sorted(칸, key=lambda z: z["낙폭20"])[:_후보수]
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

    def 앞수익(x, n):
        i2 = x["인"]
        j = i2 + n
        if j >= len(날):
            return None
        a = 주가[날[i2]].get(x["code"])
        b = 주가[날[j]].get(x["code"])
        if not a or a[0] <= 0:
            return None
        if not b:
            return (O.폐지손실 - _비용) if x["code"] in _사라짐 else None
        return (b[0] / a[0] - 1) * 100 - _비용

    print("  기간별 수익률 붙이는 중...", flush=True)
    for x in 사건:
        x["_20"] = 앞수익(x, 20)
        x["_40"] = 앞수익(x, 40)
    해수 = 10.4

    def 재무통과(x):
        return x.get("재통과") == 1.0

    def 대금통과(x):
        return x["대금억"] >= 1.0

    def 크기통과(x):
        return 300 <= x["시총억"] < 2000      # ⭐ 158차: 하한 300억

    def 바탕(x):
        return 재무통과(x) and 대금통과(x) and 크기통과(x)

    def 점(칸, 기="_20"):
        v = [x[기] for x in 칸 if x.get(기) is not None]
        if len(v) < 60:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(칸))

    def 줄(라, p, 덧=""):
        if p is None:
            print(f"  {라:<34}      표본 부족")
            return
        이, 평, n = p
        print(f"  {라:<34}{n:>8,}{n/해수:>7.0f}{이:>8.1f}%{평:>+8.2f}   {덧}")

    머2 = (f"  {'설정':<34}{'건수':>8}{'1년에':>7}{'20일 이김':>9}{'평균':>8}")

    print("\n" + "=" * 104)
    print("  169차 · **섹터·크기마다 다른 규칙**")
    print("  「꼭 한 가지 규칙으로 모든 종목을 선별하려고 하지 않아도 돼」 (사용자)")
    print(f"  후보 {len(사건):,}건 · 바탕(아무 종목·아무 날) 20일 44.7% · +0.65%")
    print(f"  ⚠️ 상장폐지는 {O.폐지손실:.0f}% 손실로 센다 · 시총 하한은 **300억**")
    print("=" * 104)

    # ── 섹터별 평소 움직임 ──
    섹칸 = {}
    for x in 사건:
        if 바탕(x) and x.get("섹터"):
            섹칸.setdefault(x["섹터"], []).append(x)
    섹들 = sorted(섹칸, key=lambda s: -len(섹칸[s]))
    print(f"\n  섹터 {len(섹들)}개 (붙은 사건 "
          f"{sum(len(v) for v in 섹칸.values()):,}건)")

    def 표준(칸):
        """그 칸의 낙폭 평균·표준편차"""
        v = [x["낙폭20"] for x in 칸]
        m = sum(v) / len(v)
        sd = (sum((z - m) ** 2 for z in v) / len(v)) ** 0.5 or 1e-9
        return m, sd

    # ── A 섹터마다 지금 규칙 ──
    print("\n  ── A **섹터마다** 지금 규칙(볼린저 -1.0 · 낙폭 -10%) ──")
    print(머2)
    전체 = [x for x in 사건 if 바탕(x) and x["볼린저"] <= -1.0
            and x["낙폭20"] <= -10.0]
    줄("모든 섹터 (지금)", 점(전체))
    print()
    섹성적 = []
    for s in 섹들[:24]:
        칸 = [x for x in 섹칸[s] if x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0]
        p = 점(칸)
        m, sd = 표준(섹칸[s])
        줄(f"{str(s)[:30]}", p, f"평소 낙폭 {m:+.1f}% (±{sd:.1f})")
        if p:
            섹성적.append((p[0], s, p))
    if 섹성적:
        섹성적.sort(reverse=True)
        print(f"\n     가장 좋은 섹터 {섹성적[0][1]} {섹성적[0][2][0]:.1f}% · "
              f"가장 나쁜 섹터 {섹성적[-1][1]} {섹성적[-1][2][0]:.1f}%  "
              f"→ **차이 {섹성적[0][2][0]-섹성적[-1][2][0]:.1f}%p**")

    # ── B 섹터마다 낙폭 문턱 고르기 ──
    print("\n  ── B **섹터마다 낙폭 문턱**을 따로 고르면 ──")
    print("     ⚠️ 과적합 위험이 크다. E절(걷기)에서 진짜인지 가린다")
    문턱들 = (-5, -8, -10, -15, -20, -30)
    고른 = {}
    for s in 섹들:
        최 = None
        for 문 in 문턱들:
            칸 = [x for x in 섹칸[s] if x["볼린저"] <= -1.0 and x["낙폭20"] <= 문]
            p = 점(칸)
            if p and (최 is None or p[0] > 최[1]):
                최 = (문, p[0])
        if 최:
            고른[s] = 최[0]
    print(f"     섹터 {len(고른)}개에서 문턱을 골랐다")
    맞춘 = []
    for s, 문 in 고른.items():
        맞춘 += [x for x in 섹칸[s] if x["볼린저"] <= -1.0 and x["낙폭20"] <= 문]
    print(머2)
    줄("모든 섹터 같은 문턱 -10% (지금)", 점(전체))
    줄("**섹터마다 고른 문턱**", 점(맞춘))
    from collections import Counter as _C
    print(f"     고른 문턱 분포: {dict(_C(고른.values()))}")

    # ── C 크기대마다 ──
    print("\n  ── C **크기대마다** 문턱을 따로 ──")
    print(머2)
    크기대 = (("300~500억", 300, 500), ("500~1,000억", 500, 1000),
              ("1,000~2,000억", 1000, 2000))
    for 라, lo, hi in 크기대:
        칸0 = [x for x in 사건 if 재무통과(x) and 대금통과(x)
               and lo <= x["시총억"] < hi]
        print(f"\n   [{라}]  (전체 {len(칸0):,}건)")
        for 문 in 문턱들:
            줄(f"  낙폭 {문}%",
               점([x for x in 칸0 if x["볼린저"] <= -1.0 and x["낙폭20"] <= 문]))

    # ── D 시장마다 ──
    print("\n  ── D **시장(코스피/코스닥)마다** ──")
    print(머2)
    for 문 in 문턱들:
        줄(f"낙폭 {문}% (섹터 붙은 것만)",
           점([x for x in 사건 if 바탕(x) and x.get("섹터")
               and x["볼린저"] <= -1.0 and x["낙폭20"] <= 문]))

    # ── E ⭐ 걷기 검증 ──
    print("\n" + "=" * 104)
    print("  E ⭐ **걷기 검증** — 앞에서 고른 문턱을 **뒤에 그대로 쓰면**")
    print("     (여기서 안 되면 B 가 아무리 좋아도 과적합이다)")
    print("=" * 104)
    print(머2)
    for 배운끝, 쓸시작, 쓸끝 in (("2019", "2020", "2022"),
                                ("2022", "2023", "2026"),
                                ("2021", "2022", "2026")):
        배움 = {}
        for s in 섹들:
            앞칸 = [x for x in 섹칸[s] if x["해"] <= 배운끝]
            최 = None
            for 문 in 문턱들:
                p = 점([x for x in 앞칸
                        if x["볼린저"] <= -1.0 and x["낙폭20"] <= 문])
                if p and (최 is None or p[0] > 최[1]):
                    최 = (문, p[0])
            if 최:
                배움[s] = 최[0]
        뒤맞춘 = []
        for s, 문 in 배움.items():
            뒤맞춘 += [x for x in 섹칸[s]
                       if 쓸시작 <= x["해"] <= 쓸끝
                       and x["볼린저"] <= -1.0 and x["낙폭20"] <= 문]
        뒤같음 = [x for x in 사건 if 바탕(x) and x.get("섹터")
                  and 쓸시작 <= x["해"] <= 쓸끝
                  and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0]
        print(f"\n   [~{배운끝} 배워서 {쓸시작}~{쓸끝} 에 쓴다 "
              f"· 섹터 {len(배움)}개]")
        a = 점(뒤같음)
        b = 점(뒤맞춘)
        줄("모두 같은 문턱 -10%", a)
        줄("**섹터마다 배운 문턱**", b,
           # ⚠️ 기회 수를 같이 본다 (2026-09-09). 전에는 이김만 봐서
           #    적게 살수록 이기는 것으로 찍혔다 (185차에서 들통)
           (("✅ 낫다" if (b[2] / a[2] if a[2] else 0) >= 0.5
             else f"❌ 기회가 {(b[2]/a[2]*100 if a[2] else 0):.0f}%로 줄었다")
            if (a and b and b[0] > a[0]) else "❌ 안 낫다"))

    # ── F 섹터 기준 표준화 ──
    print("\n" + "=" * 104)
    print("  F ⭐ 문턱을 **안 고르고** — 「그 섹터 기준으로 몇 시그마 빠졌나」")
    print("     (고르는 게 없으니 과적합이 안 생긴다. 가장 안전한 방법이다)")
    print("=" * 104)
    print(머2)
    통계 = {s: 표준(섹칸[s]) for s in 섹들 if len(섹칸[s]) >= 200}
    for x in 사건:
        s = x.get("섹터")
        if s in 통계 and 바탕(x):
            m, sd = 통계[s]
            x["섹시그마"] = (x["낙폭20"] - m) / sd
    줄("지금 (모두 -10%)", 점(전체))
    for 시 in (-0.5, -1.0, -1.5, -2.0, -2.5):
        줄(f"섹터 기준 **{시}σ** 이하",
           점([x for x in 사건 if x.get("섹시그마") is not None
               and x["볼린저"] <= -1.0 and x["섹시그마"] <= 시]))
    print("\n     (볼린저 조건 없이)")
    for 시 in (-1.0, -1.5, -2.0, -2.5):
        줄(f"섹터 기준 {시}σ 이하 · 볼린저 없이",
           점([x for x in 사건 if x.get("섹시그마") is not None
               and x["섹시그마"] <= 시]))

    print("\n" + "=" * 104)
    print("  읽는 법")
    print("    - **E 가 이 시험의 답이다.** 거기서 안 되면 B·C 는 과적합이다")
    print("    - F 는 고르는 게 없어서 안전하다. E 가 안 되면 **F 를 본다**")
    print("    - 무엇이든 바꾸려면 165차 4관문을 지나야 한다")
    print("=" * 104)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-08_169차_섹터별규칙.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
