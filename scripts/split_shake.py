#!/usr/bin/env python3
r"""
split_shake.py — **⑮ 나누는 해 흔들기** (2026-10-01) · 통과 규칙 20개를 앞/뒤 나누는 해 2017 · 2019 · 2021 로 다시 잰다

· own_lab OWN_EXPORT + OWN_SPLIT=2017/2019/2021 0101 (OWN_EXPORT_OUT=multi_cand_split{해}.jsonl) 이 낸
  「대조」 줄(같은 설정 · 오분위 문턱만 새 앞 기간 값으로 · 뒤 = 나누는 해부터)을 읽어 통과를 판정한다
· 통과 = own_lab ⑨ 뒤 확인과 같다: 현금만보다 많음 · 낙폭 {_한계:g}% 안 · 산 ≥ max(10, 2 × 뒤 해 수)
         **그리고** 같은 설정·조건 없이 아무 날 산 것이 낙폭 한계 안이면 그보다 많아야 한다 (사용자 9/30 결정 2)
· ⚠️ 새 표본 검증이 아니다 — 나눔 2017 의 뒤 2017~2018 은 규칙을 고른 앞 기간 안이고, 2021 의 뒤는 원래 뒤의 일부다.
  **문턱·기간에 대한 민감도**로 읽는다
· 사용자 「1,3,5는 너말대로 알아서해.」(⑬⑭⑮ 같은 승인) · 설계 docs/2026-09-30_무리전용_시험설계.md ⑮
"""
import io
import json
import math
import os
import sys

_L = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "_labs")
_밖 = io.open(os.path.join(_L, os.environ.get("LAB_OUT") or "split_shake.txt"), "w", encoding="utf-8")
# 10/4: 다른 판(2019 재료 시장 전체 등)도 흔들 수 있게 — 스펙·나누는 해·후보 파일 앞머리·낙폭 한계를 바꿀 수 있다 (기본은 10/1 그대로)
_해들 = tuple((os.environ.get("SHAKE_YEARS") or "2017,2019,2021").split(","))
_스펙파일 = os.environ.get("SHAKE_SPEC") or "multi_rules_spec.json"
_앞머리 = os.environ.get("SHAKE_PRE") or "multi_cand_split"
_한계 = float(os.environ.get("SHAKE_DD") or -12)


def 찍기(s=""):
    print(s, flush=True)
    _밖.write(s + "\n")
    _밖.flush()


def main():
    스펙 = json.load(io.open(os.path.join(_L, _스펙파일), encoding="utf-8"))["규칙"]
    판, 못, 끝날 = {}, {}, {}
    for 해 in _해들:
        p = os.path.join(_L, f"{_앞머리}{해}.jsonl")
        if not os.path.exists(p):
            raise SystemExit(f"🛑 {_앞머리}{해}.jsonl 이 없다")
        for 줄 in io.open(p, encoding="utf-8"):
            z = json.loads(줄)
            if z["규칙"] == "_머리":
                끝날.setdefault(해, set()).add(z["끝날"])
            elif "못만듦" in z:
                못[(z["규칙"], 해)] = z["못만듦"]
            elif "대조끝" in z:
                판[(z["규칙"], 해)] = z
    찍기("=" * 130)
    찍기(f"  ── ⑮ 나누는 해 흔들기 — 통과 규칙 {len(스펙)}개({_스펙파일}) · 나눔 {'·'.join(_해들)} · 설정 고정 · 오분위 문턱만 새 앞 기간으로 · 뒤 = 나누는 해부터 ──")
    찍기(f"     후보 파일 끝 날 { {k: sorted(v) for k, v in 끝날.items()} }")
    # 10/7 독립 검사: 해마다 다른 날 돌면 끝 날이 갈린다. 판정은 해마다 그 파일 안의 대조 값만 쓰므로 섞이지 않지만,
    #    뒤 기간 길이가 하루쯤 다르다 — 크게 찍어 읽는 사람이 알게 한다
    _모든끝 = set().union(*끝날.values()) if 끝날 else set()
    if len(_모든끝) > 1:
        찍기(f"  ⚠️⚠️ 해마다 후보 파일 끝 날이 다르다 {sorted(_모든끝)} — 판정은 해마다 따로라 섞이지 않지만 뒤 기간 길이가 다르다")
    찍기(f"     통과 = 현금만보다 많음 · 낙폭 {_한계:g}% 안 · 산 ≥ max(10, 2×뒤 해 수) · 아무 날(한계 안일 때)보다 많음 — own_lab ⑨ 와 같다")
    찍기("     ⚠️ 새 표본 검증이 아니라 **민감도**다: 나눔 2017 의 뒤 2017~18 은 규칙을 고른 앞 기간 안 · 2021 의 뒤는 원래 뒤의 일부")
    찍기("     「못 만듦」 = 새 앞 기간에 그 재료 값이 모자라거나 조건이 절반을 넘어 조건이 안 생김 · 「없음」 = 판이 터졌을 수 있다(무리 파일 확인)")
    찍기("=" * 130)
    찍기(f"  {'규칙':<5}{'무리':<22}{'조건':<38}" + "".join(f"{'나눔 ' + 해:>30}" for 해 in _해들) + "   잰 것 중 통과")
    통셋 = 0
    for r in 스펙:
        칸, 통수, 잰수, 빠 = [], 0, 0, []
        for 해 in _해들:
            z = 판.get((r["id"], 해))
            if not z:
                if (r["id"], 해) in 못:
                    칸.append(f"{'못 만듦 ' + ','.join(못[(r['id'], 해)])[:20]:>30}")
                    빠.append(f"{해} 못 만듦")
                else:
                    칸.append(f"{'없음 ❌ 판 터짐?':>30}")
                    빠.append(f"{해} 없음")
                continue
            잰수 += 1
            # 뒤 해 수 = 현금만 = 500만 × (1+0.025/245)^n 에서 n 을 되돌린다 (own_lab 시뮬과 같은 n)
            n = math.log(z["현금만"] / 5_000_000.0) / math.log(1 + 0.025 / 245)
            n해 = max(n / 245, 0.5)
            통 = (z["대조끝"] > z["현금만"] and z["대조낙"] >= _한계 and z["대조산"] >= max(10, 2 * n해)
                 and not (z["같낙"] >= _한계 and z["대조끝"] <= z["같끝"]))
            통수 += 1 if 통 else 0
            칸.append(f"{z['대조끝'] / 1e4:>9,.0f}만 {z['대조낙']:>5.1f}% {z['대조산']:>4}산 {'✅' if 통 else '❌'}"
                     f"{'(아무날↓)' if (z['같낙'] >= _한계 and z['대조끝'] <= z['같끝']) else '':>8}")
        if 통수 == len(_해들):   # 10/7 독립 검사: 3 고정이었다
            통셋 += 1
        다 = f"{통수}/{잰수}" + (f" ({' · '.join(빠)})" if 빠 else "")
        찍기(f"  {r['id']:<5}{r['무리'][:20]:<22}{r['조건'][:36]:<38}" + "".join(칸) + f"   {다}" + ("  ⚠️짧음" if r.get("짧음") else ""))
    찍기(f"\n  → 세 나눔 모두 재서 모두 통과 {통셋}개 / {len(스펙)}개")
    찍기("  [대조] SPLIT 흔들기 끝")
    _밖.close()


if __name__ == "__main__":
    sys.exit(main())
