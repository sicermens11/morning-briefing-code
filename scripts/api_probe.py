#!/usr/bin/env python3
r"""
api_probe.py — **우리 열쇠로 뭘 받을 수 있나 실제로 두드려본다** (2026-09-07 신설)

## 왜
```
사용자 지적: 「안 알아봤다 넷은 KRX OpenAPI 목록과 DART API를 다 봐봐」
그동안 「없다」·「못 구한다」고 말한 게 오늘만 일곱 번 틀렸다.
⇒ 목록을 **짐작하지 않고 하나씩 두드려** 열리는 것만 적는다
```

## 안전 규칙 (어기지 않는다)
```
✅ KRX **OpenAPI**(data-dbg.krx.co.kr/svc/apis) 만 부른다
❌ KRX 웹 포털(data.krx.co.kr · short.krx.co.kr)은 **절대 안 두드린다**
✅ DART OpenAPI(opendart.fss.or.kr/api) 만 부른다
❌ 주문 API는 부르지 않는다 — 조회만
✅ 열쇠는 config.py 로만 읽는다. 화면에 찍지 않는다
```
⚠️ 하루치만 받아 **열리나 안 열리나**만 본다. 자료를 쌓지 않는다.

쓰는 법:
    python scripts\api_probe.py                 # 둘 다
    python scripts\api_probe.py --krx           # KRX 만
    python scripts\api_probe.py --dart          # DART 만
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_날 = "20260904"          # 전 거래일
_해 = "2024"
_삼성 = "005930"

# ── KRX OpenAPI ── (서비스, 엔드포인트, 뭐냐)
_KRX = [
    ("sto", "stk_bydd_trd", "유가증권 일별 시세"),
    ("sto", "ksq_bydd_trd", "코스닥 일별 시세"),
    ("sto", "knx_bydd_trd", "코넥스 일별 시세"),
    ("sto", "stk_isu_base_info", "유가증권 종목 기본정보"),
    ("sto", "ksq_isu_base_info", "코스닥 종목 기본정보"),
    ("sto", "knx_isu_base_info", "코넥스 종목 기본정보"),
    # ⭐ 아래는 「있으면 좋겠다」 싶어 넣은 것들 — 없으면 없다고 적힌다
    ("sto", "sht_bydd_trd", "★ 공매도 일별"),
    ("sto", "shtsl_bydd_trd", "★ 공매도 일별(다른 이름)"),
    ("sto", "bal_bydd_trd", "★ 대차잔고"),
    ("sto", "ln_bydd_trd", "★ 신용융자"),
    ("sto", "invst_bydd_trd", "★ 투자자별 매매"),
    ("idx", "krx_dd_trd", "KRX 지수"),
    ("idx", "kospi_dd_trd", "코스피 지수"),
    ("idx", "kosdaq_dd_trd", "코스닥 지수"),
    ("idx", "bon_dd_trd", "채권 지수"),
    ("idx", "drvprod_dd_trd", "파생상품 지수"),
    ("etp", "etf_bydd_trd", "ETF"),
    ("etp", "etn_bydd_trd", "ETN"),
    ("etp", "elw_bydd_trd", "ELW"),
    ("bon", "kts_bydd_trd", "국채전문유통"),
    ("bon", "bnd_bydd_trd", "일반채권"),
    ("bon", "smb_bydd_trd", "소액채권"),
    ("drv", "fut_bydd_trd", "선물"),
    ("drv", "opt_bydd_trd", "옵션"),
    ("drv", "eqsfu_stk_bydd_trd", "주식선물(유가)"),
    ("drv", "eqkfu_ksq_bydd_trd", "주식선물(코스닥)"),
    ("drv", "eqsop_bydd_trd", "주식옵션"),
    ("gen", "oil_bydd_trd", "석유"),
    ("gen", "gold_bydd_trd", "금"),
    ("gen", "ets_bydd_trd", "배출권"),
    ("esg", "sri_bydd_trd", "사회책임투자채권"),
]

# ── DART OpenAPI ── (엔드포인트, 뭐냐, 붙일 인자)
_DART = [
    ("list", "공시 검색", {"bgn_de": "20260901", "end_de": _날,
                           "page_count": "1"}),
    ("company", "기업 개황", {"corp_code": "00126380"}),
    # ⭐ 분기 재무 — naver-quarter 5분기 한계를 넘을 수 있나
    ("fnlttSinglAcnt", "★ 단일회사 주요계정(분기)",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11013"}),
    ("fnlttSinglAcntAll", "★ 단일회사 전체 재무제표(분기)",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11013",
      "fs_div": "CFS"}),
    ("fnlttMultiAcnt", "다중회사 주요계정",
     {"corp_code": "00126380,00164779", "bsns_year": _해,
      "reprt_code": "11011"}),
    ("fnlttSinglIndx", "★ 재무지표",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011",
      "idx_cl_code": "M210000"}),
    ("stockTotqySttus", "주식 총수",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011"}),
    ("alotMatter", "배당",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011"}),
    ("hyslrSttus", "소액주주",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011"}),
    ("tesstkAcqsDspsSttus", "자기주식",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011"}),
    ("elestock", "임원 주식", {"corp_code": "00126380"}),
    ("majorstock", "대주주 주식", {"corp_code": "00126380"}),
    ("empSttus", "★ 직원 현황",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011"}),
    ("hmvAuditAllSttus", "★ 임원 보수",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011"}),
    ("irdsSttus", "★ 타법인 출자",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011"}),
    ("cprndNrdmpBdApplSttus", "★ 미상환 전환사채",
     {"corp_code": "00126380", "bsns_year": _해, "reprt_code": "11011"}),
    ("piicDecsn", "★ 유상증자 결정", {"corp_code": "00126380",
                                      "bgn_de": "20240101", "end_de": _날}),
    ("tsstkAqDecsn", "★ 자기주식 취득 결정",
     {"corp_code": "00126380", "bgn_de": "20240101", "end_de": _날}),
]


def 두드리기(url, headers=None, 초=12):
    req = urllib.request.Request(url, headers=headers or
                                 {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=초) as r:
            뜻 = r.read().decode("utf-8", errors="replace")
            return r.status, 뜻
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", errors="replace")[:200]
                        if e.fp else "")
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {str(e)[:80]}"


def 줄수(뜻):
    """돌아온 것에 자료가 몇 줄 들었나"""
    try:
        d = json.loads(뜻)
    except ValueError:
        return None
    if isinstance(d, list):
        return len(d)
    for k in ("OutBlock_1", "list", "output", "data"):
        if isinstance(d.get(k), list):
            return len(d[k])
    for v in d.values():
        if isinstance(v, list):
            return len(v)
    return 0


def krx():
    key = config.get("KRX_API_KEY")
    if not key:
        print("  ⚠️ KRX_API_KEY 가 없다 — 건너뛴다")
        return
    print("=" * 90)
    print("  KRX OpenAPI — data-dbg.krx.co.kr/svc/apis")
    print("  (★ 는 「있으면 좋겠다」고 넣어본 것. 없으면 없다고 나온다)")
    print("=" * 90)
    열림, 닫힘 = [], []
    for svc, ep, 뭐 in _KRX:
        u = (f"https://data-dbg.krx.co.kr/svc/apis/{svc}/{ep}"
             f"?basDd={_날}")
        코드, 뜻 = 두드리기(u, {"AUTH_KEY": key, "User-Agent": "Mozilla/5.0"})
        n = 줄수(뜻) if 코드 == 200 else None
        표 = "✅" if (코드 == 200 and n) else ("△" if 코드 == 200 else "❌")
        말 = (f"{n:,}줄" if n else
              ("빈 응답" if 코드 == 200 else f"HTTP {코드}"))
        print(f"  {표} {svc}/{ep:<22}{뭐:<24}{말}")
        (열림 if 표 == "✅" else 닫힘).append((svc, ep, 뭐))
        time.sleep(0.3)
    print(f"\n  ⇒ 열린 것 {len(열림)}개 / 안 열린 것 {len(닫힘)}개")
    return 열림


def dart():
    key = config.get("DART_API_KEY")
    if not key:
        print("  ⚠️ DART_API_KEY 가 없다 — 건너뛴다")
        return
    print("\n" + "=" * 90)
    print("  DART OpenAPI — opendart.fss.or.kr/api  (삼성전자로 시험)")
    print("=" * 90)
    열림, 닫힘 = [], []
    for ep, 뭐, 인자 in _DART:
        q = urllib.parse.urlencode(dict(인자, crtfc_key=key))
        코드, 뜻 = 두드리기(f"https://opendart.fss.or.kr/api/{ep}.json?{q}")
        상태 = ""
        n = None
        try:
            d = json.loads(뜻)
            상태 = str(d.get("status", ""))
            n = 줄수(뜻)
        except ValueError:
            pass
        됨 = (코드 == 200 and 상태 == "000")
        표 = "✅" if (됨 and n) else ("△" if 됨 else "❌")
        말 = (f"{n:,}줄" if 됨 and n else
              (f"자료 없음(status {상태})" if 코드 == 200
               else f"HTTP {코드}"))
        print(f"  {표} {ep:<26}{뭐:<26}{말}")
        (열림 if 표 == "✅" else 닫힘).append((ep, 뭐))
        time.sleep(0.3)
    print(f"\n  ⇒ 열린 것 {len(열림)}개 / 안 열린 것 {len(닫힘)}개")
    return 열림


def main():
    다 = not ("--krx" in sys.argv or "--dart" in sys.argv)
    if 다 or "--krx" in sys.argv:
        krx()
    if 다 or "--dart" in sys.argv:
        dart()
    print("\n" + "=" * 90)
    print("  ⚠️ 「자료 없음」은 **그 회사·그 해에 없다**는 뜻일 수도 있다.")
    print("     엔드포인트 자체가 없으면 HTTP 400/404 로 나온다")
    print("=" * 90)
    return 0


if __name__ == "__main__":
    sys.exit(main())
