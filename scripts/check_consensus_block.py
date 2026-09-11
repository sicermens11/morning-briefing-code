#!/usr/bin/env python3
r"""
check_consensus_block.py — **한경 차단이 풀렸나** 한 시간에 한 번만 본다 (2026-09-09)

## 왜
```
한 달치(17쪽)를 36달 연속으로 받다가 **HTTP 403** 으로 막혔다.
열흘치 첫 쪽도 403 이라 **조각 크기 문제가 아니라 우리가 막힌 것**이다.
언제 풀릴지 모른다 — **한 시간에 한 번, 한 번만** 두드려서 확인한다
```
⚠️ **우회하지 않는다.** 한 시간에 요청 하나는 사람이 보는 것보다 적다
⚠️ 풀리면 로그에 남기고 **바로 받기 시작한다**

쓰는 법:
    python scripts\check_consensus_block.py            # 풀릴 때까지 한 시간 간격
    python scripts\check_consensus_block.py --한번     # 한 번만 보고 끝
"""
import datetime as dt
import io
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_consensus as C  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "_consensus_slow.log")


def 찍기(s):
    line = f"{dt.datetime.now():%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def 풀렸나():
    """**요청 하나만** 보낸다"""
    u = f"{C.URL}&sdate=2021-05-01&edate=2021-05-05&now_page=1"
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(u, headers=C.H), timeout=30)
        s = r.read().decode("utf-8", "replace")
        n = len(C._행.findall(s))
        return True, f"HTTP {r.status} · 행 {n}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, type(e).__name__


def main():
    한번 = "--한번" in sys.argv
    찍기("===== 한경 차단이 풀렸나 — 한 시간에 한 번만 본다 =====")
    for 회 in range(1, 49):          # 최대 이틀
        됐나, 말 = 풀렸나()
        if 됐나:
            찍기(f"  ⭐ **풀렸다** ({말}) — 바로 받기 시작한다")
            subprocess.Popen(
                [sys.executable,
                 os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "collect_consensus_slow.py"),
                 "--쉼", "12", "--하루", "8"],
                cwd=_BASE)
            return 0
        찍기(f"  [{회}] 아직 막혀 있다 ({말}) — 한 시간 뒤 다시")
        if 한번:
            return 1
        time.sleep(3600)
    찍기("  ⚠️ 이틀 동안 안 풀렸다 — 사람이 봐야 한다")
    return 1


if __name__ == "__main__":
    sys.exit(main())
