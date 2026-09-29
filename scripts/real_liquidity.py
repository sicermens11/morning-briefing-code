#!/usr/bin/env python3
# ⚠️ docstring 은 r""" (raw) — 윈도 경로의 `\u` 가 유니코드 이스케이프로 해석되면 파일이 깨진다.
r"""real_liquidity.py — **우리가 실제로 넣는 돈이 거래대금의 몇 %인가** (2026-09-29 신설)

## 왜 있나
사용자: 「거래대금 1% 한도랑 시드 제한은 왜 필요한거야?」

코드 어디에도 **왜 1% 인지 안 적혀 있다.** 그런데 B136 에서 재보니
그 숫자 하나가 결론을 통째로 뒤집는다:

    대형이 이기기 시작하는 자산
      한도 0.5% → **1억**   ·  1% → **3억**  ·  2% → **10억**
      한도 5%   → 10억      ·  10% → **안 뒤집힘**

⇒ 「3억부터 대형」은 사실이 아니라 **「1% 를 골랐을 때 그렇다」** 였다.

## 시뮬 안에서는 1% 가 맞는지 알 수 없다
「하루 거래대금의 몇 % 까지 시가에 체결되나」는 **실제 주문 기록**으로만 안다.
우리에겐 그게 있다 — `forward-log.jsonl` 에 매일 후보·주문가·매수 여부가 쌓인다.

## 무엇을 재나
  ① 실전에서 **실제로 산 종목**마다 — 넣은 돈이 그날 거래대금의 몇 % 였나
  ② 그 분포 (가운데 · 위 10% · 최대)
  ③ 지금 자산에서 규칙대로 사면 몇 % 가 되나 (아직 한도에 안 걸리는지)
  ④ **자산이 얼마가 되면 1% 에 걸리기 시작하나**

⚠️ 실전 표본이 적으면(2026-08-25 부터) 「그래서 1% 가 맞다」고 단정하지 않는다.
   표본 수를 같이 찍고, 모자라면 **모자라다고 말한다**.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_데이터 = os.path.join(_뿌리, "data")

# ── 실전 기록 ──
줄들 = []
try:
    for z in io.open(os.path.join(_데이터, "forward-log.jsonl"), encoding="utf-8-sig"):
        z = z.strip()
        if z:
            try:
                줄들.append(json.loads(z))
            except ValueError:
                pass
except OSError:
    print("🔴 forward-log 를 못 읽었다")
    raise SystemExit(1)

print("=" * 96)
print("  우리가 실제로 넣는 돈이 거래대금의 몇 % 인가")
print("=" * 96)
print(f"\n  실전 기록 {len(줄들)}일"
      f" ({줄들[0].get('신호기준일') if 줄들 else '-'} ~ {줄들[-1].get('신호기준일') if 줄들 else '-'})")

# ── 그날 거래대금 — krx-daily 에서 ──
def _대금표(d8):
    for _p in (os.path.join(_데이터, "krx-daily", f"{d8}.json"),
               os.path.join(_데이터, "krx-daily", f"{d8[:4]}-{d8[4:6]}-{d8[6:]}.json")):
        if os.path.exists(_p):
            try:
                _j = json.load(io.open(_p, encoding="utf-8-sig"))
            except ValueError:
                return {}
            _벌 = _j.get("종목") or _j.get("items") or _j
            _밖 = {}
            if isinstance(_벌, dict):
                for _c, _v in _벌.items():
                    if isinstance(_v, dict):
                        _밖[_c] = _v.get("거래대금") or _v.get("대금") or 0
            elif isinstance(_벌, list):
                for _v in _벌:
                    if isinstance(_v, dict):
                        _c = str(_v.get("종목코드") or _v.get("code") or "")
                        if _c:
                            _밖[_c] = _v.get("거래대금") or _v.get("대금") or 0
            return _밖
    return {}


산것 = []
for d in 줄들:
    _d8 = str(d.get("신호기준일") or "")
    for c in (d.get("후보") or []):
        if not c.get("규칙매수"):
            continue
        산것.append((_d8, str(c.get("종목코드") or ""), c.get("이름"),
                     c.get("주문가") or c.get("문턱가")))

print(f"  규칙으로 산 것 {len(산것)}건")
if not 산것:
    print("\n  🔴 실전에서 규칙매수가 **한 건도 없다** — 이 자료로는 못 잰다")
    print("     (8월 말부터 상대갭 -3.5%p 를 넘은 날이 드물었다)")
    print("\n  ⇒ 대신 **후보 전체**로 잰다 — 「샀다면 얼마를 넣었을까」")
    산것 = []
    for d in 줄들[-20:]:
        _d8 = str(d.get("신호기준일") or "")
        for c in (d.get("후보") or [])[:6]:
            산것.append((_d8, str(c.get("종목코드") or ""), c.get("이름"),
                         c.get("어제종가") or c.get("주문가")))
    print(f"     최근 20일 후보 위 6개씩 — {len(산것)}건")

# ── 자산별로 몇 % 가 되나 ──
print(f"\n  자산이 커지면 한 종목에 **거래대금의 몇 %** 를 넣게 되나 (비중 20% 기준)")
print(f"  {'자산':>16}{'한 종목에':>16}{'거래대금 대비 가운데':>22}{'위 10%':>12}{'1% 넘는 비율':>14}")
_대금캐시 = {}
_비율들 = {}
for _자산 in (5_000_000, 50_000_000, 100_000_000, 300_000_000, 1_000_000_000):
    _넣 = _자산 * 0.20
    _벌 = []
    for _d8, _c, _이름, _값 in 산것:
        if _d8 not in _대금캐시:
            _대금캐시[_d8] = _대금표(_d8)
        _대 = (_대금캐시[_d8] or {}).get(_c)
        if not _대 or _대 <= 0:
            continue
        _벌.append(_넣 / _대 * 100)
    if not _벌:
        print(f"  {_자산:>16,}{_넣:>16,.0f}{'(거래대금 자료 없음)':>22}")
        continue
    _벌.sort()
    _비율들[_자산] = _벌
    _넘 = sum(1 for z in _벌 if z > 1.0) / len(_벌) * 100
    print(f"  {_자산:>16,}{_넣:>16,.0f}{_벌[len(_벌) // 2]:>21.2f}%"
          f"{_벌[int(len(_벌) * 0.9)]:>11.2f}%{_넘:>13.0f}%")

if _비율들:
    _첫 = sorted(_비율들)[0]
    print(f"\n  표본 {len(_비율들[_첫])}건 (거래대금 자료가 있는 것만)")
    print("\n  ⇒ 「1% 넘는 비율」이 0% 인 자산 규모에서는 **한도가 아예 안 걸린다.**")
    print("     그 위부터 한도가 실제로 물리기 시작한다")
else:
    print("\n  🔴 거래대금 자료를 못 붙였다 — krx-daily 의 꼴을 확인해야 한다")
