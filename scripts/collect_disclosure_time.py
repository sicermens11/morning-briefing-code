#!/usr/bin/env python3
r"""collect_disclosure_time.py — **공시 접수 시각을 받는다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 갭①은 *"재료가 **장 마감 후** 발생"*인데 **DART API에 시각이 없다**
   (`rcept_dt`는 날짜뿐). 그래서 2026-09-01 전 종목 검증에서 **접수번호 순번**을 대리지표로
   썼는데, 그건 실제 시각이 아니라 그날 접수 **순서**일 뿐이고 계열이 섞여 부정확했다.
   ⇒ **거래소 공시시스템(KIND)에는 `HH:MM`이 있다.** 접수번호로 DART 자료와 이어붙인다.

⚠️ 붙이는 방법: KIND의 `openDisclsViewer('<접수번호>')`와 `<td>HH:MM</td>`를 짝지어
   `{접수번호: "HH:MM"}`으로 저장한다. 종목코드는 이미 `data/dart-daily/`에 있다.

⚠️ **장 마감은 15:30이다.** 그 뒤에 접수된 것이 갭①의 「장 마감 후」다.
   ⚠️ 다만 **정규장 마감 후 시간외 거래**가 있으므로 "다음날 시가에 반영"이라는 전제는
      그대로가 아니다 — 검증할 때 이 점을 밝힌다.

쓰는 법:
    python scripts\collect_disclosure_time.py            # dart-daily에 있는 날 전부
    python scripts\collect_disclosure_time.py --limit 30 # 최근 30일만
"""
import glob
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_OUT = os.path.join(_DATA, "kind-time")
_URL = "https://kind.krx.co.kr/disclosure/todaydisclosure.do"
_ROW = re.compile(
    r'<td class="first txc">(\d{2}:\d{2})</td>.*?openDisclsViewer\(\'(\d{14})\'', re.S)


def 하루(d8: str, 최대쪽=40):
    """그날 거래소 공시의 {접수번호: 'HH:MM'}. 쪽을 넘기며 다 모은다."""
    표 = {}
    본 = "-".join((d8[:4], d8[4:6], d8[6:]))
    for 쪽 in range(1, 최대쪽 + 1):
        p = {"method": "searchTodayDisclosureSub", "currentPageSize": "100",
             "pageIndex": str(쪽), "orderMode": "0", "orderStat": "D",
             "forward": "todaydisclosure_sub", "searchMode": "",
             "selDate": 본, "marketType": "", "searchCorpName": ""}
        req = urllib.request.Request(
            _URL, data=urllib.parse.urlencode(p).encode(),
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://kind.krx.co.kr/"})
        try:
            h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception:
            break
        찾 = _ROW.findall(h)
        if not 찾:
            break
        전 = len(표)
        for 시, 번 in 찾:
            표[번] = 시
        if len(표) == 전:      # 더 안 늘면 마지막 쪽이다
            break
        time.sleep(0.15)       # ⚠️ 거래소 서버에 부담 주지 않는다
    return 표


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    날 = sorted(os.path.basename(x)[:8]
                for x in glob.glob(os.path.join(_DATA, "dart-daily", "*.json")))
    받 = {os.path.basename(x)[:8] for x in glob.glob(os.path.join(_OUT, "*.json"))}
    할 = [d for d in 날 if d not in 받]
    if limit:
        할 = 할[-limit:]
    os.makedirs(_OUT, exist_ok=True)
    print(f"  받을 날 {len(할)}일", flush=True)
    ok = 빈 = 0
    for i, d8 in enumerate(할, 1):
        표 = 하루(d8)
        if 표:
            with io.open(os.path.join(_OUT, f"{d8}.json"), "w", encoding="utf-8") as fp:
                json.dump({"기준일": d8, "건수": len(표), "시각": 표}, fp, ensure_ascii=False)
            ok += 1
        else:
            빈 += 1
        if i % 25 == 0:
            print(f"    {i}/{len(할)} — 성공 {ok} 빈날 {빈}", flush=True)
    print(json.dumps({"ok": True, "받음": ok, "빈날": 빈}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
