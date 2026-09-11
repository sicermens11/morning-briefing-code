#!/usr/bin/env python3
"""
fetch_stock.py — 후보 종목별 리서치·컨센서스·수급 직접 수집 (2026-08-25 신설)

대체 대상: STEP3의 [조건부-C + 컨센서스 + 조건부-D2 1순위 통합] 배치.
  이전에는 `web_fetch_exa(urls=[...3개...])`로 네이버 URL을 후보당 1회 배치 호출했다.

왜 바꾸나 (실측 근거):
  1. **Exa가 87자짜리 응답에서 타임아웃을 냈다.** 2026-08-25 브리핑 로그:
     "조건부-C 배치에서 엘에스일렉트릭 consensus URL만 CRAWL_LIVECRAWL_TIMEOUT 실패 →
      해당 종목 컨센서스 스냅샷 생략". 직접 호출하면 즉시 반환된다(응답 87자).
  2. 같은 계열인 MCP-10~15가 Exa 경유 시 일주일 낡은 데이터를 반환하던 것이 실측됐다.
     이 세 항목도 같은 경로를 쓰고 있었다.
  3. 조건부-C는 **점수에 직접 반영된다**(목표주가 상향 +1 / 하향 -2). 데이터가 낡거나
     빠지면 등급이 틀어진다 — MCP-10~15(서술 전용)보다 정확도 요구가 높다.

⚠️ 판정은 하지 않는다. 이 스크립트는 **수집만** 한다.
   상향/하향 판정, 30일 경과 여부, 갭③ 충족 여부는 SKILL.md STEP3·STEP4 규칙대로 모델이 한다.
   (점수 판정을 스크립트에 넣으면 규칙 변경이 두 곳으로 갈라진다.)

사용:
    run-py.ps1 -Script fetch_stock.py -Args @('--codes','010120,329180')

출력(stdout, JSON):
  {"fetched_at": "...", "stocks": {"010120": {"리서치": [...], "컨센서스": {...}, "수급": [...]}}}
  항목별로 실패하면 그 키에 {"error": "..."}가 들어간다(다른 항목은 정상 반환).
"""
import concurrent.futures as cf
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://m.stock.naver.com/",
    "Accept": "application/json",
}

# 리서치 목록은 원문이 길다(1건당 미리보기 수백 자). 브리핑이 실제로 쓰는 건
# "30일 이내인가 / 제목에 상향·하향·신규커버리지가 있는가"뿐이라 상위 N건만 남긴다.
# ⚠️⚠️ 4건 → 8건 (2026-08-31). **같은 날 여러 증권사가 내면 이력이 통째로 잘렸다** —
#    현대로템은 4건 중 3건이 07-27이라 **닷새 범위밖에 못 봤다.** 30일 판정에는 충분해도
#    "의견이 오르는 추세인가 내리는 추세인가"는 그 범위로 알 수 없다.
#    ⚠️ 추가 호출은 0회다. 스냅샷에 미리보기 300자 × 4건이 더 쌓일 뿐이다.
RESEARCH_KEEP = 8
PREVIEW_CHARS = 300


