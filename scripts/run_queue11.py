#!/usr/bin/env python3
r"""
run_queue11.py — **193차를 줄 맨 뒤에** 세운다 (2026-09-09 밤 신설)

## 줄
```
185차(도는 중) -> 190차 -> 189차   <- run_queue10.ps1 이 맡는다
                            -> **193차**  <- 이 스크립트가 맡는다
```

## ⚠️ 왜 PowerShell 이 아니라 Python 인가
```
run_queue10.ps1 을 처음 띄웠을 때 **소리 없이 죽었다.**
PowerShell 5.1 은 BOM 없는 UTF-8 을 ANSI 로 읽어서 한글 변수명이 깨진다.
BOM 을 붙여 살렸지만, Python 은 그 문제가 없다
```

## ⚠️ 왜 줄을 세우나
```
gate7(193차)은 사건을 5,437,354개 만든다. 램이 15GB 넘게 든다.
185차가 14GB 를 쓰는 중이라 같이 못 돈다.
오늘 이미 두 번 당했다 —
  · 190차는 램 0.1GB 에서 시작해 **곧바로 죽었다** (파일 0바이트)
  · 189차는 「재료 붙이는 중」에서 램이 터졌다 (파일 729바이트)
```
"""
import datetime as dt
import io
import os
import subprocess
import sys
import time

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_잠 = os.path.join(_BASE, "data", "_queue11.lock")
_기록 = os.path.join(_BASE, "data", "_queue11.log")
_앞잠 = os.path.join(_BASE, "data", "_queue10.lock")


def 찍기(s):
    줄 = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(줄, flush=True)
    try:
        with io.open(_기록, "a", encoding="utf-8") as f:
            f.write(줄 + "\n")
    except OSError:
        pass


def 램GB():
    """남은 램(GB). 못 재면 999 로 봐서 막지 않는다"""
    try:
        out = subprocess.run(
            ["wmic", "OS", "get", "FreePhysicalMemory"],
            capture_output=True, text=True, timeout=20).stdout
        for L in out.splitlines():
            L = L.strip()
            if L.isdigit():
                return int(L) / 1024 / 1024
    except Exception:  # noqa: BLE001
        pass
    return 999.0


def 도나(이름):
    """그 lab 이 돌고 있나"""
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'", "get", "CommandLine"],
            capture_output=True, text=True, timeout=30).stdout
        return 이름 in out
    except Exception:  # noqa: BLE001
        return False


def main():
    if os.path.exists(_잠):
        찍기("이미 대기 중이다 — 그만둔다")
        return 0
    io.open(_잠, "w").write("")
    try:
        찍기("===== 앞 줄(185·190·189차)이 끝나길 기다린다 =====")
        # ⚠️ run_queue10 의 자물쇠가 사라져야 그 줄이 다 끝난 것이다
        while os.path.exists(_앞잠) or 도나("group_lab"):
            time.sleep(180)
        찍기("앞 줄 끝났다")
        time.sleep(60)

        나 = "2026-09-09_193차_4관문_해외신호.txt"
        for _ in range(20):
            여 = 램GB()
            if 여 >= 8:
                break
            찍기(f"  ⚠️ 램이 {여:.1f}GB 뿐이다 — 5분 더 기다린다")
            time.sleep(300)
        찍기(f"193차 시작 — 램 {램GB():.1f}GB 남음")
        환 = dict(os.environ, LAB_OUT=나, PYTHONIOENCODING="utf-8")
        subprocess.run([sys.executable,
                        os.path.join(_BASE, "scripts", "gate7_lab.py")],
                       cwd=_BASE, env=환)
        # ⚠️ 「끝났다」가 아니라 **파일 크기**로 판정한다.
        #    오늘 0바이트·729바이트짜리를 「돌았다」고 읽을 뻔했다
        p = os.path.join(_BASE, "data", "_labs", 나)
        크 = os.path.getsize(p) if os.path.exists(p) else 0
        if 크 < 2000:
            찍기(f"  ❌ 193차가 {크:,}바이트뿐이다 — 죽었다")
        else:
            찍기(f"  ✅ 193차 끝 — {크:,}바이트")
        찍기("===== 줄 끝 =====")
    finally:
        try:
            os.remove(_잠)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
