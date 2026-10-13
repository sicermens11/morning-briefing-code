#!/usr/bin/env python3
r"""
live_vs_sim.py — **시험이 고른 종목 = 실전이 고른 종목?** (2026-10-13 · ②-2 헛점 찾기)

사용자 10/13 「통과한 테스트를 견고하게 만들고, 헛점은 없는지 확인하고 …」
· 실전: data/forward-log.jsonl — 날마다 신호기준일(전날 종가) 후보 · 규칙매수(08:55 상대갭 통과 = 산다)
· 시험: data/_labs/multi_cand_live.jsonl — gate7 MULTIDUMP 가 같은 규칙으로 날마다 고른 후보(상대갭까지 통과한 것 · 「날」 = 매수일)
· 매수일 = 신호기준일 다음 거래일 — 그 날의 두 목록을 견준다
· 다르면 왜 다른지가 헛점이다: 자료(종가·재무 늦게 옴) · 08:55 갭(시험은 표본만 갭) · 규칙 해석 차이
쓰는 법: python scripts\live_vs_sim.py [시험 후보 파일]
"""
import bisect
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_실 = os.path.join(_뿌리, "data", "forward-log.jsonl")
_시 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_뿌리, "data", "_labs", "multi_cand_live.jsonl")


def main():
    시험 = {}
    머리 = {}
    for z in io.open(_시, encoding="utf-8"):
        r = json.loads(z)
        if r.get("규칙") == "_머리":
            머리 = r
        if r.get("규칙") == "L00" and r.get("날"):
            시험[r["날"]] = {h["code"] for h in r.get("후보") or []}
    시날 = sorted(시험)
    실전 = [json.loads(z) for z in io.open(_실, encoding="utf-8")]
    print(f"시험 후보 파일: {os.path.basename(_시)} · 끝 날 {머리.get('끝날')} · 후보 있는 날 {len(시험):,}")
    print(f"{'신호일':<10}{'매수일':<10}{'실전 산다':>10}{'시험 고름':>10}{'같음':>6}{'실전만':>8}{'시험만':>8}  실전만 / 시험만 종목")
    합 = {"실": 0, "시": 0, "같": 0}
    for r in 실전:
        s = str(r.get("신호기준일") or "")
        if not s or s > str(머리.get("끝날") or "99999999"):
            continue
        # 매수일 = 신호일 다음 「시험 날짜에 있는」 날이 아니라 다음 거래일 — 시험은 후보 없는 날을 안 적으니 forward-log 의 매수일 칸을 먼저 본다
        b = r.get("매수일실제") or r.get("매수일날짜")
        if not b or not str(b).isdigit():
            i = bisect.bisect_right(시날, s)
            b = 시날[i] if i < len(시날) else None
        산다 = {x.get("종목코드") for x in (r.get("후보") or []) if x.get("규칙매수") and not x.get("B전용")}
        고름 = 시험.get(b, set()) if b else set()
        같 = 산다 & 고름
        합["실"] += len(산다)
        합["시"] += len(고름)
        합["같"] += len(같)
        if 산다 or 고름:
            print(f"{s:<10}{str(b):<10}{len(산다):>10}{len(고름):>10}{len(같):>6}{len(산다 - 고름):>8}{len(고름 - 산다):>8}  "
                  f"{','.join(sorted(산다 - 고름)) or '-'} / {','.join(sorted(고름 - 산다)) or '-'}")
    print(f"\n합: 실전이 산다 {합['실']} · 시험이 고름 {합['시']} · 같음 {합['같']}")
    print("⚠️ 매수일을 시험 후보가 있는 다음 날로 잡았다 — 그 사이 시험 후보가 없는 거래일이 있으면 어긋난다(아래에서 따로 본다)")


if __name__ == "__main__":
    main()