def get(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MAP_PATH = os.path.join(_DATA, "value-chain-map.md")
CORPCODE_PATH = os.path.join(_DATA, "dart-corpcode.json")
PEER_MAX = 8


def _load_corpcode():
    """`{종목코드: {corp_code, corp_name}}` → 코드↔이름 양방향 표."""
    with open(CORPCODE_PATH, "r", encoding="utf-8-sig") as fp:
        raw = json.load(fp)
    code2name, name2code = {}, {}
    for code, v in raw.items():
        nm = v.get("corp_name") if isinstance(v, dict) else v
        if nm:
            code2name[code] = nm
            name2code.setdefault(nm, code)
    return code2name, name2code


def _load_map_sectors():
    """`### 섹터명` 아래의 OR-쿼리 줄들에서 종목명을 뽑아 {섹터: [종목명...]}으로."""
    sectors, cur = {}, None
    with open(MAP_PATH, "r", encoding="utf-8-sig") as fp:
        for line in fp:
            line = line.rstrip()
            m = re.match(r"^###\s+(.+?)\s*(?:\(.*\))?\s*$", line)
            if m:
                cur = m.group(1).strip()
                sectors.setdefault(cur, [])
                continue
            if not cur:
                continue
            # 서브체인이 있는 섹터(반도체)는 OR-줄이 여러 개다 — 전부 합친다.
            q = re.search(r'`"(.+?)\s*\[이슈 키워드\]"`', line)
            if q:
                for nm in q.group(1).split(" OR "):
                    nm = nm.strip()
                    if nm and nm not in sectors[cur]:
                        sectors[cur].append(nm)
    return sectors


def map_peers(code: str):
    """가치사슬맵에서 **같은 섹터** 종목을 찾는다. (2026-08-26 신설)

    ⚠️ 왜 네이버 `industryCompareInfo`를 안 쓰나 — 그 필드는 네이버 **업종** 분류라
    실제 동종업계가 아니다. 2026-08-26 실측: 성광벤드(피팅 제조)의 동종업계가
    **두산에너빌리티·레인보우로보틱스·두산로보틱스**로 나왔다("기계" 업종으로 묶인 것).
    이 값을 "섹터 전체가 오른 건지 이 종목만 오른 건지"의 근거로 쓰면 판단이 통째로 틀어진다.
    가치사슬맵은 **납품·수주 관계가 확인된** 종목 묶음이라 그 질문에 맞는 비교군이다.

    반환: (섹터명, [(종목명, 코드), ...], [다른 소속 섹터...]) — 맵에 없으면 (None, [], []).
    """
    try:
        code2name, name2code = _load_corpcode()
        me = code2name.get(code)
        if not me:
            return None, [], []
        sectors = _load_map_sectors()
        # ⚠️ 한 종목이 **두 섹터에 등재**될 수 있다(2026-08-26 실측: 한화시스템·켄코아에어로스페이스가
        #    방산·우주 양쪽에 있다 — 실제로 두 사업을 다 한다). 맵 순서상 먼저 나온 섹터를 쓰되,
        #    **다른 소속을 조용히 버리지 않고 함께 돌려준다.** 그래야 브리핑이 "이 종목은 방산으로
        #    비교했지만 우주 소속이기도 하다"를 알고 서술할 수 있다.
        owned = [s for s, names in sectors.items() if me in names]
        if not owned:
            return None, [], []
        sector = owned[0]
        peers = []
        for nm in sectors[sector]:
            if nm == me:
                continue
            c = name2code.get(nm)
            if c:
                peers.append((nm, c))
            if len(peers) >= PEER_MAX:
                break
        return sector, peers, owned[1:]
    except Exception:
        return None, [], []


def classify_missing(code: str):
    """시세가 안 잡히는 종목이 **죽은 것인지 일시적 실패인지** 가른다. (2026-08-26 신설)

    ⚠️ 이게 없으면 죽은 종목이 그냥 "조회 실패"로 조용히 사라진다.
    `quote_from_series`는 30일 창으로 보므로, 반년 전에 거래가 멈춘 종목은 0행이 돼
    실패로 처리된다 — **없어진 게 아니라 안 보이게 되는 것**이라 더 나쁘다.
    실패한 종목에 한해서만 넓은 창으로 한 번 더 확인하므로 평소 비용은 0이다.

    반환: {"상태": "거래멈춤"|"데이터없음"|"일시실패", "마지막거래일": ...}
    """
    try:
        end = datetime.now(KST)
        start = end - timedelta(days=400)
        raw = urllib.request.urlopen(urllib.request.Request(
            "https://api.finance.naver.com/siseJson.naver"
            f"?symbol={code}&requestType=1&startTime={start:%Y%m%d}"
            f"&endTime={end:%Y%m%d}&timeframe=day", headers=HEADERS), timeout=15
        ).read().decode("utf-8", errors="replace")
        rows = [r for r in json.loads(raw.replace("'", '"'))[1:] if isinstance(r, list)]
        if not rows:
            return {"상태": "데이터없음", "마지막거래일": None}
        return {"상태": "거래멈춤", "마지막거래일": str(rows[-1][0])}
    except Exception:
        return {"상태": "일시실패", "마지막거래일": None}


def quote_from_series(code: str):
    """일봉 마지막 두 행으로 종가·등락률을 낸다.

    장중이든 개장 전이든 **같은 함수**로 처리된다 — 장중에는 마지막 행이 실시간 값이고
    (2026-08-26 11:30 실측: 성광벤드 마지막 행 종가가 현재가 29,650과 일치),
    개장 전에는 전일 행이 마지막이라 자연히 전일 기준이 된다.
    """
    chg = prev_session_change(code, with_price=True)
    return chg


def _as_float(v) -> float:
    """네이버가 숫자를 문자열로도 준다. 못 읽으면 0으로 본다.

    ⚠️ **`%`·`+`·콤마를 전부 벗긴다.** 지분율은 `"27.19%"` 꼴로 오는데 콤마만 벗기면
       `float("27.19%")`가 터져 **조용히 0이 된다**(2026-08-26에 외국인지분율 추이가
       전부 0.0으로 나와서 발견했다 — 에러가 아니라 0이라 알아채기 어렵다).
    """
    try:
        return float(str(v).replace(",", "").replace("%", "").replace("+", "").strip())
    except (TypeError, ValueError):
        return 0.0


def prev_session_change(code: str, with_price: bool = False):
    """일봉 종가 마지막 두 개로 등락률(%)을 직접 계산한다.
    `with_price=True`면 `{"종가":…, "등락률":…, "기준일":…}`을 돌려준다.

    개장 전에는 실시간 등락률이 전부 0이라 이 경로가 유일한 수단이다.
    fetch_us.py가 야후 지수에서 `chartPreviousClose`를 버리고 종가 시계열로 계산한 것과
    같은 이유다 — 제공되는 '등락' 필드가 어느 구간 기준인지 신뢰할 수 없다.
    """
    try:
        end = datetime.now(KST)
        start = end - timedelta(days=30)  # 연휴가 껴도 2거래일은 확보되는 여유
        raw = urllib.request.urlopen(urllib.request.Request(
            "https://api.finance.naver.com/siseJson.naver"
            f"?symbol={code}&requestType=1&startTime={start:%Y%m%d}"
            f"&endTime={end:%Y%m%d}&timeframe=day", headers=HEADERS), timeout=15
        ).read().decode("utf-8", errors="replace")
        rows = [r for r in json.loads(raw.replace("'", '"'))[1:] if isinstance(r, list)]
        if len(rows) < 2:
            return None
        last, prev = float(rows[-1][4]), float(rows[-2][4])
        if prev == 0:
            return None
        pct = round((last - prev) / prev * 100, 2)
        if with_price:
            return {"종가": last, "등락률": pct, "기준일": str(rows[-1][0])}
        return pct
    except Exception:
        return None  # 동종업계는 보조 정보다. 실패해도 본 수집을 막지 않는다.


def build_peers(code: str, integration: dict) -> dict:
    """동종업계 비교군을 만든다. **가치사슬맵 같은 섹터가 1순위**, 네이버 업종은 폴백.

    용도는 하나다 — "섹터 전체가 오른 건지 이 종목만 오른 건지" 구분.
    그 질문에는 **납품·수주 관계가 확인된 묶음**(가치사슬맵)이 맞는 비교군이다.
    """
    sector, peers, also = map_peers(code)
    if peers:
        rows, errs = [], []
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(quote_from_series, c): (nm, c) for nm, c in peers}
            for f in cf.as_completed(futs):
                nm, c = futs[f]
                try:
                    q = f.result()
                except Exception:
                    q = None
                if q:
                    rows.append({"종목": nm, "코드": c, **q})
                else:
                    errs.append((nm, c))

        # ⚠️ **거래가 멈춘 종목을 비교군에서 뺀다** (2026-08-26 신설).
        #    상장폐지·합병된 종목은 시세 조회가 **에러 없이 성공**하고 옛날 종가를 정상적으로
        #    돌려준다. 그래서 그냥 두면 8개월 전 가격이 오늘 가격과 나란히 놓여 섹터 판단이
        #    통째로 망가진다 — 실제로 `에이치디현대미포`(마지막 거래 2025-12-12)가 8개월간
        #    맵에 남아 `조선 본선` 섹터 상관을 0.371(무의미)로 끌어내리고 있었다.
        #    맵 정기 점검(`check_map_health.py`)은 09·04월에만 도니, 그 사이에 죽는 종목은
        #    여기서 걸러야 한다. 판단 기준은 **다수 종목의 최신 거래일**이라 휴장일 달력이 필요 없다.
        if len(rows) >= 3:
            cnt = {}
            for r in rows:
                cnt[r["기준일"]] = cnt.get(r["기준일"], 0) + 1
            latest = max(cnt, key=cnt.get)
            fresh, dropped = [], []
            for r in rows:
                try:
                    behind = (datetime.strptime(latest, "%Y%m%d")
                              - datetime.strptime(r["기준일"], "%Y%m%d")).days
                except Exception:
                    behind = 0
                (dropped if behind >= 10 else fresh).append(
                    {**r, "뒤처짐일": behind} if behind >= 10 else r)
            rows = fresh
        else:
            dropped = []

        # 조회가 아예 안 된 종목은 **죽은 것인지 일시적 실패인지** 갈라준다.
        # 그냥 "실패"로 묻으면 상장폐지 종목이 맵에 영원히 남는다.
        temp_fail = []
        for nm, c in errs:
            info = classify_missing(c)
            if info["상태"] == "일시실패":
                temp_fail.append(nm)
            else:
                dropped.append({"종목": nm, "코드": c, "기준일": info["마지막거래일"],
                                "사유": info["상태"]})

        rows.sort(key=lambda r: r["등락률"], reverse=True)
        res = {"기준": "가치사슬맵 동일섹터", "섹터": sector, "종목수": len(rows), "목록": rows}
        if also:
            res["다른섹터_소속"] = also
            res["_참고"] = (f"이 종목은 '{sector}'로 비교했지만 {', '.join(also)} 소속이기도 하다. "
                            "재료가 그쪽 섹터 것이면 비교군이 맞지 않을 수 있으니 서술에 반영할 것.")
        if temp_fail:
            res["조회실패"] = temp_fail
        if dropped:
            res["거래멈춤_제외"] = dropped
            res["_조치"] = ("아래 종목은 거래가 멈췄거나 시세 데이터가 없어 비교군에서 제외했다"
                            "(상장폐지·합병 의심). **STEP8 실행 로그에 그대로 남겨** 다음 맵 갱신에서 "
                            "정리할 것 — 놔두면 섹터 판단이 계속 오염된다.")
        return res

    # 폴백 — 맵에 없는 종목(2026-08-26부터 맵 밖도 후보가 될 수 있다).
    # ⚠️ 네이버 `industryCompareInfo`는 **업종** 분류라 실제 동종업계가 아닐 수 있다.
    #    성광벤드(피팅)의 비교군이 두산에너빌리티·두산로보틱스로 나온 실측이 있다.
    #    그래서 `기준` 필드에 그 사실을 박아 넘긴다 — 브리핑이 이걸 보고 신뢰도를 조절한다.
    raw = [{
        "종목": x.get("stockName"), "코드": x.get("itemCode"),
        "종가": x.get("closePrice"), "등락률": x.get("fluctuationsRatio"),
        # ⚠️ `threeMonthEarningRate`는 넣지 않는다. 2026-08-26 실측에서 전부 'N/A'였다.
    } for x in (integration.get("industryCompareInfo") or [])[:6]]

    # ⚠️ 개장 전(브리핑이 도는 08:00)에는 `fluctuationsRatio`가 전부 0.00이다 — 당일 세션
    #    기준 값이라 장이 안 열렸으면 등락이 있을 수 없다. 전부 0이면 일봉으로 직접 계산한다.
    if raw and all(_as_float(p["등락률"]) == 0.0 for p in raw):
        for p in raw:
            chg = prev_session_change(p["코드"])
            p["등락률"] = chg if chg is not None else p["등락률"]
    return {
        "기준": "네이버 업종분류(폴백)",
        "_주의": "가치사슬맵 미등재 종목이라 네이버 업종분류로 대체했다. **실제 동종업계가 아닐 수 "
                 "있다** — 2026-08-26 실측에서 아스플로(반도체 가스부품)와 링크솔루션(우주 부품)이 "
                 "'기계' 업종으로 묶여 **완전히 같은 비교군**(두산에너빌리티·레인보우로보틱스·"
                 "HD건설기계)을 받았다. 종목 구성을 먼저 보고, 후보와 사업이 무관하면 "
                 "**섹터 전반 판단(💡 섹터 참고·⚡ 섹터 강세)의 근거로 쓰지 않는다.** "
                 "이 종목은 STEP8 `unmapped`에 넣어 다음 갱신에 맵으로 편입시킨다.",
        "종목수": len(raw), "목록": raw,
    }


