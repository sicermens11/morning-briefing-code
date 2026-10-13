#!/usr/bin/env python3
r"""
limit_replay.py — **새 방식(후보 전부 문턱가 지정가 · 자리만큼)이었다면 9/3~ 몇 번 샀나** (2026-10-13)

사용자 10/13 「「지정가 주문」이 뜨는 날이 늘어난다는 건 기회도 많아진다는 뜻이야?」
· forward-log 날마다: 동시호가.종목별(예상시가·실제시가·어제종가) · 예상시장갭 · 쓴문턱
· 새 방식: 예상 상대갭 깊은 순으로 하루 6자리(섹터 2 는 근사로 뺌) · 주문가 = 문턱가(예상가 밑이면 max(문턱, 예상×1.005))
· 체결 = 실제 시가 ≤ 주문가 · 옛 방식(예상가가 문턱 밑인 것만 주문)과 견준다
쓰는 법: python scripts\limit_replay.py
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    줄 = [json.loads(z) for z in io.open(os.path.join(_뿌리, "data", "forward-log.jsonl"), encoding="utf-8")]
    합 = {"옛주문": 0, "옛체결": 0, "새주문": 0, "새체결": 0, "날": 0, "새체결날": 0, "옛체결날": 0}
    print(f"{'신호일':<10}{'시장갭':>7}{'옛 주문/체결':>12}{'새 주문/체결':>12}  새로 체결된 종목")
    for r in 줄:
        동 = r.get("동시호가") or {}
        종 = 동.get("종목별") or {}
        중 = 동.get("예상시장갭")
        문턱 = 동.get("쓴문턱") or -3.5
        if 중 is None or not 종:
            continue
        줄들 = []
        for c, v in 종.items():
            어, 예, 실 = v.get("어제종가"), v.get("예상시가"), v.get("실제시가")
            if not (어 and 예):
                continue
            상 = (예 / 어 - 1) * 100 - 중
            문 = 어 * (1 + (중 + 문턱) / 100)
            ok = 상 <= 문턱
            주 = max(문, 예 * 1.005) if ok else 문
            줄들.append((상, c, ok, 주, 실))
        if not 줄들:
            continue
        합["날"] += 1
        줄들.sort()
        옛 = [z for z in 줄들 if z[2]][:6]
        새 = 줄들[:6]
        옛체 = [z for z in 옛 if z[4] is not None and z[4] <= z[3]]
        새체 = [z for z in 새 if z[4] is not None and z[4] <= z[3]]
        합["옛주문"] += len(옛); 합["옛체결"] += len(옛체); 합["새주문"] += len(새); 합["새체결"] += len(새체)
        합["옛체결날"] += 1 if 옛체 else 0
        합["새체결날"] += 1 if 새체 else 0
        print(f"{str(r.get('신호기준일')):<10}{중:>+7.2f}{f'{len(옛)}/{len(옛체)}':>12}{f'{len(새)}/{len(새체)}':>12}  {','.join(z[1] for z in 새체) or '-'}")
    print(f"\n{합['날']}일: 옛 방식 주문 {합['옛주문']} · 체결 {합['옛체결']}(체결 있던 날 {합['옛체결날']}) │ "
          f"새 방식 주문 {합['새주문']} · 체결 {합['새체결']}(체결 있던 날 {합['새체결날']})")
    print("⚠️ 실제 시가가 없는 날(받기 전)은 체결로 안 센다 · 섹터 자리 2 는 빼고 하루 6 으로만 근사")


if __name__ == "__main__":
    main()
