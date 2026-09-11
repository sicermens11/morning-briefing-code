#!/usr/bin/env python3
r"""
ram_guard.py — **램이 바닥나면 시험을 먼저 죽인다** (2026-09-09 밤 신설)

## 왜
```
2026-09-09 23:00 실측: group_lab 이 **23.3GB** · 램 **1.8GB 남음** (전체 31.9GB)
그 시각 저녁 수집(뉴스)도 돌고 있었다.

⚠️ 램이 바닥나면 **아무거나** 죽는다. 오늘 이미 세 번 당했다:
   190차(0바이트) · 189차(729·770바이트) · 193차(386바이트)
⚠️⚠️ **수집이 시험보다 중요하다.** 수집은 그날 자료가 사라지면 영영 못 받지만,
   시험은 다시 돌리면 된다 (사용자 원칙: 브리핑 목적이 첫째다)
```

## 하는 일
```
1분마다 램을 본다.
  · 남은 램이 **1.2GB 밑**이면 → 도는 **시험** 중 제일 큰 것을 하나 죽인다
  · 수집(collect_*)은 **절대 안 죽인다**
죽인 것은 로그에 남긴다 — 줄 스크립트가 다시 돌린다
```

쓰는 법:
    python scripts\ram_guard.py           # 계속 지켜본다
    python scripts\ram_guard.py --한번     # 한 번만 보고 끝
"""
import datetime as dt
import io
import os
import re
import subprocess
import sys
import time

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "_ram_guard.log")
_바닥 = 1.2          # GB
_시험 = ("group_lab", "info_lab2", "gate5_lab", "gate6_lab", "gate7_lab",
         "corr_lab", "herd_lab", "sector_own_lab", "chain_lab", "world_lab",
         "vola_lab", "omni_lab", "combo_lab", "sector_lab")


def 찍기(s):
    줄 = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(줄, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(줄 + "\n")
    except OSError:
        pass


def _wmic(무엇):
    try:
        return subprocess.run(무엇, capture_output=True, text=True,
                              timeout=30).stdout
    except Exception:  # noqa: BLE001
        return ""


def 램GB():
    for L in _wmic(["wmic", "OS", "get", "FreePhysicalMemory"]).splitlines():
        if L.strip().isdigit():
            return int(L.strip()) / 1024 / 1024
    return 999.0


def 시험들():
    """[(pid, 이름, GB)] — **시험만**. 수집은 절대 안 넣는다"""
    o = _wmic(["wmic", "process", "where", "name='python.exe'",
               "get", "ProcessId,WorkingSetSize,CommandLine"])
    난것 = []
    for L in o.splitlines():
        L = L.strip()
        if not L or ".py" not in L:
            continue
        m = re.search(r"([a-z_0-9]+)\.py", L)
        if not m or m.group(1) not in _시험:
            continue
        숫 = re.findall(r"(\d+)\s+(\d+)\s*$", L)
        if not 숫:
            continue
        pid, 바이트 = 숫[0]
        난것.append((int(pid), m.group(1), int(바이트) / 1073741824))
    return sorted(난것, key=lambda z: -z[2])


def 한번():
    여 = 램GB()
    돎 = 시험들()
    if 여 >= _바닥:
        return False
    if not 돎:
        찍기(f"⚠️ 램이 {여:.1f}GB 뿐인데 **죽일 시험이 없다** — 수집은 안 건드린다")
        return False
    pid, 나, gb = 돎[0]
    찍기(f"⚠️⚠️ 램 {여:.1f}GB — **{나}({pid}, {gb:.1f}GB)를 죽인다.** "
         f"수집이 시험보다 먼저다")
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       capture_output=True, timeout=30)
        찍기(f"  죽였다. 줄 스크립트가 다시 돌릴 것이다")
    except Exception as e:  # noqa: BLE001
        찍기(f"  ⚠️ 못 죽였다: {type(e).__name__}")
    return True


def main():
    if "--한번" in sys.argv:
        한번()
        return 0
    찍기(f"===== 램 지킴이 시작 · 바닥 {_바닥}GB =====")
    while True:
        try:
            한번()
        except Exception as e:  # noqa: BLE001
            찍기(f"⚠️ 지킴이가 터졌다: {type(e).__name__}")
        time.sleep(60)


if __name__ == "__main__":
    sys.exit(main())
