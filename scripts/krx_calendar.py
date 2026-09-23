#!/usr/bin/env python3
r"""
krx_calendar.py — **오늘 한국 장이 서나** (2026-09-23 신설 · 사용자 「고쳐!」)

단일 원본: data/krx-holidays-2026.md 의 표 (평일인데 휴장인 날짜만).
주말은 표 없이 늘 휴장.

## 왜 만들었나
`morning_prep.장서는날()` 이 토·일만 보고 공휴일을 안 봤다. 주석엔 「krx-daily 마지막 날짜로
판단」이라 적혀 있었는데 코드가 그렇지 않았다. 08:02 브리핑·08:50 예상체결가 예약은 아예 안 봤다.
⇒ 2026-09-24(추석) 아침에 장 없는 날의 브리핑을 만들고, forward-log 에 기준일 20260923 줄을
   목요일에 써서 월요일(9/28) 08:02 가 같은 기준일을 못 덮어쓰는 사고가 예정돼 있었다.

## 쓰는 법
    from krx_calendar import 장서는날
    선다, 왜 = 장서는날()            # (False, "2026-09-24(목) 휴장 — 추석 연휴")
    python scripts/krx_calendar.py              # 오늘 · 장 서면 "장선다" · 아니면 "휴장 …"  (exit 1)
    python scripts/krx_calendar.py 2026-09-24   # 그 날짜

⚠️ 표에 없는 임시공휴일은 못 안다 — 정부가 추가 지정하면 표를 갱신해야 한다 (표 파일의 갱신 이력 참고)
"""
import datetime as dt
import io
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_표 = os.path.join(_BASE, "data", "krx-holidays-2026.md")
_요일 = "월화수목금토일"


def 휴장일들():
    r"""{날짜(date): 사유} — 표에서 읽는다. 파일이 없으면 빈 dict (주말만 본다는 뜻)"""
    난것 = {}
    try:
        for 줄 in io.open(_표, encoding="utf-8-sig"):
            m = re.match(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*[월화수목금토일]\s*\|\s*(.+?)\s*\|\s*$", 줄)
            if m:
                난것[dt.date.fromisoformat(m.group(1))] = m.group(2)
    except OSError:
        pass
    return 난것


def 장서는날(날짜=None):
    r"""(True, "") 또는 (False, 사유). 날짜를 안 주면 오늘"""
    d = 날짜 or dt.date.today()
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10]) if "-" in d else dt.date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    if d.weekday() >= 5:
        return False, f"{d.isoformat()}({_요일[d.weekday()]}) 휴장 — 주말"
    왜 = 휴장일들().get(d)
    if 왜:
        return False, f"{d.isoformat()}({_요일[d.weekday()]}) 휴장 — {왜}"
    return True, ""


def 직전거래일(날짜=None):
    r"""그 날짜 **앞의** 마지막 거래일 (오늘이 월요일이면 금요일 · 추석 뒤 월요일이면 추석 전 수요일)"""
    d = 날짜 or dt.date.today()
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10]) if "-" in d else dt.date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    for _ in range(30):
        d -= dt.timedelta(days=1)
        if 장서는날(d)[0]:
            return d
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    인자 = [a for a in sys.argv[1:] if not a.startswith("-")]
    선다, 왜 = 장서는날(인자[0] if 인자 else None)
    if 선다:
        print("장선다")
        return 0
    print(왜)
    return 1


if __name__ == "__main__":
    sys.exit(main())
