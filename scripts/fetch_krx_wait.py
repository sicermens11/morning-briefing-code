#!/usr/bin/env python3
r"""
fetch_krx_wait.py — **전 거래일 종가가 올 때까지 기다렸다 받는다** (2026-09-07 신설)

## ⚠️ 왜 만들었나 — 2026-09-07 아침에 실제로 당했다
```
07:50  morning_prep 이 fetch_krx.py 를 부른다 -> "어느 시장도 못 받았다"
08:22  브리핑이 같은 걸 부르면 **받아진다**
⇒ KRX가 08:20쯤에야 전 거래일 종가를 준다 (실측 두 번)
   09-03 자료 -> 09-04 08:22:59 도착
   09-04 자료 -> 09-07 08:24:18 도착

그래서 07:50 실행이 **하루 묵은 종가**로 후보를 뽑았고,
신호기준일이 같아 중복방지가 걸려 **기록이 아예 안 남았다.**
로그에는 「예측 기록 + 채점 ✅」로 찍혀 있었다 — **조용히 틀렸다**
```

## 하는 일
```
전 거래일(달력상 직전 평일) 자료를 받을 때까지 **2분 간격으로 다시 시도**한다.
기본 25분까지 (07:50 시작이면 08:15까지). 그 안에 오면 바로 끝낸다.
```
⚠️ **휴장일이면 영영 안 온다.** 그때는 기다린 만큼 시간만 버리고 끝난다 —
   그래도 `--최대`를 넘기면 멈추고, 이미 있는 자료로 다음 단계가 돈다.
   휴장일인지 아닌지는 여기서 판정하지 않는다 (설·추석은 해마다 움직인다).

쓰는 법:
    python scripts\fetch_krx_wait.py
    python scripts\fetch_krx_wait.py --최대 40 --간격 3
"""
import datetime as dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_krx  # noqa: E402


def 전거래일():
    """달력상 직전 평일. ⚠️ 휴장일은 못 가린다 — 그날은 API가 빈 배열을 준다."""
    d = dt.date.today() - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.strftime("%Y%m%d")


def main():
    최대 = 25
    간격 = 2
    if "--최대" in sys.argv:
        최대 = int(sys.argv[sys.argv.index("--최대") + 1])
    if "--간격" in sys.argv:
        간격 = int(sys.argv[sys.argv.index("--간격") + 1])

    날 = sys.argv[sys.argv.index("--날짜") + 1] if "--날짜" in sys.argv \
        else 전거래일()
    끝 = time.time() + 최대 * 60
    번 = 0
    while True:
        번 += 1
        try:
            d, 캐시 = fetch_krx.fetch(날)
            print(json.dumps({"ok": True, "기준일": 날, "종목수": d["종목수"],
                              "캐시": 캐시, "시도": 번,
                              "받은시각": dt.datetime.now().strftime("%H:%M:%S")},
                             ensure_ascii=False))
            return 0
        except Exception as e:  # noqa: BLE001
            남 = 끝 - time.time()
            if 남 <= 0:
                print(json.dumps(
                    {"ok": False, "기준일": 날, "시도": 번,
                     "오류": f"{type(e).__name__}: {str(e)[:80]}",
                     "말": f"{최대}분을 기다려도 안 왔다. "
                           f"휴장일이거나 KRX가 늦는 것이다"},
                    ensure_ascii=False))
                return 1
            print(f"  … {날} 아직 없다 ({번}번째) — {간격}분 뒤 다시. "
                  f"남은 시간 {남/60:.0f}분", flush=True)
            time.sleep(간격 * 60)


if __name__ == "__main__":
    sys.exit(main())
