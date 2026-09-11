#!/usr/bin/env python3
r"""
morning_krx.py — **브리핑 전에 KRX 종가·지수를 먼저 받는다** (2026-09-09 신설)

## 왜
```
when_krx.py 로 20분 간격 관측한 결과:
  09-08 19:02 ~ 09-09 07:43  **계속 없음**
  09-09 **08:03**  유가증권 943줄 · 코스닥 1,822줄 · 지수 40줄
                   -> **2초 안에 셋이 같이** 온다
```
⇒ 저녁에는 절대 안 나온다. **아침에 받아야 한다.**
⇒ 그리고 **브리핑(08:00)보다 먼저** 끝나야 한다 (사용자 지적)

## 하는 일
```
① fetch_krx_wait.py   전 거래일 **종가**가 올 때까지 기다렸다 받는다
② collect_index.py    같은 때 오는 **지수**를 받는다
```
⚠️ 전에는 지수를 **저녁 수집**이 받았는데, 저녁엔 안 나와서 매번 「아직 안 올라왔다」였다.
   저녁에서 빼면서 여기로 옮겼다 — 안 그러면 **아무도 안 받게 된다**

쓰는 법:
    python scripts\morning_krx.py                # 최대 25분 기다림
    python scripts\morning_krx.py --최대 40
"""
import datetime as dt
import io
import json
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_S = os.path.join(_BASE, "scripts")
LOG = os.path.join(_BASE, "data", "_morning_krx.log")


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def 돌리기(파일, 인자, 제한=2400):
    p = os.path.join(_S, 파일)
    if not os.path.exists(p):
        return f"{파일} 없음"
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run([sys.executable, p] + 인자, capture_output=True,
                           timeout=제한, env=e, cwd=_BASE)
    except subprocess.TimeoutExpired:
        return "⚠️ 시간 초과"
    꼬 = r.stdout.decode("utf-8", errors="replace").strip().splitlines()
    return (꼬[-1].strip()[:120] if 꼬 and 꼬[-1].strip()
            else f"코드 {r.returncode}")


def main():
    최대 = "25"
    if "--최대" in sys.argv:
        최대 = sys.argv[sys.argv.index("--최대") + 1]
    찍기("===== 브리핑 전 KRX 받기 =====")

    찍기(f"  종가  {돌리기('fetch_krx_wait.py', ['--최대', 최대, '--간격', '2'])}")
    찍기(f"  지수  {돌리기('collect_index.py', [])}")

    # 받아졌나 확인 — 브리핑이 쓸 수 있는 상태인지
    for 폴더 in ("krx-daily", "index-daily"):
        d = os.path.join(_BASE, "data", 폴더)
        if not os.path.isdir(d):
            continue
        파일 = sorted(f for f in os.listdir(d) if f.endswith(".json"))
        if not 파일:
            continue
        마지막 = 파일[-1][:8]
        늦 = (dt.date.today()
              - dt.date(int(마지막[:4]), int(마지막[4:6]), int(마지막[6:]))).days
        표 = "✅" if 늦 <= 1 else "⚠️"
        try:
            j = json.load(io.open(os.path.join(d, 파일[-1]),
                                  encoding="utf-8-sig"))
            n = len(j.get("종목") or j.get("지수") or {})
        except Exception:  # noqa: BLE001
            n = 0
        찍기(f"  {표} {폴더:<12}{마지막} · {n:,}개 · {늦}일 전")
    찍기("===== 끝 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
