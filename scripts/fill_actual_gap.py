#!/usr/bin/env python3
r"""
fill_actual_gap.py — **08:55 예측 기록표에 「진짜 시가」를 적는다** (2026-09-16 신설 · 사용자 결정 「둘 다 하자」)

## 왜
```
매일 08:55 에 예상체결가로 「시가에 얼마나 빠져서 열릴까」를 재고 산다.
백테스트는 진짜 시가로 계산했다. 둘이 얼마나 다른지를 매일 채점해야 하는데,
forward-log 의 「실제시장갭」은 record_pick 이 None 으로 넣고 **아무도 안 채웠다** (09-04 부터).
```
## 무엇을 하나
```
forward-log.jsonl 의 줄마다
  동시호가.잰시각 이 있는데  실제시장갭 이 None 이면
  → 잰 날(=매수일)의 krx-daily 에서 시가를 읽어
     종목별[code]["실제시가"] · ["실제갭"]   (어제종가 대비 %)
     실제시장갭 = 표본(동시호가.자동)의 실제 갭 중앙값   ← 예상시장갭·시장중앙갭과 같은 잣대
     실제표본수
  를 채운다. 그날 krx-daily 가 아직 없으면 건너뛴다 (다음에 다시 온다 — 멱등)
```
⚠️ 조회·기록만 한다. 주문은 없다. 다른 칸은 손대지 않는다.

쓰는 법:
    python scripts\fill_actual_gap.py            채운다
    python scripts\fill_actual_gap.py --보기      뭐가 비었나만 본다
"""
import io
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "forward-log.jsonl")
KRX = os.path.join(_BASE, "data", "krx-daily")


def _시가표(d8):
    p = os.path.join(KRX, f"{d8}.json")
    if not os.path.exists(p):
        return None
    j = json.load(io.open(p, encoding="utf-8-sig"))
    return {k: v for k, v in j.items() if isinstance(v, dict) and v.get("시가")}


def main():
    보기만 = "--보기" in sys.argv
    if not os.path.exists(LOG):
        print("⚠️ forward-log.jsonl 이 없다")
        return 1
    줄들 = [z for z in io.open(LOG, encoding="utf-8").read().split("\n")]
    바뀜 = 0
    남음 = []
    새줄 = []
    for z in 줄들:
        if not z.strip():
            새줄.append(z)
            continue
        try:
            r = json.loads(z)
        except ValueError:
            새줄.append(z)
            continue
        동 = r.get("동시호가") or {}
        잰 = str(동.get("잰시각") or "")
        if not 잰 or 동.get("실제시장갭") is not None:
            새줄.append(z)
            continue
        d8 = 잰[:10].replace("-", "")
        표 = _시가표(d8)
        if not 표:
            남음.append(d8)
            새줄.append(z)
            continue
        if 보기만:
            남음.append(f"{d8}(채울 수 있음)")
            새줄.append(z)
            continue
        # 종목별 — 예상시가·어제종가 옆에 실제시가·실제갭
        n종 = 0
        for code, v in (동.get("종목별") or {}).items():
            k = 표.get(code)
            전 = v.get("어제종가") or v.get("전일종가")
            if k and 전:
                v["실제시가"] = k["시가"]
                v["실제갭"] = round((k["시가"] / 전 - 1) * 100, 2)
                n종 += 1
        # 시장 갭 — 표본(자동)의 실제 갭 중앙값
        갭들 = []
        for code, v in (동.get("자동") or {}).items():
            k = 표.get(code)
            전 = v.get("전일종가") or v.get("어제종가")
            if k and 전:
                갭들.append((k["시가"] / 전 - 1) * 100)
        if 갭들:
            동["실제시장갭"] = round(st.median(갭들), 2)
            동["실제표본수"] = len(갭들)
        r["동시호가"] = 동
        새줄.append(json.dumps(r, ensure_ascii=False))
        바뀜 += 1
        예 = 동.get("시장중앙갭")
        print(f"  ✅ {d8}  종목 {n종}개 실제시가 적음 · 시장갭 예상 {예} → 실제 {동.get('실제시장갭')} (표본 {len(갭들)})")
    if 바뀜:
        io.open(LOG + ".bak", "w", encoding="utf-8").write("\n".join(줄들))
        io.open(LOG, "w", encoding="utf-8").write("\n".join(새줄))
    print(f"  채움 {바뀜}줄 · 아직 못 채움 {len(남음)}줄 {남음[-3:] if 남음 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
