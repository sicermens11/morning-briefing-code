#!/usr/bin/env python3
r"""
gate5_lab.py — **165차 · 4관문을 「이길 확률」 잣대로** (2026-09-08 신설)

## 왜 새로 짜나
```
지금까지 4관문(111·147차)은 **자본 시뮬**로 판정했다.
그런데 자본 시뮬은 「돈 ÷ 낙폭」이라 **적게 살수록 점수가 오른다** —
매수 기회를 깎는 방향이다. 사용자 목표(매수 타이밍 포착)와 어긋난다
```
⇒ 관문의 **뼈대는 그대로 두고 잣대만 바꾼다**

## 관문 다섯 (기존과 같은 뼈대)
```
A 앞뒤 분할     기간을 셋으로 갈라 **모두 같은 방향**인가
B 해마다        11개 해에서 **몇 승 몇 패**인가
C ⭐ 무작위 대조  같은 개수를 아무렇게나 골라 200번 —
                그 분포에서 **상위 25%** 안에 드는가
D 오차          매수가에 ±0.3 / 0.5 / 1.0%p 오차를 줘도 버티나
E 문턱 자리      문턱을 조금 옮겨도 버티나 (한 자리에서만 좋으면 과적합)
```

## 도전자 — 157·155차에서 나온 것들
```
① 크기 해제          시총 500~2,000억 조건을 뺀다   (155차: 2배 늘고 1.1%p 손해)
② 볼린저 창 60일     지금은 20일                    (157차: 52.8% -> 65.2%)
③ 볼린저 창 120일    "                              (157차: 52.8% -> 70.5%)
④ 두 창 함께        낙폭 20일 -10% **그리고** 120일 -20%  (157차: 66.3% · +7.70%)
⑤ ③+④ 같이
```
⚠️ 157차는 **상장폐지를 안 센 코드**로 돌았다. 여기서는 **-50%로 센다** —
   그래서 157차보다 숫자가 낮게 나오는 게 정상이다

쓰는 법:
    python scripts\gate5_lab.py
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
            # ── 165차: 창을 여러 개 붙인다 (157차와 같은 계산) ──
            창값 = {}
            for w in (5, 10, 20, 40, 60, 120, 250):
                if kk >= w and sq[kk - w] > 0:
                    창값[f"낙{w}"] = (c1 / sq[kk - w] - 1) * 100
            for w in (5, 10, 20, 40, 60, 120):
                if kk >= w:
                    m2 = st.mean(sq[kk - w + 1:kk + 1])
                    d2 = st.pstdev(sq[kk - w + 1:kk + 1]) or 1e-9
                    창값[f"볼{w}"] = (c1 - m2) / (2 * d2)
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
                "해": d1[:4], **창값,
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

    import random as _rnd

    def 앞수익(x, n, 오차=0.0, 씨=0):
        """n일 뒤 수익. 오차를 주면 **산 값이 그만큼 흔들린다**"""
        i2 = x["인"]
        j = i2 + n
        if j >= len(날):
            return None
        a = 주가[날[i2]].get(x["code"])
        if not a or a[0] <= 0:
            return None
        산값 = x["매수"]
        if 오차:
            r = _rnd.Random(hash((x["인"], x["code"], 씨)) & 0xFFFFFFFF)
            산값 *= (1 + r.uniform(-오차, 오차) / 100)
        b = 주가[날[j]].get(x["code"])
        if not b:
            return (O.폐지손실 - _비용) if x["code"] in _사라짐 else None
        # ⚠️ 매수는 시가(x["매수"]), 매도는 종가 — 둘 다 수정주가 기준으로 맞춘다
        비율 = a[0] / 산값 if 산값 > 0 else None
        if not 비율:
            return None
        return (b[0] * 비율 / a[0] - 1) * 100 - _비용

    # ⭐ 169차 F절: 「그 섹터 기준으로 몇 시그마 빠졌나」
    #    문턱을 고르지 않으니 과적합이 안 생긴다
    _섹칸 = {}
    for x in 사건:
        if x.get("섹터"):
            _섹칸.setdefault(x["섹터"], []).append(x["낙폭20"])
    _통계 = {}
    for s2, v2 in _섹칸.items():
        if len(v2) < 200:
            continue
        m2 = sum(v2) / len(v2)
        sd2 = (sum((z - m2) ** 2 for z in v2) / len(v2)) ** 0.5 or 1e-9
        _통계[s2] = (m2, sd2)
    for x in 사건:
        st2 = _통계.get(x.get("섹터"))
        if st2:
            x["섹시그마"] = (x["낙폭20"] - st2[0]) / st2[1]

    print("  기준 수익률 붙이는 중...", flush=True)
    for x in 사건:
        x["_20"] = 앞수익(x, 20)
        x["_40"] = 앞수익(x, 40)

    해수 = 10.4

    # ══ 도전자들 ══
    def 재무통과(x):
        return x.get("재통과") == 1.0

    def 대금통과(x):
        return x["대금억"] >= 1.0

    def 크기통과(x):
        return 500 <= x["시총억"] < 2000

    def 지금(x):
        return (재무통과(x) and 대금통과(x) and 크기통과(x)
                and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0)

    def 있(x, k):
        return x.get(k) is not None

    도전자 = [
        ("지금 규칙", 지금),
        # ⭐ 158차가 가리키는 것은 **「완전 해제」가 아니라 「하한 300억」**이다.
        #    300~500억: 57.7% · +5.03% (지금 자리보다 난다)
        #    300억 미만: 폐지를 17.68% 밟고 -2.19%p 깎인다
        ("① 하한 **300억**으로 낮춤",
         lambda x: (재무통과(x) and 대금통과(x)
                    and 300 <= x["시총억"] < 2000
                    and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0)),
        ("①-2 하한 없음 (견줌)",
         lambda x: (재무통과(x) and 대금통과(x)
                    and x["시총억"] < 2000
                    and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0)),
        ("② 볼린저 **60일** -1.5σ",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and 있(x, "볼60") and x["볼60"] <= -1.5)),
        ("③ 볼린저 **120일** -1.5σ",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and 있(x, "볼120") and x["볼120"] <= -1.5)),
        ("④ 두 창 함께 (20일-10% + 120일-20%)",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.0
                    and x["낙폭20"] <= -10.0
                    and 있(x, "낙120") and x["낙120"] <= -20.0)),
        # ⭐⭐ **2026-09-09 새 도전자** — 161·163·169차에서 나왔다.
        #    셋 다 「시장이 빠진 날에 산다」는 **같은 이야기**일 수 있다
        ("⑥ 시장이 -10%↓ 빠진 날만 (161차)",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0
                    and 있(x, "시장낙폭") and x["시장낙폭"] <= -10.0)),
        ("⑦ 시장보다 덜 빠졌다 (163차 상대강도↑)",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["낙폭20"] <= -10.0
                    and 있(x, "상대강도") and x["상대강도"] >= 5.0)),
        # ⚠⚠ **섹터를 넓게 다시 재본다** (2026-09-09 사용자 지적).
        #    전에는 **-1.5σ 하나만** 관문에 넣고 「섹터는 안 된다」고 했다.
        #    169차에서는 -2.0σ(66.5%) · -2.5σ 가 더 좋았는데 안 넣었다
        ("⑧ 섹터 기준 **-1.0σ**",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x.get("섹시그마") is not None
                    and x["섹시그마"] <= -1.0)),
        ("⑧-2 섹터 기준 **-1.5σ**",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x.get("섹시그마") is not None
                    and x["섹시그마"] <= -1.5)),
        ("⑧-3 섹터 기준 **-2.0σ**",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x.get("섹시그마") is not None
                    and x["섹시그마"] <= -2.0)),
        ("⑧-4 섹터 기준 **-2.5σ**",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x.get("섹시그마") is not None
                    and x["섹시그마"] <= -2.5)),
        ("⑧-5 섹터 -1.5σ **+ 볼린저**",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.0
                    and x.get("섹시그마") is not None
                    and x["섹시그마"] <= -1.5)),
        ("⑧-6 섹터 -2.0σ **+ 볼린저**",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.0
                    and x.get("섹시그마") is not None
                    and x["섹시그마"] <= -2.0)),
        # ⭐ 시장 문턱을 **-5%로 풀면** (사용자: 어떤 해는 0번 사면 안 된다)
        ("⑩ 시장이 **-5%↓** 빠진 날만",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0
                    and 있(x, "시장낙폭") and x["시장낙폭"] <= -5.0)),
        ("⑪ 시장이 -3%↓ 빠진 날만",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0
                    and 있(x, "시장낙폭") and x["시장낙폭"] <= -3.0)),
        ("⑤ ③ + ④ 같이",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and 있(x, "볼120") and x["볼120"] <= -1.5
                    and x["낙폭20"] <= -10.0
                    and 있(x, "낙120") and x["낙120"] <= -20.0)),
    ]

    def 점수(칸, 기="_20"):
        v = [x[기] for x in 칸 if x.get(기) is not None]
        if len(v) < 60:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(칸))

    def 줄(라, 점, 기준=None):
        if 점 is None:
            print(f"  {라:<40}      표본 부족")
            return
        이, 평, n = 점
        꼬 = ""
        if 기준:
            꼬 = f"{이-기준[0]:>+8.1f}p{평-기준[1]:>+8.2f}"
        print(f"  {라:<40}{n:>8,}{n/해수:>7.0f}{이:>8.1f}%{평:>+8.2f}{꼬}")

    머2 = (f"  {'설정':<40}{'건수':>8}{'1년에':>7}"
           f"{'20일 이김':>9}{'평균':>8}{'지금대비':>9}{'':>8}")

    print("\n" + "=" * 108)
    print("  165차 · **4관문을 「이길 확률」 잣대로**")
    print(f"  후보 {len(사건):,}건 · 바탕(아무 종목·아무 날) 20일 44.7% · +0.65%")
    print(f"  ⚠️ 상장폐지는 {O.폐지손실:.0f}% 손실로 센다")
    print("=" * 108)

    통과표 = {}

    # ── A 앞뒤 분할 ──
    print("\n" + "=" * 108)
    print("  A 앞뒤 분할 — 기간을 갈라도 **같은 방향**인가")
    print("=" * 108)
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"), ("2025·26 뺀 것", "2016", "2024"))
    for 라, fn in 도전자:
        print(f"\n   [{라}]")
        print(머2)
        방향 = []
        for 구라, a, b in 구간:
            칸 = [x for x in 사건 if fn(x) and a <= x["해"] <= b]
            기 = [x for x in 사건 if 지금(x) and a <= x["해"] <= b]
            점, 기점 = 점수(칸), 점수(기)
            줄(f"{구라}", 점, 기점)
            if 점 and 기점:
                방향.append(점[0] - 기점[0])
        if 라 != "지금 규칙" and 방향:
            좋 = all(v > 0 for v in 방향)
            통과표.setdefault(라, {})["A"] = 좋
            # ⚠️⚠️ **기회 수를 같이 찍는다** (2026-09-09).
            #    전에는 이김만 봤다. 그래서 190차에서 기회가 **6%**로 줄어든 것이
            #    「통과」로 찍혔다 (지금 규칙 1년 1,842개 -> 106개).
            #    사용자 원문: 「매도 타이밍과 자산 보유 현황도 중요하지만
            #    **그것도 때문에 상승 기회를 놓쳐서는 안돼**」
            #    ⚠️ 자동으로 떨어뜨리지는 않는다 — 기회와 승률은 교환이고
            #       어디까지 받아들일지는 사람이 정한다. 다만 **늘 보이게** 한다
            기회비 = None
            try:
                _기 = 점수([x for x in 사건 if 지금(x)])
                _도 = 점수([x for x in 사건 if fn(x)])
                if _기 and _도 and _기[2]:
                    기회비 = _도[2] / _기[2] * 100
            except Exception:  # noqa: BLE001
                pass
            꼬 = ""
            if 기회비 is not None:
                꼬 = f"  · **기회 {기회비:.0f}%**"
                if 기회비 < 50:
                    꼬 += "  ⚠️ **절반 밑이다 — 기회를 깎는다**"
            print(f"     ⇒ 네 구간 **{'전부 낫다 ✅' if 좋 else '엇갈린다 ❌'}**{꼬}")

    # ── B 해마다 ──
    print("\n" + "=" * 108)
    print("  B 해마다 — 몇 승 몇 패인가")
    print("=" * 108)
    해들 = sorted({x["해"] for x in 사건})
    for 라, fn in 도전자[1:]:
        이김, 짐, 무 = 0, 0, 0
        칸별 = []
        for y in 해들:
            점 = 점수([x for x in 사건 if fn(x) and x["해"] == y])
            기점 = 점수([x for x in 사건 if 지금(x) and x["해"] == y])
            if not 점 or not 기점:
                continue
            차 = 점[0] - 기점[0]
            칸별.append((y, 기점[0], 점[0], 차))
            if 차 > 0.5:
                이김 += 1
            elif 차 < -0.5:
                짐 += 1
            else:
                무 += 1
        print(f"\n   [{라}]  {'해':<8}{'지금':>10}{'도전':>10}{'차이':>10}")
        for y, a, b, c in 칸별:
            print(f"            {y:<8}{a:>9.1f}%{b:>9.1f}%{c:>+9.1f}p")
        print(f"     ⇒ **{이김}승 {짐}패 {무}무**")
        통과표.setdefault(라, {})["B"] = 이김 > 짐

    # ── C 무작위 대조 ──
    print("\n" + "=" * 108)
    print("  C ⭐ 무작위 대조 — 같은 개수를 **아무렇게나** 골라 200번")
    print("     (조합을 많이 훑으면 운으로 좋아 보이는 게 나온다. 그걸 걸러낸다)")
    print("=" * 108)
    바탕칸 = [x for x in 사건 if x.get("_20") is not None]
    for 라, fn in 도전자[1:]:
        칸 = [x for x in 사건 if fn(x) and x.get("_20") is not None]
        if len(칸) < 100:
            print(f"  {라:<40} 표본 부족")
            continue
        나 = sum(1 for x in 칸 if x["_20"] > 0) / len(칸) * 100
        분포 = []
        for s in range(200):
            r = _rnd.Random(9000 + s)
            뽑 = r.sample(바탕칸, len(칸))
            분포.append(sum(1 for x in 뽑 if x["_20"] > 0) / len(뽑) * 100)
        분포.sort()
        위 = sum(1 for v in 분포 if v < 나)
        상위 = (1 - 위 / len(분포)) * 100
        든다 = 상위 <= 25
        print(f"  {라:<40}{len(칸):>8,}건  나 {나:.1f}%  "
              f"무작위 중앙 {분포[100]:.1f}% · 가장 좋음 {분포[-1]:.1f}%  "
              f"→ 상위 {상위:.0f}%  {'✅' if 든다 else '❌'}")
        통과표.setdefault(라, {})["C"] = 든다

    # ── D 오차 ──
    print("\n" + "=" * 108)
    print("  D 오차 — 산 값이 흔들려도 버티나")
    print("=" * 108)
    print(머2)
    for 오차 in (0.0, 0.3, 0.5, 1.0):
        print(f"\n   [오차 ±{오차}%p]")
        기칸 = [x for x in 사건 if 지금(x)]
        기점 = 점수([dict(x, _20=앞수익(x, 20, 오차, 1)) for x in 기칸])
        줄("지금 규칙", 기점)
        for 라, fn in 도전자[1:]:
            칸 = [dict(x, _20=앞수익(x, 20, 오차, 1)) for x in 사건 if fn(x)]
            줄(라, 점수(칸), 기점)

    # ── E 문턱 자리 ──
    print("\n" + "=" * 108)
    print("  E 문턱 자리 — 조금 옮겨도 버티나 (한 자리에서만 좋으면 과적합)")
    print("=" * 108)
    print(머2)
    print("\n   [볼린저 120일 문턱]")
    for 문 in (-1.0, -1.25, -1.5, -1.75, -2.0):
        줄(f"볼린저 120일 {문}σ",
           점수([x for x in 사건
                 if 재무통과(x) and 대금통과(x) and 크기통과(x)
                 and 있(x, "볼120") and x["볼120"] <= 문]))
    print("\n   [낙폭 120일 문턱 (20일 -10% 와 함께)]")
    for 문 in (-10, -15, -20, -25, -30):
        줄(f"낙폭 120일 {문}%",
           점수([x for x in 사건
                 if 재무통과(x) and 대금통과(x) and 크기통과(x)
                 and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0
                 and 있(x, "낙120") and x["낙120"] <= 문]))
    print("\n   [크기 해제 — 시총 구간별]")
    for 라, lo, hi in (("100~300억", 100, 300), ("300~500억", 300, 500),
                       ("500~2,000억", 500, 2000),
                       ("2,000~1조", 2000, 10000), ("1조 이상", 10000, 9e9)):
        줄(f"시총 {라}",
           점수([x for x in 사건
                 if 재무통과(x) and 대금통과(x)
                 and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0
                 and lo <= x["시총억"] < hi]))

    # ── 판정 ──
    print("\n" + "=" * 108)
    print("  판정 — A·B·C 를 다 지나야 **4관문 통과**다")
    print("=" * 108)
    for 라, _ in 도전자[1:]:
        v = 통과표.get(라, {})
        다 = all(v.get(k) for k in ("A", "B", "C"))
        print(f"  {라:<40}"
              f"A {'✅' if v.get('A') else '❌'}  "
              f"B {'✅' if v.get('B') else '❌'}  "
              f"C {'✅' if v.get('C') else '❌'}   "
              f"⇒ **{'통과' if 다 else '탈락'}**")
    print("\n  ⚠️ 통과해도 바로 안 바꾼다. D·E 를 사람이 읽고 정한다")
    print("=" * 108)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      # ⚠ 다른 값으로 다시 돌릴 때 결과를 덮어쓰지 않는다
                      os.environ.get("LAB_OUT") or "2026-09-08_165차_4관문_이길확률.txt")

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
