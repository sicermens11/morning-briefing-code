#!/usr/bin/env python3
r"""
forward_groups.py — **무리 규칙 8개 예측 기록** (2026-10-02)

사용자: 「「사실 바로잡기(화면 문구)」와 「예측 기록 올리기」 두가지 진행해.」
· 규칙은 data/forward-groups-spec.json 에 **얼렸다**(10/2 · ⑮ 세 나눔 모두 통과 8개) — 바꾸지 않는다
· own_lab OWN_EXPORT=data/forward-groups-spec.json OWN_EXPORT_OUT=forward_groups_cand.jsonl 이 낸 「그날 후보」를 읽어
  **얼린 날 이후 매수일**마다 규칙별로 제 자리만큼(들고 있나·현금은 안 본다 = 신호 기록) data/forward-groups-log.jsonl 에 덧붙인다
· 이미 적은 (규칙, 매수일) 은 다시 안 적는다 — 적은 시각·얼린 커밋을 같이 남긴다 (언제 적었든 규칙이 얼어 있어 미래를 못 본다)
· 화면에는 안 띄운다 · ⚠️ 적을 때 「몫」(결과)은 대부분 비어 있다(아직 안 팔렸다) — 채점은 나중에 같은 얼린 규칙으로 다시 내보내 맞춘다
"""
import datetime
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def main():
    # 10/6: 반도체·2차전지(forward-sectors-spec.json) 도 같은 길로 — FG_SPEC · FG_CAND · FG_LOG (기본은 얼린 8개)
    spec = json.load(io.open(os.path.join(_D, os.environ.get("FG_SPEC") or "forward-groups-spec.json"), encoding="utf-8"))
    얼린 = spec["얼린날"][:10].replace("-", "")
    규칙 = {r["id"]: r for r in spec["규칙"]}
    후보p = os.path.join(_D, os.environ.get("FG_CAND") or "forward_groups_cand.jsonl")
    if not os.path.exists(후보p):
        raise SystemExit(f"🛑 {후보p} 이 없다 — own_lab OWN_EXPORT 를 먼저")
    로그p = os.path.join(_D, os.environ.get("FG_LOG") or "forward-groups-log.jsonl")
    있 = set()
    if os.path.exists(로그p):
        for 줄 in io.open(로그p, encoding="utf-8"):
            if 줄.strip():
                z = json.loads(줄)
                있.add((z["규칙"], z["매수일"]))
    끝날, 새 = None, []
    for 줄 in io.open(후보p, encoding="utf-8"):
        z = json.loads(줄)
        if z["규칙"] == "_머리":
            끝날 = max(끝날 or "", z["끝날"])
            continue
        if "대조끝" in z or "못만듦" in z:
            if "못만듦" in z:
                print(f"  🛑 {z['규칙']} 못 만듦 {z['못만듦']}")
            continue
        # 얼린 날(10/2) 매수는 얼리기(13:36) 전에 이미 시가에 샀다 — **다음 거래일부터** 받는다 (독립 검사)
        if z["날"] <= 얼린 or (z["규칙"], z["날"]) in 있 or z["규칙"] not in 규칙:
            continue
        r = 규칙[z["규칙"]]
        새.append({"기록시각": f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}", "얼린_커밋": spec["얼린_커밋"],
                  "규칙": z["규칙"], "무리": r["무리"], "조건": r["조건"], "팔기": r["팔기"], "매수일": z["날"],
                  "종목": [{"code": p["code"], "시가": p["원시"], "시총억": p.get("시총억"), "몫": p["몫"]}
                          for p in z["후보"][:r["자리"]]]})
    with io.open(로그p, "a", encoding="utf-8") as f:
        for x in sorted(새, key=lambda q: (q["매수일"], q["규칙"])):
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"얼린 날 {얼린} · 후보 자료 끝 날 {끝날} · 새로 적음 {len(새)}줄 (규칙·매수일) · 전에 적은 것 {len(있)}줄")
    for x in 새[-10:]:
        print(f"  {x['매수일']} {x['규칙']} {x['무리']} → {', '.join(p['code'] for p in x['종목'])}")
    print("[대조] 예측 기록 끝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
