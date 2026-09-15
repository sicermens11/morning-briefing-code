#!/usr/bin/env python3
r"""
newmat.py — **안 써본 재료 넷**을 사건에 붙인다 (2026-09-14 밤 신설)

## 왜
사용자: 「기존 규칙에 얹혀서 테스트 하는 게 아니라, **단독 재료로서의 효과**,
        다른 재료와의 **다양한 조합**일 때 효과를 측정해야 해」

163차(`combo4_lab.py`)가 정확히 그 틀이다 — 우리 규칙을 안 깔고 재료를 오분위로
잘라 A 하나씩 · B 둘씩(전수) · C 셋씩을 잰다. 거기에 **재료 이름만 늘리면**
새 재료도 단독·조합이 한 번에 재진다. 이 모듈이 그 재료를 만든다.

## 네 재료 (자료는 다 있는데 **한 번도 안 썼다** · field_audit 2026-09-14)
```
공시 시각    kind-time 4,110일 · 190만 건   장중에 뜬 공시 vs 장 끝난 뒤 뜬 공시
임원 매매    dart-exec 2,653종목            임원이 자기 회사 주식을 샀나
대주주 보고  dart-major 2,653종목           5% 이상 주주 지분율이 늘었나
뉴스 제목    news 2,418종목 · **1년치**      관심의 양 · 제목의 호재/악재 낱말
```

## ⚠️ 뉴스는 기간이 짧다
네이버 종목뉴스 API 가 **약 1년**만 준다(2026-09-14 실측). 10.4년 사건에 붙이면
90% 가 빈 값이라 `combo4_lab` 의 오분위가 **통째로 건너뛴다**.
⇒ 뉴스 재료는 `--최근1년` 으로 사건을 자른 판에서만 본다.

## 쓰는 법
```python
import newmat
붙은 = newmat.붙이기(사건, 날)        # 사건 dict 에 필드를 더한다. 붙은 재료 이름 목록을 준다
재료들 = 기존재료 + tuple(붙은)
```
"""
import bisect
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")

# ⚠️ 장 시간 (KRX 정규장). 15:30 뒤에 뜬 공시는 **다음 날** 값에 반영된다
_장시작, _장끝 = "09:00", "15:30"

# ⭐ 제목 낱말 — 뜻이 분명한 것만 고른다. 애매한 것(「전망」·「기대」)은 안 쓴다
# ⭐ 2026-09-15 넓혔다 — 13개·12개는 **손으로 적은 첫 판**이었다.
#    「뉴스호재5」가 바탕보다 나쁘게(41.5%) 나온 이유 하나가 이것일 수 있다:
#    호재인데 목록에 없어 안 잡히고, 애매한 말이 섞였다.
#    ⚠️ 뜻이 분명한 것만 넣는다 — 「전망」·「기대」·「추진」은 안 넣는다(방향이 없다)
_호재말 = ("수주", "계약 체결", "공급계약", "흑자전환", "최대 실적", "신고가",
          "자사주 취득", "무상증자", "특허", "임상 성공", "승인", "納品", "납품",
          # ⭐ 더한 것
          "사상 최대", "역대 최대", "어닝 서프라이즈", "실적 개선", "턴어라운드",
          "목표주가 상향", "투자의견 상향", "상향 조정", "수주 잔고",
          "국책 과제", "정부 지원", "독점 공급", "단독 공급", "대규모 공급",
          "품목허가", "식약처 허가", "FDA", "기술이전", "라이선스 아웃",
          "지분 취득", "경영권 인수", "무상감자 완료", "흑자 전환", "최대주주 변경")
_악재말 = ("적자", "감자", "횡령", "배임", "상장폐지", "거래정지", "소송",
          "유상증자", "관리종목", "불성실공시", "손실", "리콜",
          # ⭐ 더한 것
          "어닝 쇼크", "실적 부진", "영업손실", "당기순손실", "적자 전환",
          "목표주가 하향", "투자의견 하향", "하향 조정",
          "계약 해지", "수주 취소", "공급 중단", "리스크", "제재", "과징금",
          "압수수색", "검찰", "고소", "고발", "분식", "회계 의혹",
          "전환사채", "CB 발행", "BW 발행", "블록딜", "대량 매도", "지분 매각")


def _숫(s):
    """'10,149,093' → 10149093.0 · 빈 값이면 None"""
    if s is None:
        return None
    t = re.sub(r"[^\d.\-]", "", str(s))
    if not t or t in ("-", ".", "-."):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _날8(s):
    """'2026-08-25' → '20260825'"""
    return re.sub(r"[^\d]", "", str(s or ""))[:8]


# ── ① 공시 시각 ────────────────────────────────────────────────
def _공시시각표(날들):
    r"""날짜 -> {종목코드: (장중 건수, 장후 건수)}

    `dart-daily` 가 종목별 **접수번호**를 주고, `kind-time` 이 그 접수번호의 **시각**을 준다.
    둘을 이어야 「장중에 뜬 공시인가」를 알 수 있다 — 그동안 둘 다 있었는데 이은 적이 없다.
    """
    필요 = set(날들)
    표 = {}
    for f in sorted(glob.glob(os.path.join(_DATA, "dart-daily", "*.json"))):
        d8 = os.path.basename(f)[:8]
        if d8 not in 필요:
            continue
        try:
            dd = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        kt = os.path.join(_DATA, "kind-time", d8 + ".json")
        시각 = {}
        if os.path.exists(kt):
            try:
                시각 = (json.load(io.open(kt, encoding="utf-8-sig"))
                        .get("시각") or {})
            except ValueError:
                시각 = {}
        하루 = {}
        for 칸 in ("챙길공시", "그밖의공시"):
            챙 = 1 if 칸 == "챙길공시" else 0
            for x in (dd.get(칸) or []):
                code = str(x.get("종목코드") or "")
                번호 = str(x.get("접수번호") or "")
                if not code or not 번호:
                    continue
                t = str(시각.get(번호) or "")
                중, 후, 챙길 = 하루.get(code, (0, 0, 0))
                if not t:
                    pass                      # 시각을 모르면 어느 쪽에도 안 센다
                elif _장시작 <= t <= _장끝:
                    중 += 1
                else:
                    후 += 1
                # ⭐ 「챙길공시」 = 계약·실적·증자처럼 값에 닿는 것 · 「그밖」 = 주총 소집 등
                #    132차는 이 둘을 안 갈랐다 — 종류가 뜻을 가른다
                하루[code] = (중, 후, 챙길 + 챙)
        if 하루:
            표[d8] = 하루
    return 표


