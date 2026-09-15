#!/usr/bin/env python3
r"""
combo4_lab.py — **163차 · 재료 단독과 새 조합을 처음부터** (2026-09-08 신설)

## 사용자 질문
```
「단독 재료랑 새로운 조합 테스트도 예정되어 있어?
  **기존 규칙에 얹는 거 말고?**」
```
맞는 지적이다. 지금까지 한 것은 거의 다 **「우리 규칙 + 무엇」** 이었다.
144차가 단독 재료를 재긴 했지만 **자본 시뮬로 판정**해 잣대가 틀렸다

## 이 시험이 다른 점
```
우리 규칙을 **깔지 않는다.** 재무·시총·거래대금·볼린저·낙폭 전부 안 건다
재료 28가지를 **오분위**로 잘라 놓고
  A 하나씩          어느 재료가 혼자 일을 하나
  B 둘씩 (전수)      378쌍을 다 재본다
  C 셋씩            좋았던 쌍에 세 번째를 붙인다
```

## 잣대 — 155차와 같다
```
① 1년에 몇 개  ② 20일 뒤 **오른 비율**  ③ 평균 몇 %
바탕(아무 종목·아무 날) 20일 = **44.7% 오름 · +0.65%**
```
⚠️ 상장폐지는 **-50% 손실**로 센다 (2026-09-08 고침 반영)

## ⚠️ 조심할 것 — 조합을 다 훑으면 **우연히 좋은 게 나온다**
```
378쌍을 재면 그중 몇 개는 **운으로** 좋아 보인다.
그래서 상위는 반드시 **4관문**으로 넘긴다 —
특히 ③ 무작위 대조(200~300개 중 상위 25%)가 이걸 걸러낸다
```

쓰는 법:
    python scripts\combo4_lab.py
"""
from array import array as _array   # ⭐ 자리들을 4바이트로
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402
import newmat  # noqa: E402   ⭐ 2026-09-14 — 안 써본 재료 넷

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
    # ⭐ **기술지표 다섯** — 종가만으로 계산 (2026-09-15 · 사용자 「RSI MACD 는 반영됐어?」)
    #    9/2 combo3 에서 RSI≤30 을 옛 기준선에 AND 로만 봤고(68.0% · 16/16) 지금 판엔 없었다.
    #    MACD 는 한 번도 없었다. 종목마다 한 번 계산해 array('f') 에 둔다 — 신호일 kk 까지만 본다
    print("  기술지표(RSI·MACD·스토캐스틱) 계산 중...", flush=True)
    _TA = {"RSI14": {}, "RSI변화5": {}, "MACD히스토": {}, "MACD골든5": {}, "스토K14": {}}
    _nan = float("nan")
    for _c, _sq in 종계.items():
        _n = len(_sq)
        _rsi = _array("f", [_nan] * _n)
        _hist = _array("f", [_nan] * _n)
        _gold = _array("f", [0.0] * _n)
        _sto = _array("f", [_nan] * _n)
        _dr = _array("f", [_nan] * _n)
        _au = _ad = None
        _e12 = _e26 = _sig = None
        _prev_diff = None
        _cross = []                    # 골든크로스 난 자리들
        for k in range(_n):
            c = _sq[k]
            if k >= 1 and _sq[k - 1] > 0:
                ch = c - _sq[k - 1]
                g, l = (ch if ch > 0 else 0.0), (-ch if ch < 0 else 0.0)
                if _au is None:
                    _au, _ad = g, l
                else:
                    _au += (g - _au) / 14.0
                    _ad += (l - _ad) / 14.0
                if k >= 14:
                    _rsi[k] = 100.0 if _ad == 0 else 100.0 - 100.0 / (1.0 + _au / _ad)
            # MACD
            if _e12 is None:
                _e12 = _e26 = c
            else:
                _e12 += (c - _e12) * (2.0 / 13.0)
                _e26 += (c - _e26) * (2.0 / 27.0)
            _m = _e12 - _e26
            if _sig is None:
                _sig = _m
            else:
                _sig += (_m - _sig) * (2.0 / 10.0)
            _diff = _m - _sig
            if k >= 33 and c > 0:
                _hist[k] = _diff / c * 100.0
                if _prev_diff is not None and _prev_diff <= 0 < _diff:
                    _cross.append(k)
                while _cross and _cross[0] < k - 4:
                    _cross.pop(0)
                _gold[k] = 1.0 if _cross else 0.0
            _prev_diff = _diff
            # 스토캐스틱 (종가로)
            if k >= 13:
                _w = _sq[k - 13:k + 1]
                _hi, _lo = max(_w), min(_w)
                _sto[k] = ((c - _lo) / (_hi - _lo) * 100.0) if _hi > _lo else 50.0
            if k >= 19 and _rsi[k] == _rsi[k] and _rsi[k - 5] == _rsi[k - 5]:
                _dr[k] = _rsi[k] - _rsi[k - 5]
        _TA["RSI14"][_c] = _rsi
        _TA["RSI변화5"][_c] = _dr
        _TA["MACD히스토"][_c] = _hist
        _TA["MACD골든5"][_c] = _gold
        _TA["스토K14"][_c] = _sto
    print(f"    {len(종계):,}종목 · 다섯 지표", flush=True)

    def _ta(이름, code, kk):
        a = _TA[이름].get(code)
        if a is None or kk >= len(a):
            return None
        v = a[kk]
        return None if v != v else float(v)

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
                "RSI14": _ta("RSI14", code, kk), "RSI변화5": _ta("RSI변화5", code, kk),
                "MACD히스토": _ta("MACD히스토", code, kk), "MACD골든5": _ta("MACD골든5", code, kk),
                "스토K14": _ta("스토K14", code, kk),
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
            칸 = sorted(칸, key=lambda z: z["낙폭20"])[:c.get("후보수", _후보수)]
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

    기간들 = (5, 20, 40)
    print("  기간별 수익률 붙이는 중...", flush=True)
    for x in 사건:
        for n in 기간들:
            x[f"_{n}"] = 앞수익(x, n)
    # ⚠️ **박아 두면 안 된다** — `--최근N년` 으로 기간을 자를 때 안 따라온다.
    #    2026-09-15 새벽: S2판(1년)이 1,979건을 「1년에 **190**」이라 찍었다.
    #    10.4 로 나눴기 때문이다 — 실제로는 1,979 다. **10.4배 작게** 나왔다.
    #    「1년에 몇 개」는 사용자 1순위 잣대(**기회**)라 그냥 둘 수 없다.
    #    아래 `_최근년` 을 읽은 뒤 다시 계산한다 (여기 값은 자르기 전 기본)
    해수 = 10.4

    # ⭐⭐⭐ **최근 1년만** (2026-09-14) — 뉴스는 약 1년치뿐이라 10.4년 사건에
    #    붙이면 오분위가 통째로 건너뛴다. 이 선택지에서만 뉴스가 재진다
    # ⭐ --최근N년 (2026-09-14 밤 일반화). dart-snap 은 2024~2025 두 해뿐이라
    #    10.4년 사건에 붙이면 19% 로 오분위(30% 문턱)가 건너뛴다 — 2년 판이 필요하다
    # ⚠️⚠️ **`_a[3:-1]` 이 범인이었다** (2026-09-15 새벽).
    #    `--최근` 은 `-`,`-`,`최`,`근` **네 글자**다. 셋으로 잘라 「근1」이 되고
    #    `int("근1")` 이 터지는데 그걸 `pass` 로 삼켜 `_최근년 = 0` 으로 남았다.
    #    ⇒ **S판(1년)도 U판(2년)도 전체 10.4년으로 돌았다.** 출력에
    #    「최근 N년만」 줄이 아예 없는 게 증거였다
    #    ⇒ 글자 수를 박지 않고 `len(_앞)` 으로 자른다.
    #      그리고 **조용히 넘기지 않는다** — `pass` 가 이 버그를 숨겼다
    _최근년 = 0
    _앞 = "--최근"
    for _a in sys.argv:
        if _a.startswith(_앞) and _a.endswith("년"):
            try:
                _최근년 = int(_a[len(_앞):-1])
            except ValueError:
                raise SystemExit(
                    f"\n⚠️ `{_a}` 에서 햇수를 못 읽었다 — 판을 안 돌린다."
                    f"\n   `--최근1년` `--최근2년` 처럼 써라\n")
    if _최근년 and 날:
        _자른 = len(날) - 245 * _최근년
        _전 = len(사건)
        사건 = [x for x in 사건 if x["인"] >= _자른]
        # ⭐ **해수도 같이 줄인다** (2026-09-15 새벽). 안 그러면 「1년에 몇 개」가
        #    10.4 로 나뉘어 **10.4배 작게** 나온다 — 기회를 못 알아본다
        해수 = float(_최근년)
        print(f"  ⭐ **최근 {_최근년}년만** — 사건 {_전:,} → {len(사건):,}건 "
              f"({날[max(0, _자른)]} ~ {날[-1]}) · 해수 10.4 → {해수:g}", flush=True)

    # ⭐⭐⭐ **안 써본 재료 넷** (2026-09-14 · field_audit 에서 「한 번도 안 씀」).
    #    ⭐⭐ 2026-09-14 밤에 둘을 더했다 — **분기 재무(11.5년)** 와
    #       **단일종목선물(16년)**. 둘 다 자료는 처음부터 있었는데
    #       `docs/자료재고.md` 가 하위 폴더를 합쳐 세는 바람에 **눈에 안 띄었다**
    #    사용자: 「기존 규칙에 얹는 게 아니라 **단독 재료로서의 효과**와
    #             다른 재료와의 **다양한 조합**일 때 효과를 측정해야 해」
    #    ⇒ 이름만 늘리면 아래 A(하나씩)·B(둘씩 전수)·C(셋씩)가 그대로 재 준다
    print("\n  ⭐ 안 써본 재료 붙이는 중 (공시시각 · 임원 · 대주주 · 뉴스 · 컨센서스 ·"
          " 증자 · ETF · 거시 · 배당 · ⭐분기재무 · ⭐단일종목선물)...", flush=True)
    _새재료 = newmat.붙이기(사건, 날, 뉴스포함=True)
    print(f"    붙은 재료 {len(_새재료)}가지: {', '.join(_새재료)}", flush=True)

    # ══ 재료 목록 ══
    재료들 = ("볼린저", "낙폭20", "낙폭60", "60일선대비", "갭",
              "RSI14", "RSI변화5", "MACD히스토", "MACD골든5", "스토K14",     # ⭐ 기술지표 (2026-09-15)
              "시총억", "대금억", "거래량", "회전율",
              "잉여금", "부채", "ROE", "영업이익률", "순이익률", "유동비율",
              "시장낙폭", "상대강도", "시장변동성", "소형우위",
              "섹터낙폭", "섹터대비",
              "외인1", "외인5", "외인20", "기관5", "기관20", "개인5",
              "지분율", "지분20변화") + tuple(_새재료)

    print("\n" + "=" * 122)
    print("  163차 · 재료 **단독**과 **새 조합** — 우리 규칙을 안 깔고 처음부터")
    print(f"  후보 {len(사건):,}건 · 바탕(아무 종목·아무 날) 20일 44.7% · +0.65%")
    print("  ⚠️ 상장폐지는 -50% 손실로 센다")
    print("=" * 122)

    # ══ 오분위 자르기 ══
    print("\n  재료를 오분위로 자르는 중...", flush=True)
    조건 = {}          # 이름 -> 그 조건을 만족하는 사건 자리들(set)
    쓸재료 = []
    for 재 in 재료들:
        v = [x.get(재) for x in 사건]
        가 = sorted(z for z in v if z is not None)
        if len(가) < len(사건) * 0.3:
            print(f"    {재:<12} 값이 {len(가):,}개뿐 — 건너뜀")
            continue
        낮 = 가[len(가) // 5]
        높 = 가[len(가) * 4 // 5]
        # ⚠️⚠️ **값이 한 곳에 몰린 재료**를 막는다 (2026-09-14 밤).
        #    흑자전환·수주건수·유상증자처럼 **0 이 대부분**인 재료는
        #    20% 자리도 0, 80% 자리도 0 이라 아래·위가 **둘 다 「전부」**가 된다.
        #    아무것도 안 가르면서 조건 목록에 들어가 조합을 수천 개 부풀리고,
        #    정작 뜻 있는 갈래(**흑자전환 = 1**)는 사라진다
        #    ⇒ 문턱이 겹치면 「그 값보다 큰가/작은가」로 가른다
        _몰렸나 = (낮 == 높)
        # ⭐⭐ **set → int 비트마스크** (2026-09-14 밤 · MemoryError 고침).
        #    조건 110개 × set(108만) = 7GB 였다. 비트마스크면 110 × 136KB = 15MB.
        #    담는 그릇만 바뀌고 **값은 하나도 안 바뀐다**
        # ⚠️⚠️ **`아래 |= 1 << i2` 를 쓰면 안 된다** (2026-09-14 밤 · 25GB 사고).
        #    파이썬 int 는 불변이라 그 한 줄이 **136KB 짜리 int 를 새로 만든다.**
        #    108만 번 돌면 가비지가 쌓여 **램이 25GB** 까지 치솟았다(여유 1.8GB).
        #    ⇒ `bytearray` 에 **제자리로** 비트를 세우고 마지막에 한 번만 int 로.
        _바이트 = (len(사건) + 7) // 8
        _아래b = bytearray(_바이트)
        _위b = bytearray(_바이트)
        _아래수 = _위수 = 0
        for i2, z in enumerate(v):
            if z is None:
                continue
            if (z < 낮) if _몰렸나 else (z <= 낮):
                _아래b[i2 >> 3] |= 1 << (i2 & 7)
                _아래수 += 1
            if (z > 높) if _몰렸나 else (z >= 높):
                _위b[i2 >> 3] |= 1 << (i2 & 7)
                _위수 += 1
        아래 = int.from_bytes(_아래b, "little")
        위 = int.from_bytes(_위b, "little")
        # ⚠️ 조건 하나가 사건의 **절반**을 넘으면 오분위가 아니다 — 안 쓴다
        _절반 = len(사건) // 2
        if 500 < _아래수 <= _절반:
            조건[f"{재}↓"] = 아래
        if 500 < _위수 <= _절반:
            조건[f"{재}↑"] = 위
        if _몰렸나:
            print(f"    {재:<12} 값이 한 곳에 몰렸다 — "
                  f"「{낮:g} 보다 큰가」로 가른다 (위 {_위수:,}건)")
        쓸재료.append(재)
    print(f"    쓸 재료 {len(쓸재료)}가지 · 조건 {len(조건)}개"
          f" (각각 아래 20% / 위 20%)", flush=True)

    수익 = {기: [x.get(f"_{기}") for x in 사건] for 기 in 기간들}

    # ⭐ 비트마스크에서 자리를 뽑는 표 (바이트 하나에 8자리)
    _비트표 = [[i for i in range(8) if (b >> i) & 1] for b in range(256)]
    _자리수 = len(사건)

    def _자리뽑기(m):
        """비트마스크 → 사건 자리들 (`array("i")`)

        ⚠️⚠️ **list 로 주면 안 된다** (2026-09-15 새벽 · S판 MemoryError).
           109만 자리를 파이썬 list[int] 로 담으면 **~40MB** 다.
           쌍 5,565개를 훑으며 매번 만들고 버리니 램이 버티지 못했다.
           `array("i")` 는 4바이트씩 — **4.4MB** 로 1/9 이다
        """
        out = _array("i")
        bs = m.to_bytes((_자리수 + 7) // 8, "little")
        for bi, b in enumerate(bs):
            if b:
                base = bi * 8
                out.extend(base + i for i in _비트표[b])
        return out

    def 재기(m):
        """(건수, {기간: (이김%, 평균)}) — `m` 은 **비트마스크**다

        ⚠️ 중간 리스트 `v` 를 **안 만든다** (2026-09-15 새벽).
           기간 3개 x 109만 짜리 리스트를 쌍마다 만들고 버렸다.
           훑으면서 바로 더한다 — **값은 하나도 안 바뀐다**
        """
        자리들 = _자리뽑기(m) if isinstance(m, int) else m
        n = len(자리들)
        낸 = {}
        for 기 in 기간들:
            arr = 수익[기]
            센것 = 이긴것 = 0
            합 = 0.0
            for i2 in 자리들:
                z = arr[i2]
                if z is None:
                    continue
                센것 += 1
                합 += z
                if z > 0:
                    이긴것 += 1
            if 센것 < 80:
                낸[기] = None
                continue
            낸[기] = (이긴것 / 센것 * 100, 합 / 센것)
        return n, 낸

    def 줄내기(라, n, 낸):
        줄 = f"  {라:<44}{n:>9,}{n/해수:>7.0f}"
        for 기 in 기간들:
            if 낸.get(기) is None:
                줄 += f"{'-':>9}{'-':>8}"
            else:
                줄 += f"{낸[기][0]:>8.1f}%{낸[기][1]:>+8.2f}"
        return 줄

    머2 = (f"  {'설정':<44}{'건수':>9}{'1년에':>7}"
           f"{'5일 이김':>9}{'평균':>8}{'20일 이김':>10}{'평균':>8}"
           f"{'40일 이김':>10}{'평균':>8}")

    # ── A 하나씩 ──
    print("\n  ── A **재료 하나만** 쓰면 (아래 20% 또는 위 20%) ──")
    print(머2)
    단독 = []
    for 라, s in 조건.items():
        n, 낸 = 재기(s)
        if 낸.get(20):
            단독.append((낸[20][0], 라, n, 낸))
    단독.sort(reverse=True)
    for _, 라, n, 낸 in 단독:
        print(줄내기(라, n, 낸))

    # ── B 둘씩 (전수) ──
    이름들 = sorted(조건)
    print(f"\n  ── B **둘씩 조합** — {len(이름들)*(len(이름들)-1)//2:,}쌍 전수 ──")
    print("     (같은 재료의 ↑↓ 짝은 뺀다 — 서로 못 만난다)", flush=True)
    쌍 = []
    for a in range(len(이름들)):
        for b in range(a + 1, len(이름들)):
            라1, 라2 = 이름들[a], 이름들[b]
            if 라1[:-1] == 라2[:-1]:
                continue
            # ⭐ 조건이 **비트마스크**다 (2026-09-14 밤) — 개수는 bit_count()
            s = 조건[라1] & 조건[라2]
            if s.bit_count() < 500:
                continue
            n, 낸 = 재기(s)
            if 낸.get(20):
                # ⚠️ 마스크 `s` 를 담지 않는다 (2026-09-14 밤) — 통과한 쌍이 수천이면
                #    136KB × 수천 = 수백 MB 다. C절이 쓰는 상위 40개만 **다시 계산**한다
                쌍.append((낸[20][0], f"{라1} + {라2}", n, 낸, (라1, 라2)))
    쌍.sort(key=lambda z: -z[0])
    print(f"     쓸 만한 쌍 {len(쌍):,}개 · **위 30개**")
    print(머2)
    for _, 라, n, 낸, _s in 쌍[:30]:
        print(줄내기(라, n, 낸))
    print("\n     **아래 10개** (나쁜 쪽도 정보다 — 뒤집으면 쓸 수 있다)")
    print(머2)
    for _, 라, n, 낸, _s in 쌍[-10:]:
        print(줄내기(라, n, 낸))

    # ── B-2 ⭐⭐⭐ **앞뒤 분할** (4관문 ①) ─────────────────────
    #    이 파일 머리말이 스스로 「6,216쌍을 재면 몇 개는 **운으로** 좋아
    #    보인다. 상위는 반드시 4관문으로 넘긴다」라고 적어 두고도,
    #    정작 **거르는 장치가 하나도 없었다** (2026-09-15 새벽에 알았다).
    #    4관문은 gate7_lab 몫이라 손으로 옮겨 적어야 했고 그래서 안 넘어갔다.
    #    ⇒ 가장 센 것 하나(앞뒤 분할)를 **여기서 바로** 잰다
    #
    #    ⚠️ 사건은 날 순서로 쌓이므로 **자리 번호가 곧 시간순**이다.
    #       앞 절반 마스크는 `(1 << 반) - 1` 한 줄이면 된다
    #    ⚠️ 바탕도 **앞뒤 따로** 잰다 — 시장이 좋았던 쪽과 나빴던 쪽을
    #       같은 잣대로 보면 안 된다
    print("\n  ── B-2 ⭐⭐⭐ **앞뒤 분할** — 위 200쌍이 앞에서도 뒤에서도 되나 ──",
          flush=True)
    _반 = len(사건) // 2
    _앞마 = (1 << _반) - 1
    _뒤마 = ((1 << len(사건)) - 1) - _앞마
    _앞끝 = 날[사건[_반 - 1]["인"]] if _반 else "?"
    _, _바앞 = 재기(_앞마)
    _, _바뒤 = 재기(_뒤마)
    _b앞 = _바앞[20][0] if _바앞.get(20) else 0.0
    _b뒤 = _바뒤[20][0] if _바뒤.get(20) else 0.0
    print(f"     앞 {날[사건[0]['인']][:6]}~{_앞끝[:6]} 바탕 {_b앞:.1f}%"
          f"  ·  뒤 {_앞끝[:6]}~{날[사건[-1]['인']][:6]} 바탕 {_b뒤:.1f}%")
    print("     ⚠️ **앞뒤 둘 다** 그 기간 바탕을 +5%p 넘어야 ✅ 다."
          " 한쪽만이면 ⚠️ — 운으로 좋아 보인 것이다")
    print(f"\n  {'설정':<40}{'전체':>8}{'앞 건수':>9}{'앞 이김':>9}"
          f"{'뒤 건수':>9}{'뒤 이김':>9}  판정")
    _산것 = []
    for _전체, 라, n, 낸, _짝 in 쌍[:200]:      # ⭐ 30 -> 200 (2026-09-15 ㉦)
        s = 조건[_짝[0]] & 조건[_짝[1]]      # ⭐ 마스크는 여기서 다시 만든다
        n앞, 낸앞 = 재기(s & _앞마)
        n뒤, 낸뒤 = 재기(s & _뒤마)
        v앞 = 낸앞[20][0] if 낸앞.get(20) else None
        v뒤 = 낸뒤[20][0] if 낸뒤.get(20) else None
        if v앞 is None or v뒤 is None:
            판 = "— 한쪽 표본 80 미만"
        elif v앞 >= _b앞 + 5 and v뒤 >= _b뒤 + 5:
            판 = "✅"
            _산것.append(라)
        elif v앞 >= _b앞 + 5 or v뒤 >= _b뒤 + 5:
            판 = "⚠️ 한쪽만"
        else:
            판 = "❌"
        print(f"  {라:<40}{_전체:>7.1f}%{n앞:>9,}"
              f"{(f'{v앞:.1f}%' if v앞 is not None else '-'):>9}{n뒤:>9,}"
              f"{(f'{v뒤:.1f}%' if v뒤 is not None else '-'):>9}  {판}")
    print(f"\n     ⇒ 위 200쌍 중 **앞뒤 둘 다 지난 것 {len(_산것)}개**")
    if _산것:
        for 라 in _산것:
            print(f"        ⭐ {라}")
    else:
        print("        ⚠️ **하나도 없다** — 상위 30이 전부 한쪽 국면의 것이다")

    # ── B-3 ⭐⭐⭐ **종목 분할** (기간이 짧아 앞뒤를 못 쪼개는 재료용) ──
    #    사용자: 「**2027년 9월이면 너무 늦는데..**」 — 맞다.
    #    뉴스는 2025-09-03 ~ 2026-09-15 **정확히 1년**이라 앞뒤를 쪼개면
    #    「앞 0건」이 된다. 그러면 달력을 기다려야 하나? **아니다.**
    #
    #    ⭐ 시장 상승은 **이미 빠져 있다** — 이 판은 같은 날 같은 후보 안에서
    #       A vs B 를 견주므로 코스피 +58.6% 가 양쪽에 똑같이 들어간다.
    #       남는 걱정은 **과적합 하나**고, 그건 **쪼개기**로 잡는다.
    #
    #    기간 분할이 묻는 것은 「다른 **시기**에도 되나」
    #    종목 분할이 묻는 것은 「다른 **종목**에도 되나」 — 목적은 같다
    import zlib as _zl

    _씨수 = 10
    _코드들 = sorted({x["code"] for x in 사건})

    def _종목반반(씨):
        """종목을 **무작위 반반**으로 갈라 (A 마스크, B 마스크)

        ⚠️ `hash()` 는 프로세스마다 달라 되풀이가 안 된다 — `crc32` 를 쓴다
        ⚠️ 한 종목의 사건은 **통째로 한쪽에만** 간다. 안 그러면 새는 검증이다
        """
        _쪽 = {c: (_zl.crc32(f"{c}|{씨}".encode()) & 1) for c in _코드들}
        바 = bytearray((_자리수 + 7) // 8)
        for i2, x in enumerate(사건):
            if _쪽[x["code"]] == 0:
                바[i2 >> 3] |= 1 << (i2 & 7)
        A = int.from_bytes(바, "little")
        return A, ((1 << _자리수) - 1) - A

    # 볼 것 — **뉴스가 든 재료**와 뉴스가 든 상위 쌍
    # ⭐ 뉴스만 보던 것을 **앞 기간 표본이 80 미만인 재료 전부**로 (2026-09-15 21:30 · 사용자 지적).
    #    임원매수율·대주주변화(2024-09~)·ETF·분기재무 등 기간을 못 쪼개는 재료가 뉴스만이 아니었다
    def _앞표본(m):
        return bin(m & _앞마).count("1")
    _뉴단독 = [라 for 라 in sorted(조건) if _앞표본(조건[라]) < 80]
    _뉴쌍 = [(라, 짝) for _v, 라, _n, _낸, 짝 in 쌍[:200]
             if _앞표본(조건[짝[0]] & 조건[짝[1]]) < 80][:25]
    _볼것 = ([(라, (라,)) for 라 in _뉴단독] + _뉴쌍)
    print(f"     앞 기간 표본 80 미만 — 단독 {len(_뉴단독)}개 · 쌍 {len(_뉴쌍)}개 (뉴스만이 아니다)")

    print("\n  ── B-3 ⭐⭐⭐ **종목 분할** — 기간을 못 쪼개면 **종목**을 쪼갠다 ──",
          flush=True)
    print("     뉴스는 2025-09 ~ 2026-09 **1년뿐**이라 앞뒤 분할이 안 된다.")
    print("     그래서 종목 2,752개를 **무작위 반반** — 한쪽에서 되는 게")
    print("     **다른 쪽에서도** 되나. 씨를 **10번** 바꿔 되풀이한다.")
    print("  ⚠️ 시장 상승은 **이미 빠져 있다** (같은 날 안에서 견주므로).")
    print("     남는 걱정은 **과적합**이고 그건 쪼개기로 잡는다 — 달력이 아니다")
    print("  ⚠️ 한 종목의 사건은 **통째로 한쪽에만** 간다 (안 그러면 새는 검증)")
    print("  ⚠️ 못 잡는 것 하나 — 「**폭락장에서 뒤집히나**」는 약세장 자료가 있어야 안다")

    if not _볼것:
        print("     ⚠️ 뉴스가 든 재료가 없다 — 건너뛴다")
    else:
        # 씨마다 바탕이 다르다 — **그 반쪽의 바탕**과 견줘야 한다
        _반반들 = []
        for 씨 in range(_씨수):
            A, B = _종목반반(씨)
            _, _나A = 재기(A)
            _, _나B = 재기(B)
            _반반들.append((A, B,
                            _나A[20][0] if _나A.get(20) else None,
                            _나B[20][0] if _나B.get(20) else None))
            print(f"     씨 {씨}: A 바탕 "
                  f"{(f'{_반반들[-1][2]:.1f}%' if _반반들[-1][2] else '-')}"
                  f" · B 바탕 "
                  f"{(f'{_반반들[-1][3]:.1f}%' if _반반들[-1][3] else '-')}",
                  flush=True)

        print(f"\n  {'설정':<40}{'전체':>8}{'양쪽 다 +5%p':>14}"
              f"{'한쪽만':>9}{'둘 다 실패':>11}  판정")
        for 라, 짝 in _볼것:
            m = 조건[짝[0]]
            for _p in 짝[1:]:
                m &= 조건[_p]
            _n0, _낸0 = 재기(m)
            _v0 = _낸0[20][0] if _낸0.get(20) else None
            둘, 한, 없 = 0, 0, 0
            for A, B, bA, bB in _반반들:
                _nA, _가A = 재기(m & A)
                _nB, _가B = 재기(m & B)
                vA = _가A[20][0] if _가A.get(20) else None
                vB = _가B[20][0] if _가B.get(20) else None
                if vA is None or vB is None or bA is None or bB is None:
                    continue
                _ok = (vA >= bA + 5) + (vB >= bB + 5)
                if _ok == 2:
                    둘 += 1
                elif _ok == 1:
                    한 += 1
                else:
                    없 += 1
            # ⚠️ 판정 기준을 **먼저** 적는다 — 191차에 임의 기준으로 한 번 속았다
            #    10번 중 **8번 이상** 양쪽 다 넘어야 ✅ (걷기 검증과 같은 엄격함)
            판 = ("✅" if 둘 >= 8 else
                  "⚠️ 흔들린다" if 둘 >= 5 else
                  "❌" if (둘 + 한) < 10 else "❌")
            if 둘 + 한 + 없 == 0:
                판 = "— 표본 80 미만"
            print(f"  {라:<40}"
                  f"{(f'{_v0:.1f}%' if _v0 is not None else '-'):>8}"
                  f"{둘:>14}{한:>9}{없:>11}  {판}", flush=True)
        print("\n     ⭐ 판정 기준 (먼저 적는다) — 10번 중 **8번 이상**")
        print("        양쪽 반쪽이 **둘 다** 그 반쪽 바탕 +5%p 를 넘어야 ✅")

    # ── B-4 ⭐⭐ **달마다 승패** (해마다 승패의 달 판) ──
    #    1년치뿐인 재료는 「해마다」를 할 수 없다. **달마다** 한다
    print("\n  ── B-4 ⭐⭐ **달마다 승패** — 12달 중 몇 달이 그 달 바탕을 넘나 ──",
          flush=True)
    print("     1년치뿐인 재료는 「해마다」를 못 한다. 달로 쪼갠다")
    print("  ⚠️ 달마다 바탕이 다르다 — **그 달의 바탕**과 견준다")

    _달들 = sorted({날[x["인"]][:6] for x in 사건 if 날[x["인"]] >= "20250901"})
    if len(_달들) < 6 or not _볼것:
        print(f"     ⚠️ 달이 {len(_달들)}개뿐이거나 볼 재료가 없다 — 건너뛴다")
    else:
        _달마 = {}
        for _y6 in _달들:
            바 = bytearray((_자리수 + 7) // 8)
            for i2, x in enumerate(사건):
                if 날[x["인"]][:6] == _y6:
                    바[i2 >> 3] |= 1 << (i2 & 7)
            _달마[_y6] = int.from_bytes(바, "little")
        _달바탕 = {}
        for _y6, _mm in _달마.items():
            _, _나 = 재기(_mm)
            _달바탕[_y6] = _나[20][0] if _나.get(20) else None
        print(f"     달 {len(_달들)}개 · {_달들[0]} ~ {_달들[-1]}")
        print(f"\n  {'설정':<40}{'이긴 달':>9}{'진 달':>8}{'못 잼':>8}  판정")
        for 라, 짝 in _볼것:
            m = 조건[짝[0]]
            for _p in 짝[1:]:
                m &= 조건[_p]
            _승, _패, _못 = 0, 0, 0
            for _y6, _mm in _달마.items():
                _b6 = _달바탕[_y6]
                _n6, _나6 = 재기(m & _mm)
                _v6 = _나6[20][0] if _나6.get(20) else None
                if _v6 is None or _b6 is None:
                    _못 += 1
                elif _v6 > _b6:
                    _승 += 1
                else:
                    _패 += 1
            _잰달 = _승 + _패
            판 = ("— 잰 달 6 미만" if _잰달 < 6 else
                  "✅" if _승 >= _잰달 * 2 / 3 else "❌")
            print(f"  {라:<40}{_승:>9}{_패:>8}{_못:>8}  {판}", flush=True)
        print("\n     ⭐ 판정 기준 (먼저 적는다) — 잰 달의 **3분의 2 이상**을 이겨야 ✅")
        print("        (해마다 승패와 같은 잣대다)")

    # ── C 셋씩 ──
    print("\n  ── C **셋씩** — 좋았던 쌍 40개에 세 번째를 붙인다 ──", flush=True)
    셋 = []
    for _, 라, _n, _낸, _짝 in 쌍[:100]:      # ⭐ 40 -> 100 (2026-09-15 ㉦)
        s = 조건[_짝[0]] & 조건[_짝[1]]      # ⭐ 마스크는 여기서 다시 만든다
        쓴 = {p.rstrip("↑↓") for p in 라.split(" + ")}
        for 라3 in 이름들:
            if 라3.rstrip("↑↓") in 쓴:
                continue
            s3 = s & 조건[라3]
            if s3.bit_count() < 400:
                continue
            n3, 낸3 = 재기(s3)
            if 낸3.get(20):
                셋.append((낸3[20][0], f"{라} + {라3}", n3, 낸3))
    셋.sort(key=lambda z: -z[0])
    print(f"     쓸 만한 셋 {len(셋):,}개 · **위 30개**")
    print(머2)
    for _, 라, n, 낸 in 셋[:30]:
        print(줄내기(라, n, 낸))

    # ── D 지금 규칙과 견줌 ──
    # ── C-2 **넷씩** ── (2026-09-15 · 사용자 「세 개든 네 개든」)
    print("\n  ── C-2 **넷씩** — 좋았던 셋 40개에 네 번째를 붙인다 ──", flush=True)
    넷 = []
    for _, 라, _n, _낸 in 셋[:40]:
        _짝3 = 라.split(" + ")
        _s3 = 조건[_짝3[0]] & 조건[_짝3[1]] & 조건[_짝3[2]]
        _쓴3 = {p.rstrip("↑↓") for p in _짝3}
        for 라4 in 이름들:
            if 라4.rstrip("↑↓") in _쓴3:
                continue
            _s4 = _s3 & 조건[라4]
            if _s4.bit_count() < 300:
                continue
            n4, 낸4 = 재기(_s4)
            if 낸4.get(20):
                넷.append((낸4[20][0], f"{라} + {라4}", n4, 낸4))
    넷.sort(key=lambda z: -z[0])
    print(f"     쓸 만한 넷 {len(넷):,}개 · **위 20개**")
    print(머2)
    for _, 라, n, 낸 in 넷[:20]:
        print(줄내기(라, n, 낸))

    print("\n  ── D **지금 규칙**과 견주면 ──")
    print(머2)
    # ⭐ 재기() 는 마스크(int)든 자리 목록이든 둘 다 받는다 (2026-09-14 밤)
    지금 = [i2 for i2, x in enumerate(사건)
            if (x.get("재통과") == 1.0 and 500 <= x["시총억"] < 2000
                and x["대금억"] >= 1.0 and x["볼린저"] <= -1.0
                and x["낙폭20"] <= -10.0)]
    n, 낸 = 재기(지금)
    print(줄내기("지금 규칙 (갭 조건 빼고)", n, 낸))
    n2, 낸2 = 재기(list(range(len(사건))))
    print(줄내기("아무 종목·아무 날 (바탕)", n2, 낸2))

    # ── E ⭐⭐⭐ **②를 지난 쌍을 돈으로** (③ 자본 시뮬) ──
    #    사용자: 「셋 다 지금 한다고 했으면 테스트에 반영된 거야? 왜 자꾸 반복되는 거지?」
    #    이 판에는 시뮬() 이 처음부터 있었는데 **한 번도 안 불렸다** (2026-09-15 확인 · 호출 0).
    #    그래서 B-2 를 지난 12쌍이 ③ 으로 못 갔다 — 판이 아니라 **길이 없었다.**
    #    ⚠️ 규칙 값은 rule_def 에서 읽는다. D절의 「500~2,000억」은 낡은 값이다
    import rule_def as R
    print("\n" + "=" * 122)
    print("  ── E ⭐⭐⭐ **②(앞뒤 분할)를 지난 쌍을 돈으로** — ③ 자본 시뮬 ──")
    print(f"     B-2 를 지난 쌍 {len(_산것)}개 · 쌍마다 「혼자」 와 「기존 OR 쌍」 두 줄")
    print(f"     시드 {_시드:,.0f}원 · 비중 20% · 하루 {R.하루최대종목}종목 · 후보 {R.후보수}개 · "
          f"상대갭 {R.상대갭문턱:g}%p · 매도 {R.몫들}")
    print("  ⚠️ 판정은 **셋 다** — ① 산 것 늘고 ② 돈 늘고 ③ 낙폭 -10% 안. 「혼자」는 참고다")
    print("=" * 122)
    for _i2, _x in enumerate(사건):
        _x["_i"] = _i2
    _밑E = {"시총하한": R.시총하한억, "시총상한": R.시총상한억,
            "대금하한": R.대금하한억, "거래량하한": 0, "회전율하한": 0,
            "상대갭": R.상대갭문턱, "하루상한": R.하루최대종목, "비중": 0.20,
            "나눔": R.몫들, "목표": R.앞몫목표, "최대보유": R.최대보유,
            "후보수": R.후보수}

    def _마스크거름(m):
        바 = m.to_bytes((_자리수 + 7) // 8, "little")
        return lambda x: (바[x["_i"] >> 3] >> (x["_i"] & 7)) & 1

    def _지금E(x):
        return (x.get("재통과") == 1.0 and x["볼린저"] <= R.볼린저문턱
                and x["낙폭20"] <= R.낙폭20문턱)

    print(머)
    _기E = 시뮬(dict(_밑E, 거름=_지금E))
    표(_기E, "기존만 (견줌)")
    if not _산것:
        print("     ⚠️ ②를 지난 쌍이 없다 — 돈으로 갈 것이 없다")
    _E줄 = []
    # ⭐ **단독으로 바탕 +3%p 넘긴 재료**도 OR 로 (2026-09-15 21:30 · 사용자 「이긴 건 OR」)
    _바탕20 = 재기(list(range(len(사건))))[1].get(20)
    _바탕20 = _바탕20[0] if _바탕20 else 44.7
    _단독OR = [라 for _v, 라, _n, _낸 in 단독 if _v >= _바탕20 + 3.0][:12]
    print(f"     단독으로 바탕({_바탕20:.1f}%)+3%p 넘긴 재료 {len(_단독OR)}개도 OR 로 넘긴다")
    _셋E = [z[1] for z in 셋[:8]]           # ⭐ 셋·넷 상위 8개씩도 돈으로 (2026-09-15 21:35)
    _넷E = [z[1] for z in 넷[:8]]
    _E혼 = {}
    for 라 in _단독OR + _산것 + _셋E + _넷E:
        _짝E = 라.split(" + ")
        _m = 조건[_짝E[0]]
        for _p in _짝E[1:]:
            _m &= 조건[_p]
        _f = _마스크거름(_m)
        _혼 = 시뮬(dict(_밑E, 거름=_f))
        _합 = 시뮬(dict(_밑E, 거름=lambda x, g=_f: _지금E(x) or g(x)))
        표(_혼, f"{라[:26]} 혼자", _기E)
        표(_합, f"기존 OR {라[:20]}", _기E)
        _E줄.append((라, _합))
        _E혼[라] = (_혼, _f)
    print("\n     ── 판정 (기존 OR 쌍 · 셋 다여야 ✅) ──")
    print(f"     {'쌍':<40}{'산 것':>8}{'돈':>9}{'낙폭':>8}  판정")
    for 라, r in _E줄:
        _a = r["산"] > _기E["산"]
        _b = r["끝"] > _기E["끝"]
        _c = r["낙"] > -10.0
        판 = "✅ **셋 다**" if (_a and _b and _c) else (
            "⚠️ " + " ".join(z for z, ok in (("산것↓", not _a), ("돈↓", not _b),
                                            ("낙폭>10", not _c)) if ok))
        print(f"     {라:<40}{r['산']:>8}{(r['끝'] / _기E['끝'] - 1) * 100:>+8.0f}%"
              f"{r['낙']:>7.1f}%  {판}")
    print("     ⚠️ ✅ 도 바로 안 바꾼다 — gate7_lab 4관문(해마다·무작위·오차)을 다시 지나야 한다")

    # ── F ⭐⭐⭐ **기존 없이** — 셋 다 지난 조합들을 OR 로 묶어 **새 규칙** ── (2026-09-15 21:35)
    #    사용자: 「꼭 기존 규칙에 더하는 게 아니라 다른 여러 조합도 좋을 것 같아」
    #    E 에서 「기존 OR 조합」이 셋 다인 것들을, **기존 없이** 돈이 느는 순으로 하나씩 OR 로 묶는다.
    #    욕심쟁이(한 번에 하나) · 낙폭 −10% 넘으면 안 넣는다 · 돈이 안 늘면 멈춘다
    print("\n  ── F ⭐⭐⭐ **기존 없이 — 조합들의 OR 로 새 규칙** ──")
    print(머)
    표(_기E, "기존만 (견줌)")
    _통과F = sorted([(r["끝"], 라) for 라, r in _E줄
                     if r["산"] > _기E["산"] and r["끝"] > _기E["끝"] and r["낙"] > -10.0
                     and 라 in _E혼], reverse=True)
    _후보F = [라 for _, 라 in _통과F][:10]
    print(f"     셋 다 지난 조합 {len(_통과F)}개 중 위 {len(_후보F)}개로 묶는다")
    _고른F, _현재F = [], None
    for _단계 in range(min(5, len(_후보F))):
        _best = None
        for 라 in _후보F:
            if 라 in _고른F:
                continue
            _fs = [_E혼[z][1] for z in _고른F + [라]]
            _r = 시뮬(dict(_밑E, 거름=lambda x, fs=_fs: any(f(x) for f in fs)))
            if _r["낙"] <= -10.0:
                continue
            if _best is None or _r["끝"] > _best[0]["끝"]:
                _best = (_r, 라)
        if _best is None or (_현재F is not None and _best[0]["끝"] <= _현재F["끝"]):
            break
        _고른F.append(_best[1])
        _현재F = _best[0]
        표(_현재F, f"조합 {len(_고른F)}개 OR (기존 없이)", _기E)
        print(f"        + {_best[1]}")
    if _고른F:
        _fsF = [_E혼[z][1] for z in _고른F]
        _새규칙 = (lambda x: any(f(x) for f in _fsF))
        _둘다 = (lambda x: _지금E(x) or any(f(x) for f in _fsF))
        표(시뮬(dict(_밑E, 거름=_둘다)), f"기존 OR 그 조합 {len(_고른F)}개", _기E)
        print("\n     ── 앞뒤 분할 (제약 없는 판) ──")
        for _시F, _끝F, _라F in (("2016", "2021", "[앞 2016~2020]"), ("2021", "2027", "[뒤 2021~2026]")):
            print(f"\n   {_라F}")
            print(머)
            _기F = 시뮬(dict(_밑E, 거름=_지금E), 시작년=_시F, 끝년=_끝F)
            표(_기F, "[견줌] 기존만")
            표(시뮬(dict(_밑E, 거름=_새규칙), 시작년=_시F, 끝년=_끝F), "새 규칙 (기존 없이)", _기F)
            표(시뮬(dict(_밑E, 거름=_둘다), 시작년=_시F, 끝년=_끝F), "기존 OR 새 규칙", _기F)
        print("\n     ⚠️ 새 규칙이 기존을 **돈·낙폭·산 것 셋 다** 이기고 앞뒤 둘 다 이기면 → gate7 4관문으로")
    else:
        print("     ⚠️ 낙폭 −10% 안에서 묶을 수 있는 조합이 없다")

    print("\n" + "=" * 122)
    print("  읽는 법")
    print("    - ⚠️ **378쌍을 재면 몇 개는 운으로 좋아 보인다.**")
    print("      위에 있다고 채택하면 안 된다 — 반드시 **4관문**을 지나야 한다")
    print("      특히 ③ 무작위 대조(200~300개 중 상위 25%)가 이걸 걸러낸다")
    print("    - **1년에 몇 개**를 같이 본다. 1년 10개면 못 쓴다")
    print("    - D 에서 지금 규칙보다 나은 게 없으면 **지금 규칙이 괜찮은 것**이다")
    print("=" * 122)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      # ⚠ 다른 값으로 다시 돌릴 때 결과를 덮어쓰지 않는다
                      os.environ.get("LAB_OUT") or "2026-09-08_163차_단독과새조합.txt")

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
