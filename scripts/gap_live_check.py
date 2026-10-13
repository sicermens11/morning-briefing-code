#!/usr/bin/env python3
r"""
gap_live_check.py — **실전 「산다」 가 실제 시가로도 산다였나** (2026-10-13 · ②-2 헛점)

LIVECMP(10/13): 실전 상대갭(08:55 예상 체결가)이 −27~−30% 인데 실제 시가로는 0% 안팎인 종목이 여럿 —
예상 체결가가 얇은 주문으로 튀어 「싸게 시작한다」 로 본 것. 시험은 실제 시가로 판단해 안 샀다.
· 자료(forward-log.jsonl · 칸 이름은 원본 한 건으로 확인함):
  후보[]: 종목코드 · 어제종가 · 상대갭(08:55) · 문턱가 · 주문가 · 매수가(채점에 쓴 값 = 그날 실제 시가) · 규칙매수 · 결과 · 중간성적
  동시호가.종목별[코드]: 예상시가 · 실제시가 · 갭(예상) · 실제갭 · 동시호가.예상시장갭 · 실제시장갭
· 판단: 실제 시가 ≤ 주문가(지정가) 였나 = 지정가로 냈다면 실제로 샀나 · 실제 시가 ≤ 문턱가 = 시험과 같은 판단
쓰는 법: python scripts\gap_live_check.py
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    줄 = [json.loads(z) for z in io.open(os.path.join(_뿌리, "data", "forward-log.jsonl"), encoding="utf-8")]
    print(f"{'신호일':<10}{'종목':<8}{'어제종가':>9}{'예상시가':>9}{'실제시가':>9}{'주문가':>9}{'문턱가':>9}{'예상갭':>8}{'실제갭':>8}{'시장갭(예상/실제)':>18}"
          f"{'지정가 체결?':>11}{'결과':>8}{'D+10':>8}")
    n = {"산다": 0, "체결": 0, "문턱": 0, "모름": 0}
    결 = {"체결": [], "안체결": []}
    for r in 줄:
        동 = r.get("동시호가") or {}
        종 = 동.get("종목별") or {}
        for x in r.get("후보") or []:
            if not x.get("규칙매수") or x.get("B전용"):
                continue
            c = x.get("종목코드")
            j = 종.get(c) or {}
            예, 실 = _f(j.get("예상시가")), _f(j.get("실제시가"))
            주, 문 = _f(x.get("주문가")), _f(x.get("문턱가"))
            n["산다"] += 1
            if 실 is None:
                n["모름"] += 1
                체 = None
            else:
                체 = (주 is not None and 실 <= 주)
                n["체결"] += 1 if 체 else 0
                n["문턱"] += 1 if (문 is not None and 실 <= 문) else 0
            rr = x.get("결과")
            if rr is not None and 체 is not None:
                결["체결" if 체 else "안체결"].append(rr)
            d10 = (x.get("중간성적") or {}).get("D+10")
            print(f"{str(r.get('신호기준일')):<10}{c:<8}{(_f(x.get('어제종가')) or 0):>9,.0f}{(예 or 0):>9,.0f}{(실 or 0):>9,.0f}{(주 or 0):>9,.0f}{(문 or 0):>9,.0f}"
                  f"{str(j.get('갭')):>8}{str(j.get('실제갭')):>8}{(str(동.get('예상시장갭')) + '/' + str(동.get('실제시장갭'))):>18}"
                  f"{('예' if 체 else ('모름' if 체 is None else '아니오')):>11}{(f'{rr:+.1f}' if rr is not None else '-'):>8}{(str(d10) if d10 is not None else '-'):>8}")
    print(f"\n실전이 산다 {n['산다']}건 · 실제 시가 모름 {n['모름']}건")
    print(f"  · 지정가(주문가)로 냈다면 체결: {n['체결']}건 · 실제 시가가 문턱가 이하(시험과 같은 판단): {n['문턱']}건")
    for k, v in 결.items():
        if v:
            print(f"  · {k}: 채점 끝 {len(v)}건 · 평균 {sum(v) / len(v):+.2f}%")
    print("  ⚠️ 채점은 「그날 실제 시가에 샀다」 로 한다(매수기준) — 지정가가 안 닿은 날도 산 것으로 센다")


if __name__ == "__main__":
    main()