# ── ②③ 종목별 이력 (임원 매매 · 대주주 보고) ──────────────────
def _이력표(폴더, 값뽑기):
    """종목코드 -> (정렬된 날짜8 목록, 그 날의 값 목록)"""
    표 = {}
    for f in glob.glob(os.path.join(_DATA, 폴더, "*.json")):
        code = os.path.basename(f)[:-5]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        벌 = []
        for x in (j.get("이력") or []):
            d8 = _날8(x.get("접수일"))
            v = 값뽑기(x)
            if len(d8) == 8 and v is not None:
                벌.append((d8, v))
        if 벌:
            벌.sort()
            표[code] = ([z[0] for z in 벌], [z[1] for z in 벌])
    return 표


def _최근합(표, code, 날짜8, 일수, 날들, 자리):
    r"""`자리`(날 배열 인덱스)에서 **거래일 기준 `일수`만큼 거슬러** 올라가 합친다.

    ⚠️ 달력 일수가 아니라 **거래일**이다 — 사건이 거래일 기준이라 맞춰야 한다.
    """
    t = 표.get(code)
    if not t:
        return None
    시작 = 날들[max(0, 자리 - 일수)]
    ds, vs = t
    i = bisect.bisect_left(ds, 시작)
    j = bisect.bisect_right(ds, 날짜8)
    if i >= j:
        return 0.0
    return sum(vs[i:j])


def _컨센서스표():
    r"""종목코드 -> (정렬된 날짜8, 목표주가, 의견점수) — 2020~2026 · 81달

    ⚠️ 189차 때는 **2021~23 이 비어 있었다**(받는 중). 지금은 다 찼다(2026-09-14 확인) —
       그래서 그때 「표본 부족」으로 못 쟀던 목표주가·투자의견을 다시 잰다.
    의견은 말이 제각각이라(「매수」·「Buy」·「투자의견없음」) 점수로 바꾼다.
    """
    좋 = ("매수", "buy", "strongbuy", "적극매수", "outperform", "overweight")
    중 = ("중립", "hold", "neutral", "marketperform", "보유")
    나 = ("매도", "sell", "underperform", "underweight", "비중축소")
    표 = {}
    for f in sorted(glob.glob(os.path.join(_DATA, "consensus", "*.json"))):
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        for x in (j.get("리포트") or []):
            code = str(x.get("코드") or "")
            d8 = _날8(x.get("날짜"))
            if not code or len(d8) != 8:
                continue
            목 = _숫(x.get("목표주가"))
            if 목 is not None and 목 <= 0:
                목 = None                      # 「목표주가 0」은 의견 없음이다
            의 = str(x.get("의견") or "").strip().lower().replace(" ", "")
            점 = (1.0 if any(w in 의 for w in 좋) else
                  0.0 if any(w in 의 for w in 중) else
                  -1.0 if any(w in 의 for w in 나) else None)
            표.setdefault(code, []).append((d8, 목, 점))
    for code in 표:
        # ⚠️ 날짜로만 정렬한다 — 뒤 칸에 None 이 섞여 있어 튜플 비교가 터진다
        표[code].sort(key=lambda z: z[0])
    return 표


def _컨센재기(표, code, 날짜8, 일수, 날들, 자리, 주가):
    r"""(리포트 수, 목표주가 갭%, 의견 점수 평균) — 없으면 None

    목표주가 갭 = **목표주가가 지금 값보다 몇 % 위인가**. 클수록 「싸다」는 뜻이다
    (189차 E절이 재려던 것 · 그때는 표본이 모자랐다)
    """
    벌 = 표.get(code)
    if not 벌:
        return None
    시작 = 날들[max(0, 자리 - 일수)]
    ds = [z[0] for z in 벌]
    i = bisect.bisect_left(ds, 시작)
    j = bisect.bisect_right(ds, 날짜8)
    if i >= j:
        return (0, None, None)
    칸 = 벌[i:j]
    목들 = [z[1] for z in 칸 if z[1]]
    점들 = [z[2] for z in 칸 if z[2] is not None]
    갭 = None
    if 목들 and 주가 and 주가 > 0:
        갭 = (sum(목들) / len(목들) / 주가 - 1) * 100
    return (j - i, 갭, (sum(점들) / len(점들)) if 점들 else None)


def _증자표():
    r"""종목코드 -> {갈래: 정렬된 날짜8 목록}. 유상증자·무상증자·감자·자사주취득

    ⚠️ 236차가 「0건」으로 나온 적이 있다 — 구조를 잘못 읽어서였다(257차에서 재시험).
       여기서는 **접수번호 앞 8자리**를 날짜로 쓴다 (rcept_no = YYYYMMDD…)
    """
    갈래들 = ("유상증자", "무상증자", "유무상증자", "감자", "자사주취득")
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "dart-capital", "*.json")):
        code = os.path.basename(f)[:-5]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        하나 = {}
        for g in 갈래들:
            ds = []
            for x in (j.get(g) or []):
                d8 = str(x.get("rcept_no") or "")[:8]
                if len(d8) == 8 and d8.isdigit():
                    ds.append(d8)
            if ds:
                하나[g] = sorted(ds)
        if 하나:
            표[code] = 하나
    return 표


def _증자재기(표, code, 갈래, 날짜8, 일수, 날들, 자리):
    """그 갈래 공시가 최근 `일수` 거래일 안에 몇 건 있었나"""
    ds = (표.get(code) or {}).get(갈래)
    if not ds:
        return 0.0
    시작 = 날들[max(0, 자리 - 일수)]
    return float(bisect.bisect_right(ds, 날짜8) - bisect.bisect_left(ds, 시작))


def _ETF자금표(날들):
    r"""날짜8 -> (전체 ETF 거래대금 합, 시가총액 합) — **시장에 돈이 들어오나**

    ⚠️ ETF 는 종목별 재료가 아니라 **그날 시장 전체** 재료다. 사건의 날짜에 붙인다.
       246차는 ETF 를 「지수 대용 갭」으로만 썼다 — 자금 흐름은 한 번도 안 봤다.
    """
    필요 = set(날들)
    표 = {}
    for f in sorted(glob.glob(os.path.join(_DATA, "etf-krx", "*.json"))):
        d8 = os.path.basename(f)[:8]
        if d8 not in 필요:
            continue
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        대금 = 시총 = 0.0
        for v in (j.get("종목") or {}).values():
            a, b = _숫(v.get("거래대금")), _숫(v.get("시가총액"))
            if a:
                대금 += a
            if b:
                시총 += b
        if 대금 or 시총:
            표[d8] = (대금, 시총)
    return 표


