#!/usr/bin/env python3
r"""
compare_live.py — **B 아침 후보(OWN_LIVE) 대조** (2026-10-08)

사용자 10/7 「그렇다고 테스트의 정확도가 떨어져서는 안돼!」 — 아침 방식은 옛 방식과 **하나도 안 다를 때만** 쓴다.

두 가지를 본다:
  ① 옛 날들은 그대로인가 — OWN_LIVE + OWN_END=D 로 낸 파일의 「날 ≤ D」 줄(후보·대조 값)이
     같은 자료(D 까지)로 보통 방식이 낸 파일과 **글자 하나까지** 같아야 한다
  ② 새 날이 맞나 — OWN_LIVE 가 덧붙인 다음 거래일(D+1) 후보가, D+1 자료까지 들어간 보통 방식의
     D+1 후보와 **같은 종목 묶음**이어야 한다 (순서는 갭이라 아침엔 모른다 — 묶음만 본다)
     ⚠️ 정당하게 다를 수 있는 것: D+1 에 거래정지된 종목(보통 방식엔 시세가 없어 빠진다) — 종목마다 이유를 찍는다

쓰는 법:
    python scripts\compare_live.py --live data\_labs\forward_groups_cand_live1006.jsonl \
        --old data\_labs\forward_groups_cand_data1006.jsonl --new data\forward_groups_cand.jsonl \
        --spec data\forward-groups-spec.json --out data\_labs\2026-10-08_B241_아침후보_대조.txt
끝 코드 0 = 둘 다 같다 · 1 = 다르다(쓰지 마라)
"""
import argparse
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")


def 읽기(p):
    줄, 대조, 머리 = {}, {}, {}
    for z in io.open(p, encoding="utf-8"):
        if not z.strip():
            continue
        r = json.loads(z)
        if r.get("규칙") == "_머리":
            머리[r["무리"]] = r["끝날"]
        elif "대조끝" in r:
            대조[r["규칙"]] = r
        elif "날" in r:
            줄[(r["규칙"], r["날"])] = r["후보"]
    return 줄, 대조, 머리


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    밖 = io.open(a.out, "w", encoding="utf-8")

    def 찍기(s=""):
        print(s, flush=True)
        밖.write(s + "\n")

    자리 = {r["id"]: r["자리"] for r in json.load(io.open(a.spec, encoding="utf-8"))["규칙"]}
    L, L대, L머리 = 읽기(a.live)
    O, O대, O머리 = 읽기(a.old)
    N, N대, N머리 = 읽기(a.new)
    D = max(O머리.values())
    찍기(f"B 아침 후보 대조 — 아침 방식(OWN_LIVE) 파일 끝 날 {sorted(set(L머리.values()))} · 옛 파일 끝 날 {sorted(set(O머리.values()))} · "
         f"새 파일 끝 날 {sorted(set(N머리.values()))}")
    문제 = 0

    # ① 옛 날들
    L옛 = {k: v for k, v in L.items() if k[1] <= D}
    같음 = sum(1 for k, v in L옛.items() if O.get(k) == v)
    빠짐 = [k for k in O if k not in L옛]
    더함 = [k for k in L옛 if k not in O]
    다름 = [k for k, v in L옛.items() if k in O and O[k] != v]
    대다름 = [k for k in O대 if json.dumps(O대[k], sort_keys=True) != json.dumps(L대.get(k), sort_keys=True)]
    찍기(f"\n① 옛 날들(≤{D}) — 줄 {len(O):,} 중 같음 {같음:,} · 다름 {len(다름)} · 아침 쪽에 없음 {len(빠짐)} · 아침 쪽에만 {len(더함)} · "
         f"대조 값 다름 {len(대다름)}/{len(O대)}")
    for k in (다름 + 빠짐 + 더함)[:10]:
        찍기(f"   ❌ {k}")
    for k in 대다름[:10]:
        찍기(f"   ❌ 대조 {k}: 옛 {O대[k].get('대조끝')} · 아침 {(L대.get(k) or {}).get('대조끝')}")
    if 다름 or 빠짐 or 더함 or 대다름:
        문제 += 1

    # ② 새 날
    새날 = sorted({k[1] for k in L if k[1] > D})
    찍기(f"\n② 새 날 {새날} — 아침 방식 후보 vs 보통 방식(그날 자료까지 들어간) 후보 · 종목 묶음")
    if not 새날:
        찍기("   ❌ 아침 방식 파일에 새 날 줄이 없다")
        문제 += 1
    for 날 in 새날:
        규칙들 = sorted({k[0] for k in L if k[1] == 날} | {k[0] for k in N if k[1] == 날})
        if not any(k[1] == 날 for k in N):
            찍기(f"   ⚠️ 보통 방식 파일에 {날} 줄이 없다 — 그날 자료가 아직 안 들어왔거나 후보가 없다 (새 파일 끝 날을 확인)")
        for 규 in 규칙들:
            a_ = {x["code"] for x in L.get((규, 날), [])}
            b_ = {x["code"] for x in N.get((규, 날), [])}
            잘림 = max(len(L.get((규, 날), [])), len(N.get((규, 날), []))) >= 자리.get(규, 0) + 60
            if a_ == b_:
                찍기(f"   ✅ {규} {날} 같음 {len(a_)}종목" + (" ⚠️ 여분 끝까지 차서 잘렸을 수 있다" if 잘림 else ""))
            else:
                찍기(f"   ❌ {규} {날} 다름 — 아침에만 {sorted(a_ - b_)} · 보통에만 {sorted(b_ - a_)}"
                     + (" (여분 끝까지 차서 순서 차이로 잘렸을 수 있다)" if 잘림 else ""))
                문제 += 1
    찍기(f"\n[대조] 아침 후보 대조 끝 — {'✅ 하나도 안 다르다' if not 문제 else f'❌ 다른 곳 {문제}군데 — 쓰지 않는다'}")
    밖.close()
    return 0 if not 문제 else 1


if __name__ == "__main__":
    sys.exit(main())
