#!/usr/bin/env python3
r"""
freeze_sector_spec.py — **반도체·2차전지 규칙을 예측 기록용으로 얼린다** (2026-10-06)

사용자 10/6: 「1. 반도체·2차전지 규칙을 예측 기록 장부에 더하고, 화면에는 안 넣는다」
· make_spec 이 낸 data/_labs/forward_sectors_raw.json (B218 반도체 · B220 2차전지 통과 7개) 에서
  **8년 자료 규칙만**(짧음 ⚠️ 뺌) 남겨 data/forward-sectors-spec.json 으로 얼린다 · id 는 S01~ (얼린 8개 O·· 와 안 겹치게)
· 무리 글(「종목 = 코드,코드,…」)에 그날 쓴 종목 목록이 그대로 들어 있다 — 목록 파일이 바뀌어도 기록은 얼린 목록으로 돈다
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
_밖 = os.path.join(_B, "data", "forward-sectors-spec.json")


def main():
    if os.path.exists(_밖):
        raise SystemExit(f"🛑 {_밖} 이 이미 있다 — 얼린 규칙은 덮지 않는다")
    raw = json.load(io.open(os.path.join(_B, "data", "_labs", "forward_sectors_raw.json"), encoding="utf-8"))["규칙"]
    남 = [r for r in raw if not r.get("짧음")]
    for k, r in enumerate(남, 1):
        r["id"] = f"S{k:02d}"
        r["섹터"] = "반도체" if "B218_반도체" in r["파일"] else ("2차전지" if "2차전지" in r["파일"] else r["파일"])
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=_B, capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        head = "?"
    spec = {"얼린날": f"{datetime.datetime.now():%Y-%m-%d %H:%M}",
            "얼린_커밋": f"이 파일이 처음 들어간 커밋 — git log --follow -- data/forward-sectors-spec.json (만들 때 HEAD 는 {head})",
            "근거": "B218 반도체 넓힌 무리 · B220 2차전지 넓힌 무리 (낙폭 체 없음 · 자름 20) ⑨ 통과 중 8년 자료 규칙",
            "사용자": "「1. 반도체·2차전지 규칙을 예측 기록 장부에 더하고, 화면에는 안 넣는다」 (2026-10-06)",
            "쓰는 법": "own_lab OWN_EXPORT=data/forward-sectors-spec.json OWN_EXPORT_OUT=forward_sectors_cand.jsonl (MAXDD=-999 · OWN_CUT=20) → "
                      "forward_groups.py (FG_SPEC·FG_CAND·FG_LOG) → data/forward-sectors-log.jsonl",
            "주의": "목록을 2026년 지금 업종으로 만들어 과거 성적이 부풀었다(사후 선택) — 앞으로 맞는지만 본다 · 화면에는 안 띄운다",
            "규칙": 남}
    io.open(_밖, "w", encoding="utf-8").write(json.dumps(spec, ensure_ascii=False, indent=1))
    print(f"얼렸다 {_밖} · {len(남)}개 (뺀 짧은 자료 {len(raw) - len(남)}개)")
    for r in 남:
        print(f"  {r['id']} {r['섹터']} [{r['조건']}] 자리 {r['자리']} · {r['팔기']} · 뒤 연 {r.get('뒤연')}% · 낙폭 {r.get('뒤낙폭')}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