def _국내거시표(날들):
    r"""날짜8 -> {이름: 값} — 국고채 금리 · 코스피200 선물 · 금 · 휘발유 (2010~2026)

    ⚠️ 자료재고에 「krx-extra 2024~2026 · 649일」로 적혀 있었는데 **틀렸다** —
       실제로는 국고채·선물 **4,109일**(2010~) · 일반상품 3,549일(2012~)이다
       (2026-09-14 밤 실측). 기간이 짧아 못 잰다던 재료가 사실 16.7년 다 있었다.
    ⚠️ 193차에서 잰 해외 재료(S&P500·구리·원달러·공포지수·반도체ETF)는 **전부 탈락**했다.
       국내 거시는 아직 한 번도 안 쟀다 — 그래서 여기 넣는다.
    """
    필요 = set(날들)
    표 = {}

    def 숫(x, k):
        return _숫((x or {}).get(k))

    for d8 in sorted(필요):
        하루 = {}
        # 국고채 — 지표 종목의 만기별 종가(값이 오르면 금리가 내린 것)
        p = os.path.join(_DATA, "krx-extra", "국고채", d8 + ".json")
        if os.path.exists(p):
            try:
                벌 = (json.load(io.open(p, encoding="utf-8-sig"))
                      .get("자료", {}).get("kts_bydd_trd") or [])
            except ValueError:
                벌 = []
            for x in 벌:
                if x.get("GOVBND_ISU_TP_NM") != "지표":
                    continue
                만기 = str(x.get("BND_EXP_TP_NM") or "")
                v = 숫(x, "CLSPRC")
                if 만기 in ("3", "10") and v:
                    하루[f"국고{만기}년"] = v
        # 선물 — 코스피200 정규장 종가
        p = os.path.join(_DATA, "krx-extra", "선물", d8 + ".json")
        if os.path.exists(p):
            try:
                벌 = (json.load(io.open(p, encoding="utf-8-sig"))
                      .get("자료", {}).get("fut_bydd_trd") or [])
            except ValueError:
                벌 = []
            for x in 벌:
                if (x.get("PROD_NM") == "코스피200 선물"
                        and x.get("MKT_NM") == "정규"):
                    v = 숫(x, "TDD_CLSPRC")
                    if v and "코스피200선물" not in 하루:
                        하루["코스피200선물"] = v
        # 일반상품 — 금 · 휘발유
        p = os.path.join(_DATA, "krx-extra", "일반상품", d8 + ".json")
        if os.path.exists(p):
            try:
                자 = json.load(io.open(p, encoding="utf-8-sig")).get("자료", {})
            except ValueError:
                자 = {}
            for x in (자.get("gold_bydd_trd") or []):
                v = 숫(x, "TDD_CLSPRC")
                if v and "금값" not in 하루:
                    하루["금값"] = v
            for x in (자.get("oil_bydd_trd") or []):
                if x.get("OIL_NM") == "휘발유":
                    v = 숫(x, "WT_AVG_PRC")
                    if v:
                        하루["휘발유"] = v
        if 하루:
            표[d8] = 하루
    return 표


def _배당표():
    r"""종목코드 -> (정렬된 해, 시가배당률) — dart-snap/배당 (2,651종목)

    ⚠️ 배당은 **해마다 한 번**이라 사건의 신호일 기준 **가장 최근 확정 해**를 쓴다.
    """
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "dart-snap", "배당", "*.json")):
        code = os.path.basename(f)[:-5]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        벌 = []
        for 해, 항목들 in (j.get("해별") or {}).items():
            for x in (항목들 or []):
                # ⚠️ 항목 이름은 `se`, 값은 `thstrm`(당기) — 2026-09-14 밤 실측으로 확인
                이름 = str(x.get("se") or "")
                if "주당 현금배당금" in 이름 and x.get("stock_knd") == "보통주":
                    v = _숫(x.get("thstrm"))
                    if v is not None:
                        벌.append((str(해), v))
                        break
        if 벌:
            벌.sort()
            표[code] = ([z[0] for z in 벌], [z[1] for z in 벌])
    return 표


def _소액주주표():
    """종목코드 -> (정렬된 해, 소액주주 지분율) — 유통 물량이 많을수록 높다"""
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "dart-snap", "소액주주", "*.json")):
        code = os.path.basename(f)[:-5]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        벌 = []
        for 해, 항목들 in (j.get("해별") or {}).items():
            for x in (항목들 or []):
                # `hold_stock_rate` 는 '66.04%' 꼴 — _숫 이 기호를 떼 준다
                v = _숫(x.get("hold_stock_rate"))
                if v is not None:
                    벌.append((str(해), v))
                    break
        if 벌:
            벌.sort()
            표[code] = ([z[0] for z in 벌], [z[1] for z in 벌])
    return 표


def _해값(표, code, 날짜8):
    """그 종목의 **신호일 이전 가장 최근 해** 값 — 없으면 None"""
    t = 표.get(code)
    if not t:
        return None
    해들, 값들 = t
    해 = 날짜8[:4]
    i = bisect.bisect_right(해들, 해) - 1
    return 값들[i] if i >= 0 else None


def _상장주식수():
    """종목코드 -> 상장주식수(float). 임원 매매를 종목 크기로 나누는 데 쓴다"""
    표 = {}
    p = os.path.join(_DATA, "stock-base.json")
    if not os.path.exists(p):
        return 표
    try:
        j = json.load(io.open(p, encoding="utf-8-sig"))
    except ValueError:
        return 표
    for c, v in (j.get("종목") or {}).items():
        n = _숫(v.get("상장주식수"))
        if n and n > 0:
            표[c] = n
    return 표


# ── ④ 뉴스 ────────────────────────────────────────────────────
def _뉴스표():
    """종목코드 -> (정렬된 날짜8, 호재점수, 악재점수) — 건수는 날짜 개수로 센다"""
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "news", "*.json")):
        code = os.path.basename(f)[:-5]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        벌 = []
        for x in (j.get("뉴스") or []):
            d8 = _날8(x.get("날짜"))
            if len(d8) != 8:
                continue
            제 = str(x.get("제목") or "")
            호 = sum(1 for w in _호재말 if w in 제)
            악 = sum(1 for w in _악재말 if w in 제)
            벌.append((d8, 호, 악))
        if 벌:
            벌.sort()
            표[code] = ([z[0] for z in 벌], [z[1] for z in 벌], [z[2] for z in 벌])
    return 표


