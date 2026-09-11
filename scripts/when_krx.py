#!/usr/bin/env python3
r"""
when_krx.py — **KRX가 그날 종가를 몇 시에 주나 잰다** (2026-09-08 신설)

## 왜
```
사용자 지적: 「주가 아직 안 올라왔는데 정상이면 **시간대를 옮기는 게 맞지 않아?**」
맞다. 우리가 아는 건 「다음날 아침 08:20쯤 받아진다」뿐이다.
**그건 그때 물어봤기 때문**이지 그 전엔 없었다는 뜻이 아니다
실측: 19:01 에는 아직 없다 (2026-09-08)
```

## 하는 일
```
30분마다 KRX OpenAPI 에 **오늘 날짜**로 물어본다
  · 유가증권 시세 · 코스닥 시세 · 코스닥 지수
처음 자료가 온 시각을 기록한다 -> `data/_krx_when.log`
아침 09:00 까지 안 오면 멈춘다
```
⚠️ 조회만 한다. 자료를 쌓지 않는다 — **언제 오나만** 본다

쓰는 법:
    python scripts\when_krx.py            # 30분 간격 (기본)
    python scripts\when_krx.py --간격 15   # 15분 간격
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
LOG = os.path.join(_BASE, "data", "_krx_when.log")
볼것 = (("sto", "stk_bydd_trd", "유가증권"),
        ("sto", "ksq_bydd_trd", "코스닥"),
        ("idx", "kosdaq_dd_trd", "코스닥지수"))


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
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
    간격 = 30
    if "--간격" in sys.argv:
        간격 = int(sys.argv[sys.argv.index("--간격") + 1])
    날 = dt.date.today().strftime("%Y%m%d")
    찍기(f"===== {날} 종가가 언제 오나 · {간격}분 간격 =====")
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
                말.append(f"{라}:{'오류' if n < 0 else '없음'}")
        if 말:
            찍기(f"  … {' · '.join(말)}")
        if len(찾음) >= len(볼것):
            break
        time.sleep(간격 * 60)
    찍기("===== 끝 =====")
    for 라, t in 찾음.items():
        찍기(f"  {라:<12}{t:%H:%M}")
    안온것 = [라 for _, _, 라 in 볼것 if 라 not in 찾음]
    if 안온것:
        찍기(f"  ⚠️ 아침까지 안 온 것: {', '.join(안온것)}")
    if 찾음:
        늦 = max(찾음.values())
        찍기(f"\n  ⇒ 저녁 수집을 **{늦:%H:%M} 뒤**로 옮기면 그날 자료를 받는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
