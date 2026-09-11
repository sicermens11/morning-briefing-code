#!/usr/bin/env python3
"""
fetch_us.py — 미국 시장 데이터 직접 수집 (2026-08-25 신설)

대체 대상 (전부 MCP 호출 0회로 전환):
  - MCP-2   미 국채 2년·10년       ← FMP-economics
  - MCP-2.5/3/4  VIX·SPY·나스닥100  ← bigdata_market_tearsheet
  - 검색2c-A  미국 11개 섹터 등락률   ← FMP-marketPerformance
  - 검색2a   D-7 실적 캘린더        ← FMP-calendar

출처(전부 키 불필요):
  - 국채금리: 미 재무부 공식 일별 수익률 곡선 CSV
  - 지수·ETF: Yahoo Finance chart API
  - 실적:     NASDAQ 공개 실적 캘린더 API

⚠️ 등락률은 `chartPreviousClose`를 쓰지 않는다.
   그 필드는 조회 구간(range) 시작 이전의 종가라, 5일 구간을 요청하면 "5일 전 대비"가 된다.
   2026-08-25 실측에서 S&P500이 -0.28%(실제)가 아니라 -1.19%로 나왔다.
   → **종가 시계열의 마지막 두 값**으로 직접 계산한다.

사용:
    run-py.ps1 -Script fetch_us.py                     # 전체
    run-py.ps1 -Script fetch_us.py -Args @('--earnings-days','7')
"""
import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

import concurrent.futures as cf

KST = timezone(timedelta(hours=9))
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 미국 11개 섹터 대표 ETF (SPDR). 검색2c-A가 주던 "섹터별 전일 등락률"을 이걸로 만든다.
SECTOR_ETF = {
    "XLK": "기술", "XLF": "금융", "XLV": "헬스케어", "XLE": "에너지",
    "XLI": "산업재", "XLY": "임의소비재", "XLP": "필수소비재",
    "XLU": "유틸리티", "XLB": "소재", "XLRE": "부동산", "XLC": "커뮤니케이션",
}

# ⚠️⚠️ **다우가 빠져 있었다** (2026-09-11 사용자 지적: 「생각해보니까 다우존스
#    지수가 없었네..」). 확인해 보니 `data/us-index.json`(옛 수집기)에는 다우가
#    있는데 그 파일은 **2026-09-01에 멈췄고**, 지금 쓰는 이 수집기는 애초에
#    목록에 다우를 안 넣었다. 그래서 브리핑 어디에도 다우가 안 나왔다.
#    ⇒ `^DJI`(URL 인코딩 `%5EDJI`)를 더한다
INDICES = {"%5EGSPC": "S&P500", "%5ENDX": "나스닥100", "%5EDJI": "다우",
           "%5EVIX": "VIX", "SPY": "SPY"}

# 선물·원자재 (2026-08-26 신설).
# ⚠️ 이게 08:00 브리핑에 특히 중요한 이유: 미국 **현물장은 닫혀 있지만 선물은 열려 있다.**
#    지수 종가는 어젯밤 이야기고, 선물은 지금 이 순간 값이다 — "오늘 미국이 어떻게 열릴 것 같은가"를
#    유일하게 말해주는 숫자다. 원자재는 조선·화학·전력·방산 섹터 해석에 바로 붙는다.
#    2026-08-26 실측에서 WTI가 -5.07%였는데 브리핑엔 그 사실이 통째로 빠져 있었다.
FUTURES = {
    "ES%3DF": "S&P500 선물", "NQ%3DF": "나스닥100 선물",
    "CL%3DF": "WTI 원유", "HG%3DF": "구리", "GC%3DF": "금",
    "DX-Y.NYB": "달러인덱스",
    # 원/달러 (2026-08-26 추가). 한국은행 ECOS의 대체재로 골랐다 — ECOS는 **API 키가 필요**한데
    # 야후는 이미 이 파일이 쓰는 소스라 새 의존성도 키도 없다.
    # ⚠️ 이건 **시장 환율**이지 한국은행 **매매기준율**이 아니다(매매기준율은 전일 은행간
    #    거래 가중평균이라 값이 다르다 — 2026-08-26 실측 1,385.38 vs 1,380.60).
    #    서술할 때 "매매기준율"이라 쓰지 말 것. 중요한 건 정확한 절대값보다
    #    **매일 같은 출처를 써서 전일 대비 변화를 일관되게 보는 것**이다.
    #    (2026-08-21에 한 브리핑 안에서 1,402.50 / 1,380.9 / 1,393.00 세 값이 갈린 적이 있다.)
    "USDKRW%3DX": "원/달러(시장환율)",
}

