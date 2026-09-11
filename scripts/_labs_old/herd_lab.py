#!/usr/bin/env python3
r"""
herd_lab.py — **188차 · 업종이 같이 움직이는 것** (2026-09-09 신설)

## 사용자 지적
```
「**반도체는 관련 종목이 같이 오르고 같이 내리는 특징**이 있고,
  그마다 업종마다 특성이 있을 것 같은데」
```

## 여태 뭘 잘못했나
```
① 업종별 시험 넷(169·179·180·184차)은 전부
   **「볼린저·낙폭 문턱을 업종마다 다르게」**였다 -> 다 실패
   -> 사용자가 말한 「**같이 움직인다**」는 안 재봤다

② 161차에 이미 좋은 게 있었는데 4관문에 안 넣었다
   업종지수 -10%↓ 인 날만: 1년 **802개** · 20일 **71.9%** · +9.83%
   (지금 규칙 2,106개 · 60.1%)

③ 168차 G절 「같은 업종 몇 개」는 **집계가 틀려** 0건으로 나왔다
```

## 여기서 제대로 재는 것
```
A 업종지수 낙폭 눈금        -3 ~ -20% 촘촘히 (161차는 -10% 하나만)
B **같이 빠진 개수**        그날 같은 업종에서 조건을 통과한 종목이 몇이나
C **업종 동조성**          그 업종 종목들의 20일 낙폭 **중앙값** — 업종 자체가 빠졌나
D **혼자 빠졌나 같이 빠졌나** 업종은 멀쩡한데 이 종목만 빠진 것 vs 업종이 통째로
E 업종 x 시장             둘 다 빠진 날 / 업종만 / 시장만
F 업종별로 A~D 가 다른가    반도체와 음식료가 정말 다른가
```

## 잣대
```
① 1년에 몇 개  ② 20일 뒤 오른 비율  ③ 평균 몇 %
바탕(아무 종목·아무 날) 20일 = 43.5% · +0.33%
```

쓰는 법:
    python scripts\herd_lab.py
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

    print("  수익률 붙이는 중...", flush=True)
    for x in 사건:
        x["_20"] = 앞수익(x, 20)
        x["_40"] = 앞수익(x, 40)
    해수 = 10.4

    # ── 업종 ──
    업종 = {}
    _ip = os.path.join(O._DATA, "industry.json")
    if os.path.exists(_ip):
        for c2, v2 in json.load(io.open(_ip, encoding="utf-8-sig")).items():
            if isinstance(v2, dict) and v2.get("업종명"):
                업종[c2] = str(v2["업종명"])
    for x in 사건:
        x["_업"] = 업종.get(x["code"])

    def 바탕(x):
        return (x.get("재통과") == 1.0 and 300 <= x["시총억"] < 2000
                and x["대금억"] >= 1.0)

    def 신호(x):
        return 바탕(x) and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0

    # ══ ⭐ B·C·D — **같이 움직이는가**를 제대로 센다 ══
    #    ⚠️ 168차 G절은 **조건 통과 전 후보 전체**를 세어 다 「10개 이상」이 됐다.
    #       여기서는 **조건을 통과한 것만** 날·업종별로 센다
    print("  업종별 동조성 세는 중...", flush=True)
    import statistics as _st2
    날업낙 = {}          # (날, 업종) -> 그 업종 전 종목의 20일 낙폭들
    날업신호 = {}        # (날, 업종) -> 조건을 통과한 종목 수
    날업대형 = {}        # (날, 업종) -> 그 업종 **1조 이상** 종목들의 낙폭
    날업중형 = {}        # (날, 업종) -> 2천억~1조
    for x in 사건:
        if not x.get("_업"):
            continue
        키 = (x["인"], x["_업"])
        날업낙.setdefault(키, []).append(x["낙폭20"])
        if 신호(x):
            날업신호[키] = 날업신호.get(키, 0) + 1
        # ⭐ 그 업종의 **대형주(1조↑)** 와 **중형주(2천억~1조)** 낙폭
        if x["시총억"] >= 10000:
            날업대형.setdefault(키, []).append(x["낙폭20"])
        elif x["시총억"] >= 2000:
            날업중형.setdefault(키, []).append(x["낙폭20"])
    for x in 사건:
        키 = (x["인"], x.get("_업"))
        # ⭐⭐ **그 업종 대형주가 빠졌나** (2026-09-09 사용자 지적)
        #    「삼성·하이닉스는 등락폭이 작고 소부장은 크다.
        #      매수 타이밍만 알면 오히려 소부장이 더 큰 수익」
        #    ⚠️ 대형주는 우리 우주(300~2,000억) 밖이라 **후보가 아니다**.
        #       그러나 **신호로는 쓸 수 있다** — 한 번도 안 해봤다
        대 = 날업대형.get(키)
        x["_업대형낙"] = (_st2.median(대) if 대 else None)
        중 = 날업중형.get(키)
        x["_업중형낙"] = (_st2.median(중) if 중 else None)
        v = 날업낙.get(키)
        # C 업종 동조성 — 그 업종 종목들의 20일 낙폭 **중앙값**
        x["_업낙중앙"] = (_st2.median(v) if (v and len(v) >= 5) else None)
        # B 같이 빠진 개수 — 조건을 통과한 종목 수
        x["_같이"] = 날업신호.get(키, 0)
        # D 혼자인가 같이인가 — 나와 업종 중앙값의 차이
        x["_혼자정도"] = ((x["낙폭20"] - x["_업낙중앙"])
                        if x["_업낙중앙"] is not None else None)

    def 있(x, k):
        return x.get(k) is not None

    def 세기(라, fn, 최소=150):
        칸 = [x for x in 사건 if fn(x)]
        n = len(칸)
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if n < 최소 or len(v) < 80:
            print(f"  {라:<36}{n:>9,}   표본 부족")
            return None
        이 = sum(1 for z in v if z > 0) / len(v) * 100
        평 = sum(v) / len(v)
        v4 = [z["_40"] for z in 칸 if z.get("_40") is not None]
        이4 = (sum(1 for z in v4 if z > 0) / len(v4) * 100) if v4 else 0
        평4 = (sum(v4) / len(v4)) if v4 else 0
        print(f"  {라:<36}{n:>9,}{n/해수:>8.0f}{이:>9.1f}%{평:>+9.2f}"
              f"{이4:>9.1f}%{평4:>+9.2f}")
        return (이, 평, n)

    머2 = (f"  {'설정':<36}{'건수':>9}{'1년에':>8}"
           f"{'20일 이김':>10}{'평균':>9}{'40일 이김':>10}{'평균':>9}")

    print("\n" + "=" * 112)
    print("  188차 · **업종이 같이 움직이는 것**")
    print("  「반도체는 관련 종목이 **같이 오르고 같이 내리는 특징**이 있고」 (사용자)")
    print(f"  후보 {len(사건):,}건 · 바탕 20일 43.5% · +0.33% "
          f"· 상장폐지 {O.폐지손실:.0f}%")
    print("=" * 112)
    print("\n  ── 기준 ──")
    print(머2)
    세기("지금 규칙", 신호)

    print("\n  ── A **업종지수**가 얼마나 빠진 날 ──")
    print("     ⚠️ 161차는 -10% 하나만 봤다. 여기서 촘촘히")
    print(머2)
    for 문 in (-3, -5, -8, -10, -12, -15, -20):
        세기(f"업종지수 20일 {문}%↓ 인 날",
             lambda x, a=문: 신호(x) and 있(x, "섹터낙폭") and x["섹터낙폭"] <= a)

    print("\n  ── B ⭐ **같은 업종에서 몇 종목이나 같이 걸렸나** ──")
    print("     ⚠️ 168차 G절은 집계가 틀려 다 0건이었다. 여기서 제대로")
    print(머2)
    for 라, lo, hi in (("1종목뿐 (혼자)", 1, 2), ("2종목", 2, 3),
                       ("3~4종목", 3, 5), ("5~9종목", 5, 10),
                       ("10종목↑ (업종 전체가)", 10, 9999)):
        세기(f"같이 걸린 게 {라}",
             lambda x, a=lo, b=hi: 신호(x) and a <= x["_같이"] < b)

    print("\n  ── C ⭐ **업종 자체가 빠졌나** (그 업종 종목들 낙폭 중앙값) ──")
    print(머2)
    for 라, lo, hi in (("업종이 올라 있다 (+5%↑)", 5, 9e9),
                       ("업종 제자리 (-5~+5%)", -5, 5),
                       ("업종도 빠짐 (-5~-10%)", -10, -5),
                       ("업종이 많이 빠짐 (-10~-20%)", -20, -10),
                       ("업종이 폭락 (-20%↓)", -9e9, -20)):
        세기(f"{라}",
             lambda x, a=lo, b=hi: (신호(x) and 있(x, "_업낙중앙")
                                    and a <= x["_업낙중앙"] < b))

    print("\n  ── D ⭐ **혼자 빠졌나 같이 빠졌나** (나 − 업종 중앙값) ──")
    print(머2)
    for 라, lo, hi in (("업종보다 훨씬 더 빠짐 (-20%p↓)", -9e9, -20),
                       ("더 빠짐 (-20~-10%p)", -20, -10),
                       ("조금 더 빠짐 (-10~-3%p)", -10, -3),
                       ("업종과 비슷 (-3~+3%p)", -3, 3),
                       ("업종보다 덜 빠짐 (+3%p↑)", 3, 9e9)):
        세기(f"{라}",
             lambda x, a=lo, b=hi: (신호(x) and 있(x, "_혼자정도")
                                    and a <= x["_혼자정도"] < b))

    print("\n  ── G ⭐⭐ **그 업종 대형주(1조↑)가 빠졌나** ──")
    print("     「삼성·하이닉스가 빠진 날에 소부장을 사는 것」이 기회인가 (사용자)")
    print("     ⚠️ 대형주는 우리 후보가 아니다 — **신호로만** 쓴다")
    print(머2)
    for 라, lo, hi in (("대형주가 올라 있다 (+5%↑)", 5, 9e9),
                       ("대형주 제자리 (-5~+5%)", -5, 5),
                       ("대형주도 빠짐 (-5~-10%)", -10, -5),
                       ("대형주가 많이 빠짐 (-10~-20%)", -20, -10),
                       ("대형주 폭락 (-20%↓)", -9e9, -20)):
        세기(f"{라}",
             lambda x, a=lo, b=hi: (신호(x) and 있(x, "_업대형낙")
                                    and a <= x["_업대형낙"] < b))
    print()
    for 라, lo, hi in (("중형주(2천억~1조) 올라 있다", 5, 9e9),
                       ("중형주 제자리", -5, 5),
                       ("중형주도 빠짐 (-10~-20%)", -20, -10),
                       ("중형주 폭락 (-20%↓)", -9e9, -20)):
        세기(f"{라}",
             lambda x, a=lo, b=hi: (신호(x) and 있(x, "_업중형낙")
                                    and a <= x["_업중형낙"] < b))
    print()
    print("     [대형주는 멀쩡한데 내가 크게 빠진 경우 vs 같이 빠진 경우]")
    세기("대형주 멀쩡(-5%↑) · 내가 -20%↓",
         lambda x: (신호(x) and 있(x, "_업대형낙")
                    and x["_업대형낙"] >= -5 and x["낙폭20"] <= -20))
    세기("대형주도 빠짐(-10%↓) · 내가 -20%↓",
         lambda x: (신호(x) and 있(x, "_업대형낙")
                    and x["_업대형낙"] <= -10 and x["낙폭20"] <= -20))

    print("\n  ── E **업종 × 시장** ──")
    print(머2)
    for 라, 업, 시 in (("업종만 -10%↓ (시장은 멀쩡)", True, False),
                       ("시장만 -10%↓ (업종은 멀쩡)", False, True),
                       ("둘 다 -10%↓", True, True),
                       ("둘 다 멀쩡", False, False)):
        세기(f"{라}",
             lambda x, a=업, b=시: (신호(x) and 있(x, "섹터낙폭")
                                   and 있(x, "시장낙폭")
                                   and ((x["섹터낙폭"] <= -10) == a)
                                   and ((x["시장낙폭"] <= -10) == b)))

    print("\n  ── F **업종마다 A~D 가 정말 다른가** ──")
    print("     (반도체와 음식료가 다른지 — 건수 1,000 이상 업종만)")
    업칸 = {}
    for x in 사건:
        if 신호(x) and x.get("_업"):
            업칸.setdefault(x["_업"], []).append(x)
    print(f"  {'업종':<16}{'건수':>8}{'지금':>8}"
          f"{'업종 -10%↓ 인 날':>18}{'혼자 빠짐':>14}{'같이 빠짐':>14}")
    for 업 in sorted(업칸, key=lambda z: -len(업칸[z])):
        칸 = 업칸[업]
        if len(칸) < 1000:
            continue

        def _점(칸2):
            v = [z["_20"] for z in 칸2 if z.get("_20") is not None]
            return (f"{sum(1 for z in v if z > 0)/len(v)*100:.1f}% ({len(v):,})"
                    if len(v) >= 80 else "-")
        a = _점(칸)
        b = _점([z for z in 칸 if 있(z, "섹터낙폭") and z["섹터낙폭"] <= -10])
        c = _점([z for z in 칸 if 있(z, "_혼자정도") and z["_혼자정도"] <= -10])
        d = _점([z for z in 칸 if z["_같이"] >= 5])
        print(f"  {업[:15]:<16}{len(칸):>8,}{a:>8}{b:>18}{c:>14}{d:>14}")

    print("\n" + "=" * 112)
    print("  읽는 법")
    print("    - A·C 가 좋으면 **「업종이 통째로 빠진 날에 산다」**가 답이다")
    print("    - D 에서 「혼자 빠짐」이 좋으면 **업종은 멀쩡한데 이것만 빠진 것**을 산다")
    print("      둘이 반대 방향이면 **업종 특성이 진짜로 있다**는 뜻이다")
    print("    - F 에서 업종마다 부호가 갈리면 **업종별로 따로** 써야 한다")
    print("    - 좋아 보이면 **4관문**으로 넘긴다")
    print("=" * 112)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-09_188차_업종동조성.txt")

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
