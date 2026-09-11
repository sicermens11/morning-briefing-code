#!/usr/bin/env python3
r"""
when_krx2.py — **ETF·주식선물·국고채도 언제 오나** 잰다 (2026-09-09 신설)

## 왜
```
종가·지수는 관측해서 **다음날 08:03** 이라는 답을 얻었다.
그런데 폴더 날짜를 보니:
  dart-daily · kind-time   20260909 (오늘)      <- 저녁에 그날 것이 온다 ✅
  krx-daily · index-daily  20260908 (어제)      <- 08:03 에 전날 것 ✅ 정상
  **etf-krx · krx-extra     20260907 (이틀 전)**  ⚠️ 이틀 늦다
```
ETF·주식선물도 KRX 자료다. **저녁에 시도하니 늘 이틀 늦은 것**일 수 있다
-> 언제 오는지 재서, 늦으면 **아침으로 옮긴다** (종가·지수처럼)

⚠️ 조회만 한다. 자료를 쌓지 않는다

쓰는 법:
    python scripts\when_krx2.py --간격 20
"""
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "_krx_when2.log")
볼것 = (("etp", "etf_bydd_trd", "ETF"),
        ("drv", "eqsfu_stk_bydd_trd", "주식선물(유가)"),
        ("drv", "fut_bydd_trd", "선물"),
        ("bon", "kts_bydd_trd", "국고채"))


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def 줄수(key, svc, ep, 날):
    u = f"https://data-dbg.krx.co.kr/svc/apis/{svc}/{ep}?basDd={날}"
    r = urllib.request.Request(u, headers={"AUTH_KEY": key,
                                           "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(r, timeout=25) as f:
            d = json.loads(f.read().decode("utf-8"))
        return len(d.get("OutBlock_1") or [])
    except Exception:  # noqa: BLE001
        return -1


def main():
    key = config.get("KRX_API_KEY")
    if not key:
        찍기("⚠️ KRX_API_KEY 가 없다")
        return 1
    간격 = 20
    if "--간격" in sys.argv:
        간격 = int(sys.argv[sys.argv.index("--간격") + 1])
    날 = dt.date.today().strftime("%Y%m%d")
    찍기(f"===== {날} ETF·파생이 언제 오나 · {간격}분 간격 =====")
    찾음 = {}
    끝시각 = dt.datetime.now().replace(hour=9, minute=30, second=0) \
        + dt.timedelta(days=1)
    while dt.datetime.now() < 끝시각 and len(찾음) < len(볼것):
        말 = []
        for svc, ep, 라 in 볼것:
            if 라 in 찾음:
                continue
            n = 줄수(key, svc, ep, 날)
            if n > 0:
                찾음[라] = dt.datetime.now()
                찍기(f"  ⭐ **{라}** 도착 — {n:,}줄")
            else:
                말.append(f"{라}:{'오류/권한' if n < 0 else '없음'}")
        if 말:
            찍기(f"  … {' · '.join(말)}")
        if len(찾음) >= len(볼것):
            break
        time.sleep(간격 * 60)
    찍기("===== 끝 =====")
    for 라, t in 찾음.items():
        찍기(f"  {라:<16}{t:%H:%M}")
    안온것 = [라 for _, _, 라 in 볼것 if 라 not in 찾음]
    if 안온것:
        찍기(f"  ⚠️ 아침까지 안 온 것: {', '.join(안온것)}")
    if 찾음:
        늦 = max(찾음.values())
        찍기(f"\n  ⇒ **{늦:%H:%M} 뒤**에 받아야 그날 자료를 받는다")
        if 늦.hour >= 18 or 늦.hour < 12:
            찍기("     저녁(19:00)보다 늦으면 **아침으로 옮겨야 한다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
