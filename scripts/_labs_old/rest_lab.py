#!/usr/bin/env python3
r"""
rest_lab.py — **168차 · 아직 한 번도 안 재본 재료들** (2026-09-08 신설)

## 왜
```
받아만 놓고 **한 번도 시험에 안 넣은 재료**가 남아 있었다:
  컨센서스 · 임원지분 · 뉴스 · 뉴스↔공시 겹침 · 거래대금 문턱 · 영업비용 · 같은날 겹침
```
사용자: 「예정 안 된 것 여섯도 테스트해」

## 자료가 얼마나 있나 (2026-09-08 실측)
```
컨센서스   21,191건 · 1,295종목  ⚠️ 2020 · 2024~26 만 있다 (2021~23 빈다)
임원지분   32,279건 · 2,234종목
뉴스       2,380종목 (한 종목에 200건 안팎)
미결제약정  ⚠️ **뺐다** — 주식선물은 210종목뿐이고 대부분 대형주라
           우리 우주(500~2,000억)와 거의 안 겹친다
```

## 잣대 — 155차와 같다
```
① 1년에 몇 개  ② 20일 뒤 **오른 비율**  ③ 평균 몇 %
바탕(아무 종목·아무 날) 20일 = **44.7% 오름 · +0.65%**
```
⚠️ 상장폐지는 -50% 손실로 센다

## 재는 것
```
A 컨센서스     최근 30·90일 리포트 있나 · 목표주가 상향인가
B 임원지분     최근 30·90일 임원이 **샀나** (증감 > 0)
C 뉴스         최근 5·20일 기사 수 · **평소보다 많은가**
D 뉴스↔공시    같은 날 둘 다 있나 (재료가 겹치면 더 센가)
E 거래대금 문턱 0.3 / 0.5 / 1 / 2 / 5억
F 영업비용     매출 대비 영업비용 (= 100 - 영업이익률)
G 같은날 겹침   그날 후보가 몇 개나 떴나 · 같은 업종이 몇 개나
```

쓰는 법:
    python scripts\rest_lab.py
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

    # ══ 168차: 안 써본 재료들을 붙인다 ══
    import collections as _c2

    print("  컨센서스 읽는 중...", flush=True)
    컨 = {}          # 코드 -> [(날짜8, 목표주가)]
    for f in sorted(glob.glob(os.path.join(O._DATA, "consensus", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        for r in (d2.get("리포트") or []):
            c2 = r.get("코드")
            날2 = str(r.get("날짜") or "").replace("-", "")
            if not c2 or len(날2) != 8:
                continue
            컨.setdefault(c2, []).append((날2, r.get("목표주가")))
    for c2 in 컨:
        컨[c2].sort()
    print(f"    컨센서스 {sum(len(v) for v in 컨.values()):,}건 · "
          f"{len(컨):,}종목", flush=True)

    print("  임원지분 읽는 중...", flush=True)
    임 = {}          # 코드 -> [(날짜8, 증감)]
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-exec", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        c2 = d2.get("종목")
        for r in (d2.get("이력") or []):
            날2 = str(r.get("접수일") or "").replace("-", "")
            if not c2 or len(날2) != 8:
                continue
            try:
                증 = float(str(r.get("증감") or 0).replace(",", ""))
            except ValueError:
                증 = 0.0
            임.setdefault(c2, []).append((날2, 증))
    for c2 in 임:
        임[c2].sort()
    print(f"    임원지분 {sum(len(v) for v in 임.values()):,}건 · "
          f"{len(임):,}종목", flush=True)

    print("  뉴스 읽는 중...", flush=True)
    뉴 = {}          # 코드 -> {날짜8: 건수}
    for f in sorted(glob.glob(os.path.join(O._DATA, "news", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        c2 = d2.get("종목") or os.path.basename(f)[:-5]
        칸 = _c2.Counter()
        for r in (d2.get("뉴스") or []):
            날2 = str(r.get("날짜") or "")
            if len(날2) == 8:
                칸[날2] += 1
        if 칸:
            뉴[c2] = dict(칸)
    print(f"    뉴스 {len(뉴):,}종목", flush=True)

    print("  공시 읽는 중...", flush=True)
    공 = O._공시(날)
    print(f"    공시 {len(공):,}일", flush=True)

    import bisect as _bs

    def 최근(줄, d8, 일수):
        """[(날짜8, 값)] 에서 d8 이전 일수 안의 것들"""
        if not 줄:
            return []
        앞 = (dt.date(int(d8[:4]), int(d8[4:6]), int(d8[6:]))
              - dt.timedelta(days=일수)).strftime("%Y%m%d")
        i0 = _bs.bisect_left(줄, (앞, -9e18))
        i1 = _bs.bisect_right(줄, (d8, 9e18))
        return 줄[i0:i1]

    print("  재료 붙이는 중...", flush=True)
    for x in 사건:
        d8 = 날[x["인"] - 1]
        c2 = x["code"]
        # A 컨센서스
        줄 = 컨.get(c2) or []
        for 일 in (30, 90):
            칸 = 최근(줄, d8, 일)
            x[f"컨_{일}"] = len(칸)
        칸90 = 최근(줄, d8, 90)
        목 = [v for _, v in 칸90 if isinstance(v, (int, float))]
        옛목 = [v for _, v in 최근(줄, d8, 365)[:-len(칸90) or None]
                if isinstance(v, (int, float))]
        x["컨_상향"] = (1.0 if (목 and 옛목 and max(목) > max(옛목)) else 0.0)
        # B 임원지분
        줄2 = 임.get(c2) or []
        for 일 in (30, 90):
            칸 = 최근(줄2, d8, 일)
            x[f"임_{일}"] = sum(v for _, v in 칸)
            x[f"임샀나_{일}"] = 1.0 if any(v > 0 for _, v in 칸) else 0.0
        # C 뉴스
        표 = 뉴.get(c2) or {}
        if 표:
            def 세(일수):
                앞 = (dt.date(int(d8[:4]), int(d8[4:6]), int(d8[6:]))
                      - dt.timedelta(days=일수)).strftime("%Y%m%d")
                return sum(v for k, v in 표.items() if 앞 <= k <= d8)
            n5, n20, n120 = 세(5), 세(20), 세(120)
            x["뉴_5"] = n5
            x["뉴_20"] = n20
            x["뉴_많음"] = (n5 / (n120 / 24)) if n120 >= 24 else None
        # D 공시
        x["공시있나"] = 1.0 if c2 in (공.get(d8) or {}) else 0.0
        x["뉴스도공시도"] = (1.0 if (x.get("공시있나") == 1.0
                                    and (x.get("뉴_5") or 0) > 0) else 0.0)
        # F 영업비용
        x["영업비용"] = (100 - x["영업이익률"]) if x.get("영업이익률") is not None else None

    # G 같은 날 겹침
    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    for i2, v in 묶.items():
        섹칸 = _c2.Counter(z.get("섹터") for z in v)
        for x in v:
            x["그날후보수"] = len(v)
            x["같은업종수"] = 섹칸.get(x.get("섹터"), 1)

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

    기간들 = (5, 20, 40)
    print("  기간별 수익률 붙이는 중...", flush=True)
    for x in 사건:
        for n in 기간들:
            x[f"_{n}"] = 앞수익(x, n)
    해수 = 10.4

    def 재무통과(x):
        return x.get("재통과") == 1.0

    def 신호(x):
        return (재무통과(x) and 500 <= x["시총억"] < 2000
                and x["대금억"] >= 1.0
                and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0)

    머2 = (f"  {'설정':<42}{'건수':>8}{'1년에':>7}"
           f"{'5일 이김':>9}{'평균':>8}{'20일 이김':>10}{'평균':>8}"
           f"{'40일 이김':>10}{'평균':>8}")

    def 세기(라, fn, 최소=120):
        칸 = [x for x in 사건 if fn(x)]
        n = len(칸)
        if n < 최소:
            print(f"  {라:<42}{n:>8,}   표본 부족")
            return
        줄 = f"  {라:<42}{n:>8,}{n/해수:>7.0f}"
        for 기 in 기간들:
            v = [x[f"_{기}"] for x in 칸 if x.get(f"_{기}") is not None]
            if len(v) < 60:
                줄 += f"{'-':>9}{'-':>8}"
                continue
            줄 += (f"{sum(1 for z in v if z > 0) / len(v) * 100:>8.1f}%"
                   f"{sum(v) / len(v):>+8.2f}")
        print(줄)

    print("\n" + "=" * 122)
    print("  168차 · **아직 한 번도 안 재본 재료들**")
    print(f"  후보 {len(사건):,}건 · 바탕(아무 종목·아무 날) 20일 44.7% · +0.65%")
    print(f"  ⚠️ 상장폐지는 {O.폐지손실:.0f}% 손실로 센다")
    print("=" * 122)

    덮 = {k: sum(1 for x in 사건 if x.get(k) not in (None, 0, 0.0))
          for k in ("컨_90", "임_90", "뉴_20", "공시있나")}
    print(f"\n  덮는 범위 — 컨센서스 {덮['컨_90']:,} · 임원 {덮['임_90']:,} · "
          f"뉴스 {덮['뉴_20']:,} · 공시 {덮['공시있나']:,} / {len(사건):,}건")

    print("\n  ── 기준 ──")
    print(머2)
    세기("지금 규칙", 신호)
    세기("아무 종목·아무 날", lambda x: True)

    print("\n  ── A **컨센서스** ──")
    print(머2)
    세기("+ 90일 안에 리포트 있음", lambda x: 신호(x) and (x.get("컨_90") or 0) > 0)
    세기("+ 90일 안에 리포트 **없음**",
         lambda x: 신호(x) and (x.get("컨_90") or 0) == 0)
    세기("+ 30일 안에 리포트 있음", lambda x: 신호(x) and (x.get("컨_30") or 0) > 0)
    세기("+ **목표주가 상향**", lambda x: 신호(x) and x.get("컨_상향") == 1.0)

    print("\n  ── B **임원지분** ──")
    print(머2)
    for 일 in (30, 90):
        세기(f"+ {일}일 안에 임원이 **샀다**",
             lambda x, a=일: 신호(x) and x.get(f"임샀나_{a}") == 1.0)
        세기(f"+ {일}일 안에 임원이 **팔았다**",
             lambda x, a=일: 신호(x) and (x.get(f"임_{a}") or 0) < 0)
        세기(f"+ {일}일 안에 아무 일 없음",
             lambda x, a=일: 신호(x) and (x.get(f"임_{a}") or 0) == 0)

    print("\n  ── C **뉴스** ──")
    print(머2)
    for 라, lo, hi in (("5일 기사 0건", -1, 1), ("1~3건", 1, 4),
                       ("4~10건", 4, 11), ("11건 이상", 11, 9e9)):
        세기(f"+ {라}",
             lambda x, a=lo, b=hi: (신호(x) and x.get("뉴_5") is not None
                                    and a < x["뉴_5"] < b))
    세기("+ **평소보다 2배 넘게** 기사",
         lambda x: 신호(x) and (x.get("뉴_많음") or 0) >= 2.0)
    세기("+ 평소보다 적다", lambda x: 신호(x) and 0 < (x.get("뉴_많음") or 9) < 0.5)

    print("\n  ── D **뉴스↔공시 겹침** ──")
    print(머2)
    세기("+ 그날 공시 있음", lambda x: 신호(x) and x.get("공시있나") == 1.0)
    세기("+ 그날 공시 없음", lambda x: 신호(x) and x.get("공시있나") == 0.0)
    세기("+ **공시도 뉴스도** 있음", lambda x: 신호(x) and x.get("뉴스도공시도") == 1.0)

    print("\n  ── E **거래대금 문턱** ──")
    print(머2)
    for 문 in (0.0, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0):
        세기(f"거래대금 {문}억 이상",
             lambda x, a=문: (재무통과(x) and 500 <= x["시총억"] < 2000
                             and x["대금억"] >= a
                             and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0))

    print("\n  ── F **영업비용** (= 100 − 영업이익률) ──")
    print(머2)
    for 라, lo, hi in (("80% 미만 (남는 장사)", -9e9, 80), ("80~90%", 80, 90),
                       ("90~95%", 90, 95), ("95~100%", 95, 100),
                       ("100% 넘음 (영업적자)", 100, 9e9)):
        세기(f"영업비용 {라}",
             lambda x, a=lo, b=hi: (신호(x) and x.get("영업비용") is not None
                                    and a <= x["영업비용"] < b))

    print("\n  ── G **같은 날 겹침** ──")
    print(머2)
    for 라, lo, hi in (("1개뿐", 0, 2), ("2~4개", 2, 5),
                       ("5~9개", 5, 10), ("10개 이상", 10, 9e9)):
        세기(f"그날 후보 {라}",
             lambda x, a=lo, b=hi: 신호(x) and a <= x.get("그날후보수", 0) < b)
    for 라, lo, hi in (("같은 업종 1개", 0, 2), ("2~3개", 2, 4),
                       ("4개 이상", 4, 9e9)):
        세기(f"{라}",
             lambda x, a=lo, b=hi: 신호(x) and a <= x.get("같은업종수", 0) < b)

    print("\n" + "=" * 122)
    print("  읽는 법")
    print("    - **덮는 범위**를 먼저 본다. 몇 % 안 덮으면 그 재료는 쓸 수 없다")
    print("    - 컨센서스는 2021~23이 비어 있다 — 그 기간 결과는 못 믿는다")
    print("    - 지금 규칙보다 3%p 넘게 좋으면 **4관문(165차)** 으로 넘긴다")
    print("    - 미결제약정은 뺐다 — 주식선물이 210종목(대형주)뿐이라 안 겹친다")
    print("=" * 122)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      # ⚠ 다른 값으로 다시 돌릴 때 결과를 덮어쓰지 않는다
                      os.environ.get("LAB_OUT") or "2026-09-08_168차_남은재료.txt")

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
