#!/usr/bin/env python3
r"""
gap_error.py — **08:50 예상체결가가 실제 시가와 얼마나 어긋나나** (2026-09-07 신설)

## ⚠️ 이 숫자가 없으면 못 정하는 것
```
백테스트는 **실제 시가**로 갭을 잰다. 실전은 **08:50 예상체결가**로 잰다.
그 차이 때문에 실전 문턱을 -3.0 이 아니라 **-3.5**로 뒀다 (101차).

2026-09-07 오차 시뮬 결과
   오차 ±0.5%p 이하  ->  -3.0 이 낫다 (8,614만 vs 6,239만)
   오차 ±1.0%p 이상  ->  -3.5 가 낫다 (8,849만 vs 7,439만)
   그리고 오차가 커지면 -3.0 은 낙폭이 -6% -> -19.5% 로 뛴다
⇒ **오차를 재기 전에는 -3.5를 유지한다.** 이 도구가 그 오차를 잰다
```

## 어떻게 재나
```
forward-log 의 동시호가 기록에서  예상시가
krx-daily 의 그 다음 거래일에서   실제 시가
오차(%) = (예상시가 / 실제시가 - 1) x 100
```
⚠️ **표본이 20건은 넘어야** 표준편차를 믿을 수 있다. 그 전까지는 -3.5 유지.

쓰는 법:
    python scripts\gap_error.py
매일 08:50에 값을 넣는 법:
    python scripts\record_pick.py --동시호가 "052460=4550,092070=12550"
"""
import glob
import io
import json
import os
import re
import statistics as st
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "forward-log.jsonl")
KRX = os.path.join(_BASE, "data", "krx-daily")


def 다음거래일(기준일):
    """krx-daily 파일 이름으로 다음 거래일을 찾는다 (휴장일을 저절로 건너뛴다)"""
    날 = sorted(os.path.basename(p)[:8]
                for p in glob.glob(os.path.join(KRX, "*.json")))
    뒤 = [d for d in 날 if d > 기준일]
    return 뒤[0] if 뒤 else None


def 시가들(d8):
    p = os.path.join(KRX, f"{d8}.json")
    if not os.path.exists(p):
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for c, v in (d.get("종목") or {}).items():
        try:
            s = float(v.get("시가") or 0)
            if s > 0:
                out[c] = s
        except (TypeError, ValueError):
            continue
    return out


def main():
    if not os.path.exists(LOG):
        print("⚠️ forward-log.jsonl 이 없다")
        return 1
    줄 = []
    for x in io.open(LOG, encoding="utf-8"):
        x = x.strip()
        if x:
            try:
                줄.append(json.loads(x))
            except ValueError:
                pass

    print("=" * 78)
    print("  08:50 예상체결가 vs 실제 시가 — 오차")
    print("=" * 78)

    오차 = []
    맞은날 = 0
    버린날 = 0
    for r in 줄:
        동시 = r.get("동시호가") or {}
        동 = 동시.get("종목별") or {}
        if not 동:
            continue
        # ⚠️⚠️ **08:30~09:00에 잰 것만 센다** (2026-09-07 신설).
        #    동시호가는 그 시간에만 있다. 밤에 넣은 값은 예상체결가가
        #    아니라 그냥 아무 숫자다 — 2026-09-04 20:00에 넣은 시험값
        #    4건이 섞여 있었고 디엔에프는 오차 +7.73%로 나왔다
        #    (실제로는 그 시간에 잰 적이 없다)
        잰 = str(동시.get("잰시각") or "")
        때 = 잰[11:16] if len(잰) >= 16 else ""
        if not ("08:30" <= 때 <= "09:00"):
            버린날 += 1
            continue
        기 = str(r.get("신호기준일") or "")
        다 = 다음거래일(기)
        if not 다:
            continue
        시 = 시가들(다)
        if not 시:
            continue
        쓴 = 0
        for code, v in 동.items():
            예 = v.get("예상시가")
            실 = 시.get(code)
            if not 예 or not 실:
                continue
            e = (예 / 실 - 1) * 100
            오차.append({"날": 다, "code": code,
                         "이름": v.get("이름") or "", "예상": 예,
                         "실제": 실, "오차": e})
            쓴 += 1
        if 쓴:
            맞은날 += 1

    if 버린날:
        print(f"\n  ⚠️ **08:30~09:00 밖에서 넣은 기록 {버린날}일을 버렸다** — 그 시간에만 동시호가가 있다")
    if not 오차:
        print("\n  ⚠️ **아직 잰 것이 없다.**")
        print("     매일 08:50에 이렇게 넣어야 쌓인다:")
        print("       python scripts\\record_pick.py --동시호가 "
              "\"052460=4550,092070=12550\"")
        print("     그러면 다음날 이 도구가 실제 시가와 대조한다.")
        print("\n  ⇒ **20건이 쌓일 때까지 상대갭 문턱은 -3.5를 유지한다**")
        print("=" * 78)
        return 0

    v = [x["오차"] for x in 오차]
    표 = st.pstdev(v) if len(v) > 1 else 0.0
    print(f"\n  잰 것 **{len(v)}건** · {맞은날}일")
    print(f"    평균      {st.mean(v):+.3f}%")
    print(f"    표준편차   **{표:.3f}%p**   ← 오차 시뮬의 「오차 ±」가 이 값이다")
    print(f"    가장 큰 것 {max(v, key=abs):+.3f}%")
    print(f"    절대값 중앙 {st.median([abs(z) for z in v]):.3f}%")

    print("\n  ── 한 건씩 ──")
    print(f"    {'날짜':<12}{'종목':<14}{'예상':>10}{'실제':>10}{'오차':>9}")
    for x in 오차[-15:]:
        print(f"    {x['날']:<12}{x['이름'][:13]:<14}{x['예상']:>10,.0f}"
              f"{x['실제']:>10,.0f}{x['오차']:>+8.2f}%")

    print("\n  ── 그래서 문턱은 ──")
    if len(v) < 20:
        print(f"    ⚠️ 표본 {len(v)}건 — **20건은 넘어야** 믿을 수 있다. "
              f"-3.5 유지")
    elif 표 <= 0.5:
        print(f"    표준편차 {표:.2f}%p ≤ 0.5 → **-3.0 으로 바꿀 값어치가 있다** "
              f"(8,614만 vs 6,239만)")
    elif 표 >= 1.0:
        print(f"    표준편차 {표:.2f}%p ≥ 1.0 → **-3.5 를 유지한다** "
              f"(-3.0 은 낙폭이 -19.5%까지 간다)")
    else:
        print(f"    표준편차 {표:.2f}%p — 0.5~1.0 사이라 애매하다. "
              f"표본을 더 모은다")
    print("=" * 78)
    return 0


