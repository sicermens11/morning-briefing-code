#!/usr/bin/env python3
r"""
gap_error_lab.py — **245차 · 예상체결가 vs 실제 시가** (2026-09-10 밤 신설)

## 사용자 물음
```
「08:50에 09:00까지 계속 변동되던데 이게 예상체결가고, 시가가 되는거야?」
```

## ⚠️ 코드에 **적어놓고 한 번도 안 쟀다**
```
record_pick.py:317
   「백테스트는 **실제 시가**로 시장 중앙갭을 냈는데
     실전은 08:50 **예상체결가**로 낸다. 이 둘이 얼마나 다른지 **모른다**.
     예상체결가는 09:00 직전에 크게 바뀌기도 한다.
     => 매일 남겨두면 나중에 **문턱값이 얼마나 어긋나는지** 잴 수 있다」

=> forward-log 에 쌓고 있는데 **한 번도 안 쟀다**.
   101차에서 -3.0%p 대신 **-3.5%p** 로 잡은 게 이 오차 대비였는데
   그 여유가 **맞는지 틀린지 모른다**
```

## 재는 것
```
A ⭐⭐⭐ 종목마다 **예상시가 -> 실제 시가** 오차 (%p)
B ⭐⭐⭐ **중앙갭**의 오차 — 이게 문턱에 직접 걸린다
C ⭐⭐  오차 때문에 **판정이 뒤집힌 종목**이 몇 개인가
        (08:50 엔 「산다」였는데 실제로는 문턱을 못 넘은 것, 또는 반대)
D ⭐   **-3.5%p 여유가 맞나** — 오차 분포로 되짚어 본다
```

## ⚠️ 표본
```
forward-log 는 **2026-09-03 부터**다. 아직 며칠 안 된다.
동시호가를 손으로 넣은 날만 잴 수 있다 -> **표본이 아주 작을 것**이다
그래도 **틀을 만들어 두면** 날마다 쌓인다
```

쓰는 법:
    python scripts\gap_error_lab.py
"""
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "forward-log.jsonl")
_갭문턱 = -3.5


