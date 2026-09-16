#!/usr/bin/env python3
r"""
collect_ecos.py — **한국은행 ECOS** 에서 수출입 · 소비자물가 · 기준금리를 받는다 (2026-09-16 신설)

## 왜
사용자: 「우리나라는 수출 주도 국가니까 수출입 자료로 테스트 안 해봐도 되나?」 → 한 번도 안 쟀다.
FRED(차단) · FMP(구독 밖) · 한국은행 페이지(스크립트) 다 막혀 **ECOS API 키**가 유일한 길이었다. 2026-09-16 사용자가 넣었다.

## 쓰는 법
    python scripts\collect_ecos.py --찾기 수출          # 통계표 목록에서 이름 찾기 (코드를 모를 때)
    python scripts\collect_ecos.py --받기               # 아래 _시리즈 를 전부 받아 data/ecos/*.json
키는 config.require("ECOS_API_KEY") 로만 읽는다. 값을 찍지 않는다.

## 저장 (data/ecos/<이름>.json)
    {"통계코드": …, "항목": …, "주기": "M"/"D", "값": {"YYYYMM" or "YYYYMMDD": 숫자}, "받은날": …}
⚠️ 월 자료는 **그 달이 끝나고 발표된 값**이다 — 재료로 붙일 때 발표일(다음 달 1일 · 물가는 다음 달 초) 뒤부터 쓴다.
"""
import datetime as dt
import io
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUT = os.path.join(_BASE, "data", "ecos")
_LOG = os.path.join(_BASE, "data", "_ecos.log")


def 찍기(s):
    줄 = f"{dt.datetime.now():%m-%d %H:%M}  {s}"
    print(줄, flush=True)
    io.open(_LOG, "a", encoding="utf-8").write(줄 + "\n")


def _api(service, *parts):
    key = config.require("ECOS_API_KEY")
    url = "https://ecos.bok.or.kr/api/" + "/".join([service, key, "json", "kr"] + [urllib.parse.quote(str(p)) for p in parts])
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def 찾기(말):
    """통계표 목록에서 이름에 `말` 이 든 것"""
    j = _api("StatisticTableList", 1, 1000)
    rows = (j.get("StatisticTableList") or {}).get("row") or []
    if not rows:
        print(json.dumps(j, ensure_ascii=False)[:400])
        return
    n = 0
    for r in rows:
        nm = str(r.get("STAT_NAME") or "")
        if 말 in nm:
            n += 1
            print(f"  {r.get('STAT_CODE'):<10} {r.get('CYCLE') or '':<3} {nm[:70]}")
    print(f"  {n}개")


def 항목(코드):
    """그 통계표의 항목(ITEM) 목록"""
    j = _api("StatisticItemList", 1, 1000, 코드)
    rows = (j.get("StatisticItemList") or {}).get("row") or []
    for r in rows[:80]:
        print(f"  {r.get('ITEM_CODE'):<12} {r.get('CYCLE') or '':<3} {str(r.get('ITEM_NAME'))[:50]:<52} {r.get('START_TIME')}~{r.get('END_TIME')}")
    print(f"  {len(rows)}개")


# (이름, 통계코드, 주기, 항목코드1, 시작, 끝) — 2026-09-16 --찾기/--항목 으로 확인해 채웠다
_시리즈 = [
    ("수출금액", "901Y118", "M", "T002", "200001", "202612"),      # 통관기준 수출입 총괄 · 백만달러 · 관세청
    ("수입금액", "901Y118", "M", "T004", "200001", "202612"),
    ("소비자물가", "901Y009", "M", "0", "200001", "202612"),         # 총지수 (2020=100)
    ("기준금리", "722Y001", "D", "0101000", "20100101", "20261231"),  # 일별 · 결정일이 곧 금통위 날
]


def 받기():
    os.makedirs(_OUT, exist_ok=True)
    for 이름, 코드, 주기, 항, 시작, 끝 in _시리즈:
        try:
            j = _api("StatisticSearch", 1, 100000, 코드, 주기, 시작, 끝, 항)
            rows = (j.get("StatisticSearch") or {}).get("row") or []
            값 = {}
            for r in rows:
                t = str(r.get("TIME") or "")
                v = r.get("DATA_VALUE")
                try:
                    값[t] = float(v)
                except (TypeError, ValueError):
                    pass
            json.dump({"이름": 이름, "통계코드": 코드, "항목": 항, "주기": 주기, "값": 값,
                       "받은날": dt.date.today().strftime("%Y%m%d")},
                      io.open(os.path.join(_OUT, f"{이름}.json"), "w", encoding="utf-8"), ensure_ascii=False)
            ks = sorted(값)
            찍기(f"  {이름:<14} {len(값):>5}개  {ks[0] if ks else '-'} ~ {ks[-1] if ks else '-'}")
        except Exception as e:  # noqa: BLE001
            찍기(f"  ⚠️ {이름} 실패: {type(e).__name__}: {str(e)[:100]}")


def main():
    a = sys.argv[1:]
    if "--찾기" in a:
        찾기(a[a.index("--찾기") + 1])
    elif "--항목" in a:
        항목(a[a.index("--항목") + 1])
    elif "--받기" in a:
        받기()
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
