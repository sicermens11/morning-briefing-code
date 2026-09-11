#!/usr/bin/env python3
r"""
collect_consensus_slow.py — **컨센서스를 띄엄띄엄 받는다** (2026-09-09 신설)

## 왜
```
한 번에 몰아 받았더니 한경이 **HTTP 403** 으로 막았다.
2020-11 ~ 2021-04 여섯 달(5,673건)까지는 받아졌고 그 뒤로 전부 403.
최근 달(2026-08)도 403 이라 **기간 문제가 아니라 우리를 막은 것**이다
```
사용자: 「연속으로 한 번에 말고, **띄엄띄엄 받으면** 안 막히지 않을까?」

## 어떻게
```
한 달 받고 -> **15~25분 쉬고** -> 다음 달
403 이 나면 -> **점점 더 오래 쉰다** (30분 · 1시간 · 2시간 · 4시간)
네 번 내리 막히면 -> **그날은 그만둔다** (더 두드리지 않는다)
```
⚠️ **차단을 우회하지 않는다.** 사람이 쓰는 속도로 천천히 갈 뿐이다
   (메모리: stooq 봇 차단도 우회하지 않는다)
⚠️ 빈 파일은 **안 남긴다** — 남기면 다음에 「이미 받음」으로 건너뛴다

## 얼마나 걸리나
```
남은 30달 x 20분 = **약 10시간**. 하룻밤이면 끝난다
```

쓰는 법:
    python scripts\collect_consensus_slow.py                 # 빠진 달 전부
    python scripts\collect_consensus_slow.py --쉼 30         # 30분 간격
    python scripts\collect_consensus_slow.py --한번          # 한 달만 받고 끝
"""
import datetime as dt
import io
import json
import os
import random
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_consensus as C  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "consensus")
LOG = os.path.join(_BASE, "data", "_consensus_slow.log")
_처음 = "202001"


def 찍기(s):
    line = f"{dt.datetime.now():%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def 빠진달():
    """아직 못 받은 달 (파일이 없거나 안이 빈 것)"""
    이번 = dt.date.today().strftime("%Y%m")
    할것 = []
    y, m = int(_처음[:4]), int(_처음[4:])
    while f"{y:04d}{m:02d}" <= 이번:
        키 = f"{y:04d}{m:02d}"
        p = os.path.join(OUT, 키 + ".json")
        찼 = False
        if os.path.exists(p):
            try:
                찼 = bool((json.load(io.open(p, encoding="utf-8-sig"))
                          .get("리포트")) or [])
            except Exception:  # noqa: BLE001
                찼 = False
        if not 찼:
            할것.append(키)
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return 할것


def 조각들(키):
    """그 달을 **열흘씩 세 조각**으로 나눈다.

    ⚠️ 한 달치(17쪽)를 한 번에 몰아 받다가 막혔다.
       열흘치면 **6쪽 안팎** — 한 번에 두드리는 양이 3분의 1이다
    """
    y, m = int(키[:4]), int(키[4:])
    말일 = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
    나눔 = [(1, 10), (11, 20), (21, 말일)]
    return [(f"{y:04d}-{m:02d}-{a:02d}", f"{y:04d}-{m:02d}-{b:02d}")
            for a, b in 나눔]


def 한조각(sd, ed):
    """열흘치를 받는다. (건들, 막혔나)"""
    모 = []
    for p in range(1, 40):
        try:
            r = C.쪽(sd, ed, p)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                return 모, True
            찍기(f"    ⚠️ {sd} {p}쪽 HTTP {e.code}")
            break
        except Exception as e:  # noqa: BLE001
            찍기(f"    ⚠️ {sd} {p}쪽 {type(e).__name__}")
            break
        if not r:
            break
        모 += r
        time.sleep(2 + random.random() * 2)   # 쪽 사이 2~4초
    return 모, False


def 한달(키):
    """열흘씩 세 조각으로 나눠 받는다. (건수, 막혔나)"""
    모 = []
    for k, (sd, ed) in enumerate(조각들(키)):
        조각, 막혔나 = 한조각(sd, ed)
        모 += 조각
        if 막혔나:
            return len(모), True
        찍기(f"      {sd[5:]}~{ed[5:]}  {len(조각):,}건")
        if k < 2:
            time.sleep(60 * (5 + random.random() * 4))    # 조각 사이 5~9분
    if 모:
        io.open(os.path.join(OUT, 키 + ".json"), "w",
                encoding="utf-8").write(
            json.dumps({"달": 키, "건수": len(모), "리포트": 모},
                       ensure_ascii=False))
    return len(모), False


def main():
    쉼분 = 12
    if "--쉼" in sys.argv:
        쉼분 = int(sys.argv[sys.argv.index("--쉼") + 1])
    # ⚠️ **하루에 받는 양에 상한**을 둔다. 한 번에 몰아 받다가 막혔다
    하루상한 = int(sys.argv[sys.argv.index("--하루") + 1]) if "--하루" in sys.argv else 8
    한번만 = "--한번" in sys.argv

    할것 = 빠진달()
    찍기(f"===== 띄엄띄엄 받기 시작 · 빠진 달 **{len(할것)}개** · "
         f"{쉼분}분 간격 (약 {len(할것)*쉼분/60:.0f}시간) =====")
    if not 할것:
        찍기("  받을 것이 없다.")
        return 0

    막힘 = 0
    받은달, 받은건 = 0, 0
    for i, 키 in enumerate(할것, 1):
        n, 막혔나 = 한달(키)
        if 막혔나:
            막힘 += 1
            쉴 = [30, 60, 120, 240][min(막힘 - 1, 3)]
            찍기(f"  [{i}/{len(할것)}] {키} — 🚫 **막혔다**(403). "
                 f"{쉴}분 쉬고 다시 (연속 {막힘}번째)")
            if 막힘 >= 4:
                찍기("  ⚠️ **네 번 내리 막혔다 — 오늘은 그만둔다.**")
                찍기("     더 두드리지 않는다. 내일 다시 돌린다")
                break
            time.sleep(쉴 * 60)
            continue
        막힘 = 0
        받은달 += 1
        받은건 += n
        찍기(f"  [{i}/{len(할것)}] {키} — **{n:,}건** "
             f"(누적 {받은달}달 · {받은건:,}건)")
        if 한번만 or 받은달 >= 하루상한:
            찍기(f"  ⏸ **오늘 몫({하루상한}달)을 다 받았다.** 내일 이어서 받는다")
            break
        if i < len(할것):
            쉴 = 쉼분 * 60 * (0.8 + 0.4 * random.random())   # 들쭉날쭉하게
            time.sleep(쉴)
    찍기(f"===== 끝 · **{받은달}달 · {받은건:,}건** 받음 · "
         f"남은 달 {len(빠진달())}개 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