def main():
    if not os.path.exists(LOG):
        print("  ⚠️ forward-log 가 없다")
        return 1
    줄들 = []
    for line in io.open(LOG, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                줄들.append(json.loads(line))
            except ValueError:
                pass
    print(f"  forward-log {len(줄들):,}일")

    주가 = O.수정주가(("시총", "거래대금"))
    원시 = O.원시주가() if hasattr(O, "원시주가") else None
    날 = sorted(주가)

    print("\n" + "=" * 96)
    print("  245차 · ⭐⭐⭐ **예상체결가 vs 실제 시가**")
    print("     record_pick 이 「이 둘이 얼마나 다른지 **모른다**」고 적어놓고")
    print("     forward-log 에 쌓기만 했다 — **한 번도 안 쟀다**")
    print("=" * 96)

    잰것, 못잰것 = [], 0
    for r in 줄들:
        기준 = r.get("신호기준일")
        동 = r.get("동시호가") or {}
        종별 = 동.get("종목") or {}
        if not 종별:
            못잰것 += 1
            continue
        # 매수일 = 기준일 다음 거래일
        뒤 = [d for d in 날 if d > 기준]
        if not 뒤:
            continue
        매수일 = 뒤[0]
        for c, v in 종별.items():
            예상 = v.get("예상시가")
            어제 = v.get("어제종가")
            if not (예상 and 어제 and 어제 > 0):
                continue
            실 = 주가[매수일].get(c)
            if not 실:
                continue
            # ⚠️ 수정주가라 원본 시가와 다를 수 있다 — 비율로만 본다
            실시가 = 실[0]
            어제수정 = None
            앞 = [d for d in 날 if d <= 기준]
            if 앞:
                z = 주가[앞[-1]].get(c)
                어제수정 = z[0] if z else None
            if not 어제수정 or 어제수정 <= 0:
                continue
            예상갭 = (예상 / 어제 - 1) * 100
            실제갭 = (실시가 / 어제수정 - 1) * 100
            잰것.append({"날": 기준, "code": c, "이름": v.get("이름", ""),
                        "예상갭": 예상갭, "실제갭": 실제갭,
                        "오차": 실제갭 - 예상갭})

    print(f"\n  잰 것 **{len(잰것):,}건** · 동시호가가 없어 못 잰 날 {못잰것}일")
    if not 잰것:
        print("\n  ⚠️ **아직 잴 것이 없다.**")
        print("     08:50 에 `--동시호가` 로 예상체결가를 넣은 날만 잴 수 있다")
        print("     틀은 만들어 뒀으니 **날마다 쌓이면** 그때 잰다")
        print("=" * 96)
        return 0

    오차들 = sorted(x["오차"] for x in 잰것)
    n = len(오차들)
    print("\n  ── A ⭐⭐⭐ **종목마다 오차** (실제갭 − 예상갭, %p) ──")
    print(f"     가운데 **{오차들[n//2]:+.2f}%p** · "
          f"평균 {st.mean(오차들):+.2f}%p")
    print(f"     아래 10% {오차들[n//10]:+.2f} · 위 10% {오차들[int(n*0.9)]:+.2f}")
    print(f"     가장 나쁨 {오차들[0]:+.2f} · 가장 좋음 {오차들[-1]:+.2f}")
    if n > 3:
        print(f"     **흩어짐(표준편차) {st.pstdev(오차들):.2f}%p**")

    print("\n  ── B ⭐⭐⭐ **중앙갭의 오차** (문턱에 직접 걸린다) ──")
    날별 = {}
    for x in 잰것:
        날별.setdefault(x["날"], []).append(x)
    print(f"  {'날':<12}{'예상 중앙':>10}{'실제 중앙':>10}{'오차':>9}{'종목':>6}")
    중오차 = []
    for d, 벌 in sorted(날별.items()):
        if len(벌) < 2:
            continue
        예중 = st.median([x["예상갭"] for x in 벌])
        실중 = st.median([x["실제갭"] for x in 벌])
        중오차.append(실중 - 예중)
        print(f"  {d:<12}{예중:>9.2f}%{실중:>9.2f}%{실중-예중:>+8.2f}p{len(벌):>6}")
    if 중오차:
        print(f"\n     중앙갭 오차 — 가운데 {sorted(중오차)[len(중오차)//2]:+.2f}%p")

    print("\n  ── C ⭐⭐ **판정이 뒤집힌 종목** ──")
    뒤집 = 0
    for d, 벌 in sorted(날별.items()):
        if len(벌) < 2:
            continue
        예중 = st.median([x["예상갭"] for x in 벌])
        실중 = st.median([x["실제갭"] for x in 벌])
        for x in 벌:
            예상판 = (x["예상갭"] - 예중) <= _갭문턱
            실제판 = (x["실제갭"] - 실중) <= _갭문턱
            if 예상판 != 실제판:
                뒤집 += 1
                print(f"     {d} {x['이름'][:12]:<14}"
                      f"08:50 {'산다' if 예상판 else '안 산다'} → "
                      f"실제 {'산다' if 실제판 else '안 산다'}"
                      f"  (상대갭 {x['예상갭']-예중:+.2f} → {x['실제갭']-실중:+.2f})")
    print(f"     ⇒ 뒤집힌 것 **{뒤집}건 / {len(잰것)}건**")

    print("\n  ── D ⭐ **-3.5%p 여유가 맞나** ──")
    if n > 3:
        흩 = st.pstdev(오차들)
        print(f"     오차 흩어짐 {흩:.2f}%p · 101차가 잡은 여유 **0.5%p**"
              f" (-3.0 → -3.5)")
        if 흩 > 0.5:
            print(f"     ⚠️ 흩어짐이 여유보다 **크다** — 여유를 늘려야 할 수 있다")
        else:
            print("     ✅ 흩어짐이 여유 안에 든다")
    print("\n" + "=" * 96)
    print("  ⚠️ 표본이 작다. **날마다 쌓아** 다시 재야 한다")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    _p = os.path.join(_BASE, "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_245차_예상체결가오차.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
