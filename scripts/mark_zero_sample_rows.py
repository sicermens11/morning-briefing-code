r"""(월요일 제안 C) forward-log 의 「표본갭이 딱 0.0 투성이」 인 지난 줄에 표본무효 표시를 붙인다 — 기본은 보기만.

  python scripts\mark_zero_sample_rows.py          어느 줄이 걸리나 보기만 (아무것도 안 바꾼다)
  python scripts\mark_zero_sample_rows.py --적용    표시를 붙인다 (.bak 를 남긴다)

⚠️ 예상시장갭 값은 지우지 않는다 — 그날 실제로 그 값으로 판정했으니까. 「표본무효」 표시만 더해
   채점·limit_replay 가 그 줄을 따로 셀 수 있게 한다.
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "forward-log.jsonl")


def main():
    적용 = "--적용" in sys.argv
    줄들 = io.open(LOG, encoding="utf-8").read().split("\n")
    새, n = [], 0
    for z in 줄들:
        if not z.strip():
            새.append(z); continue
        r = json.loads(z)
        동 = r.get("동시호가") or {}
        표 = 동.get("표본갭") or []
        영 = sum(1 for g in 표 if g is not None and abs(g) < 1e-12)
        if len(표) >= 10 and 영 * 2 >= len(표) and not 동.get("표본무효"):
            n += 1
            print(f"  {r.get('매수일')}  표본 {len(표)} 중 0.0 {영}개 · 예상시장갭 {동.get('예상시장갭')}")
            if 적용:
                동["표본무효"] = f"0.0 이 {영}/{len(표)}개 — 받기 실패로 보임(10/16 주말 점검 · 사후 표시)"
                r["동시호가"] = 동
                z = json.dumps(r, ensure_ascii=False)
        새.append(z)
    print(f"  걸린 줄 {n}개 · {'표시 붙임' if 적용 else '보기만 (--적용 이면 붙인다)'}")
    if 적용 and n:
        io.open(LOG + ".bak_zero", "w", encoding="utf-8").write("\n".join(줄들))
        io.open(LOG, "w", encoding="utf-8").write("\n".join(새))
    return 0


if __name__ == "__main__":
    sys.exit(main())
