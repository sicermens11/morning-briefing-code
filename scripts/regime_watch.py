#!/usr/bin/env python3
r"""
regime_watch.py — **변화 감지 장치** (2026-10-02)

사용자: 「우리가 과거 데이터를 가지고 테스트를 하는데, 결국 시장은 계속 변할 수 있는데, 우리가 그 변화에 대응할 수 있는 시스템이나
        변화를 감지하는 시스템이 있나?」 → 「만들어두자.」
원칙: 장치는 「무엇이 얼마나 벗어났나」 를 근거와 함께 **알리기만** 한다 · 규칙을 빼거나 바꾸는 결정은 사용자 · 🔴 기준은 결과 보기 전에 정한다(초안)

① 규칙 성적 감시 — 예측 기록(forward-log · forward-groups-log)이 채점되면 규칙마다 실제 이김%를 과거 시험(2019~)과 견준다 (이항 검정)
② 시장 국면 감시 — 코스닥 60일 추세 × 20일 변동성 × 대형(코스피) 쏠림으로 오늘 국면을 붙이고, **규칙마다 그 국면에서 과거에 어땠나**
③ 입력 변화 감시 — 실전 규칙 「후보 뜬 날」 비율·업종 분포가 최근 60거래일에 과거와 얼마나 다른가

⚠️ 무거운 주가 표를 안 읽는다(지수 파일 + 이미 만든 후보 파일만) — 판(시험) 자리를 안 쓴다
✅ 기준 확정 2026-10-06 — 사용자 「A. 사용자 결정 대기 3번 너가 말한 게 권고사항이지? 너 권고대로 하자.」 (바꾸면 날짜와 원문을 같이 적는다)
쓰는 법: python scripts/regime_watch.py  → data/watch/watch-<날>.md · data/watch/latest.json
"""
import datetime
import glob
import io
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_D = os.path.join(_B, "data")
_L = os.path.join(_D, "_labs")
# ── 🔴 기준 (10/6 사용자 확정 · 결과 보기 전에 정한 값) ──
추세문 = 8.0          # 코스닥 60일 수익률 ±8% → 상승 / 하락 · 그 사이 횡보
변동위 = 0.70         # 20일 변동성이 **그날까지** 분포의 위 30% 면 「높음」 (미래 안 봄)
쏠림문 = 8.0          # 코스피 60일 − 코스닥 60일 ≥ 8%p → 「대형 쏠림」(반도체 대형주 장 같은 때)
성적_최소 = 20        # 채점된 거래가 20건 넘어야 판정
성적_빨강 = 0.01      # 과거 이김% 로 이 정도 나쁠 확률이 1% 밑이면 🔴 · 5% 밑이면 🟡
업종쏠림문 = 8.0      # 10/6 — 최근 120거래일 후보에서 한 업종 비중이 평소보다 8%p 넘게 늘면 🟡 (사용자에게 이렇게 설명하고 확정받음)


def 지수계열():
    날, 피, 닥 = [], [], []
    for f in sorted(glob.glob(os.path.join(_D, "index-daily", "*.json"))):
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
            z = j.get("지수") or {}
            p = float(str(z["코스피"]["종가"]).replace(",", ""))
            q = float(str(z["코스닥"]["종가"]).replace(",", ""))
        except Exception:  # noqa: BLE001
            continue
        날.append(j.get("기준일") or os.path.basename(f)[:8])
        피.append(p)
        닥.append(q)
    return 날, 피, 닥


def 국면표():
    날, 피, 닥 = 지수계열()
    수 = [None] + [닥[k] / 닥[k - 1] - 1 for k in range(1, len(닥))]
    변들, 표 = [], {}
    for k in range(60, len(날)):
        추 = (닥[k] / 닥[k - 60] - 1) * 100
        피추 = (피[k] / 피[k - 60] - 1) * 100
        변 = st.pstdev([x for x in 수[k - 19:k + 1] if x is not None]) * 100
        변들.append(변)
        정렬 = sorted(변들)
        분위 = 정렬.index(변) / max(1, len(정렬) - 1)
        표[날[k]] = {"추세": "상승" if 추 >= 추세문 else ("하락" if 추 <= -추세문 else "횡보"),
                    "변동": "높음" if (len(변들) > 250 and 분위 >= 변동위) else "보통",
                    "쏠림": "대형 쏠림" if 피추 - 추 >= 쏠림문 else "-",
                    "닥60": round(추, 1), "피60": round(피추, 1), "변20": round(변, 2)}
    return 표


