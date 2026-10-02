#!/usr/bin/env python3
r"""
make_semis_universe.py — **반도체 넓힌 무리** (2026-10-02)

사용자: 「지금 AI이슈로 반도체 종목이 핫한데 그럼 우리 규칙은 반도체 소부장 등 그런 종목을 하나도 못 잡는 거네?」 → 「네 앞당기세요」
· 가치사슬 지도 「반도체/HBM 소부장」 은 26종목뿐이라 표본이 작다 → **DART 표준산업분류(industry.json 업종코드)** 로 넓힌다
  - 261…  반도체 제조업 (2611 전자집적회로 · 2612 다이오드·트랜지스터 등 — ⚠️ LED·광전자 부품도 일부 섞인다)
  - 2927… 반도체·디스플레이 제조용 기계
  - + 가치사슬 「반도체/HBM 소부장」 26 (소재·검사·장비가 다른 코드에 있다: 동진쎄미켐 20129 · 리노공업 2629 · 주성엔지니어링 29229 …)
· ⚠️ 업종 코드는 **지금 시점** 분류다 (과거에 업종이 바뀐 회사는 반영 안 됨 — collect_industry.py 한계 그대로)
· 결과: data/semis-universe.json {"만든날", "근거", "종목": [코드…]} · own_lab OWN_GROUPS 의 「종목|코드,코드,…」 로 쓴다
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
    ind = json.load(io.open(os.path.join(_D, "industry.json"), encoding="utf-8-sig"))
    코드 = {c for c, v in ind.items() if isinstance(v, dict)
            and (str(v.get("업종코드") or "").startswith("261") or str(v.get("업종코드") or "").startswith("2927"))}
    사슬 = {c for s, 들 in 읽기().items() if "반도체" in s for _, c in 들 if c}
    모 = sorted(코드 | 사슬)
    out = {"만든날": f"{datetime.datetime.now():%Y-%m-%d %H:%M}",
           "근거": "industry.json 업종코드 261*(반도체 제조) · 2927*(반도체 제조용 기계) ∪ 가치사슬 「반도체/HBM 소부장」",
           "수": {"업종코드": len(코드), "가치사슬": len(사슬), "겹침": len(코드 & 사슬), "합": len(모)},
           "종목": 모}
    io.open(os.path.join(_D, "semis-universe.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"반도체 넓힌 무리 {len(모)}종목 (업종코드 {len(코드)} · 가치사슬 {len(사슬)} · 겹침 {len(코드 & 사슬)}) → data/semis-universe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