def trade_status(code: str) -> dict:
    """거래정지·상장폐지 여부. (2026-08-26 신설)

    ⚠️ **상장폐지 종목은 `/basic`이 HTTP 409를 던진다** — 이게 가장 싸고 빠른 판별이다.
    지금까지는 400일 시세를 받아 마지막 거래일을 보고 알아냈는데, 그건 무겁고
    **에러가 안 나서** 놓치기 쉬웠다(`에이치디현대미포`가 8개월간 맵에 남아 있었다).
    후보 종목 자체가 거래정지 상태면 진입 조건을 걸어도 의미가 없으므로 미리 알린다.
    """
    try:
        d = get(f"https://m.stock.naver.com/api/stock/{code}/basic")
        st = (d.get("tradeStopType") or {}).get("name")
        return {
            "거래가능": d.get("tradableStatus") == "tradable",
            "상태": st, "시장상태": d.get("marketStatus"),
        }
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return {"거래가능": False, "상태": "상장폐지·거래불가(HTTP 409)",
                    "_조치": "맵에서 제거하고 후보에서 뺄 것"}
        return {"error": f"HTTPError {e.code}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def financials(code: str) -> dict:
    """네이버 연간 재무제표 3개년. (2026-08-26 신설 — 강화-F2 대체)

    ⚠️ 대조 검증(2026-08-26): 브리핑이 MCP `koreaStockAnalyz-get_financials`로 받았던
       **부채비율이 완전히 일치**했다(효성중공업 190.31 · LIG 446.35).
       순이익률도 8.43 vs 8.42로 반올림 차이뿐이다.
       → **재무취약 판정의 두 조건(부채비율 200%+ / 순이익률 음수)은 이 값으로 대체 가능**하다.

    ⚠️ **ROE는 MCP와 값이 다르다**(효성중공업 24.41 vs 20.2). 산출 기준이 달라서다.
       서술에 쓸 때 **출처를 섞지 말 것** — 한 브리핑 안에서는 한쪽만 쓴다.

    ⚠️ **마지막 열은 컨센서스 추정치라 버린다.** 삼성전자 2026년 영업이익률이 53.05%로
       찍히는 식이라 그대로 쓰면 판정이 망가진다. **확정된 3개년만** 돌려준다.
    """
    KEEP = ("매출액", "영업이익", "당기순이익", "영업이익률", "순이익률",
            "ROE", "부채비율", "당좌비율", "EPS", "PER", "PBR", "BPS")
    try:
        fi = get(f"https://m.stock.naver.com/api/stock/{code}/finance/annual").get("financeInfo") or {}
        periods = [t.get("title") for t in fi.get("trTitleList") or []]
        if not periods:
            return {"error": "기간 정보 없음"}
        keep_n = max(0, len(periods) - 1)          # 마지막(추정치) 제외
        out = {"기간": periods[:keep_n], "_주의": "마지막 컨센서스 추정 열은 제외했다"}
        for row in fi.get("rowList") or []:
            title = row.get("title")
            if title not in KEEP:
                continue
            vals = [v.get("value") for _, v in sorted((row.get("columns") or {}).items())]
            out[title] = vals[:keep_n]
        return out
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def quarterly(code: str) -> dict:
    """분기 재무 6개 분기. (2026-08-26 신설)

    ⚠️ 왜 필요한가 — 지금까지 **연간만** 봤다. 그러면 **최근 분기의 꺾임을 반년 뒤에야 안다.**
       "작년 좋았다"와 "지난 분기부터 나빠지는 중이다"는 전혀 다른 이야기인데 구분이 안 됐다.

    ⚠️ 마지막 열은 **추정치일 수 있다**(`-`가 섞이면 미확정 분기다). 확정된 것만 추세로 읽는다.
    """
    KEEP = ("매출액", "영업이익", "당기순이익", "영업이익률", "순이익률", "ROE", "부채비율", "EPS")
    try:
        fi = get(f"https://m.stock.naver.com/api/stock/{code}/finance/quarter").get("financeInfo") or {}
        periods = [t.get("title") for t in fi.get("trTitleList") or []]
        if not periods:
            return {"error": "분기 정보 없음"}
        out = {"분기": periods}
        for row in fi.get("rowList") or []:
            if row.get("title") in KEEP:
                out[row["title"]] = [v.get("value")
                                     for _, v in sorted((row.get("columns") or {}).items())]
        out["_주의"] = ("`-`는 미확정 분기다. **확정된 분기만** 추세로 읽는다. "
                        "직전 분기 대비 꺾임이 보이면 연간 지표가 좋아도 주의 신호다.")
        return out
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def _isin(code: str) -> str:
    r"""6자리 종목코드 → ISIN. KRX 공매도 API가 ISIN을 요구하는데, 조회 호출을 하나
    더 쓰지 않으려고 계산한다. 한국 주식 ISIN = `KR7` + 6자리 + `00` + 체크디짓(Luhn).
    2026-08-27 검증: 003160·009540·034020·086390·005930 전부 실데이터 반환.
    """
    body = "KR7" + code + "00"
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in body)
    total, dbl = 0, True
    for ch in reversed(digits):
        d = int(ch)
        if dbl:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        dbl = not dbl
    return body + str((10 - total % 10) % 10)


