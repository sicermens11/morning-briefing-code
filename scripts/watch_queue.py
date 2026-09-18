#!/usr/bin/env python3
r"""
watch_queue.py — **줄에 걸린 판이 죽었나** 한 줄로 답한다 (2026-09-18 신설)

## 왜
```
2026-09-18 11:32 에 `queue_bandor` 가 NameError 로 죽었는데 **17:41 까지 몰랐다.**
결과 파일이 165KB 로 만들어져 있어 겉으로는 정상으로 보였다 — 죽기 전까지 쓴 것이다.
여섯 시간을 날렸다.

전수점검(audit_all) I절이 이걸 잡지만 **내가 손으로 돌려야** 보인다.
판을 걸 때마다 이걸 같이 걸면, 판이 끝나는 순간 죽었는지가 남는다.
```
## 쓰는 법
```
python scripts\watch_queue.py                최근 12시간 안에 끝난 판을 판정
python scripts\watch_queue.py --전부          돌고 있는 것까지
python scripts\watch_queue.py --기다림 bandor2  그 판이 끝날 때까지 기다렸다가 판정 (예약·백그라운드용)
```
판정:
  ✅ 끝남      「끝 =====」이 있고 Traceback 없음
  ❌ 죽음      Traceback · NameError · MemoryError · KeyError 등
  ⏳ 도는 중    「끝」 표시가 아직 없음
  ⚠️ 멈춤      3시간 넘게 로그가 안 바뀌는데 「끝」도 없음
"""
import datetime as dt
import glob
import io
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOGS = os.path.join(_BASE, "run-logs")
_죽음 = re.compile(r"Traceback|\w+Error\b|MemoryError|터졌다")


def 판정(f):
    t = io.open(f, encoding="utf-8", errors="replace").read()
    끝났나 = "끝 =====" in t
    죽은줄 = [z.strip() for z in t.splitlines() if _죽음.search(z)]
    쉰시간 = (time.time() - os.path.getmtime(f)) / 3600
    if 죽은줄:
        return "❌ 죽음", 죽은줄[-1][:90]
    if 끝났나:
        _끝 = [z for z in t.splitlines() if "끝 —" in z or "끝 ·" in z]
        return "✅ 끝남", (_끝[-1].strip()[:70] if _끝 else "")
    if 쉰시간 > 3:
        return "⚠️ 멈춤", f"{쉰시간:.1f}시간째 안 바뀜"
    return "⏳ 도는 중", (t.strip().splitlines() or [""])[-1][:70]


def main():
    argv = sys.argv[1:]
    if "--기다림" in argv:
        이름 = argv[argv.index("--기다림") + 1]
        fs = sorted(glob.glob(os.path.join(_LOGS, f"queue_{이름}_*.log")), key=os.path.getmtime)
        if not fs:
            print(f"⚠️ queue_{이름} 로그가 없다")
            return 1
        f = fs[-1]
        print(f"  {os.path.basename(f)} 를 기다린다...", flush=True)
        while True:
            표, 말 = 판정(f)
            if 표.startswith(("✅", "❌", "⚠️")):
                print(f"  {표}  {os.path.basename(f)}  {말}")
                return 0 if 표.startswith("✅") else 2
            time.sleep(60)

    _컷 = time.time() - (999 if "--전부" in argv else 12) * 3600
    fs = [f for f in sorted(glob.glob(os.path.join(_LOGS, "queue_*.log")), key=os.path.getmtime)
          if os.path.getmtime(f) >= _컷]
    if not fs:
        print("  최근에 돈 판이 없다")
        return 0
    나쁨 = 0
    print(f"  {'판':<36}{'끝난 시각':<14}판정")
    for f in fs:
        표, 말 = 판정(f)
        나쁨 += 표.startswith(("❌", "⚠️"))
        _때 = dt.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%m-%d %H:%M")
        print(f"  {os.path.basename(f)[:35]:<36}{_때:<14}{표}  {말}")
    if 나쁨:
        print(f"\n  ⚠️ **죽었거나 멈춘 판 {나쁨}개** — 위를 보라")
    return 0


if __name__ == "__main__":
    sys.exit(main())
