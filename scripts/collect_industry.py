#!/usr/bin/env python3
r"""
collect_industry.py — **업종 분류(표준산업분류)를 받는다** (2026-09-03 신설)

⚠️⚠️ **왜 필요한가 — 우리에겐 진짜 업종 분류가 없었다.**
```
`기본()`의 「업종」    실은 **소속부**다 (관리종목·중견기업부 같은 것)
KRX `SECT_TP_NM`   같다. 소속부다
네이버 integration  `industryCodeType`이 **null**이다
⇒ 77차 port_lab에서 **「종목의 조합」을 시총 구간·낙폭대로 대신**해야 했다
```
✅ **DART 기업개황(`company.json`)에 `induty_code`가 있다** (2026-09-03 실측)
   삼성전자 = **264** (한국표준산업분류: 통신 및 방송장비 제조업)

⚠️ **현재 시점의 업종이다.** 과거에 업종이 바뀐 회사는 반영이 안 된다.
   ⇒ 결과에 그 한계를 명시한다. 대부분의 경우 충분하다.

⚠️⚠️ **DART 한도를 쓴다** (종목당 1회 · 2,766종목).
   **09-04 00:05 공시 백필(900일)이 먼저다.** 그 뒤에 돌린다.

저장: `data/industry.json` → `{종목코드: {업종코드, 업종명, 회사명, 설립일}}`

쓰는 법:
    python scripts\collect_industry.py
    python scripts\collect_industry.py --확인      # 3종목만 시험
"""
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import fetch_dart as D  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "industry.json")
LOG = os.path.join(_BASE, "data", "_industry.log")
_쉼 = 0.06

# ⚠️ 한국표준산업분류 대분류(앞 2자리) — 세분류는 너무 잘게 쪼개져 쓰기 어렵다.
#    「조합을 흩는」 용도라면 **중분류(앞 2자리)**면 충분하다.
대분류 = {
    "01": "농업", "02": "임업", "03": "어업", "05": "석탄광업", "06": "원유·천연가스",
    "07": "금속광업", "08": "비금속광물", "10": "식료품", "11": "음료", "12": "담배",
    "13": "섬유", "14": "의복", "15": "가죽·신발", "16": "목재", "17": "펄프·종이",
    "18": "인쇄", "19": "코크스·석유정제", "20": "화학", "21": "의약품",
    "22": "고무·플라스틱", "23": "비금속광물제품", "24": "1차금속", "25": "금속가공",
    "26": "전자부품·통신장비", "27": "의료·정밀·광학", "28": "전기장비",
    "29": "기계·장비", "30": "자동차", "31": "기타운송장비", "32": "가구",
    "33": "기타제조", "34": "산업용기계수리", "35": "전기·가스", "36": "수도",
    "37": "하수·폐기물", "38": "폐기물처리", "41": "종합건설", "42": "전문건설",
    "45": "자동차판매", "46": "도매", "47": "소매", "49": "육상운송",
    "50": "수상운송", "51": "항공운송", "52": "창고·운송서비스", "55": "숙박",
    "56": "음식점", "58": "출판", "59": "영상·음악", "60": "방송",
    "61": "통신", "62": "컴퓨터프로그래밍", "63": "정보서비스", "64": "금융",
    "65": "보험", "66": "금융지원", "68": "부동산", "69": "임대",
    "70": "연구개발", "71": "전문서비스", "72": "건축기술·엔지니어링",
    "73": "기타전문과학", "74": "사업시설관리", "75": "사업지원",
    "76": "임대업", "84": "공공행정", "85": "교육", "86": "보건",
    "87": "사회복지", "90": "예술·스포츠", "91": "스포츠·오락",
    "94": "협회·단체", "95": "수리업", "96": "기타개인서비스",
}


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 하나(corp, key):
    u = f"https://opendart.fss.or.kr/api/company.json?crtfc_key={key}&corp_code={corp}"
    with urllib.request.urlopen(u, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    if d.get("status") != "000":
        return None, d.get("status")
    코드 = (d.get("induty_code") or "").strip()
    return {"업종코드": 코드, "업종명": 대분류.get(코드[:2], f"기타({코드[:2]})"),
            "회사명": d.get("corp_name"), "설립일": d.get("est_dt")}, None


def main():
    확인만 = "--확인" in sys.argv
    key = config.require("DART_API_KEY")
    맵 = D.load_corpcode()
    표 = {}
    if os.path.exists(OUT):
        try:
            표 = json.load(io.open(OUT, encoding="utf-8-sig"))
        except Exception:
            표 = {}
    할것 = [c for c in sorted(맵) if c not in 표]
    if 확인만:
        할것 = 할것[:3]
    찍기("===== 업종 분류 수집 (DART 기업개황) =====")
    찍기(f"  대상 {len(맵):,}종목 · 이미 받은 것 {len(표):,} · 할 것 {len(할것):,}"
         f" · 예상 {len(할것)*(_쉼+0.12)/60:.0f}분")
    ok = 실패 = 0
    for i, code in enumerate(할것, 1):
        corp = (맵[code] or {}).get("corp_code")
        if not corp:
            continue
        try:
            v, err = 하나(corp, key)
        except urllib.error.HTTPError as e:
            실패 += 1
            찍기(f"  ⚠️ {code} HTTP {e.code}")
            if e.code in (401, 403):
                break
            time.sleep(0.5)
            continue
        except Exception:
            실패 += 1
            time.sleep(0.5)
            continue
        if err:
            실패 += 1
            # ⚠️ 020 = 하루 한도 초과. 더 두드려도 소용없다
            if str(err) == "020":
                찍기("  ⚠️⚠️ DART 하루 한도를 다 썼다 — 멈춘다. 내일 이어받는다")
                break
            continue
        표[code] = v
        ok += 1
        time.sleep(_쉼)
        if i % 300 == 0:
            찍기(f"    {i}/{len(할것)} · 받음 {ok:,} · 실패 {실패}")
            io.open(OUT, "w", encoding="utf-8").write(
                json.dumps(표, ensure_ascii=False))
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(표, ensure_ascii=False))
    찍기(f"  끝 · 받음 {ok:,} · 실패 {실패} · 전체 {len(표):,}종목 → {OUT}")
    if 표:
        묶 = {}
        for c, v in 표.items():
            묶[v["업종명"]] = 묶.get(v["업종명"], 0) + 1
        찍기("  업종 상위 10: " + " · ".join(
            f"{k}({n})" for k, n in sorted(묶.items(), key=lambda x: -x[1])[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
