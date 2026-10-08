#!/usr/bin/env python3
r"""
freeze_market_spec.py — **전체 시장 규칙 4개(C)를 예측 기록용으로 얼린다** (2026-10-08)

사용자 10/7: 「B는 반영, C는 예측 기록을 본 뒤 판단」 · 「3,4는 너 권고대로 하자」(C 예측 기록 주 1회)
· data/_labs/spec_b221_2019all_4.json (B229 흔들기 3/3 통과 4개) → data/forward-market-spec.json
· id 는 M01~M04 (얼린 8개 O·· · 반도체·2차전지 S·· 와 안 겹치게)
· 이미 얼린 파일이 있으면 덮지 않는다 (바꾸려면 새 이름으로)
"""
import datetime
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_밖 = os.path.join(_B, "data", "forward-market-spec.json")


def main():
    if os.path.exists(_밖):
        print(f"이미 얼렸다 — {_밖} (안 덮는다)")
        return 0
    src = json.load(io.open(os.path.join(_B, "data", "_labs", "spec_b221_2019all_4.json"), encoding="utf-8"))
    규칙 = []
    for k, r in enumerate(src["규칙"], 1):
        규칙.append(dict(r, id=f"M{k:02d}", 옛id=r.get("id")))
    머리 = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=_B, capture_output=True, text=True).stdout.strip()
    out = {"얼린날": f"{datetime.datetime.now():%Y-%m-%d %H:%M}", "얼린_커밋": f"만들 때 HEAD {머리}",
           "출처": src.get("출처"), "사용자": "10/7 「C는 예측 기록을 본 뒤 판단」 · 주 1회",
           "설정": "OWN_ALL · OWN_START=20200102 · OWN_SPLIT=20240101 · MAXDD=-999 · OWN_CUT=20 (B221 그대로)",
           "규칙": 규칙}
    io.open(_밖, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"얼림 — {len(규칙)}개 · {out['얼린날']} → {_밖}")
    for r in 규칙:
        print(f"  {r['id']} [{r['조건']}] 문턱 {r['문턱']} · 자리 {r['자리']} · {r['팔기']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
