#!/usr/bin/env python3
r"""
antc_error.py — **예상체결가가 시가를 얼마나 맞히나** 회차별로 (2026-09-15 신설)

## 왜
```
2026-09-15 08:55  나우IB      전날 1,085원 → 예상   760원 (-29.95%)   실제 시가 1,091원 (+0.55%)
2026-09-15 08:55  에이티넘인베스트  전날 2,125원 → 예상 1,490원 (-29.88%)   실제 시가 2,115원 (-0.47%)
```
둘 다 **정확히 하한가**(전날 x 0.7)였다. 호가가 비면 예상체결가가 하한가로
찍히는데, 우리는 그걸 「30% 빠졌다」로 읽고 **살 것에 넣었다.**

⚠️ 우리 규칙은 「**많이 빠진 것**을 산다」라서, 이 가짜 값이 **정확히 우리가
   찾는 모양**으로 들어온다. 하필 가장 위험한 자리다.

## 여기서 하는 일
`data/_antc.log` 의 회차별 예상값과 `krx-daily` 의 **실제 시가**를 맞춰 본다.
  · 회차(08:50 / 08:55 / 08:58)마다 평균·중앙 오차
  · **크게 빠졌다고 나온 것**이 실제로 그랬나 — 가짜를 가려낼 문턱을 찾는다
⚠️ 짐작으로 문턱을 정하지 않는다. 실측한 값으로 정한다.

쓰는 법:
    python scripts\antc_error.py
"""
import glob
import io
import json
import os
import re
import statistics as st
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_LOG = os.path.join(_DATA, "_antc.log")

_줄 = re.compile(
    r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d):\d\d\s+· (.+?)\((\d{6})\) "
    r"전날 ([\d,]+)원 → 예상 ([\d,]+)원 \(([+-][\d.]+)%\)")


def _숫(s):
    return float(str(s).replace(",", ""))


def 읽기():
    """(날, 회차) -> [(코드, 이름, 전날, 예상, 갭%)]"""
    벌 = {}
    if not os.path.exists(_LOG):
        return 벌
    for L in io.open(_LOG, encoding="utf-8", errors="replace"):
        m = _줄.match(L.rstrip())
        if not m:
            continue
        벌.setdefault((m.group(1), m.group(2)), []).append(
            (m.group(4), m.group(3), _숫(m.group(5)), _숫(m.group(6)),
             float(m.group(7))))
    return 벌


def 시가표():
    """날짜8 -> {코드: (시가, 전날종가)}"""
    표 = {}
    앞 = {}
    for f in sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        d8 = d.get("기준일") or os.path.basename(f)[:8]
        하루 = {}
        for c, v in (d.get("종목") or {}).items():
            try:
                시 = float(v.get("시가") or 0)
                종 = float(v.get("종가") or 0)
            except (TypeError, ValueError):
                continue
            if 시 > 0:
                하루[c] = (시, 앞.get(c))
            if 종 > 0:
                앞[c] = 종
        표[d8] = 하루
    return 표


def main():
    벌 = 읽기()
    시 = 시가표()
    if not 벌:
        print("  _antc.log 에서 읽을 줄이 없다")
        return 1

    print("=" * 100)
    print("  예상체결가가 **시가**를 얼마나 맞히나 — 회차별")
    print("  ⚠️ 오차 = |예상갭 − 실제갭| (%p). 작을수록 좋다")
    print("=" * 100)

    모은것 = []          # (회차, 예상갭, 실제갭, 오차, 이름, 날)
    for (날, 회차), 줄들 in sorted(벌.items()):
        d8 = 날.replace("-", "")
        하루 = 시.get(d8)
        if not 하루:
            print(f"\n  {날} {회차} — 그날 시가 자료가 아직 없다 "
                  f"(내일 07:52에 들어온다)")
            continue
        칸 = []
        for code, 이름, 전날, 예상, 예상갭 in 줄들:
            v = 하루.get(code)
            if not v or not v[1]:
                continue
            실제갭 = (v[0] / v[1] - 1) * 100
            칸.append((abs(예상갭 - 실제갭), 예상갭, 실제갭, 이름))
            모은것.append((회차, 예상갭, 실제갭, abs(예상갭 - 실제갭), 이름, 날))
        if not 칸:
            continue
        오차들 = [z[0] for z in 칸]
        print(f"\n  {날} {회차} — {len(칸)}종목 · 평균 오차 "
              f"{st.mean(오차들):.2f}%p · 중앙 {st.median(오차들):.2f} · "
              f"최대 {max(오차들):.2f}")
        칸.sort(key=lambda z: -z[0])
        for 오, 예, 실, 이름 in 칸[:4]:
            print(f"      {이름[:14]:<16} 예상 {예:>+7.2f}%  →  실제 "
                  f"{실:>+7.2f}%   오차 **{오:.2f}%p**")

    # ── 가짜를 가려낼 문턱 ──────────────────────────────────
    if 모은것:
        print("\n" + "=" * 100)
        print("  ⭐ **크게 빠졌다고 나온 것**이 실제로 그랬나")
        print("     (우리 규칙은 많이 빠진 것을 산다 — 가짜가 **정확히 이 자리**로 들어온다)")
        print("=" * 100)
        print(f"\n  {'예상갭 구간':<18}{'개수':>6}{'평균 실제갭':>12}"
              f"{'평균 오차':>10}  보기")
        구간 = [(-100, -25, "-25% 아래"), (-25, -15, "-25 ~ -15%"),
                (-15, -8, "-15 ~ -8%"), (-8, -3.5, "-8 ~ -3.5%"),
                (-3.5, 100, "-3.5% 위")]
        for 낮, 높, 이름2 in 구간:
            칸 = [z for z in 모은것 if 낮 <= z[1] < 높]
            if not 칸:
                continue
            보기 = 칸[0]
            print(f"  {이름2:<18}{len(칸):>6}"
                  f"{st.mean([z[2] for z in 칸]):>11.2f}%"
                  f"{st.mean([z[3] for z in 칸]):>9.2f}%p"
                  f"  {보기[4][:12]} {보기[1]:+.1f}→{보기[2]:+.1f}")
        print("\n  읽는 법")
        print("    - 「-25% 아래」 칸의 **평균 실제갭이 0 근처**면 그건 전부 **가짜**다")
        print("      (호가가 비어 하한가로 찍힌 값)")
        print("    - 그 칸을 버리는 문턱을 `fetch_antc` 에 넣는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
