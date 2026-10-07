"""여러 규칙이 함께 고른 종목 vs 한 규칙만 고른 종목 — 거래 하나하나 성적 (지금 규칙 + 업종별 8개)"""
import io
import json
import statistics as st
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
D = r"C:\Users\mrblue\Claude\morning breifing_code\data"
spec = {r["id"]: r for r in json.load(io.open(D + r"\forward-groups-spec.json", encoding="utf-8"))["규칙"]}
날별 = defaultdict(lambda: defaultdict(list))   # 날 → code → [(규칙, 결과)]
for 파일, 자리 in ((D + r"\_labs\multi_cand_live.jsonl", None), (D + r"\forward_groups_cand.jsonl", "spec")):
    for 줄 in io.open(파일, encoding="utf-8"):
        z = json.loads(줄)
        if z["규칙"] == "_머리" or "후보" not in z:
            continue
        n = spec[z["규칙"]]["자리"] if 자리 and z["규칙"] in spec else (8 if not 자리 else None)
        if n is None:
            continue
        for p in z["후보"][:n]:
            rs = [(b, r) for b, r, _ in p["몫"] if r is not None]
            if not rs:
                continue
            r = sum(b * x for b, x in rs) / sum(b for b, _ in rs)
            날별[z["날"]][p["code"]].append((z["규칙"], r))
for 기간, a, b in (("2016~2018", "2016", "2018"), ("2019~", "2019", "2099")):
    한, 겹 = [], []
    for d, cs in 날별.items():
        if not (a <= d[:4] <= b):
            continue
        for c, lst in cs.items():
            r = lst[0][1]
            (겹 if len({k for k, _ in lst}) >= 2 else 한).append(r)
    for 이름, xs in (("한 규칙만", 한), ("2개 이상 규칙", 겹)):
        if xs:
            print(f"{기간} {이름:<10} {len(xs):>5}건 · 수익 난 비율 {sum(1 for x in xs if x > 0) / len(xs) * 100:5.1f}% · 평균 {st.mean(xs):+.2f}% · 중앙 {st.median(xs):+.2f}%")
