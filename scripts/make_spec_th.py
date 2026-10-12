#!/usr/bin/env python3
r"""
make_spec_th.py — **B 스펙에 사는 문턱(상대갭)만 바꾼 사본** (2026-10-12)

사용자 10/12: 「지금 규칙에 3.5% 적용하는게 뭐였지? B에는 조금더 엄격한 기준을 적용하면 되지 않아?」
B 8개는 문턱 「안 봄」(99) — 문턱만 바꾸고 조건·자리·파는 규칙은 그대로 둔다
쓰는 법: python scripts\make_spec_th.py -2   → data/_labs/spec_B_th-2.json
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
문 = float(sys.argv[1])
j = json.load(io.open(os.path.join(_D, "forward-groups-spec.json"), encoding="utf-8"))
for r in j["규칙"]:
    r["문턱"] = 문
j["바꿈"] = f"10/12 make_spec_th — 문턱 99 → {문:g} (나머지 그대로)"
p = os.path.join(_D, "_labs", f"spec_B_th{문:g}.json")
json.dump(j, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{os.path.basename(p)} · 규칙 {len(j['규칙'])}개 · 문턱 {문:g}")
