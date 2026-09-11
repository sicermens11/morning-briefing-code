#!/usr/bin/env python3
# ⚠️ docstring은 r"""(raw). 본문에 윈도 경로가 들어가면 `\u`가 유니코드 이스케이프로 해석돼
#    파일 전체가 SyntaxError가 된다(2026-08-26 track_unmapped.py에서 겪음).
r"""
fetch_sec.py — 미국 임원 내부자거래(Form 4) 직접 수집 (2026-08-26 신설)

대체 대상: **강화-B**의 AlphaVantage `INSIDER_TRANSACTIONS`.

왜 바꾸나 (실측 근거):
  1. **AlphaVantage 무료 티어는 프리미엄 엔드포인트 하루 25회 제한**이다. 실제로
     2026-08-21 실행에서 rate limit에 걸려 openinsider 스크래핑으로 폴백했다.
     SEC EDGAR는 그 데이터의 **원천**이고 사실상 무제한이다(초당 10회 권장).
  2. 2026-08-26 대조 검증: 08-25 브리핑이 AlphaVantage로 얻었던
     *"Suzanne Nora Johnson, 'A' 1,262+1,148주, share_price 0.0"* 을
     EDGAR 원문에서 **정확히 재현**했다.

⚠️ 판정은 하지 않는다. 이 스크립트는 **수집만** 한다.
   "실제 시장매수인가"(강화-B +2점) 판정은 SKILL.md 규칙대로 모델이 한다.
   다만 판정에 꼭 필요한 힌트는 함께 넘긴다 — 아래 `_판정힌트` 참고.

사용:
    run-py.ps1 -Script fetch_sec.py -Args @('--ticker','NVDA')
    run-py.ps1 -Script fetch_sec.py -Args @('--ticker','NVDA','--days','120')
    run-py.ps1 -Script fetch_sec.py -Args @('--refresh-tickers')

출력(stdout, JSON): {"ticker":..., "company":..., "cik":..., "거래":[...], "_판정힌트":{...}}
"""
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TICKER_CACHE = os.path.join(_DATA, "sec-tickers.json")
CACHE_DAYS = 30

# ⚠️ SEC는 User-Agent에 **연락처를 요구**한다. 없으면 403으로 막는다(공식 정책).
# ⚠️ `Accept-Encoding: gzip`을 넣지 않는다 — urllib은 자동 압축해제를 하지 않아서
#    본문이 gzip 바이트 그대로 오고 `JSONDecodeError`가 난다(2026-08-26에 실제로 겪었다).
HEADERS = {"User-Agent": "morning-sector-briefing sicermens11@gmail.com"}

DEFAULT_DAYS = 90
MAX_FILINGS = 8          # 최근 Form 4를 몇 건까지 원문 파싱할지(1건당 2회 요청)
REQ_INTERVAL = 0.12      # SEC 권장 초당 10회 이하

# Form 4 거래코드. **P만이 진짜 시장 매수**다.
CODE_MEANING = {
    "P": "시장매수", "S": "시장매도", "A": "보상성취득(무상)", "M": "옵션·RSU 행사",
    "F": "세금납부용 원천공제", "G": "증여", "D": "처분", "C": "전환", "X": "옵션행사",
}


def _get(url: str, timeout: int = 25) -> str:
    time.sleep(REQ_INTERVAL)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def load_tickers(force: bool = False) -> dict:
    """티커 → CIK 표. 10,388건 약 847KB라 30일 캐시한다."""
    fresh = (os.path.exists(TICKER_CACHE)
             and (time.time() - os.path.getmtime(TICKER_CACHE)) < CACHE_DAYS * 86400)
    if fresh and not force:
        with open(TICKER_CACHE, "r", encoding="utf-8-sig") as fp:
            return json.load(fp)
    raw = json.loads(_get("https://www.sec.gov/files/company_tickers.json"))
    table = {v["ticker"].upper(): {"cik": str(v["cik_str"]).zfill(10), "name": v["title"]}
             for v in raw.values() if v.get("ticker")}
    os.makedirs(_DATA, exist_ok=True)
    with open(TICKER_CACHE, "w", encoding="utf-8") as fp:
        json.dump(table, fp, ensure_ascii=False)
    return table


def _pick(pattern: str, text: str):
    m = re.search(pattern, text, re.S)
    return m.group(1).strip() if m else None


