#!/usr/bin/env python3
r"""
disclosure_reaction.py — **같은 공시인데 왜 어떤 종목은 오르고 어떤 종목은 내리나** (2026-10-08)

사용자 10/8: 「공시가 뜨면 오르는 종목이 있고 반대로 가는 종목이 있는데 이거에 대한 이유 알아?」

잰다 (data/dart-daily 2010~ · kind-time 접수 시각 · krx-daily 원본 시세):
  · 반응 = **공시 전 마지막 종가 → 공시 뒤 첫 종가** (장 전 공시 = 그날 종가 · 장중 = 그날 종가(일부 섞임) · 장 뒤 = 다음 날 종가)
  · 5일 = 공시 뒤 첫 종가 → 그 뒤 5거래일 종가 (첫 반응이 이어지나 되돌리나)
  · 공시 종류별: 건수 · 평균 · 중앙 · 오른 비율 · 아래 25% / 위 25% (같은 종류 안에서 얼마나 갈리나)
  · 갈리는 이유로 잴 수 있는 것: ① 공시 전 20일 이미 올랐나(선반영) ② 회사 크기 ③ 공시 시각(장 전/장중/장 뒤)
⚠️ 원본 시세라 공시일 근처 권리락(무상증자·분할)은 섞일 수 있다 — 그 둘은 「반응」 을 따로 읽는다
⚠️ 시장 전체 움직임은 빼지 않았다(2일 창이라 작다) — 같은 날 코스피·코스닥 중앙을 빼는 열을 함께 찍는다
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

종류 = [  # (이름, 공시명에 들어 있어야 할 말들(띄어쓰기 없앤 뒤), 빼야 할 말)
    ("자사주 취득", ("자기주식취득결정",), ("신탁",)),
    ("자사주 취득 신탁", ("자기주식취득신탁계약체결결정",), ()),
    ("자사주 처분", ("자기주식처분결정",), ()),
    ("자사주 소각", ("주식소각결정",), ()),
    ("유상증자", ("유상증자결정",), ("무상",)),
    ("무상증자", ("무상증자결정",), ("유상",)),
    ("감자", ("감자결정",), ()),
    ("전환사채 발행", ("전환사채권발행결정",), ()),
    ("신주인수권부사채 발행", ("신주인수권부사채권발행결정",), ()),
    ("공급계약", ("단일판매ㆍ공급계약체결", "단일판매·공급계약체결"), ("해지", "정정")),
    ("공급계약 해지", ("단일판매ㆍ공급계약해지", "단일판매·공급계약해지"), ()),
    ("잠정실적", ("영업(잠정)실적",), ("정정",)),
    ("매출·손익 30% 변동", ("매출액또는손익구조30%", "매출액또는손익구조15%"), ()),
    ("최대주주 변경", ("최대주주변경",), ("소유주식",)),
    ("합병", ("회사합병결정",), ()),
    ("현금배당", ("현금ㆍ현물배당결정", "현금·현물배당결정"), ()),
    ("주식분할", ("주식분할결정",), ()),
    ("타법인 주식 취득", ("타법인주식및출자증권취득결정",), ()),
    ("신규 시설투자", ("신규시설투자등",), ()),
    ("소송", ("소송등의제기",), ()),
    ("횡령·배임", ("횡령ㆍ배임", "횡령·배임"), ()),
    ("불성실공시", ("불성실공시법인지정",), ("예고",)),
    ("관리종목 지정", ("관리종목지정",), ("해제",)),
]


def 분류(제목):
    t = 제목.replace(" ", "")
    if t.startswith("[기재정정]") or "정정" in t[:6]:
        return None
    for 이름, 들, 빼 in 종류:
        if any(w in t for w in 들) and not any(w in t for w in 빼):
            return 이름
    return None


def main():
    # 1) 사건 모으기
    사건 = []
    for f in sorted(glob.glob(os.path.join(_D, "dart-daily", "*.json"))):
        d8 = os.path.basename(f)[:8]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
            tj = json.load(io.open(os.path.join(_D, "kind-time", f"{d8}.json"), encoding="utf-8-sig"))
        except (ValueError, OSError):
            continue
        시각 = tj.get("시각") or {}     # {접수번호: "HH:MM"} · 시각이 있는 공시만 쓴다(창이 정확하도록)
        for 칸 in ("챙길공시", "그밖의공시"):
            for x in j.get(칸) or []:
                c = str(x.get("종목코드") or "")
                if len(c) != 6:
                    continue
                k = 분류(str(x.get("공시명") or ""))
                t = 시각.get(x.get("접수번호"))
                if k and t:      # 시각 모르는 공시는 뺀다 — 장 뒤 공시를 그날 종가로 재면 반응을 놓친다
                    사건.append((d8, c, k, t))
    print(f"공시 사건 {len(사건):,}건 (종류 {len(종류)} · 2010~)", flush=True)
    # 2) 시세 — 사건에 나온 종목만
    코드들 = {c for _, c, _, _ in 사건}
    날, 시세, 시장중앙 = [], {}, {}
    for f in sorted(glob.glob(os.path.join(_D, "krx-daily", "*.json"))):
        d8 = os.path.basename(f)[:8]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        종 = j.get("종목") or {}
        날.append(d8)
        하루 = {}
        등 = []
        for c, v in 종.items():
            try:
                cl = float(v["종가"])
                r = float(v.get("등락률") or 0)
            except (TypeError, ValueError, KeyError):
                continue
            등.append(r)
            if c in 코드들:
                하루[c] = (cl, float(v.get("시총") or 0))
        시세[d8] = 하루
        시장중앙[d8] = st.median(등) if 등 else 0.0
    자리 = {d: i for i, d in enumerate(날)}
    # 3) 반응 재기
    줄 = {}
    for d8, c, k, t in 사건:
        i = 자리.get(d8)
        if i is None or i < 21:
            continue
        장뒤 = bool(t) and t >= "15:30"
        장중 = bool(t) and "09:00" <= t < "15:30"
        앞i = i - 1                       # 공시 전 마지막 종가: 전날
        뒤i = i + 1 if 장뒤 else i        # 공시 뒤 첫 종가
        if 뒤i + 5 >= len(날):
            continue
        a, b, e = 시세[날[앞i]].get(c), 시세[날[뒤i]].get(c), 시세[날[뒤i + 5]].get(c)
        p20 = 시세[날[앞i - 20]].get(c)
        if not a or not b or a[0] <= 0:
            continue
        반 = (b[0] / a[0] - 1) * 100
        if abs(반) > 60:                  # 권리락·분할 등 원본 가격 끊김
            continue
        시장 = sum(시장중앙.get(날[q], 0.0) for q in range(앞i + 1, 뒤i + 1))
        줄.setdefault(k, []).append({
            "반": 반, "초과": 반 - 시장,
            "5일": (e[0] / b[0] - 1) * 100 if e and b[0] > 0 else None,
            "앞20": (a[0] / p20[0] - 1) * 100 if p20 and p20[0] > 0 else None,
            "시총억": a[1] / 1e8, "때": "장뒤" if 장뒤 else ("장중" if 장중 else ("장전" if t else "모름")), "해": d8[:4]})
    밖 = io.open(os.path.join(_D, "_labs", "2026-10-08_공시반응.txt"), "w", encoding="utf-8")

    def 찍기(s=""):
        print(s, flush=True)
        밖.write(s + "\n")

    def q(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(len(xs) * p))]

    찍기("공시 종류별 주가 반응 — 공시 전 마지막 종가 → 공시 뒤 첫 종가 (%) · 2010~2026 · 시장초과 = 같은 기간 시장 중앙 등락을 뺀 값")
    찍기(f"{'종류':<16}{'건수':>7}{'평균':>8}{'중앙':>8}{'초과평균':>9}{'오른비율':>9}{'아래25%':>9}{'위25%':>8}{'그뒤5일':>9}")
    for k, _, _ in 종류:
        xs = 줄.get(k) or []
        if len(xs) < 30:
            continue
        r = [x["반"] for x in xs]
        r5 = [x["5일"] for x in xs if x["5일"] is not None]
        찍기(f"{k:<16}{len(xs):>7,}{st.mean(r):>+8.2f}{st.median(r):>+8.2f}{st.mean(x['초과'] for x in xs):>+9.2f}"
             f"{sum(1 for v in r if v > 0) / len(r) * 100:>8.0f}%{q(r, .25):>+9.2f}{q(r, .75):>+8.2f}{(st.mean(r5) if r5 else 0):>+9.2f}")

    찍기("\n같은 종류 안에서 갈리는 이유 ① — 공시 전 20일 이미 얼마나 올랐나 (셋으로 나눔 · 반응 평균 / 오른 비율)")
    찍기(f"{'종류':<16}{'이미 많이 빠짐':>18}{'중간':>16}{'이미 많이 오름':>18}")
    for k, _, _ in 종류:
        xs = [x for x in (줄.get(k) or []) if x["앞20"] is not None]
        if len(xs) < 90:
            continue
        xs.sort(key=lambda x: x["앞20"])
        n = len(xs) // 3
        칸 = [xs[:n], xs[n:2 * n], xs[2 * n:]]
        글 = "".join(f"{st.mean(x['반'] for x in z):>+9.2f} {sum(1 for x in z if x['반'] > 0) / len(z) * 100:>4.0f}%   " for z in 칸)
        찍기(f"{k:<16}{글}   (앞20 경계 {칸[0][-1]['앞20']:+.0f}% / {칸[2][0]['앞20']:+.0f}%)")

    찍기("\n같은 종류 안에서 갈리는 이유 ② — 회사 크기 (시총 1,000억 미만 / 1,000억~1조 / 1조 이상)")
    for k, _, _ in 종류:
        xs = 줄.get(k) or []
        if len(xs) < 90:
            continue
        칸 = [[x for x in xs if x["시총억"] < 1000], [x for x in xs if 1000 <= x["시총억"] < 10000], [x for x in xs if x["시총억"] >= 10000]]
        글 = "".join((f"{st.mean(x['반'] for x in z):>+8.2f}({len(z):>5,})  " if len(z) >= 20 else f"{'·':>8}({len(z):>5,})  ") for z in 칸)
        찍기(f"{k:<16}{글}")

    찍기("\n같은 종류 안에서 갈리는 이유 ③ — 공시 시각 (장 전 / 장중 / 장 뒤)")
    for k, _, _ in 종류:
        xs = 줄.get(k) or []
        if len(xs) < 90:
            continue
        글 = ""
        for 때 in ("장전", "장중", "장뒤"):
            z = [x for x in xs if x["때"] == 때]
            글 += (f"{때} {st.mean(x['반'] for x in z):>+6.2f}({len(z):>5,})  " if len(z) >= 20 else f"{때} {'·':>6}({len(z):>5,})  ")
        찍기(f"{k:<16}{글}")
    찍기("\n[대조] 공시 반응 끝")
    밖.close()


if __name__ == "__main__":
    main()