# 해외 벤치마크 (2026-08-26 신설 — 구 MCP-GLOBAL 4종을 뉴스검색에서 실제 시세로 대체).
# ⚠️ 기각 이력이 뒤집힌 항목이다. DECISIONS.md에 "FMP 페이월로 대만·중국 등 개별 티커 대부분
#    ACCESS DENIED — Exa 뉴스검색이 유일한 비페이월 경로"로 남아 있었으나, 야후는 전부 무료다.
#    뉴스 해석("중국 조선 수주 강세라더라")이 아니라 **숫자**로 판단하게 된다.
GLOBAL_BENCH = {
    "2330.TW": ("TSMC", "반도체"),
    "300750.SZ": ("CATL", "2차전지"),
    "RHM.DE": ("라인메탈", "방산"),
    "600150.SS": ("중국선박(CSSC)", "조선"),
}


def get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _bar_date(t):
    """일봉 타임스탬프 → 날짜 문자열. 야후 일봉은 개장 시각(UTC)으로 찍힌다."""
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")


def yahoo_daily(symbol: str):
    r"""마지막 두 거래일 종가로 등락률을 계산한다.

    ⚠️⚠️ **종가와 타임스탬프를 반드시 함께 거른다** (2026-08-31 사고로 확정).
       예전 코드는 `closes`에서만 `None`을 걸러내고 `ts`는 그대로 뒀다. 그래서 마지막 봉의
       종가가 비어 있으면 **직전 종가에 최신 날짜가 붙었다.**
       실제로 08-31 아침에 08-27 종가(7730.99)가 **"08-28 기준"으로** 나갔고,
       금요일 브리핑과 숫자가 한 글자도 다르지 않았다. 사용자가 "어젯밤 미국 흐름이
       금요일이랑 같다"고 잡아냈다.
       ⚠️ **틀린 값보다 나쁜 게 틀린 날짜다.** 값이 이상하면 눈에 띄지만,
          날짜만 바뀐 옛날 값은 **새 정보처럼 읽힌다.**

    ⚠️ **일봉이 비어도 `meta`에는 있다.** 2026-08-31 확인: 8개 종목 전부 금요일 일봉이
       `None`이었는데 `meta.regularMarketPrice`에는 금요일 종가가 들어 있었다.
       그래서 meta가 일봉보다 최신이면 **한 봉으로 이어 붙인다.**
       ⚠️ 단 **미국 장중에는 안 붙인다**(`marketState`가 `REGULAR`면 그건 종가가 아니라
          움직이는 값이다). 08:00 KST엔 늘 닫혀 있지만, 사람이 낮에 돌릴 수도 있다.
    """
    d = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/"
                       f"{symbol}?interval=1d&range=10d"))
    res = d["chart"]["result"][0]
    meta = res.get("meta") or {}
    ts = res.get("timestamp") or []
    raw = res["indicators"]["quote"][0]["close"]
    # ⚠️ zip으로 **짝을 지어** 거른다. 따로 거르면 짝이 어긋난다.
    bars = [(t, c) for t, c in zip(ts, raw) if c is not None]

    rmt, rmp = meta.get("regularMarketTime"), meta.get("regularMarketPrice")
    state = str(meta.get("marketState") or "").upper()
    if (rmt and rmp is not None and state != "REGULAR"
            and (not bars or _bar_date(rmt) > _bar_date(bars[-1][0]))):
        bars.append((rmt, float(rmp)))

    if len(bars) < 2:
        raise ValueError("종가 시계열이 2개 미만")
    last, prev = bars[-1][1], bars[-2][1]
    return {
        "종가": round(last, 2),
        "전일대비": round(last - prev, 2),
        "등락률": round((last - prev) / prev * 100, 2),
        "기준일": _bar_date(bars[-1][0]),
    }


def treasury():
    year = datetime.now(KST).year
    url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
           f"daily-treasury-rates.csv/{year}/all"
           f"?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv")
    rows = list(csv.DictReader(io.StringIO(get(url))))
    if not rows:
        raise ValueError("빈 CSV")
    r = rows[0]  # 최신일이 첫 행
    return {"기준일": r.get("Date"), "2년": r.get("2 Yr"), "10년": r.get("10 Yr"),
            "30년": r.get("30 Yr")}