def _뉴스재기(표, code, 날짜8, 일수, 날들, 자리):
    """(건수, 호재 수, 악재 수) — 없으면 None"""
    t = 표.get(code)
    if not t:
        return None
    시작 = 날들[max(0, 자리 - 일수)]
    ds, 호s, 악s = t
    i = bisect.bisect_left(ds, 시작)
    j = bisect.bisect_right(ds, 날짜8)
    return (j - i, sum(호s[i:j]), sum(악s[i:j]))


# ── ⑩ 분기 재무 (quarter-fin) ─────────────────────────────────
#
# ⚠️⚠️ **2026-09-14 밤에 찾았다.** `docs/자료재고.md` 에 **아예 없던 폴더**다.
#    `data_stock.py` 가 하위 폴더를 합쳐 세는 바람에 눈에 안 띄었다.
#
#      naver-quarter  종목당 **5분기뿐** (최근 1년)        <- 여태 이것만 썼다
#      quarter-fin    **43분기 x 2,073종목 x 13항목**      <- 2015~2026, 11.5년
#
#    분기 재무가 11년치면 4관문(앞뒤 분할·해마다 승패)에 걸 수 있다.
#
# ⚠️⚠️ **앞을 훔쳐보지 않게 늦춰서 쓴다.** 분기 재무는 분기가 끝나고 **45~90일 뒤**에
#    공시된다. 3월말 기준 1분기 실적을 4월 사건에 붙이면 **미래를 보는 것**이다.
#    법정 마감에 보름을 더 얹어 늦춘다:
#      1분기(3/31 기준) 마감 5/15  ->  6/01 부터 쓴다
#      반기 (6/30)      마감 8/14  ->  9/01
#      3분기(9/30)      마감 11/14 -> 12/01
#      사업 (12/31)     마감 3/31  ->  4/15  (다음 해)
#
# ⚠️ 반기·사업은 **누적**이다(반기 = 상반기 합). 그래서 크기를 그냥 비교하면 안 되고
#    **같은 분기끼리 작년과** 견준다. 비율(영업이익률 등)은 누적끼리라 괜찮다.
_분기열기 = {"1분기": (0, "0601"), "반기": (0, "0901"),
            "3분기": (0, "1201"), "사업": (1, "0415")}


def _분기재무표():
    """(차례대로 늘어선 (열리는날8, 해, 분기), 그 분기의 {종목: 항목들}) 목록"""
    벌 = []
    p = os.path.join(_DATA, "quarter-fin")
    if not os.path.isdir(p):
        return 벌
    for f in sorted(os.listdir(p)):
        if not f.endswith(".json"):
            continue
        해, _, 분기 = f[:-5].partition("_")
        늦, 날 = _분기열기.get(분기, (None, None))
        if 늦 is None or not 해.isdigit():
            continue
        try:
            j = json.load(io.open(os.path.join(p, f), encoding="utf-8-sig"))
        except ValueError:
            continue
        종목 = {c: v for c, v in (j.get("종목") or {}).items() if v}
        if not 종목:
            continue                       # 빈 분기 (2015 앞쪽 · 아직 안 온 분기)
        벌.append((f"{int(해) + 늦}{날}", 해, 분기, 종목))
    벌.sort()
    return 벌


def _재무값(칸, 이름):
    v = 칸.get(이름)
    return float(v) if isinstance(v, (int, float)) else None


# ⚠️⚠️ **나누는 밑이 너무 작으면 안 잰다** (2026-09-14 밤, 첫 시험에서 걸렸다).
#    매출이 거의 없는 회사(스팩·휴업·껍데기 지주사)가 섞이면 비율이 터진다:
#      영업이익률 **−60,057%** · 매출YoY **+119,219%** · 부채비율 **78,179%**
#    오분위는 순위로 자르니 결과를 뒤집지는 않지만, 이런 값은 **뜻이 없는 잡음**이라
#    위 20% 칸을 껍데기 회사가 채운다. 1억 원을 밑으로 둔다
_밑한계 = 1e8


def _분기지표(이제, 작년):
    """한 종목의 분기 재무 두 벌 → 재료 dict. 못 재는 것은 빼고 준다"""
    out = {}
    매 = _재무값(이제, "매출액")
    영 = _재무값(이제, "영업이익")
    순 = _재무값(이제, "당기순이익(손실)")
    부 = _재무값(이제, "부채총계")
    자 = _재무값(이제, "자본총계")
    쓸매 = 매 if (매 is not None and 매 >= _밑한계) else None
    쓸자 = 자 if (자 is not None and 자 >= _밑한계) else None
    # 비율 — 크기에 안 휘둘리게 전부 나눈 값으로 (임원 매매 때와 같은 이유)
    #
    # ⚠️⚠️ **이름 앞에 「분기」를 붙인다** (2026-09-15 새벽에 당했다).
    #    사건에는 이미 **연간** 재무에서 온 `영업이익률`·`순이익률` 이 들어 있다.
    #    같은 이름으로 넣으면 `x.update(값)` 이 **연간 값을 덮어쓴다** —
    #    R판에서 연간 두 재료가 통째로 사라졌고, 재료 목록엔 같은 이름이
    #    두 번 들어가 조건이 서로 덮였다. 한 글자 차이가 재료를 지운다
    if 쓸매:
        if 영 is not None:
            out["분기영업이익률"] = 영 / 쓸매 * 100
        if 순 is not None:
            out["분기순이익률"] = 순 / 쓸매 * 100
    if 쓸자:
        if 부 is not None:
            out["분기부채비율"] = 부 / 쓸자 * 100
        if 순 is not None:
            out["분기ROE"] = 순 / 쓸자 * 100
    if not 작년:
        return out
    매0 = _재무값(작년, "매출액")
    영0 = _재무값(작년, "영업이익")
    쓸매0 = 매0 if (매0 is not None and 매0 >= _밑한계) else None
    if 쓸매0 and 매 is not None:
        out["분기매출YoY"] = (매 / 쓸매0 - 1) * 100
    # ⚠️ 영업이익 증가율은 **부호가 뒤집히면 뜻이 없다** (-10억 → +5억 이 -150%).
    #    그래서 증가율 대신 **이익률 몇 %p 올랐나**로 잰다
    if 쓸매 and 쓸매0 and 영 is not None and 영0 is not None:
        out["분기영익률변화"] = (영 / 쓸매 - 영0 / 쓸매0) * 100
    # ⭐ 흑자전환은 밑이 필요 없다 — 부호만 본다
    if 영 is not None and 영0 is not None:
        out["분기흑자전환"] = 1.0 if (영0 < 0 <= 영) else 0.0
    자0 = _재무값(작년, "자본총계")
    부0 = _재무값(작년, "부채총계")
    쓸자0 = 자0 if (자0 is not None and 자0 >= _밑한계) else None
    if 쓸자 and 쓸자0 and 부 is not None and 부0 is not None:
        out["분기부채비율변화"] = (부 / 쓸자 - 부0 / 쓸자0) * 100
    return out