# ══ ⭐ 회차별 — _antc.log 의 08:50 · 08:55 · 09:00 값을 그날 시가와 (2026-09-14 저녁) ══
#    위 main() 은 판정 한 회차(하루 1줄)만 본다. 예약이 08:50·08:55·08:58 세 번 받으니
#    회차마다 **어느 시각이 시가를 잘 맞히나**가 쌓인다. 판정 시각 08:55 는 2026-09-14
#    하루치(21종목)로 정한 잠정값이라, 여기 표본이 20건을 넘으면 다시 판정한다
_안틱 = os.path.join(_BASE, "data", "_antc.log")
_줄꼴 = re.compile(
    r"^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):\d{2}\s+· (.+?)\((\d{6})\) 전날 ([\d,]+)원 → 예상 ([\d,]+)원")


def 회차별():
    if not os.path.exists(_안틱):
        return
    묶 = {}          # (날짜, 회차) -> {code: (이름, 예상)}
    for L in io.open(_안틱, encoding="utf-8", errors="replace"):
        m = _줄꼴.match(L.strip())
        if not m:
            continue
        날, hh, mm, 이름, code, _전, 예 = m.groups()
        if not ("08:30" <= f"{hh}:{mm}" <= "09:00"):
            continue
        # 회차 = 5분 단위로 묶는다 (08:50:23 → 08:50 · 08:58 → 08:55 묶음이 아니라 08:58 그대로)
        회 = f"{hh}:{mm}" if mm in ("50", "55", "58", "00") else f"{hh}:{int(mm) // 5 * 5:02d}"
        묶.setdefault((날, 회), {})[code] = (이름, float(예.replace(",", "")))
    if not 묶:
        return
    print("\n" + "=" * 78)
    print("  회차별 — _antc.log 의 예상체결가 vs **그날** 시가 (판정 시각을 정하는 근거)")
    print("=" * 78)
    시가캐시 = {}
    회차별오차 = {}
    없는날 = set()
    for (날, 회), 표 in sorted(묶.items()):
        d8 = 날.replace("-", "")
        if d8 not in 시가캐시:
            시가캐시[d8] = 시가들(d8)
        시 = 시가캐시[d8]
        if not 시:
            없는날.add(날)
            continue
        for code, (이름, 예) in 표.items():
            실 = 시.get(code)
            if 실:
                회차별오차.setdefault(회, []).append((예 / 실 - 1) * 100)
    if 없는날:
        print(f"  (시가가 아직 없는 날 {len(없는날)}일: {', '.join(sorted(없는날)[-3:])} — 저녁 수집 뒤에 잡힌다)")
    if not 회차별오차:
        print("  아직 맞춘 것이 없다")
        return
    print(f"\n    {'회차':<8}{'건수':>6}{'평균':>9}{'표준편차':>9}{'|오차| 중앙':>11}{'최대':>9}   판정")
    for 회 in sorted(회차별오차):
        v = 회차별오차[회]
        표 = st.pstdev(v) if len(v) > 1 else 0.0
        판 = ("표본 20 미만" if len(v) < 20 else
              ("σ ≤ 0.5 — 이 회차면 문턱 -3.0 검토" if 표 <= 0.5 else
               "σ ≥ 1.0 — 이 회차는 못 믿는다" if 표 >= 1.0 else "0.5~1.0 · 더 모은다"))
        print(f"    {회:<8}{len(v):>6}{st.mean(v):>+9.2f}{표:>9.2f}"
              f"{st.median([abs(z) for z in v]):>11.2f}{max(v, key=abs):>+9.2f}   {판}")
    print("\n  ⇒ 09:00 회차는 이미 시가라 오차 0 에 가깝다 — **그때는 못 산다.** 08:50 vs 08:55 를 본다")
    print("=" * 78)

if __name__ == "__main__":
    _rc = main()
    회차별()
    sys.exit(_rc)
