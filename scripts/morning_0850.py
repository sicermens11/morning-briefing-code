#!/usr/bin/env python3
r"""
morning_0850.py — **08:50에 이것만 실행하면 된다** (2026-09-07 신설)

## 왜
```
08:50 예상체결가를 매일 남겨야 -3.5 vs -3.0 을 정할 수 있다 (20건 필요).
그런데 지금은 이렇게 쳐야 한다:
    python scripts\record_pick.py --동시호가 "052460=4550,092070=12550,..."
종목코드를 외워서 손으로 적어야 한다 -> **며칠 안에 안 하게 된다**
```
⇒ 이 스크립트는 **오늘 후보를 먼저 보여주고**, 숫자만 차례로 물어본다.

## 하는 일
```
1. 오늘 후보를 종목명과 함께 보여준다
2. 하나씩 예상체결가를 묻는다 (엔터만 치면 건너뛴다)
3. record_pick.py 에 넘겨 갭·상대갭·매수 판정까지 낸다
```
⚠️ **08:30~09:00에만 쓴다.** 그 밖의 시간에 넣은 값은 예상체결가가 아니라서
   gap_error.py 가 버린다.

쓰는 법:
    python scripts\morning_0850.py
    python scripts\morning_0850.py --값 "052460=4550,092070=12550"   (한 번에)
"""
import datetime as dt
import io
import json
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "forward-log.jsonl")


def main():
    이제 = dt.datetime.now()
    때 = 이제.strftime("%H:%M")
    print("=" * 66)
    print(f"  08:50 예상체결가 적기   (지금 {때})")
    print("=" * 66)
    if not ("08:30" <= 때 <= "09:00"):
        print(f"\n  ⚠️ **지금은 동시호가 시간이 아니다** (08:30~09:00).")
        print(f"     지금 넣은 값은 예상체결가가 아니라서 오차 계산에서 버려진다.")
        print(f"     그래도 넣으려면 그냥 진행하되, gap_error.py 는 이 줄을 센다.")

    if not os.path.exists(LOG):
        print("\n  ⚠️ forward-log.jsonl 이 없다. 먼저 record_pick.py 를 돌려라")
        return 1
    줄 = []
    for x in io.open(LOG, encoding="utf-8"):
        x = x.strip()
        if x:
            try:
                줄.append(json.loads(x))
            except ValueError:
                pass
    if not 줄:
        print("\n  ⚠️ 기록이 비어 있다")
        return 1
    오늘 = 줄[-1]
    후보 = 오늘.get("후보") or []
    기 = str(오늘.get("신호기준일") or "")

    print(f"\n  신호기준일 {기[:4]}-{기[4:6]}-{기[6:]} · 후보 {len(후보)}개")
    if not 후보:
        print("\n  ⬛ **오늘 후보가 없다.** 적을 것도 없고 살 것도 없다.")
        print("     (규칙상 흔한 일이다 — how_often.py 참고)")
        return 0

    # ── 한 번에 넘긴 경우 ──
    if "--값" in sys.argv:
        값 = sys.argv[sys.argv.index("--값") + 1]
    else:
        print("\n  후보의 **예상체결가**를 하나씩 적어라 (엔터만 치면 건너뜀)")
        print(f"  {'#':<3}{'종목':<14}{'코드':<9}{'전날 종가':>10}{'20일':>8}")
        for n, x in enumerate(후보, 1):
            print(f"  {n:<3}{x['이름'][:13]:<14}{x['종목코드']:<9}"
                  f"{x['어제종가']:>10,}{x['20일낙폭']:>7.1f}%")
        모 = []
        for x in 후보:
            try:
                s = input(f"    {x['이름'][:13]} ({x['종목코드']}) "
                          f"전날 {x['어제종가']:,}원 → 예상체결가: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  멈춤")
                return 1
            s = s.replace(",", "").strip()
            if not s:
                continue
            try:
                float(s)
            except ValueError:
                print(f"      ⚠️ 숫자가 아니다 — 건너뛴다")
                continue
            모.append(f"{x['종목코드']}={s}")
        if not 모:
            print("\n  ⚠️ 하나도 안 적었다. 끝낸다")
            return 0
        값 = ",".join(모)

    print(f"\n  → record_pick 에 넘긴다: {값}\n")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, os.path.join(_BASE, "scripts", "record_pick.py"),
         "--동시호가", 값], env=env, cwd=_BASE)
    if r.returncode == 0:
        print("\n  ✅ 적었다. 내일 gap_error.py 가 실제 시가와 대조한다")
        print("     python scripts\\gap_error.py")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