# ── ⑪ 단일종목선물 (krx-extra) ────────────────────────────────
#
# ⚠️⚠️ **2026-09-14 밤에 찾았다.** 자료재고가 krx-extra 를 「2024~2026 · 1,947일」
#    이라 적어 뒀는데 실제로는 **2010~2026** 이고, 그 안에 **단일종목선물**이
#    하루 1,900줄씩 들어 있다. 한 번도 안 썼다.
#
#    여기서 나오는 것 둘:
#      베이시스   (선물값 − 현물값)/현물값 — 선물이 비싸면 **사자 우위**
#      미결제약정 ACC_OPNINT_QTY — 새 돈이 들어오나
#
# ⚠️⚠️ **덮는 범위가 좁다.** 기초자산이 2012년 25종목 → 2026년 284종목뿐이고,
#    **다 대형주다.** 우리 후보는 「재무 우량 **소형주**」라 대부분 빈 값이 된다.
#    combo4_lab 의 오분위는 30% 미만이면 그 재료를 통째로 건너뛴다 —
#    **건너뛰는 것도 답이다.** 「안 재고 통과」보다 낫다
_선물폴더 = ("주식선물유가", "주식선물코스닥")


def _이름코드표():
    """종목 이름 → 코드 (선물 PROD_NM 이 이름이라 이어줘야 한다)"""
    표 = {}
    p = os.path.join(_DATA, "stock-base.json")
    if not os.path.exists(p):
        return 표
    try:
        j = json.load(io.open(p, encoding="utf-8-sig"))
    except ValueError:
        return 표
    for c, v in (j.get("종목") or {}).items():
        n = str(v.get("이름") or "").strip()
        if n:
            표.setdefault(n, c)
            표.setdefault(n.replace(" ", ""), c)
    return 표


def _선물표(날들):
    """날짜8 → {종목코드: (베이시스%, 미결제약정)}

    ⚠️ 한 기초자산에 **달마다 다른 물**이 여럿 있다. 거래량이 가장 많은 것
       (=최근월물) 하나만 쓴다 — 멀리 있는 달은 거래가 거의 없어 값이 튄다
    """
    이름표 = _이름코드표()
    if not 이름표:
        return {}
    필요 = set(날들)
    표 = {}
    for 종 in _선물폴더:
        p = os.path.join(_DATA, "krx-extra", 종)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            d8 = f[:8]
            if d8 not in 필요 or not f.endswith(".json"):
                continue
            try:
                j = json.load(io.open(os.path.join(p, f), encoding="utf-8-sig"))
            except ValueError:
                continue
            자료 = j.get("자료")
            줄들 = None
            if isinstance(자료, dict):
                for v in 자료.values():
                    if isinstance(v, list):
                        줄들 = v
                        break
            elif isinstance(자료, list):
                줄들 = 자료
            if not 줄들:
                continue
            하루 = 표.setdefault(d8, {})
            고른것 = {}
            for x in 줄들:
                이름 = str(x.get("PROD_NM") or "").replace(" 선물", "").strip()
                code = 이름표.get(이름) or 이름표.get(이름.replace(" ", ""))
                if not code:
                    continue               # ETF 선물 등 — 종목이 아니다
                량 = _숫(x.get("ACC_TRDVOL")) or 0.0
                if 량 <= (고른것.get(code, (-1,))[0]):
                    continue
                고른것[code] = (량, x)
            for code, (_, x) in 고른것.items():
                현 = _숫(x.get("SPOT_PRC"))
                선 = _숫(x.get("SETL_PRC")) or _숫(x.get("TDD_CLSPRC"))
                미 = _숫(x.get("ACC_OPNINT_QTY"))
                if 현 and 현 > 0 and 선:
                    하루[code] = ((선 / 현 - 1) * 100, 미 or 0.0)
    return 표


# ── ⑫ 수주 계약 공시 (contract) ───────────────────────────────
#
# ⚠️⚠️ **2026-09-14 밤에 찾았다 — 여기도 빠져 있었다.**
#    「단일판매ㆍ공급계약」 공시가 **2010.01~2026.09 · 55,048건** 있는데
#    이 단독/조합 시험(R·S·U판)에 **한 번도 안 들어갔다.**
#    옛 시험(omni_lab·signal_map2)은 이걸 「0건 · 파싱 실패」로 쟀다 —
#    리스트인 줄 알았는데 실제로는 **딕셔너리**였다.
#
# ⭐ 수주는 「이 종목을 지금 사면 오르나」에 가장 곧바로 닿는 재료다.
#    ⚠️ 다만 **금액 그대로는 못 쓴다** — 삼성전자 1조와 소형주 1조는 뜻이 다르다.
#       공시가 주는 `매출대비pct` (계약금액이 작년 매출의 몇 %인가) 를 쓴다
#    ⚠️ **「해지」 공시가 섞여 있다** — 그건 호재가 아니라 악재다. 갈라서 센다
def _수주표():
    """종목코드 → (정렬된 날짜8, 매출대비pct, 해지인가)"""
    벌 = {}
    p = os.path.join(_DATA, "contract")
    if not os.path.isdir(p):
        return {}
    for f in sorted(os.listdir(p)):
        if not f.endswith(".json"):
            continue
        try:
            j = json.load(io.open(os.path.join(p, f), encoding="utf-8-sig"))
        except ValueError:
            continue
        for x in (j.get("건") or {}).values():
            code = str(x.get("코드") or "")
            d8 = _날8(x.get("날짜"))
            if not code or len(d8) != 8:
                continue
            이름 = str(x.get("공시명") or "")
            벌.setdefault(code, []).append(
                (d8, _숫(x.get("매출대비pct")) or 0.0, "해지" in 이름))
    표 = {}
    for c, v in 벌.items():
        v.sort()
        표[c] = ([z[0] for z in v], [z[1] for z in v], [z[2] for z in v])
    return 표


