#!/usr/bin/env python3
r"""
fetch_dart.py — DART OpenAPI 직접 수집 (2026-08-25 신설)

대체 대상 (전부 MCP 호출 0회로 전환):
  - MCP-6      관심종목 공시 브리핑      ← easyGongsi-daily_briefing ×3 + register_watchlist
  - 강화-F1    기업 고유번호 조회        ← opendart-find_company
  - 강화-D1    임원·주요주주 소유상황     ← opendart-get_executive_stock
  - 강화-OWNERSHIP  대량보유상황          ← opendart-get_major_stock

왜 바꾸나 (실측 근거, 2026-08-25 브리핑 로그):
  1. "두산에너빌리티 임원자사주 — 응답 **130,667자로 토큰 상한 초과** → 미확인"
     MCP 도구가 전체를 한 번에 뱉으려다 터졌다. 직접 호출은 필요한 필드만 골라 담을 수 있다.
  2. "**register_watchlist 8종목 실패**(비상장/사명변경, 기존과 동일 패턴)" — 매일 반복됐다.
     DART는 종목코드로 직접 조회하므로 watchlist 등록 자체가 필요 없다.
  3. "두 후보 모두 공시에 **계약 금액 미기재**로 수주 규모 미확인"
     → 공시 상세(단일판매·공급계약)는 별도 API로 금액이 구조화돼 있다(아래 `contract` 참고).

⚠️ 기업 고유번호(corp_code)는 종목코드와 다르다.
   DART가 배포하는 전체 목록(ZIP)을 받아 `data\dart-corpcode.json`에 캐시해 두고 재사용한다.
   목록은 잘 안 바뀌므로 **7일 지난 캐시만 갱신**한다(매번 받으면 수 MB를 낭비한다).

사용:
    run-py.ps1 -Script fetch_dart.py -Args @('--disclosures','20260825')       # 당일 공시 전체
    run-py.ps1 -Script fetch_dart.py -Args @('--stocks','014620,034020')       # 종목별 공시+임원+대량보유
    run-py.ps1 -Script fetch_dart.py -Args @('--refresh-corpcode')             # 기업코드 캐시 강제 갱신
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

KST = timezone(timedelta(hours=9))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORP_CACHE = os.path.join(BASE, "data", "dart-corpcode.json")
CACHE_DAYS = 7

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 브리핑이 실제로 챙기는 공시 유형. 나머지(정보성)는 건수만 세고 본문에 안 싣는다.
# ⚠️⚠️⚠️ **2026-09-03 대폭 확장.** 전에는 17개뿐이라 **하루 530건 중 230건(43%)이
#   버려졌다.** 그것도 「정보성건수」로 **숫자만 세고 공시명조차 저장 안 해서** 되살릴 수 없었다.
#   버려진 것 중에 이런 게 있었다 (20260901 실측):
#     51건 주식등의대량보유상황보고서 · 38건 임원ㆍ주요주주 소유상황
#     10건 타인에대한채무보증결정 · **3건 영업(잠정)실적(공정공시)** ← 실적 발표다
#      3건 타법인주식취득결정 · 6건 금전대여·자금차입·담보제공
SIGNAL_KEYWORDS = (
    # ── 원래 있던 17개 ──
    "단일판매", "공급계약", "수주", "자기주식", "유상증자", "무상증자",
    "횡령", "배임", "감자", "합병", "분할", "영업정지", "거래정지",
    "전환사채", "신주인수권", "최대주주", "소송",
    # ── 지분 (제일 많이 버려지던 것) ──
    "대량보유", "임원ㆍ주요주주", "임원·주요주주", "주식등의",
    # ── 실적 ──
    "실적", "결산", "매출액또는손익", "영업이익",
    # ── 재무 위험 ──
    "채무보증", "자금대여", "금전대여", "자금차입", "담보", "채무인수",
    "부도", "당좌거래", "회생절차", "파산", "자본잠식", "채권은행",
    # ── 지배구조·투자 ──
    "타법인주식", "출자증권", "주식교환", "주식이전", "영업양수", "영업양도",
    "자산양수", "자산양도", "특수관계인",
    # ── 상장 지위 ──
    "상장폐지", "관리종목", "불성실공시", "투자주의", "투자경고", "투자위험",
    # ── 사업 재료 ──
    "특허", "임상", "품목허가", "기술이전", "계약해지", "계약해제",
    "신규시설투자", "유형자산", "배당",
)


def api(path: str, **params):
    params["crtfc_key"] = config.require("DART_API_KEY")
    url = f"https://opendart.fss.or.kr/api/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


# --------------------------------------------------------------------------
# 기업 고유번호 캐시
# --------------------------------------------------------------------------
def load_corpcode(force: bool = False) -> dict:
    """{종목코드(6자리): {corp_code, corp_name}} 매핑. 7일 캐시."""
    if not force and os.path.exists(CORP_CACHE):
        age = datetime.now().timestamp() - os.path.getmtime(CORP_CACHE)
        if age < CACHE_DAYS * 86400:
            with open(CORP_CACHE, "r", encoding="utf-8") as fp:
                return json.load(fp)

    key = config.require("DART_API_KEY")
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={key}"
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        blob = r.read()

    mapping = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        xml = z.read(z.namelist()[0]).decode("utf-8", errors="replace")
    for el in ElementTree.fromstring(xml).iter("list"):
        stock = (el.findtext("stock_code") or "").strip()
        if not stock:          # 비상장은 종목코드가 비어 있다 — 우리 용도엔 불필요
            continue
        mapping[stock] = {
            "corp_code": (el.findtext("corp_code") or "").strip(),
            "corp_name": (el.findtext("corp_name") or "").strip(),
        }

    os.makedirs(os.path.dirname(CORP_CACHE), exist_ok=True)
    with open(CORP_CACHE, "w", encoding="utf-8") as fp:
        json.dump(mapping, fp, ensure_ascii=False)
    return mapping


# --------------------------------------------------------------------------
# 조회 기능
# --------------------------------------------------------------------------
def disclosures(date_yyyymmdd: str, hard_page_cap: int = 12):
    """당일 접수 공시 전체를 훑어 '챙길 공시'와 '정보성'으로 나눈다.

    easyGongsi-daily_briefing(관심종목 등록 후 조회) 대체.
    ⚠️ watchlist 등록 자체가 없어지므로, 매일 반복되던 "register_watchlist 8종목 실패
       (비상장/사명변경)"가 사라진다. 대신 **상장사 전체**의 신호성 공시가 들어온다 —
       관심종목 밖에서 재료가 터진 경우도 잡히므로 오히려 발굴 범위가 넓어진다.
       (관심종목 필터링은 모델이 value-chain-map.md와 대조해서 하면 된다.)

    페이지 수는 total_count로 계산한다. 고정값으로 두면 공시가 많은 날 뒤쪽이 잘린다
    (2026-08-25 실측: 총 567건인데 4쪽 고정이라 400건까지만 봤다).
    """
    # ⚠️⚠️ **2026-09-03 구조 변경.** 전에는 안 걸린 것을 `info_count`로 **세기만** 했다.
    #   그러면 나중에 어떤 유형을 쓰고 싶어도 **다시 받는 수밖에 없다**(4,102일 × 6쪽 = 2만 5천 회).
    #   ⇒ 이제 **전부 담는다.** `챙길공시`와 `그밖의공시`로 나눌 뿐 버리지 않는다.
    signal, other, total = [], [], 0
    page = 1
    while page <= hard_page_cap:
        d = api("list.json", bgn_de=date_yyyymmdd, end_de=date_yyyymmdd,
                page_no=str(page), page_count="100")
        if d.get("status") != "000":
            if page == 1:
                raise RuntimeError(f"DART {d.get('status')}: {d.get('message')}")
            break
        rows = d.get("list") or []
        total = int(d.get("total_count") or 0)
        for x in rows:
            nm = x.get("report_nm") or ""
            if any(k in nm for k in SIGNAL_KEYWORDS):
                signal.append({
                    "종목명": x.get("corp_name"), "종목코드": x.get("stock_code"),
                    "공시명": nm.strip(), "접수번호": x.get("rcept_no"),
                })
            else:
                other.append({
                    "종목명": x.get("corp_name"), "종목코드": x.get("stock_code"),
                    "공시명": nm.strip(), "접수번호": x.get("rcept_no"),
                })
        if page * 100 >= total or not rows:
            break
        page += 1

    truncated = total > page * 100
    return {"기준일": date_yyyymmdd, "전체건수": total,
            "조회건수": page * 100 if not truncated else hard_page_cap * 100,
            "챙길공시": signal, "정보성건수": len(other),
            "그밖의공시": other,
            "잘림": truncated,
            "원문URL형식": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={접수번호}"}


def executive_stock(corp_code: str, limit: int = 12):
    """임원·주요주주 특정증권등 소유상황보고. 최신순 상위 N건만.

    ⚠️ MCP 도구는 전체를 반환해 13만 자를 넘긴 적이 있다(2026-08-25 실측).
       여기서는 필요한 필드만 뽑고 건수를 잘라 그 문제를 없앤다.
    """
    d = api("elestock.json", corp_code=corp_code)
    if d.get("status") == "013":          # 조회된 데이터 없음
        return []
    if d.get("status") != "000":
        raise RuntimeError(f"DART {d.get('status')}: {d.get('message')}")
    rows = d.get("list") or []
    rows.sort(key=lambda r: r.get("rcept_dt") or "", reverse=True)
    return [{
        "접수일": r.get("rcept_dt"), "성명": r.get("repror"),
        "직위": r.get("isu_exctv_ofcps"), "등기여부": r.get("isu_exctv_rgist_at"),
        "주요주주여부": r.get("isu_main_shrholdr"),
        "변동후수량": r.get("sp_stock_lmp_cnt"), "증감": r.get("sp_stock_lmp_irds_cnt"),
        "사유": r.get("sp_stock_lmp_irds_rson"),
    } for r in rows[:limit]]


def major_holders(corp_code: str, limit: int = 8):
    """주식등의 대량보유상황보고(5% 룰). 강화-OWNERSHIP 대체."""
    d = api("majorstock.json", corp_code=corp_code)
    if d.get("status") == "013":
        return []
    if d.get("status") != "000":
        raise RuntimeError(f"DART {d.get('status')}: {d.get('message')}")
    rows = d.get("list") or []
    rows.sort(key=lambda r: r.get("rcept_dt") or "", reverse=True)
    # ⚠️ 증감은 `stkrt_irds`다. `bfore_stkrt`라는 필드는 없어서 2026-08-25 첫 실행에서
    #    직전비율이 통째로 빈 값으로 나왔다(에러가 아니라 조용한 누락이라 알아채기 어렵다).
    return [{
        "접수일": r.get("rcept_dt"), "보유자": r.get("repror"),
        "보유비율": r.get("stkrt"), "비율증감": r.get("stkrt_irds"),
        "보유수량": r.get("stkqy"), "수량증감": r.get("stkqy_irds"),
        "보유목적": r.get("report_resn"),
    } for r in rows[:limit]]


def main():
    argv = sys.argv[1:]
    out = {"fetched_at": datetime.now(KST).isoformat(timespec="seconds")}
    errors = {}

    if "--refresh-corpcode" in argv:
        m = load_corpcode(force=True)
        out["기업코드캐시"] = {"건수": len(m), "경로": CORP_CACHE}
        print(json.dumps(out, ensure_ascii=False))
        return

    if "--disclosures" in argv:
        date = argv[argv.index("--disclosures") + 1]
        try:
            out["공시"] = disclosures(date)
        except Exception as e:
            errors["공시"] = f"{type(e).__name__}: {e}"

    if "--stocks" in argv:
        codes = [c.strip() for c in argv[argv.index("--stocks") + 1].split(",") if c.strip()]
        try:
            cmap = load_corpcode()
        except Exception as e:
            cmap = {}
            errors["기업코드"] = f"{type(e).__name__}: {e}"
        stocks = {}
        for code in codes:
            info = cmap.get(code)
            if not info:
                stocks[code] = {"error": "corp_code 매핑 없음(비상장이거나 캐시 갱신 필요)"}
                continue
            item = {"기업명": info["corp_name"], "corp_code": info["corp_code"]}
            for label, fn in (("임원소유", executive_stock), ("대량보유", major_holders)):
                try:
                    item[label] = fn(info["corp_code"])
                except Exception as e:
                    item[label] = {"error": f"{type(e).__name__}: {e}"}
            stocks[code] = item
        out["종목"] = stocks

    if errors:
        out["_실패항목"] = errors
    if len(out) == 1:
        out["error"] = "옵션 없음 — --disclosures YYYYMMDD 또는 --stocks 코드,코드"
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