def 거래들():
    """규칙 → [(매수일, 결과%)] — 실전(L00) · 무리 규칙(스펙) · 예측 기록 8개"""
    out, 이름 = defaultdict(list), {}

    def 한거래(p):
        s = w = 0.0
        for 비, r, _ in p["몫"]:
            if r is not None:
                s += 비 * r
                w += 비
        return s / w if w else None
    자리 = {}
    sp = os.path.join(_L, "multi_rules_spec.json")
    if os.path.exists(sp):
        for r in json.load(io.open(sp, encoding="utf-8"))["규칙"]:
            자리[r["id"]] = r["자리"]
            이름[r["id"]] = f"{r['무리']} [{r['조건']}]"
    이름["L00"] = "실전 규칙(지금 화면)"
    for f in ("multi_cand_live.jsonl", "multi_cand_own.jsonl"):
        p = os.path.join(_L, f)
        if not os.path.exists(p):
            continue
        for 줄 in io.open(p, encoding="utf-8"):
            z = json.loads(줄)
            if "후보" not in z:
                continue
            for q in z["후보"][:자리.get(z["규칙"], 99)]:
                v = 한거래(q)
                if v is not None:
                    out[z["규칙"]].append((z["날"], v, q["code"]))
    return out, 이름


def 이항_아래(k, n, p):
    """이김 k 이하가 나올 확률 (과거 이김% p 가 맞다면)"""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def main():
    오늘 = f"{datetime.date.today():%Y%m%d}"
    국 = 국면표()
    끝날 = max(국)
    지금 = 국[끝날]
    거, 이름 = 거래들()
    줄 = [f"# 변화 감지 보고 — {끝날[:4]}-{끝날[4:6]}-{끝날[6:]} 자료 기준 (만든 날 {오늘})", "",
         "> 장치는 알리기만 한다 · 규칙을 바꾸는 결정은 사용자 · 국면 문턱과 🔴 기준은 **10/6 사용자 확정**", ""]
    # ② 지금 국면
    줄 += ["## ② 지금 시장 국면", "",
           f"- 코스닥 60일 **{지금['닥60']:+.1f}%** → 추세 **{지금['추세']}** · 20일 변동성 {지금['변20']:.2f}% → **{지금['변동']}**"
           f" · 코스피 60일 {지금['피60']:+.1f}% → {지금['쏠림'] if 지금['쏠림'] != '-' else '쏠림 없음'}", ""]
    키 = (지금["추세"], 지금["변동"], 지금["쏠림"])
    같은날 = {d for d, v in 국.items() if (v["추세"], v["변동"], v["쏠림"]) == 키}
    줄 += [f"- 2010년 뒤 이런 국면이었던 날: **{len(같은날):,}일** / {len(국):,}일 ({len(같은날) / len(국) * 100:.0f}%)", ""]
    줄 += ["### 규칙마다 — 이 국면에서 과거에 어땠나 (그 국면에 산 거래 · 비용 넣음)", "",
           "| 규칙 | 이 국면 거래 | 이김 | 평균 | 다른 때 거래 | 이김 | 평균 | 판단 |", "|---|---|---|---|---|---|---|---|"]
    결과 = {}
    for k in sorted(거, key=lambda z: (z != "L00", z)):
        안 = [v for d, v, _ in 거[k] if d in 같은날]
        밖 = [v for d, v, _ in 거[k] if d not in 같은날 and d in 국]
        if not 밖:
            continue

        def 요(xs):
            return (len(xs), sum(1 for x in xs if x > 0) / len(xs) * 100 if xs else None, st.mean(xs) if xs else None)
        a, b = 요(안), 요(밖)
        판 = "자료 적음" if a[0] < 10 else ("이 국면에 약했다 🟡" if a[2] < b[2] - 5 or a[1] < b[1] - 15 else
                                        ("이 국면에 강했다" if a[2] > b[2] + 5 else "비슷"))
        결과[k] = {"이름": 이름.get(k, k), "이국면": a, "다른때": b, "판단": 판}
        f = (lambda t: f"{t[0]} | {t[1]:.0f}% | {t[2]:+.1f}%" if t[0] else f"{t[0]} | - | -")
        줄.append(f"| {k} {이름.get(k, k)[:40]} | {f(a)} | {f(b)} | {판} |")
    # ③ 입력 변화
    줄 += ["", "## ③ 입력 변화 — 실전 규칙 후보가 평소와 다르게 뜨나", ""]
    L = 거.get("L00", [])
    날들 = sorted(국)
    뜬 = {d for d, _, _ in L}
    if L and len(날들) > 300:
        자료끝 = max(d for d, _, _ in L)
        구간 = [d for d in 날들 if d <= 자료끝]
        창 = [sum(1 for d in 구간[k - 60:k] if d in 뜬) / 60 * 100 for k in range(60, len(구간))]
        최근 = 창[-1]
        분 = sum(1 for x in 창 if x <= 최근) / len(창) * 100
        줄.append(f"- 최근 60거래일(~{자료끝}) 후보 뜬 날 **{최근:.0f}%** · 2016~ 60일 창들 중 아래에서 {분:.0f}% 자리"
                  + (" → **평소보다 적다 🟡**" if 분 <= 10 else (" → **평소보다 많다 🟡**" if 분 >= 90 else " → 평소 범위")))
        ind = json.load(io.open(os.path.join(_D, "industry.json"), encoding="utf-8-sig"))
        업 = {c: (v.get("업종명") if isinstance(v, dict) else None) or "?" for c, v in ind.items()}
        최근120 = set(구간[-120:])
        a = defaultdict(int)
        b = defaultdict(int)
        for d, _, c in L:
            (a if d in 최근120 else b)[업.get(c, "?")] += 1
        na, nb = sum(a.values()) or 1, sum(b.values()) or 1
        차 = sorted(((a[u] / na - b[u] / nb) * 100, u) for u in set(a) | set(b))
        줄.append(f"- 최근 120거래일 후보 {na}건의 업종 — 평소보다 **늘어난 쪽**: "
                  + ", ".join(f"{u} {x:+.0f}%p" for x, u in 차[::-1][:3] if x > 0)
                  + " · **줄어든 쪽**: " + ", ".join(f"{u} {x:+.0f}%p" for x, u in 차[:3] if x < 0))
        _쏠 = [(x, u) for x, u in 차 if x >= 업종쏠림문]
        if _쏠:
            줄.append("- 🟡 **업종 쏠림** — 평소보다 " + f"{업종쏠림문:g}%p 넘게 늘어난 업종: " + ", ".join(f"{u} {x:+.0f}%p" for x, u in _쏠[::-1]))
    # ① 성적 감시
    줄 += ["", "## ① 규칙 성적 감시 — 예측 기록 (과거 2019~ 이김%와 견줌)", ""]
    채, 전체 = defaultdict(list), defaultdict(int)
    for f in ("forward-groups-log.jsonl", "forward-sectors-log.jsonl"):   # 10/6 반도체·2차전지 장부도
        p = os.path.join(_D, f)
        if os.path.exists(p):
            for s in io.open(p, encoding="utf-8"):
                z = json.loads(s)
                for q in z.get("종목", []):
                    전체[z["규칙"]] += 1
                    rs = [(b, r) for b, r, _ in q["몫"] if r is not None]
                    if rs and len(rs) == len(q["몫"]):
                        채[z["규칙"]].append(sum(b * r for b, r in rs) / sum(b for b, _ in rs))
    if not 전체:
        줄.append("- 예측 기록이 아직 없다 (10/6 화요일부터 쌓인다) — 틀만 있다")
    for k in sorted(전체):
        과 = [v for d, v, _ in 거.get(k, []) if d >= "20190101"]
        p0 = sum(1 for x in 과 if x > 0) / len(과) if 과 else None
        xs = 채.get(k, [])
        if len(xs) < 성적_최소 or not p0:
            줄.append(f"- {k} {이름.get(k, k)[:40]}: 기록 {전체[k]}건 · 채점 {len(xs)}건 — {성적_최소}건 모이면 판정")
            continue
        w = sum(1 for x in xs if x > 0)
        pv = 이항_아래(w, len(xs), p0)
        표 = "🔴" if pv < 성적_빨강 else ("🟡" if pv < 0.05 else "✅")
        줄.append(f"- {표} {k}: 채점 {len(xs)}건 이김 {w / len(xs) * 100:.0f}% (과거 {p0 * 100:.0f}%) · 이만큼 나쁠 확률 {pv * 100:.1f}%")
    줄 += ["", "## 기준 (10/6 사용자 확정)", "",
           f"- 국면: 코스닥 60일 ±{추세문:g}% · 20일 변동성 그날까지 위 {round((1 - 변동위) * 100)}% · 코스피−코스닥 60일 ≥ {쏠림문:g}%p 면 대형 쏠림 · 후보 업종 비중 +{업종쏠림문:g}%p↑ 🟡",
           f"- 성적: 채점 {성적_최소}건 이상 · 과거 이김%로 이만큼 나쁠 확률 <{성적_빨강 * 100:g}% 🔴 · <5% 🟡",
           "- 국면 판단: 이 국면 평균이 다른 때보다 5%p 넘게 낮거나 이김이 15%p 넘게 낮으면 🟡 (거래 10건 미만은 「자료 적음」)"]
    os.makedirs(os.path.join(_D, "watch"), exist_ok=True)
    md = os.path.join(_D, "watch", f"watch-{오늘}.md")
    io.open(md, "w", encoding="utf-8").write("\n".join(줄) + "\n")
    io.open(os.path.join(_D, "watch", "latest.json"), "w", encoding="utf-8").write(json.dumps(
        {"만든날": 오늘, "자료끝": 끝날, "지금국면": 지금, "같은국면_일수": len(같은날), "규칙": 결과}, ensure_ascii=False, indent=1))
    print("\n".join(줄))
    print(f"\n썼다 {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