_KRX_OPENER = None


def _krx_session():
    r"""KRX는 **세션 쿠키(JSESSIONID)가 없으면 POST가 전부 HTTP 400**이다.
    화면 로더를 한 번 GET해서 쿠키를 받아둔다. 이게 이전 시도들이 실패한 이유 중 하나였다.
    """
    global _KRX_OPENER
    if _KRX_OPENER is None:
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        op.open(urllib.request.Request(
            "https://data.krx.co.kr/comm/srt/srtLoader/index.cmd?screenId=MDCSTAT301",
            headers={"User-Agent": HEADERS["User-Agent"]}), timeout=20).read()
        _KRX_OPENER = op
    return _KRX_OPENER


def short_selling(code: str, days: int = 20) -> dict:
    r"""KRX 개별종목 공매도 거래. (2026-08-27 신설 — 오래 "최대 공백"이던 항목)

    ⚠️ **왜 그동안 못 가져왔나 — 두 가지가 동시에 틀렸다.**
       ① 경로: `dbms/MDC/STAT/srt/MDCSTAT301xx`로 찍어봤는데 실제로는
          **`dbms/MDC_OUT/STAT/srt/MDCSTAT30102_OUT`** 이다(`MDC_OUT` + `_OUT` 접미사).
          화면 ID(`MDCSTAT301`)와 데이터 ID가 달라 추측으로는 못 맞힌다.
       ② 세션: 쿠키 없이 POST하면 전부 400이다.
       찾은 경로 — **네이버 공매도 페이지가 KRX를 iframe으로 박아두고 있었고**
       (`finance.naver.com/item/short_trade.naver` → `data.krx.co.kr/.../srtLoader`),
       그 iframe HTML 안에 실제 bld 경로가 들어 있었다.

    ⚠️ **점수·등급에 반영하지 않는다(2026-08-27 사용자 결정, A안).**
       "공매도가 늘면 떨어진다"는 검증된 적 없는 실증 주장이다. 서술로만 쓰고
       스냅샷에 쌓아 9월 하순에 점수화 여부를 판단한다.

    ⚠️ **오늘 날짜 행은 항상 뺀다.** 공매도 집계는 장 마감 후에 확정되는데, 장중에 부르면
       전체거래량은 쌓여 있고 공매도만 `0`이라 **비중이 0.00으로 와 평균을 끌어내린다.**
       2026-08-27 10시대 실측: 오늘 행을 넣으면 디아이 최근5일이 1.19%로 나왔다.
       브리핑은 08:00 개장 전에 도니 오늘 행은 어차피 쓸 값이 아니다.
    """
    end = datetime.now(KST)
    start = end - timedelta(days=max(days * 2, 30))
    body = {
        "bld": "dbms/MDC_OUT/STAT/srt/MDCSTAT30102_OUT", "locale": "ko_KR",
        "isuCd": _isin(code), "isuCd2": code,
        "strtDd": start.strftime("%Y%m%d"), "endDd": end.strftime("%Y%m%d"),
        "share": "1", "money": "1", "csvxls_isNo": "false", "inqCondTpCd": "1",
    }
    op = _krx_session()
    r = op.open(urllib.request.Request(
        "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
        data=urllib.parse.urlencode(body).encode(),
        headers={"User-Agent": HEADERS["User-Agent"], "Referer": "https://data.krx.co.kr/",
                 "X-Requested-With": "XMLHttpRequest",
                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}),
        timeout=25)
    rows = json.loads(r.read().decode("utf-8", "replace")).get("OutBlock_1") or []
    today = end.strftime("%Y/%m/%d")
    live = [x for x in rows
            if _as_float(x.get("ACC_TRDVOL")) > 0 and x.get("TRD_DD") != today]
    if not live:
        return {"error": "공매도 데이터 없음(신규상장·거래정지 등)"}

    wt = [_as_float(x["TRDVOL_WT"]) for x in live if x.get("TRDVOL_WT")]
    recent, prior = wt[:5], wt[5:]
    out = {
        "기준일": live[0]["TRD_DD"],
        "최근비중pct": _as_float(live[0].get("TRDVOL_WT")),
        "유효거래일": len(live),
        "일별": [{"거래일": x["TRD_DD"], "공매도수량": x["CVSRTSELL_TRDVOL"],
                  "전체거래량": x["ACC_TRDVOL"], "비중pct": _as_float(x.get("TRDVOL_WT"))}
                 for x in live[:days]],
        "_주의": ("⚠️ 점수·등급 미반영(2026-08-27). 서술 전용이다. "
                   "공매도 비중이 높다=나쁘다는 검증된 적 없다 — "
                   "재료가 터지면 숏커버로 상승이 증폭될 수도 있다. 사실만 쓴다."),
    }
    if recent:
        out["최근5일평균pct"] = round(sum(recent) / len(recent), 2)
    if recent and prior:
        a, b = sum(recent) / len(recent), sum(prior) / len(prior)
        out["직전평균pct"] = round(b, 2)
        out["추세"] = "급증" if a > b * 1.5 else ("감소" if a < b * 0.67 else "평상")
    return out


