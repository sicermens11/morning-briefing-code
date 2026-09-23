r"""E1 — **예상체결가를 언제 봐야 맞나** (2026-09-23 · 연휴 계획 E1)

지금 판정 시각은 **08:55** 다. 그런데 그 결정은 2026-09-14 **하루 표본**으로 했다.
여기서는 쌓인 호가 스냅샷(`data/orderbook-antc/<날짜>_<시각>.json`)을
그날 **실제 시가**(`data/krx-daily/<그날>.json`)와 대 본다.

재는 것 (시각마다)
  · 오차   = 예상체결가 ÷ 실제 시가 − 1   (%p)
  · 치우침 = 오차의 가운데값 (양수면 예상이 **높게** 나온다)
  · 흩어짐 = |오차| 의 가운데값 · 90분위
  · 뒤집힘 = 예상은 갭 −3.5%p 아래인데 실제 시가는 아니었던 비율 (판정이 뒤집히는 자리)

쓰기: python scripts/antc_timing.py
⚠️ 표본이 얇으면 **결론을 내지 않는다** — 며칠 치인지 맨 위에 찍는다.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
자료 = os.path.join(뿌리, "data")

# ── 스냅샷 모으기 ──
스냅 = {}
for 길 in sorted(glob.glob(os.path.join(자료, "orderbook-antc", "*.json"))):
    이름 = os.path.basename(길)[:-5]
    if "_" not in 이름:
        continue
    날, 시각 = 이름.split("_", 1)
    try:
        d = json.load(io.open(길, encoding="utf-8-sig"))
    except ValueError:
        continue
    스냅.setdefault(시각, {})[날] = (d.get("호가") or {})

if not 스냅:
    print("⚠️ orderbook-antc 스냅샷이 없다")
    raise SystemExit(0)

# ── 그날 실제 시가 ──
시가표 = {}


def 하루(날):
    if 날 not in 시가표:
        길 = os.path.join(자료, "krx-daily", f"{날}.json")
        try:
            d = json.load(io.open(길, encoding="utf-8-sig"))
            시가표[날] = d.get("종목") or {}
        except (OSError, ValueError):
            시가표[날] = {}
    return 시가표[날]


날전부 = sorted({날 for v in 스냅.values() for 날 in v})
있는날 = [날 for 날 in 날전부 if 하루(날)]
print(f"E1 — 스냅샷 {len(날전부)}일 · 그날 시가까지 있는 날 {len(있는날)}일 "
      f"({있는날[0] if 있는날 else '?'} ~ {있는날[-1] if 있는날 else '?'})")
if len(있는날) < 15:
    print(f"⚠️ **표본이 얇다 ({len(있는날)}일).** 아래 숫자는 참고만 한다 — 판정 시각은 안 바꾼다.")
    print("   (9/14 하루 표본으로 08:55 를 정했던 것과 같은 실수를 반복하지 않는다)")

print(f"\n   {'시각':<8}{'날':>5}{'종목·날':>9}{'치우침(가운데)':>16}{'|오차| 가운데':>15}{'|오차| 90분위':>15}")
결과 = {}
for 시각 in sorted(스냅):
    오차들 = []
    날수 = 0
    for 날, 호가 in sorted(스냅[시각].items()):
        그날 = 하루(날)
        if not 그날:
            continue
        날수 += 1
        for code, v in 호가.items():
            예상 = v.get("예상체결가")
            실제 = (그날.get(code) or {}).get("시가")
            if not 예상 or not 실제:
                continue
            try:
                예상, 실제 = float(예상), float(실제)
            except (TypeError, ValueError):
                continue
            if 예상 <= 0 or 실제 <= 0:
                continue
            오차들.append((예상 / 실제 - 1) * 100)
    if not 오차들:
        continue
    절대 = sorted(abs(z) for z in 오차들)
    결과[시각] = (날수, len(오차들), st.median(오차들), st.median(절대), 절대[int(len(절대) * 0.9)])
    print(f"   {시각[:2]}:{시각[2:]:<4}{날수:>5}{len(오차들):>9}"
          f"{결과[시각][2]:>15.2f}%p{결과[시각][3]:>14.2f}%p{결과[시각][4]:>14.2f}%p")

if len(결과) >= 2:
    좋은 = min(결과, key=lambda k: 결과[k][3])
    print(f"\n   ⇒ |오차| 가운데값이 가장 작은 시각: **{좋은[:2]}:{좋은[2:]}** "
          f"({결과[좋은][3]:.2f}%p · {결과[좋은][0]}일 {결과[좋은][1]}건)")
    if len(있는날) < 15:
        print("   ⚠️ 그래도 **바꾸지 않는다** — 15일 넘게 쌓인 뒤 다시 본다")
else:
    print("\n   ⇒ 견줄 시각이 둘도 안 된다")
