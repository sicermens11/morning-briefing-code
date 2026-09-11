#!/usr/bin/env python3
r"""
group_lab.py — **185차 · 섹터마다 제 규칙** (2026-09-09 신설)

## 사용자 지적 (여러 번 말했는데 내가 못 알아들었다)
```
「**모든 섹터에 통하는 한 가지 규칙**을 만들라는 뜻이 아니라
  **각 섹터에 맞게 각각의 규칙**을 테스트해보라는 뜻이야!」
```
내가 계속 재본 것은 **한 가지 공식을 섹터마다 스케일만 바꾼 것**이었다
(169차 F절: 「그 섹터 기준 몇 σ」 — 공식은 하나다).
사용자가 말한 것은 **섹터마다 재료도 문턱도 다른, 서로 다른 규칙**이다

## 그래서 이 시험이 하는 것
```
섹터 하나를 잡고 **그 섹터 안에서만** 격자를 돌려 제일 좋은 규칙을 찾는다
  볼린저 창  20 · 60일          x 문턱 -0.5 / -1.0 / -1.5
  낙폭 창    20 · 60 · 120일    x 문턱 -5 / -10 / -15 / -20 / -30%
  = 섹터마다 90칸을 다 돌려 **그 섹터의 규칙**을 찾는다
그걸 20개 섹터에 대해 따로 한다 -> **섹터마다 다른 규칙 20개**
```

## ⚠️⚠️ 2026-09-09 고침 — E절이 **기회 수를 안 봤다**
```
전:  이김만 봤다  ->  1년 42개(80.7%)가 1년 2,115개(53.6%)를 이긴 것으로 찍혔다
     그래서 나누는 법 22가지가 **전부** 통과한 것처럼 보였다
후:  **기회가 절반 밑으로 줄면 못 이긴 것**으로 본다
     사용자 원칙 ④: 「매수 기회 포착 우선 — 적게 살수록 점수가 오르면 안 된다」
```

## ⚠️⚠️ 이 시험의 핵심은 **E절(걷기 검증)**이다
```
섹터가 20개면 고를 것이 20배가 된다. 과거에 맞추기는 너무 쉽다.
그래서 **앞 기간에서 찾은 규칙을 뒤 기간에 그대로 써본다.**
거기서 안 되면 아무리 A~D 가 좋아도 **과적합**이다
```

## 잣대 — 155차와 같다
```
① 1년에 몇 개  ② 20일 뒤 오른 비율  ③ 평균 몇 %
바탕(아무 종목·아무 날) 20일 = 43.5% · +0.33%
⚠️ 상장폐지는 -50% 손실로 센다
```

쓰는 법:
    python scripts\sector_own_lab.py
"""
import glob
import datetime as dt
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
    # ⭐⭐ **krx-daily 를 한 번만 파싱한다** (2026-09-09).
    #    전에는 수정주가()로 52초 + 아래 루프로 62초 = **114초**를 같은 파일에 썼다.
    #    krx한번읽기() 는 한 번 읽어 다섯 개를 다 만들고 **캐시**까지 한다 -> 3초
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = sorted(주가)
    _사라짐 = O.사라진종목(주가, 날)
    print(f"  중간에 사라진 종목 {len(_사라짐):,}개 — "
          f"상장폐지는 {O.폐지손실:.0f}% 손실로 센다", flush=True)
    assert isinstance(날, list) and len(날) > 1000, ('거래일 목록이 깨졌다', len(날))
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

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

    # ⭐ **시장표를 먼저 만든다** (2026-09-09 고침).
    #    전에는 사건을 만든 **뒤**에 만들어서 UnboundLocalError 로 죽었다
    #    (185차가 2분 만에 죽은 원인)
    시장표 = {}
    _sp = os.path.join(O._DATA, "stock-base.json")
    if os.path.exists(_sp):
        _sb = json.load(io.open(_sp, encoding="utf-8-sig"))
        for c2, v2 in _sb.items():
            if isinstance(v2, dict) and v2.get("시장"):
                시장표[c2] = str(v2["시장"])

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
            # ⭐ statistics 는 분수로 세느라 **36배 느리다** (2026-09-09 실측)
            s20, sd = O.창평균표준(sq, kk, 20)
            sd = sd or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            # ── 180차: 섹터마다 고를 수 있게 창을 여럿 붙인다 ──
            창값 = {}
            for w in (10, 20, 60, 120):
                if kk >= w and sq[kk - w] > 0:
                    창값[f"낙{w}"] = (c1 / sq[kk - w] - 1) * 100
            # ── ⭐ 나누는 법을 더 찾는다 (2026-09-09) ──
            if kk >= 20:
                뒤 = sq[kk - 20:kk + 1]
                하루들 = [(뒤[z] / 뒤[z - 1] - 1) * 100
                          for z in range(1, len(뒤)) if 뒤[z - 1] > 0]
                if 하루들:
                    # ⑬ 빠지는 모양 — 가장 나빴던 하루가 20일 낙폭의 몇 %인가
                    창값["_최악하루"] = min(하루들)
                    창값["_내린날"] = sum(1 for z in 하루들 if z < 0)
                # ⑯ 며칠째 내리 빠지나
                연 = 0
                for z in range(kk, max(0, kk - 20), -1):
                    if sq[z] < sq[z - 1]:
                        연 += 1
                    else:
                        break
                창값["_연속하락"] = 연
            if kk >= 250:
                # ⑮ 250일 최고가 대비 어디쯤인가
                최고 = max(sq[kk - 250:kk + 1])
                창값["_최고대비"] = ((c1 / 최고 - 1) * 100) if 최고 > 0 else None
            for w in (10, 20, 60, 120):
                if kk >= w:
                    m2, d2 = O.창평균표준(sq, kk, w)
                    d2 = d2 or 1e-9
                    창값[f"볼{w}"] = (c1 - m2) / (2 * d2)
                    if w == 20:
                        # ⭐ 1σ 가 그 종목에서 몇 %인가 (제변동성 계산용)
                        창값["_1σ퍼센트"] = (d2 / c1 * 100) if c1 else None
            낙60 = ((c1 / sq[kk - 60] - 1) * 100
                    if kk >= 60 and sq[kk - 60] > 0 else None)
            s60 = O.창평균표준(sq, kk, 60)[0] if kk >= 59 else None
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
            # ⑭ 투매인가 — 20일 평균 거래량 대비 오늘 거래량
            _옛량 = [(거량.get(날[max(0, i - z)]) or {}).get(code)
                     for z in range(1, 21)]
            _옛량 = [v for v in _옛량 if v]
            창값["_거래량배"] = ((량 / (sum(_옛량) / len(_옛량)))
                              if (_옛량 and 량) else None)
            사건.append({
                "인": i + 1, "code": code, "원시": o0, "대금": b0[2],
                "볼린저": 볼, "낙폭20": 낙,
                "시총억": 시총 / 1e8, "대금억": 대금 / 1e8, "거래량": 량,
                "회전율": (대금 / 시총 * 100) if 시총 > 0 else 0,
                "갭": g, "매수": 매수, "재통과": 재통과, "낙폭60": 낙60,
                "해": d1[:4], "_시장": 시장표.get(code), **창값,
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
                    m20 = O.창평균표준(sq2, kk2, 20)[0]
                    회복 = False
                    if 상태 == "20일선":
                        회복 = sq2[kk2] > m20
                    else:
                        sd2 = O.창평균표준(sq2, kk2, 20)[1] or 1e-9
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

    # ── 업종 (industry.json — 표준산업분류) ──
    업종 = {}
    _ip = os.path.join(O._DATA, "industry.json")
    if os.path.exists(_ip):
        for c2, v2 in json.load(io.open(_ip, encoding="utf-8-sig")).items():
            if isinstance(v2, dict) and v2.get("업종명"):
                업종[c2] = str(v2["업종명"])

    def 바탕(x):
        # ⚠⚠ **시총 상한을 푸었다** (2026-09-09 사용자 지적).
        #    「대형주도 **매수 기회 신호가 있으면 후보가 될 수 있는 거 아니야?」
        #    지금 상한 2,000억은 **94차에서 자본 시뮬로** 정한 것이고,
        #    그 잣대가 기회를 긎는다는 걸 나중에 알았다.
        #    158차(이길확률): 1조 이상 55.6% > 2,000억~1조 51.6%
        #    → 「대형주가 안 된다」가 아니라
        #      「대형주에 **지금 문턱(-10%)을** 쓰면 안 된다」일 수 있다
        return (x.get("재통과") == 1.0 and x["시총억"] >= 300
                and x["대금억"] >= 1.0)

    # ⭐⭐ **섹터만이 아니다** (2026-09-09 사용자 지적).
    #    「종목별로 섹터별로 **규모별로** 매수 기회포착을 위한
    #      규칙을 달리 적용해도 된다는 거!」
    #    -> 나누는 방법을 **셋**으로 하고 각각 다 돌린다
    def 규모칸(x):
        # ⭐ **2,000억 위까지 넘는다** (2026-09-09)
        v = x["시총억"]
        if v < 500:
            return "규 1) 소형 300~500억"
        if v < 800:
            return "규 2) 중소 500~800억"
        if v < 1200:
            return "규 3) 중형 800~1,200억"
        if v < 2000:
            return "규 4) 준대형 1,200~2,000억"
        if v < 5000:
            return "규 5) **2,000~5,000억**"
        if v < 10000:
            return "규 6) **5,000억~1조**"
        if v < 100000:
            return "규 7) **1조~10조**"
        return "규 8) **10조 이상**"

    def 상태칸(x):
        """종목 하나하나는 표본이 모자란다 —
        대신 **그 종목이 얼마나 잘 움직이는가**로 묶는다"""
        v = x.get("시장변동성")
        if v is None:
            return None
        if v < 1.2:
            return "조용한 장"
        if v < 1.8:
            return "보통 장"
        return "흔들리는 장"

    # ══════════════════════════════════════════════════════════════
    #  ⭐⭐ **나눌 만한 방법을 내가 찾아본다** (2026-09-09 사용자 요청)
    #     「꼭 규모별 섹터별로 나누라는 게 아니고, 테스트해보고
    #       **구분하는 게 좋은 결과가 나오면** 구분하는 거고,
    #       한 가지 규칙으로 충분하다고 결론 나면 한 가지여도 돼.
    #       내가 얘기하고 싶은 건 **규모별·섹터별로 나누는 게 유효한지**야.
    #       그리고 **규모·섹터 말고도 구분 지을 게 있는지 니가 한번 찾아보기도 하고!**」
    #
    #     ⚠️ 결론이 「나눌 까닭이 없다」여도 그게 답이다. 억지로 나누지 않는다
    # ══════════════════════════════════════════════════════════════
    def 가격대(x):
        """⚠️ **호가 단위가 다르다.** 1,000원짜리는 1원 단위(0.1%),
           50,000원짜리는 100원 단위(0.2%) — 갭과 체결이 다르게 걸린다"""
        p = x.get("원시") or 0
        if p <= 0:
            return None
        if p < 2000:
            return "가 1) 2,000원 미만"
        if p < 5000:
            return "가 2) 2,000~5,000원"
        if p < 20000:
            return "가 3) 5,000~2만원"
        return "가 4) 2만원 이상"

    def 유동성(x):
        """거래대금 — 얇으면 호가가 튀고 못 산다"""
        v = x.get("대금억")
        if v is None:
            return None
        if v < 2:
            return "유 1) 1~2억"
        if v < 5:
            return "유 2) 2~5억"
        if v < 15:
            return "유 3) 5~15억"
        return "유 4) 15억↑"

    def 제변동성(x):
        """⚠️ **섹터보다 직접적이다.** 반도체라서 많이 움직이는 게 아니라
           **그 종목이** 많이 움직인다. 20일 볼린저 폭으로 잰다"""
        폭 = x.get("_1σ퍼센트")
        if 폭 is None:
            return None
        if 폭 < 8:
            return "변 1) 조용 (1σ<8%)"
        if 폭 < 13:
            return "변 2) 보통 (8~13%)"
        if 폭 < 20:
            return "변 3) 활발 (13~20%)"
        return "변 4) 사나움 (20%↑)"

    def 회전율칸(x):
        """거래대금 ÷ 시총 — 손바뀜이 얼마나 잦나"""
        v = x.get("회전율")
        if v is None:
            return None
        if v < 0.3:
            return "회 1) 0.3% 미만"
        if v < 1.0:
            return "회 2) 0.3~1%"
        if v < 3.0:
            return "회 3) 1~3%"
        return "회 4) 3%↑"

    def 재무등급(x):
        """잉여금이 두터운가 — 같은 「우량」 안에서도 층이 있다"""
        v = x.get("잉여금")
        if v is None:
            return None
        if v < 60:
            return "재 1) 잉여금 30~60%"
        if v < 150:
            return "재 2) 60~150%"
        if v < 400:
            return "재 3) 150~400%"
        return "재 4) 400%↑"

    def 수익성(x):
        """영업이익률 — 남는 장사인가"""
        v = x.get("영업이익률")
        if v is None:
            return None
        if v < 3:
            return "익 1) 3% 미만"
        if v < 8:
            return "익 2) 3~8%"
        if v < 15:
            return "익 3) 8~15%"
        return "익 4) 15%↑"

    def 흐름칸(x):
        """60일 흐름 — 꾸준히 빠졌나, 급등 뒤 되돌림인가"""
        v = x.get("낙폭60")
        if v is None:
            return None
        if v <= -20:
            return "흐 1) 60일도 크게 하락"
        if v <= -5:
            return "흐 2) 60일 완만 하락"
        if v <= 10:
            return "흐 3) 60일 제자리"
        return "흐 4) ⚠️ 급등 뒤 되돌림"

    def 시장칸(x):
        """코스피냐 코스닥이냐"""
        return x.get("_시장")

    def 상대강도칸(x):
        """시장보다 더 빠졌나 덜 빠졌나"""
        v = x.get("상대강도")
        if v is None:
            return None
        if v <= -10:
            return "상 1) 시장보다 훨씬 더 빠짐"
        if v <= 0:
            return "상 2) 시장보다 더 빠짐"
        return "상 3) 시장보다 덜 빠짐"

    # ══ ⭐ 나누는 법을 더 찾았다 (2026-09-09 사용자: 「또 구분해야 하는 기준이 있을까?」) ══
    def 왜빠졌나(x):
        """⚠️ **이유 있는 하락과 이유 없는 하락은 되돌림이 다르다**.
           공시가 있었으면 이유가 있는 것이다"""
        v = x.get("_공시5")
        if v is None:
            return None
        return "왜 1) 공시 있었다" if v else "왜 2) 조용히 빠졌다"

    def 빠지는모양(x):
        """하루에 왕창인가, 계단식인가.
           ⚠️ 하루 -15%와 스무날 걸쳐 -15%는 **다른 일**이다"""
        최 = x.get("_최악하루")
        낙 = x.get("낙20")
        if 최 is None or 낙 is None or 낙 >= 0:
            return None
        몫 = 최 / 낙          # 가장 나쁜 하루가 전체 낙폭의 몇 배
        if 몫 >= 0.7:
            return "모 1) 하루에 왕창"
        if 몫 >= 0.4:
            return "모 2) 며칠에 나눠"
        return "모 3) 계단식으로 천천히"

    def 투매인가(x):
        """빠질 때 거래량이 터졌나 — 던져진 것인가 흘러내린 것인가"""
        v = x.get("_거래량배")
        if v is None:
            return None
        if v < 0.8:
            return "투 1) 거래 줄었다 (관심 없음)"
        if v < 1.5:
            return "투 2) 평소만큼"
        if v < 3:
            return "투 3) 거래 늘었다"
        return "투 4) ⚠️ 터졌다 (3배↑)"

    def 신저가인가(x):
        """250일 최고가 대비 어디쯤"""
        v = x.get("_최고대비")
        if v is None:
            return None
        if v <= -60:
            return "저 1) 최고가 -60%↓ (바닥권)"
        if v <= -40:
            return "저 2) -40~60%"
        if v <= -20:
            return "저 3) -20~40%"
        return "저 4) -20% 이내 (고가권)"

    def 며칠째(x):
        v = x.get("_연속하락")
        if v is None:
            return None
        if v <= 1:
            return "연 1) 1일"
        if v <= 3:
            return "연 2) 2~3일"
        if v <= 5:
            return "연 3) 4~5일"
        return "연 4) 6일↑"

    def 회사나이(x):
        """최근 상장인가 오래된 회사인가"""
        v = x.get("_나이")
        if v is None:
            return None
        if v < 15:
            return "나 1) 15년 미만"
        if v < 30:
            return "나 2) 15~30년"
        if v < 50:
            return "나 3) 30~50년"
        return "나 4) 50년↑"

    def 금리국면(x):
        """미국 기준금리가 석 달 새 오르나 내리나"""
        v = x.get("_금리변화")
        if v is None:
            return None
        if v <= -0.25:
            return "금 1) 내리는 중"
        if v < 0.25:
            return "금 2) 그대로"
        return "금 3) 올리는 중"

    def 환율국면(x):
        """원/달러가 한 달 새 올랐나 (원화 약세인가)"""
        v = x.get("_환율변화")
        if v is None:
            return None
        if v <= -2:
            return "환 1) 원화 강세"
        if v < 2:
            return "환 2) 보합"
        return "환 3) 원화 약세"

    def 전날미국(x):
        """어젯밤 미국장(SPY)이 어땠나"""
        v = x.get("_미국하루")
        if v is None:
            return None
        if v <= -2:
            return "미 1) 미국 크게 빠짐"
        if v < 0:
            return "미 2) 미국 조금 빠짐"
        if v < 2:
            return "미 3) 미국 조금 오름"
        return "미 4) 미국 크게 오름"

    def 외인순매수(x):
        """외국인이 20일 동안 사고 있었나 팔고 있었나"""
        v = x.get("외인20")
        if v is None:
            return None
        if v <= -0.5:
            return "외 1) 외국인 많이 팜"
        if v < 0:
            return "외 2) 외국인 조금 팜"
        if v < 0.5:
            return "외 3) 외국인 조금 삼"
        return "외 4) 외국인 많이 삼"

    def 대량보유(x):
        """최근 90일에 5% 대량보유 신고가 있었나 — 큰손이 움직였나"""
        v = x.get("_대량보유")
        if v is None:
            return None
        return "대 1) 큰손 움직임 있었다" if v else "대 2) 없었다"

    나누기들 = (
        ("섹터", lambda x: 업종.get(x["code"])),
        ("규모", 규모칸),
        ("가격대", 가격대),
        ("유동성(거래대금)", 유동성),
        ("**그 종목 변동성**", 제변동성),
        ("회전율", 회전율칸),
        ("재무 두께", 재무등급),
        ("수익성", 수익성),
        ("60일 흐름", 흐름칸),
        ("상대강도", 상대강도칸),
        ("시장상태", 상태칸),
        # ⭐ 2026-09-09 새로 찾은 여섯
        ("**왜 빠졌나**(공시)", 왜빠졌나),
        ("**빠지는 모양**", 빠지는모양),
        ("**투매인가**(거래량)", 투매인가),
        ("**신저가인가**", 신저가인가),
        ("며칠째 빠지나", 며칠째),
        ("회사 나이", 회사나이),
        # ⭐ 2026-09-09 「모두 반영해」 — 바깥 자료 다섯
        ("**금리 국면**", 금리국면),
        ("**환율 국면**", 환율국면),
        ("**전날 미국장**", 전날미국),
        ("**외국인 순매수**", 외인순매수),
        ("**5% 대량보유**", 대량보유),
    )

    # ══ 재료 조건 목록 — **눈금을 잘게, 재료를 넓게** ══
    #  ⚠️⚠️ 180차는 **볼린저와 낙폭 둘뿐**이었다.
    #     사용자: 「각 재료의 **세분화한 데이터와 조합**해보고 나온 결과야?
    #             **단독이든 새로운 조합이든**?」 -> 아니었다. 여기서 넓힌다
    def 있(x, k):
        return x.get(k) is not None

    조건들 = []
    for w in (10, 20, 60, 120):
        for 문 in (-0.5, -1.0, -1.5, -2.0):
            조건들.append((f"볼{w}일{문}σ",
                          lambda x, a=w, b=문: (있(x, f"볼{a}")
                                               and x[f"볼{a}"] <= b)))
    for w in (10, 20, 60, 120):
        for 문 in (-5, -10, -20, -30):
            조건들.append((f"낙{w}일{문}%",
                          lambda x, a=w, b=문: (있(x, f"낙{a}")
                                               and x[f"낙{a}"] <= b)))
    # ── 볼린저·낙폭 말고도 ──
    for 라, k, 문들, 위 in (
            ("잉여금", "잉여금", (30, 80, 200), True),
            ("부채", "부채", (40, 60, 80), False),
            ("ROE", "ROE", (0, 5, 12), True),
            ("영업이익률", "영업이익률", (0, 5, 12), True),
            ("대금", "대금억", (1, 3, 10), True),
            ("회전율", "회전율", (0.5, 1.5, 4), True),
            ("시장낙폭", "시장낙폭", (-3, -7, -12), False),
            ("상대강도", "상대강도", (-12, -5, 3), False),
            ("섹터대비", "섹터대비", (-12, -5, 3), False),
            ("외인20", "외인20", (0.0,), True),
            ("기관20", "기관20", (0.0,), True),
            ("60일선대비", "60일선대비", (-10, -25), False)):
        for 문 in 문들:
            if 위:
                조건들.append((f"{라}≥{문}",
                              lambda x, a=k, b=문: 있(x, a) and x[a] >= b))
            else:
                조건들.append((f"{라}≤{문}",
                              lambda x, a=k, b=문: 있(x, a) and x[a] <= b))
    print(f"  재료 조건 **{len(조건들)}개**", flush=True)

    def 점(칸, 최소=120):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < 최소:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(칸))

    def 단계고르기(칸, 깊이=3, 최소=120):
        r"""**단계적으로** 조건을 하나씩 붙여 간다.

        ⚠️ 전수 조합(40C3 = 9,880)은 못 돌린다. 단계적이면 40+39+38 = 117.
           대신 **과적합이 더 쉽다** -> 걷기 검증으로 가려야 한다
        """
        고름, 남은 = [], list(range(len(조건들)))
        지금칸 = 칸
        best = 점(지금칸, 최소)
        for _ in range(깊이):
            좋 = None
            for i2 in 남은:
                _라, fn = 조건들[i2]
                새칸 = [z for z in 지금칸 if fn(z)]
                p = 점(새칸, 최소)
                if p and (좋 is None or p[0] > 좋[0][0]):
                    좋 = (p, i2, 새칸)
            if not 좋 or (best and 좋[0][0] <= best[0] + 0.3):
                break          # 더 붙여도 안 나아지면 멈춘다
            best, i2, 지금칸 = 좋[0], 좋[1], 좋[2]
            고름.append(i2)
            남은.remove(i2)
        return (best, 고름) if 고름 else None

    def 규칙쓰기(고름):
        return " + ".join(조건들[i2][0] for i2 in 고름)

    def 걸림2(x, 고름):
        return all(조건들[i2][1](x) for i2 in 고름)

    def 지금걸림(x):
        return x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0

    print("\n" + "=" * 122)
    print("  185차 · **무리마다 재료를 단계적으로 골라 조합까지 만든다**")
    print("  사용자: 「각 재료의 **세분화한 데이터와 조합**해보고 나온 결과야?")
    print("           **단독이든 새로운 조합이든**?」")
    print(f"  후보 {len(사건):,}건 · 바탕(아무 종목·아무 날) 20일 43.5% · +0.33%")
    print(f"  ⚠️ 상장폐지 {O.폐지손실:.0f}% · **1년에 몇 개**를 먼저 본다")
    print("=" * 122)

    # ⭐ 공시(5일 안에 있었나) · 회사 나이를 붙인다
    print("  공시·설립일 읽는 중...", flush=True)
    _공 = O._공시(날)
    _공날 = {}
    for d8, v in _공.items():
        for c2 in v:
            _공날.setdefault(c2, set()).add(d8)
    _나이 = {}
    _ip2 = os.path.join(O._DATA, "industry.json")
    if os.path.exists(_ip2):
        for c2, v2 in json.load(io.open(_ip2, encoding="utf-8-sig")).items():
            s2 = str((v2 or {}).get("설립일") or "")
            if len(s2) == 8 and s2.isdigit():
                _나이[c2] = int(s2[:4])
    for x in 사건:
        i3 = x["인"] - 1
        s3 = _공날.get(x["code"]) or set()
        x["_공시5"] = 1.0 if any(d in s3 for d in 날[max(0, i3 - 4):i3 + 1]) else 0.0
        해2 = _나이.get(x["code"])
        x["_나이"] = (int(x["해"]) - 해2) if 해2 else None

    # ══ ⭐ 바깥 자료를 붙인다 (2026-09-09 · 「모두 테스트에 반영해」) ══
    #  ⚠️ 「자료가 얕아서 못 넣는다」고 했는데 **열어보니 다 있었다**
    #     (메모리 dont-declare-impossible)
    print("  금리·환율·미국장·대량보유 읽는 중...", flush=True)

    def _계열(경로, 키=None):
        try:
            d2 = json.load(io.open(경로, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            return {}
        v = d2.get(키) if 키 else d2.get("값")
        return v if isinstance(v, dict) else {}

    _금리 = _계열(os.path.join(O._DATA, "fred", "AV_FEDFUNDS.json"))
    _환율 = _계열(os.path.join(O._DATA, "fx-daily.json"), "USDKRW")
    _미국 = _계열(os.path.join(O._DATA, "yahoo", "SPY.json"), "종가")
    print(f"    금리 {len(_금리):,}일 · 환율 {len(_환율):,}일 · "
          f"미국 {len(_미국):,}일", flush=True)

    def _앞값(표, d8, n):
        """d8 에서 n 달력일 전의 값 (없으면 가장 가까운 앞 것)"""
        키 = sorted(k for k in 표 if k <= d8)
        if not 키:
            return None, None
        지금 = 표[키[-1]]
        _dt = dt.datetime.strptime(d8, "%Y%m%d") - dt.timedelta(days=n)
        앞8 = _dt.strftime("%Y%m%d")
        앞키 = [k for k in 키 if k <= 앞8]
        return (지금, 표[앞키[-1]]) if 앞키 else (지금, None)

    # 5% 대량보유
    _대량 = {}
    for f2 in glob.glob(os.path.join(O._DATA, "dart-major", "*.json")):
        try:
            d2 = json.load(io.open(f2, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        c2 = d2.get("종목")
        for r2 in (d2.get("이력") or []):
            날2 = str(r2.get("접수일") or "").replace("-", "")
            if c2 and len(날2) == 8:
                _대량.setdefault(c2, set()).add(날2)
    print(f"    5% 대량보유 {len(_대량):,}종목", flush=True)

    # 날짜별로 한 번만 계산해 캐시
    _국면캐시 = {}
    for x in 사건:
        d8 = 날[x["인"] - 1]
        c3 = _국면캐시.get(d8)
        if c3 is None:
            금지, 금앞 = _앞값(_금리, d8, 90)
            환지, 환앞 = _앞값(_환율, d8, 30)
            미지, 미앞 = _앞값(_미국, d8, 3)
            c3 = {
                "_금리변화": (금지 - 금앞) if (금지 and 금앞) else None,
                "_환율변화": ((환지 / 환앞 - 1) * 100)
                if (환지 and 환앞) else None,
                "_미국하루": ((미지 / 미앞 - 1) * 100)
                if (미지 and 미앞) else None,
            }
            _국면캐시[d8] = c3
        x.update(c3)
        # 5% 대량보유 — 최근 90일
        s3 = _대량.get(x["code"]) or set()
        앞8 = (dt.datetime.strptime(d8, "%Y%m%d")
               - dt.timedelta(days=90)).strftime("%Y%m%d")
        x["_대량보유"] = 1.0 if any(앞8 <= z <= d8 for z in s3) else 0.0

    바탕칸 = [x for x in 사건 if 바탕(x)]
    from collections import Counter as _C

    # ── 0 나누지 않고 (견줌용) ──
    print("\n  ── 0 **나누지 않고** 단계적으로 고르면 (견줌용) ──")
    지 = 점([x for x in 바탕칸 if 지금걸림(x)])
    if 지:
        print(f"  {'지금 규칙':<44}{지[2]:>9,}건 · 1년 {지[2]/해수:>5.0f}개"
              f" · 이김 {지[0]:>5.1f}% · 평균 {지[1]:>+6.2f}%")
    통 = 단계고르기(바탕칸)
    if 통:
        (이, 평, n), 고름 = 통
        print(f"  {규칙쓰기(고름)[:43]:<44}{n:>9,}건 · 1년 {n/해수:>5.0f}개"
              f" · 이김 {이:>5.1f}% · 평균 {평:>+6.2f}%")

    for 나름, 뽑기 in 나누기들:
        칸별 = {}
        for x in 바탕칸:
            k = 뽑기(x)
            if k:
                칸별.setdefault(k, []).append(x)
        최소칸 = 3000 if 나름 == "섹터" else 6000
        무리들 = [g for g in sorted(칸별, key=lambda z: -len(칸별[z]))
                  if len(칸별[g]) >= 최소칸]
        if not 무리들:
            print(f"\n  ⚠️ {나름}: 표본이 되는 무리가 없다")
            continue

        print("\n" + "=" * 122)
        print(f"  ══ **{나름}**로 나눠 각각 골라 보면 ({len(무리들)}개 무리) ══")
        print("=" * 122)

        print(f"\n  ── A {나름}마다 **단계적으로 고른 규칙** ──")
        print(f"  {'무리':<16}{'전체':>9}{'지금':>8}{'그 무리 규칙':>46}"
              f"{'이김':>8}{'좋아짐':>9}")
        찾은 = {}
        for g in 무리들:
            칸 = 칸별[g]
            지 = 점([z for z in 칸 if 지금걸림(z)])
            r = 단계고르기(칸)
            if not r:
                print(f"  {str(g)[:15]:<16}{len(칸):>9,}   못 골랐다")
                continue
            (이, 평, n), 고름 = r
            찾은[g] = 고름
            print(f"  {str(g)[:15]:<16}{len(칸):>9,}"
                  f"{(f'{지[0]:.1f}%' if 지 else '-'):>8}"
                  f"{규칙쓰기(고름)[:45]:>46}{이:>7.1f}%"
                  + (f"{이-지[0]:>+9.1f}p" if 지 else ""))

        print(f"\n  ── B {나름}마다 제 규칙을 쓰면 **전체로는** ──")
        지칸 = [x for x in 바탕칸 if 지금걸림(x)]
        제칸 = []
        for g, 고름 in 찾은.items():
            제칸 += [z for z in 칸별[g] if 걸림2(z, 고름)]
        for 라, 칸 in (("모두 같은 규칙 (지금)", 지칸),
                       (f"**{나름}마다 제 규칙**", 제칸)):
            p = 점(칸)
            if p:
                print(f"  {라:<30}{p[2]:>9,}건 · 1년 {p[2]/해수:>5.0f}개"
                      f" · 이김 {p[0]:>5.1f}% · 평균 {p[1]:>+6.2f}%")

        print(f"\n  ── C {나름}마다 고른 **첫 재료**가 얼마나 다른가 ──")
        첫 = _C(조건들[고름[0]][0] for 고름 in 찾은.values() if 고름)
        print(f"  {dict(첫)}")
        print("  ⚠️ 한 재료에 몰려 있으면 **나눌 까닭이 없다**는 뜻이다")

        print(f"\n  ── E ⭐ **걷기 검증** ──")
        for 배움끝, 씀시작, 씀끝 in (("2019", "2020", "2022"),
                                    ("2021", "2022", "2026"),
                                    ("2022", "2023", "2026")):
            배운 = {}
            for g in 무리들:
                r = 단계고르기([z for z in 칸별[g] if z["해"] <= 배움끝],
                              최소=60)
                if r:
                    배운[g] = r[1]
            뒤제것, 뒤지금 = [], []
            for g in 무리들:
                뒤칸 = [z for z in 칸별[g] if 씀시작 <= z["해"] <= 씀끝]
                뒤지금 += [z for z in 뒤칸 if 지금걸림(z)]
                고름 = 배운.get(g)
                if 고름:
                    뒤제것 += [z for z in 뒤칸 if 걸림2(z, 고름)]
            a = 점(뒤지금)
            b = 점(뒤제것)
            print(f"\n   [~{배움끝} 배워 {씀시작}~{씀끝} · 무리 {len(배운)}개]")
            for 라, p in (("모두 같은 규칙", a), (f"**{나름}마다 배운 규칙**", b)):
                if p:
                    print(f"     {라:<26}{p[2]:>8,}건 · 1년 {p[2]/해수:>5.0f}개"
                          f" · 이김 {p[0]:>5.1f}% · 평균 {p[1]:>+6.2f}%")
            if a and b:
                # ⚠️⚠️ **기회 수를 반드시 같이 본다** (2026-09-09 고침).
                #    전에는 이김만 봤다(b[0] > a[0]). 그래서
                #      모두 같은 규칙 1년 2,115개 53.6%
                #      규모마다      1년    42개 80.7%  -> 「✅ 낫다 +27.1%p」
                #    **기회가 1/50 로 줄었는데 이겼다고 셌다.**
                #    사용자 원칙 ④: 「매수 기회 포착 우선 — **적게 살수록 점수가
                #    오르면 안 된다**」 를 정면으로 어긴 것이다
                기회비 = (b[2] / a[2]) if a[2] else 0.0
                이겼나 = (b[0] > a[0]) and 기회비 >= 0.5
                꼬 = ("" if 기회비 >= 0.5
                      else f"  ⚠️ **기회가 {기회비*100:.0f}% 로 줄었다 — 못 이긴 것으로 본다**")
                print(f"     ⇒ {'✅ **낫다**' if 이겼나 else '❌ 안 낫다'}"
                      f"  ({b[0]-a[0]:+.1f}%p · 기회 {기회비*100:.0f}%){꼬}")

    print("\n" + "=" * 122)
    print("  읽는 법")
    print("    - **E 가 답이다.** A·B 는 과거에 맞춘 것이라 늘 좋아 보인다")
    print("    - ⚠️⚠️ E 는 **기회 수를 같이 본다.** 기회가 절반 밑으로 줄면")
    print("      아무리 이김이 높아도 **못 이긴 것**이다 (원칙 ④: 매수 기회 포착 우선).")
    print("      2026-09-09 전에는 이김만 봐서 1년 42개짜리가 2,115개짜리를 이긴 것으로 찍혔다")
    print("    - C 에서 첫 재료가 한 곳에 몰리면 **나눌 까닭이 없다**")
    print("    - ⚠️ 단계적 고르기는 **과적합이 더 쉽다** — E 를 더 엄하게 본다")
    print("    - 「나눌 까닭 없음」이 답이어도 그게 답이다. 억지로 안 나눈다")
    print("=" * 122)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-09_185차_나누는법열가지.txt")

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
