#!/usr/bin/env python3
r"""
contract_reaction.py — **공급계약 공시: 크기(매출 대비 %)·선반영·방산에 따라 주가 반응이 어떻게 다른가** (2026-10-08)

사용자 10/8: 「방산 종목의 무기 계약 … 소식에도 오를 것 같은데 안 오르는 경우도 있더라고!」
자료: data/contract/YYYYMM.json (공급계약 체결·해지 · 금액 · 매출대비pct · 2010~) · kind-time 접수 시각 · krx-daily 원본 시세
반응 = 공시 전날 종가 → 공시 다음 날 종가 (2일 창 · 장중·장 뒤 공시 모두 담는다)
보는 것: ① 매출 대비 크기별 ② 공시 전 20일 이미 올랐나 ③ 방산 회사(chain_map 「방산」)만 따로 ④ 자율공시 vs 의무공시
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_D = os.path.join(_B, "data")
sys.path.insert(0, os.path.join(_B, "scripts"))


def main():
    try:
        from chain_map import 읽기 as _맵
        맵 = _맵()
        방산 = {c for s, 들 in 맵.items() if "방산" in s for _, c in 들 if c}
        우주 = {c for s, 들 in 맵.items() if "우주" in s for _, c in 들 if c}
        조선 = {c for s, 들 in 맵.items() if "조선" in s for _, c in 들 if c}
    except Exception:  # noqa: BLE001
        방산 = 우주 = 조선 = set()
    시각 = {}
    for f in glob.glob(os.path.join(_D, "kind-time", "*.json")):
        try:
            시각.update(json.load(io.open(f, encoding="utf-8-sig")).get("시각") or {})
        except ValueError:
            pass
    건들 = []
    for f in sorted(glob.glob(os.path.join(_D, "contract", "*.json"))):
        for rc, x in (json.load(io.open(f, encoding="utf-8-sig")).get("건") or {}).items():
            t = 시각.get(rc)
            if not x.get("코드"):
                continue
            제 = str(x.get("공시명") or "").replace(" ", "")
            if "정정" in 제:
                continue
            건들.append({"d": x["날짜"], "c": x["코드"], "t": t, "pct": x.get("매출대비pct"),
                        "해지": "해지" in 제, "자율": "자율" in 제})
    코드들 = {z["c"] for z in 건들}
    날, 시세 = [], {}
    for f in sorted(glob.glob(os.path.join(_D, "krx-daily", "*.json"))):
        d8 = os.path.basename(f)[:8]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        날.append(d8)
        시세[d8] = {c: (float(v["종가"]), float(v.get("시총") or 0)) for c, v in (j.get("종목") or {}).items()
                   if c in 코드들 and v.get("종가")}
    자리 = {d: i for i, d in enumerate(날)}
    줄 = []
    for z in 건들:
        i = 자리.get(z["d"])
        if i is None or i < 21:
            continue
        뒤i = i + 1     # 10/8: 시각 자료가 계약 공시엔 드물다 — 공시 전날 종가 → 다음 날 종가(장중·장 뒤 모두 담는 2일 창)
        if 뒤i + 5 >= len(날):
            continue
        a, b = 시세[날[i - 1]].get(z["c"]), 시세[날[뒤i]].get(z["c"])
        p20, e = 시세[날[i - 21]].get(z["c"]), 시세[날[뒤i + 5]].get(z["c"])
        if not a or not b or a[0] <= 0:
            continue
        반 = (b[0] / a[0] - 1) * 100
        if abs(반) > 60:
            continue
        줄.append(dict(z, 반=반, 앞20=(a[0] / p20[0] - 1) * 100 if p20 and p20[0] > 0 else None,
                       오일=(e[0] / b[0] - 1) * 100 if e and b[0] > 0 else None, 시총억=a[1] / 1e8))
    밖 = io.open(os.path.join(_D, "_labs", "2026-10-08_공급계약반응.txt"), "w", encoding="utf-8")

    def 찍기(s=""):
        print(s, flush=True)
        밖.write(s + "\n")

    def 요약(xs):
        if len(xs) < 15:
            return f"{'·':>7} ({len(xs):>5,}건)"
        r = [x["반"] for x in xs]
        r5 = [x["오일"] for x in xs if x["오일"] is not None]
        return (f"평균 {st.mean(r):>+6.2f} · 중앙 {st.median(r):>+6.2f} · 오른 {sum(1 for v in r if v > 0) / len(r) * 100:>3.0f}% · "
                f"그뒤5일 중앙 {st.median(r5) if r5 else 0:>+5.2f} ({len(xs):>5,}건)")
    체결 = [x for x in 줄 if not x["해지"]]
    찍기(f"공급계약 공시 반응 · 2010~ · 공시 {len(줄):,}건(체결 {len(체결):,} · 해지 {len(줄) - len(체결):,})")
    찍기("반응 = 공시 전날 종가 → 공시 다음 날 종가 (%) · 그뒤5일 = 첫 반응 뒤 5거래일 (이어가나 되돌리나)\n")
    찍기("① 계약 금액이 매출의 몇 %인가")
    for 라, lo, hi in (("5% 미만", 0, 5), ("5~10%", 5, 10), ("10~20%", 10, 20), ("20~50%", 20, 50), ("50% 이상", 50, 1e9)):
        찍기(f"  {라:<9} {요약([x for x in 체결 if x['pct'] is not None and lo <= x['pct'] < hi])}")
    찍기(f"  해지      {요약([x for x in 줄 if x['해지']])}")
    찍기("\n② 공시 전 20일 이미 얼마나 올랐나 (체결만)")
    for 라, lo, hi in (("−10% 밑(빠지던 중)", -1e9, -10), ("−10~0%", -10, 0), ("0~+10%", 0, 10), ("+10~+30%", 10, 30), ("+30% 넘게(이미 급등)", 30, 1e9)):
        찍기(f"  {라:<16} {요약([x for x in 체결 if x['앞20'] is not None and lo <= x['앞20'] < hi])}")
    찍기("\n③ 크기 × 선반영 (매출 20% 이상 큰 계약만)")
    큰 = [x for x in 체결 if x["pct"] is not None and x["pct"] >= 20]
    for 라, lo, hi in (("이미 안 오른 것(앞20 < +10%)", -1e9, 10), ("이미 오른 것(앞20 ≥ +10%)", 10, 1e9)):
        찍기(f"  {라:<22} {요약([x for x in 큰 if x['앞20'] is not None and lo <= x['앞20'] < hi])}")
    찍기("\n④ 업종 (chain_map)")
    for 이름, 들 in (("방산", 방산), ("조선", 조선), ("우주", 우주)):
        xs = [x for x in 체결 if x["c"] in 들]
        찍기(f"  {이름:<4} 전체      {요약(xs)}")
        찍기(f"  {이름:<4} 매출 20%↑ {요약([x for x in xs if x['pct'] is not None and x['pct'] >= 20])}")
        찍기(f"  {이름:<4} 매출 20%↓ {요약([x for x in xs if x['pct'] is not None and x['pct'] < 20])}")
        찍기(f"  {이름:<4} 이미 오른 것(앞20 ≥ +10%) {요약([x for x in xs if x['앞20'] is not None and x['앞20'] >= 10])}")
    찍기("\n⑤ 자율공시(의무 아님 · 회사가 알리고 싶어서) vs 의무공시")
    찍기(f"  자율 {요약([x for x in 체결 if x['자율']])}")
    찍기(f"  의무 {요약([x for x in 체결 if not x['자율']])}")
    찍기("\n⑥ 회사 크기 (체결만)")
    for 라, lo, hi in (("1,000억 미만", 0, 1000), ("1,000억~1조", 1000, 10000), ("1조 이상", 10000, 1e12)):
        찍기(f"  {라:<11} {요약([x for x in 체결 if lo <= x['시총억'] < hi])}")
    찍기("\n[대조] 공급계약 반응 끝")
    밖.close()


if __name__ == "__main__":
    main()
