#!/usr/bin/env python3
r"""
fetch_sector_news.py — 13개 섹터 뉴스를 매일 전수 스캔 (2026-08-25 신설)

무엇을 푸나:
  기존 MCP-7은 뉴스검색 슬롯이 최대 4개뿐이라 13개 섹터를 다 볼 수 없었다.
  그래서 "국내독립 2순위" 슬롯 하나로 7개 섹터를 **요일별로 돌려가며** 확인했다.
  DECISIONS.md 129차에 그 한계가 그대로 적혀 있다:

      "완전한 매일 커버리지(7개 섹터 매일 전수확인)는 슬롯 1개로는 구조적으로 불가능함을
       설명(7개 섹터에 슬롯 1개씩 배정하려면 하루 7슬롯 필요, 예산상 비현실적)"

  → 그 제약은 **MCP 호출 예산** 때문이었다. 로컬에서 직접 부르면 예산이 걸리지 않으므로
     13개 섹터를 매일 전부 훑을 수 있다. 요일 분산이 필요 없어진다.

  덤: DECISIONS.md 117차에서 "대체후보를 찾을 방법이 없어 실행 불가능"이라 완화됐던
      섹터다양성 규칙("미조회 섹터로 교체")도 다시 실행 가능해진다.

⚠️ 토큰 비용 주의 — 그래서 **필터링이 이 스크립트의 핵심**이다.
   13섹터 뉴스를 통째로 반환하면 컨텍스트가 커져 비용이 되레 는다.
   그래서 (1) 최근 N일 이내 (2) 제목에 신호 키워드가 있는 것 (3) 섹터당 상위 K건
   세 겹으로 걸러 **섹터당 2~3건, 전체 3,000자 안팎**만 내보낸다.

출처: 구글뉴스 RSS (키 불필요). 네이버 검색 API는 키가 필요해 일부러 피했다.

사용:
    run-py.ps1 -Script fetch_sector_news.py
    run-py.ps1 -Script fetch_sector_news.py -Args @('--days','2','--per-sector','2')
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# value-chain-map.md의 13개 `###` 섹터와 1:1 대응.
# 쿼리는 "그 섹터에서 재료가 터졌는가"를 잡도록 수주·계약 중심으로 짰다.
# ⚠️ 쿼리에 따옴표를 넣어 **구절 검색**으로 묶는다.
#    2026-08-25 첫 실행에서 단어 나열식 쿼리가 엉뚱한 기사를 끌어왔다 —
#    "사이버보안 공급계약 수주"에 두산에너빌리티 가스복합발전소 기사가 잡히고,
#    "2차전지 소재 공급계약"에 LS일렉트릭 데이터센터 기사가 잡혔다.
#    구글이 단어를 흩어서 매칭하기 때문이다. 핵심어를 따옴표로 고정하면 걸러진다.
SECTORS = {
    "조선기자재": '"조선기자재" OR "선박 기자재" 수주',
    "조선본선": '"조선" (수주 OR 발주) (선박 OR 운반선 OR 컨테이너선)',
    "방산": '"방산" (수출 OR 수주 OR 계약)',
    "원전기자재": '("원전" OR "SMR") (수주 OR 공급계약)',
    "전력인프라": '("변압기" OR "전력기기" OR "배전반") (수주 OR 공급)',
    "2차전지소부장": '("2차전지" OR "배터리 소재" OR "양극재") (수주 OR 공급계약)',
    "휴머노이드로봇": '("로봇" OR "감속기" OR "액추에이터") (수주 OR 공급계약 OR 양산)',
    "바이오CDMO": '("CDMO" OR "위탁생산") (수주 OR 계약)',
    "의료기기디지털헬스": '"의료기기" (인허가 OR 공급 OR 수주)',
    "사이버보안": '("사이버보안" OR "정보보안") (공급 OR 수주 OR 계약)',
    "AI소프트웨어": '("AI 솔루션" OR "인공지능 소프트웨어") (수주 OR 공급계약)',
    "우주": '("위성" OR "발사체" OR "우주항공") (수주 OR 계약)',
    "반도체HBM소부장": '("HBM" OR "반도체 장비" OR "반도체 소재") (수주 OR 공급계약)',
}

# 제목에 이게 없으면 버린다. "그냥 업계 동향" 기사를 걸러내는 장치다.
SIGNAL = ("수주", "계약", "공급", "납품", "체결", "증설", "투자", "인수",
          "급등", "상한가", "돌파", "최대", "신규", "확대", "선정", "낙찰", "승인")

# 있으면 버린다 — 광고성·전망성 기사.
NOISE = ("전망", "추천주", "테마주 주의", "기고", "칼럼", "오늘의 운세")


def fetch_rss(query: str, days: int, timeout: int = 15):
    """⚠️ `when:Nd` 연산자가 핵심이다.

    구글뉴스 RSS는 기본이 **관련도순**이라, 그냥 검색하면 상위 결과가 두 달 전 기사로
    채워지고 최신 기사는 뒤로 밀린다(2026-08-25 실측: '조선기자재 수주' 상위 5건이
    08-05·06-22·08-20·08-04·08-14). 날짜로 사후 필터링하면 최신 기사가 아예 안 잡혀
    "무신호 섹터"로 잘못 판정된다.

    `when:3d`를 붙이면 검색 단계에서 기간이 걸려 상위가 전부 당일·전일이 된다
    (같은 쿼리가 08-25·08-25·08-23·08-25·08-24로 바뀜).
    """
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(f"{query} when:{days}d") + "&hl=ko&gl=KR&ceid=KR:ko")
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return ET.fromstring(r.read())


def clean_title(t: str):
    """구글뉴스 제목은 '제목 - 언론사' 형태다. 언론사를 떼어 따로 돌려준다."""
    if " - " in t:
        head, _, src = t.rpartition(" - ")
        return head.strip(), src.strip()
    return t.strip(), ""


def scan(days: int, per_sector: int):
    cutoff = datetime.now(KST) - timedelta(days=days)
    out, errors = {}, {}
    seen_titles = set()   # 같은 기사가 여러 섹터에 걸리는 것을 막는다

    for sector, query in SECTORS.items():
        try:
            root = fetch_rss(query, days)
        except Exception as e:
            errors[sector] = f"{type(e).__name__}: {e}"
            continue

        picked = []
        for item in root.findall(".//item"):
            raw = item.findtext("title") or ""
            title, source = clean_title(raw)
            if not title:
                continue
            if not any(k in title for k in SIGNAL):
                continue
            if any(k in title for k in NOISE):
                continue

            pub = item.findtext("pubDate") or ""
            try:
                dt = parsedate_to_datetime(pub).astimezone(KST)
            except Exception:
                continue
            if dt < cutoff:
                continue

            # 제목 앞부분이 같으면 같은 사건으로 보고 건너뛴다(언론사별 중복 기사)
            key = re.sub(r"[^가-힣A-Za-z0-9]", "", title)[:18]
            if key in seen_titles:
                continue
            seen_titles.add(key)

            picked.append({
                "제목": title[:80],
                "언론사": source,
                "일시": dt.strftime("%Y-%m-%d %H:%M"),
                "링크": item.findtext("link"),
            })
            if len(picked) >= per_sector:
                break

        if picked:
            out[sector] = picked

    return out, errors


def main():
    argv = sys.argv[1:]
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else 3
    per = int(argv[argv.index("--per-sector") + 1]) if "--per-sector" in argv else 3

    hits, errors = scan(days, per)
    payload = {
        "fetched_at": datetime.now(KST).isoformat(timespec="seconds"),
        "조회조건": {"최근일수": days, "섹터당최대": per, "전체섹터수": len(SECTORS)},
        "신호포착섹터": list(hits.keys()),
        "무신호섹터": [s for s in SECTORS if s not in hits],
        "섹터별뉴스": hits,
    }
    if errors:
        payload["_실패항목"] = errors
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