def _수주재기(표, code, 날짜8, 일수, 날들, 자리):
    """(체결 건수, 매출대비% 합, 해지 건수) — 없으면 None"""
    t = 표.get(code)
    if not t:
        return None
    시작 = 날들[max(0, 자리 - 일수)]
    ds, 비s, 해s = t
    i = bisect.bisect_left(ds, 시작)
    j = bisect.bisect_right(ds, 날짜8)
    건, 비, 해 = 0, 0.0, 0
    for k in range(i, j):
        if 해s[k]:
            해 += 1
        else:
            건 += 1
            비 += 비s[k]
    return (건, 비, 해)


# ── 붙이기 ─────────────────────────────────────────────────────
def 붙이기(사건, 날들, 뉴스포함=True, 찍기=print):
    r"""사건 dict 에 새 재료를 더하고 **붙은 재료 이름 목록**을 돌려준다.

    사건은 `{"인": <날 배열 자리>, "code": ...}` 를 들고 있어야 한다.
    ⚠️ 「인」은 **매수일** 자리다(신호 다음 날). 재료는 **신호일(인-1)** 까지만 본다 —
       매수일 아침에 알 수 있는 것만 써야 앞을 훔쳐보지 않는다
    """
    붙은 = []
    if not 사건:
        return 붙은
    # ⚠️⚠️ **덮어쓰기를 막는 자리다** (2026-09-15 새벽 · R판에서 당했다).
    #    사건에는 이미 연간 재무에서 온 `영업이익률`·`순이익률` 이 들어 있었는데
    #    분기 재무를 같은 이름으로 넣어 `x.update(값)` 이 그걸 **덮어썼다.**
    #    재료 목록에도 같은 이름이 두 번 들어가 조건이 서로 덮였다.
    #    오류도 안 나고 결과는 그럴듯했다 — **「안 재고 통과」가 제일 나쁘다**
    #    ⇒ 49분짜리 판을 돌리기 **전에** 터뜨린다
    _원래키 = set(사건[0])
    for x in 사건[:200]:
        _원래키 |= set(x)

    # ① 공시 시각
    찍기("    공시 시각(kind-time × dart-daily) 잇는 중...")
    공시 = _공시시각표(날들)
    if 공시:
        for x in 사건:
            i = x["인"] - 1                      # 신호일
            d8 = 날들[i] if 0 <= i < len(날들) else None
            중, 후, 챙 = ((공시.get(d8) or {}).get(x["code"], (0, 0, 0))
                        if d8 else (0, 0, 0))
            x["공시장중"] = float(중)
            x["공시장후"] = float(후)
            x["공시건수"] = float(중 + 후)
            x["챙길공시"] = float(챙)
        붙은 += ["공시장중", "공시장후", "공시건수", "챙길공시"]
        찍기(f"      {len(공시):,}일 · 사건에 붙임")

    # ② 임원 매매 — 증감 주수를 **상장주식수 대비 %** 로
    #    ⚠️ 주수 그대로 두면 오분위 위 20% 를 대형주가 독식한다 —
    #       삼성전자 5,000주와 소형주 5,000주는 뜻이 다르다
    찍기("    임원 매매(dart-exec) 붙이는 중...")
    주식수 = _상장주식수()
    임원 = _이력표("dart-exec", lambda x: _숫(x.get("증감")))
    if 임원:
        for x in 사건:
            i = x["인"] - 1
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if not d8:
                continue
            발 = 주식수.get(x["code"])
            for 일, 이름 in ((20, "임원매수율20"), (60, "임원매수율60")):
                v = _최근합(임원, x["code"], d8, 일, 날들, i)
                if v is not None and 발:
                    x[이름] = v / 발 * 100
                elif v is not None:
                    x[이름] = 0.0
        붙은 += ["임원매수율20", "임원매수율60"]
        찍기(f"      {len(임원):,}종목 · 상장주식수 {len(주식수):,}개로 정규화")

    # ③ 대주주 — 지분율 **증감** 합
    찍기("    대주주 보고(dart-major) 붙이는 중...")
    def _지분변화(x):
        # ⚠️⚠️ 「직전지분율」은 **이름이 잘못 붙은 것**이다 (2026-09-14 밤 발견).
        #    DART `stkrt_irds` 는 increase/decrease = **증감**이라 그대로 쓴다.
        #    「지분율 − 직전지분율」로 읽으면 20.08 − 0.00 이 매번 더해져
        #    대주주 변화가 **141%p** 로 나왔다 (collect_major.py 도 같이 고쳤다)
        v = _숫(x.get("증감지분율"))
        return v if v is not None else _숫(x.get("직전지분율"))
    대주주 = _이력표("dart-major", _지분변화)
    if 대주주:
        for x in 사건:
            i = x["인"] - 1
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if d8:
                x["대주주변화60"] = _최근합(대주주, x["code"], d8, 60, 날들, i)
        붙은 += ["대주주변화60"]
        찍기(f"      {len(대주주):,}종목")

    # ④ 뉴스 — 1년치뿐이라 기본은 붙이되, 오분위에서 걸러진다
    if 뉴스포함:
        찍기("    뉴스(news) 붙이는 중...")
        뉴스 = _뉴스표()
        if 뉴스:
            # ⭐⭐ **평소 대비** (2026-09-15 · 사용자 지적).
            #    지금은 「뉴스 5건」을 **절대 수**로 본다. 그런데 평소 0건인 종목의
            #    5건과 평소 20건인 종목의 5건은 **뜻이 정반대**다.
            #    ⇒ 「그 종목 **평소의 몇 배**인가」를 같이 넣는다.
            #    어젯밤 「뉴스5↑」가 바탕보다 나빴던(40.9%) 이유가 이것일 수 있다 —
            #    절대 수로는 「큰 회사라 원래 기사가 많다」와 구별이 안 된다
            _평소 = {c9: (len(t9[0]) / 250.0) for c9, t9 in 뉴스.items()}
            for x in 사건:
                i = x["인"] - 1
                d8 = 날들[i] if 0 <= i < len(날들) else None
                if not d8:
                    continue
                a = _뉴스재기(뉴스, x["code"], d8, 5, 날들, i)
                b = _뉴스재기(뉴스, x["code"], d8, 20, 날들, i)
                if a:
                    x["뉴스5"], x["뉴스호재5"], x["뉴스악재5"] = (
                        float(a[0]), float(a[1]), float(a[2]))
                    # ⚠️⚠️ **뉴스가 있을 때만 넣는다** (2026-09-15 오후에 당했다).
                    #    처음엔 `_pm > 0` 만 보고 **건수가 0 이어도 0 을 넣었다.**
                    #    그러면 대부분이 0 이라 오분위가 「한 곳에 몰렸다 →
                    #    0 보다 큰가」로 갈리고, 결국 **`뉴스5↑` 와 똑같은 조건**이 됐다.
                    #    (실측: 뉴스5↑ 40.9% · 뉴스평소배↑ **40.8%** — 같은 것을 두 번 잰 셈)
                    #    ⇒ 「평소의 **몇 배**」라는 뜻이 살려면 **뉴스가 있는 사건 안에서**
                    #      오분위가 갈려야 한다
                    #    ⚠️ 그러면 값이 있는 사건이 10.4년 판에서 5% 뿐이라 건너뛴다 —
                    #       **1년 판**에서만 뜻이 산다
                    _pm = _평소.get(x["code"]) or 0.0
                    if _pm > 0 and a[0] > 0:
                        x["뉴스평소배"] = (a[0] / 5.0) / _pm
                if b:
                    x["뉴스20"] = float(b[0])
            붙은 += ["뉴스5", "뉴스20", "뉴스호재5", "뉴스악재5", "뉴스평소배"]
            찍기(f"      {len(뉴스):,}종목 (⚠️ 약 1년치 — 옛 사건은 빈 값)")

    # ⑤ 컨센서스 — 189차가 「리포트 유무」만 쟀다. 목표주가·의견은 그때 표본 부족이었고
    #    2021~23 이 비어 있었다. **지금은 81달이 다 찼다** (2026-09-14 확인)
    찍기("    컨센서스(consensus) 붙이는 중...")
    컨 = _컨센서스표()
    if 컨:
        for x in 사건:
            i = x["인"] - 1
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if not d8:
                continue
            r = _컨센재기(컨, x["code"], d8, 90, 날들, i, x.get("주가"))
            if r is None:
                continue
            x["리포트90"] = float(r[0])
            if r[1] is not None:
                x["목표주가갭"] = r[1]
            if r[2] is not None:
                x["투자의견"] = r[2]
            # ⭐⭐ **수준이 아니라 «변화»** (2026-09-15 · 사용자 지적).
            #    여태 잰 것은 「목표가가 지금 주가보다 몇 % 위인가」= **수준**이다.
            #    실전에서 촉매로 알려진 것은 **「목표가가 올랐나 내렸나」**다.
            #    ⚠️ 덮는 범위가 낮을 것이다 — 우리 후보는 시총 300~2,000억 소형주라
            #       리포트가 거의 없다(어젯밤 목표주가갭이 **10%** 만 붙어 건너뛰었다).
            #       그래도 **재고 나서** 접는다. 「안 재고 통과」가 제일 나쁘다
            _벌9 = 컨.get(x["code"]) or []
            _최근 = [z for z in _벌9 if z[0] <= d8][-6:]
            _목9 = [z[1] for z in _최근 if z[1]]
            if len(_목9) >= 2 and _목9[-2]:
                x["목표주가변화"] = (_목9[-1] / _목9[-2] - 1) * 100
            _의9 = [z[2] for z in _최근 if z[2] is not None]
            if len(_의9) >= 2:
                x["투자의견변화"] = _의9[-1] - _의9[-2]
        붙은 += ["리포트90", "목표주가갭", "투자의견",
                "목표주가변화", "투자의견변화"]
        찍기(f"      {len(컨):,}종목 · 2020~2026")

    # ⑥ 증자·감자·자사주 — 236차가 「0건」으로 나왔던 것(구조를 잘못 읽었다)
    찍기("    증자·감자·자사주(dart-capital) 붙이는 중...")
    증자 = _증자표()
    if 증자:
        짝 = (("유상증자", "유상증자60"), ("무상증자", "무상증자60"),
              ("감자", "감자60"), ("자사주취득", "자사주60"))
        for x in 사건:
            i = x["인"] - 1
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if not d8:
                continue
            for 갈, 이름 in 짝:
                x[이름] = _증자재기(증자, x["code"], 갈, d8, 60, 날들, i)
        붙은 += [z[1] for z in 짝]
        찍기(f"      {len(증자):,}종목")

    # ⑦ ETF 자금 — **그날 시장 전체**. 246차는 ETF 를 지수 대용으로만 썼다
    찍기("    ETF 자금 흐름(etf-krx) 붙이는 중...")
    etf = _ETF자금표(날들)
    if etf:
        순 = [etf.get(d) for d in 날들]
        for x in 사건:
            i = x["인"] - 1
            if not (0 <= i < len(날들)) or not 순[i]:
                continue
            대금, 시총 = 순[i]
            # 20 거래일 평균 대비 오늘 ETF 거래대금 (시장에 돈이 몰리나)
            앞 = [순[j][0] for j in range(max(0, i - 19), i + 1) if 순[j]]
            if 앞 and sum(앞) > 0:
                x["ETF대금배수"] = 대금 / (sum(앞) / len(앞))
            # 20 거래일 전 대비 ETF 전체 시가총액 변화율 (자금 유입)
            j0 = i - 20
            if j0 >= 0 and 순[j0] and 순[j0][1] > 0:
                x["ETF시총20"] = (시총 / 순[j0][1] - 1) * 100
        붙은 += ["ETF대금배수", "ETF시총20"]
        찍기(f"      {len(etf):,}일")

    # ⑧ 국내 거시 — 국고채 금리 · 코스피200 선물 · 금 · 휘발유 (2010~2026)
    #    ⚠️ 193차가 잰 해외 재료(S&P500·구리·원달러·공포지수·반도체ETF)는 **전부 탈락**했다.
    #       국내 거시는 한 번도 안 쟀다. 종목이 아니라 **그날 시장 전체** 재료다
    찍기("    국내 거시(국고채·선물·금·휘발유) 붙이는 중...")
    거시 = _국내거시표(날들)
    if 거시:
        벌 = [거시.get(d) or {} for d in 날들]
        이름들 = ("국고3년", "국고10년", "코스피200선물", "금값", "휘발유")
        for x in 사건:
            i = x["인"] - 1
            if not (0 <= i < len(날들)):
                continue
            이제, 전 = 벌[i], (벌[i - 20] if i >= 20 else {})
            for 이 in 이름들:
                a, b = 이제.get(이), 전.get(이)
                if a and b and b > 0:
                    x[f"{이}20"] = (a / b - 1) * 100     # 20 거래일 변화율
        붙은 += [f"{이}20" for 이 in 이름들]
        찍기(f"      {len(거시):,}일")

    # ⑨ 배당 · 소액주주 — dart-snap (⚠️ **2024~2025 두 해뿐**)
    #    10.4년 사건에 붙이면 19% 라 오분위(30% 문턱)가 건너뛴다 — `--최근N년` 판에서만 산다
    찍기("    배당·소액주주(dart-snap) 붙이는 중...")
    배당 = _배당표()
    소액 = _소액주주표()
    if 배당 or 소액:
        for x in 사건:
            i = x["인"] - 1
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if not d8:
                continue
            v = _해값(배당, x["code"], d8)
            if v is not None and x.get("주가"):
                # 주당 배당금을 **주가로 나눠** 배당수익률(%)로 — 크기에 안 휘둘리게
                x["배당수익률"] = v / x["주가"] * 100
            v2 = _해값(소액, x["code"], d8)
            if v2 is not None:
                x["소액주주지분"] = v2
        붙은 += ["배당수익률", "소액주주지분"]
        찍기(f"      배당 {len(배당):,}종목 · 소액주주 {len(소액):,}종목 "
             "(⚠️ 2024~2025 두 해뿐)")

    # ⑩ 분기 재무 — **11.5년치**. 09-14 밤에 찾은 quarter-fin (위 설명 참고)
    #    ⚠️ 늦춰서 쓴다 — 3월말 실적을 4월 사건에 붙이면 미래를 보는 것이다
    찍기("    분기 재무(quarter-fin) 붙이는 중...")
    분기들 = _분기재무표()
    if 분기들:
        열린날 = [z[0] for z in 분기들]
        # (해, 분기) → 차례 — 「작년 같은 분기」를 찾으려고
        자리표 = {(z[1], z[2]): i for i, z in enumerate(분기들)}
        # ⚠️ 전부 **「분기」로 시작한다** — 사건에 이미 연간 `영업이익률`·`순이익률`
        #    이 있어서, 같은 이름을 쓰면 `x.update()` 가 그걸 지운다 (2026-09-15)
        이름들 = ("분기영업이익률", "분기순이익률", "분기부채비율", "분기ROE",
                  "분기매출YoY", "분기영익률변화", "분기흑자전환",
                  "분기부채비율변화")
        닿은것 = 0
        for x in 사건:
            i = x["인"] - 1                  # 신호일
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if not d8:
                continue
            # 그날 **이미 공시돼 있던** 가장 최근 분기
            k = bisect.bisect_right(열린날, d8) - 1
            if k < 0:
                continue
            _, 해, 분기, 종목 = 분기들[k]
            이제 = 종목.get(x["code"])
            if not 이제:
                continue
            j = 자리표.get((str(int(해) - 1), 분기))
            작년 = 분기들[j][3].get(x["code"]) if j is not None else None
            값 = _분기지표(이제, 작년)
            if 값:
                x.update(값)
                닿은것 += 1
        붙은 += list(이름들)
        찍기(f"      분기 {len(분기들)}개 ({분기들[0][1]}~{분기들[-1][1]}) · "
             f"사건 {닿은것:,}건에 붙음")

    # ⑪ 단일종목선물 — 베이시스·미결제약정 (위 설명 참고)
    #    ⚠️ 대형주에만 있다. 소형주 후보는 대부분 빈 값 → 오분위가 건너뛸 수 있다
    찍기("    단일종목선물(krx-extra) 붙이는 중...")
    선물 = _선물표(날들)
    if 선물:
        주식수2 = 주식수 or _상장주식수()
        닿은것 = 0
        for x in 사건:
            i = x["인"] - 1
            if not (0 <= i < len(날들)):
                continue
            이제 = (선물.get(날들[i]) or {}).get(x["code"])
            if not 이제:
                continue
            베, 미 = 이제
            x["선물베이시스"] = 베
            발 = 주식수2.get(x["code"])
            if 발:
                # 미결제약정을 **상장주식수로 나눠** 크기를 지운다
                x["선물미결제율"] = 미 / 발 * 100
            # 20 거래일 전 대비 미결제약정 변화 — 새 돈이 들어왔나
            j = i - 20
            옛 = (선물.get(날들[j]) or {}).get(x["code"]) if j >= 0 else None
            if 옛 and 옛[1] > 0:
                x["선물미결제20"] = (미 / 옛[1] - 1) * 100
            닿은것 += 1
        붙은 += ["선물베이시스", "선물미결제율", "선물미결제20"]
        덮 = 닿은것 / len(사건) * 100 if 사건 else 0
        찍기(f"      {len(선물):,}일 · 사건 {닿은것:,}건에 붙음 "
             f"(덮는 범위 {덮:.0f}% — ⚠️ 대형주에만 있다)")

    # ⑫ 수주 계약 — 16.7년치. 옛 시험이 「0건」으로 쟀던 것 (위 설명 참고)
    찍기("    수주 계약(contract) 붙이는 중...")
    수주 = _수주표()
    if 수주:
        for x in 사건:
            i = x["인"] - 1
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if not d8:
                continue
            for 일, 꼬리 in ((20, "20"), (60, "60")):
                r = _수주재기(수주, x["code"], d8, 일, 날들, i)
                if r is None:
                    r = (0, 0.0, 0)      # 자료는 있는데 이 종목엔 수주가 없다 = 0건
                x[f"수주건수{꼬리}"] = float(r[0])
                x[f"수주매출비{꼬리}"] = r[1]
            x["수주해지60"] = float(
                (_수주재기(수주, x["code"], d8, 60, 날들, i) or (0, 0, 0))[2])
        붙은 += ["수주건수20", "수주매출비20", "수주건수60", "수주매출비60",
                "수주해지60"]
        찍기(f"      {len(수주):,}종목 · 2010~2026")

    # ── 덮어쓰기 검사 (위 `_원래키` 설명 참고) ──────────────────
    겹침 = sorted(set(붙은) & _원래키)
    겹겹 = sorted({n for n in 붙은 if 붙은.count(n) > 1})
    if 겹침 or 겹겹:
        말 = []
        if 겹침:
            말.append(f"사건에 **이미 있던** 이름을 덮어썼다: {', '.join(겹침)}")
        if 겹겹:
            말.append(f"새 재료끼리 이름이 겹친다: {', '.join(겹겹)}")
        raise SystemExit(
            "\n⚠️⚠️ **재료 이름이 겹친다 — 판을 안 돌린다**\n   "
            + "\n   ".join(말)
            + "\n   이대로 두면 재료 하나가 조용히 **사라진다.**"
            "\n   `newmat.py` 에서 이름 앞에 「분기」처럼 갈래를 붙여라\n")
    찍기(f"    ✅ 이름 겹침 없음 — 새 재료 {len(붙은)}가지")
    return 붙은


if __name__ == "__main__":
    print(__doc__)
