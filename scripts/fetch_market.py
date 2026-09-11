#!/usr/bin/env python3
"""
fetch_market.py — 네이버 증권 비공식 JSON API 직접 수집기 (2026-08-25 신설)

배경:
  이식 전까지 이 데이터들은 Exa(`web_fetch_exa`)를 **프록시로 삼아** 긁어왔다.
  Claude → Exa → stock.naver.com → 텍스트 변환 → 모델이 다시 파싱, 이라는 왕복이었다.
  문제가 둘이었다:
    1) **데이터가 낡았다.** 2026-08-25 실측 — Exa 경유로 받은 국고채 금리는 08-18자였는데
       직접 호출하니 같은 날 16:07 기준값이 나왔다. 일주일 낡은 값으로 판단하고 있었다.
       (브리핑 로그에 "MCP-10~14 stale — 국내금리 08-18자, 예탁금 08-13자"가 반복 기록됨)
    2) JSON을 텍스트로 바꿔 모델이 다시 읽으므로 변환 손실·토큰 낭비가 있었다.

  로컬 실행이라 그냥 직접 부르면 된다. 호출 비용 0, 왕복 없음, 원본 JSON 그대로.

출력(stdout, JSON):
  {
    "fetched_at": "2026-08-25T16:55:00+09:00",
    "items": {
      "<키>": {"ok": true, "data": {...}, "as_of": "..."} 또는 {"ok": false, "error": "..."}
    }
  }

⚠️ 비공식 API다. 언제든 스키마가 바뀌거나 막힐 수 있다.
   그래서 **항목별로 독립 처리**한다 — 하나가 실패해도 나머지는 정상 반환한다.
   호출부는 ok=false인 항목만 "미확인"으로 처리하고 계속 진행하면 된다.

사용:
    run-py.ps1 -Script fetch_market.py                    # 전체
    run-py.ps1 -Script fetch_market.py -Args @('--only','bond,deposit')
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

HEADERS = {
    # 네이버 증권 API는 브라우저 컨텍스트를 기대한다. 이 두 헤더가 없으면 거부되는 경우가 있다.
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://stock.naver.com/",
    "Accept": "application/json",
}

ENDPOINTS = {
    "bond": {
        "url": "https://stock.naver.com/api/securityService/marketindex/bond/nation/KOR",
        "desc": "국내 국채금리(2년·10년)",
    },
    "deposit": {
        "url": "https://stock.naver.com/api/domestic/market/trendDeposit?startIdx=0&pageSize=5",
        "desc": "투자자 예탁금·신용융자",
    },
    "econ_calendar": {
        "url": ("https://stock.naver.com/api/securityService/economic/indicator/nations/upcoming"
                "?limit=10&nationTypeList=USA&nationTypeList=KOR"),
        "desc": "미국·한국 경제지표 발표예정",
    },
    "sector_rank": {
        "url": "https://stock.naver.com/api/domestic/market/home/upjongTheme/ranking?sortType=changeRate",
        "desc": "업종·테마 등락률 랭킹",
    },
    "foreign_rank": {
        "url": ("https://stock.naver.com/api/domestic/market/trend/trendForeignOrg"
                "?investorType=FOREIGNER&tradeType=KRX&marketType=ALL"
                "&startIdx=0&pageSize=10&periodType=DAY"),
        "desc": "외국인 순매수 상위 랭킹",
    },
    "kospi": {
        "url": "https://polling.finance.naver.com/api/realtime/domestic/index/KOSPI",
        "desc": "코스피 지수(실시간)",
    },
}


def fetch(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _g(d, *path, default=None):
    """중첩 딕셔너리/리스트에서 안전하게 값 꺼내기. 하나라도 없으면 default."""
    cur = d
    for p in path:
        try:
            cur = cur[p]
        except (KeyError, IndexError, TypeError):
            return default
    return cur


def summarize(items: dict) -> dict:
    """브리핑이 실제로 쓰는 필드만 추려 컴팩트하게 만든다.

    원본 6개 응답을 합치면 34,000자가 넘는데 브리핑이 쓰는 건 그중 극히 일부다.
    Exa 경유 시절엔 그 전부가 텍스트로 변환돼 컨텍스트에 들어갔고, 매 턴 재전송되며
    비용을 밀어올렸다. 여기서 잘라내면 1,000자 안팎이 된다.

    ⚠️ 비공식 API라 스키마가 바뀔 수 있다. 모든 접근은 _g()로 감싸 실패해도
       그 필드만 None이 되게 한다 — 전체가 무너지지 않는다.
    """
    out = {}

    # --- 국채금리 ---------------------------------------------------------
    if _g(items, "bond", "ok"):
        rows = _g(items, "bond", "data", default=[]) or []
        picked = {}
        for r in rows:
            nm = r.get("name", "")
            if "10년" in nm or "2년" in nm:
                picked[nm] = {"금리": r.get("closePrice"), "기준시각": r.get("localTradedAt")}
        out["국채금리"] = picked or None

    # --- 예탁금 -----------------------------------------------------------
    if _g(items, "deposit", "ok"):
        c = _g(items, "deposit", "data", "content", 0)
        if c:
            out["예탁금"] = {
                "기준일": c.get("bizdate"),
                "투자자예탁금_억원": c.get("customerDeposit"),
                "전일대비_억원": c.get("customerDepositDiff"),
                "신용융자_억원": c.get("creditLoan"),
                "신용융자_전일대비_억원": c.get("creditLoanDiff"),
            }

    # --- 코스피 -----------------------------------------------------------
    if _g(items, "kospi", "ok"):
        d = _g(items, "kospi", "data", "datas", 0)
        if d:
            out["코스피"] = {
                "지수": d.get("closePrice"),
                "전일대비": d.get("compareToPreviousClosePrice"),
                "등락률": d.get("fluctuationsRatio"),
                "방향": _g(d, "compareToPreviousPrice", "text"),
                "거래시간": f'{_g(d, "stockExchangeType", "startTime")}~{_g(d, "stockExchangeType", "endTime")}',
            }

    # --- 업종·테마 랭킹 ----------------------------------------------------
    if _g(items, "sector_rank", "ok"):
        data = _g(items, "sector_rank", "data", default={}) or {}

        def top(lst, n=3):
            return [{
                "순위": x.get("ranking"),
                "이름": x.get("upjongThemeName"),
                "등락률": x.get("prevChangeRate"),
                "상승/하락": f'{x.get("riseCnt")}/{x.get("fallCnt")}',
                "대표종목": x.get("leadingItemName"),
                "대표종목코드": x.get("leadingItemCode"),
            } for x in (lst or [])[:n]]

        out["업종랭킹"] = top(data.get("upjongRankList"))
        out["테마랭킹"] = top(data.get("themeRankList"))

    # --- 외국인 순매수 랭킹 -------------------------------------------------
    if _g(items, "foreign_rank", "ok"):
        # ⚠️ `sections`가 리스트일 때도 단일 객체일 때도 있다(2026-08-25 실측: 단일 객체).
        #    둘 다 받아준다 — 스키마가 바뀌어도 한쪽은 걸린다.
        sec = _g(items, "foreign_rank", "data", "sections")
        if isinstance(sec, list):
            sec = sec[0] if sec else {}
        buy = (sec or {}).get("buyRankList") or []
        out["외국인순매수상위"] = [{
            "순위": i + 1,
            "종목": x.get("itemname"),
            "코드": x.get("itemcode"),
            "현재가": x.get("nowPrice"),
            "등락률": x.get("prevChangeRate"),
            "거래량": x.get("dailyTradeVolume"),
            "기준일": x.get("bizdateTo"),
        } for i, x in enumerate(buy[:5])]

    # --- 경제지표 캘린더 ---------------------------------------------------
    if _g(items, "econ_calendar", "ok"):
        cal = _g(items, "econ_calendar", "data", default=[]) or []
        if isinstance(cal, dict):
            cal = cal.get("indicators") or cal.get("content") or []
        out["경제지표예정"] = [{
            "국가": x.get("nationKoreanName") or x.get("nationName"),
            "지표": x.get("name") or x.get("indicatorName"),
            "발표일": x.get("releaseDate") or x.get("date"),
            "중요도": x.get("importance"),
            "이전치": x.get("previousValue"),
        } for x in cal[:8] if isinstance(x, dict)]

    # 실패한 항목은 호출부가 "미확인"으로 처리할 수 있게 따로 알린다.
    failed = [k for k, v in items.items() if not v.get("ok")]
    if failed:
        out["_실패항목"] = {k: items[k].get("error") for k in failed}
    return out


def main():
    argv = sys.argv[1:]
    only = None
    if "--only" in argv:
        only = {k.strip() for k in argv[argv.index("--only") + 1].split(",")}
    want_summary = "--summary" in argv

    items = {}
    for key, spec in ENDPOINTS.items():
        if only and key not in only:
            continue
        try:
            data = fetch(spec["url"])
            items[key] = {"ok": True, "desc": spec["desc"], "data": data}
        except Exception as e:
            # 항목별 독립 실패 — 하나가 죽어도 나머지는 살린다.
            items[key] = {"ok": False, "desc": spec["desc"],
                          "error": f"{type(e).__name__}: {e}"}

    payload = {"fetched_at": datetime.now(KST).isoformat(timespec="seconds")}
    if want_summary:
        payload["summary"] = summarize(items)
    else:
        payload["items"] = items

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