def earnings(days: int):
    """오늘~오늘+N일 실적 발표. 날짜별로 하루씩 조회한다(API가 단일 날짜만 받는다)."""
    out = []
    today = datetime.now(KST).date()
    for i in range(days + 1):
        day = today + timedelta(days=i)
        if day.weekday() >= 5:      # 주말은 발표가 없다
            continue
        try:
            d = json.loads(get(f"https://api.nasdaq.com/api/calendar/earnings?date={day}"))
            rows = (d.get("data") or {}).get("rows") or []
        except Exception:
            continue                 # 하루가 실패해도 나머지 날짜는 계속
        for r in rows:
            out.append({
                "날짜": str(day), "D": i,
                "티커": r.get("symbol"), "회사": r.get("name"),
                "예상EPS": r.get("epsForecast"), "시가총액": r.get("marketCap"),
            })
    # 시가총액 큰 순으로 상위만 남긴다 — 전부 넣으면 하루 50건씩 쌓여 의미가 없다.
    def cap(x):
        try:
            return float(str(x.get("시가총액") or "0").replace("$", "").replace(",", ""))
        except ValueError:
            return 0.0
    out.sort(key=cap, reverse=True)
    return out[:15]


def main():
    argv = sys.argv[1:]
    days = int(argv[argv.index("--earnings-days") + 1]) if "--earnings-days" in argv else 7

    result = {"fetched_at": datetime.now(KST).isoformat(timespec="seconds")}
    errors = {}

    try:
        result["미국채금리"] = treasury()
    except Exception as e:
        errors["미국채금리"] = f"{type(e).__name__}: {e}"

    # ⚠️ 야후 조회는 **동시에** 던진다. 항목이 25개라 순차로 돌리면 16초가 30초 가까이 된다
    #    (2026-08-26 실측: 순차 16.2초). 브리핑 전체 시간에서 스크립트 비중은 작지만, 이건
    #    한 스크립트 안에서 네트워크 대기만 겹치는 것이라 위험 없이 그냥 줄어드는 구간이다.
    all_syms = list(INDICES) + list(SECTOR_ETF) + list(FUTURES) + list(GLOBAL_BENCH)
    quotes = {}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(yahoo_daily, s): s for s in all_syms}
        for f in cf.as_completed(futs):
            sym = futs[f]
            try:
                quotes[sym] = f.result()
            except Exception as e:
                quotes[sym] = {"_err": f"{type(e).__name__}: {e}"}

    def take(sym, group, label):
        q = quotes.get(sym) or {"_err": "미조회"}
        if "_err" in q:
            errors[f"{group}:{label}"] = q["_err"]
            return None
        return q

    idx = {}
    for sym, label in INDICES.items():
        q = take(sym, "지수", label)
        if q:
            idx[label] = q
    if idx:
        result["지수"] = idx

    fut = {}
    for sym, label in FUTURES.items():
        q = take(sym, "선물", label)
        if q:
            fut[label] = {"현재": q["종가"], "등락률": q["등락률"], "기준일": q["기준일"]}
    if fut:
        result["선물원자재"] = fut

    gb = {}
    for sym, (label, sector) in GLOBAL_BENCH.items():
        q = take(sym, "해외벤치마크", label)
        if q:
            gb[label] = {"티커": sym, "섹터": sector, "종가": q["종가"],
                         "등락률": q["등락률"], "기준일": q["기준일"]}
    if gb:
        result["해외벤치마크"] = gb

    sec = {}
    for sym, label in SECTOR_ETF.items():
        q = take(sym, "섹터", label)
        if q:
            # ⚠️ **기준일을 반드시 같이 넣는다.** 예전엔 섹터에만 날짜가 없어서
            #    값이 며칠째 그대로여도 알 방법이 없었다 — 사용자가 "업종 흐름이
            #    금요일이랑 같다"고 먼저 알아챘다(2026-08-31). 화면에 안 쓰더라도 남긴다.
            sec[label] = {"ETF": sym, "등락률": q["등락률"], "종가": q["종가"],
                          "기준일": q["기준일"]}
    if sec:
        # 등락률 내림차순 — 강세/약세 섹터를 바로 읽을 수 있게
        result["미국섹터"] = dict(sorted(sec.items(), key=lambda kv: kv[1]["등락률"], reverse=True))

    try:
        result["실적캘린더"] = earnings(days)
    except Exception as e:
        errors["실적캘린더"] = f"{type(e).__name__}: {e}"

    if errors:
        result["_실패항목"] = errors
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