def fetch_one(code: str) -> dict:
    out = {}
    out["거래상태"] = trade_status(code)
    out["재무3개년"] = financials(code)
    out["분기6개"] = quarterly(code)
    # ⚠️ 공매도는 KRX 세션이 필요해 실패 가능성이 다른 항목보다 높다.
    #    실패해도 나머지 수집을 막지 않는다(다른 항목과 동일 원칙).
    try:
        out["공매도"] = short_selling(code)
    except Exception as e:
        out["공매도"] = {"error": f"{type(e).__name__}: {e}"}

    # --- 리서치 리포트 목록 (조건부-C) ---
    try:
        raw = get(f"https://m.stock.naver.com/api/research/stock/{code}")
        items = raw if isinstance(raw, list) else (raw.get("list") or [])
        out["리서치"] = [{
            "제목": r.get("title"),
            "증권사": r.get("brokerName"),
            "작성일": r.get("writeDate"),
            "researchId": r.get("researchId"),
            # 상향/하향 판정에 제목만으로 부족할 때 모델이 읽을 근거. 길어서 잘라 넣는다.
            "미리보기": (r.get("previewContent") or "")[:PREVIEW_CHARS],
        } for r in items[:RESEARCH_KEEP]]
    except Exception as e:
        out["리서치"] = {"error": f"{type(e).__name__}: {e}"}

    # --- 투자자별 수급 10거래일 (조건부-D2 1순위 → 갭③ + 등급조정 연속판정) ---
    #
    # ⚠️ **10거래일치인 것이 중요하다.** 등급조정 규칙에 "외국인 **5거래일 연속** 순매도"가
    #    있는데, 이전에는 스냅샷 1~3일치뿐이라 연속 여부를 확정할 수 없어
    #    "확정되지 않으면 등급을 깎지 않는다"로 회피하고 있었다(허위 근거 방지).
    #    10일치가 있으면 **연속 판정이 추론이 아니라 계산**이 된다.
    try:
        rows = get(f"https://m.stock.naver.com/api/stock/{code}/trend")
        if not isinstance(rows, list):
            rows = rows.get("list") or []
        def _chg_pct(close, diff):
            """⚠️ **갭④ 판정의 정본** (2026-08-27 신설).

            `등락`은 원 단위라 모델이 매번 손으로 %를 계산하고 있었다. 여기서 낸다.
            전일 종가 = 종가 − 등락 이므로 등락률 = 등락 ÷ (종가 − 등락) × 100.

            ⚠️ **왜 이게 정본인가** — 규칙(점수표)은 갭④를 `강화-P`의 `change_rate`로
               판정하라고 지정하는데, 그건 `koreaStock-stock_get_quote`의 **당일 실시간** 값이다.
               브리핑은 **08:00 개장 전**에 돌아서 그 값이 **항상 0으로 온다.**
               2026-08-26·08-27 이틀 연속 4종목 전부 `change_rate=0`이었고, 모델이 매번
               이 필드로 우회 계산했다. 규칙이 지정한 소스가 구조적으로 못 쓰는 값이었던 것이다.
            """
            c, d = _as_float(close), _as_float(diff)
            base = c - d
            return round(d / base * 100, 2) if base else None

        out["수급10일"] = [{
            "거래일": r.get("bizdate"),
            "외국인순매수수량": r.get("foreignerPureBuyQuant"),
            "기관순매수수량": r.get("organPureBuyQuant"),
            "개인순매수수량": r.get("individualPureBuyQuant"),
            "외국인지분율": r.get("foreignerHoldRatio"),
            "종가": r.get("closePrice"),
            "등락": r.get("compareToPreviousClosePrice"),
            "등락률pct": _chg_pct(r.get("closePrice"),
                                  r.get("compareToPreviousClosePrice")),
        } for r in rows[:10]]
        # 외국인 지분율 10거래일 변화. (2026-08-26 신설)
        # ⚠️ 이 값은 **원래부터 오고 있었는데 규칙 어디에도 없어 안 쓰이고 있었다.**
        #    갭③은 **하루치 순매수**만 본다 — 그날 하루 우연히 산 것과 열흘째 꾸준히
        #    늘리는 것이 같은 +1점을 받는다. 지분율 추이는 그 둘을 갈라준다.
        #    실측(2026-08-26): 효성중공업 26.70→27.19(+0.49%p) · LIG 26.66→27.24(+0.58%p)
        #    둘 다 10거래일 단조 증가였다.
        try:
            seq = [(_as_float(r["외국인지분율"]), r["거래일"]) for r in out["수급10일"]
                   if r.get("외국인지분율")]
            if len(seq) >= 5:
                new, old = seq[0], seq[-1]
                rising = sum(1 for i in range(len(seq) - 1) if seq[i][0] >= seq[i + 1][0])
                out["외국인지분율추이"] = {
                    "최근": new[0], "기준일": new[1], "N일전": old[0], "시작일": old[1],
                    "변화pct_p": round(new[0] - old[0], 2),
                    "관측일수": len(seq),
                    "증가일비율": f"{rising}/{len(seq) - 1}",
                    "_주의": ("갭③은 **하루치 순매수**만 본다. 이 값은 **열흘째 꾸준히 늘리는지**를 "
                              "보여준다 — 같은 갭③ +1점이라도 무게가 다르다. ⚠️ 점수·등급 미반영."),
                }
        except Exception:
            pass
    except Exception as e:
        out["수급10일"] = {"error": f"{type(e).__name__}: {e}"}

    # --- 통합 정보 (컨센서스 + 동종업계 비교 + 예정 이벤트) ---
    #
    # `integration` 한 번에 여러 블록이 함께 온다. 그중 브리핑에 쓸 것만 추린다.
    # **동종업계 비교(industryCompareInfo)는 이전에 아예 없던 정보다** — 후보가 같은 업종
    # 안에서 상대적으로 어디쯤인지(밸류에이션·등락률) 보면 "섹터 전체가 오른 건지, 이 종목만
    # 오른 건지"를 구분할 수 있다. 지금은 '💡 섹터 참고' 플래그를 텍스트 추정으로 붙이고 있다.
    try:
        d = get(f"https://m.stock.naver.com/api/stock/{code}/integration")

        ci = d.get("consensusInfo") or {}
        out["컨센서스"] = {
            "기준일": ci.get("createDate"),
            "의견점수": ci.get("recommMean"),
            "목표주가": ci.get("priceTargetMean"),
        } if ci else {"error": "컨센서스 없음(커버리지 미달 종목)"}

        out["당일시세"] = {i.get("key"): i.get("value")
                           for i in (d.get("totalInfos") or [])
                           if i.get("key") in ("전일", "시가", "고가", "저가", "거래량", "대금")}

        out["동종업계"] = build_peers(code, d)

        ev = {}
        if d.get("shareholdersMeetingInfo"):
            ev["주총"] = d["shareholdersMeetingInfo"]
        if d.get("irScheduleInfo"):
            ev["IR일정"] = d["irScheduleInfo"]
        if ev:
            out["예정이벤트"] = ev
    except Exception as e:
        out["통합정보"] = {"error": f"{type(e).__name__}: {e}"}

    return out


def main():
    argv = sys.argv[1:]
    if "--codes" not in argv:
        print(json.dumps({"error": "--codes 010120,329180 형식으로 종목코드 필요"},
                         ensure_ascii=False))
        return
    codes = [c.strip() for c in argv[argv.index("--codes") + 1].split(",") if c.strip()]

    stocks = {}
    for c in codes:
        try:
            stocks[c] = fetch_one(c)
        except Exception as e:
            stocks[c] = {"error": f"{type(e).__name__}: {e}"}

    print(json.dumps({
        "fetched_at": datetime.now(KST).isoformat(timespec="seconds"),
        "stocks": stocks,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()


