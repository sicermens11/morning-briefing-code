#!/usr/bin/env python3
r"""
probe_rates.py — **금리 자료를 어디서 구할 수 있나 전수 확인** (2026-09-03)

⚠️⚠️ **「불가능」 오판을 다섯 번 했다.** 원인은 늘 같다 —
   **두세 곳만 두드려보고 결론.** 이번엔 **열 곳 넘게** 두드린다.

## 왜 금리가 필요한가 (사용자 지적)
```
*"금리는 필요하지 않아? 국채금리, 중앙은행 금리!"*

지금까지 잰 것    미국 국채 **하루 변동** (변화율 -> 가짜, bp로 재도 약함)
안 재본 것       **금리 수준** · **인상/인하 국면** · **한국 기준금리·국고채**
                **한미 금리차** · **장단기 역전** · **FOMC 날짜**
⇒ 하루 변동은 잡음이지만 **국면**은 다른 이야기다
```

## 이미 있는 것
```
✅ 미국 국채 일별 31년  Yahoo ^TNX(10년) ^TYX(30년) ^FVX(5년) ^IRX(13주)
   ⇒ **장단기 역전(10년 − 13주)은 이미 계산할 수 있다**
⚠️ 한국 국고채  KRX OpenAPI `bon/kts_bydd_trd` — **2.6년(649일)뿐**
❌ 한국 기준금리 · 미국 기준금리(목표금리) — 없다
```
"""
import io
import json
import sys
import urllib.request

_H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Accept": "*/*"}


def 재보기(이름, url, 뭘, 초=12, 헤더=None):
    try:
        req = urllib.request.Request(url, headers=헤더 or _H)
        with urllib.request.urlopen(req, timeout=초) as r:
            b = r.read()
        t = b.decode("utf-8", errors="replace")
        if len(t) < 30:
            print(f"  ⚠️ {이름:<34}{뭘:<22}응답이 너무 짧다 ({len(t)}자)")
            return None
        줄 = [x for x in t.splitlines() if x.strip()]
        미 = t[:70].replace("\n", " ")
        print(f"  ✅ {이름:<34}{뭘:<22}{len(t):>9,}자 {len(줄):>6}줄  {미[:46]}")
        return t
    except Exception as e:
        print(f"  ❌ {이름:<34}{뭘:<22}{type(e).__name__} {str(e)[:38]}")
        return None


def main():
    print("═" * 100)
    print("  금리 자료 출처 전수 확인 — **열 곳 넘게 두드린다**")
    print("═" * 100)

    print("\n── ① FRED (미국 연준. 키 없이 CSV를 준다고 알려져 있다) ──")
    for sid, 뭘 in (("DFF", "미국 기준금리 일별"),
                    ("DFEDTARU", "연준 목표 상단"),
                    ("DGS2", "미국 2년물"),
                    ("T10Y2Y", "장단기차 10Y-2Y"),
                    ("IRLTLT01KRM156N", "한국 장기금리 월별"),
                    ("IR3TIB01KRM156N", "한국 3개월 월별")):
        재보기(f"fred.stlouisfed.org {sid}",
               f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", 뭘)

    print("\n── ② FRED 다른 길 (호스트·경로를 바꿔본다) ──")
    재보기("fred 다운로드 경로",
           "https://fred.stlouisfed.org/data/DFF.txt", "미국 기준금리 텍스트")
    재보기("research.stlouisfed.org",
           "https://research.stlouisfed.org/fred2/data/DFF.txt", "미국 기준금리")

    print("\n── ③ 한국은행 ECOS (키가 필요한지 확인) ──")
    재보기("ecos.bok.or.kr 표 목록",
           "https://ecos.bok.or.kr/api/StatisticTableList/sample/json/kr/1/10/",
           "샘플 키로 되나")

    print("\n── ④ 네이버 금융 (채권) ──")
    재보기("네이버 채권 API",
           "https://api.finance.naver.com/siseJson.naver?"
           "symbol=KOR3YT%3DRR&requestType=1&startTime=20100101&"
           "endTime=20260903&timeframe=day", "국고채 3년")
    재보기("네이버 marketindex",
           "https://finance.naver.com/marketindex/interestDailyQuote.naver?"
           "marketindexCd=IRR_GOVT03Y", "국고채 3년 일별")

    print("\n── ⑤ Yahoo (한국 국채 심볼이 있는지) ──")
    for 심, 뭘 in (("KR10YT=RR", "한국 10년물"), ("^KS11", "참고(코스피)"),
                   ("KRWUSD=X", "참고(환율)")):
        재보기(f"yahoo {심}",
               f"https://query2.finance.yahoo.com/v8/finance/chart/{심}"
               f"?range=5y&interval=1d", 뭘)

    print("\n── ⑥ 미국 재무부 공식 (키 불필요) ──")
    재보기("treasury.gov 국채금리",
           "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
           "v2/accounting/od/avg_interest_rates?page[size]=5",
           "평균 금리")
    재보기("home.treasury.gov XML",
           "https://home.treasury.gov/resource-center/data-chart-center/"
           "interest-rates/pages/xml?data=daily_treasury_yield_curve&"
           "field_tdr_date_value=2025", "일별 수익률 곡선 2025")

    print("\n── ⑦ 세계은행·OECD (키 불필요) ──")
    재보기("worldbank 한국 실질금리",
           "https://api.worldbank.org/v2/country/KR/indicator/"
           "FR.INR.RINR?format=json&per_page=100", "한국 실질금리 연별")

    print("\n── ⑧ 이미 있는 것 확인 ──")
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f, 뭘 in (("data/yahoo/IDX_TNX.json", "미국 10년물"),
                  ("data/yahoo/IDX_IRX.json", "미국 13주"),
                  ("data/yahoo/IDX_FVX.json", "미국 5년물")):
        p = os.path.join(base, f)
        if os.path.exists(p):
            d = json.load(io.open(p, encoding="utf-8-sig"))
            k = sorted(d.get("종가") or {})
            print(f"  ✅ {f:<34}{뭘:<22}{len(k):>6}일  {k[0]} ~ {k[-1]}")
        else:
            print(f"  ❌ {f:<34}{뭘:<22}없음")
    import glob
    g = sorted(glob.glob(os.path.join(base, "data", "krx-extra", "국고채",
                                      "*.json")))
    if g:
        print(f"  ⚠️ KRX 국고채                        한국 국고채"
              f"            {len(g):>6}일  "
              f"{os.path.basename(g[0])[:8]} ~ {os.path.basename(g[-1])[:8]}"
              f"   ← **2.6년뿐**")
        d = json.load(io.open(g[-1], encoding="utf-8-sig"))
        print(f"     담긴 것: {str(d)[:300]}")

    print("\n" + "═" * 100)
    print("  ⚠️ ✅가 뜬 곳만 실제로 쓸 수 있다. ❌는 이 PC에서 막혔거나 없는 것")
    return 0


if __name__ == "__main__":
    sys.exit(main())
