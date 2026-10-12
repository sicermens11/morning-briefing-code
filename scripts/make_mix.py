#!/usr/bin/env python3
r"""
make_mix.py — **여러 규칙 묶음(B·C·반도체)을 한 스펙·한 후보 파일로 합친다** (2026-10-12)

사용자 10/12: 「지금 규칙과 반영예정과 예측 기록중의 조합에 대해서는 테스트 한건가?」
→ 지금 규칙 + B 만 쟀다(B240b). + C 는 끝 날이 달라 멈췄고, + 반도체 · 넷 다는 안 쟀다 → multi_lab 이 한 번에 읽게 합친다

쓰는 법:  python scripts\make_mix.py <이름> <스펙1> <후보1> [<스펙2> <후보2> …]
          (경로는 data/ 기준 · 결과: data/_labs/spec_mix_<이름>.json · data/_labs/mix_cand_<이름>.jsonl)
⚠️ 규칙 id 가 겹치면 멈춘다 · 후보 파일 끝 날이 다르면 멈춘다(multi_lab 도 다시 본다)
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def main():
    이름, 짝 = sys.argv[1], sys.argv[2:]
    if not 짝 or len(짝) % 2:
        raise SystemExit("꼴: make_mix.py <이름> <스펙> <후보> [<스펙> <후보> …]")
    규칙, 끝날들, 줄수 = [], set(), 0
    밖후보 = os.path.join(_D, "_labs", f"mix_cand_{이름}.jsonl")
    with io.open(밖후보, "w", encoding="utf-8") as fo:
        for i in range(0, len(짝), 2):
            s = json.load(io.open(os.path.join(_D, 짝[i]), encoding="utf-8"))["규칙"]
            ids = {r["id"] for r in 규칙}
            겹 = [r["id"] for r in s if r["id"] in ids]
            if 겹:
                raise SystemExit(f"🛑 규칙 id 가 겹친다: {겹}")
            규칙 += s
            for z in io.open(os.path.join(_D, 짝[i + 1]), encoding="utf-8"):
                if not z.strip():
                    continue
                r = json.loads(z)
                if r.get("규칙") == "_머리":
                    끝날들.add(r["끝날"])
                fo.write(z if z.endswith("\n") else z + "\n")
                줄수 += 1
    if len(끝날들) != 1:
        os.remove(밖후보)
        raise SystemExit(f"🛑 후보 파일 끝 날이 다르다 {sorted(끝날들)} — 같은 날까지 다시 내라")
    json.dump({"규칙": 규칙, "만든것": f"make_mix {' '.join(짝)}"},
              io.open(os.path.join(_D, "_labs", f"spec_mix_{이름}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"spec_mix_{이름}.json 규칙 {len(규칙)}개 ({', '.join(r['id'] for r in 규칙)}) · mix_cand_{이름}.jsonl {줄수}줄 · 끝 날 {끝날들.pop()}")


if __name__ == "__main__":
    main()
