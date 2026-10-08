#!/usr/bin/env python3
r"""
make_spec_subset.py — **기간 바꿔 판정(split_shake)에서 「3/3」 통과한 규칙만 남긴 스펙** (2026-10-08)

B240: 오르는 걸 사는 규칙 83개 중 47개가 나눔 2017·2019·2021 모두 통과 → 그 47개만 실전과 한 계좌로 합쳐 보려고
쓰는 법: python scripts\make_spec_subset.py <판정 파일> <원 스펙> <새 스펙>
  (data/_labs 안 이름 · 판정 줄에서 「O·· … 3/3」 인 id 만 남긴다)
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
_L = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "_labs")


def main():
    판, 원, 새 = sys.argv[1:4]
    통 = set()
    for z in io.open(os.path.join(_L, 판), encoding="utf-8"):
        m = re.match(r"\s+(O\d+)\s.*\s3/3(\s|$)", z.rstrip())     # 뒤에 「⚠️짧음」 이 붙는 줄도
        if m:
            통.add(m.group(1))
    s = json.load(io.open(os.path.join(_L, 원), encoding="utf-8"))
    s["규칙"] = [r for r in s["규칙"] if r["id"] in 통]
    s["출처"] = f"{s.get('출처')} · {판} 에서 3/3 통과만 ({len(s['규칙'])}개)"
    io.open(os.path.join(_L, 새), "w", encoding="utf-8").write(json.dumps(s, ensure_ascii=False, indent=1))
    print(f"3/3 통과 {len(통)}개 → 스펙 {len(s['규칙'])}개 · {새}")


if __name__ == "__main__":
    main()