def parse_form4(xml: str) -> dict:
    """Form 4 XML에서 사람·직위·거래내역을 뽑는다.

    ⚠️ 표준 라이브러리만 쓰려고 정규식으로 읽는다. SEC XML은 스키마가 고정돼 있어
       실무상 안전하지만, **필드가 안 잡히면 조용히 None이 된다.** 그래서 원문 URL을
       항상 함께 돌려줘서 사람이 확인할 수 있게 한다.
    """
    owner = _pick(r"<rptOwnerName>(.*?)</rptOwnerName>", xml)
    title = _pick(r"<officerTitle>(.*?)</officerTitle>", xml)
    is_dir = _pick(r"<isDirector>(.*?)</isDirector>", xml)
    if not title and is_dir in ("1", "true"):
        title = "이사(Director)"

    # 비파생 거래 블록만 본다(파생상품 거래는 옵션 부여라 시장매수와 성격이 다르다).
    rows = []
    for blk in re.findall(r"<nonDerivativeTransaction>(.*?)</nonDerivativeTransaction>", xml, re.S):
        code = _pick(r"<transactionCode>(.*?)</transactionCode>", blk)
        shares = _pick(r"<transactionShares>\s*<value>(.*?)</value>", blk)
        price = _pick(r"<transactionPricePerShare>\s*<value>(.*?)</value>", blk)
        ad = _pick(r"<transactionAcquiredDisposedCode>\s*<value>(.*?)</value>", blk)
        date = _pick(r"<transactionDate>\s*<value>(.*?)</value>", blk)
        try:
            price_f = float(price) if price not in (None, "") else 0.0
        except ValueError:
            price_f = 0.0
        rows.append({
            "거래일": date, "코드": code, "코드뜻": CODE_MEANING.get(code, "기타"),
            "취득처분": ad, "수량": shares, "단가": price_f,
            # ⚠️ **이 한 줄이 강화-B의 핵심이다.** 코드가 A(보상성 취득)면 단가가 0으로 찍히는데,
            #    그걸 "임원이 샀다"로 읽으면 없는 신호를 만든다. 2026-08-25에 실제로
            #    엔비디아 사외이사의 'A' 1,262주를 매수로 오독할 뻔했다.
            "실제시장매수": bool(code == "P" and price_f > 0),
        })
    return {"보고자": owner, "직위": title, "거래": rows}


def fetch(ticker: str, days: int) -> dict:
    table = load_tickers()
    info = table.get(ticker.upper())
    if not info:
        return {"ticker": ticker, "error": f"티커를 SEC 목록에서 찾지 못했다({len(table)}건 중)"}
    cik = info["cik"]
    cutoff = (datetime.now(KST) - timedelta(days=days)).strftime("%Y-%m-%d")

    sub = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    rec = sub["filings"]["recent"]
    picked = [(rec["filingDate"][i], rec["accessionNumber"][i])
              for i, f in enumerate(rec["form"])
              if f == "4" and rec["filingDate"][i] >= cutoff][:MAX_FILINGS]

    out, errs = [], []
    bare = cik.lstrip("0")
    for fdate, acc in picked:
        a = acc.replace("-", "")
        try:
            idx = json.loads(_get(f"https://www.sec.gov/Archives/edgar/data/{bare}/{a}/index.json"))
            xmls = [x["name"] for x in idx["directory"]["item"]
                    if x["name"].lower().endswith(".xml")]
            if not xmls:
                errs.append({"접수일": fdate, "사유": "XML 없음"})
                continue
            parsed = parse_form4(_get(f"https://www.sec.gov/Archives/edgar/data/{bare}/{a}/{xmls[0]}"))
            parsed["접수일"] = fdate
            parsed["원문"] = f"https://www.sec.gov/Archives/edgar/data/{bare}/{a}/{xmls[0]}"
            out.append(parsed)
        except Exception as e:
            errs.append({"접수일": fdate, "사유": f"{type(e).__name__}: {e}"})

    buys = [(f, r) for f in out for r in f["거래"] if r["실제시장매수"]]
    sells = [(f, r) for f in out for r in f["거래"] if r["코드"] == "S"]
    res = {
        "ticker": ticker.upper(), "company": info["name"], "cik": cik,
        "조회기간": f"최근 {days}일(≥{cutoff})", "Form4건수": len(out), "보고": out,
    }
    res["_판정힌트"] = {
        "실제시장매수_있음": bool(buys),
        "실제시장매수_요약": [f"{f['보고자']}({f['직위'] or '-'}) {r['거래일']} {r['수량']}주 @${r['단가']}"
                              for f, r in buys],
        "매도_요약": [f"{f['보고자']}({f['직위'] or '-'}) {r['거래일']} {r['수량']}주" for f, r in sells],
        "⚠️": ("코드 A는 **보상성 취득**이라 단가가 0으로 찍힌다 — 매수가 아니다. "
                "강화-B(+2)는 `실제시장매수_있음`이 true일 때만 검토한다. "
                "매수와 매도가 같이 있으면 둘 다 서술한다."),
    }
    if errs:
        res["_실패항목"] = errs
    return res


