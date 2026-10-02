#!/usr/bin/env python3
r"""
make_sector_universe.py — **넓힌 섹터 무리** 만들기 (2026-10-02 · 반도체 make_semis_universe 를 일반화)

사용자 10/2: 「휴머노이드 로봇이나 2차전지 이런것도 우리 구분되어 있나?」 — 가치사슬 지도는 11종목씩이라 표본이 작다
· 씨앗 = industry.json 업종코드(앞자리) ∪ 가치사슬 지도 섹터 ∪ 조사로 더한 것 − 조사로 뺀 것
· 조사 파일 data/<이름>-research.json: {"더함": {코드: {"이름","까닭","근거"}}, "뺌": {코드: {…}}}
  기준(반도체 3차와 같다): 상장 중 = 최근 3년(2023~25) 매출에서 그 분야가 최대 사업 또는 30% 이상 · 상장폐지 = 상장 기간
· ⚠️ 업종 코드는 지금 시점 분류다(과거 바뀐 회사 반영 안 됨)
쓰는 법:
    python scripts/make_sector_universe.py 2차전지 2820 "2차전지 소부장"
    python scripts/make_sector_universe.py 로봇 2928 "휴머노이드/로봇"
  → data/<이름>-universe.json · 조사 파일이 없으면 씨앗만으로 만든다(경고)
"""
import datetime
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chain_map import 읽기  # noqa: E402

_D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def main():
    if len(sys.argv) < 4:
        raise SystemExit("쓰는 법: make_sector_universe.py <이름> <업종코드앞자리,…> <가치사슬 섹터 이름>")
    이름, 코드앞, 섹터 = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
    ind = json.load(io.open(os.path.join(_D, "industry.json"), encoding="utf-8-sig"))
    씨 = {c for c, v in ind.items() if isinstance(v, dict) and any(str(v.get("업종코드") or "").startswith(k) for k in 코드앞)}
    지도 = {c for s, 들 in 읽기().items() if s == 섹터 for _, c in 들 if c}
    if not 지도:
        print(f"  ⚠️ 가치사슬 지도에 「{섹터}」 섹터가 없다 — 이름을 확인하라 ({sorted(읽기())})")
    조p = os.path.join(_D, f"{이름}-research.json")
    더, 뺄 = {}, {}
    if os.path.exists(조p):
        조 = json.load(io.open(조p, encoding="utf-8"))
        더, 뺄 = 조.get("더함", {}), 조.get("뺌", {})
    else:
        print(f"  ⚠️ 조사 파일이 없다({조p}) — 씨앗(업종코드 ∪ 지도)만으로 만든다")
    모 = sorted((씨 | 지도 | set(더)) - set(뺄))
    out = {"만든날": f"{datetime.datetime.now():%Y-%m-%d %H:%M}",
           "근거": f"industry.json 업종코드 {코드앞} ∪ 가치사슬 「{섹터}」 ∪ 조사 더함 − 조사 뺌 ({os.path.basename(조p)})",
           "수": {"업종코드": len(씨), "가치사슬": len(지도), "겹침": len(씨 & 지도), "더함": len(더), "뺌": len(뺄), "합": len(모)},
           "종목": 모}
    밖 = os.path.join(_D, f"{이름}-universe.json")
    io.open(밖, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{이름} 넓힌 무리 {len(모)}종목 (업종코드 {len(씨)} · 지도 {len(지도)} · 겹침 {len(씨 & 지도)} · 더함 {len(더)} · 뺌 {len(뺄)}) → {밖}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
