#!/usr/bin/env python3
r"""
reset_forward_scores.py — **forward-log 채점을 지우고 다시 채점할 수 있게** (2026-10-06)

· 10/6 버그: record_pick 이 원본 매수가를 수정 주가와 견줘 「산 날 +15% 도달」 이 잘못 적혔다 (신풍 · 위드텍 등)
· 예측(후보·규칙매수·매수가)은 **그대로 두고** 채점 칸(결과·며칠·채점일·중간성적)만 지운다 → record_pick --채점만 으로 다시
· 지우기 전 파일을 data/forward-log_백업_<시각>.jsonl 로 남긴다
"""
import datetime
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "forward-log.jsonl")
_칸 = ("결과", "며칠", "채점일", "중간성적")


def main():
    백 = _LOG.replace(".jsonl", f"_백업_{datetime.datetime.now():%Y%m%d_%H%M%S}.jsonl")
    shutil.copy(_LOG, 백)
    줄 = [json.loads(l) for l in io.open(_LOG, encoding="utf-8") if l.strip()]
    n = 0
    for r in 줄:
        for x in list(r.get("후보") or []) + list(r.get("산것") or []):
            for k in _칸:
                if k in x:
                    del x[k]
                    n += 1
    with io.open(_LOG, "w", encoding="utf-8") as f:
        for r in 줄:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"백업 {백} · 지운 칸 {n}개 · 기록 {len(줄)}일 (예측은 그대로)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