def _yahoo_crumb():
    """야후 quoteSummary는 2026년부터 crumb 인증을 요구한다.

    ⚠️ 쿠키 출처가 중요하다 — `fc.yahoo.com`은 404를 던지고,
       **`finance.yahoo.com/quote/<티커>/`를 먼저 열어야** 유효한 쿠키가 잡힌다
       (2026-08-26 실측: 전자 실패, 후자 성공).
    """
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.9"}
    op.open(urllib.request.Request("https://finance.yahoo.com/quote/NVDA/", headers=ua),
            timeout=20).read()
    crumb = op.open(urllib.request.Request(
        "https://query1.finance.yahoo.com/v1/test/getcrumb", headers=ua),
        timeout=20).read().decode("utf-8", "replace").strip()
    if not crumb or len(crumb) > 30:
        raise ValueError(f"crumb 형식 이상: {crumb[:20]!r}")
    return op, ua, crumb


def analyst_trend(ticker: str) -> dict:
    """미국 종목의 **애널리스트 의견 추이·등급 변경·어닝 서프라이즈**. (2026-08-26 신설)

    ⚠️ 이 셋은 지금까지 **아예 못 보던 것**이다. 강화-G는 "현재 매수비율" 스냅샷만 봤다.
       - `의견추이`: 3개월 전과 비교해 **의견이 좋아지는 중인지** — 스냅샷으로는 알 수 없다
       - `등급변경`: 어느 증권사가 언제 올렸나/내렸나
       - `어닝서프라이즈`: 이 회사가 예상을 **꾸준히 넘기는지**

    ⚠️ 판정은 하지 않는다. 강화-G 점수(매수비율 70/85% 기준)는 기존 규칙 그대로다.
       이건 **서술 보강용**이다.
    """
    try:
        op, ua, crumb = _yahoo_crumb()
        url = ("https://query1.finance.yahoo.com/v10/finance/quoteSummary/"
               f"{urllib.parse.quote(ticker)}?modules="
               "recommendationTrend,upgradeDowngradeHistory,earningsHistory"
               f"&crumb={urllib.parse.quote(crumb)}")
        d = json.loads(op.open(urllib.request.Request(url, headers=ua), timeout=25)
                       .read().decode("utf-8", "replace"))
        res = (d.get("quoteSummary", {}).get("result") or [{}])[0]
        out = {"ticker": ticker.upper()}
        tr = res.get("recommendationTrend", {}).get("trend") or []
        out["의견추이"] = [{"시점": t.get("period"), "적극매수": t.get("strongBuy"),
                            "매수": t.get("buy"), "중립": t.get("hold"),
                            "매도": t.get("sell"), "적극매도": t.get("strongSell")}
                           for t in tr[:4]]
        ud = res.get("upgradeDowngradeHistory", {}).get("history") or []
        out["등급변경"] = [{"증권사": h.get("firm"), "이전": h.get("fromGrade"),
                            "이후": h.get("toGrade"), "구분": h.get("action")}
                           for h in ud[:6]]
        eh = res.get("earningsHistory", {}).get("history") or []
        out["어닝서프라이즈"] = [{"분기": (e.get("quarter") or {}).get("fmt"),
                                  "예상": (e.get("epsEstimate") or {}).get("raw"),
                                  "실제": (e.get("epsActual") or {}).get("raw"),
                                  "서프라이즈율": (e.get("surprisePercent") or {}).get("raw")}
                                 for e in eh[:4]]
        # `0m`이 현재, `-1m`이 한 달 전. 첫 두 개를 비교해 방향만 알려준다.
        if len(out["의견추이"]) >= 2:
            def score(t):
                tot = sum(t.get(k) or 0 for k in ("적극매수", "매수", "중립", "매도", "적극매도"))
                return round(((t.get("적극매수") or 0) + (t.get("매수") or 0)) / tot * 100, 1) if tot else None
            now, prev = score(out["의견추이"][0]), score(out["의견추이"][1])
            if now is not None and prev is not None:
                out["_매수비율_변화"] = {"현재": now, "1개월전": prev,
                                          "변화": round(now - prev, 1),
                                          "방향": "개선" if now > prev else "악화" if now < prev else "보합"}
        return out
    except Exception as e:
        return {"ticker": ticker.upper(), "error": f"{type(e).__name__}: {e}"}


def main():
    argv = sys.argv[1:]
    if "--analyst" in argv:
        t = argv[argv.index("--analyst") + 1]
        print(json.dumps(analyst_trend(t), ensure_ascii=False))
        return
    if "--refresh-tickers" in argv:
        t = load_tickers(force=True)
        print(json.dumps({"ok": True, "티커수": len(t), "path": TICKER_CACHE}, ensure_ascii=False))
        return
    if "--ticker" not in argv:
        print(json.dumps({"error": "--ticker 필요"}, ensure_ascii=False))
        return
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else DEFAULT_DAYS
    try:
        print(json.dumps(fetch(argv[argv.index("--ticker") + 1], days), ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"_fatal_error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

